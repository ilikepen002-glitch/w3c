# Retired pet UI resource audit

## Scope and measured baseline

Final parent source: `674f00186627fa0637ecc58fe27728613f137479`.
Initial investigation was against frozen capture-65; final checks/build use the released terrain-64 combination.
Baseline map SHA-256: `335fe6774fd9bff432b8c7e412f0cbbb91953ba9cc2aec1047dd1afb01f8041f`.

- Map: 5,863,657 bytes; 476 listed MPQ members.
- Three retired portrait families (FlamePhoenix, StormFaerieDragon, GhostWisp):
  63 normal + 63 disabled BLP files, 1,524,852 raw bytes.
- Their actual existing MPQ compressed blocks total **419,750 bytes**. This is
  payload savings, not a prediction of exact rebuilt map length; archive tables,
  metadata and the corrected tooltip can change the final net delta.
- Skill capacity stays 49. IDs 4, 9, 10, 13, 14, 15 already fail
  `tdPetSkillDefined`/`tdPetSkillAllowed` in the baseline and do not generate
  preview or slot objects. **Additional object savings: zero.** No renumbering,
  registry changes, shared native icon deletion or tower ability deletion.

## Reference evidence and conservative bounds

`tools/AuditMapResourceReachability.py` reads actual MPQ bytes, scans every
non-image/audio member including JASS, object data, all MDX/MDL payloads,
SLK/FDF/TOC and unknown formats, plus all current Wurst sources. Model payloads
are conservatively roots even if their own reachability is unknown. Paths are
case-normalized and JASS escape separators collapsed. Both implicit disabled
icon sibling paths and dynamic Wurst string fragments retain resources.

No retired family name appears in these roots. The old names appear only in
archive list/import inventory metadata. Current species paths are assembled by
`tdPetSpeciesIconStem`: `TDPetSpecies` + two-digit species, then optional quality.
Current runtime/generation helpers contain no old family stem or branch.

This is a conservative inventory and a narrowly reviewed deletion allowlist,
not a claim to solve arbitrary runtime string construction. Unknown resources
are retained. In particular credits, `dummy.mdx`, map minimap and preview remain;
implicit engine/stdlib references or attribution are sufficient reasons not to
delete them. No new species texture/model or model material is changed.

## Rebuild and regression safeguards

- Default pet UI generator handles only the 15 current menu icon pairs.
- All 63 obsolete portrait SVG inputs and historical hashes remain in
  `archived_assets`; generated obsolete BLPs cannot silently return during
  `--verify-only` or a default rebuild.
- Existing historical contact sheet is explicitly labeled archival.
- Current menu BLP bytes remain locked; all 15 new species and their 75 BTN/DIS
  pairs remain untouched.
- Optional `--baseline` audit requires the exact 126-member removal and byte
  identity of every retained media/model/SLK/FDF/TOC member.
- `--require-retired-absent` verifies the final packaged deletion and absent
  inactive preview/slot rawcodes.

The small accompanying tooltip correction uses the same
`tdGhoulCorpseExplosionDamage()` helper as epidemic ticket creation. Its four
quality amounts are 45/72/99/126; runtime damage and 180-radius epidemic behavior
are unchanged.

## Validation checkpoint

13 focused Python source/resource-negative tests pass; manifest hashes and
`git diff --check` pass. An expanded 44-test sample passes 42 with two errors
reproduced unchanged against the frozen baseline: unavailable historical TDHud
Git object, and the historical Pbat fixture expecting pre-balance attack values.
Final locked full Wurst checks and build PASS on the released parent. The new
four-quality Wurst tooltip test passes (float comparison tolerance 0.0001;
actual formatted strings are exact). Actual-map pet UI verification PASS:
633 Channels, 93 slot displays, 61 prototypes, 15 models/atlases and 75 species
BTN/DIS pairs. No game was launched or visually tested.

Final map: **5,433,550 bytes**, SHA-256
`59a519fbb47761840320241f08a3b95e8a717cd38fb603e5da0911abf9a3a8eb`.
Actual net reduction: **430,107 bytes (7.34%)**; 476 → 350 archive members.
All 330 remaining media/model resources are byte-identical. All 1,047 ability
IDs remain; only 16 `aub1` fields change in `Ps30`, `Ps61`, `s230`, `s261`.
Unit/item/buff, terrain, pathing and doodad payloads are byte-identical.
Packaged JASS bodies for epidemic ticket creation, epidemic explosion, damage
basis, capture handling and terrain validity are unchanged after canonicalization.
The text correction does not reduce or increase actual epidemic damage.

Checks transaction: `linux-qy_7o02s`; build transaction: `linux-44vu1w9j`.
Reproduce read-only artifact checks with:

```
python3 tools/AuditMapResourceReachability.py ExampleMap.w3x --require-retired-absent --baseline <formal-parent-map>
python3 tools/VerifyPetUIArtifact.py ExampleMap.w3x
```

Detailed deletion allowlist and object delta:
`2026-10-13-retired-pet-resource-result.json`.
