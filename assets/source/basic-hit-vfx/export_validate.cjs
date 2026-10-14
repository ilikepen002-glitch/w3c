const fs=require('fs'),path=require('path'),crypto=require('crypto');
const rt=process.env.MDX_PARSER_RUNTIME;if(!rt)throw Error('Set MDX_PARSER_RUNTIME to project-pinned runtime');
const ts=require(rt+'/typescript');require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const base=rt+'/mdx-m3-viewer/src',get=n=>require(base+'/parsers/mdlx/'+n+'.ts').default;
const Model=get('model'),Geoset=get('geoset'),GeosetAnimation=get('geosetanimation'),Bone=get('bone'),Sequence=get('sequence'),Texture=get('texture'),Material=get('material'),Layer=get('layer');
const {FloatAnimation,Vector3Animation}=require(base+'/parsers/mdlx/animations.ts'),{createTypedSd}=require(base+'/viewer/handlers/mdx/sd.ts');
const out=path.join(__dirname,'output');fs.mkdirSync(out,{recursive:true});let evidence=[];
for(const file of fs.readdirSync(__dirname).filter(x=>x.endsWith('-source.json'))){
 const src=JSON.parse(fs.readFileSync(path.join(__dirname,file))),m=new Model();m.version=800;m.name=src.name;m.blendTime=0;
 m.extent.min.set([-110,-110,0]);m.extent.max.set([110,110,65]);m.extent.boundsRadius=170;
 const tex=new Texture();tex.path=src.texture;m.textures.push(tex);
 for(const [name,start,end] of [['Stand',0,src.lifetimeMs],['Death',400,401]]){const s=new Sequence();s.name=name;s.interval.set([start,end]);s.flags=1;s.extent=m.extent;m.sequences.push(s);}
 const bone=new Bone();bone.name='HitOrigin';bone.objectId=0;bone.parentId=-1;bone.geosetId=-1;bone.geosetAnimationId=-1;const sc=new Vector3Animation();sc.name='KGSC';sc.interpolationType=1;for(const [t,v]of [[0,.82],[25,1],[src.holdMs,1],[src.lifetimeMs,.60],[400,.60],[401,.60]]){sc.frames.push(t);sc.values.push(new Float32Array([v,v,v]));}bone.animations.push(sc);m.bones.push(bone);m.pivotPoints.push(new Float32Array([0,0,0]));
 for(let core=0;core<2;core++){
  const mat=new Material(),l=new Layer();l.filterMode=core?3:2;l.flags=1;l.textureId=0;mat.layers.push(l);m.materials.push(mat);
  const g=new Geoset(),v=[],n=[],uv=[],idx=[];
  for(const p of src.parts.filter(p=>Number(p.core)===core))for(const f of p.faces){const [a,b,c]=f.map(i=>p.vertices[i]);const ab=b.map((x,i)=>x-a[i]),ac=c.map((x,i)=>x-a[i]);let nn=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]],len=Math.hypot(...nn);if(len<1e-6)throw Error('degenerate');nn=nn.map(x=>x/len);for(const vi of f){idx.push(v.length/3);v.push(...p.vertices[vi]);n.push(...nn);uv.push(5.5/64,3.5/64);}}
  g.vertices=new Float32Array(v);g.normals=new Float32Array(n);g.faces=new Uint16Array(idx);g.uvSets=[new Float32Array(uv)];g.vertexGroups=new Uint8Array(v.length/3);g.matrixGroups=new Uint32Array([1]);g.matrixIndices=new Uint32Array([0]);g.faceTypeGroups=new Uint32Array([4]);g.faceGroups=new Uint32Array([idx.length]);g.materialId=core;g.extent=m.extent;g.sequenceExtents=[m.extent,m.extent];m.geosets.push(g);
  const ga=new GeosetAnimation();ga.geosetId=core;ga.flags=2;ga.color.set((core?[1,.96,.78]:src.color).slice().reverse());const an=new FloatAnimation();an.name='KGAO';an.interpolationType=1;
  for(const [t,a]of [[0,1],[src.holdMs,1],[src.holdMs+20,.72],[src.holdMs+50,.25],[src.lifetimeMs,0],[400,0],[401,0]]){an.frames.push(t);an.values.push(new Float32Array([a]));}ga.animations.push(an);m.geosetAnimations.push(ga);
 }
 const bytes=Buffer.from(m.saveMdx());fs.writeFileSync(path.join(out,src.name+'.mdx'),bytes);fs.writeFileSync(path.join(out,src.name+'.mdl'),m.saveMdl());
 // Validate bytes actually exported, never feed source geometry into preview.
 const r=new Model();r.load(new Uint8Array(fs.readFileSync(path.join(out,src.name+'.mdx'))));if(!Buffer.from(r.saveMdx()).equals(bytes))throw Error('roundtrip');
 if(r.version!==800||r.textures.length!==1||r.textures[0].path!==src.texture||r.bones.length!==1||r.sequences.some(s=>s.flags!==1))throw Error('format/texture/sequence');for(const g of r.geosets){for(let i=0;i<g.vertices.length;i++){const x=g.vertices[i],k=i%3;if(!Number.isFinite(x)||x<r.extent.min[k]||x>r.extent.max[k])throw Error('extent');}for(let i=0;i<g.normals.length;i+=3)if(Math.abs(Math.hypot(...g.normals.slice(i,i+3))-1)>1e-5)throw Error('normal');} const tris=r.geosets.reduce((s,g)=>s+g.faces.length/3,0);if(tris>200||r.materials.length>2||r.particleEmitters.length||r.particleEmitters2.length||r.ribbonEmitters.length||r.eventObjects.length)throw Error('budget');
 for(const ga of r.geosetAnimations){const a=new Float32Array(1);createTypedSd(r,ga.animations[0]).getValue(a,1,400,0);if(a[0]!==0)throw Error('visible Death outlives budget');}
 const frames=[];for(let t=0;t<=360;t+=10){const death=t>=src.lifetimeMs,mt=death?400:t,si=death?1:0;
  const alpha=r.geosetAnimations.map(ga=>{const a=new Float32Array(1);createTypedSd(r,ga.animations[0]).getValue(a,si,mt,mt-r.sequences[si].interval[0]);if(!Number.isFinite(a[0])||a[0]<0||a[0]>1)throw Error('alpha');return a[0]});const scale=new Float32Array(3);createTypedSd(r,r.bones[0].animations[0]).getValue(scale,si,mt,mt-r.sequences[si].interval[0]);frames.push({time:t,sequence:death?'Death':'Stand',modelTime:mt,alpha,scale:Array.from(scale)});}
 if(frames.filter(f=>f.time<=50).some(f=>f.alpha.some(a=>a<.99))||frames.at(-1).alpha.some(a=>a!==0))throw Error('timing');
 evidence.push({name:src.name,holdMs:src.holdMs,lifetimeMs:src.lifetimeMs,triangles:tris,materials:r.materials.length,bones:r.bones.length,particleEmitters:0,ribbons:0,bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),texture:r.textures[0].path,frames,geometry:r.geosets.map((g,i)=>({vertices:Array.from(g.vertices),faces:Array.from(g.faces),uv:Array.from(g.uvSets[0]),rgb:Array.from(r.geosetAnimations[i].color).reverse(),filterMode:r.materials[g.materialId].layers[0].filterMode}))});
}
global.ImageData=class{constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4)}};
const Blp=require(base+'/parsers/blp/image.ts').BlpImage,b=new Blp(),atlas=path.resolve(__dirname,'../../../imports/Textures/TDPetVfxAtlas.blp');b.load(new Uint8Array(fs.readFileSync(atlas)));const mip=b.getMipmap(0),i=(3*64+5)*4;
const result={status:'PASS offline exported MDX validation',inGameTested:false,preview:'Actual parsed MDX triangles and sampled alpha; approximate software blend, fixed camera. Complete fade is inside non-loop Stand and budgeted lifetime; Death is transparent. Native rendering remains unverified.',atlasSha256:crypto.createHash('sha256').update(fs.readFileSync(atlas)).digest('hex'),textureSampleRGBA:Array.from(mip.data.slice(i,i+4)),models:evidence};
fs.writeFileSync(path.join(__dirname,'validation-frames.json'),JSON.stringify(result));console.log(JSON.stringify({status:result.status,models:evidence.map(({name,triangles,bytes,sha256})=>({name,triangles,bytes,sha256}))},null,2));
