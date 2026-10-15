const fs=require('fs'),path=require('path');
const modules=process.env.MDX_PARSER_MODULES||path.dirname(path.dirname(require.resolve('mdx-m3-viewer/package.json')));
for(const[n,v]of [['mdx-m3-viewer','5.7.9'],['typescript','4.9.5']])if(require(path.join(modules,n,'package.json')).version!==v)throw Error('Pinned dependency mismatch: '+n);
const ts=require(path.join(modules,'typescript'));
require.extensions['.ts']=(module,filename)=>module._compile(ts.transpileModule(fs.readFileSync(filename,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2018}}).outputText,filename);
exports.Model=require(path.join(modules,'mdx-m3-viewer/src/parsers/mdlx/model.ts')).default;
exports.Sequence=require(path.join(modules,'mdx-m3-viewer/src/parsers/mdlx/sequence.ts')).default;
exports.Extent=require(path.join(modules,'mdx-m3-viewer/src/parsers/mdlx/extent.ts')).default;
exports.walk=function walk(o,p='',out=[]){if(!o||typeof o!=='object'||ArrayBuffer.isView(o))return out;if(Array.isArray(o.animations))o.animations.forEach((a,i)=>out.push({path:p+'.animations['+i+']',track:a}));for(const[k,v]of Object.entries(o)){if(k!=='animations'&&v&&typeof v==='object')walk(v,p?p+'.'+k:k,out)}return out;};
