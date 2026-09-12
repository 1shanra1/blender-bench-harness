"""Export GLB 3D models from scene.blend for experiment runs.

Filters out studio backdrops, ground planes, shadow catchers, and helper cutters,
matching the exact geometry evaluation logic in render_views.py and views.json.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS_DIR = ROOT / "outputs" / "experiments"
BLENDER_PATH = "/opt/homebrew/bin/blender"

BLENDER_EXPORT_SCRIPT = """
import bpy
import json
import sys
from pathlib import Path

output_path = sys.argv[-1]
run_dir = Path(output_path).parent.parent
views_file = run_dir / 'evaluation' / 'views.json'

valid_names = None
if views_file.is_file():
    try:
        data = json.loads(views_file.read_text())
        if isinstance(data.get('geometry'), list) and data['geometry']:
            valid_names = set(data['geometry'])
    except Exception:
        pass

if valid_names is None:
    collection = bpy.data.collections.get('Reconstruction')
    members = set(collection.all_objects) if collection else set(bpy.context.scene.objects)
    excluded_names = {'Studio_Backdrop', 'Ground_Shadow_Catcher', 'Backdrop', 'Plane', 'Floor'}
    valid_names = {
        o.name for o in bpy.context.scene.objects
        if o.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'VOLUME'}
        and not o.hide_render
        and o in members
        and o.name not in excluded_names
        and not o.name.startswith('Belt_Clip_Window_Cutter')
    }

bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
    if o.name in valid_names:
        o.select_set(True)
    else:
        o.select_set(False)

selected = [o.name for o in bpy.context.selected_objects]
if not selected:
    print('No renderable geometry selected for GLB export', file=sys.stderr)
    sys.exit(1)

bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    use_selection=True,
    export_apply=True
)
print(f'Exported GLB with {len(selected)} objects to: {output_path}')
"""


def export_run(run_dir: Path, blender_path=BLENDER_PATH):
    blend_file = run_dir / "capture" / "artifacts" / "scene.blend"
    if not blend_file.is_file():
        blend_file = run_dir / "live-backup" / "scene.blend"
        if not blend_file.is_file():
            print(f"[-] No scene.blend in {run_dir.name}")
            return False

    eval_dir = run_dir / "evaluation"
    eval_dir.mkdir(parents=True, exist_ok=True)
    out_glb = eval_dir / "scene.glb"

    cmd = [
        blender_path,
        "--background",
        "--factory-startup",
        "--disable-autoexec",
        str(blend_file),
        "--python-expr",
        BLENDER_EXPORT_SCRIPT,
        "--",
        str(out_glb),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=600)
        size_kb = out_glb.stat().st_size / 1024
        print(f"[+] Exported {run_dir.parent.name}/{run_dir.name}: {out_glb.name} ({size_kb:.1f} KB)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to export {run_dir}: {e.stderr}", file=sys.stderr)
        return False


def main():
    target_dirs = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            target_dirs.append(Path(arg).resolve())
    else:
        for batch in sorted(EXPERIMENTS_DIR.glob("*")):
            if not batch.is_dir():
                continue
            for harness in ("codex", "cursor", "antigravity", "claude"):
                h_dir = batch / harness
                if h_dir.is_dir():
                    target_dirs.append(h_dir)

    successes = 0
    for target in target_dirs:
        if export_run(target):
            successes += 1

    print(f"\nDone: {successes} GLB models exported.")


if __name__ == "__main__":
    main()
