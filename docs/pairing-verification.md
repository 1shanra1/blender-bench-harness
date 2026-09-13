# Model–harness pairing verification

These notes record compatibility checks beginning September 8, 2026, with later checks below. Reconstruction experiments have since been published at [meshmatch.net](https://meshmatch.net); see the [current experiment matrix](../README.md#the-published-experiments). A passing compatibility check establishes basic image/tool transport and goal behavior, not reconstruction quality.

## Initial Gemini 3.8 Flash High checks

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
- The experiment runner enforces a 90-minute agent limit. Compatibility checks have a separate short timeout.

Harness permission implementations and model-serving routes differ; this standardizes the Blender environment and supplied inputs, not the harness internals. Legacy `*_smoke.py` scripts retain their original smaller resource settings.

## Reproduce the checks

### Claude Code

Verified September 11, 2026: Claude Code 2.1.268 with Gemini 3.8 Flash through Vercel read the reference, inspected Blender through MCP, saved and read a viewport image, and received a native achieved-goal verdict. It exited successfully after 46 seconds with no permission denials. Local evidence: `outputs/pairing-verification/claude-20260911T141118Z/` (ignored by Git).

A short scene-editing check also passed on September 12, 2026 (UTC): the same pairing created a rough kettle body, lid, and handle, adjusted the handle, saved the scene, inspected its viewport preview, and completed its native goal in 204 seconds with no permission denials. This was a deliberately reduced objective, not a full reconstruction benchmark. Logs, goal verdict, and viewport evidence: `outputs/pairing-verification/claude-20260912T034345Z/` (ignored by Git). The disposable sandbox was terminated after collection; the saved Blender scene was not downloaded.

`scripts/claude_setup.py` installs official Claude Code 2.1.268 for Linux x64 and verifies the published SHA-256. The `claude` pairing reuses the existing `blender-bench-vercel-auth` Modal Secret (`AI_GATEWAY_API_KEY`), so it needs no separate Claude account login. Configuration and conversation state are created inside each fresh sandbox.

```sh
uv run python scripts/claude_setup.py
uv run python scripts/verify_pairings.py claude
```

The first command checks installation without model calls. The second consumes model usage and checks both image reads, Blender MCP, and the native `/goal` verdict. It preserves `claude-transcript.jsonl` and `bench-native-result.json` alongside the event log. See the [native goal documentation](https://code.claude.com/docs/en/goal) and [Vercel endpoint configuration](https://vercel.com/docs/ai-gateway/coding-agents/claude-code).

The driver uses Vercel's `/claude-code` endpoint and disables experimental API betas. Gemini also needs `CLAUDE_CODE_MODEL_CAPABILITIES=google/gemini-3.8-flash=-mid_conv_system`: otherwise the CLI sends system messages mid-conversation and the provider rejects the request. This native setting was checked in the pinned CLI's implementation; it is not documented in the public configuration reference. Keep the version pinned and recheck compatibility when upgrading. The driver records these settings in `bench-native-result.json`; the CLI binary and native goal loop are unmodified.

### Existing pairings

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

## Kimi Code CLI

Pinned official Linux binary: **0.42.0**, verified against the release manifest's SHA-256. Each sandbox creates its own configuration and uses the existing `blender-bench-vercel-auth` Modal Secret. No Kimi subscription or host configuration is imported.

Verified September 12, 2026 (UTC):

| Model | Vercel API / Kimi provider type | Check |
| --- | --- | --- |
| Gemini 3.8 Flash High | Responses / `openai_responses` | Correctly identified the kettle, inspected Blender, saved and read a viewport, and completed its native goal in 32 seconds. |
| Kimi K3 High | Chat Completions / `openai` | Correctly identified the kettle, changed cube geometry and material, edited its width, saved the scene, read the viewport, and completed its native goal in 31 seconds. |

Local evidence (Git-ignored): `outputs/pairing-verification/kimi-20260912T052724Z/` and `outputs/pairing-verification/kimi-20260912T053403Z/`. The editing check also preserves `scene.blend`.

```sh
uv run python scripts/kimi_setup.py
uv run python scripts/verify_pairings.py kimi
uv run python scripts/verify_pairings.py kimi --model moonshotai/kimi-k3
```

`--objective-file PATH` accepts a small custom compatibility objective. This check expects the reference and `/workspace/viewport.png` to be read. It does not run the reconstruction benchmark.

The driver submits one `kimi -p "/goal ..."` command. Completion requires both exit code zero and a native `goal.summary` with `status=complete`. MCP calls have a ten-minute timeout. The shared supervisor applies the 90-minute run limit and collector interval of 120 seconds. The native wire transcript preserves reasoning and per-request usage, while the normal stream preserves tool results and image payloads. A goal summary's `tokensUsed` is not a total-input token metric.

Protocol choice matters: Gemini's Chat Completions check returned HTTP 400 after image reading. Kimi K3 misidentified the reference through Responses, Messages, and the `kimi` adapter; one of these checks declared completion despite incorrect visual identification. A direct image request correctly identified it. The generic `openai` adapter, which moves tool images into user messages, then passed the editing check. These failed routes are not verified pairings.

Both launch commands accept `--model PROVIDER/MODEL` for Vercel-backed harnesses. This selects the requested model without mutating shared pairing defaults. Kimi K3 in Codex and Claude Code failed the visual compatibility checks below; adding a model override does not establish compatibility.

References: [installation](https://www.kimi.com/code/docs/en/kimi-code-cli/guides/getting-started.html), [providers](https://www.kimi.com/code/docs/en/kimi-code-cli/configuration/providers), [native goals](https://www.kimi.com/code/docs/en/kimi-code-cli/guides/goals.html).

### Kimi K3 in Codex and Claude Code

Small editing checks on September 12, 2026 (UTC) failed visual compatibility through the existing Vercel endpoints. Both harnesses read the same kettle reference, edited the default cube and its material through MCP, saved `scene.blend`, and read a viewport image. Codex identified the kettle as a yellow bus; Claude Code identified it as a pencil. These are failed pairings despite successful Blender operations.

Codex used `/codex/v1` (Responses) and reported native goal status `complete`, then continued through context compaction and eventually completed its turn. Our explicit sandbox termination raced with the check’s final artifact collection, causing a collection error; the earlier evidence copy preserved the scene, viewport, and logs. Its reported per-request input jumped from 12,846 to 149,282 after the reference read, then to 459,750 after the viewport read. This is consistent with incorrect image-to-text conversion, but the precise conversion boundary has not been isolated. Claude Code used `/claude-code` (Messages). Its original parsed result incorrectly reported no goal verdict because the objective ended in a newline. Rechecking the saved transcript after fixing whitespace matching confirmed native goal completion, despite the incorrect image identification. Further work on these routes was stopped after preserving evidence.

Local evidence (Git-ignored): `outputs/pairing-verification/codex-20260912T053927Z/` and `outputs/pairing-verification/claude-20260912T053928Z/`. Both include logs, the viewport, and the saved scene. Kimi Code with generic Chat Completions remains the verified Kimi K3 pairing. Do not launch Kimi K3 reconstruction benchmarks through Codex or Claude Code until image transport is fixed and rechecked.

### GPT-5.6 Luna in Kimi Code and Claude Code

Verified September 12, 2026 (UTC), using `openai/gpt-5.6-luna` with High effort through Vercel. Both harnesses correctly identified the kettle reference, inspected Blender, read a viewport preview, and completed their native goals. Follow-up editing checks created a tall yellow block, changed its width, saved `scene.blend`, inspected the preview, and completed natively: Kimi Code took 75 seconds; Claude Code took 69 seconds. A subsequent Codex check through Vercel also passed; see below.

Kimi Code uses the existing Responses adapter. It initially interpreted crop dimensions as normalized coordinates and requested a one-pixel image, then corrected the request itself. Claude Code recovered from an invalid empty `pages` argument. These were model tool-use mistakes, not provider image-transport failures.

The Claude editing check exposed a parser bug: `/goal` trims surrounding objective whitespace, while our parser required an exact match including the prompt file's trailing newline. The parser now trims surrounding whitespace on both sides. Replaying the saved transcript verified the successful native verdict without another API call. Original results remain preserved alongside `goal-reassessment.json`; the same correction was applied to the earlier Kimi K3 transcript, whose visual identification still failed.

Local evidence (Git-ignored): `kimi-20260912T055231Z/`, `claude-20260912T055232Z/`, `kimi-20260912T055319Z/`, and `claude-20260912T055319Z/` under `outputs/pairing-verification/`. These checks establish basic compatibility, not full reconstruction quality.

### GPT-5.6 Luna in Codex through Vercel

Verified September 12, 2026 (UTC): Codex selected `openai/gpt-5.6-luna` with High reasoning through `/codex/v1` using the existing Vercel API credential. It correctly identified the kettle, inspected the default scene through Blender MCP, saved and read a viewport preview, confirmed unchanged geometry, and completed its native goal. The check exited successfully and its sandbox was terminated. This was an inspection check, not a reconstruction or geometry-editing run.

Evidence: `outputs/pairing-verification/codex-20260912T060829Z/` (Git-ignored), including events, native completion result, and viewport. All six Gemini/Luna pairings across Codex, Claude Code, and Kimi Code now have basic compatibility evidence through Vercel; no Codex subscription credentials are needed for these pairings.
