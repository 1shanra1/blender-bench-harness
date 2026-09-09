# Reconstruction runs

Each selected harness gets a new Modal sandbox, its own credential Secret, the same reference image and approved prompt, and the shared Blender environment. No histories, output directories, or volumes are shared between agents. Codex uses Gemini 3.8 Flash through Vercel; Cursor and Antigravity select their native Gemini 3.8 Flash High entries.

Preview without creating sandboxes or calling models:

```sh
uv run python scripts/run_experiment.py --harness codex cursor antigravity --dry-run
```

Remove `--dry-run` to run those harnesses concurrently. Select only the desired harness names; each invocation produces one independent run per selected harness. This consumes provider credits. Existing harness authentication and Modal setup are prerequisites; see [setup verification](pairing-verification.md).

## Lifecycle

Cursor CLI 2026.09.02-c22c1a3 is patched at image build time to give MCP tool calls a 600-second timeout. `runtime/patch_cursor_timeout.py` checks the original bundle hash and changes only the SDK call's timeout option. Run manifests identify this as `mcp-tool-timeout-600s-v1`; native goal behavior is unchanged. The first drill batch predates this patch.

The runner stages `prompts/reconstruction-draft.md` unchanged and submits it once through each harness's native goal interface. The previously verified goal drivers are reused, with smoke-only viewport assertions disabled. They still require native goal completion. There is no custom continuation or feedback loop.

The supervisor starts the 75-minute clock when it launches the harness driver, including CLI startup. On process exit or timeout it terminates the remaining driver process group, stops Blender, and collects artifacts. Setup and collection have additional sandbox lifetime; they do not extend the agent's deadline. A successful process exit without native completion is not recorded as goal completion. A completed goal does not imply that the saved artifacts are valid or match the reference.

## Outputs

Each invocation writes a unique directory under ignored `outputs/experiments/`, with a subdirectory per harness:

- `manifest.json`, `prompt.md`: exact submitted prompt, input hashes, requested model/effort, versions, resources, and sandbox ID.
- `capture/result.json`: native completion, deadline/exit information, and required artifact presence.
- `capture/artifacts/`: final files from `/workspace/output/`, including the agent's scene and chosen render.
- `capture/versions/` and `capture/trajectory.jsonl`: saved file versions indexed by SHA-256, original path, and observation time.
- `capture/*events.jsonl` and logs: full streams exposed by the CLIs, including available usage data. Antigravity may abbreviate tool arguments; these are not complete operating-system audits.
- `evaluation/`: independent renders and camera metadata. `evaluation.log` records renderer errors.
- `result.json`: run outcome plus evaluation outcome.

Capture samples saved files every two seconds, retains files stable during the read, and takes a final snapshot after Blender stops. It can miss rapid overwrites and cannot preserve unsaved Blender memory. It does not ask the agent to checkpoint or change its behavior. Final files remain final even if an earlier version looks better. Symlinks are excluded. Keep the local controller running through collection; a controller or sandbox failure can leave incomplete results. When possible, failed collection preserves a recovery archive.

## Independent views

Evaluation starts after the agent sandbox is terminated, in another sandbox with no Secrets and blocked networking. Blender opens the final scene with automatic script execution disabled. The evaluator never overwrites the saved scene or sends images back to the agent.

All visible geometry is framed together, including any unwanted floor/backdrop the agent saved. The evaluator replaces cameras, lights, world, and presentation settings, disables compositing and sequencing, and renders the positive and negative X/Y/Z directions orthographically. Axis names are literal; they do not assume models share a semantic front. Materials and geometry are retained. Current settings: 1024×1024, Cycles CPU, 32 samples with denoising, consistent neutral lighting and AgX color management. Rendering has a separate nine-minute process timeout. Use `--skip-evaluation` to collect the agent output without rendering these views.

These views support inspection, not an automated quality score. Missing/corrupt scenes and renderer failures are reported without substituting an earlier checkpoint. Provider-domain allowlists and harness permissions restrict downloads, but do not constitute a complete audit of content returned by allowed hosts.
