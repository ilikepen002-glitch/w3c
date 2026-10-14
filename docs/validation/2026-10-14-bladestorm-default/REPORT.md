# Bladestorm defaults to autocast on first grant

Ordinary narrow fix: A132 uses native Aslo with slowon/slowoff. Its metadata default was UNKNOWN while Bloodlust already defaulted ON. Change only the A132 initial choice to ON. The existing stable construction/upgrade/cancel entrypoints run initialization after busy work and equipment refresh; persisted manual choices still take precedence. No new orders, timers or lifecycle state were added.

## Verification

- Full typecheck and Wurst tests PASS: `_build/linux-3z6wow66/manifest.json`, `19-java.log`. This tested the default change on 96bddd3; then merged the independently checked corpse-tooltip/overhead freeze f7845d.
- Full integrated Linux build PASS: `_build/linux-uphz7v_o/manifest.json` at e46afd9. No further gameplay source changes after build.
- `VerifyActiveCooldownContract.py ExampleMap.w3x`: PASS all 24 shared definitions, 35 hosts, two native active skills, 40 equipment items and 63 dynamic support mounts.
- `VerifyBloodlustAutocastArtifact.py` and `VerifyBladestormAbilityArtifact.py`: PASS. A131 unchanged; A132 retains 41 levels, 9-second base cooldown, range 780 and zero carrier slow.
- New `VerifyBladestormDefaultAutocast.py`: executes actual packaged uO15 upgrade start and uO6B completion, initialization, manual-order listener, immediate/deferred CDR restore and generation-guarded cancellation callback. PASS first-grant ON, manual OFF retention, repeated completion, stale cancel suppression, matching cancel restore, and forgotten handle default ON. Engine handles/ability mounting/order dispatch and unrelated upgrade presentation/equipment bridges are modeled explicitly. The same replay fails against the baseline at the default-ON assertion.
- Strict whole-MPQ delta: only war3map.j and build metadata war3map.w3i changed. Actual JASS differs by exactly the A132 metadata UNKNOWN-to-ON assignment; all other script bytes, object data and assets are identical to f7845d. See strict-delta.json.

Map SHA256: 209b08ea44e82c675176be57694eb1e76650aa54305d6386879daf52abf69d30

Not tested: Warcraft engine/UI input or actual automatic casting timing. No game was launched.
