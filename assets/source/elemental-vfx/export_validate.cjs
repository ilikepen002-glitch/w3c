const fs=require('fs'),path=require('path'),crypto=require('crypto');
const rt=path.resolve(process.env.MDX_PARSER_RUNTIME||path.join(__dirname,'runtime/node_modules'));
const ts=require(rt+'/typescript');require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const base=rt+'/mdx-m3-viewer/src',get=n=>require(base+'/parsers/mdlx/'+n+'.ts').default;
const Model=get('model'),Geoset=get('geoset'),GeosetAnimation=get('geosetanimation'),Bone=get('bone'),Sequence=get('sequence'),Texture=get('texture'),Material=get('material'),Layer=get('layer'),Extent=get('extent');
const {FloatAnimation}=require(base+'/parsers/mdlx/animations.ts'),{createTypedSd}=require(base+'/viewer/handlers/mdx/sd.ts');const {vec3}=require(rt+'/gl-matrix');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');const OUT=path.join(__dirname,'output');let reports=[];let allFrames={source:'fresh parse of on-disk MDX800; original source is NOT preview geometry',models:[]};
function anim(tag,entries){const a=new FloatAnimation();a.name=tag;a.interpolationType=1;for(const [f,v]of entries){a.frames.push(f);a.values.push(new Float32Array([v]));}return a;}
for(const name of ['TDPetVfxSwordArray','TDPetVfxVerdantRoot','TDPetVfxFaultRidge']){
 const src=JSON.parse(fs.readFileSync(path.join(__dirname,name+'-source.json'))),m=new Model();m.name=name;m.version=800;m.blendTime=0;
 const vv=src.parts.flatMap(p=>p.verts);const lo=[0,1,2].map(k=>Math.min(...vv.map(v=>v[k]))),hi=[0,1,2].map(k=>Math.max(...vv.map(v=>v[k])));
 function ext(){const e=new Extent();e.min.set(lo.map(v=>v-.1));e.max.set(hi.map(v=>v+.1));e.boundsRadius=Math.hypot(...[0,1,2].map(k=>Math.max(Math.abs(lo[k]),Math.abs(hi[k]))))+.1;return e;}
 m.extent=ext();const tex=new Texture();tex.path=src.texturePath;m.textures.push(tex);
 // True opaque depth-writing Stand. Same geometry switches to Blend for the 600ms death fade.
 const body=new Material(),opaque=new Layer(),fade=new Layer();opaque.textureId=fade.textureId=0;opaque.filterMode=0;fade.filterMode=2;
 opaque.animations.push(anim('KMTA',[[0,1],[1000,1],[1001,0],[1600,0]]));fade.animations.push(anim('KMTA',[[0,0],[1000,0],[1001,1],[1600,1]]));body.layers.push(opaque,fade);m.materials.push(body);
 const light=new Material(),ll=new Layer();ll.textureId=0;ll.filterMode=3;ll.flags=1|128;light.layers.push(ll);m.materials.push(light);
 for(const s of src.sequences){const q=new Sequence();q.name=s.name;q.interval.set([s.start,s.end]);q.flags=s.loop?0:1;q.extent=ext();m.sequences.push(q);}
 const bone=new Bone();bone.name='EffectOrigin';bone.objectId=0;bone.parentId=-1;bone.geosetId=-1;bone.geosetAnimationId=-1;m.bones.push(bone);m.pivotPoints.push(new Float32Array([0,0,0]));
 for(let isGlow=0;isGlow<2;isGlow++){
  const g=new Geoset(),v=[],n=[],uv=[],idx=[],groups=[];
  for(const p of src.parts.filter(p=>Number(p.glow)===isGlow)){
   const low=[0,1,2].map(k=>Math.min(...p.verts.map(v=>v[k]))),high=[0,1,2].map(k=>Math.max(...p.verts.map(v=>v[k])));
   for(const f of p.faces){const a=vec3.fromValues(...p.verts[f[0]]),b=vec3.fromValues(...p.verts[f[1]]),c=vec3.fromValues(...p.verts[f[2]]),nn=vec3.create();vec3.sub(b,b,a);vec3.sub(c,c,a);vec3.cross(nn,b,c);if(vec3.length(nn)<1e-6)throw Error('degenerate '+p.name);vec3.normalize(nn,nn);const abs=Array.from(nn).map(Math.abs),axes=abs[2]>=abs[1]&&abs[2]>=abs[0]?[0,1]:abs[1]>=abs[0]?[0,2]:[1,2];
    for(const vi of f){const pos=p.verts[vi];idx.push(v.length/3);v.push(...pos);n.push(...nn);groups.push(0);const a=(pos[axes[0]]-low[axes[0]])/Math.max(1e-6,high[axes[0]]-low[axes[0]]),b=(pos[axes[1]]-low[axes[1]])/Math.max(1e-6,high[axes[1]]-low[axes[1]]);uv.push(((p.tile%4)*16+2+11*a)/64,(Math.floor(p.tile/4)*16+2+11*(1-b))/64);}
   }
  }
  g.vertices=new Float32Array(v);g.normals=new Float32Array(n);g.faces=new Uint16Array(idx);g.uvSets=[new Float32Array(uv)];g.vertexGroups=new Uint8Array(groups);g.matrixGroups=new Uint32Array([1]);g.matrixIndices=new Uint32Array([0]);g.faceTypeGroups=new Uint32Array([4]);g.faceGroups=new Uint32Array([idx.length]);g.materialId=isGlow;g.extent=ext();g.sequenceExtents=src.sequences.map(()=>ext());m.geosets.push(g);
  const ga=new GeosetAnimation();ga.geosetId=isGlow;ga.alpha=1;ga.animations.push(anim('KGAO',isGlow?[[0,.70],[250,.88],[500,1],[750,.88],[1000,.70],[1120,.70],[1360,.40],[1600,0]]:[[0,1],[1000,1],[1120,1],[1360,.6],[1600,0]]));m.geosetAnimations.push(ga);
 }
 const fp=path.join(OUT,name+'.mdx');fs.writeFileSync(fp,Buffer.from(m.saveMdx()));fs.writeFileSync(path.join(OUT,name+'.mdl'),m.saveMdl());
 const bytes=fs.readFileSync(fp),r=new Model();r.load(new Uint8Array(bytes));if(!bytes.equals(Buffer.from(r.saveMdx())))throw Error('MDX roundtrip mismatch');const mdl=new Model();mdl.load(r.saveMdl());if(mdl.geosets.length!==r.geosets.length||mdl.version!==800)throw Error('MDL semantic mismatch');let mdlMaxError=0;for(let gi=0;gi<r.geosets.length;gi++){for(const field of ['vertices','normals']){const a=r.geosets[gi][field],b=mdl.geosets[gi][field];if(a.length!==b.length)throw Error('MDL geometry length');for(let k=0;k<a.length;k++){mdlMaxError=Math.max(mdlMaxError,Math.abs(a[k]-b[k]));}}if(String(r.geosets[gi].faces)!==String(mdl.geosets[gi].faces))throw Error('MDL indices');}if(mdlMaxError>1e-4)throw Error('MDL text precision');
 if(r.version!==800||r.textures[0].path!=='Textures\\TDPetVfxAtlas.blp'||r.sequences.length!==2||r.sequences[1].flags!==1)throw Error('format contract');
 if(r.particleEmitters.length||r.particleEmitters2.length||r.ribbonEmitters.length)throw Error('unexpected emitter');
 for(const mat of r.materials)for(const l of mat.layers){if(l.flags&16)throw Error('TwoSided not allowed');if(l.textureId!==0)throw Error('texture ref');}
 let corners=0,maxCornerError=0,topology=[];
 for(let gi=0;gi<2;gi++){
  let vi=0;const gg=r.geosets[gi];
  for(const p of src.parts.filter(p=>Number(p.glow)===gi)){
   let vol=0;const edges=new Map();
   for(const f of p.faces){const a=p.verts[f[0]],b=p.verts[f[1]],c=p.verts[f[2]];vol+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6;
    for(let k=0;k<3;k++){const a=f[k],b=f[(k+1)%3],key=[Math.min(a,b),Math.max(a,b)].join(',');if(!edges.has(key))edges.set(key,[]);edges.get(key).push([a,b]);
     for(let dim=0;dim<3;dim++){const error=Math.abs(p.verts[a][dim]-gg.vertices[gg.faces[vi]*3+dim]);maxCornerError=Math.max(maxCornerError,error);if(error>2e-5)throw Error('source to MDX mismatch');}vi++;corners++;
    }
   }
   for(const e of edges.values())if(e.length!==2||e[0][0]!==e[1][1]||e[0][1]!==e[1][0])throw Error('open/reversed '+p.name);if(vol<=0)throw Error('inward '+p.name);topology.push({name:p.name,closed:true,consistentWinding:true,positiveVolume:vol});
  }
 }
 const animations=[],frames=[];
 for(let si=0;si<2;si++){
  const s=r.sequences[si],sampled=[];let prev=2;
  for(let j=0;j<25;j++){
   const time=s.interval[0]+j*(s.interval[1]-s.interval[0])/24;const alphas=r.geosetAnimations.map(ga=>{const o=new Float32Array(1);createTypedSd(r,ga.animations[0]).getValue(o,si,time,time-s.interval[0]);return o[0]});
   if(alphas.some(v=>!Number.isFinite(v)||v<0||v>1))throw Error('alpha range');if(si===1&&alphas[0]>prev+1e-6)throw Error('nonmonotonic Death');prev=alphas[0];
   const layers=r.materials.map(mat=>mat.layers.map(l=>{if(!l.animations.length)return l.alpha;const o=new Float32Array(1);createTypedSd(r,l.animations[0]).getValue(o,si,time,time-s.interval[0]);return o[0]}));
   if(si===0&&(layers[0][0]!==1||layers[0][1]!==0||alphas[0]!==1))throw Error('Stand not opaque');if(si===1&&j>0&&(layers[0][0]!==0||layers[0][1]!==1))throw Error('fade layer switch');
   for(const g of r.geosets){for(let v=0;v<g.vertices.length;v++){const k=v%3;if(!Number.isFinite(g.vertices[v])||g.vertices[v]<r.extent.min[k]||g.vertices[v]>r.extent.max[k])throw Error('bound');}for(let v=0;v<g.normals.length;v+=3)if(Math.abs(Math.hypot(...g.normals.slice(v,v+3))-1)>1e-5)throw Error('normal');}
   sampled.push({time,geosetAlpha:alphas,layerAlpha:layers});frames.push({sequence:s.name,index:j,time,alphas,layers});
  }
  if(si===1&&(sampled[0].geosetAlpha[0]!==1||sampled[24].geosetAlpha.some(v=>v!==0)))throw Error('Death endpoints');animations.push({name:s.name,interval:Array.from(s.interval),loop:s.flags===0,samples:sampled});
 }
 const geometry=r.geosets.map(g=>({vertices:Array.from(g.vertices),normals:Array.from(g.normals),faces:Array.from(g.faces),uv:Array.from(g.uvSets[0]),materialId:g.materialId}));
 allFrames.models.push({name,geometry,frames});
 const report={name,status:'PASS offline format/topology/alpha validation',game127aTested:false,version:r.version,bytes:bytes.length,sha256:sha(bytes),triangles:r.geosets.reduce((n,g)=>n+g.faces.length/3,0),bones:r.bones.length,geosets:r.geosets.length,materials:r.materials.map(m=>m.layers.map(l=>({filterMode:l.filterMode,flags:l.flags}))),texturePath:r.textures[0].path,bounds:{min:lo,max:hi},maxSourceCornerError:maxCornerError,mdxBinaryRoundtripExact:true,mdlTextRoundtripMaxError:mdlMaxError,topology,animations};if(report.triangles>600)throw Error('triangle budget');reports.push(report);
}
global.ImageData=class{constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4)}};const BlpImage=require(base+'/parsers/blp/image.ts').BlpImage;const texb=fs.readFileSync(path.join(OUT,'TDPetVfxAtlas.blp')),blp=new BlpImage();blp.load(new Uint8Array(texb));if(blp.width!==64||blp.height!==64||blp.mipmaps()!==7)throw Error('BLP contract');for(let i=0;i<7;i++){const m=blp.getMipmap(i);for(let k=3;k<m.data.length;k+=4)if(m.data[k]!==255)throw Error('body texture opacity');}fs.writeFileSync(path.join(OUT,'atlas-decoded.rgba'),Buffer.from(blp.getMipmap(0).data));
const report={status:'PASS',models:reports,texture:{name:'TDPetVfxAtlas.blp',version:1,width:64,height:64,mipmaps:7,bytes:texb.length,sha256:sha(texb),alphaMin:255,alphaMax:255}};
fs.writeFileSync(path.join(__dirname,'validation-report.json'),JSON.stringify(report,null,2));fs.writeFileSync(path.join(__dirname,'sampled-mdx-frames.json'),JSON.stringify(allFrames));console.log(JSON.stringify({status:report.status,models:reports.map(r=>({name:r.name,triangles:r.triangles,bytes:r.bytes,sha256:r.sha256})),texture:report.texture},null,2));
