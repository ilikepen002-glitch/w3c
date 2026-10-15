# Archer native attack-flow restoration

## Scope and artifact

This restores only the seven ARCHER catalog identities (uA11/uA12/uA13/uA14/uA15/uA6A/uA6B) to direct native ATTACKED split registration and removes scripted target redirect, park, recovery orders and zero-acquisition projection from that family. The other 28 tower identities retain their existing priority policy and order transaction. Existing work/cast/sale/pet-busy safety checks remain read-only on the archer path.

Implementation base: 1c9ec8ac333d6e7e794d2f375c7e63e121098345, tree-equivalent to published bbe7ad67d3e66272b2da2822b70022f307c12fa5. The cancellation of spirit-modified native attack appearance is preserved.

Candidate map SHA256: c0f210f906b9d3437d5040be09373797387147e4acf224565ffbc3dcf657d67f
Display name: 契灵守卫战 20261015-0958-UTC+8

No damage, TTL, attack-point, tower data or object/resource edits were made. Shared all-visible arrows launch at attack start; true native primary damage authorizes split damage. Immutable original damage, equipment extra arrows, pet impact hooks, trial contexts and sole-expiry volley destruction are retained.

## Automatic validation

- Official Linux full checks: PASS, transaction linux-vdmdyanf. Typecheck and all Wurst tests succeeded, including 7-native/28-scripted catalog routing.
- Official Linux map build: PASS, transaction linux-ksyyn9ns. Locked compiler/Grill/JDK/stdlib probes, 154 legacy-JASS allocator checks, active cooldown, startup, all 407 import bytes, map-info and object parsing passed.
- Actual archive delta: 427 members, only war3map.j and timestamped war3map.w3i changed from the published native-appearance map; all other object/resource bytes are identical.
- Actual equipment/range replay: all 245 identity/loadout cases passed. Archers retain real acquisition when stale parked state exists; non-archers retain parked projection, and secondary equipment attack/speed attributes remain correct.
- Actual full-arrow replay: 40 towers × 4 overlapping volleys × 7 arrows = 1120 launches and 1120 peak live arrows, none budget-suppressed. Shared timer, epoch cancellation, failed native effect creation and Fx recycler cleanup passed; warm pool returns to 48. Independent combat case verified six shots, six launches and six real split-damage segments.
- Targeted Python source tests: PASS; source negative mutations reject restored archer priority admission, omitted final branch, stale recovery control, range projection, stopped global setup, early volley destroy, mutable damage basis and other unsafe changes.

- Actual target-priority/archer packed gate: PASS. All seven archer identities each completed six stable and thirty changing-HP/primary starts, 252 starts total. Every start immediately launched all selected arrows and produced exactly its own 11/23/37 native-primary-authorized side damage. No archer Best, Accept, Redirect, attack or stop control ran. All 28 non-archer selectors and true/false/synchronous transaction, manual lock, identity, forty-tower sparse recovery and range regressions passed.
- Archer lifecycle and integration: PASS for manual/stop/hold/empty-field/target-death behavior, stale parked/pending recovery alongside Dryad, consumed-volley/new-allocation/old-expiry identity, two sources sharing a primary, spell/code/Tspl recursion filters, work/cast/sale/pet/owner/epoch safety, equipment six-to-seven arrows, trial revision reuse, deferred target death/removal/leak/reset, lethal primary and copied values surviving volley expiry. Immutable basis integration retained primary 210 with side basis 100.
- Negative coverage: all 26 source and 18 packed mutations rejected by specific semantic assertions; interpreter faults are not accepted as negative-test evidence.
- Independent chronological packed replay: PASS, forty delayed primary hits and eighty side-damage segments across two twenty-attack scenes, peak four in-flight volleys, forty expiries and zero final live/pending records. Timers are delivered by absolute deadline within the unchanged historic expiry window, rather than immediately emitting hits. No scripted order, stop or acquisition writes occurred. See astra-review/replay_chronological.py and .json (JSON SHA256 313fe8a8c57ea868b4db77ef0912c1a3463c0e8f8fc152a0f66bd62821adf222).

The final target-priority JSON corrects one legacy event-observation sentence without changing any verification body. Its verification_execution_tool_sha256 preserves the actual executed tool hash; tool_sha256 identifies the final wording-only revision, with metadata_only_correction explaining the difference. The raw execution log is retained unchanged. Actual client timing was not observed.

## Broad historical Python-suite limitations

The additional broad source diagnostic is NOT PASS: 222 methods ran, 203 passed; 19 methods failed/errored, plus a class setup failure prevented ten methods from running. There are ten reported assertion failures and fourteen reported errors (including subtests/setup); 96 unclassified tests are explicitly not covered.

Every failing method and the inheritance setup error were re-run against the unchanged, published-equivalent native-appearance baseline and reproduced the same outcome. See broad-source-baseline-comparison.json, baseline-source-failures.log and baseline-inheritance-fixture.log. They include stale source-shape assertions and missing historical inputs, not a newly introduced archer result. In particular, the equipment Phase-C test expects the old four-argument split-shot helper even though the released optimized helper already takes the cached distance as its fifth argument. Those legacy assertions were not weakened in this change.

## Lifecycle audit and limits

All supported tower removal paths were inspected. Direct tower removal occurs only in sale and rejected construction, both of which clear sale state first. Native construction cancellation and tower death also clear it. Pet/other RemoveUnit paths remove pet visuals or enemies, not host towers. No supported busy/selling sale-record leak path requiring a new identity mechanism was found.

The historic .35-second margin plus captured flight expiry remains unchanged. Historical conditions under which a hypothetical late primary arrives after expiry remain possible; this restoration does not claim to fix arbitrary native projectile identity or timing. Continuous/timed replay reports use declared controlled inputs within that old window.

No Warcraft III client was launched. Actual 1.27a engine turning, attack point, native callback timing, visible smoothness, FPS and multiplayer synchronization are not measured. The existing JASS/v1.28 build configuration is preserved.

## Final review

GPT-6 Astra final verdict: PASS WITH NOTES for the same c0f210 candidate and frozen production inputs. Non-blocking notes: no 1.27a live test; unchanged historic TTL/FIFO identity limits; broad historical Python failures reproduced on the unchanged baseline. See astra-review/FINAL_REVIEW.md.
