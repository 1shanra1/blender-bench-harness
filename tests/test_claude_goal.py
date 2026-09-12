"""Check native completion evidence without calling a model."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from claude_goal_check import goal_completed, goal_verdict


class ClaudeGoalTests(unittest.TestCase):
    def test_successful_exit_does_not_prove_goal_completion(self):
        self.assertFalse(goal_completed(None, {"subtype": "success"}))

    def test_only_evaluator_achievement_counts(self):
        for verdict, expected in [
            ({"met": True}, True),
            ({"met": False}, False),
            ({"met": True, "sentinel": True}, False),
            ({"met": True, "failed": True}, False),
        ]:
            self.assertEqual(goal_completed(verdict, {"subtype": "success"}), expected)
        self.assertFalse(goal_completed({"met": True}, {"subtype": "error_during_execution", "is_error": True}))
        # The CLI can label an API error as subtype=success; is_error wins.
        self.assertFalse(goal_completed({"met": True}, {"subtype": "success", "is_error": True}))

    def test_reads_matching_native_attachment_not_assistant_claim(self):
        transcript = "\n".join(json.dumps(event) for event in [
            {"type": "assistant", "message": {"content": "Goal achieved"}},
            {"type": "attachment", "attachment": {"type": "goal_status", "condition": "other", "met": True}},
            {"type": "attachment", "attachment": {"type": "goal_status", "condition": "inspect", "met": True, "reason": "Both images inspected"}},
        ])
        verdict = goal_verdict(transcript, "inspect")
        self.assertEqual(verdict["reason"], "Both images inspected")
        self.assertEqual(goal_verdict(transcript, "inspect\n"), verdict)
        self.assertIsNone(goal_verdict(transcript, "missing"))


if __name__ == "__main__":
    unittest.main()
