"""Export selected batches on Modal, then download only the website bundle."""

import argparse
import json
import shutil
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from frontend_data import LocalArchive, read_json
from render_evolution import export_evolution


def build_bundle(root, batches, destination, include_models=True):
    """Read mounted results and copy only assets referenced by the public JSON."""
    root = root.resolve()
    experiments = root / "experiments"
    for batch_id in batches:
        if not batch_id or Path(batch_id).name != batch_id or batch_id in {".", ".."}:
            raise ValueError("Use batch IDs, not paths")
        summary = read_json(experiments / batch_id / "batch.json", root)
        if summary.get("status") != "finished":
            raise ValueError(f"Batch {batch_id} is not marked finished")

    archive = LocalArchive(root, experiments_root=experiments)
    catalogue = archive.catalogue(batch_ids=batches)
    if {item["id"] for item in catalogue["experiments"]} != set(batches):
        raise ValueError("A selected batch has no readable run manifests")
    destination.mkdir(parents=True, exist_ok=True)
    assets = destination / "assets"
    assets.mkdir()

    def copy_asset(url):
        if url is None:
            return None
        source = archive.asset_path(url.rsplit("/", 1)[-1])
        if source is None:
            raise FileNotFoundError(url)
        # Only GLB is self-contained; loose glTF may reference unexported files.
        if source.suffix.lower() in {".glb", ".gltf"}:
            if not include_models or source.suffix.lower() != ".glb":
                return None
        filename = url.rsplit("/", 1)[-1] + source.suffix.lower()
        shutil.copyfile(source, assets / filename)
        return "assets/" + filename

    for experiment in catalogue["experiments"]:
        experiment["name"] = batches[experiment["id"]]
        experiment["reference"] = copy_asset(experiment["reference"])
        for run in experiment["runs"]:
            run["evolution"] = export_evolution(experiments / experiment["id"] / run["id"], assets)
            run["render"] = copy_asset(run["render"])
            run["model_url"] = copy_asset(run["model_url"])
            run["views"] = {view: copy_asset(url) for view, url in run["views"].items()}
    (destination / "results.json").write_text(json.dumps(catalogue, indent=2) + "\n")
    return catalogue


def batch_selection(value):
    batch_id, separator, name = value.partition("=")
    if not separator or not name.strip() or Path(batch_id).name != batch_id or batch_id in {"", ".", ".."}:
        raise argparse.ArgumentTypeError("Use BATCH_ID=Display name")
    return batch_id, name.strip()


def main():
    import modal
    from remote_experiment import APP_NAME, VOLUME_NAME

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", nargs="+", type=batch_selection, metavar="BATCH_ID=NAME")
    parser.add_argument("--images-only", action="store_true", help="Skip interactive GLB models")
    args = parser.parse_args()
    batches = dict(args.batches)
    if len(batches) != len(args.batches):
        parser.error("Select each batch once")
    export = modal.Function.from_name(APP_NAME, "export_results")
    bundle = export.remote(batches, not args.images_only)
    print(f"Modal export: {bundle['path']} ({bundle['bytes']:,} bytes)", flush=True)

    public = Path(__file__).resolve().parents[1] / "frontend/public"
    public.mkdir(exist_ok=True)
    destination = public / "data"
    if destination.exists() and not (destination / "results.json").is_file():
        raise RuntimeError(f"Refusing to replace a directory without an exported results.json: {destination}")
    volume = modal.Volume.from_name(VOLUME_NAME)
    with TemporaryDirectory(dir=public) as temporary:
        temporary = Path(temporary)
        archive = temporary / "bundle.tar.gz"
        with archive.open("wb") as output:
            for chunk in volume.read_file(bundle["path"]):
                output.write(chunk)
        staged = temporary / "data"
        with tarfile.open(archive) as source:
            source.extractall(staged, filter="data")
        json.loads((staged / "results.json").read_text())
        if destination.exists():
            shutil.rmtree(destination)
        staged.rename(destination)
    print(f"Website data saved to {destination}. Run npm run dev in frontend to preview.")


if __name__ == "__main__":
    main()
