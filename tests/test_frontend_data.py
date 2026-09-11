"""Contract checks for the local frontend; no Modal or provider calls."""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from frontend_data import LocalArchive, is_local_file, reported_usage


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.reference = self.root / "references/drill/reference.png"
        self.reference.parent.mkdir(parents=True)
        self.reference.write_bytes(b"saved drill reference")
        self.digest = hashlib.sha256(self.reference.read_bytes()).hexdigest()
        self.archive = LocalArchive(self.root)

    def run_folder(self, harness="codex", reference_hash="default", result=None):
        folder = self.root / "outputs/experiments/20260909-test" / harness
        folder.mkdir(parents=True)
        manifest = {"model": "test-model", "reference_sha256": self.digest if reference_hash == "default" else reference_hash, "experiment_seconds": 2700}
        (folder / "manifest.json").write_text(json.dumps(manifest))
        (folder / "result.json").write_text(json.dumps(result or {"status": "complete", "native": {"complete": True}, "elapsed_seconds": 600}))
        return folder

    def test_matches_original_reference_despite_newer_subject(self):
        self.run_folder()
        kettle = self.root / "references/kettle/current.png"
        kettle.parent.mkdir()
        kettle.write_bytes(b"new global reference")
        experiment = self.archive.catalogue()["experiments"][0]
        self.assertEqual(experiment["name"], "Cordless drill")
        self.assertEqual(self.archive.image_path(experiment["reference"].split("/")[-1]), self.reference)

    def test_disagreeing_or_unknown_reference_is_not_shared(self):
        self.run_folder("codex")
        self.run_folder("cursor", reference_hash=None)
        self.assertIsNone(self.archive.catalogue()["experiments"][0]["reference"])
        manifest = self.root / "outputs/experiments/20260909-test/cursor/manifest.json"
        manifest.write_text(json.dumps({"model": "test-model", "reference_sha256": "different"}))
        self.assertIsNone(self.archive.catalogue()["experiments"][0]["reference"])

    def test_no_checkpoint_promoted_to_missing_final_render(self):
        folder = self.run_folder(result={"status": "execution_failed"})
        checkpoint = folder / "capture/checkpoints/last/render.png"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_bytes(b"old render")
        run = self.archive.catalogue()["experiments"][0]["runs"][0]
        self.assertIsNone(run["render"])
        self.assertIsNone(run["elapsed_seconds"])
        self.assertIsNone(run["native_complete"])
        self.assertIsNone(run["cost_usd"])
        self.assertTrue(all(value is None for value in run["views"].values()))

    def test_timeout_retains_final_artifact_without_claiming_completion(self):
        folder = self.run_folder(result={"status": "time_limit", "elapsed_seconds": 2700})
        image = folder / "capture/artifacts/render.png"
        image.parent.mkdir(parents=True)
        image.write_bytes(b"saved final render")
        run = self.archive.catalogue()["experiments"][0]["runs"][0]
        self.assertIsNotNone(run["render"])
        self.assertEqual(run["status"], "time_limit")
        self.assertIsNone(run["native_complete"])

    def test_symlinked_asset_and_parent_are_rejected(self):
        folder = self.run_folder()
        image = folder / "capture/artifacts/render.png"
        image.parent.mkdir(parents=True)
        image.symlink_to(self.reference)
        self.assertIsNone(self.archive.catalogue()["experiments"][0]["runs"][0]["render"])
        image.unlink()
        image.write_bytes(b"real final render")
        data = self.archive.catalogue()
        key = data["experiments"][0]["runs"][0]["render"].split("/")[-1]
        image.unlink()
        image.symlink_to(self.reference)
        self.assertIsNone(self.archive.image_path(key))
        alias = self.root / "alias"
        alias.symlink_to(self.reference.parent, target_is_directory=True)
        self.assertFalse(is_local_file(alias / self.reference.name, alias))

    def test_asset_keys_do_not_accept_paths(self):
        self.run_folder()
        self.archive.catalogue()
        self.assertIsNone(self.archive.image_path("../../credentials/secret.json"))
        self.assertFalse(is_local_file(self.root / "references/../outside.txt", self.root / "references"))

    def test_empty_or_partial_archive(self):
        self.assertEqual(self.archive.catalogue(), {"experiments": []})
        folder = self.run_folder()
        (folder / "manifest.json").write_text('{"unfinished":')
        self.assertEqual(self.archive.catalogue(), {"experiments": []})


class UsageTests(unittest.TestCase):
    def parse(self, harness, events):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            path.write_text("\n".join(json.dumps(event) for event in events) + '\n{"partial":')
            return reported_usage(path, harness)

    def test_codex_uses_latest_cumulative_summary_not_sum(self):
        events = [{"method": "thread/tokenUsage/updated", "params": {"tokenUsage": {"total": {"totalTokens": tokens, "cachedInputTokens": 25}}}} for tokens in [100, 400, None]]
        result = self.parse("codex", events)
        self.assertEqual(result["tokens"], 400)
        self.assertEqual(result["cached_tokens"], 25)
        self.assertEqual(result["basis"], "Includes cached input")

    def test_cursor_uses_result_and_keeps_cache_separate(self):
        result = self.parse("cursor", [{"type": "step", "usage": {"inputTokens": 500}}, {"type": "result", "usage": {"inputTokens": 90, "outputTokens": 10, "cacheReadTokens": 1000}}])
        self.assertEqual(result["tokens"], 100)
        self.assertEqual(result["cached_tokens"], 1000)

    def test_antigravity_requires_final_usage(self):
        step = {"step_update": {"usage": {"total_tokens": 100}}}
        self.assertIsNone(self.parse("antigravity", [step]))
        result = self.parse("antigravity", [step, {"result": {"usage": {"total_tokens": 300, "cache_read_tokens": 2000}}}])
        self.assertEqual(result["tokens"], 300)
        self.assertEqual(result["cached_tokens"], 2000)

    def test_invalid_numeric_counts_stay_missing(self):
        for bad in [-10, "100", True, float("inf")]:
            self.assertIsNone(self.parse("antigravity", [{"result": {"usage": {"total_tokens": bad}}}]))


if __name__ == "__main__":
    unittest.main()
