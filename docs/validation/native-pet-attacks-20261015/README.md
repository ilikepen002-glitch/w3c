# Native tower attacks during pet possession — verified release

- Base source/map: `0304f12b4e74de623f359a29d45f3d32e9fc93f2`.
- Runtime source candidate: `4f2a3eacdd09ff5778792a2b2ae56bd95dba3800`.
- Final root map SHA256: `3b8c5c35fa03120108b416d5db80ab26d7d9236d02367a3c7827c62d25a2a7c5`.
- Baseline root map SHA256: `87adc84f8513e69dafbeb4dc748e7fbb2b197673039202bc34380e873a985654`.

## Scope

Remove the single ordinary-hit `tdCombatVisualHit` call in `TDPetCombat`.
This removes the possession elemental hit decoration, gold lightning line and
its incidental decisive-hit RifleImpact accent. No alternate attack renderer
is introduced. All other non-comment lines of that runtime package were
compared byte-for-byte with the baseline and are identical.

Damage, decisive-hit counters/multipliers, additional passive damage, debuffs,
hero passive triggers, active spells, active buff/cast feedback and tower split
arrows are unchanged. Unused renderer/assets remain in source/imports; no
unrelated resource cleanup is included.

## Evidence index

- `checks.log`, `checks-manifest-summary.json`: official isolated Linux
  `Run-WurstLinux.py checks` PASS, including typecheck and Wurst tests.
- `build.log`, `build-manifest-summary.json`: official isolated Linux build
  PASS, legacy-JASS/cooldown/startup/object/import gates. 407 imports verified.
- `artifact-report.json`: actual packed JASS replay, 25 ordinary hits across
  five elements with no new effects/lightning, 18 baseline/candidate combat
  trajectories identical, and tower split-arrow traces identical.
- Strict archive delta: all 427 member names unchanged; only `war3map.j` and
  the display timestamp fields in `war3map.w3i` differ. All other bytes match.

The combat comparison uses `VerifyCombatVisualArtifact.verify_gameplay` with
both actual scripts. Its 18 cases cover six loadouts under normal, failed
native effect creation and exhausted effect budget conditions; compare damage,
damage timing, score, gold, random draws, control, resolve counters, cooldown,
bonuses and target speed. Split comparison uses
`VerifyLocalCombatHotpathArtifact.split_traces`; archive validation uses that
module's `archive_delta`. Historical gate expectations were not relaxed.

## Tests and known baseline limitations

- Narrow `test_basic_hit_vfx_source.py`: 4/4 PASS.
- `test_pet_attack_phase_one.py`: six source tests PASS; four artifact-dependent
  entries skipped in the source-only invocation because no map was supplied.
- `test_elemental_pet_runtime_source.py`: six PASS, two ERROR for missing
  `visualSwordCut` and `visualSeedSpread` fixture stubs. Both errors reproduced
  unchanged on base source `0304f12`; this release does not modify those files.
- The old full `ReplayCombatVfxARegression.py attack` gate stops on historical
  A102 native bonus expectation 18 versus actual 90. The identical mismatch
  was reproduced against the baseline map. `war3map.w3a` is byte-identical
  between the baseline and candidate. This is not claimed as a full gate pass.

The final root map is copied byte-for-byte from the passed build; it is not a
new compilation. No in-game session, native visual inspection, FPS measurement
or engine armor simulation was performed. Rendering/clock/native boundaries
are modeled in the packed-JASS replay.
