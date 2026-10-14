# Five elemental bound-primary hit meshes

Production integration replaces only the ordinary bound-primary hit models. The existing TDPetCombat on-hit call, admission/ownership/cleanup, 128 total / 32 hit / 2 per-source / 120 creations per second / 8 moving and split-arrow budgets are unchanged. Unbound attacks and purple specialization weapon scope are unchanged. Kills preserve the admitted elemental effect and its deadline; finisher adds no effect.

Gold (184 triangles) and Fire (96 triangles) reuse the original reviewed sample geometry exactly. Wood (80) has crossed green leaves/thorns, Water (96) an ice crescent/crystal shards, Earth (88) low ochre slabs/mineral seams. Every mesh is MDX800, 2 materials, 1 bone, no particles, ribbons, sounds or events. Total new imports: approximately 67 KiB. All use unchanged Textures\TDPetVfxAtlas.blp.

The complete visible envelope is authored into non-looping Stand: Gold 180 ms, Wood 280 ms, Water 260 ms, Fire 230 ms, Earth 280 ms. Each starts fully opaque, expands over 25 ms, and fades over the final 80 ms. The existing shared cleanup holds its hit slot for this full envelope; Death is fully transparent, so releasing an effect cannot leave a visible unbudgeted tail. A 50 ms cleanup cadence can conservatively retain a transparent slot for up to one tick. No new timer, dummy, damage, launch-event or fake projectile is added. Gold's pre-existing lightning accent and wood's pre-existing second hit piece are retained within their existing two-slot admission.

Rebuild using the existing pinned parser runtime (mdx-m3-viewer 5.7.9, TypeScript 4.9.5, gl-matrix 3.4.4):

    python3 assets/source/basic-hit-vfx/build_source.py
    MDX_PARSER_RUNTIME=/absolute/path/to/pinned/node_modules node assets/source/basic-hit-vfx/export_validate.cjs
    cp assets/source/basic-hit-vfx/output/*.mdx imports/war3mapImported/
    python3 assets/source/basic-hit-vfx/render_preview.py

Exporter reloads actual MDX bytes and verifies exact roundtrip, geometry/normals/extents, format, texture path, budget and sampled alpha every 10 ms. Preview is software projection of that parsed geometry and animation, not a Warcraft capture. Native camera scale, depth/occlusion, actual appearance and FPS are not tested. `tools/VerifyCombatVisualArtifact.py` verifies exact current packed imports and exercises actual packed JASS hit/finisher/admission/cleanup/gameplay traces; it must be run after the map build.
