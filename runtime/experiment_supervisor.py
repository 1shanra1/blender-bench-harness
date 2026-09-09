"""Bound a single native goal process and archive files. Never send follow-up prompts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tarfile
import threading
import time

CAPTURE = Path('/tmp/bench-capture')


def capture_files(workspace, destination, seen, started):
    """Capture stable saved versions, ignoring symlinks and files outside output."""
    for path in workspace.rglob('*'):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            before = path.stat()
        except OSError:
            continue
        signature = (before.st_size, before.st_mtime_ns)
        relative = str(path.relative_to(workspace))
        if seen.get(relative) == signature:
            continue
        try:
            # A file may disappear or be replaced while Blender saves it.
            with path.open('rb') as source:
                data = source.read()
            after = path.stat()
            if signature != (after.st_size, after.st_mtime_ns) or path.is_symlink():
                continue
        except (FileNotFoundError, OSError):
            continue
        digest = hashlib.sha256(data).hexdigest()
        blob = destination / 'versions' / digest
        blob.parent.mkdir(parents=True, exist_ok=True)
        if not blob.exists():
            blob.write_bytes(data)
        with (destination / 'trajectory.jsonl').open('a') as journal:
            journal.write(json.dumps({'observed_seconds': time.monotonic() - started,
                'path': relative, 'sha256': digest, 'bytes': len(data)}) + '\n')
        seen[relative] = signature


def kill_group(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    # The driver may have exited while its model/tool children are still alive.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def supervise(command, workspace, destination, seconds, env=None):
    destination.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    stopped = threading.Event()
    seen = {}
    capture_errors = []
    log_offset = 0

    def observe():
        nonlocal log_offset
        while not stopped.is_set():
            try:
                capture_files(workspace, destination, seen, started)
                with (destination / 'driver.log').open() as log:
                    log.seek(log_offset)
                    text = log.read()
                    log_offset = log.tell()
                if text:
                    print(text, end='', flush=True)
            except Exception as exc:
                capture_errors.append(str(exc))
            stopped.wait(2)

    observer = threading.Thread(target=observe, daemon=True)
    with (destination / 'driver.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True, env=env)
        observer.start()
        timed_out = False
        try:
            process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            kill_group(process)
            stopped.set()
            observer.join()
    result = {'exit_code': process.returncode, 'timed_out': timed_out,
        'elapsed_seconds': time.monotonic() - started, 'limit_seconds': seconds,
        'capture_errors': capture_errors}
    return result, seen, started


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('harness', choices=['codex', 'cursor', 'antigravity'])
    parser.add_argument('--seconds', type=int, default=75 * 60)
    args = parser.parse_args()
    env = dict(os.environ, BENCH_EXPERIMENT='1', BENCH_SECONDS=str(args.seconds),
        BENCH_OBJECTIVE=Path('/workspace/task.md').read_text())
    result, seen, started = supervise(['python', f'/opt/bench/{args.harness}_goal_check.py'],
        Path('/workspace/output'), CAPTURE, args.seconds, env)
    # Stop the scene process before final collection, including an in-flight render
    # at the deadline. Unsaved memory is deliberately not turned into a checkpoint.
    for entry in Path('/proc').iterdir():
        try:
            if entry.name.isdigit() and (entry / 'comm').read_text().strip() == 'blender':
                os.kill(int(entry.name), signal.SIGSTOP)
        except (OSError, ProcessLookupError):
            pass
    capture_files(Path('/workspace/output'), CAPTURE, seen, started)
    final = CAPTURE / 'artifacts'
    final.mkdir(exist_ok=True)
    for path in Path('/workspace/output').rglob('*'):
        if stat.S_ISREG(path.lstat().st_mode):
            target = final / path.relative_to('/workspace/output')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    prefix = {'codex': 'codex', 'cursor': 'cursor', 'antigravity': 'agy'}[args.harness]
    for name in [f'{prefix}-events.jsonl', f'{prefix}-stderr.log', 'codex-server.log', 'blender.log', 'bench-native-result.json']:
        path = Path('/tmp') / name
        if path.is_file() and not path.is_symlink():
            shutil.copyfile(path, CAPTURE / name)
    native = CAPTURE / 'bench-native-result.json'
    result['native'] = json.loads(native.read_text()) if native.exists() else None
    result['status'] = ('time_limit' if result['timed_out'] else
        'complete' if result['exit_code'] == 0 and result['native'] and result['native']['complete'] else 'stopped')
    result['scene_saved'] = (final / 'scene.blend').is_file()
    result['render_saved'] = (final / 'render.png').is_file()
    (CAPTURE / 'result.json').write_text(json.dumps(result, indent=2))
    with tarfile.open('/tmp/bench-result.tar', 'w') as archive:
        archive.add(CAPTURE, arcname='capture')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
