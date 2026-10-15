'use strict';
// Read-only final-MDX/BLP inspection. This is not Warcraft rendering or FPS.
// MDX_PARSER_MODULES=/path/node_modules node tools/InspectSpiritRefinementModels.cjs [--output /tmp/report.json]
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..');
const runtime=process.env.MDX_PARSER_MODULES||path.dirname(path.dirname(require.resolve('mdx-m3-viewer/package.json')));
const ts=require(runtime+'/typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const helper=require('../assets/source/elemental-spirits/display-animations.cjs');
const {Model,createTypedSd}=helper.api(runtime);
global.ImageData=class{constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4);}};
const {BlpImage}=require(runtime+'/mdx-m3-viewer/src/parsers/blp/image.ts');
const args=process.argv.slice(2),oi=args.indexOf('--output'),manifest=JSON.parse(fs.readFileSync(path.join(ROOT,'assets/source/elemental-spirits/import-manifest.json')));
const expected=[['Stand',0,2000,0],['Walk',2100,3100,0],['Attack',3200,3900,1],['Death',4000,5400,1],['Portrait',5500,7500,0],['Display Float',8000,10000,0],['Display Jump',10100,10900,1],['Display Spin',11000,12200,1],['Display Sleep',12300,15300,0],['Display Cast',15400,16600,1]];
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const requireOk=(v,m)=>{if(!v)throw Error(m);};
const finite=a=>Array.from(a).every(Number.isFinite);
const inside=(v,e,tol=.02)=>v.every((n,k)=>n>=e.min[k%3]-tol&&n<=e.max[k%3]+tol);
const ext=e=>({min:Array.from(e.min),max:Array.from(e.max),radius:e.boundsRadius});
const textureCache=new Map();
function texture(t){
 if(t.replaceableId)return {path:t.path,replaceableId:t.replaceableId,kind:'native-replaceable'};
 requireOk(t.path&&!t.path.includes('\\\\')&&!t.path.includes('/')&&!t.path.includes('..'),'Noncanonical TEXS path '+JSON.stringify(t.path));
 const p=path.join(ROOT,'imports',t.path.replaceAll('\\','/'));
 if(!fs.existsSync(p))return {path:t.path,replaceableId:0,kind:'external-native-unverified'};
 if(!textureCache.has(t.path)){
  const b=fs.readFileSync(p);requireOk(b.subarray(0,4).toString()==='BLP1','Texture is not BLP1 '+t.path);
  const blp=new BlpImage();blp.load(new Uint8Array(b));requireOk(blp.width>0&&blp.height>0&&blp.width<=1024&&blp.height<=1024,'Texture dimensions');
  requireOk((blp.width&(blp.width-1))===0&&(blp.height&(blp.height-1))===0,'Non-power-of-two texture');
  let lo=255,hi=0;for(let i=0;i<blp.mipmaps();i++){const rgba=blp.getMipmap(i).data;requireOk(rgba.length>0,'Empty mip');if(i===0)for(let a=3;a<rgba.length;a+=4){lo=Math.min(lo,rgba[a]);hi=Math.max(hi,rgba[a]);}}
  requireOk(blp.mipmaps()===Math.floor(Math.log2(Math.max(blp.width,blp.height)))+1,'Incomplete mip chain '+t.path);
  textureCache.set(t.path,{path:t.path,replaceableId:0,kind:'packaged-custom',sha256:sha(b),bytes:b.length,width:blp.width,height:blp.height,mipmaps:blp.mipmaps(),alphaBits:blp.alphaBits,alphaRange:[lo,hi]});
 }
 return textureCache.get(t.path);
}
const models=[];
for(const entry of manifest.models){
 const bytes=fs.readFileSync(path.join(ROOT,'imports',entry.modelImportPath.replaceAll('\\','/'))),m=new Model();m.load(new Uint8Array(bytes));
 requireOk(m.version===800,'Not MDX800 '+entry.name);
 requireOk(sha(bytes)===entry.modelSha256&&bytes.length===entry.modelBytes,'Manifest MDX hash/length '+entry.name);
 requireOk(m.sequences.length>=10,'Missing required sequences '+entry.name);
 for(let i=0;i<10;i++){const s=m.sequences[i],e=expected[i];requireOk(s.name===e[0]&&s.interval[0]===e[1]&&s.interval[1]===e[2]&&s.flags===e[3],'Sequence contract '+entry.name+'/'+i);}
 let triangles=0,vertices=0;
 for(const g of m.geosets){
  requireOk(g.vertices.length===g.normals.length&&g.vertices.length/3===g.vertexGroups.length,'Vertex array mismatch');
  requireOk(g.uvSets.length>=1&&g.uvSets[0].length/2===g.vertexGroups.length,'UV array mismatch');
  requireOk(finite(g.vertices)&&finite(g.normals)&&g.uvSets.every(finite),'Nonfinite geometry');
  requireOk(g.faces.length%3===0&&Array.from(g.faces).every(i=>i<g.vertexGroups.length),'Bad faces');
  requireOk(g.sequenceExtents.length===m.sequences.length,'Sequence extent count');
  requireOk(g.materialId<m.materials.length,'Bad material id');
  requireOk(g.matrixGroups.reduce((n,x)=>n+x,0)===g.matrixIndices.length,'Bad matrix group counts');
  requireOk(Array.from(g.vertexGroups).every(i=>i<g.matrixGroups.length),'Bad matrix group index');
  triangles+=g.faces.length/3;vertices+=g.vertices.length/3;
 }
 requireOk(triangles===entry.triangles&&m.bones.length===entry.bones,'Manifest geometry statistics '+entry.name);
 const textureReports=m.textures.map(texture);
 for(const t of textureReports)if(t.kind==='external-native-unverified')requireOk((entry.nativeTexturePaths||[]).includes(t.path),'Missing unclassified texture '+entry.name+'/'+t.path);
 if(entry.customTextures){const actual=textureReports.filter(t=>t.kind==='packaged-custom');requireOk(actual.length===entry.customTextures.length,'Custom texture manifest count');for(const t of actual){const declared=entry.customTextures.find(x=>x.path===t.path);requireOk(declared&&declared.sha256===t.sha256&&declared.bytes===t.bytes,'Additional custom texture manifest '+t.path);}}
 const required=textureReports.find(t=>t.path===entry.requiredTextureImportPath);
 requireOk(required&&required.kind==='packaged-custom'&&required.sha256===entry.textureSha256&&required.bytes===entry.textureBytes,'Primary texture manifest '+entry.name);
 const materials=m.materials.map(mat=>({priorityPlane:mat.priorityPlane,flags:mat.flags,layers:mat.layers.map(l=>{
  requireOk(l.textureId>=0&&l.textureId<m.textures.length,'Bad layer texture id');
  requireOk(l.filterMode>=0&&l.filterMode<=6&&Number.isFinite(l.alpha),'Bad material');
  return {textureId:l.textureId,filterMode:l.filterMode,flags:l.flags,alpha:l.alpha};
 })}));
 const sample=helper.sampler(m,runtime),sequenceReports=[];
 const alphaTracks=new Map(m.geosetAnimations.map(g=>[g.geosetId,{base:g.alpha,track:g.animations.find(a=>a.name==='KGAO')}]).map(([id,g])=>[id,{base:g.base,track:g.track?createTypedSd(m,g.track):null}]));
 function visible(gi,si,t){const a=alphaTracks.get(gi);if(!a)return true;const v=[a.base];if(a.track)a.track.getValue(v,si,t,t-m.sequences[si].interval[0]);return v[0]>.001;}
 for(let si=0;si<m.sequences.length;si++){
  const s=m.sequences[si],lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity],bodyLo=[Infinity,Infinity,Infinity],bodyHi=[-Infinity,-Infinity,-Infinity],first=sample(si,s.interval[0]);let motion=0,outside=0,visibleSamples=0;
  for(let i=0;i<=64;i++){
   const t=s.interval[0]+(s.interval[1]-s.interval[0])*i/64;
   const pose=sample(si,t);
   for(let gi=0;gi<pose.length;gi++){
    const v=pose[gi].vertices;requireOk(finite(v),'Nonfinite sampled pose '+entry.name+'/'+s.name);
    if(!visible(gi,si,t))continue;visibleSamples++;
    for(let k=0;k<v.length;k++){lo[k%3]=Math.min(lo[k%3],v[k]);hi[k%3]=Math.max(hi[k%3],v[k]);motion=Math.max(motion,Math.abs(v[k]-first[gi].vertices[k]));if(!entry.mainBodyGeosetIndices||entry.mainBodyGeosetIndices.includes(gi)){bodyLo[k%3]=Math.min(bodyLo[k%3],v[k]);bodyHi[k%3]=Math.max(bodyHi[k%3],v[k]);}}
    if(!inside(v,s.extent)||!inside(v,m.geosets[gi].sequenceExtents[si]))outside++;
   }
  }
  requireOk(outside===0,'Sampled visible geometry outside culling bounds '+entry.name+'/'+s.name+' ('+outside+')');
  if(si<10)requireOk(visibleSamples>0,'Required sequence invisible '+entry.name+'/'+s.name);
  if(si===1||si>=5&&si<10)requireOk(motion>.05,'Static required animation '+entry.name+'/'+s.name);
  sequenceReports.push({index:si,name:s.name,interval:Array.from(s.interval),loop:s.flags===0,samples:65,maxCoordinateMotion:motion,visibleGeosetSamples:visibleSamples,bounds:visibleSamples?{min:lo,max:hi}:null,bodyBounds:Number.isFinite(bodyLo[0])?{min:bodyLo,max:bodyHi}:null,extent:ext(s.extent)});
 }
 const fxBudget=[];
 function animatedValue(object,tag,fallback,si,time){const a=object.animations.find(x=>x.name===tag);if(!a)return fallback;const out=[fallback];createTypedSd(m,a).getValue(out,si,time,time-m.sequences[si].interval[0]);return out[0];}
 for(let si=0;si<Math.min(10,m.sequences.length);si++){
  const seq=m.sequences[si];let particles=0,ribbons=0,emitters=0;
  for(let i=0;i<=32;i++){
   const t=seq.interval[0]+(seq.interval[1]-seq.interval[0])*i/32;
   let np=0,nr=0,ne=0;
   for(const e of m.particleEmitters2){const vis=animatedValue(e,'KP2V',1,si,t),rate=animatedValue(e,'KP2E',e.emissionRate,si,t);if(vis>.001&&rate>0){np+=rate*e.lifeSpan;ne++;}}
   for(const e of m.ribbonEmitters){const vis=animatedValue(e,'KRVS',1,si,t),alpha=animatedValue(e,'KRAL',e.alpha,si,t);if(vis>.001&&alpha>.001)nr+=e.emissionRate*e.lifeSpan;}
   particles=Math.max(particles,np);ribbons=Math.max(ribbons,nr);emitters=Math.max(emitters,ne);
  }
  fxBudget.push({index:si,name:seq.name,maxRateTimesLifeParticleEstimate:particles,maxRateTimesLifeRibbonSegmentEstimate:ribbons,maxActiveParticleEmitterCount:emitters});
  if(entry.runtimeFxBudget&&si!==3){requireOk(particles<=entry.runtimeFxBudget.maxSteadyParticles+.001,'Phoenix steady particle budget '+seq.name);requireOk(ribbons<=entry.runtimeFxBudget.maxSteadyRibbonSegments+.001,'Phoenix ribbon budget '+seq.name);}
 }
 models.push({species:entry.suggestedSpeciesId,name:entry.name,path:entry.modelImportPath,sha256:sha(bytes),bytes:bytes.length,version:m.version,triangles,vertices,bones:m.bones.length,helpers:m.helpers.length,geosets:m.geosets.length,particleEmitters:m.particleEmitters.length,particleEmitters2:m.particleEmitters2.length,ribbonEmitters:m.ribbonEmitters.length,globalSequences:Array.from(m.globalSequences),materials,textures:textureReports,sequences:sequenceReports,fxBudget});
 console.error(entry.name+': final MDX/BLP and '+m.sequences.length+' sequence bounds PASS');
}
const report={status:'PASS',boundary:'Final-byte structural and sampled-pose checks; billboard camera rotation, emitters, native texture rendering, Warcraft performance and in-game appearance are not tested.',models,totalModelBytes:models.reduce((n,m)=>n+m.bytes,0),totalTriangles:models.reduce((n,m)=>n+m.triangles,0),uniqueCustomTextureBytes:[...textureCache.values()].reduce((n,t)=>n+t.bytes,0)};
if(oi>=0)fs.writeFileSync(args[oi+1],JSON.stringify(report,null,2)+'\n');else console.log(JSON.stringify(report,null,2));
