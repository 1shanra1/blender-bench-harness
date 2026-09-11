# Blender Bench frontend

A local results viewer built with React, TypeScript, Vite, and Tailwind CSS. The visual direction follows the approved Paper comparison, with the redundant labels removed.

## Run

Requires Python 3.12+ and Node 22.12+ (Node 24 LTS recommended).

```sh
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173/**. This single command starts Vite and the Python results API on port 8766. Stop both with Ctrl-C. Frontend edits reload automatically; restart the command after editing the Python API.

For a production build served locally:

```sh
npm run build
npm run preview
```

Open **http://127.0.0.1:8765/**. Both servers bind to the loopback interface.

## Components

- [shadcn/ui with Base UI](https://ui.shadcn.com/docs/installation/vite): select menus, tabs, tooltips, image aspect ratios, loading and empty states. Generated components are in `src/components/ui`.
- [shadcn charts](https://ui.shadcn.com/docs/components/chart) and [Recharts](https://recharts.github.io): the wall-time comparison.
- [Yet Another React Lightbox](https://yet-another-react-lightbox.com): image inspection with zoom, captions, and keyboard navigation.
- [Paper Shaders](https://github.com/paper-design/shaders): the original Grain Gradient settings, confined to a subtle monochrome backdrop. Animation pauses in hidden tabs and for reduced-motion preferences.
- Inter Variable and Lucide icons are bundled locally.

The UI supports experiment selection, agent renders, and synchronized independent camera axes. Select an image to enlarge it. The drill defaults first because all three pairings have final renders.

## Local data contract

`scripts/frontend_data.py` reads collected batches in `outputs/experiments/`. `scripts/frontend_server.py` exposes `GET /api/experiments` and opaque, allowlisted image URLs. It serves no credentials, event logs, scene files, or arbitrary filesystem paths, and makes no Modal or provider requests. Images remain in the existing ignored archive; nothing is copied into the frontend build.

- Reference images are matched against each batch's manifest SHA-256, independently of the currently configured experiment reference. Missing or conflicting hashes do not get a guessed shared reference.
- Agent images come from `capture/artifacts/render.png`. Independent views come from each run's `evaluation/{positive,negative}_{x,y,z}.png` files. Older checkpoints are not promoted to final renders.
- Duration and completion status come from `result.json`; missing values remain missing. A saved render from a timed-out run is still viewable, without claiming that the native goal completed.
- Codex tokens use the last valid cumulative `thread/tokenUsage/updated` total, not a sum of updates. Cursor uses input + output from the final result. Antigravity uses the final result's `total_tokens`. Native cache semantics differ, so tokens are presented as annotated values rather than ranked bars.
- Costs are currently unavailable. No prices or estimates are invented.

The current local archive contains the drill batch (three final renders) and skull batch (Codex and Antigravity final renders; Cursor failed without one). Refresh to rescan after collecting another batch.

## Checks

```sh
npm run build
cd ..
python3 -m unittest discover -s tests -v
```

The tests cover reference matching, missing and timed-out runs, final-artifact selection, token provenance, and file-serving boundaries. The initial pass was checked through compilation and HTTP/data checks; no browser automation was used.
