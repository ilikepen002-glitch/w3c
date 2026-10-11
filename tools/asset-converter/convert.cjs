// Pinned upstream MDL/MDX parser with a TypeScript transpile hook.
const fs = require('fs');
const path = require('path');
const ts = require('typescript');
require.extensions['.ts'] = function(module, filename) {
  const code = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2018 }
  }).outputText;
  module._compile(code, filename);
};
const Model = require('mdx-m3-viewer/src/parsers/mdlx/model.ts').default;
const root = path.resolve(__dirname, '../..');
for (let choice = 1; choice <= 5; choice++) {
  const source = fs.readFileSync(path.join(root, `assets/source/TDEvolutionWings${choice}.mdl`), 'utf8');
  const model = new Model(); model.load(source);
  if (model.textures[0].path !== 'war3mapImported\\TDEvolutionWings.blp') throw Error('Bad texture path ' + model.textures[0].path);
  const binary = model.saveMdx();
  const reread = new Model(); reread.load(binary);
  if (reread.version !== 800 || reread.geosets.length !== 2 || reread.bones.length !== 2 || reread.sequences[0].name !== 'Stand') throw Error('Model verification failed');
  if (reread.materials[0].layers[0].filterMode !== 2 || !(reread.materials[0].layers[0].flags & 0x10)) throw Error('Missing alpha blend or two-sided flag');
  fs.writeFileSync(path.join(root, `imports/war3mapImported/TDEvolutionWings${choice}.mdx`), Buffer.from(binary));
  console.log(`PASS wing ${choice}: MDX800, two geosets/bones, Blend/TwoSided, looping Stand, ${binary.byteLength} bytes`);
}

// Pillow's BLP1 reader ignores the per-pixel alpha plane; use the independent
// Warcraft-format parser to verify encoded alpha and each mip instead.
global.ImageData = class { constructor(w,h) { this.width=w; this.height=h; this.data=new Uint8ClampedArray(w*h*4); } };
const BlpImage = require('mdx-m3-viewer/src/parsers/blp/image.ts').BlpImage;
for (const name of fs.readdirSync(path.join(root,'imports/war3mapImported')).filter(n => n.endsWith('.blp'))) {
  const bytes=fs.readFileSync(path.join(root,'imports/war3mapImported',name));
  const image=new BlpImage(); image.load(new Uint8Array(bytes));
  const mip=image.getMipmap(0);
  let low=255,high=0;
  for(let i=3;i<mip.data.length;i+=4){low=Math.min(low,mip.data[i]);high=Math.max(high,mip.data[i]);}
  for(let level=0;level<image.mipmaps();level++) image.getMipmap(level);
  if(name==='TDEvolutionWings.blp' && (low!==0 || high!==255)) throw Error('Wing alpha lost');
  if(name.startsWith('BTN') && (image.width!==64 || image.height!==64 || low!==255)) throw Error('Bad icon');
  console.log(`PASS BLP ${name}: ${image.width}x${image.height}, alpha${low}-${high}, ${image.mipmaps()} mips`);
}
