# Elemental skill VFX assets

Three project-original Warcraft Classic MDX800 effects, procedurally authored in this task. They are effects, not unit models. No third-party meshes or texture pixels are included.

## Rebuild

1. Install the existing project-pinned converter runtime with `cd runtime && npm ci --ignore-scripts --no-audit --no-fund`. The package and lockfile preserve mdx-m3-viewer 5.7.9 / TypeScript 4.9.5 / gl-matrix 3.4.4; tarball origins are the official npm registry and integrity hashes are preserved.
2. Run `python build_vfx.py` (numpy, Pillow).
3. Run `node export_validate.cjs`. Alternatively set `MDX_PARSER_RUNTIME` to an existing trusted node_modules folder containing those same dependencies.
## Four exact imports

- `war3mapImported\TDPetVfxSwordArray.mdx`
- `war3mapImported\TDPetVfxVerdantRoot.mdx`
- `war3mapImported\TDPetVfxFaultRidge.mdx`
- `Textures\TDPetVfxAtlas.blp`

All three MDX TEXS records reference exactly `Textures\TDPetVfxAtlas.blp`. No external textures, replaceable textures, particles, ribbons, cameras or attachment nodes are needed.

## Animation and materials

Stand is 0–1000 ms looping. Closed solid geometry is opaque with depth writing, normal backface culling and alpha=1; narrow additive edge geometry gently pulses. Death is 1000–1600 ms, nonlooping. A body-material visibility switch at 1001 ms enables a Blend layer on the same geometry, allowing GeosetAnim KGAO to fade it smoothly; the opaque layer is disabled. The first 120 ms hold the recognizable silhouette, followed by monotonic fade to zero at 1600 ms. TwoSided is absent throughout. There are two geosets, two materials and one identity bone per model. No timer or gameplay state is encoded.

The shared 64×64 BLP1 texture has seven full mips and all-opaque texels. Model-layer / geoset alpha, rather than texture cutouts, controls fading. Broad authored atlas light/shadow planes provide gold/ivory, bark/leaves and rock/mineral distinction.

The body remains stationary; motion/segment placement is owned by the existing skill visual runtime. Native effect destruction selecting Death and its precise fade / ground placement remain client verification items. Offline previews are illustrative renders of the actual exported data, not Warcraft screenshots or exact additive blending emulation.

## Verification

The exporter writes MDX800, then starts a new parser from the on-disk bytes. It verifies exact MDX binary roundtrip, an MDL text roundtrip (float rounding tolerance), 50 sequence samples per model, opaque Stand and monotonic Death layer/alpha endpoints, finite geometry/extents/unit normals, exact texture paths and BLP decoding at all seven mip levels. Every component has two oppositely-directed uses of each edge and positive volume. Ordered source triangle corners are compared with actual parsed MDX corners. All models stay below 600 triangles. The exporter regenerates `validation-report.json`; checked import hashes and aggregate evidence are retained in `production-manifest.json`.

Only `output/*.mdx` plus `output/TDPetVfxAtlas.blp` are production imports. The generated MDL, raw decoded pixels, sampled frame data and preview images are verification outputs, not imports. The repository retains scripts, three source JSON files, atlas PNG, provenance, manifest and runtime package/lock. Rebuild reports, node_modules, sampled frames and previews are not production inputs and remain untracked.
