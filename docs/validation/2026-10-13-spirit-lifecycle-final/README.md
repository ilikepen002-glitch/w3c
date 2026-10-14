# Wild 180 seconds, occupied rebinding and cancelled route interception

Final artifact: `ExampleMap.w3x`, 5,745,005 bytes, SHA256
`5d6701cf84d4910fdcae6c2eaf299ae76e640577640e416564ba8ab38fac69d5`.
Packed JASS SHA256:
`bc37aeeac4e76bb9ef0d7d32fc30c382d459d8f579ea1fe9b9ff568db907b000`.
Display stamp: `契灵守卫战 20261014-0043-UTC+8`.

## Implemented behavior

- Wild spirits retain their original absolute `appearedAt + 180` deadline across
  waves. Live wild spirits no longer block Boss preparation. Old enemies,
  pending spawns, unresolved waves and trial gates remain; normal 20/60 second
  advance delays remain. Capture success is still 65%, with unchanged skill
  count probabilities 55/35/10.
- Explicit deployment may replace an occupied tower: A moves to the target,
  B stays in its original collection slot unbound, and A's old tower is empty.
  Both cooldown deadlines survive. Full collections are supported; a same-pet,
  same-tower request is a strict no-op. Bounded ownership/identity census,
  pre-created visual and post-native revalidation precede both real recalls.
  The Combat facade immediately refreshes old/new tower bonuses.
- User-cancelled 3-second route interception is removed. Current automatic
  target priorities are the reviewed HP/Boss strategy, with manual/pending
  precedence and the existing 720/780 melee ranges preserved. The older ETA
  validation document is explicitly historical.
- The precise 21 P0 map decorative critters become neutral-passive once at
  startup. Native pickup/drop/give constants are root-imported at 1200; they
  do not change inventory eligibility, ownership, slots or event handlers.

## Required review and formal validation

Wild and binding were treated as high-risk: GPT-6 Astra read-only PLAN PASS,
GPT-6.1 Sol implementation, independent Astra SOURCE PASS and final actual
artifact PASS. The narrow guard extraction was separately SOURCE PASS: it
avoids a strict offline parser's mixed AND/OR grammar, not a discovered old
Warcraft/JASS semantic error. Astra also independently approved the final
cancelled-ETA artifact. No required phase was waived.

Formal full checks and build PASS via `Run-WurstLinux.py`, serialized:
`checks-manifest.json` / `formal-checks.log` and `build-manifest.json` /
`formal-build.log`. Build parent is `6483629`; subsequent commits changed only
validation tools/documents. `freeze.json` verifies all 141 current production
Wurst files against the build input hashes and records exact final verifier
hashes. The build verified all 392 imports, source-template native script,
startup, object/resource bounds and native active-cooldown artifacts.

## Actual packed-JASS evidence

- `wild-actual.json`: strict 179.999/180/180.001 boundaries, capture/expiry race,
  native death/leave/defeat/inactive/game-over cleanup, four live wild records,
  real wave-8 preparation callback, Boss ACTIVE, real Boss death settlement,
  exact real-wave-credit +6 contribution and capture of the retained wild
  record. Also old enemy/pending/resolved/trial guards, normal delays, 61
  capture tooltip levels and 6 exact semantic mutations.
- `rebinding-actual.json`: real transaction/recall/refresh, 8 deployment cases,
  strict no-op, 13 preflight failures and 11 post-native adversaries, old busy
  source migration, original slots/readyAt preservation, buffs and pending
  cleanup, queued/running/on-stack cast fences and other-source completion.
  Six exact semantic mutations reject missing rollback/ownership/census/
  B-recall/cooldown/refresh behavior; unknown interpreter errors cannot pass.
- `../2026-10-13-remove-route-interception-result.json`: no ETA symbols or
  speed/exit-rectangle reads; near-exit targets do not override HP/Boss.
  Original attack/manual/pending/recovery, 9 exact packed mutations and eight
  baseline trajectories with 65 native hits remain equivalent.

These tools execute the actual packed owners and transactions with recorded
native engine boundaries. They do not claim observed Warcraft gameplay,
visual smoothness, performance, or native pickup/drop/give interaction.

## QoL and resource closure

`inventory-range-actual.json`: exact 72-byte root `war3mapMisc.txt`, no prefixed
copy. `qol-source-tests.log`: five focused source replays PASS, including the
exact four-species/21-unit whitelist, all owners, once-only startup/group
cleanup, unchanged inventory abilities and root import bytes.

`media-preservation.json`: compared to final icon baseline map SHA256
`e770a0151f846c8fc6cf9bc7bdb456ea1207eb230e8d946431e63108e481980e`,
all 390 media/model/interface payloads are byte-identical; the only added MPQ
member is root `war3mapMisc.txt`. The four ignored Leoric members independently
match the source hash lock. `icon-preservation.json` preserves 43 skills,
40 equipment records, 175 display bindings and all 60 new BTN/DIS resources.
`resource-reachability.json` confirms all 126 retired icons and their retired
preview objects remain absent; unresolved resources are retained.
