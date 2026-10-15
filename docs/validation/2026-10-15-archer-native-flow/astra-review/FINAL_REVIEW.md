# Astra final review — native archer attack restoration

**Verdict: PASS WITH NOTES.** No blocking finding in the reviewed production change or frozen candidate. Approved scope is the targeted historical attack-flow restoration for all seven ARCHER types, not a claim of arbitrary native-projectile identity correctness or measured Warcraft client behavior.

Reviewed 2026-10-15 UTC by the designated Astra review agent. Read-only production review; no additional Grill/build or Warcraft launch performed by reviewer.

## Exact artifact and scope

- Source change commit: `380b8876dd7809a974be90e5fd13706faaed5981`, parent published `bbe7ad67d3e66272b2da2822b70022f307c12fa5`.
- Compiler execution base `1c9ec8ac333d6e7e794d2f375c7e63e121098345` has the same source tree as that published parent. Reparenting did not change compiler inputs.
- Frozen candidate and current root `ExampleMap.w3x` both SHA256: `c0f210f906b9d3437d5040be09373797387147e4acf224565ffbc3dcf657d67f`.
- Actual candidate `war3map.j` SHA256: `55731ea0f66390da225c745cfb6483afbb1b3b777dfd89d6b983f59392504f06`.
- Production changes are limited to four files, 42 insertions and one deletion. Final artifact/document commits may follow; approval follows the exact production hashes and candidate bytes below, not an unreviewed later code change.

| Production file | SHA256 |
| --- | --- |
| `wurst/items/TDInventoryRuntime.wurst` | `f96b78e9aa489472b7bae133947692d5c14220e752cffad05053462c1ed1cecc` |
| `wurst/towers/TDTowerRuntime.wurst` | `be2349d42c2bcc48054947832d289cdb7e4cd5b463111a6413c34942badf6b41` |
| `wurst/towers/TDTowerTargetPriorityRules.wurst` | `5f53c664695203f4b43bd35dbe3f12e5f52da1e287b812c31a0a6e501fda9eff` |
| `wurst/towers/TDTowerTargetPriorityRuntime.wurst` | `831e3a9bf4629812b36ea775e2eb621601ef9ba60056d9b6c8eb45006ea7afdf` |

## Findings

1. All seven catalog ARCHER identities route native ATTACKED directly to the existing split registration, after independent read-only source/lane/pet/sale/lifecycle guards. Existing working/casting/owner/epoch state remains respected, without introducing a pending/manual/player-hold acceptance token or creating a state record.
2. The other archer control entrances are consistently excluded: order observation, redirect, park, recovery, and inventory acquisition projection. A stale queued archer is popped, its pending state cleared, and its native acquisition range restored only if changed; it is not requeued or given attack/stop orders. There is no acquisition write per ordinary archer attack.
3. Global priority setup remains installed. All 28 non-archer types preserve their scripted selection and transaction paths, including dryad absolute-lowest-HP and melee Boss/guard/normal ordering. The shared working state used by auras is retained.
4. Split registration, immediate all-arrow visual launch, snapshot selection, damage dispatch, immutable damage basis, trial identity, equipment count, recursion filtering and historical TTL are unchanged. `consume` only dequeues; the original expiry remains the unique destroy owner. The dangerous historical consume/destroy/reallocation regression is not reintroduced.
5. Supported tower removals clear sale state. Sale/RejectConstruction explicitly clear it, and construction-cancel/death handlers do likewise. The reviewed game/pet removal sites remove enemies or pet visuals/wild units, not host towers. No supported stale-sale-handle path was found; an unrelated state redesign is not warranted.
6. No production departure from the approved seven-archer PLAN, no reinstated visual budget, no rejected late-launch implementation, and no object/resource rollback were found.

## Evidence checked

