'use strict';
// Resource-only ground-origin variant; no animation, hierarchy or gameplay edits.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..'),runtime=process.env.MDX_PARSER_MODULES;
if(!runtime)throw Error('Set MDX_PARSER_MODULES');
const ts=require(runtime+'/typescript');require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const helper=require('../assets/source/elemental-spirits/display-animations.cjs'),{Model,createTypedSd}=helper.api(runtime);
const config=JSON.parse(fs.readFileSync(path.join(ROOT,'assets/source/elemental-spirits/refinement-20261015/wild-phoenix.json')));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const bytes=fs.readFileSync(path.join(ROOT,config.source)),before=new Model();before.load(bytes);
if(sha(bytes)!==config.sourceSha256)throw Error('Wild variant source pin mismatch');
if(!Number.isFinite(config.zOffset)||config.zOffset<0||config.zOffset>200)throw Error('Unexpected ground-origin offset');
const m=new Model();m.load(bytes);const z=config.zOffset;
// Wild units never call tower-display indices. Keep only the five base aliases,
// retaining every referenced key/tangent and all wall-clock global tracks.
const retainedTrackAudit=[];
function trimTracks(o,label='model'){
 if(!o||typeof o!=='object'||ArrayBuffer.isView(o))return;
 if(Array.isArray(o.animations))for(const t of o.animations){
  if(t.globalSequenceId>=0)continue;
  const keep=t.frames.map((f,i)=>[f,i]).filter(([f])=>f<=7500).map(([,i])=>i);
  retainedTrackAudit.push({path:label,tag:t.name,before:t.frames.length,after:keep.length});
  t.frames=keep.map(i=>t.frames[i]);t.values=keep.map(i=>t.values[i]);
  if(t.interpolationType>1){t.inTans=keep.map(i=>t.inTans[i]);t.outTans=keep.map(i=>t.outTans[i]);}
 }
 for(const [k,v]of Object.entries(o))if(k!=='animations'){
  if(Array.isArray(v))v.forEach((x,i)=>trimTracks(x,label+'.'+k+'.'+i));
  else if(v&&typeof v==='object')trimTracks(v,label+'.'+k);
 }
}
trimTracks(m);
for(const e of m.eventObjects)if(e.globalSequenceId<0)e.tracks=new Uint32Array(Array.from(e.tracks).filter(f=>f<=7500));
m.sequences=m.sequences.slice(0,5);for(const g of m.geosets)g.sequenceExtents=g.sequenceExtents.slice(0,5);
const nonCoordinates=o=>JSON.stringify(o,(k,v)=>['vertices','extent','sequenceExtents','pivotPoints','position','targetPosition'].includes(k)?undefined:ArrayBuffer.isView(v)?Array.from(v):v);
const expectedNonCoordinates=nonCoordinates(m);
const shift=v=>{v[2]+=z;};
const shiftExtent=e=>{shift(e.min);shift(e.max);e.boundsRadius=Math.max(e.boundsRadius,Math.hypot(...Array.from(e.min,(v,k)=>Math.max(Math.abs(v),Math.abs(e.max[k])))));};
for(const g of m.geosets){for(let i=2;i<g.vertices.length;i+=3)g.vertices[i]+=z;shiftExtent(g.extent);g.sequenceExtents.forEach(shiftExtent);}
m.pivotPoints.forEach(shift);m.sequences.forEach(s=>shiftExtent(s.extent));shiftExtent(m.extent);
for(const c of m.cameras){shift(c.position);shift(c.targetPosition);}
for(const c of m.collisionShapes){for(let i=2;i<c.vertices.length;i+=3)c.vertices[i]+=z;}
const out=path.join(ROOT,config.output);fs.mkdirSync(path.dirname(out),{recursive:true});fs.writeFileSync(out,Buffer.from(m.saveMdx()));
const finalBytes=fs.readFileSync(out),r=new Model();r.load(finalBytes);
if(nonCoordinates(r)!==expectedNonCoordinates)throw Error('Wild variant changed preserved static data or retained animation keys/tangents');
function chunks(b){const result={};for(let i=4;i<b.length;){const t=b.subarray(i,i+4).toString(),s=b.readUInt32LE(i+4);result[t]=b.subarray(i+8,i+8+s);i+=8+s;}return result;}
const a=chunks(bytes),b=chunks(finalBytes),changed=[];if(Object.keys(a).join()!=Object.keys(b).join())throw Error('Wild variant chunk set changed');
for(const key in a)if(!a[key].equals(b[key])){if(!['MODL','SEQS','GEOS','PIVT','CAMS','CLID','BONE','HELP','MTLS','GEOA','ATCH','PRE2','PREM','RIBB','EVTS','TXAN','LITE'].includes(key))throw Error('Wild variant changed non-coordinate chunk '+key);changed.push(key);}
const sampleBefore=helper.sampler(before,runtime),sampleAfter=helper.sampler(r,runtime);
const alphaTracks=new Map(r.geosetAnimations.map(g=>[g.geosetId,{base:g.alpha,track:g.animations.find(a=>a.name==='KGAO')}]).map(([id,g])=>[id,{base:g.base,track:g.track?createTypedSd(r,g.track):null}]));
function alpha(gi,si,t){const a=alphaTracks.get(gi);if(!a)return 1;const v=[a.base];if(a.track)a.track.getValue(v,si,t,t-r.sequences[si].interval[0]);return v[0];}
const seqReports=[],frames=[];let maxTranslationError=0;
for(let si=0;si<r.sequences.length;si++){
 const s=r.sequences[si],lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];let visible=0;
 for(let i=0;i<=256;i++){
  const time=s.interval[0]+(s.interval[1]-s.interval[0])*i/256,old=sampleBefore(si,time),now=sampleAfter(si,time,true);
  for(let gi=0;gi<now.length;gi++){
   const v=now[gi].vertices;
   for(let k=0;k<v.length;k++)maxTranslationError=Math.max(maxTranslationError,Math.abs(v[k]-old[gi].vertices[k]-(k%3===2?z:0)));
   if(!config.mainBodyGeosetIndices.includes(gi)||alpha(gi,si,time)<=.001)continue;
   visible++;
   for(let k=0;k<v.length;k++){lo[k%3]=Math.min(lo[k%3],v[k]);hi[k%3]=Math.max(hi[k%3],v[k]);}
  }
  if(si<4&&i%64===0)frames.push({sequence:s.name,index:i/64,time,geosets:now.map((g,gi)=>({index:gi,vertices:Array.from(g.vertices),normals:Array.from(g.normals),faces:Array.from(r.geosets[gi].faces),uv:Array.from(r.geosets[gi].uvSets[0]),materialId:r.geosets[gi].materialId,alpha:alpha(gi,si,time)}))});
 }
 seqReports.push({index:si,name:s.name,samples:257,visibleBodySamples:visible,bounds:visible?{min:lo,max:hi}:null,scaledBounds:visible?{min:lo.map(x=>x*config.wildScale),max:hi.map(x=>x*config.wildScale)}:null});
}
if(maxTranslationError>.001)throw Error('World translation invariant failed '+maxTranslationError);
for(const s of seqReports.slice(0,2))if(s.bounds.min[2]<-.01)throw Error('Wild Stand/Walk body crosses ground plane');
const report={status:'PASS',sourceSha256:sha(bytes),outputSha256:sha(finalBytes),sourceBytes:bytes.length,outputBytes:finalBytes.length,zOffset:z,wildScale:config.wildScale,mainBodyGeosetIndices:config.mainBodyGeosetIndices,changedCoordinateChunks:changed,unchangedChunkBytes:Object.keys(a).filter(k=>a[k].equals(b[k])),retainedSequences:[0,1,2,3,4],retainedStaticDataAndKeysTangentsExact:true,retainedTrackAudit,maxSampledWorldTranslationError:maxTranslationError,sequences:seqReports,boundary:'Offline 257-phase model-coordinate audit. Native terrain/renderer, particles, billboards and game engine behavior untested.'};
const audit=path.join(ROOT,'evidence/wild-phoenix');fs.mkdirSync(audit,{recursive:true});fs.writeFileSync(path.join(audit,'variant-report.json'),JSON.stringify(report,null,2)+'\n');fs.writeFileSync(path.join(audit,'frames.json'),JSON.stringify({model:'EmberBirdWild',frames}));
console.log(JSON.stringify(report,null,2));
