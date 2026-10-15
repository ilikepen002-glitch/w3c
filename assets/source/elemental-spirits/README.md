# Elemental spirit production assets

The current set contains fourteen original program-authored creature models and
one credited derivative of johnwar's **Phoenix (Re-Classic)**, replacing the
original EmberBird. See `LICENSE-PROVENANCE.txt`,
`docs/credits/phoenix-reclassic.md`, and the embedded `Credits-Phoenix.txt`.
Do not describe all fifteen current meshes as original project artwork.

## Current authoritative inputs and outputs

`import-manifest.json` identifies all fifteen species, exact model and texture
paths, actual SHA256/byte counts, geometry statistics, and the separate wild
phoenix resource. Its explicit native-texture paths are external dependencies,
not missing custom imports or verified 1.27a installation files.

The 2026-10-15 refinement preserves established silhouettes and animations on
fourteen models while improving selected eyes and painterly material atlases.
The approved Silver Mane atlas is retained byte-for-byte. The new Phoenix uses
two drawn textures, its existing mature rig/actions, and a fixed display-index
adapter. Original imagegen inputs and prompts are persisted in the repository.
No procedural replacement painting is used for those drawn atlas pixels.

- Metal/wood: `refinement-20261015/batch-a/` and
  `tools/RebuildMetalWoodRefinement.py` / `.cjs`.
- Water/earth: model-specific generators, persisted
  `models/<model>/original/atlas-refined-imagegen.png`, and
  `tools/BuildWaterEarthRefinements.py`.
- Fire fox/salamander: `refinement-20261015/batch-c-fire/` and
  `tools/BuildFireTextureRefinements.py`.
- Phoenix: the credited pinned source and deterministic adapter in the fire
  refinement source chain; wild-origin adaptation uses
  `tools/BuildWildPhoenixVariant.cjs`.

The unified entry point is:

    MDX_PARSER_MODULES=/path/to/node_modules python3 tools/BuildSpiritRefinementAssets.py

It copies only pinned required inputs into a temporary directory, rebuilds all
approved imports, and compares exact bytes. `--write` restores approved imports
only after matching the recorded output hashes; it never updates hashes to
accept a mismatch. `refinement-20261015/rebuild-plan.json` is the complete input,
command and output inventory. Node dependencies are pinned in
`tools/asset-converter/package-lock.json` (mdx-m3-viewer 5.7.9, TypeScript 4.9.5,
gl-matrix 3.4.4); Python uses NumPy and Pillow.

The historical `BuildPetDisplayModels.cjs` fixed-BASE path refuses to overwrite
active refinements. Old per-model exporters and historical source descriptions
are not an alternative production rebuild chain. Renderer caches, raw sampled
frame JSON, decoded RGBA buffers and temporary validation output are not source
assets and are not shipped as imports.

## Offline acceptance and gameplay boundary

    node tools/InspectSpiritRefinementModels.cjs --output /tmp/inspection.json
    python3 tools/VerifySpiritRefinementArtifact.py --inspection /tmp/inspection.json --map ExampleMap.w3x

The first command reparses actual MDX800/BLP1 bytes, exact TEXS paths, material
flags, complete mip levels/alpha, sequence contracts, and sampled visible culling
bounds. The second checks permitted source/object deltas, unchanged original
rigs and keys on fourteen species, actual MPQ bytes and all wild/collection/
attached unit references. The historical `VerifyAllPetDisplayArtifact.py` entry
routes active refinements through these honest current gates rather than
weakening its old immutable-geometry assertions.

Check and build only through the repository's official entry points, serialized
as required by AGENTS.md. Resource verification and Blender renders are offline
evidence, not Warcraft III 1.27a rendering, native texture availability or FPS.
The current collection icons are retained from the existing production UI;
this pass changes actual creature resources, not the full icon system.
