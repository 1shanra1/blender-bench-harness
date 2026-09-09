# Blender Bench Harness

Compare how vision models reconstruct editable 3D objects from reference images using coding agents and the [official Blender MCP server](https://www.blender.org/lab/mcp-server/).

Runs use native goal modes in isolated Modal sandboxes, with a 75-minute agent limit, saved-file checkpoints, and independent multiview renders. Current pairings use Gemini 3.8 Flash High with Codex (via Vercel), Cursor, and Antigravity CLI.

```sh
uv sync
uv run modal setup
uv run python scripts/run_experiment.py --harness codex cursor antigravity --dry-run
```

Configure harness credentials before running. See [setup verification](docs/pairing-verification.md) and [running experiments](docs/experiments.md). Remove `--dry-run` to launch the selected pairings; runs consume provider credits. Results stay in ignored `outputs/` directories.
