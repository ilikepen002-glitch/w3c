'use strict';
// Deterministic generation plus independent final-byte corner/pose verification.
// MDX_PARSER_RUNTIME=/.../node_modules node tools/VerifyClassicBossMesh.cjs [--write]
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto'),cp=require('child_process');
const root=path.resolve(__dirname,'..'); process.chdir(root);
const rt=process.env.MDX_PARSER_RUNTIME; assert(rt,'MDX_PARSER_RUNTIME required');
const ts=require(rt+'/typescript');
require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const Model=require(rt+'/mdx-m3-viewer/src/parsers/mdlx/model.ts').default;
const Geoset=require(rt+'/mdx-m3-viewer/src/parsers/mdlx/geoset.ts').default;
const {optimize,MAX_VERTICES}=require('./ClassicBossMesh.cjs');
const {sampler}=require('../assets/source/elemental-spirits/display-animations.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const parse=b=>{const m=new Model();m.load(new Uint8Array(b));return m;};
function chunks(b){let o=4,r={};while(o<b.length){const tag=b.toString('ascii',o,o+4),n=b.readUInt32LE(o+4);assert(!r[tag]);r[tag]=b.subarray(o,o+8+n);o+=8+n;}assert.equal(o,b.length);return r;}
function groups(g){let o=0;return Array.from(g.matrixGroups,n=>{const ids=Array.from(g.matrixIndices.subarray(o,o+n));o+=n;return ids;});}
// Independent indexed expansion, not the optimizer key or its selected mapping.
function corners(m,pose){const out=[];m.geosets.forEach((g,gi)=>{const gs=groups(g);for(const i of g.faces){out.push([...Array.from((pose?pose[gi].vertices:g.vertices).subarray(i*3,i*3+3)),...Array.from((pose?pose[gi].normals:g.normals).subarray(i*3,i*3+3)),...g.uvSets.flatMap(uv=>Array.from(uv.subarray(i*2,i*2+2))),g.materialId,g.selectionGroup,g.selectionFlags,...gs[g.vertexGroups[i]]]);}});return out;}
function signature(m,pose){const rows=corners(m,pose), values=[];for(const row of rows)values.push(row.length,...row);const binary=new Float64Array(values);return sha(Buffer.from(binary.buffer));}
function audit(m){
 assert.equal(m.globalSequences.length,0);const ids=new Map(m.bones.map(b=>[b.objectId,b]));assert.equal(ids.size,m.bones.length);
 let tracks=0,maxTranslation=0,minScale=Infinity,maxScale=0,maxQuaternionError=0;
 for(const b of m.bones){assert.equal(b.flags,256);assert(b.objectId<m.pivotPoints.length);let p=b,seen=new Set();while(p){assert(!seen.has(p.objectId));seen.add(p.objectId);assert(p.parentId===-1||ids.has(p.parentId));p=ids.get(p.parentId);}
 for(const a of b.animations){tracks++;assert.equal(a.globalSequenceId,-1);assert.equal(a.interpolationType,1);assert(a.frames.every((f,i)=>i===0||f>a.frames[i-1]));assert.equal(a.frames.length,a.values.length);for(const seq of m.sequences){assert(a.frames.includes(seq.interval[0])&&a.frames.includes(seq.interval[1]),'Missing sequence boundary');}for(const v of a.values){assert(Array.from(v).every(Number.isFinite));if(a.name==='KGTR')maxTranslation=Math.max(maxTranslation,Math.hypot(...v));if(a.name==='KGSC'){minScale=Math.min(minScale,...v);maxScale=Math.max(maxScale,...v);}if(a.name==='KGRT')maxQuaternionError=Math.max(maxQuaternionError,Math.abs(Math.hypot(...v)-1));}}
 }
 for(const g of m.geosets){assert.equal(g.matrixGroups.reduce((a,b)=>a+b,0),g.matrixIndices.length);assert(Array.from(g.matrixIndices).every(id=>ids.has(id)));assert(g.matrixGroups.every(n=>n>0&&n<=8));assert.equal(g.sequenceExtents.length,m.sequences.length);assert(g.faces.every(i=>i<g.vertices.length/3));assert(g.vertexGroups.every(i=>i<g.matrixGroups.length));for(const a of [g.vertices,g.normals,...g.uvSets])assert(a.every(Number.isFinite));}
 return {bones:m.bones.length,tracks,globalSequences:0,vertexCounts:m.geosets.map(g=>g.vertices.length/3),matrixGroupCounts:m.geosets.map(g=>g.matrixGroups.length),maxBonesPerGroup:Math.max(...m.geosets.flatMap(g=>Array.from(g.matrixGroups))),maxFaceIndex:Math.max(...m.geosets.flatMap(g=>Array.from(g.faces))),maxTranslation,minScale,maxScale,maxQuaternionError,sequences:m.sequences.map(s=>({name:s.name,interval:Array.from(s.interval),rarity:s.rarity,flags:s.flags})),ribbonEmitters:m.ribbonEmitters.length};
}
const reports=[];
for(const [name,folder] of [['EclipseSpellweaver','eclipse-spellweaver-v3'],['UncrownedAbyssKing','uncrowned-abyss-king']]){
 const file='imports/war3mapImported/'+name+'.mdx';
 const before=cp.execFileSync('git',['show','7834f5c:'+file],{maxBuffer:4e6}), a=parse(before), beforeAudit=audit(a);
 const generated=Buffer.from(optimize(parse(before),Geoset).saveMdx());
 if(process.argv.includes('--write')){
  fs.writeFileSync(file,generated);
  const manifestPath='assets/source/'+folder+'/production-manifest.json',manifest=JSON.parse(fs.readFileSync(manifestPath));
  const entry=manifest.assets.find(x=>x.role==='model');entry.sha256=sha(generated);entry.bytes=generated.length;
  manifest.rawAssetBytes=manifest.assets.reduce((n,x)=>n+x.bytes,0);
  manifest.classicMeshCompatibility={strategy:'Exact attribute deduplication and triangle-order-preserving batches',maxVerticesPerGeoset:MAX_VERTICES,baselineSha256:sha(before),nativeEngineVerified:false};
  fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
 }
 const after=fs.readFileSync(file);assert(after.equals(generated),'Run --write to regenerate target assets');const b=parse(after),afterAudit=audit(b);
 const ac=chunks(before),bc=chunks(after);assert.deepEqual(Object.keys(ac),Object.keys(bc));for(const tag of Object.keys(ac))if(tag!=='GEOS')assert(ac[tag].equals(bc[tag]),'Changed non-GEOS '+tag);
 assert.equal(signature(a),signature(b),'Ordered corners differ');
 assert.equal(a.geosets.length,1,'Frozen originals must each have one geoset');
 for(const g of b.geosets)for(const key of ['matrixGroups','matrixIndices','materialId','selectionGroup','selectionFlags','extent','sequenceExtents','faceTypeGroups'])assert.deepEqual(g[key],a.geosets[0][key],'Changed geoset metadata '+key);
 assert(b.geosets.every(g=>g.vertices.length/3<=MAX_VERTICES));assert(Buffer.from(b.saveMdx()).equals(after));
 const sa=sampler(a,rt),sb=sampler(b,rt);let poses=0;
 for(let si=0;si<a.sequences.length;si++){const [lo,hi]=a.sequences[si].interval;const times=new Set(Array.from({length:33},(_,i)=>lo+(hi-lo)*i/32));for(const bone of a.bones)for(const t of bone.animations)for(const f of t.frames)if(f>=lo&&f<=hi)times.add(f);for(const time of times){assert.equal(signature(a,sa(si,time,true)),signature(b,sb(si,time,true)),'Pose differs '+si+'/'+time);poses++;}}
 // Reject unsafe reuse and ensure verification catches UV, normal and skin changes.
 let negatives=0;for(const mutate of [m=>m.version=1000,m=>m.geosetAnimations.push({}),m=>m.bones[0].geosetId=0,m=>m.geosets[0].faces[0]=65535]){const m=parse(before);mutate(m);assert.throws(()=>optimize(m,Geoset));negatives++;}
 for(const mutate of [m=>m.geosets[0].uvSets[0][0]+=.1,m=>m.geosets[0].normals[0]+=.1,m=>m.geosets[0].vertexGroups[0]=(m.geosets[0].vertexGroups[0]+1)%m.geosets[0].matrixGroups.length]){const m=parse(after);mutate(m);assert.notEqual(signature(a),signature(m));negatives++;}
 reports.push({name,beforeSha256:sha(before),afterSha256:sha(after),beforeBytes:before.length,afterBytes:after.length,before:beforeAudit,after:afterAudit,orderedCorners:a.geosets.reduce((s,g)=>s+g.faces.length,0),orderedCornerSignature:signature(b),sampledPoses:poses,maxPoseCornerDifference:0,unchangedNonGeosChunks:Object.keys(ac).filter(x=>x!=='GEOS'),negativeCases:negatives});
}
const report={status:'PASS',nativeEngineVerified:false,scope:'Asset-local compatibility candidate, not a proven root-cause fix. No scale, gameplay, texture or animation edits.',reports};
fs.mkdirSync('docs/validation/2026-10-15-classic-boss-mesh',{recursive:true});fs.writeFileSync('docs/validation/2026-10-15-classic-boss-mesh/report.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
