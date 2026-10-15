"""Blender renders exact newly parsed final MDX geometry and exact BLP pixels."""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(sys.argv[sys.argv.index('--')+1]); rows=json.loads((ROOT/'evidence/water-earth-hashes.json').read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=False
scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast'
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.30,.35,.42,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.8
bpy.ops.object.light_add(type='AREA',location=(50,-90,170));bpy.context.object.data.energy=180000;bpy.context.object.data.size=130
bpy.ops.object.camera_add(location=(145,-210,140));camera=bpy.context.object;camera.rotation_euler=(Vector((-5,0,34))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=205;scene.camera=camera
scene.render.resolution_x=512;scene.render.resolution_y=448;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG'
for row in rows:
 model=row['model'];d=ROOT/'evidence'/model
 for kind in ['before','after']:
  image=bpy.data.images.new(model+kind,256,256,alpha=True);rgba=(d/(kind+'.rgba')).read_bytes();image.pixels=[v/255 for y in reversed(range(256)) for v in rgba[y*1024:(y+1)*1024]];image.pack()
  material=bpy.data.materials.new(model+kind);material.use_nodes=True;bsdf=material.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=1
  if 'Specular IOR Level' in bsdf.inputs:bsdf.inputs['Specular IOR Level'].default_value=0
  texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image;texture.interpolation='Linear';material.node_tree.links.new(texture.outputs['Color'],bsdf.inputs['Base Color'])
  data=json.loads((d/(kind+'-frames.json')).read_text());objects=[]
  for g in data['frames'][0]['geosets']:
   mesh=bpy.data.meshes.new('Actual MDX mesh');mesh.from_pydata([g['vertices'][i:i+3] for i in range(0,len(g['vertices']),3)],[],[g['faces'][i:i+3] for i in range(0,len(g['faces']),3)]);mesh.update();obj=bpy.data.objects.new('Actual MDX '+model,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(material);uv=mesh.uv_layers.new()
   for poly in mesh.polygons:
    poly.use_smooth=True
    for li in poly.loop_indices:
     vi=mesh.loops[li].vertex_index;uv.data[li].uv=(g['uv'][vi*2],1-g['uv'][vi*2+1])
   objects.append(obj)
  for frame in data['frames']:
   if kind=='before' and frame['index']!=0:continue
   for obj,g in zip(objects,frame['geosets']):
    for i,v in enumerate(obj.data.vertices):v.co=g['vertices'][i*3:i*3+3]
    obj.data.update()
    if hasattr(obj.data,'normals_split_custom_set_from_vertices'):obj.data.normals_split_custom_set_from_vertices([g['normals'][i:i+3] for i in range(0,len(g['normals']),3)])
   scene.render.resolution_percentage=100 if frame['index']==0 else 60
   scene.render.filepath=str(d/(kind+'-'+frame['sequence'].replace(' ','-')+'-'+str(frame['fraction'])+'.png'));bpy.ops.render.render(write_still=True)
  for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
  bpy.data.images.remove(image);bpy.data.materials.remove(material)
