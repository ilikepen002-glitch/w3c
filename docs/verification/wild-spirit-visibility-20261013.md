# Wild spirit visibility inspection

## Scoped source change

Wild unit object generation changes scale from 0.85 to 4.25, exactly five times.
Attached visuals remain 0.45 and collection displays remain 0.65. Native Ghost
Visible (`Aeth`), zero collision, spawn pathing disable and invulnerability are
unchanged. No lifecycle, capture, combat, VFX or balance changes are included.

## Color evidence (existing formal map, before this change)

Inspected `ExampleMap.w3x` from source commit
`1d4938cf47a41ccb200526ec537fbf5986871f7c`, not a rebuilt candidate:

- All 480 wild objects have scale approximately 0.85, `uabi=Aeth`, `ucol=0`.
- All 15 packaged model and 15 packaged texture hashes exactly match
  `assets/source/elemental-spirits/import-manifest.json`.
- Fresh mdx-m3-viewer 5.7.9 parsing of the actual imported MDX files finds one
  opaque layer each: texture ID 0, alpha 1, material/layer flags 0, no layer
  animation or geoset color animation, no replaceable/team-color texture.
  UV coordinates range from 0.01953125 to 0.98046875.
- Actual BLP1 files decode to colored 256x256 atlases. Mean HSV saturation by
  species 1–15 is 0.253, 0.323, 0.401, 0.454, 0.444, 0.408, 0.397, 0.426,
  0.317, 0.573, 0.542, 0.604, 0.359, 0.322, 0.413. This is an atlas-wide
  diagnostic, not an on-screen perceived-color measurement.
- Formal JASS contains one SetUnitVertexColor wrapper; its only caller is
  DummyRecycler_recycle. No wild-spirit runtime tint is present.

These checks rule out grayscale source atlases, a mismatched packaged atlas,
and explicit wild-spirit tinting in current source. They do not prove why the
user sees gray in Warcraft. The opaque shaded materials can be affected by map
lighting; small on-screen scale and muted base palettes are possible contributors,
not established root causes. `Aeth` is Ghost Visible, not evidence of an ethereal
rendering mode. Removing it risks regressing the previously fixed blocking issue.

## Validation boundary

- `python3 -m unittest discover -s tests/python -p test_pet_wild_visibility_source.py -v`: 1 passed.
- `python3 -m unittest discover -s tests/python -p test_elemental_pet_source.py -q`: 7 passed.
- `git diff --check`: passed.
- Wurst checks and new map build: pending the coordinated serial build token.
- Warcraft appearance, perceived size, camera overlap and native-engine behavior:
  not live-tested. A fivefold size change can cover nearby units visually without
  increasing their collision footprint.

Risk: low for the known scale field change. Implemented and inspected by the
current worker; no system-level lifecycle redesign or Astra gate is required.
