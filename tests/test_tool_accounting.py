import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from tool_accounting import reported_tool_calls

class ToolAccountingTests(unittest.TestCase):
    def count(self, harness, events):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'events.jsonl'
            path.write_text('\n'.join(json.dumps(e) for e in events) + '\n{partial')
            return reported_tool_calls(path, harness)

    def test_codex_deduplicates_start_completion_and_excludes_messages(self):
        def event(method, kind, id):
            return {'method': method, 'params': {'item': {'type': kind, 'id': id}}}
        self.assertEqual(self.count('codex', [
            event('item/started', 'mcpToolCall', 'one'),
            event('item/completed', 'mcpToolCall', 'one'),
            event('item/started', 'commandExecution', 'two'),
            event('item/completed', 'imageView', 'three'),
            event('item/completed', 'reasoning', 'four'),
        ]), 3)

    def test_claude_counts_calls_not_results_or_repeated_blocks(self):
        call = {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': 'one'}]}}
        self.assertEqual(self.count('claude', [call, call, {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'one'}]}}]), 1)

    def test_kimi_counts_parallel_calls_and_retry_ids(self):
        call = {'role': 'assistant', 'tool_calls': [{'id': 'one'}, {'id': 'two'}]}
        self.assertEqual(self.count('kimi', [call, call, {'role': 'tool', 'tool_call_id': 'one'}, {'role': 'assistant', 'tool_calls': [{'id': 'retry'}]}]), 3)

    def test_missing_or_empty_is_unavailable(self):
        self.assertIsNone(reported_tool_calls(Path('/nonexistent/tool-events.jsonl'), 'codex'))
        self.assertIsNone(self.count('codex', []))

if __name__ == '__main__':
    unittest.main()
