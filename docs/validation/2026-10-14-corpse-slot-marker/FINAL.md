# Corpse, slot name, and wild marker verification

Result: PASS WITH NOTES. The final candidate is SHA256 f28f375462e64ea08e159eea88e386582cdcb1e2b3dc448fe979108a40468a13, based on published e599851c1e05cb062f8e9026d87da35de6f6aad5.

- Official complete Linux typecheck/tests passed, followed by official build and its packaged artifact gates.
- Build and checks use identical 225 Wurst/test/configuration inputs; all 837 current source/test/tool/import inputs matched the successful build snapshot.
- Four Boss types each passed five packed callback scenarios: corpse, revived, removed, changed identity, changed type. Real Boss death, duplicate delivery, and delayed cleanup awarded rewards only once. The native timer delivery is modeled; the actual packed callback, cleanup predicates and closure destructor execute.
- Wild markers passed six viewer/visibility/liveness scenarios without gameplay state changes; clearing is idempotent, and direct record destruction releases its marker. Existing capture deadline, expiry/capture ordering, leave/defeat/game-over cleanup, cross-Boss readiness and reward-ball cases also passed.
- Three exact negative mutations were rejected for revival, identity and viewer guards.
- All 415 other packed members, including models, textures, sounds, objects and imports, remain byte-identical. Only JASS and W3I differ. After normalizing the normal build stamp, W3I changes only Enemy Slot to 黑潮怪物. JASS retains computer/ORC Player(4) and has no player-name override.
- The compiler renamed an unrelated enum local from enemy_1 to enemy_2. The artifact guard now binds the explicit null rejection to the actual GetEnumUnit result; the complete matrix and added positive/negative regressions pass. This is a verifier fix, not a production rule change.

## Reproduce focused checks

Run from the repository root:

    python3 docs/validation/2026-10-14-corpse-slot-marker/verify_third_batch.py
    python3 docs/validation/2026-10-14-corpse-slot-marker/verify_mutations.py
    PYTHON_CANDIDATE_MAP="$PWD/ExampleMap.w3x" python3 -m unittest discover -s tests/python -p 'test_pet_compiled_rule_guards.py' -v
    python3 -m unittest discover -s tests/python -p 'test_boss_corpse_cleanup_source.py' -v

The focused scripts read the current ExampleMap and compare packed resources to the exact published predecessor. The first script also accepts a candidate map path. It requires the repository history and the existing tools' Python dependencies. The official build entry remains tools/Run-WurstLinux.py, with verified --tools, --jdk and --stdlib arguments as documented by that tool; no ad hoc packaging is substituted.

Limits: no Warcraft engine run, render/FPS measurement or native animation timing claim. Boss death lengths are offline MDX evidence (three 2-second sequences; Leoric 2.234 seconds), with a 3-second cleanup delay. This batch changes no tower or spirit balance numbers.
