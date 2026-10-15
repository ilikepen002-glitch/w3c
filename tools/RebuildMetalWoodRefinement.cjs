'use strict';
// Deterministic local refinement of PINNED current production MDX800. No git-show, no old BASE.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ROOT=path.resolve(process.argv[2]||path.join(__dirname,'..'));
const SRC=path.join(ROOT,'assets/source/elemental-spirits/refinement-20261015/batch-a');
const runtime=process.env.MDX_PARSER_MODULES;
if(!runtime)throw Error('Set MDX_PARSER_MODULES to installed mdx-m3-viewer + typescript directory');
const ts=require(runtime+'/typescript');require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const helper=require(SRC+'/display-animations-pinned.cjs'),{Model}=helper.api(runtime);
global.ImageData=class{constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4);}};
const {BlpImage}=require(runtime+'/mdx-m3-viewer/src/parsers/blp/image.ts');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const stable=m=>JSON.stringify({sequences:m.sequences.map(s=>({name:s.name,flags:s.flags,interval:Array.from(s.interval),moveSpeed:s.moveSpeed})),bones:m.bones,helpers:m.helpers,pivots:m.pivotPoints});
const reports=[];const only=process.argv[3];
for(const e of JSON.parse(fs.readFileSync(SRC+'/config.json'))){
 const name=e.model;if(only&&only!==name)continue;
 const dir=path.join(SRC,name),input=fs.readFileSync(dir+'/input.mdx');
 if(sha(input)!==e.inputMdxSha256)throw Error('Pinned input hash mismatch '+name);
 const texture=path.join(ROOT,'imports',e.requiredTextureImportPath.replaceAll('\\','/'));
 if(!fs.existsSync(texture)){console.log('Awaiting texture '+name);continue;}
 const m=new Model();m.load(new Uint8Array(input));
 const immutable=stable(m);if(m.version!==800||m.sequences.length!==10)throw Error('Format/animation contract');
 const s=JSON.parse(fs.readFileSync(dir+'/parts-source.json')),g=m.geosets[0];if(m.geosets.length!==1)throw Error('Expected known single-geoset source');
 let off=0,maxInputDelta=0;const edits=[],uvEdits=[];
 for(const p of s.parts){
  const count=p.faces.length*3;
  for(let i=0;i<count;i++)for(let a=0;a<3;a++)maxInputDelta=Math.max(maxInputDelta,Math.abs(g.vertices[(off+i)*3+a]-p.verts[p.faces[Math.floor(i/3)][i%3]][a]));
  if(e.uvRemap&&p.name===e.uvRemap.part){
   const u=e.uvRemap;let changed=0;
   for(let fi=0;fi<Math.min(p.faces.length,u.faceEndExclusive);fi++)if((p.facecols?p.facecols[fi]:p.color)===u.fromTile){
    for(let vi=0;vi<3;vi++){const k=(off+fi*3+vi)*2;g.uvSets[0][k]+=(u.toTile%4-u.fromTile%4)/4;g.uvSets[0][k+1]+=(Math.floor(u.toTile/4)-Math.floor(u.fromTile/4))/4;}changed++;
   }uvEdits.push({...u,facesChanged:changed});
  }
  const eye=/eye|iris|pupil|sap glow/.test(p.name);
  if(eye){
   const low=[0,1,2].map(a=>Math.min(...p.verts.map(v=>v[a]))),high=[0,1,2].map(a=>Math.max(...p.verts.map(v=>v[a]))),center=low.map((v,a)=>(v+high[a])/2);
   const color=p.color,scale=color===14?e.eyeScale:color===0?1.07:color===15?1.15:1.08;
   const axis=e.faceAxis,sign=axis===0?1:Math.sign(center[1]);
   const outward=color===14?.10:color===13?.23:color===15?.25:0;
   for(let i=off;i<off+count;i++)for(let a=0;a<3;a++)g.vertices[i*3+a]=center[a]+(g.vertices[i*3+a]-center[a])*scale+(a===axis?sign*outward:0);
   edits.push({part:p.name,vertices:count,scale,outward,axis});
  }
  off+=count;
 }
 if(maxInputDelta>1e-3||off!==g.vertices.length/3)throw Error('Source ordering differs from pinned MDX '+name+' '+maxInputDelta);
 if(stable(m)!==immutable)throw Error('Animation or rig was changed');
 const out=path.join(ROOT,'imports',e.modelImportPath.replaceAll('\\','/'));fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,Buffer.from(m.saveMdx()));
 const bytes=fs.readFileSync(out),r=new Model();r.load(new Uint8Array(bytes));if(stable(r)!==immutable)throw Error('Serialized rig/animation changed');
 if(r.textures.length!==1||r.textures[0].path!==e.requiredTextureImportPath)throw Error('Texture mapping changed');
 const preview=path.join(ROOT,'previews',name);fs.mkdirSync(preview+'/original',{recursive:true});
 const sample=helper.sampler(r,runtime),frames=[],checks=[],geometry=r.geosets.map(g=>({faces:Array.from(g.faces),uv:Array.from(g.uvSets[0]),materialId:g.materialId}));
 for(let si=0;si<r.sequences.length;si++){
  const seq=r.sequences[si],lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity],first=sample(si,seq.interval[0])[0].vertices,last=sample(si,seq.interval[1])[0].vertices;let maxDelta=0;
  for(let i=0;i<=64;i++){
   const time=seq.interval[0]+(seq.interval[1]-seq.interval[0])*i/64,gs=sample(si,time,true);
   for(const gg of gs)for(let k=0;k<gg.vertices.length;k++){const v=gg.vertices[k];if(!Number.isFinite(v))throw Error('Nonfinite pose');lo[k%3]=Math.min(lo[k%3],v);hi[k%3]=Math.max(hi[k%3],v);maxDelta=Math.max(maxDelta,Math.abs(v-first[k]));}
   if((si===0&&i===0)||([1,5,6,7,8,9].includes(si)&&i%8===0))frames.push({sequence:seq.name,index:i/8,time,geosets:gs.map((g,k)=>({vertices:Array.from(g.vertices),normals:Array.from(g.normals),...geometry[k]}))});
  }
  const loopDelta=Math.max(...last.map((v,k)=>Math.abs(v-first[k])));if(seq.flags===0&&loopDelta>1e-3)throw Error('Loop discontinuity '+name+'/'+seq.name);if(maxDelta<.05)throw Error('Static animation '+name+'/'+seq.name);
  // Every pose remains in the existing conservative bound; otherwise fail instead of silently widening.
  const extentOK=lo.every((v,k)=>v>=seq.extent.min[k]-1e-3)&&hi.every((v,k)=>v<=seq.extent.max[k]+1e-3);
  if(!extentOK)throw Error('Pose exceeds original bounds '+name+'/'+seq.name);
  checks.push({index:si,name:seq.name,interval:Array.from(seq.interval),loop:seq.flags===0,samples:65,maxVertexCoordinateChange:maxDelta,loopEndpointMaxDelta:loopDelta,bounds:{min:lo,max:hi},withinOriginalExtent:extentOK});
 }
 const blpbytes=fs.readFileSync(texture),blp=new BlpImage();blp.load(new Uint8Array(blpbytes));for(let i=0;i<blp.mipmaps();i++)blp.getMipmap(i);
 fs.writeFileSync(preview+'/original/palette-decoded.rgba',Buffer.from(blp.getMipmap(0).data));
 fs.writeFileSync(preview+'/sampled-mdx-frames.json',JSON.stringify({model:name,source:'New parse of final MDX and decoded final BLP; offline rendering, not Warcraft capture',frames}));
 const baseline=new Model();baseline.load(new Uint8Array(input));const bsample=helper.sampler(baseline,runtime),bg=bsample(0,baseline.sequences[0].interval[0],true);
 const bdir=preview+'/baseline';fs.mkdirSync(bdir+'/original',{recursive:true});fs.writeFileSync(bdir+'/sampled-mdx-frames.json',JSON.stringify({model:name,frames:[{sequence:'Stand',index:0,geosets:bg.map((g,k)=>({vertices:Array.from(g.vertices),normals:Array.from(g.normals),...geometry[k],uv:Array.from(baseline.geosets[k].uvSets[0])}))}]}));
 const bblp=new BlpImage();bblp.load(new Uint8Array(fs.readFileSync(dir+'/input.blp')));fs.writeFileSync(bdir+'/original/palette-decoded.rgba',Buffer.from(bblp.getMipmap(0).data));
 const report={model:name,name:e.name,status:'PASS',game127aTested:false,modelPath:e.modelImportPath,texturePath:e.requiredTextureImportPath,modelSha256:sha(bytes),textureSha256:sha(blpbytes),modelBytes:bytes.length,textureBytes:blpbytes.length,triangles:r.geosets.reduce((n,g)=>n+g.faces.length/3,0),bones:r.bones.length,geometryCountUnchanged:true,rigAndAnimationKeyframesUnchanged:true,approvedSilverTexturePreserved:name!=='SilverManeBeast'||sha(blpbytes)===e.inputBlpSha256,maxInputSourceDelta:maxInputDelta,eyeGeometryEdits:edits,uvEdits,blp:{version:1,width:blp.width,height:blp.height,alphaBits:blp.alphaBits,mipmaps:blp.mipmaps()},sequences:checks};
 fs.mkdirSync(ROOT+'/validation',{recursive:true});fs.writeFileSync(ROOT+'/validation/'+name+'.json',JSON.stringify(report,null,2)+'\n');reports.push(report);console.log(name+' PASS; '+checks.length+' moving sequences; triangles '+report.triangles);
}
fs.writeFileSync(ROOT+'/validation/batch-a-summary.json',JSON.stringify({status:'PASS',game127aTested:false,models:reports},null,2)+'\n');
