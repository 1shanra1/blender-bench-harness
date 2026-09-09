"""Check Antigravity + Gemini + Blender with one bounded native goal."""
import modal

from antigravity_setup import antigravity_image, AUTH_SECRET, AGY_DOMAINS
from environment import ROOT


def main():
    app = modal.App.lookup('blender-bench-harness', create_if_missing=True)
    with modal.enable_output():
        sandbox = modal.Sandbox.create(
            app=app, image=antigravity_image.add_local_dir(ROOT / "runtime", remote_path="/opt/bench"), timeout=300, cpu=2, memory=4096,
            secrets=[modal.Secret.from_name(AUTH_SECRET)],
            outbound_domain_allowlist=AGY_DOMAINS,
        )
    print('Sandbox:', sandbox.object_id, flush=True)
    output = ROOT / 'outputs' / 'antigravity-smoke'
    output.mkdir(parents=True, exist_ok=True)
    try:
        setup = sandbox.exec('sh', '-c', 'useradd -m blender && mkdir -p /workspace && chmod 777 /workspace')
        setup.wait()
        if setup.returncode:
            raise RuntimeError(setup.stderr.read())
        sandbox.exec(
            'env', '-u', 'AGY_AUTH_TOKEN', 'runuser', '-u', 'blender', '--',
            'xvfb-run', '-a', '-s', '-screen 0 1280x800x24 +extension GLX',
            'sh', '-c',
            'openbox >/tmp/openbox.log 2>&1 & xcompmgr >/tmp/compositor.log 2>&1 & exec blender --factory-startup --online-mode --gpu-backend opengl --python /opt/bench/start_blender.py >/tmp/blender.log 2>&1',
        )
        process = sandbox.exec('python', '/opt/bench/antigravity_goal_check.py', timeout=240)
        for line in process.stdout:
            print(line, end='', flush=True)
        print(process.stderr.read(), end='', flush=True)
        process.wait()
        for remote, filename in [('/tmp/agy-events.jsonl', 'events.jsonl'), ('/tmp/agy-stderr.log', 'stderr.log')]:
            (output / filename).write_bytes(sandbox.filesystem.read_bytes(remote))
        if process.returncode:
            raise RuntimeError(f'Antigravity check failed; logs in {output}')
        (output / 'viewport.png').write_bytes(sandbox.filesystem.read_bytes('/workspace/viewport.png'))
    finally:
        sandbox.terminate()
        print('Sandbox terminated.', flush=True)


if __name__ == '__main__':
    main()
