// Read-only inspection of the unchanged author model using the project-pinned MIT parser.
// node tools/asset-converter/inspect-king-leoric.cjs [asset-directory]
// The directory defaults to imports; portrait/main live in war3mapImported.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert').strict;
const ts = require('typescript');
require.extensions['.ts'] = function(module, filename) {
  module._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2018 }
  }).outputText, filename);
};
const Model = require('mdx-m3-viewer/src/parsers/mdlx/model.ts').default;
global.ImageData = class {
  constructor(w, h) { this.width = w; this.height = h; this.data = new Uint8ClampedArray(w*h*4); }
};
const { BlpImage } = require('mdx-m3-viewer/src/parsers/blp/image.ts');
const root = path.resolve(__dirname, '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'assets/source/king-leoric.json'), 'utf8'));
const directory = path.resolve(process.argv[2] || path.join(root, 'imports'));
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
const finite = values => Array.from(values).every(Number.isFinite);
const read = name => {
  const spec = manifest.assets.find(a => a.name === name);
  const file = path.join(directory, directory === path.join(root, 'imports') && name.endsWith('.mdx') ? 'war3mapImported' : '', name);
  const bytes = fs.readFileSync(file);
  assert.equal(bytes.length, spec.size_bytes, name + ': size changed');
  assert.equal(sha(bytes), spec.sha256, name + ': original bytes changed');
  return bytes;
};

function validateModel(name, triangles, requiredSequences) {
  const bytes = read(name);
  assert.equal(bytes.toString('ascii', 0, 4), 'MDLX');
  const chunks = [];
  let offset = 4;
  while (offset < bytes.length) {
    assert(offset + 8 <= bytes.length, 'Truncated chunk header');
    const tag = bytes.toString('ascii', offset, offset + 4);
    const size = bytes.readUInt32LE(offset + 4);
    assert(!['FAFX', 'BPOS', 'CORN'].includes(tag), 'Reforged-only chunk');
    assert(offset + size + 8 <= bytes.length, 'Truncated chunk body');
    chunks.push(tag); offset += size + 8;
  }
  assert.equal(offset, bytes.length);
  const m = new Model(); m.load(new Uint8Array(bytes));
  assert.equal(m.version, 800);
  assert.equal(m.unknownChunks.length, 0);
  assert.equal(m.animationFile, '', 'Unexpected external animation file');
  assert.equal(m.geosets.reduce((n,g) => n + g.faces.length/3, 0), triangles);
  const sequences = m.sequences.map(s => s.name.toLowerCase());
  for (const seq of requiredSequences) assert(sequences.includes(seq), 'Missing ' + seq);
  for (const s of m.sequences) assert(s.interval[1] > s.interval[0], 'Empty sequence');
  const nodeKinds = ['bones', 'helpers', 'lights', 'attachments', 'particleEmitters',
    'particleEmitters2', 'ribbonEmitters', 'eventObjects', 'collisionShapes'];
  const nodes = nodeKinds.flatMap(k => m[k]);
  const ids = new Set(nodes.map(n => n.objectId));
  assert.equal(ids.size, nodes.length, 'Duplicate node IDs');
  const byId = new Map(nodes.map(n => [n.objectId, n]));
  for (const n of nodes) {
    assert(n.objectId >= 0 && n.objectId < m.pivotPoints.length, 'Missing pivot');
    assert(finite(m.pivotPoints[n.objectId]), 'Nonfinite pivot');
    assert(n.parentId === -1 || ids.has(n.parentId), 'Missing node parent');
    let cursor = n, seen = new Set();
    while (cursor) {
      assert(!seen.has(cursor.objectId), 'Node hierarchy cycle'); seen.add(cursor.objectId);
      cursor = byId.get(cursor.parentId);
    }
    for (const a of n.animations) {
      assert([0,1,2,3].includes(a.interpolationType), 'Unknown interpolation');
      assert.equal(a.frames.length, a.values.length);
      assert(a.globalSequenceId === -1 || a.globalSequenceId < m.globalSequences.length);
      assert(a.frames.every((frame,i) => i === 0 || frame >= a.frames[i-1]), 'Unordered track');
      assert(a.values.every(finite) && a.inTans.every(finite) && a.outTans.every(finite));
    }
  }
  for (const g of m.geosets) {
    const count = g.vertices.length / 3;
    assert(Number.isInteger(count) && count > 0 && finite(g.vertices) && finite(g.normals));
    assert.equal(g.normals.length, g.vertices.length);
    assert.equal(g.vertexGroups.length, count);
    assert.equal(g.faces.length % 3, 0);
    assert(Array.from(g.faces).every(i => i < count));
    assert.equal(g.matrixGroups.reduce((a,b) => a+b,0), g.matrixIndices.length);
    assert(Array.from(g.matrixGroups).every(n => n > 0));
    assert(Array.from(g.matrixIndices).every(id => ids.has(id)));
    assert(Array.from(g.vertexGroups).every(i => i < g.matrixGroups.length));
    assert(g.uvSets.length > 0 && g.uvSets.every(uv => uv.length === count*2 && finite(uv)));
    assert(g.materialId < m.materials.length);
    assert.equal(g.skin.length, 0); assert.equal(g.tangents.length, 0);
  }
  for (const mat of m.materials) for (const layer of mat.layers) {
    assert(layer.textureId < m.textures.length);
    assert(layer.filterMode >= 0 && layer.filterMode <= 6);
  }
  for (const p of m.particleEmitters2) assert(p.textureId < m.textures.length);
  for (const n of m.attachments.concat(m.particleEmitters)) assert.equal(n.path, '', 'External model dependency');
  const textures = m.textures.filter(t => t.path).map(t => t.path);
  const expectedTextures = name === 'Leoric.mdx' ? ['Leoric.blp', ...manifest.native_texture_references] : ['Leoric.blp'];
  assert.deepEqual(textures, expectedTextures);
  if (name === 'Leoric.mdx') assert.deepEqual(m.eventObjects.map(e => e.name), manifest.main_native_event_objects);
  else assert.deepEqual(m.textures.filter(t => t.replaceableId).map(t => t.replaceableId), [2]);
  return {name, sha256: sha(bytes), version: m.version, triangles,
    bones: m.bones.length, helpers: m.helpers.length, nodes: nodes.length,
    sequences: m.sequences.map(s => ({name:s.name, start:s.interval[0], end:s.interval[1], looping:!(s.flags&1)})),
    textures: m.textures.map(t => ({path:t.path, replaceableId:t.replaceableId})), chunks};
}

const report = {
  scope: 'Original bytes and offline format/dependency inspection; not target game or map verification',
  models: [validateModel('Leoric.mdx', 972, ['stand','walk','death']),
    validateModel('Leoric_Portrait.mdx', 486, ['portrait','portrait talk'])]
};
const textureBytes = read('Leoric.blp');
assert.equal(textureBytes.toString('ascii',0,4), 'BLP1');
const blp = new BlpImage(); blp.load(new Uint8Array(textureBytes));
assert.equal(blp.width, 256); assert.equal(blp.height, 256);
assert.equal(blp.alphaBits, 8); assert.equal(blp.mipmaps(), 9);
for (let i=0;i<9;i++) {
  assert(blp.mipmapOffsets[i]+blp.mipmapSizes[i] <= textureBytes.length);
  const mip=blp.getMipmap(i);
  assert.equal(mip.width, Math.max(1,256>>i)); assert.equal(mip.height, Math.max(1,256>>i));
  assert.equal(mip.data.length, mip.width*mip.height*4);
}
const mip = blp.getMipmap(0);
let alphaMin=255, alphaMax=0;
for (let i=3;i<mip.data.length;i+=4) { alphaMin=Math.min(alphaMin,mip.data[i]); alphaMax=Math.max(alphaMax,mip.data[i]); }
assert.equal(alphaMin,0); assert.equal(alphaMax,255);
report.texture = {name:'Leoric.blp', sha256:sha(textureBytes), format:'BLP1', width:256,height:256,alphaBits:8,mips:9,alphaMin,alphaMax};
report.unverified = ['Target 1.27a native textures, TeamGlow and native events', 'Current map compilation/MPQ imports/objects', 'Game rendering, animation timing and performance'];
console.log(JSON.stringify(report,null,2));
