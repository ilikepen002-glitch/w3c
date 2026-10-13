const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const rt=path.resolve(process.env.MDX_PARSER_RUNTIME || path.join(__dirname,'../boss-leoric-20261013/technical/parser-runtime/node_modules'));
const ts=require(rt+'/typescript');require.extensions['.ts']=(m,f)=>m._compile(ts.transpileModule(fs.readFileSync(f,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,f);
const Model=require(rt+'/mdx-m3-viewer/src/parsers/mdlx/model.ts').default;
const source=JSON.parse(fs.readFileSync(__dirname+'/original/eclipse-source.json'));
const bytes=fs.readFileSync(__dirname+'/original/EclipseSpellweaver.mdx');const model=new Model();model.load(new Uint8Array(bytes));const g=model.geosets[0];
let corner=0,maxError=0;const findings=[];
for(const p of source.parts){const edges=new Map();let volume=0,minDoubleArea=Infinity;
 for(const face of p.faces){const [a,b,c]=face.map(i=>p.verts[i]);const sub=(a,b)=>a.map((v,i)=>v-b[i]);const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];const dot=(a,b)=>a.reduce((t,v,i)=>t+v*b[i],0);
  volume+=dot(a,cross(b,c))/6;minDoubleArea=Math.min(minDoubleArea,Math.hypot(...cross(sub(b,a),sub(c,a))));
  for(let i=0;i<3;i++){const u=face[i],v=face[(i+1)%3],key=[u,v].sort((a,b)=>a-b).join(',');if(!edges.has(key))edges.set(key,[]);edges.get(key).push([u,v]);const actual=g.faces[corner];for(let k=0;k<3;k++){const e=Math.abs(g.vertices[actual*3+k]-p.verts[u][k]);maxError=Math.max(maxError,e);assert(e<.00001,'MDX corner differs from source '+p.name);}corner++;}
 }
 let badEdges=0;for(const e of edges.values())if(e.length!==2||e[0][0]!==e[1][1]||e[0][1]!==e[1][0])badEdges++;
 assert.equal(badEdges,0,'non-manifold/open/misoriented '+p.name);assert(volume>0,'negative-volume '+p.name);assert(minDoubleArea>1e-7,'degenerate '+p.name);
 findings.push({part:p.name,triangles:p.faces.length,closed:true,opposedSharedEdges:true,positiveSignedVolume:volume,minDoubleArea});
}
assert.equal(corner,g.faces.length);assert.equal(model.materials.length,1);assert.equal(model.materials[0].layers[0].flags,0);assert.equal(model.materials[0].layers[0].filterMode,0);assert.equal(model.cameras[0].name,'Portrait');
const summary={passed:true,mdxSha256:crypto.createHash('sha256').update(bytes).digest('hex'),components:findings.length,allClosedAndConsistentlyOutward:true,sourceToMdxAllOrderedCornersMatch:true,maxFloat32CoordinateError:maxError,singleSidedOpaqueMaterial:true,layerFlags:0,camera:{name:model.cameras[0].name,position:Array.from(model.cameras[0].position),target:Array.from(model.cameras[0].targetPosition)},findings};
fs.writeFileSync(__dirname+'/surface-integrity-report.json',JSON.stringify(summary,null,2));const report=JSON.parse(fs.readFileSync(__dirname+'/validation-report.json'));report.surfaceIntegrity={...summary,findings:undefined};fs.writeFileSync(__dirname+'/validation-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify({...summary,findings:undefined}));
