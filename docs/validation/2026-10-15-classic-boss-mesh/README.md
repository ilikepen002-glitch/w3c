# Classic Boss mesh compatibility candidate

## Observed issue and scope

The supplied live screenshot shows EclipseSpellweaver (uB24): purple robe, gold trim, skull face and crescent. Long strips contain the body's atlas texture. This is mesh distortion, not a ribbon emitter; neither target MDX contains ribbon emitters. Baseline is the exact model bytes in published commit 7834f5c.

Root cause is **not proven**. The independent audit covers matrix count and lookup, parent hierarchy, per-vertex array sizes, index bounds, classic node flags, global-sequence IDs, sorted animation keys and explicit keys at every sequence boundary. Both models have one unusually large fully expanded geoset (16,962 / 18,318 vertices). These indices fit unsigned 16 bits; groups are far below 255. No global sequences or invalid transform values explain the screenshot. MDX roundtrip and offline CPU sampling cannot validate the native renderer, animation blending, culling or GPU buffer behavior.

A first-person historical report describes trouble above roughly 9,000 vertices per geoset and relief after splitting. Other replies explicitly question driver involvement and matrix-group limits. It is evidence for a controlled batching experiment, **not** proof of a 9,000 / 16,384 engine limit or a 1.27a-specific defect:
https://www.hiveworkshop.com/threads/importing-models-symptoms-and-cures.287451/
The June 1, 2018 reply #12 and surrounding replies contain the relevant discussion. The preceding 1.27 crash remark concerns animation rarity, not a proven vertex-count threshold.

## Candidate

`tools/ClassicBossMesh.cjs` performs bit-exact attribute deduplication and sequential triangle batching at a conservative budget of 3,000 vertices. It never merges UV seams, different normals or different matrix-group membership. Triangle order, number of faces, every corner attribute, all original matrix tables, extents, material IDs and rendering flags are preserved. Every non-GEOS chunk is byte-identical, so bones, animation keys, sequences, pivot points, texture references and material contents cannot have changed. No object scale, gameplay or texture change.

The two assets have no GeosetAnim entries and every bone has GeosetId/GeosetAnimationId = -1. The converter asserts these conditions rather than silently remapping references. It is intentionally not a general-purpose model optimizer.

The previous `diagnostics/final-boss-geoset-split` experiment used pure splitting of expanded vertices into 6 / 7 geosets, with no reduction in total vertex count. This candidate additionally removes exact duplicate full vertex records; it retains every triangle and uses fewer vertex records and batches. That reduces both per-draw and total vertex load. Neither candidate has a native-engine pass; do not claim this one is already fixed because the offline gate passes.

## Rebuild and verification

From repository root with the approved parser runtime installed:

    MDX_PARSER_RUNTIME=/path/node_modules node tools/VerifyClassicBossMesh.cjs --write
    MDX_PARSER_RUNTIME=/path/node_modules node tools/VerifyFinalBossStructure.cjs

The first command reads frozen original MDX bytes from commit 7834f5c (not from a previous candidate), regenerates both imports and production manifest hashes, independently expands every indexed corner, and compares animated positions/normals at all original key times plus 33 evenly spaced times per sequence. It also verifies all non-GEOS chunks byte for byte and exercises negative cases. Without `--write`, it checks current files against deterministic output. The original authoring exporters remain archived original-asset sources; run this explicit compatibility pass after authoring when integrating these frozen originals. Changes to original art require intentionally updating the baseline and reviewing equivalence; the script must not silently accept them.

`report.json` contains final-byte audit, corner hashes, sampling counts and sizes. These are focused offline checks. No Wurst/full map build, packaging check or Warcraft run was performed in this worker. Parent integration must run the normal build and compare packaged MDX hashes with these manifests. In-game validation must cover idle, walk, spell/attack, hit, death, turn and camera exit/re-entry at unchanged current scale, ideally with baseline/candidate under the same client and scene.

Final offline result: Eclipse 16,962 → 10,814 vertex records in 4 batches (2,998 / 3,000 / 3,000 / 1,816); Abyss 18,318 → 10,947 in 4 batches (3,000 / 2,999 / 2,998 / 1,950). Geometry corner counts remain 16,962 / 18,318 (5,654 / 6,106 triangles). Each model passed 294 sampled poses and 7 negative cases. Matrix groups remain 25 / 28, with maximum 1 / 2 bones per group. The earlier six/seven-batch candidate did not reduce total vertex records.
