# Results website

A static React/Vite gallery of published experiment results. The website needs no Python server, database, or connection to Modal.

## Export and preview

From the repository root, deploy after changing the exporter, then select finished batches with display names:

```sh
uv run modal deploy scripts/remote_experiment.py
uv run python scripts/export_results.py '20260910T064103Z-E35312EC=Kettle'
cd frontend
npm ci
npm run dev
```

The export runs on Modal. The command downloads only the resulting website bundle into `frontend/public/data/`, replacing the previous selection. Pass several `BATCH_ID=Name` arguments to publish several experiments. Interactive GLBs are included by default. Missing GLBs are converted from saved Blender scenes on Modal. Use `--images-only` only when models are deliberately unwanted.

Open http://127.0.0.1:5173. For a production preview, run `npm run build` and `npm run preview` (port 4173). Deploy `frontend/dist/` to a static host. Export before building: generated website data is ignored by Git and must be present on the build machine. For a subpath deployment, build with `npm run build -- --base=/your-path/`.

## Data flow

Modal Volume → export function → selected JSON/images/GLBs → `public/data/` → Vite build.

The bundle contains `results.json`, reference images, final agent renders, independent camera views, interactive GLBs, and small evolution thumbnails. Full `.blend` files, original checkpoint archives, credentials, and raw logs stay outside the website bundle. Export archives remain under `exports/` on the Modal results volume.

`scripts/render_evolution.py` selects up to six chronological render/preview checkpoints per run, validates that each image decodes, and exports 640px WebP thumbnails. Crops and named alternate/inspection views are excluded; the submitted render ends the sequence. This is filename-based selection, not a visual quality assessment. Timestamps are when the supervisor observed a saved file, not exact render completion times. The frontend loops checkpoints at equal intervals, holds the final frame longer, and provides one shared play/pause control. Reduced-motion users start paused.

`scripts/frontend_data.py` reads the recorded outcomes and native usage counters. `scripts/export_results.py` selects batches, copies the display assets, and converts their references to relative static paths. The frontend fetches `data/results.json` once on page load.

Missing values remain missing, and timed-out or failed runs retain their recorded status. Codex totals include cached input; other harnesses report cache separately. Claude Code uses per-model totals that include goal evaluation. Costs are not estimated.

Tool-call totals come from `scripts/tool_accounting.py`: distinct Codex tool item IDs across start/completion events, Claude assistant `tool_use` IDs, and Kimi assistant `tool_calls` IDs. Repeated events are deduplicated; retries with new IDs count separately, and failed calls remain included. Counts describe harness-level invocations, not individual operations inside a shell command or Blender script. Missing logs produce an unreported value.

## Checks

```sh
uv run python -m unittest discover -s tests
cd frontend
npm run build
```
