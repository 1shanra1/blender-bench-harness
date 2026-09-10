"""Deploy the batch controller; only this container mounts the results volume."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import modal

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
    .add_local_dir(ROOT / "scripts", "/opt/project/scripts", ignore=["**/__pycache__/**"])
    .add_local_dir(ROOT / "runtime", "/opt/project/runtime", ignore=["**/__pycache__/**"])
)


@app.function(
    image=controller_image,
    volumes={"/results": results},
    # 75 minutes for the agent, plus setup, image preparation and final rendering.
    timeout=2 * 60 * 60,
    retries=0,
    memory=4096,  # Reservation for concurrent archive collection; no hard ceiling.
    include_source=False,
)
def run_batch(batch_id, harnesses, reference, prompt, skip_evaluation=False):
    from run_experiment import run
    from verify_pairings import PAIRINGS

    if not harnesses or len(set(harnesses)) != len(harnesses):
        raise ValueError("Select each harness once")
    if any(h not in PAIRINGS for h in harnesses):
        raise ValueError("Unknown harness")
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
                    reference=reference, prompt=prompt, commit=commit
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
