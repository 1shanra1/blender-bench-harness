"""Recover missing Claude usage from Gateway without changing original run logs."""
import json
from pathlib import Path
import modal

app = modal.App('blender-bench-recover-usage')
volume = modal.Volume.from_name('blender-bench-results')
image = modal.Image.debian_slim().add_local_file(
    Path(__file__).with_name('gateway_accounting.py'), '/opt/bench/gateway_accounting.py')

@app.function(image=image, volumes={'/results': volume}, secrets=[modal.Secret.from_name('blender-bench-vercel-auth')], timeout=600)
def recover():
    import sys, os, hashlib, urllib.request, time
    from concurrent.futures import ThreadPoolExecutor
    sys.path.insert(0, '/opt/bench')
    from gateway_accounting import generation_ids, recovered_usage, FIELDS
    output = {}
    for batch in ['20260912T204833Z-C152B68E', '20260912T204842Z-93B01016', '20260912T061834Z-C4C05134']:
        folder = Path('/results/experiments') / batch / 'claude'
        path = folder / 'capture/claude-events.jsonl'
        raw = path.read_bytes()
        events = []
        for line in raw.splitlines():
            try: events.append(json.loads(line))
            except ValueError: pass
        if any(e.get('type') == 'result' and e.get('modelUsage') for e in events if isinstance(e, dict)):
            raise ValueError('Refusing to replace a native final summary')
        ids = generation_ids(events)
        def lookup(gid):
            for attempt in range(3):
                request = urllib.request.Request('https://ai-gateway.vercel.sh/v1/generation?id=' + gid,
                    headers={'Authorization': 'Bearer ' + os.environ['AI_GATEWAY_API_KEY']})
                try:
                    with urllib.request.urlopen(request, timeout=30) as response: data = json.load(response)['data']
                    if data.get('id') != gid: raise ValueError('Generation identity mismatch')
                    return {'id': gid, **{k: data.get(k) for k in FIELDS}}
                except Exception:
                    if attempt == 2: raise
                    time.sleep(1 + attempt)
        with ThreadPoolExecutor(max_workers=4) as pool:
            records = list(pool.map(lookup, ids))
        usage = recovered_usage(records)
        report = {'schema_version': 1, 'events_sha256': hashlib.sha256(raw).hexdigest(),
                  'discovered_requests': len(ids), 'retrieved_requests': len(records),
                  'usage': usage, 'records': records,
                  'transcript_present': (folder / 'capture/claude-transcript.jsonl').is_file()}
        # Separate evidence sidecar; the captured native logs/results stay intact.
        target = folder / 'gateway-usage-recovery.json'
        target.write_text(json.dumps(report, indent=2))
        volume.commit()
        output[batch] = report
        print(batch, json.dumps(usage), flush=True)
    return output

@app.local_entrypoint()
def main():
    reports = recover.remote()
    destination = Path('outputs/accounting-audit/recovered-claude-usage.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(reports, indent=2))
    print('Saved', destination)
