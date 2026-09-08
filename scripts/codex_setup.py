"""Install Codex remotely and save a device login as a Modal Secret."""
import modal

from environment import ROOT, blender_image

CODEX_VERSION = "0.153.4"
CODEX_SHA256 = "f479424eca092484dc40d87ae28c44f4cc40234a60045d6131e493800d814a30"
AUTH_SECRET = "blender-bench-codex-auth"
CODEX_DOMAINS = ["auth.openai.com", "chatgpt.com", "api.openai.com"]

codex_image = (
    blender_image.run_commands(
        f"curl -fLsS --retry 3 https://github.com/openai/codex/releases/download/rust-v{CODEX_VERSION}/codex-x86_64-unknown-linux-musl.tar.gz -o /tmp/codex.tar.gz",
        f"echo '{CODEX_SHA256}  /tmp/codex.tar.gz' | sha256sum -c -",
        "tar -xzf /tmp/codex.tar.gz -C /usr/local/bin && mv /usr/local/bin/codex-x86_64-unknown-linux-musl /usr/local/bin/codex && rm /tmp/codex.tar.gz",
        "codex --version",
    )
    .run_commands(
        f"curl -fLsS --retry 3 https://github.com/openai/codex/releases/download/rust-v{CODEX_VERSION}/codex-code-mode-host-x86_64-unknown-linux-musl.tar.gz -o /tmp/codex-host.tar.gz",
        "echo 'f95830a869590957664bbfc67bccb08773806b693670baf15908176f89b4cd31  /tmp/codex-host.tar.gz' | sha256sum -c -",
        "tar -xzf /tmp/codex-host.tar.gz -C /usr/local/bin && mv /usr/local/bin/codex-code-mode-host-x86_64-unknown-linux-musl /usr/local/bin/codex-code-mode-host && rm /tmp/codex-host.tar.gz",
    )
    .add_local_dir(ROOT / "runtime", remote_path="/opt/bench")
)


def main():
    app = modal.App.lookup("blender-bench-harness", create_if_missing=True)
    with modal.enable_output():
        sandbox = modal.Sandbox.create(
            app=app, image=codex_image, timeout=900,
            outbound_domain_allowlist=CODEX_DOMAINS,
        )
    print(f"Login sandbox: {sandbox.object_id}", flush=True)
    try:
        sandbox.filesystem.make_directory("/root/.codex")
        sandbox.filesystem.write_bytes(
            (ROOT / "runtime" / "codex.toml").read_bytes(), "/root/.codex/config.toml"
        )
        process = sandbox.exec("codex", "--version")
        print(process.stdout.read(), flush=True)
        process = sandbox.exec("codex", "login", "--device-auth", timeout=840)
        for line in process.stdout:
            print(line, end="", flush=True)
        print(process.stderr.read(), end="", flush=True)
        process.wait()
        if process.returncode:
            raise RuntimeError("Codex login failed")
        auth = sandbox.filesystem.read_bytes("/root/.codex/auth.json").decode()
        modal.Secret.objects.create(AUTH_SECRET, {"CODEX_AUTH_JSON": auth})
        print(f"Login saved to Modal Secret: {AUTH_SECRET}")
    finally:
        sandbox.terminate()
        print("Login sandbox terminated.")


if __name__ == "__main__":
    main()
