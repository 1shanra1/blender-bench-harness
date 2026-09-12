"""Pinned official Kimi Code CLI; API credentials come from Modal Secrets."""

import modal
from environment import blender_image

KIMI_VERSION = "0.42.0"
KIMI_SHA256 = "ebb4ef02d85fe0a29dda95a5a60bcd0608a28c1ff331d27e99be54b9d472e33d"
kimi_image = blender_image.run_commands(
    f"curl -fLsS --retry 3 https://code.kimi.com/kimi-code/binaries/{KIMI_VERSION}/kimi-code-linux-x64 -o /usr/local/bin/kimi",
    f"echo '{KIMI_SHA256}  /usr/local/bin/kimi' | sha256sum -c -",
    "chmod +x /usr/local/bin/kimi",
    "kimi --version",
)


def main():
    app = modal.App.lookup("blender-bench-harness", create_if_missing=True)
    with modal.enable_output():
        sandbox = modal.Sandbox.create(app=app, image=kimi_image, timeout=180, block_network=True)
    try:
        process = sandbox.exec("kimi", "--version")
        print(process.stdout.read(), end="")
        process.wait()
        if process.returncode:
            raise RuntimeError(process.stderr.read())
    finally:
        sandbox.terminate()


if __name__ == "__main__":
    main()
