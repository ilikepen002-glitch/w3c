'use strict';
// Asset-local compatibility candidate. 3000 is a conservative batching budget,
// NOT a claimed Warcraft engine limit. Never weld unlike normal/UV/skin seams.
const assert = require('assert');
const MAX_VERTICES = 3000;
function bytes(a, start, count) {
  return Buffer.from(a.buffer, a.byteOffset + start * a.BYTES_PER_ELEMENT,
    count * a.BYTES_PER_ELEMENT);
}
function vertexKey(g, i) {
  return Buffer.concat([bytes(g.vertices,i*3,3), bytes(g.normals,i*3,3),
    ...g.uvSets.map(uv=>bytes(uv,i*2,2)), bytes(g.vertexGroups,i,1)]).toString('hex');
}
function optimize(model, Geoset) {
  assert.equal(model.version,800, 'Only classic MDX800 supported');
  // Both target assets have no geoset animation and all bone IDs are Multiple.
  // Refuse models requiring remapping rather than silently changing references.
  assert.equal(model.geosetAnimations.length,0, 'GeosetAnim remap not supported');
  assert(model.bones.every(b=>b.geosetId===-1 && b.geosetAnimationId===-1), 'Specific bone geoset reference');
  const result=[];
  for(const g of model.geosets) {
    assert.deepEqual(Array.from(g.faceTypeGroups),[4]);
    assert.deepEqual(Array.from(g.faceGroups),[g.faces.length]);
    assert.equal(g.faces.length%3,0);
    assert.equal(g.vertices.length/3,g.vertexGroups.length);
    assert.equal(g.normals.length,g.vertices.length);
    assert(g.uvSets.length && g.uvSets.every(uv=>uv.length===g.vertexGroups.length*2));
    assert(g.matrixGroups.length<=255);
    assert(Array.from(g.vertexGroups).every(i=>i<g.matrixGroups.length));
    assert(Array.from(g.faces).every(i=>i<g.vertexGroups.length));
    let lookup, selected, faces;
    const reset=()=>{lookup=new Map(); selected=[]; faces=[];};
    const flush=()=>{
      if(!faces.length)return;
      const out=Object.assign(new Geoset(),g);
      out.vertices=new Float32Array(selected.flatMap(i=>Array.from(g.vertices.subarray(i*3,i*3+3))));
      out.normals=new Float32Array(selected.flatMap(i=>Array.from(g.normals.subarray(i*3,i*3+3))));
      out.uvSets=g.uvSets.map(uv=>new Float32Array(selected.flatMap(i=>Array.from(uv.subarray(i*2,i*2+2)))));
      out.vertexGroups=new Uint8Array(selected.map(i=>g.vertexGroups[i]));
      out.faces=new Uint16Array(faces);
      out.faceGroups=new Uint32Array([faces.length]);
      // Keep all matrix entries, extents, material IDs and rendering flags intact.
      result.push(out); reset();
    };
    reset();
    for(let f=0;f<g.faces.length;f+=3) {
      const tri=Array.from(g.faces.subarray(f,f+3));
      const keys=tri.map(i=>vertexKey(g,i));
      if(lookup.size+new Set(keys.filter(k=>!lookup.has(k))).size>MAX_VERTICES)flush();
      keys.forEach((key,k)=>{if(!lookup.has(key)){lookup.set(key,selected.length);selected.push(tri[k]);}faces.push(lookup.get(key));});
    }
    flush();
  }
  model.geosets=result;
  return model;
}
module.exports={MAX_VERTICES,vertexKey,optimize};
