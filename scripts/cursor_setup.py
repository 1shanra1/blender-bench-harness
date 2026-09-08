"""Install the official Cursor CLI in an isolated Modal login sandbox."""
import modal

from environment import ROOT, blender_image

CURSOR_VERSION = "2026.09.02-c22c1a3"
CURSOR_DOMAINS = ["cursor.com", "*.cursor.com", "*.cursor.sh"]
AUTH_SECRET = "blender-bench-cursor-auth"
cursor_image = (
    blender_image.run_commands(
        f"curl -fLsS --retry 3 https://downloads.cursor.com/lab/{CURSOR_VERSION}/linux/x64/agent-cli-package.tar.gz -o /tmp/cursor.tar.gz",
        "mkdir -p /opt/cursor && tar -xzf /tmp/cursor.tar.gz --strip-components=1 -C /opt/cursor && rm /tmp/cursor.tar.gz",
        "ln -s /opt/cursor/cursor-agent /usr/local/bin/cursor-agent",
        "cursor-agent --version",
    )
    .add_local_dir(ROOT / 'runtime', remote_path='/opt/bench')
)


def main():
    app = modal.App.lookup('blender-bench-harness', create_if_missing=True)
    with modal.enable_output():
        sandbox = modal.Sandbox.create(
            app=app, image=cursor_image, timeout=900,
            outbound_domain_allowlist=CURSOR_DOMAINS,
        )
    print('Login sandbox:', sandbox.object_id, flush=True)
    try:
        process = sandbox.exec('sh', '-c', 'NO_OPEN_BROWSER=1 cursor-agent login 2>&1', timeout=840)
        for line in process.stdout:
            print(line, end='', flush=True)
        process.wait()
        if process.returncode:
            raise RuntimeError('Cursor login failed')
        print('Authenticated. Inspecting available models.', flush=True)
        process = sandbox.exec('cursor-agent', 'models')
        print(process.stdout.read(), flush=True)
        print(process.stderr.read(), flush=True)
        auth = sandbox.filesystem.read_bytes('/root/.config/cursor/auth.json').decode()
        modal.Secret.objects.create(AUTH_SECRET, {'CURSOR_AUTH_JSON': auth})
        print('Cursor login saved to Modal Secret:', AUTH_SECRET)
    finally:
        sandbox.terminate()
        print('Login sandbox terminated.')


if __name__ == '__main__':
    main()
