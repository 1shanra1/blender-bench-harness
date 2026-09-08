"""Verify Modal authentication and remote sandbox execution."""

import modal


def main():
    app = modal.App.lookup("blender-bench-harness", create_if_missing=True)
    sandbox = modal.Sandbox.create(
        app=app,
        image=modal.Image.debian_slim(python_version="3.12"),
        timeout=60,
    )
    print(f"Sandbox: {sandbox.object_id}", flush=True)
    try:
        process = sandbox.exec(
            "python", "-c", "import platform; print('Modal OK:', platform.system())",
            timeout=30,
        )
        print(process.stdout.read(), end="")
        print(process.stderr.read(), end="")
        process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"Remote command exited with {process.returncode}")
    finally:
        sandbox.terminate()
        print("Sandbox terminated.")


if __name__ == "__main__":
    main()
