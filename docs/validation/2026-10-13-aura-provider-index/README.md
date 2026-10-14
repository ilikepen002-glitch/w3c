# Conservative aura provider index

Formal baseline: 20281071597a8a36f94cc45fec16855293b05ab4, tree eb8ffed2a61b7d1a99bd9b3c687140c66571adf5, map a20d063f1e6d7bd484213483d939d545c9bd6429b336243f95d5f7fe64abd8df.
Production freeze: b75a42f3896021c78a9d8d7111b131e47d401bca.
Final candidate: map 0204a84e260d8095f9d240adcb50a4bc9fb1d005d1e3db2b5938e1b1c12883b3, 5746461 bytes; JASS 2fbac85cd4315c98e0597256094b0d56455b1bf9e81f852f07c4bf9b95c7ed4a.
Initial 587ee20a candidate is retired. Working/native family predicate was rewritten as nested source conditions to avoid relying on mixed-operator lowering. This is equivalent source clarification, not evidence of a Warcraft engine bug.

## Scope and ownership

One false-initialized membership boolean on each existing TDAuraTarget and one global provider list. New tower records conservatively join, then the existing Inventory snapshot narrows membership. Candidates are working towers, the nine native aura tower forms, or any of the existing three captured aura equipment IDs, with exact DROP-handle exclusion. WorkStarted affects only already registered records. Detach and destructor remove membership idempotently before record reuse.

Only Runtime's source collection changed. Recipient/all-tower registries, tick period and quota, full readonly OfferSource, aggregate transaction, timed contributions, carrier/native repair, and every full Apply remain. No numerical cache, additional timer, lane/owner snapshot, target policy, damage/RNG/cooldown rule, VFX budget or imported numeric/media object change. Native provider forms stay candidates through ability remove/re-add. Arbitrary external scripts inventing native aura on non-provider forms without a project hook are not supported; legal item events and existing recipient refresh remain supported.

## Verification

Official final Linux checks/build PASS, serialized transactions `_build/linux-kqopi3e5` and `_build/linux-whz81cmg`, identical inputs and locked toolchain. Full Wurst tests including two new provider predicates passed. Exact MPQ active cooldown (including nonzero deadline), startup, script and imports gates passed.

Independent REPORT.json binds scripts, actual maps/JASS and stage bytes. 87 actual W3U/normal/evolved/equipment-three-slot cases and 20 transition states match baseline. These cover all 35 tower forms, ten evolved object-ability sets and all 14 actual aura catalog items in all three slots, with a real uO6A native-active cooldown receiver and nonzero cooldown assertions. Not every aura-kind/quality combination exists in the production catalog, so none was fabricated. Native source removal/re-add, receiver carrier repair/failed-add/retry, mechanical and cross-owner targets, weak fallback and last-source removal match.

Supplementary actual tests: empty-source timed expiry and trial contribution still Apply; exact recycled class ID has no inherited membership; equal-rank/power reordering preserves values; 41 synthetic sources retain the final strongest source and clean up to empty.

Entry11: actual pickup0→1, occupied-slot DROP1→0, duplicate rejection, scripted native add/transfer using production PICKUP/DROP, failed native add with no success event, upgrade start/finish, lawful cancel narrowing, stale cancel generation rejected, registration-before-gear-failure recovery. Unused tdTryGiveEquipmentItem is DCE on both maps and was not claimed as executed; its unchanged source and formal Wurst checks are separate evidence. Native event delivery, item ownership/storage, terrain and clock are controlled boundaries.

Nine exact semantic mutations are rejected by the intended assertions: missing native candidate, working safeguard, wrong excluded handle, missing third equipment slot, detach cleanup, empty-source Apply, live owner check, equal-rank carrier repair and premature aggregate publication. Partial-publication negative builds the initial valid state using original JASS, replaces only the packed scan callback and simulates a source interruption inside ForForce; unrelated interpreter exceptions are not counted.

Fresh target/split/no-ETA, wild180 and occupied-binding gates passed on0204. Root Misc is byte-identical (building Buff enabled and three1200 item ranges); 411 members,390 protected media payloads and eight numeric-object/terrain/placement payloads match baseline.

## Measured complete16-target cost

All measurements execute the actual callback including Inventory/provider maintenance, using the real packed tower catalog rather than historical level/branch stubs.

- Native sources0: visits640→0; calls20100→10196; interpreted expressions79638→60806
- Native sources4: visits640→64; calls20290→12426; expressions80856→66208
- Native sources10: visits640→160; calls20470→15666; expressions82038→73666
- Native sources40: visits640→640; calls20692→20868(+0.85%); expressions83478→83686(+0.25%)
- Four equipment sources: calls21496→13680; expressions84070→69506
- Worst40 equipment sources, third slot aura and two preceding non-aura slots: calls25684→26052(+1.43%); expressions97366→97910(+0.56%)

The full equipment/gear path remains. These are controlled interpreter counts, not Warcraft opcodes or measured FPS. No new timer/group/unit/order/RNG activity was introduced in these fixtures. All-source maintenance overhead remains below the approved5% count threshold.

## Limits and reproducibility

No Warcraft launch or in-client FPS/Buff-appearance claim. Historical Python/CLI failures disclosed by the baseline hotfix remain; they were not relabelled green or broadly rerun here. Source unchanged numeric behavior is covered by exact objects, actual projection mirror, full Wurst rules and inherited packed contracts rather than a new complete damage-engine simulator.

Probes are preserved byte-for-byte in probes/ and probe-bytes.json. They retain their original recorded execution-environment paths and controlled native adapters; REPORT hashes bind the exact original independent probes. They are evidence probes, not a new portable build entrypoint. All formal builds used Run-WurstLinux.py only.

A non-blocking attempt to add complete native sale/game-over/timer-owner simulation stopped at the old harness's unsupported PauseTimer boundary. This supplemental deep cleanup suite did not complete and is not counted as PASS. Actual death/live-reject, external Remove/Detach, recycled membership and41-source empty cleanup already provide relevant index ownership evidence. No production change was made to accommodate the harness.
