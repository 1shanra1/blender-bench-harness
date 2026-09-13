"""Run one native Kimi Code /goal and preserve its output; never prompt it again."""

import json
import os
from pathlib import Path
import shutil
import subprocess

from event_log import EventLog


def main():
    model = os.environ["BENCH_MODEL"]
    if model not in {"google/gemini-3.8-flash", "moonshotai/kimi-k3", "openai/gpt-5.6-luna", "openai/gpt-5.6-terra"}:
        raise ValueError(f"Kimi Code model capabilities have not been configured for {model}")
    objective = os.environ["BENCH_OBJECTIVE"]
    if len(objective) > 4000:
        raise ValueError("Kimi Code native goals accept at most 4000 characters")
    # The generic Chat adapter moves tool images into user messages for Kimi.
    protocol = "openai" if model.startswith("moonshotai/") else "openai_responses"
    base_url = "https://ai-gateway.vercel.sh/v1"
    config = Path("/tmp/kimi-config")
    config.mkdir(mode=0o700)
    # Only this sandbox's selected model and credentials are available.
    settings = f'''default_model = "bench"
telemetry = false

[providers.gateway]
type = {json.dumps(protocol)}
base_url = {json.dumps(base_url)}
api_key = {json.dumps(os.environ["AI_GATEWAY_API_KEY"])}

[models.bench]
provider = "gateway"
model = {json.dumps(model)}
max_context_size = 1048576
max_output_size = 65536
capabilities = ["thinking", "image_in", "tool_use"]
support_efforts = ["high"]
default_effort = "high"

[thinking]
enabled = true
effort = "high"
keep = "all"

[[permission.rules]]
decision = "deny"
pattern = "SearchWeb"

[[permission.rules]]
decision = "deny"
pattern = "FetchURL"
'''
    (config / "config.toml").write_text(settings)
    (config / "config.toml").chmod(0o600)
    (config / "tui.toml").write_text("[upgrade]\nauto_install = false\n")
    (config / "mcp.json").write_text(json.dumps({"mcpServers": {"blender": {
        "command": "sh",
        "args": ["/opt/bench/start_mcp.sh", "runuser", "-u", "blender", "--", "blender-mcp"],
        "toolTimeoutMs": 600_000,
    }}}))
    env = dict(os.environ, KIMI_CODE_HOME=str(config))
    command = ["kimi", "-m", "bench", "-p", "/goal " + objective,
               "--output-format", "stream-json"]
    goal = None
    pending_reads = {}
    image_reads = set()
    with open("/tmp/kimi-stderr.log", "w") as stderr, EventLog("/tmp/kimi-events.jsonl") as events:
        process = subprocess.Popen(command, cwd="/workspace", env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=stderr, text=True)
        try:
            for line in process.stdout:
                events.write(line)
                events.flush()
                print(line[:1800].rstrip(), flush=True)
                event = json.loads(line)
                if event.get("type") == "goal.summary":
                    goal = event
                for call in event.get("tool_calls", []):
                    function = call.get("function", {})
                    if function.get("name") == "ReadMediaFile":
                        pending_reads[call["id"]] = json.loads(function["arguments"]).get("path")
                if event.get("role") == "tool" and event.get("tool_call_id") in pending_reads:
                    try:
                        content = json.loads(event["content"])
                    except (ValueError, TypeError):
                        continue  # A failed image tool can return plain text.
                    if isinstance(content, list) and any(part.get("type") == "image_url" for part in content):
                        image_reads.add(pending_reads[event["tool_call_id"]])
            process.wait()
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            # Wire records include reasoning and usage omitted by stream-json.
            transcripts = list(config.glob("sessions/*/*/agents/main/wire.jsonl"))
            if len(transcripts) == 1:
                shutil.copyfile(transcripts[0], "/tmp/kimi-transcript.jsonl")
            diagnostic = config / "logs/kimi-code.log"
            if diagnostic.is_file():
                shutil.copyfile(diagnostic, "/tmp/kimi-diagnostic.log")
    # Require the native goal summary as well as the documented exit code.
    status = {0: "complete", 3: "blocked", 6: "paused"}.get(process.returncode, "error")
    complete = status == "complete" and goal is not None and goal.get("status") == "complete"
    Path("/tmp/bench-native-result.json").write_text(json.dumps({
        "complete": complete, "goal_status": status, "goal": goal,
        "exit_code": process.returncode, "model": model,
        "image_reads": sorted(image_reads),
        "api_base_url": base_url, "api_protocol": protocol,
    }, indent=2))
    if process.returncode:
        raise RuntimeError(f"Kimi Code goal ended: {status} (exit {process.returncode})")
    if os.environ.get("BENCH_EXPERIMENT") != "1" and not (complete and {
        "/workspace/references/reference-01.png", "/workspace/viewport.png"
    }.issubset(image_reads)):
        raise RuntimeError("Native goal completion and both image reads were not verified")


if __name__ == "__main__":
    main()
