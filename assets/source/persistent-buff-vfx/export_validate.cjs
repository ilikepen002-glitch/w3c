/* Deterministic MDX800 export and validation of the actual reloaded bytes. */
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const rt = process.env.MDX_PARSER_RUNTIME;
if (!rt) throw Error('Set MDX_PARSER_RUNTIME to the existing project-pinned node_modules');
const ts = require(rt+'/typescript');
require.extensions['.ts'] = (m, f) => m._compile(ts.transpileModule(fs.readFileSync(f, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2018}
}).outputText, f);
const base = rt+'/mdx-m3-viewer/src';
const get = n => require(base+'/parsers/mdlx/'+n+'.ts').default;
const Model=get('model'), Geoset=get('geoset'), GeosetAnimation=get('geosetanimation');
const Bone=get('bone'), Sequence=get('sequence'), Texture=get('texture');
const Material=get('material'), Layer=get('layer');
const {FloatAnimation, Vector3Animation, Vector4Animation} = require(base+'/parsers/mdlx/animations.ts');
const {createTypedSd} = require(base+'/viewer/handlers/mdx/sd.ts');
const {mat4, vec3} = require(rt+'/gl-matrix');
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const check = (ok, msg) => { if (!ok) throw Error(msg); };
const out = path.join(__dirname, 'output');
fs.mkdirSync(out, {recursive:true});

