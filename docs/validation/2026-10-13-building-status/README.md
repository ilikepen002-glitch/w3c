# Native building Buff status display

## Diagnosis and scope

The reported selected tower is `uH6A` (审判圣骑士). Formal baseline
`bc96b4910a8ecd8ea428ba4a1de98937cf9bb0ec` has map SHA-256
`5d6701cf84d4910fdcae6c2eaf299ae76e640577640e416564ba8ab38fac69d5`.
Its W3U has `ubdg=1`. The MPQ-root `war3mapMisc.txt` contains only the three
1200 inventory ranges and does not enable native building status display.

The purple 统御号角 contributes identity 3/rank 4: W3A `AM0d` inherits
`Aasl`, targets `self`, applies `BM08`, and has zero native movement factor.
W3H `BM08` inherits `Basl`; its `fart`, `ftip`, and `fube` are present,
including `BTNCommand.blp`, 12% and range 550. The independent numeric path is
`tdAuraOfferSource -> record.effective -> tdRefreshTowerEquipmentBonuses`:
base attack times the effective aura power is projected through the existing
attack-bonus ability. White tiger/commander instead use native AEar/AIcd
percentage carriers. Enemy slow uses the same display mechanism on non-building
enemies, with movement set separately by `tdRefreshEnemyMoveSpeed`.

A visible ground ring or the screenshot's total +383 attack does not isolate
this item's numeric effect. Carrier existence is also not proof that the engine
has projected its Buff. No native 1.27a gameplay was executed.

## Minimal fix

Add `[Misc] DisplayBuildingStatus=1` to the existing source import, preserving
all inventory constants. No unit classification, Buff generation, numeric
aggregation, timer or polling changes. The setting applies to native building
status panels map-wide, including other buildings with Buffs.

Original pre-Reforged sources (first-hand editor configuration/reproduction):
- Raw field name, 2010: https://www.hiveworkshop.com/threads/everyone-can-see-aura-icon.155556/
- Original custom constants import instructions and default value, 2009:
  https://www.hiveworkshop.com/threads/changing-gameplay-constants-for-roc-maps.149065/
- Building aura reproduction and native display setting, 2016:
  https://www.hiveworkshop.com/threads/problem-with-buildings-having-auras.285484/
- Follow-up user confirms the setting resolves missing building Buffs, 2020:
  https://www.hiveworkshop.com/threads/trying-to-get-an-ability-to-apply-buff-to-a-building.321452/

## Verification

The artifact gate now strictly parses the exact four-key `[Misc]` section,
rejecting missing/false/misspelled display settings, changed ranges, duplicate
keys, extra settings/sections and an ineffective imported-prefix copy. Source
and synthetic parser/archive tests pass; the old formal map fails the new gate
as expected because its display setting is absent. No Grill or map build was
run for this isolated change; integrate with the pending performance build,
then run `python3 tools/VerifyInventoryRangeArtifact.py <candidate-map>`.

Future explicit native 1.27a validation should select a tower with the purple
horn, confirm the 12% tooltip/status and attack delta, test a same-name stronger
source and its removal, test tower upgrades/sale, and independently confirm
non-building enemy slow Buff and speed enter/exit together. Do not infer FPS,
actual Buff projection or numeric correctness solely from these offline gates.

Additional runner check: `test_python_checks` runs 24 tests with three failure
assertions in two existing methods, identically reproduced on the unmodified
4378e7e baseline. Its legacy-reader fixture still names removed pet/UI test
methods (`test_actual_all_2176_skill_admission_combinations` and
`test_actual_farmer_grid_is_eleven_cells_with_empty_blink_slot`). This change
only classifies the new synthetic test class; it does not repair those unrelated
stale fixtures. Six directly affected source/parser/archive tests pass through
the project's `Run-PythonChecks.py` entry point.
