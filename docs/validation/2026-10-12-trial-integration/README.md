# Formal72 → damage trial offline evidence

The inherited formal baseline is commit `72b2c9c3406868d33969c087dd5e6015abc3ac7b`, tree `d1b1567bd10b47e974ddbe8cfd44fcb91c2e5edc`. The trial candidate is map SHA-256 `03921c61e64e5392f8f9100291ca62df539b3f0bb8c7c4af47e82fa2bba21dde`; its actual MPQ JASS is `a47a8d6226776bf27ab033bb6539fae258f3e889ed55746ccc6b9d219445536c`.

## Current actual production evidence

- `artifact-final-result.json`: actual uTrG custom `narg` parent, fixed 1,000,000 HP, 0 armor/Normal, non-hero/non-mechanical/no inherited immunity, 260 base/max speed, no attacks/native bounties, native statue model reference, exact BTN/DISBTN paths, independently frozen icon hashes and all seven BLP1 alpha8 mips.
- `replay-final-result.json`: bounded execution of actual production TDInit registration, Game/Flow interface dispatch, concrete trial callbacks, independent native target creation/removal, 0/4 damage listeners and actual ordinary ledger. Timer-first/watchdog-first release, false/partial creation failure, two-match registration/reset and stale native deadline/route/watchdog/death callbacks, current source routes, death replacement/slot limits and withdrawn-lane cleanup run from real packaged JASS. The last-tick-before-release departed leader receives no prize and keeps its ranking occupancy. Real pet debuff records restore 260 and are removed explicitly; real `onAttack` captures old-trial proc identity and the old AoE cannot enumerate or damage the new ordinary wave or clear a newer pending serial. Actual score additions preserve 2,148,000,001 versus 2,148,000,000 in HUD, sorting and round-two prizes. Real equipment additional segments credit 25% in-round and reject old handles/replaced slots/post-release targets.
- `strict-delta-final-result.json`: exact independently approved source/MPQ/object/JASS contract. The complete unchanged bytes of 1,354 functions are preserved; 239 added and 404 changed compiler-visible functions have full exact templates, with no function deletions. Eleven new trial owners and nine changed existing owners are enumerated. Ordinary manager scalar, transaction, authority and asset contracts execute against current sources. All original object encodings are preserved except two explicit equipment tooltip strings, plus the one new uTrG object. No diagnostic/type/closure erasure or old Boss oracle widening.
- `exact-contract-PROPOSED.json`: despite its historical proposed filename, Astra independently approved only this exact SHA-256 `144aab9d9c31f08f1eea33d90f4f3ce64b71ae2a13bbaf36292057097492f1cf` on 2026-10-12. VerifyTrialDelta pins that SHA and rejects every other contract.

The first compiled candidate (`7c62b3469490d1bb380f215c3c7edd58f452d54df0d8956af5d566e353fac8fc`) is deliberately not accepted as final. `replay-expanded-first.log` records its actual last-tick departed-prize failure. The corrected candidate above passes both normal-release and Game-watchdog versions.

## Historical oracle preservation

`formal72-pure-boss-command.json` records the unchanged old Boss strict gate against the immutable formal72 map/source and immutable formal654 source/map. Its successful output log has the original formal SHA `142b05d9dbba68ab0b2f515e7e68922315ab0d8237940d2500fd8b3144185aac`. The old gate and its reviewed templates are unmodified and never accept the new trial map. `historical-boss-python-complete.log` ran all 35 old Boss tests, including five real map/harness tests, with zero skips. `historical-manager-python.log` records 13 manager tests.

Historical source test input is restored from the pinned formal72 git commit/tree by `tests/python/trial_formal72_fixture.py`. A checkout must retain that reachable git history; a source-only archive without `.git` is not sufficient to recover this fixture. A source-only backup must also retain the required git history or the exported immutable inputs; the test helper does not silently reconstruct missing git objects. Missing history fails explicitly and never substitutes mutable current source.

## Reproducible commands

All commands run from the integration repository root; none compiles, edits an MPQ, launches Warcraft or pushes.

```sh
python tools/VerifyTrialArtifact.py ExampleMap.w3x --output docs/validation/2026-10-12-trial-integration/artifact-final-result.json
python tools/VerifyTrialReplay.py ExampleMap.w3x --output docs/validation/2026-10-12-trial-integration/replay-final-result.json
python tools/VerifyTrialDelta.py ExampleMap.w3x --source wurst --reviewed-contract docs/validation/2026-10-12-trial-integration/exact-contract-PROPOSED.json --output docs/validation/2026-10-12-trial-integration/strict-delta-final-result.json
```

The original complete Python run used 461 tests and recorded eight failures/five errors confined to six historical fixture or mutation-input assumptions. Those six files and their current Trial dependencies were repaired and re-run as a frozen 119-test batch, all passing without skips. `combined-python-coverage.json` reconciles all 473 final unique test IDs: 354 unchanged tests from the complete run plus 119 affected/current tests from the narrowed run, with zero uncovered IDs or unresolved failures. This is combined-batch coverage, not a single all-green run. Exact commands, immutable input paths, actual trial SHA and code-file/log fingerprints are in `full-python-final-command.json` and `targeted-repaired-final-command.json`. Build/check commands and their original transaction provenance are recorded separately in the formal delivery directory.

## Explicit boundaries

No native Warcraft playtest, native pathing/control visual behavior, timer delivery, multiplayer synchronization, balance or FPS was observed. Native engine calls and collections are modeled boundaries; all trial gameplay guards and production compiled methods execute. Integer score/HUD checks are exact; the replay does not emulate arbitrary fractional float32 behavior.

No lawful verified target 1.28 installation archive was available. The packaged model reference matches the fixed WurstStdlib `Units.golemStatue1` / `UnitIds.battlegolem` metadata, which is static consistency evidence only. Native model existence and the target installation's actual attack-type table remain NOT_VERIFIED. Normal non-hero armor does not imply every attack type deals 1× damage. Provisional source damage arithmetic assumes known current source bonuses and bounded attack/armor multipliers; it does not cover unreleased equipment or guarantee survival against arbitrary future single-hit damage.
