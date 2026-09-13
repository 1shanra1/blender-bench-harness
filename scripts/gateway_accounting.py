"""Conservative recovery of usage for requests retained in Claude's event stream."""
import math

FIELDS = ("tokens_prompt", "tokens_completion", "native_tokens_reasoning",
          "native_tokens_cached", "native_tokens_cache_creation")


def generation_ids(events):
    # Assistant messages can be repeated for separate content blocks. Count
    # generation IDs once; never extract IDs from tool output or user text.
    return sorted({event["message"]["id"] for event in events
                   if isinstance(event, dict) and event.get("type") == "assistant"
                   and isinstance(event.get("message"), dict)
                   and str(event["message"].get("id", "")).startswith("gen_")})


def recovered_usage(records):
    if not records:
        return None
    seen = set()
    totals = dict.fromkeys(FIELDS, 0)
    for record in records:
        gid = record["id"]
        if gid in seen:
            raise ValueError("Duplicate generation record")
        seen.add(gid)
        for field in FIELDS:
            value = record[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or int(value) != value:
                raise ValueError(f"Invalid or missing usage: {field}")
            totals[field] += int(value)
    # Gateway exposes uncached prompt, cache reads/writes and reasoning
    # separately from visible completion. Each component is included once.
    return {
        "tokens": sum(totals.values()),
        "cached_tokens": totals["native_tokens_cached"],
        "coverage": "recorded_requests",
        "request_count": len(seen),
        "source": "Vercel AI Gateway per-request records",
        "basis": "Recorded requests only; unlogged goal evaluations or interrupted requests may add usage. Input including cache + output including reasoning.",
    }
