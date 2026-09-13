"""Export a small chronological slideshow from captured render versions."""

import hashlib
import json
import re
from pathlib import Path

from frontend_data import is_local_file, number, presentation_asset


def render_candidate(path):
    """Only main render/preview filenames; exclude crops and inspection views."""
    name = Path(path).name.lower()
    return (
        Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        and re.match(r"^(render|preview)(?:[_.-]|\d)", name) is not None
        and not re.search(r"(?:^|[_-])(alt(?:ernate)?|rear|side|top|front|crop|inspect\w*|comparison)(?:[_.-]|$)", name)
    )


def export_evolution(run_dir, assets, limit=6):
    journal = run_dir / "capture/trajectory.jsonl"
    if not is_local_file(journal, run_dir):
        return []
    from PIL import Image, UnidentifiedImageError

    candidates = []
    seen = set()
    for line in journal.read_text().splitlines():
        try:
            row = json.loads(line)
            digest, path = row["sha256"], row["path"]
            seconds = number(row.get("observed_seconds"))
            if seconds is None or not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                continue
            if not isinstance(path, str) or not render_candidate(path) or digest in seen:
                continue
            blob = run_dir / "capture/versions" / digest
            if not is_local_file(blob, run_dir):
                continue
            candidates.append({"source": blob, "digest": digest, "elapsed_seconds": seconds})
            seen.add(digest)
        except (ValueError, KeyError, TypeError):
            continue
    candidates.sort(key=lambda row: row["elapsed_seconds"])

    final = presentation_asset(run_dir, "render.png")
    if is_local_file(final, run_dir):
        digest = hashlib.sha256(final.read_bytes()).hexdigest()
        matched = next((row for row in candidates if row["digest"] == digest), None)
        # End at the submitted render, even if later captures were diagnostics.
        if matched:
            candidates = [row for row in candidates if row["elapsed_seconds"] <= matched["elapsed_seconds"] and row["digest"] != digest]
        candidates.append({"source": final, "digest": digest, "elapsed_seconds": matched["elapsed_seconds"] if matched else None, "final": True})

    valid = []
    for row in candidates:
        try:
            # A capture can catch a render halfway through writing. Decode fully.
            with Image.open(row["source"]) as image:
                image.load()
            valid.append(row)
        except (OSError, ValueError, UnidentifiedImageError):
            continue
    if len(valid) > limit:
        valid = [valid[round(i * (len(valid) - 1) / (limit - 1))] for i in range(limit)]

    frames = []
    for row in valid:
        filename = f"evolution-{row['digest']}.webp"
        with Image.open(row["source"]) as image:
            image.thumbnail((640, 640), Image.Resampling.LANCZOS)
            image.convert("RGB").save(assets / filename, "WEBP", quality=85)
        frames.append({"src": f"assets/{filename}", "elapsed_seconds": row["elapsed_seconds"], "final": row.get("final", False)})
    return frames
