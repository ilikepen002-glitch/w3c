'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const rt=process.env.MDX_PARSER_RUNTIME;if(!rt)throw Error('Set MDX_PARSER_RUNTIME to the repository-pinned mdx-m3-viewer 5.7.9 runtime');
for(const [name,version] of [['mdx-m3-viewer','5.7.9'],['typescript','4.9.5'],['gl-matrix','3.4.4']])if(require(rt+'/'+name+'/package.json').version!==version)throw Error('Unexpected parser dependency '+name);
const ts=require(rt+'/typescript');require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const base=rt+'/mdx-m3-viewer/src',get=n=>require(base+'/parsers/mdlx/'+n+'.ts').default;
const Model=get('model'),Geoset=get('geoset'),GeosetAnimation=get('geosetanimation'),Bone=get('bone'),Sequence=get('sequence'),Texture=get('texture'),Material=get('material'),Layer=get('layer'),Extent=get('extent');
const {FloatAnimation,Vector3Animation,Vector4Animation}=require(base+'/parsers/mdlx/animations.ts'),{createTypedSd}=require(base+'/viewer/handlers/mdx/sd.ts');
const {vec3,quat}=require(rt+'/gl-matrix');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const OUT=path.join(__dirname,'output');fs.mkdirSync(OUT,{recursive:true});
const names=['TDPetVfxSwordDomain','TDPetVfxFrostDomain','TDPetVfxVortexDomain','TDPetVfxStarfallDomain','TDPetVfxEarthSealDomain','TDPetVfxFlowerBloomLoop','TDPetVfxLotusBurstLoop'];
if(process.argv.includes('--timeline'))names.push('TDPetVfxFrostPrison','TDPetVfxStarfall');
const reports=[],preview={source:'Fresh parse of actual on-disk MDX800 bytes. No source geometry is used for frame previews.',inGameTested:false,models:[]};
function anim(tag,entries,interpolation=1){const C=tag==='KGRT'?Vector4Animation:(tag==='KGSC'||tag==='KGTR'||tag==='KGAC'?Vector3Animation:FloatAnimation),a=new C();a.name=tag;a.interpolationType=interpolation;for(const [f,v]of entries){a.frames.push(f);a.values.push(new Float32Array(Array.isArray(v)?v:[v]));}return a;}
function ext(src){const e=new Extent();e.min.set(src.bounds.min);e.max.set(src.bounds.max);e.boundsRadius=Math.hypot(...src.bounds.max.map((x,k)=>Math.max(Math.abs(x),Math.abs(src.bounds.min[k]))));return e;}
function cross(a,b,c){const u=b.map((v,k)=>v-a[k]),v=c.map((x,k)=>x-a[k]);return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];}
function getFrame(r,si,t){const time=Math.max(r.sequences[si].interval[0],Math.min(t,r.sequences[si].interval[1]));
 const sample=(a,defaultValue)=>{if(!a)return defaultValue;const v=new Float32Array(defaultValue.length);createTypedSd(r,a).getValue(v,si,time,time-r.sequences[si].interval[0]);return Array.from(v);};
 return {time,sequence:r.sequences[si].name,alphas:r.geosetAnimations.map(a=>sample(a.animations.find(a=>a.name==='KGAO'),[a.alpha])[0]),colors:r.geosetAnimations.map(a=>sample(a.animations.find(a=>a.name==='KGAC'),Array.from(a.color)).reverse()),layers:r.materials.map(m=>m.layers.map(l=>sample(l.animations.find(a=>a.name==='KMTA'),[l.alpha])[0])),bones:r.bones.map((b,i)=>({pivot:Array.from(r.pivotPoints[i]),translation:sample(b.animations.find(a=>a.name==='KGTR'),[0,0,0]),scale:sample(b.animations.find(a=>a.name==='KGSC'),[1,1,1]),rotation:sample(b.animations.find(a=>a.name==='KGRT'),[0,0,0,1])}))};
}
function pose(g,i,f){const group=g.vertexGroups[i];let offset=0;for(let j=0;j<group;j++)offset+=g.matrixGroups[j];const id=g.matrixIndices[offset];if(g.matrixGroups[group]!==1)throw Error('Multiple influence not supported by this verifier');const b=f.bones[id],p=g.vertices.slice(i*3,i*3+3);const out=vec3.fromValues(...Array.from(p,(x,k)=>(x-b.pivot[k])*b.scale[k]));vec3.transformQuat(out,out,b.rotation);return Array.from(out,(x,k)=>x+b.pivot[k]+b.translation[k]);}
for(const name of names){
 const src=JSON.parse(fs.readFileSync(path.join(__dirname,'generated-source',name+'.json'))),m=new Model();m.name=name;m.version=800;m.blendTime=0;m.extent=ext(src);
 const tex=new Texture();tex.path=src.texture;m.textures.push(tex);
 for(const [name,start,end,loop] of [['Stand',0,src.endMs,src.loop],['Death',10000,10001,false]]){const s=new Sequence();s.name=name;s.interval.set([start,end]);s.flags=loop?0:1;s.extent=ext(src);m.sequences.push(s);}
 for(const [i,sb]of src.bones.entries()){const b=new Bone();b.name=sb.name;b.objectId=i;b.parentId=-1;b.geosetId=-1;b.geosetAnimationId=-1;for(const a of sb.tracks)b.animations.push(anim(a.tag,a.entries,a.interpolation));m.bones.push(b);m.pivotPoints.push(new Float32Array(sb.pivot));}
 for(let i=0;i<2;i++){const mat=new Material(),l=new Layer();l.filterMode=i?3:2;l.flags=i?129:1;l.textureId=0;l.animations.push(anim('KMTA',[[0,1],[src.endMs,1],[10000,0],[10001,0]]));mat.layers.push(l);m.materials.push(mat);}
 for(const [gi,sg]of src.geosets.entries()){
  const g=new Geoset(),v=[],n=[],uv=[],idx=[],groups=[];
  for(const p of sg.parts)for(const f of p.faces){const nn=cross(...f.map(i=>p.vertices[i])),len=Math.hypot(...nn);if(len<1e-6)throw Error('Degenerate source '+p.name);for(const vi of f){idx.push(v.length/3);v.push(...p.vertices[vi]);n.push(...nn.map(x=>x/len));uv.push(.5,.5);groups.push(p.bone);}}
  g.vertices=new Float32Array(v);g.normals=new Float32Array(n);g.faces=new Uint16Array(idx);g.uvSets=[new Float32Array(uv)];g.vertexGroups=new Uint8Array(groups);g.matrixGroups=new Uint32Array(src.bones.map(()=>1));g.matrixIndices=new Uint32Array(src.bones.map((_,i)=>i));g.faceTypeGroups=new Uint32Array([4]);g.faceGroups=new Uint32Array([idx.length]);g.materialId=sg.material;g.extent=ext(src);g.sequenceExtents=[ext(src),ext(src)];m.geosets.push(g);
  const ga=new GeosetAnimation();ga.geosetId=gi;ga.alpha=1;ga.flags=2;ga.color.set(sg.color.slice().reverse());ga.animations.push(anim('KGAO',sg.alpha.concat([[10000,0],[10001,0]])));if(sg.colorKeys)ga.animations.push(anim('KGAC',sg.colorKeys.concat([[10000,sg.colorKeys.at(-1)[1]],[10001,sg.colorKeys.at(-1)[1]]]).map(([t,c])=>[t,c.slice().reverse()])));m.geosetAnimations.push(ga);
 }
 const fp=path.join(OUT,name+'.mdx'),bytes=Buffer.from(m.saveMdx());fs.writeFileSync(fp,bytes);fs.writeFileSync(path.join(OUT,name+'.mdl'),m.saveMdl());
 // From here onward validation and animation sampling use freshly reparsed bytes.
 const r=new Model();r.load(new Uint8Array(fs.readFileSync(fp)));if(!Buffer.from(r.saveMdx()).equals(bytes))throw Error(name+' binary roundtrip');
 const mdl=new Model();mdl.load(r.saveMdl());let textError=0;if(mdl.version!==800||mdl.geosets.length!==r.geosets.length)throw Error('MDL semantic mismatch');
 for(let gi=0;gi<r.geosets.length;gi++){const a=r.geosets[gi],b=mdl.geosets[gi];if(String(a.faces)!==String(b.faces))throw Error('MDL faces');for(const fld of ['vertices','normals']){if(a[fld].length!==b[fld].length)throw Error('MDL geometry');for(let k=0;k<a[fld].length;k++)textError=Math.max(textError,Math.abs(a[fld][k]-b[fld][k]));}}if(textError>1e-4)throw Error('MDL precision');
 if(r.version!==800||r.textures.length!==1||r.textures[0].path!=='Textures\\TDPetVfxSolidWhite.blp'||r.sequences.length!==2||r.sequences[0].flags!==(src.loop?0:1)||r.sequences[1].flags!==1)throw Error('Format contract');
 if(r.bones.length>8||r.materials.length>2||r.globalSequences.length||r.particleEmitters.length||r.particleEmitters2.length||r.ribbonEmitters.length||r.eventObjects.length||r.cameras.length||r.lights.length||r.attachments.length)throw Error('Unexpected feature or node budget');
 for(const mat of r.materials)for(const l of mat.layers){if(l.flags&16||l.flags&64||l.textureId!==0||![2,3].includes(l.filterMode))throw Error('Material contract');}
 let cornerError=0,closed=0,planes=0;const topology=[];
 for(const [gi,g]of r.geosets.entries()){
  if(g.vertices.length/3!==g.vertexGroups.length||g.uvSets[0].length!==g.vertices.length/3*2)throw Error('Array lengths');for(const v of g.faces)if(v>=g.vertices.length/3)throw Error('Face index');
  for(let k=0;k<g.normals.length;k+=3)if(Math.abs(Math.hypot(...g.normals.slice(k,k+3))-1)>1e-5)throw Error('Unit normal');
  let fi=0;for(const p of src.geosets[gi].parts){const edges=new Map();let volume=0;
   for(const f of p.faces){const [a,b,c]=f.map(i=>p.vertices[i]);volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6;
    if(Math.hypot(...cross(a,b,c))<1e-6)throw Error('Source degenerate');if(!p.closed&&a[2]===b[2]&&b[2]===c[2]&&cross(a,b,c)[2]<=0)throw Error('Ground backface '+p.name);
    for(let j=0;j<3;j++){const vi=g.faces[fi++];for(let k=0;k<3;k++){const err=Math.abs(p.vertices[f[j]][k]-g.vertices[vi*3+k]);cornerError=Math.max(cornerError,err);if(err>2e-5)throw Error('Source corner mismatch');}if(g.vertexGroups[vi]!==p.bone)throw Error('Bone group mismatch');const a=f[j],b=f[(j+1)%3],key=[Math.min(a,b),Math.max(a,b)].join(',');if(!edges.has(key))edges.set(key,[]);edges.get(key).push([a,b]);}
   }
   if(p.closed){for(const e of edges.values())if(e.length!==2||e[0][0]!==e[1][1]||e[0][1]!==e[1][0])throw Error('Closed topology '+p.name);if(volume<=0)throw Error('Inward solid '+p.name);closed++;}else planes++;
   topology.push({part:p.name,closed:p.closed,consistentWinding:p.closed,positiveVolume:p.closed?volume:null});
  }
 }
 const tris=r.geosets.reduce((s,g)=>s+g.faces.length/3,0);if(tris>250)throw Error('Triangle budget');
 const samples=new Set([0,1,49,50,589,590,599,600,601,739,740,749,750,751,939,940,949,950,951,1199,1200,1299,1300,1749,1750,1999,2000,2749,2750,3749,3750,3999,4000].filter(t=>t<=src.endMs));for(let t=0;t<=src.endMs;t+=10)samples.add(t);for(const ga of r.geosetAnimations)for(const a of ga.animations)for(const t of a.frames)if(t<=src.endMs)samples.add(t);for(const b of r.bones)for(const a of b.animations)for(const t of a.frames)if(t<=src.endMs)samples.add(t);
 let maxRadius=0,maxMotion=0,visibleAt0=0;const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity],boundsSamples=[];const f0=getFrame(r,0,0);
 for(const t of [...samples].sort((a,b)=>a-b)){const f=getFrame(r,0,t);if(f.alphas.some(a=>!Number.isFinite(a)||a<0||a>1)||f.layers.flat().some(a=>!Number.isFinite(a)||a<0||a>1))throw Error('Alpha bounds');let visibleTris=0,visibleRadius=0;
  for(const [gi,g]of r.geosets.entries()){const visible=f.alphas[gi]*f.layers[g.materialId][0]>1e-5;if(visible)visibleTris+=g.faces.length/3;
   for(let i=0;i<g.vertices.length/3;i++){const p=pose(g,i,f),p0=pose(g,i,f0);maxMotion=Math.max(maxMotion,Math.hypot(...p.map((x,k)=>x-p0[k])));for(let k=0;k<3;k++){if(!Number.isFinite(p[k])||p[k]<r.extent.min[k]-1e-4||p[k]>r.extent.max[k]+1e-4)throw Error(name+' animated extent '+t+' '+p);lo[k]=Math.min(lo[k],p[k]);hi[k]=Math.max(hi[k],p[k]);}const rad=Math.hypot(p[0],p[1]);if(visible){visibleRadius=Math.max(visibleRadius,rad);maxRadius=Math.max(maxRadius,rad);if(rad>src.radius+1e-4)throw Error(name+' false radius '+rad);}}
  }
  if(t===0){visibleAt0=visibleTris;if(visibleTris===0||visibleRadius<src.radius-4.01)throw Error(name+' starts invisible or undersized');}
  if(src.loop&&visibleTris===0)throw Error('Loop invisible '+name);boundsSamples.push({timeMs:t,visibleTriangles:visibleTris,visibleRadius});
 }
 if(maxMotion<1)throw Error('Static posed vertices');
 const end=getFrame(r,0,src.endMs);let seamError=0;if(src.loop){for(const g of r.geosets)for(let i=0;i<g.vertices.length/3;i++){const a=pose(g,i,f0),b=pose(g,i,end);seamError=Math.max(seamError,Math.hypot(...a.map((x,k)=>x-b[k])));}if(seamError>1e-4||f0.alphas.some((a,i)=>Math.abs(a-end.alphas[i])>1e-6))throw Error('Loop seam');}
 for(const t of [10000,10000.25,10000.5,10000.75,10001]){const f=getFrame(r,1,t);if(f.alphas.some(a=>a!==0)||f.layers.flat().some(a=>a!==0))throw Error('Visible Death');}
 if(src.loop){for(const t of [0,50,590,600,940,950,1200,1750,2000]){const f=getFrame(r,0,t);if(f.alphas.some(a=>a<=0))throw Error('Neutral loop changes phase visibility');}}
 const chosen=[0,50,590,600,740,750,940,950,1200,1750,1999,2000,3750,4000].filter(t=>src.loop||t<=src.endMs).map(t=>({...getFrame(r,0,src.loop?t%src.endMs:t),elapsedMs:t}));chosen.push({...getFrame(r,1,10000),elapsedMs:'Death'});
 preview.models.push({name,skill:src.skill,radius:src.radius,endMs:src.endMs,loop:src.loop,triangles:tris,geometry:r.geosets.map((g,i)=>({vertices:Array.from(g.vertices),normals:Array.from(g.normals),faces:Array.from(g.faces),vertexGroups:Array.from(g.vertexGroups),matrixGroups:Array.from(g.matrixGroups),matrixIndices:Array.from(g.matrixIndices),materialId:g.materialId,filterMode:r.materials[g.materialId].layers[0].filterMode,label:src.geosets[i].name})),frames:chosen});
 reports.push({name,skill:src.skill,status:'PASS exported MDX800 offline validation',inGameTested:false,importPath:'war3mapImported\\'+name+'.mdx',bytes:bytes.length,sha256:sha(bytes),radius:src.radius,maxVisibleRadius:maxRadius,triangles:tris,bones:r.bones.length,materials:r.materials.length,geosets:r.geosets.length,sequences:r.sequences.map(s=>({name:s.name,interval:Array.from(s.interval),loop:s.flags===0})),deathAlpha:0,materialFlags:r.materials.map(m=>m.layers.map(l=>({filterMode:l.filterMode,flags:l.flags}))),mdxBinaryRoundtripExact:true,mdlTextRoundtripMaxError:textError,maxSourceCornerError:cornerError,maxAnimatedVertexMotion:maxMotion,loopSeamError:seamError,visibleTrianglesAt0:visibleAt0,animatedBounds:{min:lo,max:hi},declaredBounds:src.bounds,sampledTimes:samples.size,phaseContract:src.phaseContract,closedParts:closed,oneSidedSurfaces:planes,topology,boundsSamples});
}
global.ImageData=class{constructor(w,h){this.width=w;this.height=h;this.data=new Uint8ClampedArray(w*h*4)}};const BlpImage=require(base+'/parsers/blp/image.ts').BlpImage,b=new BlpImage(),tx=fs.readFileSync(path.join(OUT,'TDPetVfxSolidWhite.blp'));b.load(new Uint8Array(tx));if(b.width!==4||b.height!==4||b.mipmaps()!==3)throw Error('White BLP contract');for(let i=0;i<3;i++){const m=b.getMipmap(i);if(Array.from(m.data).some(v=>v!==255))throw Error('White BLP pixels/alpha');}
if(process.argv.includes('--verify-imports')){const root=path.resolve(__dirname,'../../..');for(const model of reports.filter(m=>m.phaseContract.neutral)){const actual=fs.readFileSync(path.join(root,'imports/war3mapImported',model.name+'.mdx'));if(actual.length!==model.bytes||sha(actual)!==model.sha256)throw Error('Production import mismatch '+model.name);}if(!fs.readFileSync(path.join(root,'imports/Textures/TDPetVfxSolidWhite.blp')).equals(tx))throw Error('Production white BLP mismatch');}
const result={status:'PASS',inGameTested:false,format:'MDX800',models:reports,texture:{importPath:'Textures\\TDPetVfxSolidWhite.blp',bytes:tx.length,sha256:sha(tx),version:1,width:4,height:4,mipmaps:3,rgbaAll:[255,255,255,255]},limitations:'Offline software projection does not verify Warcraft native animation choice, depth/occlusion, terrain fitting or FPS.'};
fs.writeFileSync(path.join(__dirname,'validation-report.json'),JSON.stringify(result,null,2));fs.writeFileSync(path.join(__dirname,'parsed-preview-data.json'),JSON.stringify(preview));
const summary={...result,models:reports.map(({topology,boundsSamples,...r})=>r)};fs.writeFileSync(path.join(__dirname,'production-manifest.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify({status:result.status,models:reports.map(({name,triangles,bones,bytes,maxVisibleRadius,sha256})=>({name,triangles,bones,bytes,maxVisibleRadius,sha256})),texture:result.texture},null,2));
