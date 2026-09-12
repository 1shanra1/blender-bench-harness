"""Small export contract checks; no Modal or model calls."""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from export_results import build_bundle


class ExportTests(unittest.TestCase):
    def test_bundle_contains_only_selected_public_assets_and_preserves_failure(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            batch = root / "experiments/batch-1"
            run = batch / "claude"
            artifacts = run / "capture/artifacts"
            artifacts.mkdir(parents=True)
            reference = b"reference image"
            (batch / "reference.png").write_bytes(reference)
            (batch / "prompt.md").write_text("Reconstruct the object.")
            (batch / "batch.json").write_text(json.dumps({"status": "finished"}))
            (run / "manifest.json").write_text(json.dumps({"model": "test", "reference_sha256": hashlib.sha256(reference).hexdigest()}))
            (run / "result.json").write_text(json.dumps({"status": "time_limit", "elapsed_seconds": 4500}))
            for name in ("render.png", "scene.glb", "scene.blend", "private.log"):
                (artifacts / name).write_bytes(b"saved file")
            output = root / "bundle"
            # Modal mounts the volume through a symlink such as /results.
            mount = root / "mounted-results"
            mount.symlink_to(root, target_is_directory=True)
            data = build_bundle(mount, {"batch-1": "Kettle"}, output, include_models=False)
            experiment = data["experiments"][0]
            self.assertEqual(experiment["name"], "Kettle")
            self.assertNotIn("prompt", experiment)
            self.assertEqual(experiment["runs"][0]["status"], "time_limit")
            self.assertIsNone(experiment["runs"][0]["native_complete"])
            self.assertIsNone(experiment["runs"][0]["model_url"])
            self.assertTrue((output / experiment["reference"]).is_file())
            self.assertEqual(len(list((output / "assets").iterdir())), 2)
            with_models = root / "with-models"
            data = build_bundle(root, {"batch-1": "Kettle"}, with_models)
            self.assertTrue((with_models / data["experiments"][0]["runs"][0]["model_url"]).is_file())
            self.assertFalse(any(p.suffix in {".blend", ".log"} for p in with_models.rglob("*")))

    def test_running_or_missing_batch_is_rejected(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            with self.assertRaisesRegex(ValueError, "not marked finished"):
                build_bundle(root, {"missing": "Kettle"}, root / "bundle")


if __name__ == "__main__":
    unittest.main()
