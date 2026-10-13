# Elemental active VFX, batch B

Approved minimal VFX plan, Sol implementation. Gameplay definitions and original-hit fence are unchanged. This batch depends on A's `TDPetCastContext` wrappers (`addMoving`, `moveMoving`, `clearMoving`, `addTimedLine`) and shared visual budget/recycler; it creates no timer or target selector.

## Actual stage wiring

| ID | Prepare / movement | Existing impact | Finish |
|---|---|---|---|
|19|No new windup|Same-step 650 gold line, blade endpoint and middle cut|Short cut Death tail|
|20|No new windup|Sword flash, two metal sparks and armor marker at target|Marker destruction + cut tail|
|21|No new windup|Four 120-unit cardinal starts with short traces at 0/.2/.4/.6|Fourth impact then cut tail|
|22|Original sword-array mesh on one Fx, height260→0 in each existing 1s round|One bolt and four small cuts per existing round|Last round + cut tail|
|23|No new windup|Instant roots, two opposite leaf sparks and bright sprout|Native roots Death + seed tail|
|24|Bright main seed/core|Main pulse each original tick; ≤3 green lines only to already-remembered weak seeds|Two original weak ticks then seed tail; dead primary uses retained point|
|25|Three captured-road flower effects|Only the first actual contact blooms each corresponding flower, no new scan|Flower destruction/seed tail|
|26|Leading original curved root mesh reused at three captured road points|Retained woody root silhouettes, green branch arc and leaf burst, 0/.4/.8|Root Death + seed tail|
|27|No new windup|Immediate ice star + narrow cold trace; original small cold marker remains|Marker destruction + ice tail|
|28|No new flight|Blue-white full-line out immediately, reversed endpoints at existing .6 return|Water/native Death + ice tail|
|29|Four mirror perimeter warnings + two reused ice-shard Fx converge during .6 warning|Existing .6 freeze; .95 clears Fx and makes five-point shatter ring|Native shatter Death + ice tail|
|30|One main vortex Fx, rotation/scale only|Existing periodic pulse: one shatter and two short rotating-quarter lines|Vortex destruction/collapse tail|
|31|One initial brand|Four existing ember pulses, one brand plus two low embers|Low ember extinguish tail|
|32|No new windup|One full fire lotus, four small brand petals, two short fire spokes|Low ember tail|
|33|Four warning corners and one high fireball Fx descending520→0 during existing .75|.75 clears Fx, one meteor+four low embers; three existing ground ticks|Low ember tail|
|34|Original ≤4 target marks|Each existing burst one flame+ash and short line to next already-marked saved point|Ash/ember tail|
|35|No new windup|Instant original faceted rock mesh + flat dust and two stone sparks|Rock Death/dust tail|
|36|No new windup|Three small original rock silhouettes at captured 90° fan positions and three immediate spokes|Rock Death/dust tail|
|37|One earth sigil and four low gold-brown diamond edges|Once-per-second breathing, no damage call|Sigil destruction/dust tail|
|38|Leading faceted ridge Fx reused across four original .2 road segments|Each captured point ridge+stone spark, last segment dust; separate from wood26|Final ridge Death + dust tail|

All motion uses at most two Fx per cast and A's eight-global/eight-new-per-second ceiling. Raw effects, lines and moving Fx share the same eight cast slots. Native decorations may be skipped when a visual allocation is rejected, without influencing the existing combat branch. `visualTick` never allocates Fx or raw effects per .05 tick; sigil creation is explicitly one-second edge gated. Mirror and meteor Fx end at their already-existing phase edge, with the shared one-second dummy recycle tail. No cancel adds a new flash.

## Original resources

Three MDX800 meshes and one shared 64², seven-mip BLP1 atlas: 157,068 raw bytes; the independently frozen four-file ZIP is 35,882 bytes. Exact imports and SHA256 are in `assets/source/elemental-vfx/production-manifest.json`. The archive size is not claimed as final MPQ compression; final build checks actual packed bytes and total map <8MiB. There are no external textures, particle emitters, gameplay units or abilities in these resources. Procedural source, editable JSON/atlas and provenance are retained; previews, sampled frame caches and node_modules are excluded.

