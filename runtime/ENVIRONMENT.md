# Available environment

Blender is already running and connected through the official Blender MCP server.
Use MCP to inspect and modify that scene. Save previews or renders as PNGs and
open them with the harness's image-reading tool.

## Python

There are two separate Python environments:

- **Shell Python (`python`, Python 3.12):** image analysis, calculations, and file
  processing. Installed libraries: Pillow (`PIL`), NumPy, SciPy, SymPy,
  Matplotlib, OpenCV (`cv2`), scikit-image (`skimage`), trimesh, Shapely, Rtree,
  NetworkX, and manifold3d. `uv` is also available.
- **Blender Python (through MCP):** `bpy` accesses the live scene, geometry,
  materials, cameras, and rendering. Shell Python cannot import `bpy`, and the
  shell libraries listed above are not necessarily installed in Blender Python.
  Exchange data through files in `/workspace/scripts` or `/workspace/output`.

## Shell tools

- Files and text: Bash, coreutils, find, grep, sed, awk, rg, jq, file, Git,
  tar, gzip, xz, zip, unzip, and curl.
- Images and video: ImageMagick (`identify`, `convert`), ffmpeg, and ffprobe.
- Processes and resources: ps, top, free, pgrep, pstree, lsof, and `/usr/bin/time`.
- Building code: GCC, G++, make, and pkg-config.

Use `python` directly to access the preinstalled libraries; a fresh `uv` virtual
environment does not inherit them. Library versions are available through
`python -m pip list` and each command's version option.

## Files and access

The reference is `/workspace/references/reference-01.png`. Put shared scripts in
`/workspace/scripts` and saved models/renders in `/workspace/output`. Blender runs
as the `blender` user; keep shared files readable by that user. It cannot read
private harness files under `/root`.

The installed tools do not grant internet access. Provider connections are
allowlisted; external assets, web searches, and image-generation services remain
disallowed. Create geometry and materials yourself using Blender MCP.
