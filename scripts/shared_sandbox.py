"""Common resources and workspace preparation; no agent continuation logic."""

import hashlib

import modal
from environment import BLENDER_VERSION, MCP_COMMIT, ROOT

# Keep CPU capacity equal; memory can grow beyond its reservation if available.
CPU = (4.0, 4.0)
MEMORY_MIB = 8192
EXPERIMENT_SECONDS = 75 * 60
REFERENCE = ROOT / "references/skull/reference-01.png"
PROMPT = ROOT / "prompts/reconstruction-draft.md"


def create_sandbox(image, secret, domains, timeout):
    return modal.Sandbox.create(
        app=modal.App.lookup("blender-bench-harness"),
        image=image.add_local_dir(ROOT / "runtime", remote_path="/opt/bench"),
        cpu=CPU,
        memory=MEMORY_MIB,
        timeout=timeout,
        secrets=[modal.Secret.from_name(secret)],
        outbound_domain_allowlist=domains,
    )


def prepare_workspace(sandbox, reference=None, prompt=None):
    process = sandbox.exec(
        "sh",
        "-c",
        "useradd -m blender && mkdir -p /workspace/references /workspace/output /workspace/scripts "
        "&& chmod 777 /workspace /workspace/output /workspace/scripts",
    )
    process.wait()
    if process.returncode:
        raise RuntimeError(process.stderr.read())
    reference = REFERENCE.read_bytes() if reference is None else reference
    prompt = PROMPT.read_bytes() if prompt is None else prompt
    sandbox.filesystem.write_bytes(reference, "/workspace/references/reference-01.png")
    sandbox.filesystem.write_bytes(prompt, "/workspace/task.md")
    environment_note = (ROOT / "runtime/ENVIRONMENT.md").read_bytes()
    sandbox.filesystem.write_bytes(environment_note, "/workspace/ENVIRONMENT.md")
    process = sandbox.exec(
        "chmod", "444", "/workspace/references/reference-01.png", "/workspace/task.md",
        "/workspace/ENVIRONMENT.md",
    )
    process.wait()
    if process.returncode:
        raise RuntimeError(process.stderr.read())
    # Credentials and unrelated runs are never included in the workspace.
    return {
        "cpu": CPU,
        "memory_mib": MEMORY_MIB,
        "memory_limit_mib": None,
        "blender_version": BLENDER_VERSION,
        "mcp_commit": MCP_COMMIT,
        "display": "1280x800x24",
        "graphics": "software OpenGL",
        "experiment_seconds": EXPERIMENT_SECONDS,
        "reference_sha256": hashlib.sha256(reference).hexdigest(),
        "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
        "environment_note_sha256": hashlib.sha256(environment_note).hexdigest(),
    }


def start_blender(sandbox):
    # Start Blender in headless Xvfb as a persistent background daemon (do not wait).
    # env -i keeps provider credentials out of Blender and its descendants.
    sandbox.exec(
        "env",
        "-i",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "BLENDER_USER_SCRIPTS=/opt/blender-user",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "runuser",
        "-u",
        "blender",
        "--",
        "xvfb-run",
        "-a",
        "-s",
        "-screen 0 1280x800x24 +extension GLX",
        "sh",
        "-c",
        "openbox >/tmp/openbox.log 2>&1 & xcompmgr >/tmp/compositor.log 2>&1 & "
        "exec blender --factory-startup --online-mode --gpu-backend opengl "
        "--python /opt/bench/start_blender.py >/tmp/blender.log 2>&1",
    )
    # Synchronously probe until Blender's MCP server is accepting connections on port 9876.
    process = sandbox.exec("python", "/opt/bench/wait_for_port.py", "9876", "30")
    process.wait()
    if process.returncode:
        raise RuntimeError("Blender MCP did not become ready: " + process.stderr.read())
