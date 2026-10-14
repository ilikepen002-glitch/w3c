const fs=require('fs'),path=require('path'),crypto=require('crypto');
const runtime=process.env.MDX_PARSER_MODULES || path.dirname(path.dirname(require.resolve('mdx-m3-viewer/package.json')));
const ts=require(runtime+'/typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const base=runtime+'/mdx-m3-viewer/src';const get=n=>require(base+'/parsers/mdlx/'+n+'.ts').default;
const Model=get('model'),Geoset=get('geoset'),Bone=get('bone'),Sequence=get('sequence'),Texture=get('texture'),Material=get('material'),Layer=get('layer'),Camera=get('camera'),Extent=get('extent');
const {Vector3Animation,Vector4Animation}=require(base+'/parsers/mdlx/animations.ts');
const {createTypedSd}=require(base+'/viewer/handlers/mdx/sd.ts');const {mat4,vec3}=require(runtime+'/gl-matrix');
const src=JSON.parse(fs.readFileSync(__dirname+'/original/emberbird-source.json'));
const m=new Model();m.name=src.name;m.version=800;m.blendTime=150;
function ext(min=[-95,-95,-10],max=[85,95,130]){const e=new Extent();e.min.set(min);e.max.set(max);e.boundsRadius=150;return e;}
m.extent=ext();const tex=new Texture();tex.path='Textures\\EmberBirdAtlas.blp';m.textures.push(tex);
const mat=new Material(),layer=new Layer();layer.textureId=0;layer.filterMode=0;layer.flags=0;mat.layers.push(layer);m.materials.push(mat);
for(const s of src.sequences){const a=new Sequence();a.name=s.name;a.interval.set([s.start,s.end]);a.flags=s.loop?0:1;a.moveSpeed=s.name==='Walk'?85:0;a.extent=ext();m.sequences.push(a);}
for(let i=0;i<src.bones.length;i++){const b=src.bones[i],a=new Bone();a.name=b.name;a.objectId=i;a.parentId=b.parent;a.geosetId=-1;a.geosetAnimationId=-1;
 for(const [tag,entries] of Object.entries(b.tracks)){const tr=tag==='KGRT'?new Vector4Animation():new Vector3Animation();tr.name=tag;tr.interpolationType=1;for(const [f,v] of entries){tr.frames.push(f);tr.values.push(new Float32Array(v));}a.animations.push(tr);}m.bones.push(a);m.pivotPoints.push(new Float32Array(b.pivot));}
const g=new Geoset();const verts=[],normals=[],faces=[],uv=[],groups=[];
for(const p of src.parts){const smooth=p.verts.map(()=>[0,0,0]),faceNormals=[];
 for(const f of p.faces){const a=vec3.fromValues(...p.verts[f[0]]),b=vec3.fromValues(...p.verts[f[1]]),c=vec3.fromValues(...p.verts[f[2]]),n=vec3.create();vec3.sub(b,b,a);vec3.sub(c,c,a);vec3.cross(n,b,c);if(vec3.length(n)<1e-7)throw Error('degenerate triangle '+p.name);vec3.normalize(n,n);faceNormals.push(Array.from(n));for(const vi of f)for(let k=0;k<3;k++)smooth[vi][k]+=n[k];}
 smooth.forEach(v=>vec3.normalize(v,v));
 const low=[0,1,2].map(a=>Math.min(...p.verts.map(v=>v[a]))),high=[0,1,2].map(a=>Math.max(...p.verts.map(v=>v[a])));
 p.faces.forEach((f,fi)=>{const color=p.facecols?p.facecols[fi]:p.color,n=faceNormals[fi].map(Math.abs);let axes=n[2]>=n[0]&&n[2]>=n[1]?[0,1]:(n[0]>=n[1]?[1,2]:[0,2]);if(p.name.includes('scute'))axes=[0,1];if(p.name.includes('amber spine'))axes=n[0]>=n[1]?[1,2]:[0,2];
 for(const vi of f){const pos=p.verts[vi];const a=p.uvs?p.uvs[vi][0]:(pos[axes[0]]-low[axes[0]])/Math.max(1e-7,high[axes[0]]-low[axes[0]]),b=p.uvs?p.uvs[vi][1]:(pos[axes[1]]-low[axes[1]])/Math.max(1e-7,high[axes[1]]-low[axes[1]]);const u=((color%4)*64+5+54*a)/256,v=(Math.floor(color/4)*64+5+54*(1-b))/256;faces.push(verts.length/3);verts.push(...pos);normals.push(...(p.smooth?smooth[vi]:faceNormals[fi]));uv.push(u,v);groups.push(p.bone);}});
}
g.vertices=new Float32Array(verts);g.normals=new Float32Array(normals);g.faces=new Uint16Array(faces);g.uvSets=[new Float32Array(uv)];g.vertexGroups=new Uint8Array(groups);g.matrixGroups=new Uint32Array(src.bones.map(()=>1));g.matrixIndices=new Uint32Array(src.bones.map((_,i)=>i));g.faceTypeGroups=new Uint32Array([4]);g.faceGroups=new Uint32Array([faces.length]);g.extent=ext();g.sequenceExtents=src.sequences.map(()=>ext());m.geosets.push(g);
const cam=new Camera();cam.name='Portrait';cam.position.set([115,-72,95]);cam.targetPosition.set([8,0,72]);cam.fieldOfView=.7;cam.nearClippingPlane=1;cam.farClippingPlane=1000;m.cameras.push(cam);
require('../../display-animations.cjs').append(m, 'EmberBird', runtime);
const out=__dirname+'/original/EmberBird.mdx';fs.writeFileSync(out,Buffer.from(m.saveMdx()));fs.writeFileSync(__dirname+'/original/EmberBird.mdl',m.saveMdl());
// Every preview below comes from a NEW parse of the on-disk MDX, not the generator JSON.
const r=new Model();const mdx=fs.readFileSync(out);r.load(new Uint8Array(mdx));if(r.version!==800)throw Error('not MDX800');
const nodes=new Map(r.bones.concat(r.helpers).map(n=>[n.objectId,n]));const tracks=new Map([...nodes].map(([id,n])=>[id,Object.fromEntries(n.animations.map(a=>[a.name,createTypedSd(r,a)]))]));
function sample(si,time){const mats=new Map();function node(id){if(mats.has(id))return mats.get(id);const n=nodes.get(id);if(!n)throw Error('missing bone');const t=vec3.create(),q=new Float32Array([0,0,0,1]),s=new Float32Array([1,1,1]);const tr=tracks.get(id);for(const [tag,out]of[['KGTR',t],['KGRT',q],['KGSC',s]])if(tr[tag])tr[tag].getValue(out,si,time,time-r.sequences[si].interval[0]);const a=mat4.create();mat4.fromRotationTranslationScaleOrigin(a,q,t,s,r.pivotPoints[id]);if(n.parentId!==-1)mat4.mul(a,node(n.parentId),a);mats.set(id,a);return a;}
 return r.geosets.map(g=>{let off=0;const groups=Array.from(g.matrixGroups,c=>{const x=Array.from(g.matrixIndices.slice(off,off+c));off+=c;return x});const v=[],norms=[];for(let i=0;i<g.vertices.length/3;i++){const ids=groups[g.vertexGroups[i]],o=vec3.create(),nn=vec3.create();for(const id of ids){const a=vec3.create();vec3.transformMat4(a,g.vertices.subarray(i*3,i*3+3),node(id));vec3.add(o,o,a);}vec3.scale(o,o,1/ids.length);v.push(...o);}return{vertices:v,faces:Array.from(g.faces),uv:Array.from(g.uvSets[0]),materialId:g.materialId};});}
const result={source:'NEW parse of exported EmberBird.mdx',version:r.version,texture:'EmberBirdAtlas_decoded.png',frames:[],sequences:r.sequences.map(s=>({name:s.name,interval:Array.from(s.interval)}))};const checks=[];
for(let si=0;si<r.sequences.length;si++){const s=r.sequences[si],bounds={min:[Infinity,Infinity,Infinity],max:[-Infinity,-Infinity,-Infinity]};let first=null,maxDelta=0;const count=25;
 for(let i=0;i<count;i++){const t=s.interval[0]+(s.interval[1]-s.interval[0])*i/(count-1),geosets=sample(si,t);if(!first)first=geosets[0].vertices;
  for(const gg of geosets)gg.vertices.forEach((v,k)=>{if(!Number.isFinite(v))throw Error('nonfinite pose');bounds.min[k%3]=Math.min(bounds.min[k%3],v);bounds.max[k%3]=Math.max(bounds.max[k%3],v);maxDelta=Math.max(maxDelta,Math.abs(v-first[k]));});
  result.frames.push({sequence:s.name,index:i,time:t,geosets});}
 if(maxDelta<.05)throw Error('static animation '+s.name);checks.push({sequence:s.name,samples:count,maxVertexCoordinateChange:maxDelta,bounds,loop:s.flags===0});}
global.ImageData=class{constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4);}};const {BlpImage}=require(base+'/parsers/blp/image.ts');const blp=new BlpImage();blp.load(new Uint8Array(fs.readFileSync(__dirname+'/original/EmberBirdAtlas.blp')));for(let i=0;i<blp.mipmaps();i++)blp.getMipmap(i);fs.writeFileSync(__dirname+'/original/palette-decoded.rgba',Buffer.from(blp.getMipmap(0).data));
const report={status:'offline-format-and-sampling-passed',game127aTested:false,sha256:crypto.createHash('sha256').update(mdx).digest('hex'),bytes:mdx.length,version:r.version,triangles:r.geosets.reduce((n,g)=>n+g.faces.length/3,0),vertices:r.geosets.reduce((n,g)=>n+g.vertices.length/3,0),bones:r.bones.length,textures:r.textures.map(t=>t.path),cameras:r.cameras.map(c=>c.name),blp:{version:1,width:blp.width,height:blp.height,mipmaps:blp.mipmaps(),alphaBits:blp.alphaBits},animations:checks,provenance:'Original program-authored geometry, rig, animations and palette; no third-party model data.'};
fs.writeFileSync(__dirname+'/validation-report.json',JSON.stringify(report,null,2));fs.writeFileSync(__dirname+'/sampled-mdx-frames.json',JSON.stringify(result));console.log(JSON.stringify(report,null,2));
