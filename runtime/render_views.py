"""Render an existing scene from six axis-aligned views; never overwrite it."""
import json
from pathlib import Path
import argparse
import sys
import bpy
from mathutils import Vector

OUTPUT = Path('/evaluation')
OUTPUT.mkdir(exist_ok=True)
scene = bpy.context.scene
parser = argparse.ArgumentParser()
parser.add_argument('--exclude-object', action='append', default=[])
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
# Use the agreed collection, or explicit exclusions for older scenes. Never guess
# from an object's name or size: a large flat object may be part of the model.
collection = bpy.data.collections.get('Reconstruction')
selection = 'Reconstruction collection' if collection else 'all visible geometry'
members = set(collection.all_objects) if collection else set(scene.objects)
for name in args.exclude_object:
    if scene.objects.get(name) is None:
        raise ValueError(f'Excluded object does not exist: {name}')
geometry = [o for o in scene.objects if o.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'VOLUME'}
            and not o.hide_render and o in members and o.name not in args.exclude_object]
if not geometry:
    raise RuntimeError('No renderable geometry in saved scene')
excluded = [o.name for o in scene.objects if o.type in {'MESH', 'CURVE', 'SURFACE', 'META', 'FONT', 'VOLUME'}
            and not o.hide_render and o not in geometry]
for name in excluded:
    scene.objects[name].hide_render = True
depsgraph = bpy.context.evaluated_depsgraph_get()
points = [o.evaluated_get(depsgraph).matrix_world @ Vector(corner)
          for o in geometry for corner in o.evaluated_get(depsgraph).bound_box]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
center = (low + high) / 2
radius = max((p - center).length for p in points)
if radius <= 0:
    raise RuntimeError('Saved geometry has zero extent')
for obj in list(scene.objects):
    if obj.type in {'LIGHT', 'CAMERA'}:
        bpy.data.objects.remove(obj, do_unlink=True)
scene.world = bpy.data.worlds.new('Evaluation World')
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.18, 0.18, 0.18, 1)
background.inputs['Strength'].default_value = 0.7
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 32
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1024
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.render.use_compositing = False
scene.render.use_sequencer = False
scene.use_nodes = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
camera_data = bpy.data.cameras.new('Evaluation Camera')
camera_data.type = 'ORTHO'
camera_data.clip_start = radius * 0.001
camera_data.clip_end = radius * 20
camera = bpy.data.objects.new('Evaluation Camera', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
# World-axis labels do not assume a common semantic front/orientation across agents.
views = {'positive_x': (1, 0, 0), 'negative_x': (-1, 0, 0),
         'positive_y': (0, 1, 0), 'negative_y': (0, -1, 0),
         'positive_z': (0, 0, 1), 'negative_z': (0, 0, -1)}
lights = []
for name, energy, offset in [('Key', 5, (1, 1, 2)), ('Fill', 2, (-1, 0.3, 1))]:
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy * radius * radius * 10
    data.shape = 'DISK'
    data.size = radius * 3
    light = bpy.data.objects.new(name, data)
    scene.collection.objects.link(light)
    lights.append((light, Vector(offset)))
for name, direction in views.items():
    camera.location = center + Vector(direction) * radius * 4
    rotation = (center - camera.location).to_track_quat('-Z', 'Y')
    camera.rotation_euler = rotation.to_euler()
    projected = [rotation.inverted() @ (point - center) for point in points]
    width = max(p.x for p in projected) - min(p.x for p in projected)
    height = max(p.y for p in projected) - min(p.y for p in projected)
    camera_data.ortho_scale = max(width, height) * 1.15
    for light, offset in lights:
        light.location = center + rotation @ (offset * radius * 2)
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUTPUT / f'{name}.png')
    bpy.ops.render.render(write_still=True)
(OUTPUT / 'views.json').write_text(json.dumps({'views': views, 'center': list(center),
    'radius': radius, 'engine': 'CYCLES', 'samples': 32, 'resolution': [1024, 1024],
    'geometry': [o.name for o in geometry], 'selection': selection,
    'excluded_objects': excluded, 'framing_margin': 1.15}, indent=2))
