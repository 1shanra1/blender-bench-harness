# Meshmatch results website

The static React/Vite results website for [Meshmatch](https://meshmatch.net). The website needs no Python server, database, or connection to Modal.

## Export and preview

From the repository root, deploy after changing the exporter, then select finished batches with display names:

```sh
uv run modal deploy scripts/remote_experiment.py
uv run python scripts/export_results.py 'GEMINI_BATCH_ID=Desk Lamp' 'LUNA_BATCH_ID=Desk Lamp'
cd frontend
npm ci
npm run prepare:images
npm run dev
```

Use Node.js 22.12+ and replace the example batch IDs with finished batches in your own Modal results volume. Batches with the same display name are grouped as variants of the same object.

The export runs on Modal. The command downloads only the resulting website bundle into `frontend/public/data/`, replacing the previous selection. Pass several `BATCH_ID=Name` arguments to publish several experiments. Interactive GLBs are included by default. Missing GLBs are converted from saved Blender scenes on Modal. Use `--images-only` only when models are deliberately unwanted.

Open the URL printed by Vite, normally http://127.0.0.1:5173. For a production preview, run `npm run build` and `npm run preview` (port 4173). Deploy `frontend/dist/` to a static host. Export before building: generated website data is ignored by Git and must be present on the build machine. For a subpath deployment, build with `npm run build -- --base=/your-path/`.

## Data flow

Modal Volume → export function → selected JSON/images/GLBs → `public/data/` → Vite build.

The bundle contains `results.json`, reference images, final agent renders, independent camera views, interactive GLBs, and small evolution thumbnails. Full `.blend` files, original checkpoint archives, credentials, and raw logs stay outside the website bundle. Export archives remain under `exports/` on the Modal results volume.

`scripts/render_evolution.py` selects up to six chronological render/preview checkpoints per run, validates that each image decodes, and exports 640px WebP thumbnails. Crops and named alternate/inspection views are excluded; the submitted render ends the sequence. This is filename-based selection, not a visual quality assessment. Timestamps are when the supervisor observed a saved file, not exact render completion times. The frontend loops checkpoints at equal intervals, holds the final frame longer, and provides one shared play/pause control. Reduced-motion users start paused.

`scripts/frontend_data.py` reads the recorded outcomes and native usage counters. `scripts/export_results.py` selects batches, copies the display assets, and converts their references to relative static paths. The frontend fetches `data/results.json` once on page load.

Missing values remain missing. Token totals count input, including cache reads and writes, plus output; cache is included once per request. Codex, Claude Code, and Kimi Code expose different native fields, so the exporter normalizes them. Claude Code uses its final per-model totals, including goal evaluation, when available. If that summary is missing, verified Gateway request records can supply a lower bound, displayed with **≥**. Recovery requires a matching event-log hash and every discovered request ID. Unlogged evaluator or interrupted requests may still be absent. Dollar costs are not estimated.

Artifact recovery is explicit: captured deliverables take priority, while a recorded post-run script rebuild can supply a missing render or scene without changing the original run status. A recovered completion requires the supervisor’s saved native verdict. The published selection also includes a fresh rerun replacing one failed run; a plain batch export does not automatically reproduce that manual selection. The original run records remain separate from the website presentation.

Tool-call totals come from `scripts/tool_accounting.py`: distinct Codex tool item IDs across start/completion events, Claude assistant `tool_use` IDs, and Kimi assistant `tool_calls` IDs. Repeated events are deduplicated; retries with new IDs count separately, and failed calls remain included. Counts describe harness-level invocations, not individual operations inside a shell command or Blender script. Missing logs produce an unreported value.

## Checks

`npm run build` prepares 960px card previews and bounds evolution frames to 640px using Sharp. Original renders and references remain available for enlargement; usage and timing fields are unchanged. Run `npm run prepare:images` after replacing local exports during development. Evolution images load when the section enters the viewport, and the 3D viewer code loads only when opened.

```sh
uv run python -m unittest discover -s tests
cd frontend
npm run build
node --test scripts/prepare-previews.test.mjs
```

## Cloudflare Pages

The site uses Direct Upload so the exported results are included even though they are not stored in Git. From `frontend/`, run `npx wrangler login` once, then `npm run deploy`. The included configuration targets the `meshmatch` Pages project with `main` as its production branch. For your own deployment, choose your own project name in `wrangler.jsonc` and the `deploy` command in `package.json`. Always keep the current `public/data/` export present before building.

For your own site, add a domain you control under the Pages project’s Custom domains settings. Associate each domain with Pages before creating its DNS record. The results catalogue uses `Cache-Control: no-cache` so returning visitors can receive updated experiment data.

Cloudflare Pages permits individual assets up to 25 MiB. The current largest GLB is about 20 MiB; check this limit when adding new results. Deploy only `dist/`, which contains public site assets rather than raw logs, Blender source files, or credentials.
