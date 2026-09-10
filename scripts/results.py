"""Inspect saved Modal results; download only a file you explicitly select."""

import argparse
import json
from pathlib import Path, PurePosixPath

import modal
from remote_experiment import VOLUME_NAME


def read_json(volume, path):
    try:
        return json.loads(b"".join(volume.read_file(path)))
    except FileNotFoundError:
        return None


def status(volume, batch):
    summary = read_json(volume, f"{batch}/batch.json")
    if summary is None:
        raise FileNotFoundError(f"No saved batch summary at {batch}")
    runs = {}
    for harness in summary["harnesses"]:
        outcome = summary["results"].get(harness)
        if outcome is None:
            outcome = read_json(volume, f"{batch}/{harness}/result.json")
        run = {"saved_result": outcome}
        manifest = read_json(volume, f"{batch}/{harness}/manifest.json")
        if manifest:
            run["sandbox_id"] = manifest["sandbox_id"]
            if harness not in summary["results"]:
                try:
                    sandbox = modal.Sandbox.from_id(manifest["sandbox_id"])
                    code = sandbox.poll()
                    run["sandbox"] = "running" if code is None else "exited"
                    run["sandbox_exit_code"] = code
                except modal.exception.NotFoundError:
                    run["sandbox"] = "no longer available"
        else:
            run["sandbox"] = "not recorded yet"
        runs[harness] = run
    print(json.dumps({
        "batch": batch,
        "last_saved_controller_status": summary["status"],
        "runs": runs,
    }, indent=2))


def relative_path(value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise argparse.ArgumentTypeError("Use a relative path inside the results volume")
    return str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    show = commands.add_parser("status", help="Show saved outcomes and live sandbox state")
    show.add_argument("batch", type=relative_path, help="Batch ID")
    files = commands.add_parser("files", help="List a volume directory without downloading files")
    files.add_argument("path", nargs="?", type=relative_path, default="experiments")
    get = commands.add_parser("get", help="Download one file to an explicit destination")
    get.add_argument("path", type=relative_path, help="File path from the files command")
    get.add_argument("destination", type=Path)
    args = parser.parse_args()
    volume = modal.Volume.from_name(VOLUME_NAME)
    if args.command == "status":
        status(volume, f"experiments/{args.batch}")
    elif args.command == "files":
        for entry in volume.listdir(args.path, recursive=False):
            print(f"{entry.type.name:10} {entry.size:12,d} bytes  {entry.path}")
    else:
        # Exclusive creation protects an existing local file from replacement.
        with args.destination.open("xb") as output:
            try:
                for chunk in volume.read_file(args.path):
                    output.write(chunk)
            except Exception:
                args.destination.unlink()
                raise
        print(f"Saved {args.destination.resolve()}")


if __name__ == "__main__":
    main()
