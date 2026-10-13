// Offline Walk/rig audit of the actual imported MDX800 binaries. No game claims.
// MDX_PARSER_MODULES points to node_modules containing the pinned parser stack.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const runtime = process.env.MDX_PARSER_MODULES || path.dirname(path.dirname(require.resolve('mdx-m3-viewer/package.json')));
const ts = require(runtime + '/typescript');
require.extensions['.ts'] = (m, f) => m._compile(ts.transpileModule(fs.readFileSync(f, 'utf8'), {compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2018}}).outputText, f);
const base = runtime + '/mdx-m3-viewer/src';
const Model = require(base + '/parsers/mdlx/model.ts').default;
const {createTypedSd} = require(base + '/viewer/handlers/mdx/sd.ts');
const {mat4, vec3} = require(runtime + '/gl-matrix');
const root = path.resolve(__dirname, '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'assets/source/elemental-spirits/import-manifest.json')));
const motionBones = [
 ['FrontLeft','FrontRight','HindLeft','HindRight'], ['LeftWing','RightWing'],
 ['DiggingArmLeft','DiggingArmRight','HindLeft','HindRight'], ['LeafUpperLeft','LeafUpperRight','RootLeft','RootRight'],
 ['FrontLeft','FrontRight','RearLeft','RearRight'], ['RootFootLeft','RootFootRight'],
 ['SwimSpine0','SwimSpine2','SwimSpine5'], ['FinLeft','FinRight'],
 ['FrontLeftPaw','FrontRightPaw','RearLeftPaw','RearRightPaw'], ['WingLeft','WingRight'],
 ['FrontLeft','FrontRight','HindLeft','HindRight'], ['FrontLeft','FrontRight','HindLeft','HindRight'],
 ['FrontLeft','FrontRight','BackLeft','BackRight'], ['LeftLeg','RightLeg'], ['SoftFoot']
];
function check(test, message) {if (!test) throw Error(message);}
const results = [];
for (const entry of manifest.models) {
 const bytes = fs.readFileSync(path.join(root, 'imports', ...entry.modelImportPath.split('\\')));
 check(crypto.createHash('sha256').update(bytes).digest('hex') === entry.modelSha256, entry.name + ': manifest mismatch');
 const m = new Model(); m.load(new Uint8Array(bytes));
 check(m.version === 800, entry.name + ': wrong MDX version');
 const si = m.sequences.findIndex(s => s.name === 'Walk'), w = m.sequences[si];
 check(w && w.flags === 0 && w.interval[1] > w.interval[0], entry.name + ': missing looping Walk');
 const bones = new Map(m.bones.map(b => [b.objectId, b]));
 const rows = [];
 for (const name of motionBones[entry.suggestedSpeciesId - 1]) {
  const bone = m.bones.find(b => b.name === name);
  check(bone, entry.name + ': missing motion bone ' + name);
  check(bone.animations.every(a => a.globalSequenceId === -1), name + ': unexpected global sequence');
  const tracks = Object.fromEntries(bone.animations.map(a => [a.name, createTypedSd(m, a)]));
  const vertices = [];
  for (const g of m.geosets) {
   let offset = 0;
   const groups = Array.from(g.matrixGroups, n => {const ids = Array.from(g.matrixIndices.slice(offset, offset + n)); offset += n; return ids;});
   for (let i = 0; i < g.vertices.length / 3; i++) {
    const ids = groups[g.vertexGroups[i]];
    check(ids && ids.every(id => bones.has(id)), entry.name + ': invalid skinning');
    if (ids.length === 1 && ids[0] === bone.objectId) vertices.push(g.vertices.subarray(i * 3, i * 3 + 3));
   }
  }
  check(vertices.length > 0, entry.name + ': motion bone not bound to mesh ' + name);
  const poses = [];
  for (let sample = 0; sample <= 16; sample++) {
   const time = w.interval[0] + (w.interval[1] - w.interval[0]) * sample / 16;
   const t = vec3.create(), q = new Float32Array([0,0,0,1]), s = new Float32Array([1,1,1]);
   for (const [tag, value] of [['KGTR',t],['KGRT',q],['KGSC',s]]) if (tracks[tag]) tracks[tag].getValue(value, si, time, time - w.interval[0]);
   const matrix = mat4.create(); mat4.fromRotationTranslationScaleOrigin(matrix, q, t, s, m.pivotPoints[bone.objectId]);
   // Deliberately exclude parent/root motion: measure movement relative to torso.
   poses.push(vertices.map(v => Array.from(vec3.transformMat4(vec3.create(), v, matrix))));
  }
  let displacement = 0, seam = 0;
  for (let i = 0; i < vertices.length; i++) {
   for (const pose of poses) displacement = Math.max(displacement, vec3.distance(pose[i], poses[0][i]));
   seam = Math.max(seam, vec3.distance(poses[0][i], poses[16][i]));
  }
  check(Number.isFinite(displacement) && displacement > 0.5, entry.name + ': stationary limb ' + name);
  check(seam < 0.01, entry.name + ': discontinuous Walk loop ' + name);
  rows.push({bone: name, boundVertices: vertices.length, maxLocalDisplacement: +displacement.toFixed(3), loopSeam: +seam.toFixed(6)});
 }
 results.push({species: entry.suggestedSpeciesId, name: entry.name, walkMs: w.interval[1] - w.interval[0], modelMoveSpeed: w.moveSpeed, motion: rows});
}
check(results.length === 15, 'Expected all 15 spirit species');
console.log(JSON.stringify({status: 'PASS', scope: 'actual imported models; local limb deformation, skin binding, looping and global sequence checks; not game verification', models: results}, null, 2));
