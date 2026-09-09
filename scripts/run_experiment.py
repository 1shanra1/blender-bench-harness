"""Run selected harnesses independently; no reconstruction runs on import."""

import argparse
import json
import tarfile
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import modal
from antigravity_setup import AGY_VERSION
from codex_setup import CODEX_VERSION
from cursor_setup import CURSOR_VERSION, CURSOR_TIMEOUT_PATCH
from environment import ROOT, blender_image
from shared_sandbox import (
    EXPERIMENT_SECONDS,
    PROMPT,
    create_sandbox,
    prepare_workspace,
    start_blender,
)
from verify_pairings import PAIRINGS

VERSIONS = {
    "codex": CODEX_VERSION,
    "cursor": CURSOR_VERSION,
    "antigravity": AGY_VERSION,
}


def unpack(archive_path, destination):
    # Remote output is untrusted. Reject links and non-files; constrain paths.
    with tarfile.open(archive_path) as archive:
        for member in archive:
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Archive path escapes run directory")
            if not (member.isdir() or member.isfile()):
                raise ValueError("Archive contains a link or special file")
        archive.extractall(destination, filter="data")


def evaluate(folder, exclude_objects=()):
    artifacts = folder / "capture/artifacts"
    if not (artifacts / "scene.blend").is_file():
        return {"status": "skipped", "reason": "No final scene.blend saved"}
    sandbox = modal.Sandbox.create(
        app=modal.App.lookup("blender-bench-harness"),
        image=blender_image.add_local_dir(ROOT / "runtime", remote_path="/opt/bench"),
        block_network=True,
        cpu=(4.0, 4.0),
        memory=(8192, 8192),
        timeout=600,
    )
    try:
        # Preserve relative resources beside the scene, even if the agent failed to pack them.
        for path in artifacts.rglob("*"):
            if path.is_file() and not path.is_symlink():
                remote = "/workspace/output/" + str(path.relative_to(artifacts))
                mkdir = sandbox.exec("mkdir", "-p", str(Path(remote).parent))
                mkdir.wait()
                if mkdir.returncode:
                    raise RuntimeError(mkdir.stderr.read())
                sandbox.filesystem.write_bytes(path.read_bytes(), remote)
        render_arguments = []
        for name in exclude_objects:
            render_arguments.extend(["--exclude-object", name])
        process = sandbox.exec(
            "blender",
            "--background",
            "--factory-startup",
            "--disable-autoexec",
            "--python-exit-code",
            "1",
            "/workspace/output/scene.blend",
            "--python",
            "/opt/bench/render_views.py",
            "--",
            *render_arguments,
            timeout=540,
        )
        (folder / "evaluation.log").write_text(
            process.stdout.read() + process.stderr.read()
        )
        process.wait()
        pack = sandbox.exec(
            "tar", "-cf", "/tmp/evaluation.tar", "-C", "/", "evaluation"
        )
        pack.wait()
        if pack.returncode == 0:
            archive = folder / "evaluation.tar"
            archive.write_bytes(sandbox.filesystem.read_bytes("/tmp/evaluation.tar"))
            unpack(archive, folder)
            archive.unlink()
        return {
            "status": "complete" if process.returncode == 0 else "failed",
            "exit_code": process.returncode,
        }
    finally:
        sandbox.terminate()


def run(harness, batch, skip_evaluation=False):
    folder = batch / harness
    folder.mkdir()
    pairing = PAIRINGS[harness]
    sandbox = None
    stage = "setup"
    result = {}
    try:
        # Extra lifetime is for setup and collection; the supervisor caps the agent
        # separately and kills its process group at 75 minutes.
        sandbox = create_sandbox(
            pairing.image, pairing.secret, pairing.domains, EXPERIMENT_SECONDS + 600
        )
        manifest = prepare_workspace(sandbox)
        manifest.update(
            harness=harness,
            harness_version=VERSIONS[harness],
            model=pairing.model,
            provider="vercel" if harness == "codex" else harness,
            sandbox_id=sandbox.object_id,
            reasoning_effort="high",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        if harness == "cursor":
            manifest["harness_patch"] = CURSOR_TIMEOUT_PATCH
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (folder / "prompt.md").write_bytes(PROMPT.read_bytes())
        start_blender(sandbox)
        stage = "execution"
        process = sandbox.exec(
            "python",
            "/opt/bench/experiment_supervisor.py",
            harness,
            "--seconds",
            str(EXPERIMENT_SECONDS),
            env={"BENCH_MODEL": pairing.model},
            timeout=EXPERIMENT_SECONDS + 300,
        )
        with (folder / "supervisor.log").open("w") as log:
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(f"[{harness}] {line}", end="", flush=True)
            log.write(process.stderr.read())
        process.wait()
        if process.returncode:
            raise RuntimeError(f"Supervisor exited {process.returncode}")
        archive = folder / "capture.tar"
        archive.write_bytes(sandbox.filesystem.read_bytes("/tmp/bench-result.tar"))
        unpack(archive, folder)
        archive.unlink()
        result = json.loads((folder / "capture/result.json").read_text())
    except Exception as exc:
        result = {"status": f"{stage}_failed", "error": str(exc)}
        # Recover any files already captured even if the supervisor failed.
        if sandbox:
            try:
                pack = sandbox.exec(
                    "tar", "-cf", "/tmp/recovery.tar", "-C", "/tmp", "bench-capture"
                )
                pack.wait()
                if pack.returncode == 0:
                    archive = folder / "recovery.tar"
                    archive.write_bytes(
                        sandbox.filesystem.read_bytes("/tmp/recovery.tar")
                    )
            except Exception as recovery_error:
                result["recovery_error"] = str(recovery_error)
    finally:
        if sandbox:
            sandbox.terminate()
        (folder / "result.json").write_text(json.dumps(result, indent=2))
    if skip_evaluation:
        result["evaluation"] = {"status": "skipped", "reason": "--skip-evaluation"}
    else:
        try:
            result["evaluation"] = evaluate(folder)
        except Exception as exc:
            result["evaluation"] = {"status": "failed", "error": str(exc)}
    (folder / "result.json").write_text(json.dumps(result, indent=2))
    return harness, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", nargs="+", required=True, choices=PAIRINGS)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print plan without Modal or model calls"
    )
    parser.add_argument("--skip-evaluation", action="store_true")
    args = parser.parse_args()
    if len(set(args.harness)) != len(args.harness):
        parser.error(
            "Specify each harness once; use another invocation for repetitions"
        )
    if args.dry_run:
        print(
            json.dumps(
                {
                    "harnesses": args.harness,
                    "seconds": EXPERIMENT_SECONDS,
                    "prompt": str(PROMPT),
                    "models": {h: PAIRINGS[h].model for h in args.harness},
                    "evaluation": not args.skip_evaluation,
                },
                indent=2,
            )
        )
        return
    batch = (
        ROOT
        / "outputs/experiments"
        / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid.uuid4().hex[:8]
        )
    )
    batch.mkdir(parents=True)
    print("Results:", batch, flush=True)
    with ThreadPoolExecutor(max_workers=len(args.harness)) as pool:
        futures = [
            pool.submit(run, h, batch, args.skip_evaluation) for h in args.harness
        ]
        for future in as_completed(futures):
            harness, result = future.result()
            print(harness, json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
