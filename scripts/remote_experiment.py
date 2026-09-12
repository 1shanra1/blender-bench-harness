"""Deploy the batch controller; only this container mounts the results volume."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import modal
from environment import blender_image

ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "blender-bench-controller"
VOLUME_NAME = "blender-bench-results"
app = modal.App(APP_NAME)
results = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True, version=2)

# Bundle code only. Inputs arrive with each invocation; credentials and previous
# experiments are never copied into this image or into an agent sandbox.
controller_image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("modal==1.5.5")
    .env({"PYTHONPATH": "/opt/project/scripts"})
    .add_local_dir(ROOT / "scripts", "/opt/project/scripts", copy=True, ignore=["**/__pycache__/**"])
    .add_local_dir(ROOT / "runtime", "/opt/project/runtime", copy=True, ignore=["**/__pycache__/**"])
)


@app.function(
    image=controller_image,
    volumes={"/results": results},
    # 90 minutes for the agent, plus setup, image preparation and final rendering.
    timeout=135 * 60,
    retries=0,
    memory=4096,  # Reservation for concurrent archive collection; no hard ceiling.
    include_source=False,
)
def run_batch(batch_id, harnesses, reference, prompt, skip_evaluation=False, model=None):
    from run_experiment import run
    from verify_pairings import PAIRINGS

    if not harnesses or len(set(harnesses)) != len(harnesses):
        raise ValueError("Select each harness once")
    if any(h not in PAIRINGS for h in harnesses):
        raise ValueError("Unknown harness")
    if model and any(h not in {"codex", "claude", "kimi"} for h in harnesses):
        raise ValueError("A shared model override requires Vercel-backed harnesses")
    allowed = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-"
    if not batch_id or any(c not in allowed for c in batch_id):
        raise ValueError("Invalid batch ID")

    batch = Path("/results/experiments") / batch_id
    # An existing directory stops a repeated invocation from rerunning agents.
    batch.mkdir(parents=True, exist_ok=False)
    (batch / "reference.png").write_bytes(reference)
    (batch / "prompt.md").write_bytes(prompt)
    summary = {
        "batch_id": batch_id,
        "status": "running",
        "harnesses": harnesses,
        "models": {h: model or PAIRINGS[h].model for h in harnesses},
        "results": {},
    }

    commit_lock = Lock()

    def commit():
        # Each collector writes its own folder; serialize shared-volume commits.
        with commit_lock:
            results.commit()

    def save_summary():
        (batch / "batch.json").write_text(json.dumps(summary, indent=2))
        commit()

    save_summary()
    try:
        with ThreadPoolExecutor(max_workers=len(harnesses)) as pool:
            futures = {
                pool.submit(
                    run, h, batch, skip_evaluation,
                    reference=reference, prompt=prompt, commit=commit, model=model
                ): h
                for h in harnesses
            }
            for future in as_completed(futures):
                harness = futures[future]
                try:
                    _, outcome = future.result()
                except Exception as exc:
                    outcome = {"status": "controller_failed", "error": str(exc)}
                summary["results"][harness] = outcome
                save_summary()
        # This means collection has ended, not that every agent succeeded.
        summary["status"] = "finished"
    except Exception as exc:
        summary.update(status="controller_failed", error=str(exc))
        raise
    finally:
        save_summary()
    return summary


# Conversion uses Blender on Modal; source scenes never need to reach the Mac.
export_image = (
    blender_image
    .uv_pip_install("modal==1.5.5")
    .env({"PYTHONPATH": "/opt/project/scripts"})
    .add_local_dir(ROOT / "scripts", "/opt/project/scripts", copy=True, ignore=["**/__pycache__/**"])
    .add_local_dir(ROOT / "runtime", "/opt/project/runtime", copy=True, ignore=["**/__pycache__/**"])
)


@app.function(image=export_image, volumes={"/results": results},
              timeout=1800, cpu=4, memory=8192, include_source=False)
def export_results(batches, include_models=True):
    """Prepare a static website bundle next to the archives, without agent access."""
    import tarfile
    import uuid
    from tempfile import TemporaryDirectory
    from export_results import build_bundle
    from export_glb import export_run

    results.reload()
    exports = Path("/results/exports")
    exports.mkdir(exist_ok=True)
    archive = exports / f"{uuid.uuid4().hex}.tar.gz"
    with TemporaryDirectory() as temporary:
        bundle = Path(temporary) / "data"
        # Validate the selection before opening scenes, and find runs missing a GLB.
        catalogue = build_bundle(Path("/results"), batches, bundle, include_models)
        if include_models:
            import shutil
            for experiment in catalogue["experiments"]:
                for run in experiment["runs"]:
                    if run["model_url"]:
                        continue
                    run_dir = Path("/results/experiments") / experiment["id"] / run["id"]
                    has_scene = any((run_dir / path).is_file() for path in (
                        "capture/artifacts/scene.blend", "live-backup/scene.blend"
                    ))
                    if has_scene and not export_run(run_dir, blender_path="/usr/local/bin/blender"):
                        raise RuntimeError(f"GLB conversion failed: {run_dir}")
            shutil.rmtree(bundle)
            build_bundle(Path("/results"), batches, bundle, include_models)

        with tarfile.open(archive, "w:gz") as output:
            for path in sorted(bundle.rglob("*")):
                if path.is_file():
                    output.add(path, arcname=path.relative_to(bundle))
    results.commit()
    return {"path": str(archive.relative_to("/results")), "bytes": archive.stat().st_size}
