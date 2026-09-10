"""Copy logs and saved versions to the controller's storage, without agent feedback."""

import hashlib
import json
import shutil
import tarfile
import threading
from datetime import datetime, timezone
from pathlib import Path

from modal.exception import SandboxFilesystemNotFoundError

# Independent of the supervisor's two-second file sampling. This bounds the
# usual collection lag without making network requests on every tool call.
COLLECTION_SECONDS = 120


class LiveCollector:
    def __init__(self, sandbox, folder, harness, commit):
        self.sandbox = sandbox
        self.folder = folder
        self.capture = folder / "capture"
        self.capture.mkdir(exist_ok=True)
        self.prefix = "agy" if harness == "antigravity" else harness
        self.commit = commit
        self.errors = 0
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.observe, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopped.set()
        self.thread.join()
        self.collect_safely()

    def observe(self):
        while not self.stopped.is_set():
            self.collect_safely()
            self.stopped.wait(COLLECTION_SECONDS)

    def collect_safely(self):
        try:
            self.collect_logs()
            self.collect_versions(Path("."))
            self.collect_versions(Path("scripts"))
        except Exception as exc:
            self.report_error(exc)
        # Preserve partial progress even if another file could not be copied.
        try:
            self.commit()
        except Exception as exc:
            self.report_error(exc)

    def report_error(self, exc):
        self.errors += 1
        error = {"at": datetime.now(timezone.utc).isoformat(), "error": str(exc)}
        with (self.folder / "collection-errors.jsonl").open("a") as log:
            log.write(json.dumps(error) + "\n")
        print(f"[{self.folder.name}] Live collection failed: {exc}", flush=True)

    def collect_logs(self):
        offsets = {
            path.name: path.stat().st_size
            for path in self.capture.iterdir()
            if path.suffix in {".log", ".jsonl"} and path.name != "trajectory.jsonl"
        }
        process = self.sandbox.exec(
            "python", "/opt/bench/collect_log_deltas.py", self.prefix,
            json.dumps(offsets), timeout=60,
        )
        process.wait()
        if process.returncode:
            raise RuntimeError(process.stderr.read())
        archive_path = self.folder / "log-deltas.tar"
        self.sandbox.filesystem.copy_to_local("/tmp/bench-log-deltas.tar", archive_path)
        with tarfile.open(archive_path) as archive:
            for entry in archive:
                if not entry.isfile() or Path(entry.name).name != entry.name:
                    raise ValueError("Expected a log filename in the delta archive")
                with archive.extractfile(entry) as source:
                    with (self.capture / entry.name).open("ab") as destination:
                        shutil.copyfileobj(source, destination)
        archive_path.unlink()

    def collect_versions(self, relative):
        remote = Path("/tmp/bench-capture") / relative
        destination = self.capture / relative
        journal = destination / "trajectory.jsonl"
        offset = journal.stat().st_size if journal.exists() else 0
        try:
            # Journals contain only small metadata rows; the large blobs use
            # streaming file transfers below, never read_bytes().
            data = self.sandbox.filesystem.read_bytes(str(remote / "trajectory.jsonl"))
        except SandboxFilesystemNotFoundError:
            return  # No saved versions yet.
        destination.mkdir(parents=True, exist_ok=True)
        for line in data[offset:].splitlines(keepends=True):
            if not line.endswith(b"\n"):
                break  # The supervisor is still writing this row.
            record = json.loads(line)
            digest = record["sha256"]
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("Invalid checkpoint hash")
            blob = destination / "versions" / digest
            if not blob.exists():
                blob.parent.mkdir(exist_ok=True)
                partial = blob.with_suffix(".partial")
                self.sandbox.filesystem.copy_to_local(str(remote / "versions" / digest), partial)
                with partial.open("rb") as source:
                    if hashlib.file_digest(source, "sha256").hexdigest() != digest:
                        raise ValueError("Checkpoint transfer hash mismatch")
                partial.replace(blob)
            # Publish the journal row only after its saved version is present.
            with journal.open("ab") as output:
                output.write(line)
