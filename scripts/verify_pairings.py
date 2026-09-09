"""Small compatibility checks only. Does not run the reconstruction prompt."""
import argparse
import json
import hashlib
from datetime import datetime, timezone

from typing import NamedTuple, Sequence

import modal
from environment import ROOT
from codex_setup import codex_image, CODEX_VERSION
from cursor_setup import cursor_image, CURSOR_DOMAINS, CURSOR_VERSION
from antigravity_setup import antigravity_image, AGY_VERSION, AGY_DOMAINS
from shared_sandbox import create_sandbox, prepare_workspace, start_blender


class HarnessPairing(NamedTuple):
    image: modal.Image
    secret: str
    domains: Sequence[str]
    model: str
    log_prefix: str


PAIRINGS: dict[str, HarnessPairing] = {
    'codex': HarnessPairing(codex_image, 'blender-bench-vercel-auth', ['ai-gateway.vercel.sh'], 'google/gemini-3.8-flash', 'codex'),
    'cursor': HarnessPairing(cursor_image, 'blender-bench-cursor-auth', CURSOR_DOMAINS, 'gemini-3.8-flash-high', 'cursor'),
    'antigravity': HarnessPairing(antigravity_image, 'blender-bench-antigravity-auth', AGY_DOMAINS, 'gemini-3.8-flash-high', 'agy'),
}
OBJECTIVE = """This is a compatibility check, not a modeling task. Open /workspace/references/reference-01.png and identify the pictured object in one sentence. Use Blender MCP to inspect the default scene and save a viewport preview at /workspace/viewport.png. Open that PNG and briefly describe what you see. Preserve scene geometry. Direct screenshots are black on this display; bpy.ops.render.opengl(write_still=True, view_context=True) with a VIEW_3D area and WINDOW region override works. Use only Blender MCP and image reading, no shell commands, web access, downloads, or subagents. Complete the goal once both images have been inspected and the scene described."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('harness', choices=PAIRINGS)
    parser.add_argument('--codex-provider', choices=['vercel', 'openrouter'], default=None)
    args = parser.parse_args()
    name = args.harness
    if args.codex_provider and name != 'codex':
        parser.error('--codex-provider only applies to Codex')
    # This CLI account's catalog must list the exact model before any paid call.
    if name == 'cursor':
        catalog = (ROOT / 'outputs/pairing-verification/cursor-models.txt').read_text()
        if 'gemini-3.8-flash-high - ' not in catalog:
            raise RuntimeError('Gemini 3.8 Flash High is absent from the verified Cursor catalog; no substitution')
    pairing = PAIRINGS[name]
    image, secret, domains, model, prefix = (
        pairing.image,
        pairing.secret,
        pairing.domains,
        pairing.model,
        pairing.log_prefix,
    )
    provider = (args.codex_provider or 'vercel') if name == 'codex' else name
    if name == 'codex' and provider == 'openrouter':
        secret, domains = 'blender-bench-openrouter-auth', ['openrouter.ai']
    output = ROOT / 'outputs/pairing-verification' / (name + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(parents=True)
    sandbox = create_sandbox(image, secret, domains, timeout=300)
    print('Sandbox:', sandbox.object_id, flush=True)
    try:
        manifest = prepare_workspace(sandbox)
        manifest.update(harness=name, provider=provider, model=model, reasoning_effort='high', sandbox_id=sandbox.object_id,
                        harness_version={'codex': CODEX_VERSION, 'cursor': CURSOR_VERSION, 'antigravity': AGY_VERSION}[name],
                        verification_objective_sha256=hashlib.sha256(OBJECTIVE.encode()).hexdigest())
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        start_blender(sandbox)
        process = sandbox.exec('python', f'/opt/bench/{name}_goal_check.py',
            env={'BENCH_MODEL': model, 'BENCH_OBJECTIVE': OBJECTIVE}, timeout=240)
        for line in process.stdout:
            print(line, end='', flush=True)
        print(process.stderr.read(), flush=True)
        process.wait()
        for remote, target in [(f'/tmp/{prefix}-events.jsonl', 'events.jsonl'),
                               (f'/tmp/{prefix}-' + ('server.log' if name == 'codex' else 'stderr.log'), 'stderr.log'),
                               ('/tmp/blender.log', 'blender.log')]:
            (output / target).write_bytes(sandbox.filesystem.read_bytes(remote))
        if process.returncode:
            raise RuntimeError(f'Compatibility check failed; logs: {output}')
        (output / 'viewport.png').write_bytes(sandbox.filesystem.read_bytes('/workspace/viewport.png'))
        print('Check completed. Evidence:', output)
    finally:
        sandbox.terminate()
        print('Sandbox terminated.', flush=True)


if __name__ == '__main__':
    main()
