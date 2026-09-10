"""Package only log bytes the remote collector has not received yet."""

import json
import sys
import tarfile
from pathlib import Path


def main():
    prefix, offsets_json = sys.argv[1:]
    offsets = json.loads(offsets_json)
    logs = {
        "driver.log": Path("/tmp/bench-capture/driver.log"),
        **{name: Path("/tmp") / name for name in (
            f"{prefix}-events.jsonl",
            f"{prefix}-events.timestamps.jsonl",
            f"{prefix}-stderr.log",
            "codex-server.log",
            "blender-mcp.log",
            "blender.log",
        )},
    }
    with tarfile.open("/tmp/bench-log-deltas.tar", "w") as archive:
        for name, path in logs.items():
            if not path.is_file() or path.is_symlink():
                continue
            offset = offsets.get(name, 0)
            with path.open("rb") as source:
                size = path.stat().st_size
                if size < offset:
                    raise RuntimeError(f"Log was truncated: {name}")
                if size == offset:
                    continue
                source.seek(offset)
                entry = tarfile.TarInfo(name)
                entry.size = size - offset
                archive.addfile(entry, source)


if __name__ == "__main__":
    main()
