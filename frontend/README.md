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

The bundle contains `results.json`, reference images, final agent renders, independent camera views, interactive GLBs. Full `.blend` files, checkpoints, credentials, and raw logs stay outside the website bundle. Export archives remain under `exports/` on the Modal results volume.

`scripts/frontend_data.py` reads the recorded outcomes and native usage counters. `scripts/export_results.py` selects batches, copies the display assets, and converts their references to relative static paths. The frontend fetches `data/results.json` once on page load.

Missing values remain missing, and timed-out or failed runs retain their recorded status. Codex totals include cached input; other harnesses report cache separately. Claude Code uses per-model totals that include goal evaluation. Costs are not estimated.

## Checks

```sh
uv run python -m unittest discover -s tests
cd frontend
npm run build
```
