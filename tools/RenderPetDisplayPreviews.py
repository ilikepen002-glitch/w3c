"""Blender rendering of newly parsed final MDX poses and exact decoded BLP pixels.
Run with: blender -b -t 2 --python tools/RenderPetDisplayPreviews.py -- INPUT_MODEL_DIR OUTPUT_DIR
This is an offline art preview, never a Warcraft/tower/FPS verification.
"""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
source, output = map(Path, args[:2])
cast_only = '--cast-only' in args
large = '--large' in args
output.mkdir(parents=True, exist_ok=True)
data = json.loads((source / 'sampled-mdx-frames.json').read_text())
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
image = bpy.data.images.new('Exact approved BLP atlas', 256, 256, alpha=True)
rgba = (source / 'original/palette-decoded.rgba').read_bytes()
image.pixels = [v / 255 for y in reversed(range(256)) for v in rgba[y * 1024:(y + 1) * 1024]]
image.pack()
material = bpy.data.materials.new('Original opaque atlas')
material.use_nodes = True
bsdf = material.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Roughness'].default_value = 1
bsdf.inputs['Specular IOR Level'].default_value = 0
texture = material.node_tree.nodes.new('ShaderNodeTexImage')
texture.image = image
texture.interpolation = 'Linear'
material.node_tree.links.new(texture.outputs['Color'], bsdf.inputs['Base Color'])
objects = []
for g in data['frames'][0]['geosets']:
    mesh = bpy.data.meshes.new('Newly parsed MDX geometry')
    mesh.from_pydata([g['vertices'][i:i + 3] for i in range(0, len(g['vertices']), 3)], [],
                     [g['faces'][i:i + 3] for i in range(0, len(g['faces']), 3)])
    mesh.update()
    obj = bpy.data.objects.new('MDX spirit', mesh)
    bpy.context.collection.objects.link(obj)
    mesh.materials.append(material)
    uv = mesh.uv_layers.new()
    for poly in mesh.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            uv.data[li].uv = (g['uv'][vi * 2], 1 - g['uv'][vi * 2 + 1])
    objects.append(obj)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16 if large else 8
scene.cycles.use_denoising = False
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'Medium High Contrast'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.32, .38, .46, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .75
bpy.ops.object.light_add(type='AREA', location=(50, -90, 170))
bpy.context.object.data.energy = 220000
bpy.context.object.data.size = 130
bpy.ops.object.camera_add(location=(145, -210, 140))
camera = bpy.context.object
camera.rotation_euler = (Vector((-5, 0, 36)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 220
scene.camera = camera
scene.render.resolution_x = 512 if large else 256
scene.render.resolution_y = 448 if large else 224
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
for frame in data['frames']:
    if cast_only and frame['sequence'] != 'Display Cast':
        continue
    for obj, g in zip(objects, frame['geosets']):
        for i, vertex in enumerate(obj.data.vertices):
            vertex.co = g['vertices'][i * 3:i * 3 + 3]
        obj.data.update()
        if hasattr(obj.data, 'normals_split_custom_set_from_vertices'):
            obj.data.normals_split_custom_set_from_vertices([g['normals'][i:i + 3] for i in range(0, len(g['normals']), 3)])
    scene.render.filepath = str(output / (frame['sequence'].replace(' ', '-') + f"-{frame['index']:02d}.png"))
    bpy.ops.render.render(write_still=True)
