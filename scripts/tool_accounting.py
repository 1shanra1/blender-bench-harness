"""Count distinct tool invocations in native harness event logs."""
import json

CODEX_TOOLS = {
    "commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall",
    "webSearch", "imageView", "imageGeneration", "collabAgentToolCall",
}


def reported_tool_calls(path, harness):
    if harness not in {"codex", "claude", "kimi"} or not path.is_file():
        return None
    calls = set()
    readable = False
    try:
        with path.open() as source:
            for line in source:
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        continue
                    readable = True
                    ids = []
                    if harness == "codex" and event.get("method") in {"item/started", "item/completed"}:
                        item = event.get("params", {}).get("item", {})
                        if item.get("type") in CODEX_TOOLS:
                            ids.append(item.get("id"))
                    elif harness == "claude" and event.get("type") == "assistant":
                        ids.extend(block.get("id") for block in event.get("message", {}).get("content", [])
                                   if isinstance(block, dict) and block.get("type") == "tool_use")
                    elif harness == "kimi" and event.get("role") == "assistant":
                        ids.extend(call.get("id") for call in event.get("tool_calls", []))
                    calls.update(value for value in ids if isinstance(value, str) and value)
                except (ValueError, TypeError, AttributeError):
                    continue
    except OSError:
        return None
    return len(calls) if readable else None
