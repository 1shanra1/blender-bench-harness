"""Submit one native Claude Code /goal; capture its stream and actual goal verdict."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from event_log import EventLog


def goal_verdict(transcript, objective):
    """A normal exit or a goal-clear sentinel is not evidence of achievement."""
    verdict = None
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") != "attachment":
            continue
        attachment = event.get("attachment", {})
        if attachment.get("type") == "goal_status" and (attachment.get("condition") or "").strip() == objective.strip():
            verdict = attachment
    return verdict


def goal_completed(verdict, result):
    return bool(
        verdict and verdict.get("met") is True
        and not verdict.get("sentinel") and not verdict.get("failed")
        and result.get("subtype") == "success" and not result.get("is_error")
    )


def main():
    model = os.environ["BENCH_MODEL"]
    objective = os.environ["BENCH_OBJECTIVE"]
    experiment = os.environ.get("BENCH_EXPERIMENT") == "1"
    # Fresh per-sandbox configuration; never import the host's Claude settings.
    config = Path("/tmp/claude-config")
    config.mkdir(exist_ok=True)
    mcp = config / "mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"blender": {
        "command": "sh",
        "args": ["/opt/bench/start_mcp.sh", "runuser", "-u", "blender", "--", "blender-mcp"],
        "timeout": 600_000,
    }}}))
    settings = config / "settings.json"
    settings.write_text(json.dumps({"permissions": {
        "allow": ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "mcp__blender__*"],
        "deny": ["WebFetch", "WebSearch"],
    }}))
    env = dict(os.environ)
    env.update(
        CLAUDE_CONFIG_DIR=str(config),
        ANTHROPIC_BASE_URL="https://ai-gateway.vercel.sh/claude-code",
        ANTHROPIC_AUTH_TOKEN=env.pop("AI_GATEWAY_API_KEY"),
        ANTHROPIC_API_KEY="",
        ANTHROPIC_MODEL=model,
        CLAUDE_CODE_SUBAGENT_MODEL=model,
        CLAUDE_CODE_EFFORT_LEVEL="high",
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
        # Third-party API compatibility; native /goal stays enabled.
        CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="1",
        # 2.1.268's native capability override: Gemini requires system messages
        # at the start. The general beta flag above does not disable this feature.
        CLAUDE_CODE_MODEL_CAPABILITIES=f"{model}=-mid_conv_system",
        ENABLE_TOOL_SEARCH="false",
        MCP_TOOL_TIMEOUT="600000",
    )
    # /goal uses the small-fast-model slot. Keep every alias on the selected model,
    # including the evaluator and background calls; do not introduce a second model.
    for family in ("HAIKU", "SONNET", "OPUS", "FABLE"):
        env[f"ANTHROPIC_DEFAULT_{family}_MODEL"] = model
    session_id = str(uuid.uuid4())
    command = [
        "claude", "-p", "/goal " + objective,
        "--model", model, "--effort", "high", "--session-id", session_id,
        "--output-format", "stream-json", "--verbose", "--include-hook-events",
        "--strict-mcp-config", "--mcp-config", str(mcp),
        "--settings", str(settings), "--setting-sources", "user",
    ]
    result = {}
    pending_reads = {}
    image_reads = set()
    with open("/tmp/claude-stderr.log", "w") as stderr, EventLog("/tmp/claude-events.jsonl") as events:
        process = subprocess.Popen(command, cwd="/workspace", env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=stderr, text=True)
        try:
            for line in process.stdout:
                events.write(line)
                events.flush()
                print(line[:1800].rstrip(), flush=True)
                event = json.loads(line)
                if event.get("type") == "result":
                    result = event
                for block in event.get("message", {}).get("content", []):
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use" and block.get("name") == "Read":
                        pending_reads[block["id"]] = block.get("input", {}).get("file_path")
                    if block.get("type") == "tool_result" and not block.get("is_error"):
                        content = block.get("content", [])
                        if isinstance(content, list) and any(part.get("type") == "image" for part in content):
                            path = pending_reads.get(block.get("tool_use_id"))
                            if path:
                                image_reads.add(path)
            process.wait()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            # The native transcript includes goal_status attachments that the
            # public message stream may omit. Preserve it as completion evidence.
            transcript = config / "projects" / "-workspace" / f"{session_id}.jsonl"
            if transcript.is_file():
                shutil.copyfile(transcript, "/tmp/claude-transcript.jsonl")
    text = transcript.read_text() if transcript.is_file() else ""
    verdict = goal_verdict(text, objective)
    complete = process.returncode == 0 and goal_completed(verdict, result)
    Path("/tmp/bench-native-result.json").write_text(json.dumps({
        "complete": complete,
        "goal": verdict,
        "goal_evaluator_model": model,
        "api_base_url": env["ANTHROPIC_BASE_URL"],
        "model_capabilities": env["CLAUDE_CODE_MODEL_CAPABILITIES"],
        "experimental_betas_disabled": True,
        "session_id": session_id,
        "image_reads": sorted(image_reads),
        "reported_models": list(result.get("modelUsage", {})),
    }, indent=2))
    if process.returncode or result.get("is_error"):
        detail = result.get("result") or result.get("terminal_reason") or result.get("subtype")
        raise RuntimeError(f"Claude Code failed: exit={process.returncode}, {detail}")
    if not experiment and not (complete and {
        "/workspace/references/reference-01.png", "/workspace/viewport.png"
    }.issubset(image_reads)):
        raise RuntimeError("Native goal achievement and both image reads were not verified")


if __name__ == "__main__":
    main()
