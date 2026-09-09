# Gemini 3.8 Flash High setup verification

Verified September 8, 2026. No reconstruction experiments have been run.

| Harness | Requested model | Result |
| --- | --- | --- |
| Codex CLI 0.153.4 via OpenRouter | `google/gemini-3.8-flash`, High effort | Not compatible in this check: Google HTTP 400 after image viewing. |
| Codex CLI 0.153.4 via Vercel AI Gateway | `google/gemini-3.8-flash`, High effort | Passed: identified the drill image, used Blender MCP, viewed the viewport, and completed native `/goal`. |
| Cursor CLI 2026.09.02-c22c1a3 | `gemini-3.8-flash-high` | Passed: identified the drill image, used Blender MCP, viewed the viewport, and completed native `/goal`. |
| Antigravity CLI 1.1.27 | `gemini-3.8-flash-high` | Passed: identified the drill image, used Blender MCP, viewed the viewport, and completed native `/goal`. |

With OpenRouter, Codex confirmed the requested model and `high` reasoning effort. Its image-view tool opened the reference, but the next provider request failed with `Requests ending with a model turn are not supported.` This does **not** verify that Gemini received the image through OpenRouter. The OpenRouter model-catalog response also produced a metadata-decoding warning. No custom adapter or continuation loop was added.

A standalone Responses API diagnostic reproduced the failure without Codex or Blender: text tool output succeeded, but image tool output failed. Direct image input in a new request succeeded. Moving the image into a subsequent user message did not resolve the tool-history failure. Google returned the same model-turn error; fallback to Google AI Studio returned `Corrupted thought signature.` This localizes the blocker to the OpenRouter/Gemini conversation-translation path, not Blender or authentication. No configuration-only fix has been verified. Diagnostic scripts and responses are saved under ignored `outputs/openrouter-diagnostic/`.

The refreshed authenticated Cursor catalog lists Gemini 3.8 Flash Low, Medium, and High. The check confirmed `Gemini 3.8 Flash High` in the CLI initialization event. All three harnesses now pass the compatibility check, with Codex routed through Vercel. No substitute model was selected.

The successful Vercel check is saved at `outputs/pairing-verification/codex-20260908T060008Z`. It confirmed both image-view events, successful Blender MCP calls, native goal completion, and a normal default-scene viewport PNG. This account required card verification and paid credits before requests could run.

## Shared setup

`scripts/shared_sandbox.py` defines the environment used by `scripts/verify_pairings.py`:

- Fresh Modal sandbox and harness home for every check, with only that harness's credential Secret.
- Same pinned Blender 5.2.1 and official MCP revision from `scripts/environment.py`.
- CPU request and ceiling: 4 cores. RAM request and ceiling: 8192 MiB. These provide more headroom than the earlier cube smoke checks; they are not a measured recommendation for complex rendering.
- CPU software OpenGL, identical 1280×800 virtual display, factory startup scene.
- Blender runs as a separate user with a clean environment, excluding provider credentials.
- Same original reference at `/workspace/references/reference-01.png` and approved prompt at `/workspace/task.md`, with matching SHA-256 hashes. The reference and prompt are read-only to the Blender user.
- Same output path `/workspace/output/`; no other runs' files, volumes, or histories are mounted.
- Provider-specific network allowlists are necessary for authentication/inference. Antigravity also requires its Google profile-image host. These are domain-level restrictions, not a complete asset-download audit.
- The experiment runner enforces a 45-minute agent limit. Compatibility checks have a separate short timeout.

Harness permission implementations and model-serving routes differ; this standardizes the Blender environment and supplied inputs, not the harness internals. Legacy `*_smoke.py` scripts retain their original smaller resource settings.

## Reproduce the checks

```sh
uv run python scripts/check_model_catalogs.py cursor
uv run python scripts/check_model_catalogs.py openrouter
uv run python scripts/check_model_catalogs.py antigravity
uv run python scripts/verify_pairings.py cursor
uv run python scripts/verify_pairings.py antigravity
uv run python scripts/verify_pairings.py codex
```

`verify_pairings.py codex` checks Vercel AI Gateway using the `blender-bench-vercel-auth` Modal Secret (`AI_GATEWAY_API_KEY`). Its configuration uses Vercel's [documented Codex endpoint](https://vercel.com/docs/ai-gateway/coding-agents/openai-codex), requests High effort, and supplies no alternative-model fallback list. Image-tool compatibility passed; gateway account routing rules have not been independently audited.

`verify_pairings.py codex --codex-provider openrouter` reproduces the failing OpenRouter pairing. Both checks consume model usage. `verify_pairings.py cursor` refuses to substitute another model when 3.8 Flash High is absent from the saved catalog.

The compatibility objective asks only for reference identification and default-scene inspection. The approved reconstruction prompt is staged but not submitted. Logs and images remain in ignored `outputs/pairing-verification/` directories. The separate [experiment runner](experiments.md) collects saved-file versions and renders independent multiview images.
