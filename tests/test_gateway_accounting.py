"""Recovery must not double-count streams or silently invent missing usage."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from gateway_accounting import generation_ids, recovered_usage
from frontend_data import gateway_usage_fallback

class GatewayAccountingTests(unittest.TestCase):
    def record(self, gid='gen_one'):
        return dict(id=gid, tokens_prompt=10, tokens_completion=20,
                    native_tokens_reasoning=30, native_tokens_cached=40,
                    native_tokens_cache_creation=50)

    def test_stream_duplicates_and_user_content_are_not_requests(self):
        event = {'type': 'assistant', 'message': {'id': 'gen_one'}}
        self.assertEqual(generation_ids([event, event, {'type':'user','message':{'id':'gen_fake'}}]), ['gen_one'])

    def test_all_components_once_and_partial_coverage_explicit(self):
        usage = recovered_usage([self.record()])
        self.assertEqual(usage['tokens'], 150)
        self.assertEqual(usage['cached_tokens'], 40)
        self.assertEqual(usage['coverage'], 'recorded_requests')
        with self.assertRaises(ValueError):
            recovered_usage([self.record(), self.record()])
        for bad in [None, -1, float('nan'), True, 0.5]:
            with self.assertRaises(ValueError):
                recovered_usage([{**self.record(), 'tokens_prompt': bad}])

    def test_recovery_requires_matching_log_and_every_discovered_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            events = root / 'events.jsonl'
            events.write_text(json.dumps({'type':'assistant','message':{'id':'gen_one'}})+'\n')
            report = {'schema_version':1, 'events_sha256':hashlib.sha256(events.read_bytes()).hexdigest(),
                      'records':[self.record()], 'usage': {'tokens': 999999}}
            sidecar = root/'gateway-usage-recovery.json'
            sidecar.write_text(json.dumps(report))
            self.assertEqual(gateway_usage_fallback(root, events)['tokens'],150)
            report['records'] = [self.record('gen_wrong')]
            sidecar.write_text(json.dumps(report))
            self.assertIsNone(gateway_usage_fallback(root, events))
            report['records'] = [self.record()]
            sidecar.write_text(json.dumps(report))
            events.write_text(events.read_text()+'{}\n')
            self.assertIsNone(gateway_usage_fallback(root, events))

if __name__ == '__main__': unittest.main()
