'use strict';
// Append poses to exact published MDX bytes; do not rebuild geometry or textures.
// MDX_PARSER_MODULES=/path/node_modules node tools/BuildPetDisplayModels.cjs --write --preview-dir /scratch/preview
const fs=require('fs'),path=require('path'),cp=require('child_process'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..'),BASE='2847c3f742a69661972cabb7a616e08e81cbae9c';
const runtime=process.env.MDX_PARSER_MODULES||path.dirname(path.dirname(require.resolve('mdx-m3-viewer/package.json')));
const ts=require(runtime+'/typescript');require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const helper=require('../assets/source/elemental-spirits/display-animations.cjs'),{Model}=helper.api(runtime);
const args=process.argv.slice(2),write=args.includes('--write'),pi=args.indexOf('--preview-dir'),preview=pi>=0?path.resolve(args[pi+1]):null;
const manifestPath=path.join(ROOT,'assets/source/elemental-spirits/import-manifest.json'),manifest=JSON.parse(fs.readFileSync(manifestPath)),reports=[];
if(manifest.refinementRevision)throw Error('Refined assets are active. Historical BASE append would overwrite approved geometry/textures. Use python3 tools/BuildSpiritRefinementAssets.py [--write] for the verified isolated rebuild.');
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
for(const entry of manifest.models.slice(1)){
  const relative='imports/'+entry.modelImportPath.replaceAll('\\','/'),model=path.basename(relative,'.mdx');
  const baseline=cp.execFileSync('git',['show',BASE+':'+relative],{cwd:ROOT,maxBuffer:4*1024*1024}),m=new Model();m.load(new Uint8Array(baseline));helper.append(m,model,runtime);
  const bytes=Buffer.from(m.saveMdx());if(!write&&!bytes.equals(fs.readFileSync(path.join(ROOT,relative))))throw Error('Regeneration differs from current import '+model);if(write){fs.writeFileSync(path.join(ROOT,relative),bytes);entry.modelSha256=sha(bytes);entry.modelBytes=bytes.length;}
  const reread=write?fs.readFileSync(path.join(ROOT,relative)):bytes,r=new Model();r.load(new Uint8Array(reread));const sample=helper.sampler(r,runtime),animations=[];
  const geo=r.geosets.map(g=>({faces:Array.from(g.faces),uv:Array.from(g.uvSets[0]),materialId:g.materialId})),frames=[];
  for(let si=5;si<10;si++){
    const s=r.sequences[si],first=sample(si,s.interval[0])[0].vertices,last=sample(si,s.interval[1])[0].vertices;
    let maxChange=0,maxStep=0,previous=first;const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];
    for(let i=0;i<128;i++){
      const time=s.interval[0]+(s.interval[1]-s.interval[0])*(i+.5)/128,v=sample(si,time)[0].vertices;
      for(let k=0;k<v.length;k++){if(!Number.isFinite(v[k]))throw Error('Nonfinite pose');if(v[k]<s.extent.min[k%3]-1e-4||v[k]>s.extent.max[k%3]+1e-4)throw Error('Outside derived extent '+model+'/'+s.name);maxChange=Math.max(maxChange,Math.abs(v[k]-first[k]));maxStep=Math.max(maxStep,Math.abs(v[k]-previous[k]));lo[k%3]=Math.min(lo[k%3],v[k]);hi[k%3]=Math.max(hi[k%3],v[k]);}previous=v;
    }
    const loopDelta=Math.max(...last.map((v,k)=>Math.abs(v-first[k])));if(s.flags===0&&loopDelta>1e-4)throw Error('Loop discontinuity '+model+'/'+s.name);if(maxChange<.05)throw Error('Static display '+model+'/'+s.name);
    let minDot=1;for(const b of r.bones){const tr=b.animations.find(a=>a.name==='KGRT'),keys=tr.frames.map((f,i)=>[f,tr.values[i]]).filter(([f])=>f>=s.interval[0]&&f<=s.interval[1]);for(let i=1;i<keys.length;i++){const dot=keys[i][1].reduce((n,v,k)=>n+v*keys[i-1][1][k],0);minDot=Math.min(minDot,dot);}}if(minDot<.9)throw Error('Quaternion jump '+model+'/'+s.name);
    animations.push({index:si,name:s.name,interval:Array.from(s.interval),loop:s.flags===0,samples:128,maxVertexCoordinateChange:maxChange,maxAdjacentMidpointCoordinateChange:maxStep,loopEndpointMaxDelta:loopDelta,minAdjacentQuaternionDot:minDot,bounds:{min:lo,max:hi},extent:{min:Array.from(s.extent.min),max:Array.from(s.extent.max),radius:s.extent.boundsRadius}});
    if(preview)for(let i=0;i<=16;i++){const gs=sample(si,s.interval[0]+(s.interval[1]-s.interval[0])*i/16,true);frames.push({sequence:s.name,index:i,geosets:gs.map((g,k)=>({vertices:Array.from(g.vertices),normals:Array.from(g.normals),...geo[k]}))});}
  }
  if(preview){const dir=path.join(preview,model);fs.mkdirSync(path.join(dir,'original'),{recursive:true});fs.writeFileSync(path.join(dir,'sampled-mdx-frames.json'),JSON.stringify({model,source:'New parse of final exported MDX bytes; offline only',frames}));
    global.ImageData=class{constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4);}};const {BlpImage}=require(runtime+'/mdx-m3-viewer/src/parsers/blp/image.ts'),blp=new BlpImage();blp.load(new Uint8Array(fs.readFileSync(path.join(ROOT,'imports',entry.requiredTextureImportPath.replaceAll('\\','/')))));fs.writeFileSync(path.join(dir,'original/palette-decoded.rgba'),Buffer.from(blp.getMipmap(0).data));
  }
  const report={species:entry.suggestedSpeciesId,name:entry.name,model,sha256:sha(reread),bytes:reread.length,rawGrowthBytes:reread.length-baseline.length,profile:helper.PROFILES[model],animations};reports.push(report);console.log(model+': 5 display sequences sampled; '+report.rawGrowthBytes+' bytes added');
}
if(write)fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
const report={status:'PASS',baseline:BASE,scope:'14 append-only MDX800 display extensions; no atlas/geometry/rig/runtime scheduler edits',formatBoundary:'New parse of final MDX bytes; not Warcraft rendering or FPS',models:reports,totalGrowthBytes:reports.reduce((n,r)=>n+r.rawGrowthBytes,0)};
if(preview)fs.writeFileSync(path.join(preview,'sampling-report.json'),JSON.stringify(report,null,2)+'\n');else console.log(JSON.stringify(report,null,2));
