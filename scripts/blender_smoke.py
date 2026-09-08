"""Build the Blender/MCP image and verify a viewport render on Modal."""
from pathlib import Path

import modal

BLENDER_VERSION = "5.2.1"
BLENDER_SHA256 = "a31f524fa99a527d3d52b7f5aaa68c34e1a19d5a1c9473f79c5cc610fd5b10e9"
MCP_COMMIT = "4309a39646e644261624bfcd2bca669b343b7621"
ROOT = Path(__file__).resolve().parents[1]

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        "curl", "git", "xz-utils", "xvfb", "xauth", "openbox", "xcompmgr",
        "libgl1", "libegl1", "libgl1-mesa-dri", "libxrender1", "libxi6",
        "libxfixes3", "libxkbcommon0", "libsm6", "libxxf86vm1",
    )
    .run_commands(
        f"curl -fL --retry 3 https://mirror.blender.org/release/Blender5.2/blender-{BLENDER_VERSION}-linux-x64.tar.xz -o /tmp/blender.tar.xz",
        f"echo '{BLENDER_SHA256}  /tmp/blender.tar.xz' | sha256sum -c -",
        "mkdir -p /opt/blender && tar -xJf /tmp/blender.tar.xz --strip-components=1 -C /opt/blender && rm /tmp/blender.tar.xz",
        "ln -s /opt/blender/blender /usr/local/bin/blender",
        "git clone https://projects.blender.org/lab/blender_mcp.git /opt/blender-mcp",
        f"git -C /opt/blender-mcp checkout {MCP_COMMIT}",
        "mkdir -p /opt/blender-user/addons && cp -r /opt/blender-mcp/addon/blender_mcp_addon /opt/blender-user/addons/",
    )
    # The official server imports FastMCP, which was removed in MCP SDK 2.x.
    .uv_pip_install("/opt/blender-mcp/mcp", "mcp[cli]<2")
    .env({"BLENDER_USER_SCRIPTS": "/opt/blender-user", "LIBGL_ALWAYS_SOFTWARE": "1"})
    .add_local_dir(ROOT / "runtime", remote_path="/opt/bench")
)


def main():
    app = modal.App.lookup("blender-bench-harness", create_if_missing=True)
    with modal.enable_output():
        sandbox = modal.Sandbox.create(
            app=app, image=image, timeout=180, cpu=2, memory=4096,
            block_network=True,
        )
    print(f"Sandbox: {sandbox.object_id}", flush=True)
    try:
        sandbox.exec(
            "xvfb-run", "-a", "-s", "-screen 0 1280x800x24 +extension GLX",
            "sh", "-c",
            "openbox >/tmp/openbox.log 2>&1 & xcompmgr >/tmp/compositor.log 2>&1 & exec blender --factory-startup --online-mode --gpu-backend opengl --python /opt/bench/start_blender.py >/tmp/blender.log 2>&1",
        )
        probe = sandbox.exec("python", "/opt/bench/check_mcp.py", timeout=90)
        print(probe.stdout.read(), end="")
        print(probe.stderr.read(), end="")
        probe.wait()
        if probe.returncode != 0:
            log = sandbox.exec("cat", "/tmp/blender.log")
            print(log.stdout.read())
            raise RuntimeError("Blender MCP smoke check failed")
        output = ROOT / "outputs" / "viewport.png"
        output.parent.mkdir(exist_ok=True)
        output.write_bytes(sandbox.filesystem.read_bytes("/tmp/viewport.png"))
        print(f"Saved {output}")
    finally:
        sandbox.terminate()
        print("Sandbox terminated.")


if __name__ == "__main__":
    main()
