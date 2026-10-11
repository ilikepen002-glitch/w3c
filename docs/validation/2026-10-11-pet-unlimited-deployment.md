# Unlimited spirit deployment — offline integrated validation

## Scope and predecessor

Based on published wild-pathing commit `71a0c42b054370d7136dd2f687a6b4e7da830f19`
(tree `bf75df2451f81116b5336d681f68e0c183c10e2e`). The frozen predecessor root
map has SHA256 `6f4859b0ee6e22ca373ebafa222f16c1d150ac64908fdcea04da31a771b8c7b7`.
The semantic icons, player-facing tooltip rewrite, native Aeth attachment and
other earlier changes remain inherited.

Delete only the total deployed-spirit cap. `tdPetCanDeploy` retains all three
legality guards byte-for-byte and changes its final cap expression to `return true`.
Remove `TD_PET_DEPLOY_LIMIT`; retain the collection capacity of 12. Pdep, Pc04
and the deployment failure notice now say `每座塔可上阵1只精灵`. The preceding
capture-tooltip rewrite stays unchanged and all 61 Pcap levels contain no old
three-spirit cap.

No change to deployment execution, recall, active cooldown, host lookup,
collection/release lifecycle, combat scheduling or tower population. The latter
still unlocks 4/6/8/10 towers. The public deployment function's existing internal
boundary accepting an otherwise-valid unregistered record is unchanged; UI
records still come from `tdPetAt`. No new ownership subsystem is introduced.

## Models and review gate

Risk tier: high, gameplay admission with generated ability descriptions.
GPT-6 Astra supplied the approved plan; GPT-6.1 Sol implemented and validated.
Independent GPT-6 Astra implementation review: PASS WITH NOTES, no blockers.
Non-blocking notes: validation executes the packaged gate with controlled stubs;
11-deployed coverage is synthetic, normal population remains at most 10; offline
checks do not prove native Warcraft behavior or increased-load performance.
No gate was waived.

## Real packaged admission proof

`VerifyPetDeploymentArtifact.py` executes the real `tdPetCanDeploy` extracted
from the frozen old MPQ and the new MPQ. It reuses the existing scalar helper;
only bounded array reads, string parameters/constants, short-circuit boolean
semantics and exact balanced Wurst debug-stack statements were added. Unknown
functions, arrays, assignments or stack forms fail closed.

Controlled stubs provide native unit properties, lane eligibility, busy-table
membership and collection count/host lookup over two concrete independent
12-slot fixtures. No deployment, recall, combat, timers or whole-engine model
is simulated.

- Old red: three records already have hosts and the real old gate refuses a
  fourth unbound record, while fewer than three and legal empty-tower rebind
  succeed. This is behavioral failure, not wording or parsing failure.
- New green: lanes 0 and 1 each admit new records with existing counts
  0/1/2/3/4/9/11, independent of the other lane's fixture count.
- Each lane rejects null/released pet, null/dead tower, stopped lane, foreign
  owner, non-tower, busy tower, occupied tower and same-host repeat.
- Legal empty-tower rebind succeeds at existing 3/4/9/11.
- The 11-deployed fixture is synthetic gate coverage only. It is not a promise
  of 12 simultaneous deployments in normal play; tower population tops out at 10.
- Source and packaged differential checks preserve deploy, recall, host lookup,
  12-slot lifecycle, cooldown and tower-population functions. Existing collection
  ownership/capacity, release/reward, cooldown and population tests are unchanged.
- Mutation coverage directly proves the original packaged gate accepts a fourth
  record, a restored three-record-cap mutation refuses it, and acceptance
  verification detects the restored dependency.

## Verification and evidence

Evidence is under `2026-10-11-pet-unlimited-deployment/` next to this report.

- Fixed external Linux entrypoint: install PASS; typecheck PASS; 310/310 Wurst
  tests PASS. All 164 dependency libraries use the locked fixed root. Original
  configuration and obsolete dependency-directory hashes/metadata were restored.
- Fixed build PASS. This is the documented Linux port of the repository's
  Windows entrypoints; no Windows bat execution or deployment is claimed.
- Full Python initial run: 224/225 passed. The new restoration negative test
  expected `existing=3` although the verifier correctly detects its count call
  earlier at existing=0. Only the test expectation was corrected, adding direct
  original-true / restored-false fourth-record assertions. The seven deployment
  tests pass on targeted retest. The requested full rerun passes 225/225;
  the initial red and final green logs are both retained.
- Deployment artifact proof PASS; Pdep/Pc04 one-per-tower hints and every Pcap
  level have no old three-spirit cap.
- Twelve existing relevant artifact verifiers PASS: pet UI, player tooltips,
  placement, upgrades, sale, tower/UI/ground, equipment, evolution, ground menu,
  actual-JASS ground upgrade, slow and bladestorm.
- Wild-only inherited contracts PASS: all 96 hpea wild spirits keep exactly
  native Aeth, Pcap61/Pmas1 capture masks remain valid. The prewild zero-runtime
  diff verifier is deliberately not misused on this later gameplay commit.
- Exact predecessor object differential: only Pdep/Pc04 extended descriptions
  at level 1 change, excluding generated wurs markers. All unit/item fields,
  semantic icon bindings and actual icon/model/terrain/pathing/import bytes
  remain unchanged against the frozen wild predecessor.
- `git diff --check` PASS.

Root `ExampleMap.w3x`: `深渊守望 20261012-0009-UTC+8`.
SHA256: `10a6eb992b4a9fb0edf2aa81db8700e5b78042462e5d5a130b71a2747907bb0f`.
See `artifact.json` for root-map Git blob, byte count and fixed dependency tree.
The date rollover reflects UTC+8; the verification session's UTC date is October 11.

## Limits and residual risks

No Warcraft III, World Editor, user-computer access or native playtest was run.
Offline tests do not establish live deployment/effects, rendering, native
engine lifecycle, multiplayer behavior or performance under more simultaneous
spirit combat. Existing higher-load combat scheduling is unchanged but no
real-machine performance guarantee is made. Actual unit-parent checks against
installed game MPQ data are not run; no game data was downloaded.

Non-blocking existing tool notices: PatchMapDisplayName.java uses a deprecated
API; existing Pillow tests report Image.getdata deprecation. Neither causes a
validation failure or changes game behavior.
