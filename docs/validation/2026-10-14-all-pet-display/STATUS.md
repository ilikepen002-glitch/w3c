# All 15 species tower-display actions

## Scope

Ordinary append-only art/capability extension of the published Silver Mane display architecture. Species 2–15 gain indices 5–9; species 1 remains exactly unchanged. Only TDPetDisplayRules capability changes at runtime. No combat, scheduler, effect admission, damage, gameplay/object value or lifecycle change is included here. Real active skill visuals are handled by the independent VFX task.

The 14 new models add 603,480 bytes (about 589 KiB) in total. All 15 texture files, triangle counts, bone counts, cameras, materials, attachment sets, mesh/normal/UV/topology/binding bytes, original source JSON and all old 0–4 binary keys/sequence extents remain unchanged. The shared generator uses 17 keys per new interval; source caches and renders are deliberately not committed.

## Offline verification

- All 14 models were serialized, read again from final import bytes, and sampled independently at 128 offset midpoint times per new interval (70 intervals total).
- Every new interval visibly changes vertices and animates at least one non-root bone. Both loop intervals have exact vertex endpoint closure.
- Adjacent quaternion dots are at least 0.989; no short-arc/wrap jump is introduced. The new Spin is a bounded looking/banking/sway gesture.
- New sequence extents use 129 samples plus all key times, with 2-unit padding; every independent midpoint remains inside.
- All 14 original source exporters, with the shared append helper, reproduce exactly the same final MDX bytes as the pinned-binary append generator.
- A dry regeneration also matches the current import bytes exactly.
- The 15-pair source/resource gate passes, including raw old binary keys and original sequences/extents.
- Seven Python regression/negative tests pass: all pairs; runtime capability-only delta; rejection of original-key, missing-sequence, UV, and texture-reference mutations; revised limb rotation/recovery checks.
- Per-model previews render newly parsed final MDX poses with the exact original decoded BLP pixels. GIFs add short end-of-action reading pauses and are labelled offline. They are not gameplay captures.

Commands:

- `MDX_PARSER_MODULES=/path/node_modules node tools/BuildPetDisplayModels.cjs`
- `python3 tools/VerifyAllPetDisplayArtifact.py --output report.json`
- `python3 -m unittest discover -s tests/python -p test_all_pet_display_assets.py -v`
- After the unified build: `python3 tools/VerifyAllPetDisplayArtifact.py --map final.w3x --output packed-report.json`
- After the unified build: `python3 tools/VerifyPetDisplayReplay.py final.w3x --output replay-report.json`

The historical Silver-only VerifyPetDisplayArtifact resource delta is superseded by the all-species gate for this change.

## Pending shared acceptance

The parent-authorized independent integration now passed full Wurst checks, official map build, actual packed replay and final map hash closure. See integration/FINAL.md and evidence. No command overlapped another task's Grill use. Warcraft native rendering, tower overlap/culling and FPS were not tested.

## Cast legibility revision

A visual review found the first five-species cast sample too subtle, despite numerical vertex changes. Species 3, 5, 9, 11 and 14 now have stronger visible claw/forehoof/front-paw/horn/fist gestures using the actual bone axes and pivots. The mountain gibbon double-fist shoulder rotation increases from -0.55 to -1.20 radians so fists reach chest/head height; no limb scale/stretch is added. All five new start/peak/end panels were visually inspected by the parent and approved.

The revision changes only those five Cast intervals. All original keys and all previously added Display5–8 keys/sequence extents remain exact, verified separately in cast-revision-delta-report.json. All 70 intervals were re-sampled after revision, and all preservation/negative tests re-passed. Final compact gallery and model hashes are updated; full five-species enlarged Cast GIFs and panels stay in scratch. No Grill or map build was run during the art revision; the subsequent parent-authorized integration is verified separately below.
