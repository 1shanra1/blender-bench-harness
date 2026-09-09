"""Pinned official Antigravity CLI image for isolated Modal runs."""
import argparse
import sys
import threading
import modal
from environment import blender_image

AGY_VERSION = '1.1.27'
AUTH_SECRET = 'blender-bench-antigravity-auth'
AGY_DOMAINS = ['antigravity.google', 'oauth2.googleapis.com', 'www.googleapis.com',
               'cloudcode-pa.googleapis.com', 'daily-cloudcode-pa.googleapis.com',
               'play.googleapis.com', 'lh3.googleusercontent.com']
AGY_URL = 'https://storage.googleapis.com/antigravity-public/antigravity-cli/1.1.27-5211191891591168/linux-x64/cli_linux_x64.tar.gz'
AGY_SHA512 = '793d4b9ea2c08d9a7e50bafa02cfc8c19424bd60d6e83f91408d45f9c6d4ce79a5d576fede5bef164d823abf84f81359a14b4ca665952c47b0a7cfd743bb69c0'
antigravity_image = blender_image.run_commands(
    f'curl -fLsS --retry 3 {AGY_URL} -o /tmp/agy.tar.gz',
    f"echo '{AGY_SHA512}  /tmp/agy.tar.gz' | sha512sum -c -",
    'mkdir -p /opt/antigravity && tar -xzf /tmp/agy.tar.gz -C /opt/antigravity && rm /tmp/agy.tar.gz',
    'ln -s /opt/antigravity/antigravity /usr/local/bin/agy',
    'agy --version',
)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--login', action='store_true')
    args = parser.parse_args()
    app = modal.App.lookup('blender-bench-harness', create_if_missing=True)
    with modal.enable_output():
        sandbox = modal.Sandbox.create(app=app, image=antigravity_image,
                                       timeout=900 if args.login else 180,
                                       block_network=not args.login)
    try:
        if args.login:
            print('Complete Google login and onboarding, then enter /exit. No task prompt is needed.', flush=True)
            process = sandbox.exec('agy', pty=True,
                                   env={'SSH_CONNECTION': 'remote', 'TERM': 'xterm-256color'}, timeout=840)
            def forward_input():
                for line in sys.stdin:
                    process.stdin.write(line.rstrip('\n') + '\r')
                    process.stdin.drain()
            threading.Thread(target=forward_input, daemon=True).start()
        else:
            process = sandbox.exec('agy', '--help')
        for line in process.stdout:
            print(line, end='', flush=True)
        process.wait()
        if args.login:
            token = sandbox.filesystem.read_bytes('/root/.gemini/antigravity-cli/antigravity-oauth-token').decode()
            modal.Secret.objects.create('blender-bench-antigravity-auth', {'AGY_AUTH_TOKEN': token})
            print('Credentials saved to Modal Secret; no conversation state copied.')
        elif process.returncode:
            raise RuntimeError('Antigravity CLI installation check failed')
    finally:
        sandbox.terminate()


if __name__ == '__main__':
    main()