function track(Type, name, keys) {
  const a = new Type(); a.name=name; a.interpolationType=1;
  for (const [t,v] of keys) {a.frames.push(t); a.values.push(new Float32Array(v));}
  return a;
}
const models=[];
for (const file of fs.readdirSync(__dirname).filter(x=>x.endsWith('-source.json')).sort()) {
  const src=JSON.parse(fs.readFileSync(path.join(__dirname,file))), m=new Model();
  m.version=800; m.name=src.name; m.blendTime=0;
  m.extent.min.set([-65,-65,40]); m.extent.max.set([65,65,160]); m.extent.boundsRadius=185;
  const tex=new Texture(); tex.path=src.texture; m.textures.push(tex);
  for (const [name,start,end,flags] of [['Stand',0,src.durationMs,0],['Death',2000,2050,1]]) {
    const s=new Sequence(); s.name=name; s.interval.set([start,end]); s.flags=flags;
    s.extent=m.extent; m.sequences.push(s);
  }
  for (const [bi,b] of src.bones.entries()) {
    const n=new Bone(); n.name=b.name; n.objectId=bi; n.parentId=-1;
    n.geosetId=-1; n.geosetAnimationId=-1;
    const rk=[], sk=[], tk=[];
    for(let i=0;i<=24;i++) {
      const t=Math.round(src.durationMs*i/24), u=i/24;
      const a=2*Math.PI*b.turns*u;
      // Full revolution uses enough quaternion keys to preserve its direction.
      rk.push([t,[0,0,Math.sin(a/2),Math.cos(a/2)]]);
      const pulse=Math.sin(2*Math.PI*(u*(src.durationMs===1200?3:1)+b.phase));
      const s=1+b.xyPulse*pulse;
      sk.push([t,[s,s,1]]);
      tk.push([t,[0,0,b.lift*pulse]]);
    }
    for(const t of [2000,2050]) {
      rk.push([t,[0,0,0,1]]); sk.push([t,[1,1,1]]); tk.push([t,[0,0,0]]);
    }
    n.animations.push(track(Vector4Animation,'KGRT',rk), track(Vector3Animation,'KGSC',sk),
                      track(Vector3Animation,'KGTR',tk));
    m.bones.push(n); m.pivotPoints.push(new Float32Array(b.pivot));
  }
  for(let core=0;core<2;core++) {
    const mat=new Material(), l=new Layer();
    l.filterMode=4; l.flags=0x1|0x10|0x80; l.textureId=0;
    // AddAlpha / unshaded / two-sided / no depth writes. Normal depth testing remains.
    mat.layers.push(l); m.materials.push(mat);
  }
  for(let bi=0;bi<src.bones.length;bi++) for(let core=0;core<2;core++) {
    const parts=src.parts.filter(p=>p.bone===bi&&Number(p.core)===core);
    if(!parts.length) continue;
    const g=new Geoset(), vertices=[], normals=[], uv=[], faces=[];
    for(const p of parts) for(const face of p.faces) {
      const [a,b,c]=face.map(i=>p.vertices[i]);
      const ab=b.map((v,i)=>v-a[i]), ac=c.map((v,i)=>v-a[i]);
      const nn=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]];
      const len=Math.hypot(...nn); check(len>1e-5,'Degenerate source triangle');
      for(const vi of face) {
        faces.push(vertices.length/3); vertices.push(...p.vertices[vi]);
        normals.push(...nn.map(v=>v/len)); uv.push(5.5/64,3.5/64);
      }
    }
    g.vertices=new Float32Array(vertices); g.normals=new Float32Array(normals);
    g.faces=new Uint16Array(faces); g.uvSets=[new Float32Array(uv)];
    g.vertexGroups=new Uint8Array(vertices.length/3); g.matrixGroups=new Uint32Array([1]);
    g.matrixIndices=new Uint32Array([bi]); g.faceTypeGroups=new Uint32Array([4]);
    g.faceGroups=new Uint32Array([faces.length]); g.materialId=core;
    g.extent=m.extent; g.sequenceExtents=[m.extent,m.extent];
    const gi=m.geosets.length; m.geosets.push(g);
    const ga=new GeosetAnimation(); ga.geosetId=gi; ga.flags=2;
    ga.color.set((core?src.coreColor:src.color).slice().reverse());
    const keys=[];
    for(let i=0;i<=24;i++) {
      const u=i/24, cycles=src.durationMs===1200?3:1;
      const pulse=(1+Math.cos(2*Math.PI*u*cycles))/2;
      keys.push([Math.round(src.durationMs*u),[(core?.77:.72)+(core?.23:.28)*pulse]]);
    }
    keys.push([2000,[0]],[2050,[0]]);
    ga.animations.push(track(FloatAnimation,'KGAO',keys)); m.geosetAnimations.push(ga);
  }
  const bytes=Buffer.from(m.saveMdx()), modelPath=path.join(out,src.name+'.mdx');
  fs.writeFileSync(modelPath,bytes); fs.writeFileSync(path.join(out,src.name+'.mdl'),m.saveMdl());
  const r=new Model(); r.load(new Uint8Array(fs.readFileSync(modelPath)));
  check(Buffer.from(r.saveMdx()).equals(bytes),'Actual MDX roundtrip mismatch');
  if(process.argv.includes('--check-imports')) {
    const imported=path.resolve(__dirname,'../../../imports/war3mapImported',src.name+'.mdx');
    check(fs.existsSync(imported)&&fs.readFileSync(imported).equals(bytes),'Imported MDX differs from deterministic export');
  }
  check(r.version===800&&r.sequences[0].flags===0&&r.sequences[1].flags===1,'Format/loop flags');
  check(r.textures.length===1&&r.textures[0].path===String.raw`Textures\TDPetVfxAtlas.blp`,'Exact texture path');
  const textureDisk=path.resolve(__dirname,'../../../imports',...r.textures[0].path.split('\\'));
  check(fs.existsSync(textureDisk),'Texture not present in baseline imports');
  const tris=r.geosets.reduce((n,g)=>n+g.faces.length/3,0);
  check(tris<=200&&r.materials.length<=2,'Triangle/material budget');
  check(!r.particleEmitters.length&&!r.particleEmitters2.length&&!r.ribbonEmitters.length&&
        !r.eventObjects.length&&!r.lights.length&&!r.attachments.length&&!r.globalSequences.length,'Unexpected auxiliaries');
  for(const mat of r.materials) check(mat.layers.length===1&&mat.layers[0].filterMode===4&&
      mat.layers[0].flags===0x91&&mat.layers[0].textureId===0,'Material settings');
  for(const g of r.geosets) {
    check(g.matrixGroups.length===1&&g.matrixGroups[0]===1,'Unexpected weighted skeleton');
    check(g.matrixIndices[0]<r.bones.length&&g.vertexGroups.every(x=>x===0),'Bone reference');
    for(let i=0;i<g.normals.length;i+=3) check(Math.abs(Math.hypot(...g.normals.slice(i,i+3))-1)<1e-5,'Normal length');
    check(Array.from(g.vertices).every(Number.isFinite)&&Array.from(g.normals).every(Number.isFinite),'Non-finite geometry');
    check(Array.from(g.faces).every(x=>x<g.vertices.length/3),'Invalid face');
  }
  const bs=r.bones.map(b=>b.animations.map(a=>createTypedSd(r,a)));
  const alphaTracks=r.geosetAnimations.map(a=>createTypedSd(r,a.animations[0]));
  const min=[Infinity,Infinity,Infinity], max=[-Infinity,-Infinity,-Infinity];
  let minAlpha=1,maxRadius=0;
  function sample(time,sequence=0) {
    const matrices=r.bones.map((b,i)=>{
      const q=new Float32Array(4),s=new Float32Array(3),t=new Float32Array(3);
      bs[i][0].getValue(q,sequence,time,time); bs[i][1].getValue(s,sequence,time,time);
      bs[i][2].getValue(t,sequence,time,time);
      check([...q,...s,...t].every(Number.isFinite)&&Math.abs(Math.hypot(...q)-1)<1e-5,'Invalid sampled transform');
      const matrix=mat4.create(); mat4.fromRotationTranslationScaleOrigin(matrix,q,t,s,r.pivotPoints[i]);
      return Array.from(matrix);
    });
    const alpha=alphaTracks.map(a=>{
      const v=new Float32Array(1);a.getValue(v,sequence,time,time);
      check(Number.isFinite(v[0])&&v[0]>=0&&v[0]<=1,'Invalid alpha');return v[0];
    });
    const geometry=r.geosets.map((g,gi)=>{
      const vs=[],v=vec3.create(),matrix=matrices[g.matrixIndices[0]];
      for(let i=0;i<g.vertices.length;i+=3) {
        vec3.transformMat4(v,g.vertices.slice(i,i+3),matrix); vs.push(...v);
        if(sequence===0) {
          for(let j=0;j<3;j++) {min[j]=Math.min(min[j],v[j]);max[j]=Math.max(max[j],v[j]);}
          maxRadius=Math.max(maxRadius,Math.hypot(v[0],v[1]));
          for(let j=0;j<3;j++) check(v[j]>=r.extent.min[j]-1e-4&&v[j]<=r.extent.max[j]+1e-4,'Animated extent');
        }
      }
      return vs;
    });
    if(sequence===0) minAlpha=Math.min(minAlpha,...alpha);
    else check(alpha.every(x=>x===0),'Visible Death tail');
    return {time,sequence:sequence===0?'Stand':'Death',alpha,matrices,geometry};
  }
  const frames=[];
  for(let time=0;time<=src.durationMs;time+=10) frames.push(sample(time));
  for(let time=2000;time<=2050;time++) frames.push(sample(time,1));
  check(frames.filter(f=>f.sequence==='Stand'&&f.time<=50).every(f=>f.alpha.every(a=>a>=.75)),'Not visible by 50 ms');
  check(min[2]>=40&&max[2]<=160&&maxRadius<=65,'Tower-body envelope');
  const first=frames[0],last=frames.find(f=>f.time===src.durationMs);
  let loopDelta=0;
  for(let gi=0;gi<first.geometry.length;gi++) for(let i=0;i<first.geometry[gi].length;i++)
    loopDelta=Math.max(loopDelta,Math.abs(first.geometry[gi][i]-last.geometry[gi][i]));
  check(loopDelta<1e-4&&first.alpha.every((a,i)=>Math.abs(a-last.alpha[i])<1e-5),'Loop position/alpha mismatch');
  const dynamic=frames.find(f=>f.time===src.durationMs/4);
  const movement=Math.max(...first.geometry.flatMap((vs,gi)=>vs.map((v,i)=>Math.abs(v-dynamic.geometry[gi][i]))));
  check(movement>1,'Animation has no observable geometric movement');
  models.push({name:src.name,description:src.description,durationMs:src.durationMs,
    resourcePath:'war3mapImported\\'+src.name+'.mdx',bytes:bytes.length,sha256:sha(bytes),
    triangles:tris,materials:r.materials.length,geosets:r.geosets.length,bones:r.bones.length,
    particleEmitters:0,ribbonEmitters:0,eventObjects:0,deathAlpha:0,
    texture:r.textures[0].path,textureSha256:sha(fs.readFileSync(textureDisk)),
    sampledEnvelope:{min,max,maxRadius,minAlpha,loopPositionMaxDelta:loopDelta,
      quarterLoopMovement:movement,standSamplingStepMs:10,deathSamplingStepMs:1},
    geometry:r.geosets.map((g,gi)=>({vertices:Array.from(g.vertices),faces:Array.from(g.faces),
      bone:g.matrixIndices[0],rgb:Array.from(r.geosetAnimations[gi].color).reverse(),
      uv:Array.from(g.uvSets[0]),filterMode:r.materials[g.materialId].layers[0].filterMode})),
    frames:frames.map(({geometry,...frame})=>frame)});
}
global.ImageData=class {constructor(w,h) {this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4);}};
const Blp=require(base+'/parsers/blp/image.ts').BlpImage, blp=new Blp();
const atlas=path.resolve(__dirname,'../../../imports/Textures/TDPetVfxAtlas.blp');
blp.load(new Uint8Array(fs.readFileSync(atlas))); const mip=blp.getMipmap(0), texel=(3*64+5)*4;
check(mip.width===64&&mip.height===64,'Unexpected baseline atlas size');
const textureSampleRGBA=Array.from(mip.data.slice(texel,texel+4));
check(textureSampleRGBA.every((x,i)=>x===[255,254,229,255][i]),'Expected opaque warm-white baseline atlas swatch');
const result={status:'PASS exported MDX800 offline validation',inGameTested:false,
  parserVersion:JSON.parse(fs.readFileSync(rt+'/mdx-m3-viewer/package.json')).version,
  importedBytesChecked:process.argv.includes('--check-imports'),
  textureSampleRGBA,models,
  caveat:'Actual exported/reparsed MDX mesh and animation. Software projection is not Warcraft rendering. '
    +'No production/runtime integration or map build. Samples do not prove continuous runtime behavior, '
    +'native depth/attachment behavior, all tower profiles, or FPS.'};
fs.writeFileSync(path.join(__dirname,'validation-frames.json'),JSON.stringify(result)+'\n');
const compact={...result,models:models.map(({geometry,frames,...m})=>({...m,
  importFile:'imports/war3mapImported/'+m.name+'.mdx',
  sourceFile:'assets/source/persistent-buff-vfx/'+m.name+'-source.json'}))};
fs.writeFileSync(path.join(__dirname,'manifest.json'),JSON.stringify(compact,null,2)+'\n');
console.log(JSON.stringify(compact,null,2));
