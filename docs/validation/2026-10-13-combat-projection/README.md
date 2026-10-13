# Bounded combat projection write hotfix

Formal baseline: bc96b4910a8ecd8ea428ba4a1de98937cf9bb0ec, tree 64eb930fb5c7db34480c84887a85f9d9eb56aa2b.
Candidate map: SHA256 a20d063f1e6d7bd484213483d939d545c9bd6429b336243f95d5f7fe64abd8df, 5744774 bytes.
Production source: 65fa19b03491deee204947176f6af1a3ad44ea00; source-only assertion update: 20bacc2.

Changes: compare actual native values before control-rank, projected acquisition-range and full composed enemy-speed writes. Retain missing-ability behavior, supplied/saved original speed bases, parked range, every projection computation and next-refresh external correction. Short-circuit readonly cooldown eligibility and reuse local catalog arguments/native ability read. No cache, state, timer, source snapshot, target rule or visual budget change. Building status uses root Misc DisplayBuildingStatus=1; the three 1200 inventory ranges remain.

## Evidence

Official serialized Linux checks and build PASS with identical input inventories. Transactions `_build/linux-lwu610c_` and `_build/linux-8xqb2_t_`; locked tools, JDK27 and pre1.29 stdlib unchanged. Full Wurst tests succeeded; actual active-cooldown gate includes nonzero deadline and early-level rejection. Native startup, script and import gates passed.

Actual MPQ guard, target-priority, wild 180-second/no-ETA, rebinding and aura routing/reuse/strong-to-weak/removal/constructor-negative gates passed. Independent comparison covers 16 eligibility cases and 13 numeric projection stages including gear, pet expiry, invalid binding, lock, native correction and park/unpark. Supplement covers real Boss burst390, saved original retirement base300 despite default999, trial260 and parked equipment changes. Seven semantic mutations are rejected with exact intended assertions.

411 archive list members and 390 media payloads match baseline; W3U/W3A/W3H and eight existing object/terrain/placement payloads are byte-identical. Four ignored Leoric source assets were restored from verified bytes and official packaging checked them. Retired icon objects/media remain absent.

Warm16 fixture: calls17822→17692, interpreted expressions63970→64036. Sixteen equal native setters become zero setters plus sixteen getters. Native-active+pet: calls1428→1369, expressions4702→4600. Empty enemy: calls836 unchanged, expressions2372→2373. The complete equipment/gear path and 640 source visits remain. These controlled counts are not engine opcodes or FPS measurements.

## Disclosed limitations and historical gates

No Warcraft launch or in-client FPS/Buff visibility claim. Numerical projection mirror does not fully simulate original/derived damage, RNG or engine native casting. Damage/RNG production sources and numeric objects are unchanged; formal Wurst rules and existing target/active cooldown gates supply separate coverage.

The historical AuraPerf CLI requires every fixture's calls AND expressions to decrease; the added native read causes its empty-enemy strict reduction oracle to fail. Its correctness subgates pass separately, without weakening the oracle. Its old metadata-only runtime also lacks the initialized catalog table. Resource audit's historical --baseline mode requires exactly126 icons to disappear, so it is not applicable to this no-member-delta hotfix; retirement audit and direct retained-byte comparisons pass.

Initial full reviewed Python source selection: 217 tests run,201 passed,12 failures and9 errors (36 not covered). Two assertions became obsolete specifically because of these approved guards, were strengthened to current exact native/binding/unlock contracts, and pass2/2 on targeted rerun. Remaining10 failures+9 errors were precisely reproduced on formal baseline:14 selectors produce10 failures+8 errors, and unchanged inheritance fixture adds1 setup error. No blanket Python-green claim. Historical equipment replay CLI references eliminated pure helper/current-old shield functions and does not pass either map; it is not counted as acceptance evidence.
