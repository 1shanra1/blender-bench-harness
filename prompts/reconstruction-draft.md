# Reconstruction prompt — draft

Create an editable 3D reconstruction in Blender of the object shown in the reference image at `/workspace/references/reference-01.png`. Inspect the image before modeling.

Match the object's shape, proportions, visible details, colors, and materials as closely as you can. Build a complete three-dimensional object that remains plausible from other angles; infer parts not visible in the reference. Reproduce visible markings where possible. Do not use the reference image or a crop of it as a texture, backdrop, or substitute for geometry.

Create the model and materials yourself using Blender MCP. Do not download or import external assets, search the web, or use image-generation services. Procedural materials and textures you create within Blender are allowed.

Only consider the task complete when the reconstructed object closely matches the reference in shape, proportions, visible details, colors, and materials. Inspect images of your work and compare them directly against the reference. Keep iterating, correcting discrepancies, and trying different modeling approaches until this condition is met. Include inspection from multiple angles to verify that the reconstruction is a coherent three-dimensional object.

Reconstruct only the object. Do not recreate the reference background, floor, shadows, or photographic setup. Use simple neutral lighting and a plain background to make the object's geometry and materials easy to inspect, with a camera angle similar to the reference for comparison.

Save your work to `/workspace/output/scene.blend` as you progress and before finishing. Keep any required resources packed in the file. Save a final render to `/workspace/output/render.png`.

## Shared environment note

Put all reconstructed object parts in a collection named `Reconstruction`. Keep any presentation geometry outside that collection so independent inspection renders can frame the object from different angles.

Save Python scripts that Blender needs to execute in `/workspace/scripts`, which is accessible to both the CLI and Blender in this run. Keep those files readable by the `blender` user; private harness folders under `/root` are not accessible to Blender.

Blender is running and connected to the official Blender MCP server. Use its tools to inspect and modify the scene. To visually inspect work, save a PNG and open it with your image-reading tool. Direct MCP screenshots return black images on this display. For a viewport preview, `bpy.ops.render.opengl(write_still=True, view_context=True)` works when called with a `VIEW_3D` area and `WINDOW` region context override. Standard scene rendering is also available.
