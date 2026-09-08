# Blender Bench Harness

A benchmark exploring how well vision models reconstruct 3D objects from reference images using coding agents and the [official Blender MCP server](https://www.blender.org/lab/mcp-server/).

Each model–harness pairing uses its native goal mode to build, inspect, and refine a Blender scene until it finishes or reaches a 45-minute limit. Runs are designed for isolated Modal environments, with no asset downloads. Scene checkpoints and renders from multiple angles capture progress and final quality.

Early development; the benchmark runner is not yet implemented.

## Setup

```sh
uv sync
uv run modal setup
uv run python scripts/modal_smoke.py
```

The smoke check starts a temporary CPU sandbox on Modal, verifies remote execution, and terminates it.

Build and check the Blender environment:

```sh
uv run python scripts/blender_smoke.py
```

Uses Blender 5.2.1 and a pinned official MCP revision. Saves a viewport preview to `outputs/viewport.png`, then terminates the sandbox. Runtime outbound networking is blocked.

Direct MCP screenshots return black images under this software display. The check uses Blender's viewport-render operation through MCP instead; agents will need to open the resulting PNG with their image-reading tool. The official server requires MCP SDK 1.x.
