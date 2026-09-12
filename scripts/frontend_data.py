"""Read reconstruction archives from disk for the website exporter."""

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESSES = ("codex", "cursor", "antigravity", "claude", "kimi")
VIEWS = ("positive_x", "negative_x", "positive_y", "negative_y", "positive_z", "negative_z")
IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}
MODEL_TYPES = {".glb", ".gltf"}


def is_local_file(path, base):
    try:
        relative = path.relative_to(base)
        current = base
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                return False
        return base.resolve() == base.absolute() and not base.is_symlink() and path.is_file() and path.resolve().is_relative_to(base.resolve())
    except (ValueError, OSError):
        return False


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value >= 0 else None


def read_json(path, base):
    if not is_local_file(path, base):
        return {}
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def reported_usage(path, harness):
    """Count input (including cache reads/writes) plus output for current harnesses.

    Codex and Claude final summaries are cumulative; Kimi usage.record events
    are per request. Never add the duplicated step.end copies of Kimi usage.
    """
    if not path.is_file():
        return None
    latest = None
    kimi_records = []
    try:
        with path.open() as source:
            for line in source:
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        continue
                    candidate = None
                    if harness == "kimi" and event.get("type") == "usage.record":
                        kimi_records.append(event["usage"])
                    if harness == "codex" and event.get("method") == "thread/tokenUsage/updated":
                        usage = event["params"]["tokenUsage"]["total"]
                        candidate = {"tokens": number(usage.get("totalTokens")), "cached_tokens": number(usage.get("cachedInputTokens")), "basis": "Includes cached input", "source": "Codex cumulative token usage"}
                    elif harness == "cursor" and event.get("type") == "result" and isinstance(event.get("usage"), dict):
                        usage = event["usage"]
                        input_tokens, output_tokens = number(usage.get("inputTokens")), number(usage.get("outputTokens"))
                        candidate = {"tokens": input_tokens + output_tokens if input_tokens is not None and output_tokens is not None else None, "cached_tokens": number(usage.get("cacheReadTokens")), "basis": "Cache reads reported separately", "source": "Cursor final result"}
                    elif harness == "antigravity" and isinstance(event.get("result"), dict) and isinstance(event["result"].get("usage"), dict):
                        usage = event["result"]["usage"]
                        candidate = {"tokens": number(usage.get("total_tokens")), "cached_tokens": number(usage.get("cache_read_tokens")), "basis": "Cache reads reported separately", "source": "Antigravity final result"}
                    elif harness == "claude" and event.get("type") == "result" and event.get("modelUsage"):
                        # Top-level usage omits native /goal evaluation. The final
                        # per-model counters include it; sum each model once.
                        models = list(event["modelUsage"].values())
                        counts = [number(model.get(key)) for model in models for key in ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")]
                        cached = [number(model.get("cacheReadInputTokens")) for model in models]
                        candidate = {
                            "tokens": sum(counts) if all(value is not None for value in counts) else None,
                            "cached_tokens": sum(cached) if all(value is not None for value in cached) else None,
                            "basis": "Input including cache reads/writes + output",
                            "source": "Claude Code per-model totals, including goal evaluation",
                        }
                    if candidate is not None and candidate["tokens"] is not None:
                        latest = candidate
                except (ValueError, TypeError, KeyError, AttributeError):
                    continue  # Partial JSON lines can occur during collection.
    except OSError:
        return None
    if harness == "kimi":
        return summed_usage(kimi_records,
            ("inputOther", "output", "inputCacheRead", "inputCacheCreation"),
            "inputCacheRead", "Kimi Code per-request usage records")
    return latest


def summed_usage(records, keys, cache_key, source):
    if not records:
        return None
    counts = [number(record.get(key)) for record in records for key in keys]
    if any(value is None for value in counts):
        return None
    return {
        "tokens": sum(counts),
        "cached_tokens": sum(record[cache_key] for record in records),
        "basis": "Input including cache reads/writes + output",
        "source": source,
    }


class LocalArchive:
    def __init__(self, root=ROOT, experiments_root=None):
        self.root = root.resolve()
        self.experiments_root = experiments_root or self.root / "outputs/experiments"
        self.assets = {}

    def catalogue(self, batch_ids=None):
        experiments_root = self.experiments_root
        reference_root = self.root / "references"
        assets = {}

        def asset(path, base, allowed_types=IMAGE_TYPES):
            if path is None or path.suffix.lower() not in allowed_types or not is_local_file(path, base):
                return None
            # Include file modification time in the asset key to ensure instant cache invalidation on edits
            mtime = int(path.stat().st_mtime) if path.is_file() else 0
            key = hashlib.sha256(f"{path.relative_to(self.root)}:{mtime}".encode()).hexdigest()[:24]
            assets[key] = (path, base)
            prefix = "models" if path.suffix.lower() in MODEL_TYPES else "images"
            return f"/api/{prefix}/{key}"

        references = {}
        if reference_root.is_dir() and not reference_root.is_symlink():
            for path in reference_root.rglob("*"):
                if path.suffix.lower() in IMAGE_TYPES and is_local_file(path, reference_root):
                    references[hashlib.sha256(path.read_bytes()).hexdigest()] = path

        experiments = []
        batches = sorted(experiments_root.iterdir(), reverse=True) if experiments_root.is_dir() and not experiments_root.is_symlink() else []
        for batch in batches:
            if batch_ids is not None and batch.name not in batch_ids:
                continue
            if not batch.is_dir() or batch.is_symlink():
                continue
            runs = []
            hashes = set()
            reference = None
            for harness in HARNESSES:
                folder = batch / harness
                if not folder.is_dir() or folder.is_symlink():
                    continue
                manifest = read_json(folder / "manifest.json", experiments_root)
                result = read_json(folder / "result.json", experiments_root)
                if not manifest:
                    continue
                reference_hash = manifest.get("reference_sha256")
                reference_hash = reference_hash if isinstance(reference_hash, str) and reference_hash else None
                hashes.add(reference_hash)
                reference = references.get(reference_hash) or reference
                prefix = "agy" if harness == "antigravity" else harness
                events = folder / "capture" / ("kimi-transcript.jsonl" if harness == "kimi" else f"{prefix}-events.jsonl")
                usage = reported_usage(events, harness) if is_local_file(events, experiments_root) else None
                glb_candidate = folder / "evaluation/scene.glb"
                if not is_local_file(glb_candidate, experiments_root):
                    glb_candidate = folder / "capture/artifacts/scene.glb"
                runs.append({
                    "id": harness,
                    "name": {"codex": "Codex", "cursor": "Cursor", "antigravity": "Antigravity", "claude": "Claude Code", "kimi": "Kimi Code"}[harness],
                    "model": manifest.get("model", "Unknown model"),
                    "provider": manifest.get("provider"),
                    "effort": manifest.get("reasoning_effort"),
                    "started_at": manifest.get("started_at"),
                    "status": result.get("status", "unavailable"),
                    "native_complete": (result.get("native") or {}).get("complete"),
                    "elapsed_seconds": number(result.get("elapsed_seconds")),
                    "limit_seconds": number(result.get("limit_seconds", manifest.get("experiment_seconds"))),
                    "model_url": asset(glb_candidate, experiments_root, allowed_types=MODEL_TYPES),
                    "render": asset(folder / "capture/artifacts/render.png", experiments_root),
                    "views": {view: asset(folder / "evaluation" / f"{view}.png", experiments_root) for view in VIEWS},
                    "evaluation_status": (result.get("evaluation") or {}).get("status", "unavailable"),
                    "usage": usage,
                    "cost_usd": None,
                })
            if not runs:
                continue
            # Only show one common reference when the manifests agree on it.
            common_reference = len(hashes) == 1 and None not in hashes
            if not common_reference:
                reference = None
            reference_url = asset(reference, reference_root)
            staged_reference = batch / "reference.png"
            if common_reference and is_local_file(staged_reference, experiments_root):
                if hashlib.sha256(staged_reference.read_bytes()).hexdigest() in hashes:
                    reference_url = asset(staged_reference, experiments_root)
            subject = reference.parent.name if reference else "reconstruction"
            experiments.append({
                "id": batch.name,
                "name": {"drill": "Cordless drill", "skull": "Human skull", "kettle": "Kettle"}.get(subject, subject.replace("_", " ").capitalize()),
                "reference": reference_url,
                "started_at": runs[0]["started_at"],
                "runs": runs,
            })
        self.assets = assets
        return {"experiments": experiments}

    def asset_path(self, key):
        entry = self.assets.get(key)
        return entry[0] if entry and is_local_file(*entry) else None

    def image_path(self, key):
        return self.asset_path(key)
