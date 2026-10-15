'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..'),BASE=path.resolve(process.argv[2]),runtime=process.env.MDX_PARSER_MODULES;
const ts=require(runtime+'/typescript');require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const h=require('../assets/source/elemental-spirits/display-animations.cjs'),{Model}=h.api(runtime);
global.ImageData=class{constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4);}};
const {BlpImage}=require(runtime+'/mdx-m3-viewer/src/parsers/blp/image.ts');
const rows=JSON.parse(fs.readFileSync(path.join(ROOT,'evidence/water-earth-hashes.json'))),report=[];
for(const row of rows){
 const model=row.model,out=path.join(ROOT,'evidence',model);fs.mkdirSync(out,{recursive:true});
 const models={};for(const [kind,root] of [['before',BASE],['after',ROOT]]){const m=new Model();const bytes=fs.readFileSync(path.join(root,'imports',row.modelImportPath.replaceAll('\\','/')));m.load(new Uint8Array(bytes));models[kind]=m;
 const blp=new BlpImage();blp.load(new Uint8Array(fs.readFileSync(path.join(root,'imports',row.requiredTextureImportPath.replaceAll('\\','/')))));for(let i=0;i<blp.mipmaps();i++)blp.getMipmap(i);fs.writeFileSync(path.join(out,kind+'.rgba'),Buffer.from(blp.getMipmap(0).data));
 const sample=h.sampler(m,runtime),frames=[];for(const [si,fractions] of [[0,[.2]],[1,[.2,.5,.8]],...[5,6,7,8,9].map(si=>[si,[.2,.5,.8]])])for(const u of fractions){const s=m.sequences[si];frames.push({sequence:s.name,index:si,fraction:u,geosets:sample(si,s.interval[0]+(s.interval[1]-s.interval[0])*u,true).map((g,k)=>({vertices:Array.from(g.vertices),normals:Array.from(g.normals),faces:Array.from(m.geosets[k].faces),uv:Array.from(m.geosets[k].uvSets[0])}))});}
 fs.writeFileSync(path.join(out,kind+'-frames.json'),JSON.stringify({model,source:'New parse of final MDX + decoded BLP; offline rendering only',frames}));}
 const a=models.before,b=models.after;
 const bonesEqual=JSON.stringify(a.bones)===JSON.stringify(b.bones),pivotsEqual=JSON.stringify(a.pivotPoints)===JSON.stringify(b.pivotPoints),sequencesEqual=JSON.stringify(a.sequences.map(s=>[s.name,Array.from(s.interval),s.flags,s.moveSpeed]))===JSON.stringify(b.sequences.map(s=>[s.name,Array.from(s.interval),s.flags,s.moveSpeed]));
 if(!bonesEqual||!pivotsEqual||!sequencesEqual)throw Error('Animation contract changed '+model+' '+JSON.stringify({bonesEqual,pivotsEqual,sequencesEqual}));
 const sample=h.sampler(b,runtime),animations=[];for(let si=0;si<10;si++){const s=b.sequences[si],first=sample(si,s.interval[0])[0].vertices,last=sample(si,s.interval[1])[0].vertices;let delta=0,outside=0;for(let i=0;i<=64;i++){for(const g of sample(si,s.interval[0]+(s.interval[1]-s.interval[0])*i/64))for(let k=0;k<g.vertices.length;k++){const v=g.vertices[k];if(!Number.isFinite(v))throw Error('nonfinite '+model);delta=Math.max(delta,Math.abs(v-first[k]));if(v<s.extent.min[k%3]-.01||v>s.extent.max[k%3]+.01)outside++;}}const loopDelta=Math.max(...last.map((v,k)=>Math.abs(v-first[k])));if(outside||delta<.05||(s.flags===0&&loopDelta>.001))throw Error('Invalid pose '+model+'/'+s.name+' '+JSON.stringify({outside,delta,loopDelta}));animations.push({index:si,name:s.name,samples:65,maxCoordinateChange:delta,loopEndpointDelta:loopDelta,outsideSequenceExtent:outside});}
 report.push({...row,version:b.version,bones:b.bones.length,trianglesBefore:a.geosets.reduce((s,g)=>s+g.faces.length/3,0),trianglesAfter:b.geosets.reduce((s,g)=>s+g.faces.length/3,0),bonesEqual,pivotsEqual,sequencesEqual,animations});console.log(model+' PASS: all 10 sequence identities and every bone key unchanged; parsed 65 samples per animation');
}
fs.writeFileSync(path.join(ROOT,'evidence/water-earth-contract-validation.json'),JSON.stringify({status:'PASS',game127aTested:false,models:report},null,2)+'\n');
