# Blender Bench Harness

How far does a vision-capable model, operating through a coding harness's native goal mode, get when reconstructing a 3D object from reference images before it considers the task finished?

Status: experiment design only. No runner, installations, or experiment runs yet.

## Agreed experiment

- Use each harness's built-in `/goal` or equivalent. No custom continuation wrappers, hooks, or follow-up prompts.
- Submit one task; allow the harness's native internal continuation behavior to run.
- Stop when the native goal/session reliably reports completion, or at a 45-minute wall-clock limit. Start the experiment clock when the task is submitted after environment readiness; provisioning is separate.
- Detect completion externally. Do not require the model to emit benchmark status labels or bookkeeping. An intermediate turn ending is not necessarily goal completion. Verify the actual terminal signal for each harness; silence alone is not completion.
- Capture trajectory externally: available tool events, images, scene checkpoints, timing, and usage. Checkpoint mechanics remain to be implemented without introducing agent hooks or continuation logic.
- Automatically render final saved scenes from multiple angles outside the agent's session. Preserve the agent's own output too. Evaluation renders do not count toward the agent's time limit.
- Run remotely on Modal with an isolated environment per run. Agents cannot access other runs' work, artifacts, or histories.
- Ban asset downloads. Preinstall dependencies and enforce runtime network restrictions while preserving required inference and authentication access.
- Use the official [Blender Lab MCP server](https://www.blender.org/lab/mcp-server/) ([source](https://projects.blender.org/lab/blender_mcp)).
- The user selects references, pairings, and repetition counts. No experiment size is assumed.
- Verification is a small smoke check of native goal execution, visual feedback, and completion detection. No major test suite.

Candidate harnesses: Codex, Claude Code, Cursor, Devin CLI, and Antigravity. Exact model availability and unattended native goal behavior remain to be verified per installed version.

## How the agent sees its work

Blender scene data describes geometry, materials, and transforms. Visual inspection additionally requires an image delivered to the model.

- A viewport screenshot shows the current interactive view without requiring a full camera render.
- A quick thumbnail render allows a cheaper rendered preview.
- A full render shows the scene using its camera, lighting, materials, and render settings.

The Blender MCP tool interface available during project setup exposes area/window screenshots and thumbnail rendering. The remote installation still needs a smoke check that image content reaches each model. A saved image path alone does not mean the model saw the image.

For viewport screenshots, plan on Blender with a virtual display in the remote container, subject to a small compatibility check. Pure background rendering is also possible in Blender, but does not provide an interactive viewport to screenshot.

## Setup to discuss before installing

- Local: a project virtual environment containing the Modal SDK/CLI, used only for provisioning and collecting remote runs.
- Authentication: Modal browser login and supported authentication for each selected CLI; keep credentials out of repository files and container images.
- Remote image: Blender, the official MCP server and add-on, selected harness binaries, and required graphics/display dependencies. The official MCP installation page currently specifies Blender 5.1 or newer.
- Inputs: user-selected reference images and initial harness/model pairing.

No local Blender experiment is required. No dependencies have been installed by this project.

## Next implementation step

After setup choices and authentication, establish a remote native-goal smoke check with visual feedback and a reliable completion signal. Expand the experiment only under user direction.
