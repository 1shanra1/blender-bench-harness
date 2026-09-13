"""Contract checks for the local frontend; no Modal or provider calls."""
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from frontend_data import LocalArchive, is_local_file, reported_usage, presentation_asset, presentation_result


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

    def test_rebuild_is_explicit_and_preserves_original_run_status(self):
        folder = self.run_folder(result={"status": "time_limit", "elapsed_seconds": 5400})
        rebuilt = folder / "recovery-rebuild"
        rebuilt.mkdir()
        image = rebuilt / "rebuilt-render.png"
        image.write_bytes(b"rebuilt render")
        self.assertFalse(presentation_asset(folder, "render.png").exists())
        (rebuilt / "recovery.json").write_text(json.dumps({"kind": "post-run script rebuild"}))
        run = self.archive.catalogue()["experiments"][0]["runs"][0]
        self.assertIsNotNone(run["render"])
        self.assertEqual(run["status"], "time_limit")
        original = folder / "capture/artifacts/render.png"
        original.parent.mkdir(parents=True)
        original.write_bytes(b"original render")
        self.assertEqual(presentation_asset(folder, "render.png"), original)

    def test_recovered_completion_requires_recorded_supervisor_verdict(self):
        failure = {"status": "execution_failed", "error": "collection failed"}
        folder = self.run_folder(result=failure)
        (folder / "recovery.json").write_text(json.dumps({"blend_validation": ["verified"]}))
        (folder / "supervisor.log").write_text('{"type":"goal.summary","status":"complete"}\n')
        self.assertEqual(presentation_result(folder, failure), failure)
        verdict = {"status": "complete", "native": {"complete": True}, "limit_seconds": 5400,
                   "elapsed_seconds": 675, "scene_saved": True, "render_saved": True}
        with (folder / "supervisor.log").open("a") as log:
            log.write(json.dumps(verdict) + "\n")
        self.assertEqual(presentation_result(folder, failure)["elapsed_seconds"], 675)
        self.assertEqual(json.loads((folder / "result.json").read_text()), failure)

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

    def test_indexes_glb_model(self):
        folder = self.run_folder()
        glb = folder / "evaluation/scene.glb"
        glb.parent.mkdir(parents=True, exist_ok=True)
        glb.write_bytes(b"test glb binary data")
        run = self.archive.catalogue()["experiments"][0]["runs"][0]
        self.assertTrue(run["model_url"].startswith("/api/models/"))
        key = run["model_url"].split("/")[-1]
        self.assertEqual(self.archive.asset_path(key), glb)

    def test_claude_code_is_included_in_results(self):
        self.run_folder("claude")
        run = self.archive.catalogue()["experiments"][0]["runs"][0]
        self.assertEqual(run["id"], "claude")
        self.assertEqual(run["name"], "Claude Code")
        self.assertTrue(run["native_complete"])

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

    def test_claude_includes_goal_evaluator_without_double_counting_messages(self):
        result = self.parse("claude", [
            {"type": "assistant", "message": {"usage": {"input_tokens": 50, "output_tokens": 20}}},
            {"type": "result",
             "usage": {"input_tokens": 90, "output_tokens": 30},
             "modelUsage": {"selected-model": {"inputTokens": 100, "outputTokens": 40, "cacheReadInputTokens": 1000, "cacheCreationInputTokens": 200}}},
        ])
        self.assertEqual(result["tokens"], 1340)
        self.assertEqual(result["cached_tokens"], 1000)
        self.assertIn("including goal evaluation", result["source"])

    def test_kimi_sums_requests_but_ignores_step_end_copies(self):
        usage = {"inputOther": 10, "output": 5, "inputCacheRead": 100, "inputCacheCreation": 20}
        result = self.parse("kimi", [
            {"type": "usage.record", "usage": usage},
            {"type": "context.append_loop_event", "event": {"type": "step.end", "usage": usage}},
            {"type": "usage.record", "usage": usage},
        ])
        self.assertEqual(result["tokens"], 270)
        self.assertEqual(result["cached_tokens"], 200)

    def test_claude_without_final_summary_stays_missing(self):
        message = {"id": "same", "usage": {"input_tokens": 0, "output_tokens": 0}}
        self.assertIsNone(self.parse("claude", [{"type": "assistant", "message": message}]))

    def test_invalid_numeric_counts_stay_missing(self):
        for bad in [-10, "100", True, float("inf")]:
            self.assertIsNone(self.parse("antigravity", [{"result": {"usage": {"total_tokens": bad}}}]))


if __name__ == "__main__":
    unittest.main()
