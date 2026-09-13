# Meshmatch

Compare how vision models reconstruct editable 3D objects from reference images using coding agents and the [official Blender MCP server](https://www.blender.org/lab/mcp-server/).

Runs use native goal modes in isolated Modal sandboxes, with a 90-minute agent limit, saved-file checkpoints, and independent multiview renders. Harnesses include Codex, Cursor, Claude Code, Kimi Code, and Antigravity CLI. Codex, Claude Code, and Kimi Code connect through Vercel. See the verified model pairings below before launching.

```sh
uv sync
uv run modal setup
uv run python scripts/launch_experiment.py --harness codex cursor claude --dry-run
```

Configure harness credentials before running. See [setup verification](docs/pairing-verification.md) and [running experiments](docs/experiments.md). Remove `--dry-run` to launch the selected pairings; runs consume provider credits. Results stay on a Modal Volume; download only the files you want.

## Results frontend

Export selected finished batches on Modal, then preview the static website:

```sh
uv run python scripts/export_results.py 'BATCH_ID=Display name'
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173/**. Build with `npm run build` and deploy `frontend/dist/` to a static host. See [export setup and data notes](frontend/README.md).
