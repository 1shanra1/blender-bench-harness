"""Pinned official Claude Code CLI image; provider auth comes from Modal Secrets."""

import modal
from environment import blender_image

CLAUDE_VERSION = "2.1.268"
CLAUDE_SHA256 = "9691a2b7bd796712ca8cffb8e32e54ff7fc45b662540233171a16a94a0425653"
claude_image = blender_image.run_commands(
    f"curl -fLsS --retry 3 https://downloads.claude.ai/claude-code-releases/{CLAUDE_VERSION}/linux-x64/claude -o /usr/local/bin/claude",
    f"echo '{CLAUDE_SHA256}  /usr/local/bin/claude' | sha256sum -c -",
    "chmod +x /usr/local/bin/claude",
    "claude --version",
)


def main():
    app = modal.App.lookup("blender-bench-harness", create_if_missing=True)
    with modal.enable_output():
        sandbox = modal.Sandbox.create(app=app, image=claude_image, timeout=180, block_network=True)
    try:
        process = sandbox.exec("claude", "--version")
        print(process.stdout.read(), end="")
        process.wait()
        if process.returncode:
            raise RuntimeError(process.stderr.read())
    finally:
        sandbox.terminate()


if __name__ == "__main__":
    main()
