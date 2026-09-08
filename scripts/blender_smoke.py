"""Build the Blender/MCP image and verify a viewport render on Modal."""
import modal

from environment import ROOT, blender_image

image = blender_image.add_local_dir(ROOT / "runtime", remote_path="/opt/bench")

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
