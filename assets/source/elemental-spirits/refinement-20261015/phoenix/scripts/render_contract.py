"""Blender 4.3 offline true-mesh preview, no game code or source mutation.
Examples:
 blender -b -t 4 --python scripts/render_phoenix.py -- --mode quick --team crimson
 blender -b -t 4 --python scripts/render_phoenix.py -- --mode quick --team blue
 blender -b -t 4 --python scripts/render_phoenix.py -- --mode bake --fps 24
Flags --body/--head select new artwork PNGs. G4 cutout, G5–7 teamcolor compositing,
G8 opaque. Mesh deformation is evaluated from original BONE+HELP track data.
"""
import sys,json,math,argparse,hashlib
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));from mdx_decode import decode,Evaluator,ROOT,DEFAULT_SOURCE
p=argparse.ArgumentParser();p.add_argument('--source',default=str(DEFAULT_SOURCE));p.add_argument('--body',default=str(ROOT/'textures/PhoenixBody.png'));p.add_argument('--head',default=str(ROOT/'textures/PhoenixHead.png'));p.add_argument('--team',choices=['crimson','blue'],default='crimson');p.add_argument('--mode',choices=['quick','stage','bake','clips','turntable'],default='quick');p.add_argument('--fps',type=int,default=24);p.add_argument('--resolution',type=int,default=960);p.add_argument('--output',default=None);p.add_argument('--samples',type=int,default=8);p.add_argument('--times',nargs='+',type=float,default=None);p.add_argument('--fit',action='store_true');p.add_argument('--diagnostic',default=None);p.add_argument('--quick-frames',type=int,default=3);p.add_argument('--quick-views',nargs='+',default=['hero','top','side','front'])
args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--'in sys.argv else []);out=Path(args.output)if args.output else ROOT/'previews'/args.team;out.mkdir(parents=True,exist_ok=True)
d=decode(args.source);ev=Evaluator(d)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=args.samples;scene.cycles.use_denoising=False;scene.cycles.max_bounces=4;scene.cycles.transparent_max_bounces=12;scene.render.resolution_x=args.resolution;scene.render.resolution_y=int(args.resolution*.8);scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=False;scene.render.fps=args.fps;scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast' if False else 'None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
world=bpy.data.worlds.new('Neutral dark technical preview');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.012,.016,.024,1);world.node_tree.nodes['Background'].inputs[1].default_value=1;scene.world=world
body=bpy.data.images.load(str(Path(args.body).resolve()),check_existing=True);head=bpy.data.images.load(str(Path(args.head).resolve()),check_existing=True);body.colorspace_settings.name='sRGB';head.colorspace_settings.name='sRGB';body.pack();head.pack();diagnostic=bpy.data.images.load(str(Path(args.diagnostic).resolve()),check_existing=True) if args.diagnostic else None
if diagnostic:diagnostic.colorspace_settings.name='sRGB';diagnostic.pack()
# Team colors are explicit preview values, not claims of an exact WC3 TeamColor texture sample.
team_srgb=(.62,.012,.025)if args.team=='crimson'else(.012,.12,.85)
def linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
team=tuple(linear(c)for c in team_srgb)+(1,)
def material(gid):
 m=bpy.data.materials.new(f'G{gid} | true UV | '+('body cutout'if gid==4 else 'teamcolor under body alpha'if gid<8 else 'head opaque'));m.use_nodes=True;m.use_backface_culling=False;n=m.node_tree.nodes;n.clear();l=m.node_tree.links;o=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');em.inputs['Strength'].default_value=1;tex=n.new('ShaderNodeTexImage');tex.image=head if gid==8 else diagnostic if diagnostic and gid in [6,7] else body;tex.interpolation='Linear';tex.extension='EXTEND';l.new(tex.outputs['Color'],em.inputs['Color'])
 if gid in [5,6,7]:
  mix=n.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[1].default_value=team;l.new(tex.outputs['Alpha'],mix.inputs[0]);l.new(tex.outputs['Color'],mix.inputs[2]);l.new(mix.outputs['Color'],em.inputs['Color'])
 if gid==4:
  alpha=n.new('ShaderNodeMath');alpha.operation='GREATER_THAN';alpha.inputs[1].default_value=.75 # MDX Transparent filter alpha threshold (~0.75)
  l.new(tex.outputs['Alpha'],alpha.inputs[0]);trans=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');l.new(alpha.outputs[0],mix.inputs[0]);l.new(trans.outputs[0],mix.inputs[1]);l.new(em.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],o.inputs['Surface'])
 else:l.new(em.outputs[0],o.inputs['Surface'])
 # Original visible layers do not set TwoSided. Cycles ignores the viewport
 # material culling switch, so make back-facing hits explicitly transparent.
 prior=o.inputs['Surface'].links[0].from_socket;l.remove(o.inputs['Surface'].links[0]);geom=n.new('ShaderNodeNewGeometry');attr=n.new('ShaderNodeAttribute');attr.attribute_name='MDX_opposed_face_pair';inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;l.new(attr.outputs['Fac'],inv.inputs[1]);factor=n.new('ShaderNodeMath');factor.operation='MULTIPLY';l.new(inv.outputs[0],factor.inputs[0]);l.new(geom.outputs['Backfacing'],factor.inputs[1]);backtrans=n.new('ShaderNodeBsdfTransparent');cull=n.new('ShaderNodeMixShader');l.new(factor.outputs[0],cull.inputs[0]);l.new(prior,cull.inputs[1]);l.new(backtrans.outputs[0],cull.inputs[2]);l.new(cull.outputs[0],o.inputs['Surface'])
 return m
