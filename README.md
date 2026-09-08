# Blender Bench Harness

A benchmark exploring how well vision models reconstruct 3D objects from reference images using coding agents and the [official Blender MCP server](https://www.blender.org/lab/mcp-server/).

Each model–harness pairing uses its native goal mode to build, inspect, and refine a Blender scene until it finishes or reaches a 45-minute limit. Runs are designed for isolated Modal environments, with no asset downloads. Scene checkpoints and renders from multiple angles capture progress and final quality.

Early development; the benchmark runner is not yet implemented.
