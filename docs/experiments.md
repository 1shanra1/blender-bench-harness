# Reconstruction runs

Each selected harness gets a new Modal sandbox, its own credential Secret, the same reference image and approved prompt, and the shared Blender environment. No histories, output directories, or volumes are shared between agents. Codex uses Gemini 3.8 Flash through Vercel; Cursor and Antigravity select their native Gemini 3.8 Flash High entries.

Preview without creating sandboxes or calling models:

```sh
uv run python scripts/launch_experiment.py --harness codex cursor antigravity --dry-run
```

Deploy the controller once, and redeploy after changing its code or bundled runtime:

```sh
uv run modal deploy scripts/remote_experiment.py
```

Remove `--dry-run` to submit those harnesses concurrently. The launcher prints a batch ID and Modal function call ID, then exits; the remote controller continues after the laptop disconnects. Results stay in the `blender-bench-results` Modal Volume under `experiments/<batch-id>/`. Only the controller mounts that volume. Agents cannot browse it, and no experiment artifacts are automatically downloaded to the laptop.

`batch.json` records collection progress and each harness outcome. Its `finished` status means the controller finished collecting, not that all models succeeded. The controller has a separate two-hour ceiling covering setup, the 75-minute agent deadline, and final rendering. Automatic function retries are disabled; an existing batch directory prevents repeating that batch.

During execution, the controller collects log deltas and new saved checkpoint versions, waiting 120 seconds between completed passes, plus a final pass when the driver stops. Large files stream directly from the sandbox to the controller’s volume mount. Each pass commits the received data; no artifact data passes through the laptop. A crash can still lose unsaved work or files that have not finished copying and committing.

The original `scripts/run_experiment.py` remains available for explicit local execution.

Select only the desired harness names; each invocation produces one independent run per selected harness. This consumes provider credits. Existing harness authentication and Modal setup are prerequisites; see [setup verification](pairing-verification.md).

## Lifecycle

Cursor CLI 2026.09.02-c22c1a3 is patched at image build time to give MCP tool calls a 600-second timeout. `runtime/patch_cursor_timeout.py` checks the original bundle hash and changes only the SDK call's timeout option. Run manifests identify this as `mcp-tool-timeout-600s-v1`; native goal behavior is unchanged. The first drill batch predates this patch.

The runner stages `prompts/reconstruction-draft.md` unchanged and submits it once through each harness's native goal interface. The previously verified goal drivers are reused, with smoke-only viewport assertions disabled. They still require native goal completion. There is no custom continuation or feedback loop.

The supervisor starts the 75-minute clock when it launches the harness driver, including CLI startup. On process exit or timeout it terminates the remaining driver process group, stops Blender, and collects artifacts. Setup and collection have additional sandbox lifetime; they do not extend the agent's deadline. A successful process exit without native completion is not recorded as goal completion. A completed goal does not imply that the saved artifacts are valid or match the reference.

## Outputs

Each remote invocation writes a unique directory under `experiments/` on the results volume, with a subdirectory per harness (the legacy local runner uses ignored `outputs/experiments/`):

- `manifest.json`, `prompt.md`: exact submitted prompt, input hashes, requested model/effort, versions, resources, and sandbox ID.
- `capture/result.json`: native completion, deadline/exit information, and required artifact presence.
- `capture/artifacts/`: final files from `/workspace/output/`, including the agent's scene and chosen render.
- `capture/scripts/files/`: final shared scripts from `/workspace/scripts`; `capture/scripts/versions/` and `trajectory.jsonl` retain their saved revisions. Scripts elsewhere are not collected.
- `capture/versions/` and `capture/trajectory.jsonl`: saved file versions indexed by SHA-256, original path, and observation time.
- `capture/*events.jsonl` and logs: full streams exposed by the CLIs, including available usage data. Antigravity may abbreviate tool arguments; these are not complete operating-system audits.
- `capture/*events.timestamps.jsonl`: receipt timestamps keyed by native event line number. These measure when the driver received a line, not when the provider generated it.
- `capture/blender-mcp.log`: MCP server stderr, kept separate from protocol stdout.
- `evaluation/`: independent renders and camera metadata. `evaluation.log` records renderer errors.
- `result.json`: run outcome plus evaluation outcome and live-collection error count.
- `collection-errors.jsonl`: timestamped collection failures, also printed in controller logs. Collection retries on the next pass without prompting or stopping the agent.

Capture samples saved files every two seconds, retains files stable during the read, and takes a final snapshot after Blender stops. It can miss rapid overwrites and cannot preserve unsaved Blender memory. It does not ask the agent to checkpoint or change its behavior. Final files remain final even if an earlier version looks better. Symlinks are excluded. The remote controller persists the batch summary at startup, commits received files during collection, and commits results after each harness finishes. It copies the existing checkpoint journals and verifies each new blob against its recorded SHA-256 before appending that journal row. Logs are copied by byte offset, preserving the raw stream even if a line is split across passes. On failure, already-collected versions and logs remain in `capture/`; they are not promoted to final artifacts or treated as a completed run. A controller or sandbox failure can still leave incomplete results. When possible, failed collection preserves a recovery archive.

## Independent views

Evaluation starts after the agent sandbox is terminated, in another sandbox with no Secrets and blocked networking. Blender opens the final scene with automatic script execution disabled. The evaluator never overwrites the saved scene or sends images back to the agent.

The evaluator frames visible geometry in the `Reconstruction` collection, including its child collections. If that collection is absent, it falls back to all visible geometry. Explicit object exclusions support older scenes; no name or size heuristics are used. Each view fits the projected bounds with a 15% margin. Selection and excluded objects are recorded in `views.json`. Geometry outside the selection is hidden only for these inspection renders. The evaluator replaces cameras, lights, world, and presentation settings, disables compositing and sequencing, and renders the positive and negative X/Y/Z directions orthographically. Axis names are literal; they do not assume models share a semantic front. Selected geometry and materials are retained. Current settings: 1024×1024, Cycles CPU, 32 samples with denoising, consistent neutral lighting and AgX color management. Rendering has a separate nine-minute process timeout. Use `--skip-evaluation` to collect the agent output without rendering these views.

These views support inspection, not an automated quality score. Missing/corrupt scenes and renderer failures are reported without substituting an earlier checkpoint. Provider-domain allowlists and harness permissions restrict downloads, but do not constitute a complete audit of content returned by allowed hosts.

To regenerate views from a saved run without invoking a model:

```sh
uv run python scripts/render_saved.py outputs/experiments/<batch>/<harness> --exclude-object Studio_Backdrop
```

Exclusion names must exactly match objects in that scene. This replaces the derived `evaluation/` views and writes `inspection-result.json`; the saved model and agent render remain unchanged. Back up earlier inspection views first if you want to retain them.

Blender startup disables Online Essentials catalog access while leaving localhost MCP available. Network allowlists remain in effect.