Independent asset validation checked MDX800 roundtrip, 150 sequence/alpha samples, seven BLP mips, closed/outward geometry and original source-to-binary triangle corners. Original-generation rebuild reproduced the four frozen bytes. The authored shapes differ by geometry: upright white-gold swords, curved woody/leaved roots, chunky transverse stone slabs. DestroyEffect selecting the authored nonlooping 600ms Death animation still requires client verification.

## Verification status and boundary

Sol implemented B under the approved high-risk plan; Astra reviewed the source and packed-map evidence. Actual locked Linux checks, Wurst tests (including the seven new visual tests), and build passed. The final candidate is 7,532,104 bytes, below 8MiB, SHA256 `b8660ed83b6bf211a4c9be7e464e06ebbc7700398eb9358a8e71aebcd2ff64eb`. The real legacy-JASS gate checked 151 allocators; CD/startup/import-byte gates passed. The compiler and standard library locks were preserved. B adds four packed resources; gameplay object members remain identical to published A.

Passed offline checks:

- Actual Wurst gameplay normalization against official254c534: Direct/Periodic/dispatch mechanics unchanged; 49 cosmetic scalar cases, 17 wired stage helpers and four rejecting mutations.
- All20 packed elemental mechanisms plus 12 identity/trial/source/terminal negatives. The ten Hero mechanisms and their original identity/queue/native-hook cases also pass on this exact map.
- All20 VFX normal, native-creation rejection and actual128-handle saturation cases have identical damage/accepted-control/CD/target-life/score/gold/random traces to official254c534. Recorded native model, position, phase and clock calls establish same-frame instant traces, distinct cardinal cuts, existing-delay sword/meteor descent, selected seed/mark links, low-frequency sigil breathing and normal completion. Visual failure never authorizes damage.
- The B map, where moving classes are live, executes actual `TDVisualMoving`, locked `Fx`, `DummyRecycler` and recycle callbacks: two slots per cast, eight global, eight new per second, and 100 moves without effect/dummy rebuilding. The global-eight ceiling is separately tested after the rate bucket expires. Actual scheduled recycle delay is exactly one second: none returns at .99, first group returns at1.00, later group at its own1.99 deadline, restoring the 48-unit pool. In-memory packed mutations to delay0/.01 and global limit9 are rejected for those exact reasons. A's baseline DCE of moving classes is not used as proof of this gate.
- A's 4200 profession/quality/slot cases, appearance lifecycle and 15 original-attack combat traces pass on B through the native-only compatibility driver. It retains A's assertions and legal pet fixture; the complete original DamageEvent/damage/fence/trial gate also passes, including the 250/100 corpse-chain counterexample and same-handle/new-revision rejection.
- Shared expression evaluation now reads live globals after a preceding same-expression call, while locals still shadow them. Two focused tests and the existing 51 Boss verifier tests pass.

Reproducible artifact entries (baseline file extracted from the pinned Git commit):

```sh
mkdir -p _build
git show 254c53418697445451ebbca98a048d1bcdd19c56:ExampleMap.w3x > _build/vfx-baseline.w3x
python3 tools/VerifyElementalVfxSource.py
python3 tools/VerifyElementalVfxArtifact.py ExampleMap.w3x --baseline _build/vfx-baseline.w3x --output _build/elemental-vfx.json
python3 tools/VerifyElementalPetArtifact.py ExampleMap.w3x --report _build/elemental-mechanisms.json
python3 tools/VerifyPetHeroArtifact.py ExampleMap.w3x --output _build/hero-mechanisms.json
python3 tools/ReplayCombatVfxARegression.py attack ExampleMap.w3x
python3 tools/ReplayCombatVfxARegression.py visual ExampleMap.w3x
```

Nonblocking historical note: the optional legacy GroundUpgrade suite still asserts retired five-quality/old-synthesis rules. Its same eight failures and eleven errors among20 tests reproduce on published A; this batch does not alter ground production or claim every historical Python oracle passes.

These are offline packed-JASS executions with recorded native art/lightning handles, clock delivery, collections, flat terrain/world bounds and cosmetic dummy setters. Native Buff acceptance and native split/full-storm/corpse/shield notifications use controlled engine boundaries. Warcraft1.27 visual blending, authored Death selection, perceived size, simultaneous camera readability and FPS have not been tested in the client. No game session or deployment was performed.
