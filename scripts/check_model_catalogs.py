"""Refresh model availability without submitting model prompts."""
import argparse

import modal
from environment import ROOT
from cursor_setup import cursor_image, CURSOR_DOMAINS
from antigravity_setup import antigravity_image, AGY_DOMAINS
from shared_sandbox import create_sandbox

CATALOGS = {
    'cursor': (cursor_image, 'blender-bench-cursor-auth', CURSOR_DOMAINS,
        "import os,pathlib,subprocess; p=pathlib.Path('/root/.config/cursor/auth.json'); "
        "p.parent.mkdir(parents=True,exist_ok=True); p.write_text(os.environ.pop('CURSOR_AUTH_JSON')); "
        "p.chmod(0o600); subprocess.run(['cursor-agent','models'],check=True)"),
    'antigravity': (antigravity_image, 'blender-bench-antigravity-auth', AGY_DOMAINS,
        "import os,pathlib,subprocess; p=pathlib.Path('/root/.gemini/antigravity-cli/antigravity-oauth-token'); "
        "p.parent.mkdir(parents=True,exist_ok=True); p.write_text(os.environ.pop('AGY_AUTH_TOKEN')); "
        "p.chmod(0o600); subprocess.run(['agy','models'],check=True)"),
    'openrouter': (modal.Image.debian_slim(python_version='3.12'), 'blender-bench-openrouter-auth', ['openrouter.ai'],
        "import os,json,urllib.request; r=urllib.request.Request('https://openrouter.ai/api/v1/models', "
        "headers={'Authorization':'Bearer '+os.environ['OPENROUTER_API_KEY']}); "
        "d=json.load(urllib.request.urlopen(r)); "
        "print(json.dumps([m for m in d['data'] if m['id']=='google/gemini-3.8-flash'],indent=2))"),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('provider', choices=CATALOGS)
    args = parser.parse_args()
    image, secret, domains, code = CATALOGS[args.provider]
    sandbox = create_sandbox(image, secret, domains, timeout=120)
    try:
        process = sandbox.exec('python', '-c', code, timeout=90)
        out, err = process.stdout.read(), process.stderr.read()
        process.wait()
        if process.returncode:
            raise RuntimeError(err)
        folder = ROOT / 'outputs/pairing-verification'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{args.provider}-models.txt'
        path.write_text(out)
        print('\n'.join(line for line in out.splitlines() if 'gemini' in line.lower()))
        print('Full catalog:', path)
    finally:
        sandbox.terminate()


if __name__ == '__main__':
    main()