- Official locked `Run-WurstLinux.py` full checks and build: PASS (`official-checks.log`, `official-build.log`, and their manifests). Independently rechecked all current `.wurst` and configuration compiler inputs against both manifests: no changes. This covers the frozen Wurst tests as well as production source.
- Actual archive comparison: 427 members; only `war3map.j` and `war3map.w3i` differ from the published native-appearance baseline. All other object/resource member bytes are identical (`archive-delta.json`).
- Final actual-MPQ priority/restoration gate: PASS (`target-priority-archer-native.json/.log`). Seven archers execute 252 starts total: six stable-target and thirty changing-primary/HP starts each. Each start launches the entire selected side set immediately, and each supplied native primary hit produces its expected side targets and immutable amount, without priority query/reorder/stop. The test's native event delivery is controlled.
- The same gate covers all 28 non-archer selectors, old true/false/synchronous reentry transactions, manual commands, bounded recovery, mixed archer/dryad stale recovery, independent lifecycle exclusions, equipment extra arrows, two sources sharing a primary, A/B/A, code/spell/Tspl exclusion, lethal primary, target death/remove/leak, reset/trial generation and revision reuse, copied delayed data after volley expiry, and consume/new-allocation/old-expiry safety. Twenty-six source and eighteen packed semantic mutations are rejected by the intended assertions.
- **Independent chronological actual-packed review:** `astra-review/replay_chronological.py/.json`, JSON SHA256 `313fe8a8c57ea868b4db77ef0912c1a3463c0e8f8fc152a0f66bd62821adf222`. Twenty same-primary starts and twenty A/B/A starts, every 0.07 seconds, primary hits at start +0.25 seconds. Actual production expiry callbacks run in absolute-deadline order. Each shot has its own two side targets and a distinct original damage amount. All forty primary hits produce the exact eighty expected damage segments, including both final shots. Peak four pending volleys; forty expiry callbacks; final pending/live zero; zero script attack/stop/acquisition writes. The 0.25-second arrival is an explicit test input within the unchanged 0.55-second window, not a native attack-point measurement.
- Actual range/inventory replay: PASS, 35 types ×7 loadouts =245 cases (`range-packed.log`).
- Full-arrow actual-packed renderer/Fx replay: PASS, 40 towers ×4 overlapping waves ×7 selected arrows =1,120 attempts/peak active, no visual-admission omission. Shared timer cleanup, epoch cancellation and native effect-creation failure cleanup pass, warm pool returns to 48 (`full-arrow-packed.json/.log`). Its separate six-shot combat case means six side arrows in one volley, not six primary attacks.
- `git diff --check` passes. Targeted updated source tests pass. The production source and actual compiled entrance/recovery functions were inspected, rather than relying only on regex results.

## Non-blocking notes required at delivery

1. **No Warcraft 1.27a live play was performed.** Offline replay proves the supplied native-event sequences through the actual packed code. It does not measure engine windup, rendering on the user's machine, FPS, multiplayer synchronization or arbitrary native order cancellation. The repository's existing v1.28 build configuration is not the user's client version.
2. The historical `.35 + maximum captured flight` TTL and source/primary-target FIFO matching remain intentionally unchanged. They predate the recent priority intervention. If a native main hit arrives outside that old window, or an indistinguishable same-target canceled start precedes another hit, the historical attribution limits remain. This restoration removes the newer automatic archer reorders that created an avoidable interference path; it must not be sold as a universal projectile-identity redesign or a proven fix for every possible zero-damage cause.
3. The broad legacy Python suite is **not wholly green**: 222 methods ran, 203 passed; nineteen failing/error methods plus an inheritance class-setup failure reproduced on the published-equivalent baseline, and 96 unclassified entries were marked not covered. The comparison and raw baseline logs were inspected (`broad-source-baseline-comparison.json`, `baseline-source-failures.log`, `baseline-inheritance-fixture.log`). These pre-existing fixture/contracts failures do not block this bounded restoration, but must not be reported as a full-suite PASS. Official Wurst checks and the changed-path source/actual-packed gates pass separately.
4. An old verifier report sentence incorrectly named Warcraft 1.28 as an observed engine boundary. A metadata-only correction is allowed to replace it with a controlled-replay statement, retaining the executed verifier hash and recording the final text-only verifier hash. This does not change any test body, candidate or production code and needs no redundant build. A semantic code/test change would require review again.

Recommended delivery wording: restored the original uninterrupted archer attack/split entry and removed the later automatic archer retargeting intervention; all selected side arrows remain visible. Other tower-family priorities and modern safety/feature layers are retained. Actual 1.27a feel remains unobserved.
