# All 15 display integration: PASS

- Base source: 347dab20329e7c967564f49457ccebd948827464 (A R2 source).
- A R2 baseline map: 05746604cc6cc7108d95619cd6538fa508d97db18dabb4aed184d125ed56d504.
- Integrated source: b453393d9a1d979b88ac06a5572ccd9b176f2eb8 (1263c62 then b453393 cherry-picks).
- Final map: 9f8a2a52902016a59f22883b0cde2bccede4ec06eeda5ff95453010e1159d887; 5,970,622 bytes. Baseline was 5,817,894 bytes.
- Official Linux full checks: PASS, transaction linux-3espeuia.
- Official Linux build: PASS, transaction linux-1kgk4pmf. An earlier attempt ran out of disk during generated JDK copying, before compilation/output. Only this task's reproducible pose caches and incomplete install copy were cleaned; successful checks were reused.
- Four ignored licensed Leoric inputs copied and verified exactly against the existing provenance manifest.
- Actual final MPQ contains all 15 exact MDX/BLP pairs. Original geometry, UVs, normals, rig, 0–4 sequences/extents and binary keys are preserved; all 15 atlases unchanged.
- Delta against A R2: same MPQ members; media changes are exactly the fourteen extended spirit MDX files. All A resources, all other media, gameplay unit fields/parents, other object/terrain files and TimerStart site count remain unchanged.
- Actual packed display replay: PASS across 525 tower-profile/species combinations and every species' 5–9 actions; 22 active traces equivalent with/without visuals; failed-start and post-hit invalidation produce no Cast; pause, upgrade, stale ownership, 80-bound steady state and rebinding cleanup pass. Five display mutations and six rebinding mutations were rejected.
- Seven Python model/negative regression tests and all 70 offline interval samples passed before integration. Revised five Cast silhouettes were visually inspected and approved separately.

This is a verified local build, not a Warcraft rendering/FPS/playtest result. Root owns publishing. A's later documentation-only changes may be integrated before publication; do not replace this new all-species map with an older A or c7 map.