objects={}
for g in d['geosets'][4:9]:
 i=g['index'];mesh=bpy.data.meshes.new(f'Original MDX geoset {i}');mesh.from_pydata(g['vertices'],[],g['faces']);mesh.update();ob=bpy.data.objects.new(f'G{i} original topology / {len(g["faces"])} triangles',mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(material(i));uv=mesh.uv_layers.new(name='Original MDX UV V-flipped for Blender')
 for poly in mesh.polygons:
  poly.use_smooth=True
  for li in poly.loop_indices:
   vi=mesh.loops[li].vertex_index;u,v=g['uvSets'][0][vi];uv.data[li].uv=(u,1-v)
 # Opposite-winding coplanar duplicates are explicit two-sided cards in
 # this MDX. Cycles transparency cannot reliably ray-through a coincident
 # back face into its exact front-face mate. Mark these pairs to evaluate
 # as a two-sided surface, which matches their rasterized coverage.
 facekeys=[]
 for ff in g['faces']:
  pp=[tuple(round(x,5)for x in g['vertices'][vi]+g['uvSets'][0][vi])for vi in ff];facekeys.append(min(tuple(pp[k:]+pp[:k])for k in range(3)))
 lookup=set(facekeys);paired=[]
 for key in facekeys:
  rev=list(key[::-1]);paired.append(float(min(tuple(rev[k:]+rev[:k])for k in range(3))in lookup))
 att=mesh.attributes.new('MDX_opposed_face_pair','FLOAT','FACE');att.data.foreach_set('value',paired);ob['opposed_face_pairs_rendered_two_sided']=int(sum(paired))
 objects[i]=ob;ob['original_geoset_index']=i;ob['original_material_id']=g['materialId'];ob['original_mdx_sha256']=d['sha256'];ob['preview_note']='Original vertex topology, exact sampled MDX node animation, newly authored texture. Native effects excluded.'
# This object carries original animation metadata, not a replacement skeleton.
meta=bpy.data.objects.new('MDX SOURCE + LIMITATIONS',None);bpy.context.collection.objects.link(meta);meta['source_sha256']=d['sha256'];meta['sequence_definitions']=json.dumps(d['sequences']);meta['excluded_geosets']='0,1,2,3 (glow, teleport, egg, egg glow); source unchanged';meta['not_rendered']='Original particle/ribbon/event/attachment effects';meta['skin']='MDX800 matrix groups with equal bone weight; original pivots; SLERP and SQUAD quaternion interpolation';meta['teamcolor_preview']=args.team
bpy.ops.object.camera_add();camera=bpy.context.object;camera.name='Orthographic review camera';camera.data.type='ORTHO';camera.data.clip_start=.1;camera.data.clip_end=3000;scene.camera=camera
center=Vector((-33,0,22))
def view(name):
 dirs={'hero':(1.2,-1.75,1.1),'top':(.25,-.12,3),'side':(.1,-3,.45),'front':(3,-.15,.4)}
 camera.location=center+Vector(dirs[name])*250;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=300 if name!='side'else 280

def pose(seq,frame,elapsed=0):
 samples=ev.sample(seq,frame,elapsed,list(objects))
 for x in samples:
  ob=objects[x['index']];ob.data.vertices.foreach_set('co',x['vertices'].ravel());ob.data.update();ob.hide_render=x['alpha']<=.001
  try:ob.data.normals_split_custom_set_from_vertices(x['normals'].tolist())
  except Exception:pass
 return samples
# Camera fitting uses points on actual used triangles. Cutout-card bounds are
# estimated on a 16-subdivision barycentric lattice through the current alpha.
alpha_pixels=np.array(body.pixels[:],dtype=np.float32).reshape(body.size[1],body.size[0],4)[:,:,3]
fitcache={}
for gg in d['geosets'][4:9]:
 gi=gg['index'];ff=np.array(gg['faces'],int)
 if gi==4:
  nn=16;bb=np.array([(1-(i+j)/nn,i/nn,j/nn) for i in range(nn+1)for j in range(nn+1-i)])
  uu=np.einsum('bi,fij->fbj',bb,np.array(gg['uvSets'][0])[ff]);xx=np.clip(np.rint(uu[:,:,0]*(body.size[0]-1)).astype(int),0,body.size[0]-1);yy=np.clip(np.rint((1-uu[:,:,1])*(body.size[1]-1)).astype(int),0,body.size[1]-1);keep=alpha_pixels[yy,xx]>.75;fi,bi=np.where(keep);fitcache[gi]=(ff[fi],bb[bi])
 else:fitcache[gi]=np.array(sorted(set(ff.ravel().tolist())),int)
def visible_points(samples):
 points=[]
 for x in samples:
  if x['alpha']<=.001:continue
  c=fitcache[x['index']];vv=x['vertices']
  if isinstance(c,tuple):points.append(np.einsum('ni,nij->nj',c[1],vv[c[0]]))
  else:points.append(vv[c])
 return np.concatenate(points)
def fit_points(points,margin=1.1):
 q=camera.rotation_euler.to_quaternion();right=np.array(q@Vector((1,0,0)));up=np.array(q@Vector((0,1,0)));pp=points@np.stack([right,up],axis=1);low=pp.min(0);high=pp.max(0);mid=(low+high)/2;target=np.array(center);target+=right*(mid[0]-target@right)+up*(mid[1]-target@up);direction=(camera.location-center).normalized();camera.location=Vector(target)+direction*700;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();aspect=scene.render.resolution_x/scene.render.resolution_y;camera.data.ortho_scale=float(max(high[0]-low[0],(high[1]-low[1])*aspect)*margin)

manifest={'sourceSha256':d['sha256'],'body':str(args.body),'bodySha256':hashlib.sha256(Path(args.body).read_bytes()).hexdigest(),'head':str(args.head),'headSha256':hashlib.sha256(Path(args.head).read_bytes()).hexdigest(),'diagnosticTextureG6G7':args.diagnostic,'teamColor':args.team,'teamSrgb':team_srgb,'renderedGeosets':list(objects),'renderedTriangles':487,'frames':[],'limitations':meta['not_rendered']+'; geosets 0–3 not rendered; texture artwork is a new interpretation, not recovered original'}

# Contact-sheet source frames from the actual final MDX and exact BLP readback.
view('hero')
points=[]
for seq in d['sequences'][:10]:
 for t in np.linspace(*seq['interval'],21):
  samples=ev.sample(seq['name'],t,t-seq['interval'][0],list(objects))
  if any(x['alpha']>.001 for x in samples):points.append(visible_points(samples))
fit_points(np.concatenate(points),1.12)
for i,seq in enumerate(d['sequences'][:10]):
 for j,phase in enumerate([0.,.3333333333,.6666666667,1.]):
  t=seq['interval'][0]+phase*(seq['interval'][1]-seq['interval'][0]);samples=pose(seq['name'],t,t-seq['interval'][0])
  scene.render.filepath=str(out/f'{i:02d}-{j:02d}.png');bpy.ops.render.render(write_still=True)
  manifest['frames'].append({'file':scene.render.filepath,'index':i,'sequence':seq['name'],'interval':seq['interval'],'phase':phase,'time':t,'visibleBodyGeosets':[x['index']for x in samples if x['alpha']>.001]})
manifest['note']='Actual MDX800 mesh and deformation; BLP readback; 487 triangles G4–8 only; native glows, particles and ribbons omitted; not a Warcraft screenshot.'
(out/'render-manifest.json').write_text(json.dumps(manifest,indent=2))
