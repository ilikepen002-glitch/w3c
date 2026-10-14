# Reliable elemental active-core geometry

Project-original pure geometry and one new original 4x4 opaque white BLP1. Existing spirit models, approved textures, the prior VFX atlas and prior SwordArray are unchanged. No particles, ribbons, lights, sound/events, cameras, attachment nodes, global sequences or new dummy units.

These are semantic-neutral area cores for the reliable active-feedback protocol. They show the real cast/query area from the first animation sample and remain visible while the actual context owns the one effect. They do not independently announce a freeze, fracture, falling meteor, impact or damage tick. The actual runtime callbacks must own those decorative events. This is important if real gameplay phases or admission are delayed.

## Exact production paths and scale

- Skill 22: `war3mapImported\TDPetVfxSwordDomain.mdx`, query radius 260, poised ivory/gold blades and compass formation, 192 triangles.
- Skill 29: `war3mapImported\TDPetVfxFrostDomain.mdx`, query radius 240, blue six-branch ice field and gently floating facets, 126 triangles.
- Skill 30: `war3mapImported\TDPetVfxVortexDomain.mdx`, query radius 280, three low rotating water spirals and crests, 168 triangles.
- Skill 33: `war3mapImported\TDPetVfxStarfallDomain.mdx`, query radius 240, jagged orange star field and low warm-energy teeth, 90 triangles.
- Skill 37: `war3mapImported\TDPetVfxEarthSealDomain.mdx`, query radius 260, ochre diamond seal, cross runes and four standing rune stones, 112 triangles.
- Skill 25: `war3mapImported\TDPetVfxFlowerBloomLoop.mdx`, query radius 100 at only the first actual road flower point, open green flower and pollen heart, 104 triangles. It does not claim a continuous field or the two other flower points.
- Skill 32: `war3mapImported\TDPetVfxLotusBurstLoop.mdx`, actual burst radius 230, large scarlet lotus petals and a warm inner crown, 186 triangles. Context plus authorized 250-ms visual dwell owns its release; the cosmetic loop does not authorize repeat damage.
- Shared texture: `Textures\TDPetVfxSolidWhite.blp`, 1222 bytes, 4x4 with three full mips, independently decoded as RGBA 255/255/255/255 everywhere.

All use effect scale 1.0 at the actual fixed center and terrain Z. The outer visible markers are conservatively inset 4 map units from the exact query radius; no visible triangle crosses the true radius. Each model is MDX800, two materials, two independent bones and three geosets. Body Blend and narrow Additive geometry are Unshaded, one-sided and depth-tested. No opaque field blanket is drawn; enemies and battlefield remain visible through the deliberately large negative spaces.

Stand 0-2000 ms loops, with no invisible beginning or phase transition. Death 10000-10001 ms is nonlooping and entirely transparent, in both every geoset and every material layer. Hold and release are controlled by real context lifetime, not these cosmetic clocks; a cleanup can hide immediately without leaving visible unbudgeted Death tails. Native Warcraft effect startup selecting Stand is still a client verification item.

## Rebuild and independent verification

Run from repository root:

    python3 assets/source/active-core-vfx/build_source.py
    MDX_PARSER_RUNTIME=/absolute/path/to/pinned/node_modules node assets/source/active-core-vfx/export_validate.cjs
    python3 assets/source/active-core-vfx/render_preview.py
    cp assets/source/active-core-vfx/output/TDPetVfx*Domain.mdx imports/war3mapImported/
    cp assets/source/active-core-vfx/output/TDPetVfx*Loop.mdx imports/war3mapImported/
    cp assets/source/active-core-vfx/output/TDPetVfxSolidWhite.blp imports/Textures/
    MDX_PARSER_RUNTIME=/absolute/path/to/pinned/node_modules node assets/source/active-core-vfx/export_validate.cjs --verify-imports

Reuse the trusted `assets/source/elemental-vfx/runtime` dependency lock. The exporter refuses any runtime except mdx-m3-viewer 5.7.9, TypeScript 4.9.5 and gl-matrix 3.4.4. No new dependency is required or installed.

The exporter writes actual MDX800 and starts a new parser from on-disk bytes. Checks include exact binary roundtrip, MDL text roundtrip, ordered source/parsed triangle corners, array lengths/indices/bone groups, nondegenerate triangles and unit normals, closed solid edge winding and positive volume, one-sided upward ground faces, exact single-separator texture path, animated extents and visible radial bounds at 10-ms samples plus all timing boundaries, non-static posed vertices, loop closure, alpha/material validity and transparent Death at five subframe samples. At 0, 50, 590, 600, 940, 950, 1200 and 1750 ms all neutral-core geosets stay visible. There is no fixed-stage visibility jump. Actual reparse summaries and exact hashes are retained in `production-manifest.json`.

`previews/neutral-core-contact-sheet.png` and `previews/neutral-core-loop-boundary.png` cover the first five domains. `previews/flower-lotus-contact-sheet.png` and `previews/flower-lotus-loop-boundary.png` cover the two flower cores. They show actual reparsed triangles posed by the parsed bones and sampled parsed material/geoset alpha. Grey dashed reference guides denote the query radius; they are not model geometry. These are offline software projections, not Warcraft screenshots. Native animation selection, terrain fitting, depth/occlusion, game-camera readability and FPS have not been tested. The implementing task must additionally verify exact MDX/BLP bytes in the current built MPQ.

## Existing-resource audit

Independent reparse of the unchanged `TDPetVfxSwordArray.mdx` confirms looping Stand 0-1000 ms, so it can remain alive for four seconds. It is 524 triangles, has roughly 100-unit planar extent and a visible 600-ms Death fade; it is retained as degradable decoration rather than the precise radius-260 reliable core. The former skill-30 TornadoElementalSmall and skill-37 EarthquakeTarget are native assets, not project-authored exact-radius long-lived mesh subjects. Their startup behavior has not been established from native game bytes here; the two new inspectable domains replace that reliance for the critical core.

## Optional timeline research source

The deterministic generator also emits ignored source descriptions for `TDPetVfxFrostPrison` (600-ms freeze / 950-ms fracture) and `TDPetVfxStarfall` (750-ms fall/impact / 3750-ms burn end). They are not default exports, not production imports and are not validated production models. They must never be used as authoritative phase cores under a phase fence. `--timeline` is an explicit offline experimentation export only. No timeline MDX, large sampled animation JSON or optional research preview is committed.
