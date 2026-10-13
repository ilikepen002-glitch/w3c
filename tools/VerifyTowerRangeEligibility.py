#!/usr/bin/env python3
"""Read-only source matrix and optional actual-map ranged-equipment replay.
Native inventory/type/ability storage is modeled; no live Warcraft claims.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
from ReadEquipmentCatalog import catalog
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
from VerifyEquipmentAbilityArtifact import require
from VerifyPetManagerSource import function_body
from GenerateTowerTerrainMask import Mpq

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'bfd59de'
PATH = 'wurst/items/TDInventoryRuntime.wurst'


def roster(evaluator):
    rows = []
    for choice in range(1, evaluator.constant('TD_TOWER_CHOICE_COUNT') + 1):
        maximum = evaluator.call('tdTowerMaxLevel', [choice])
        for level in range(1, maximum + 1):
            branches = evaluator.call('tdTowerUltimateBranchCount', [choice]) if level == maximum else 1
            for branch in range(1, branches + 1):
                rows.append((choice, level, branch, evaluator.call('tdTowerUnitIdForLevelBranch', [choice, level, branch])))
    require(len(rows) == 35 and len({row[3] for row in rows}) == 35, 'Tower roster changed')
    return rows


def gear_ids():
    entries = sorted((x for x in catalog() if x.line == 1), key=lambda x: x.quality)
    require([x.primary for x in entries] == ['RANGE'] * 4 and [x.primary_value for x in entries] == [90, 150, 230, 340], 'Range gear changed')
    return [int.from_bytes(x.rawcode.encode(), 'big') for x in entries]


def source_check():
    ids = gear_ids()
    # Only the stateful catalog lookup is a controlled source boundary; the
    # range-family selection and all 35 tower bases execute their actual source.
    values = dict(zip(ids, (90., 150., 230., 340.)))
    class Rules(SourceScalarEvaluator):
        def expression(self, expression, scope):
            # Wurst's int-to-real widening is exact for these small tower ranges.
            return super().expression(expression.replace('.toReal()', ''), scope)
        def call(self, name, args, fields=None):
            if name == 'tdEquipmentRangeBonusForItems':
                return min(500., sum(values.get(x, 0.) for x in set(args)))
            return super().call(name, args, fields)
    evaluator = Rules(read_sources())
    ranged = {evaluator.constant('TD_TOWER_CHOICE_ARCHER'), evaluator.constant('TD_TOWER_CHOICE_DRYAD')}
    cases = [((0, 0, 0), 0.), *((((x, 0, 0), bonus)) for x, bonus in values.items()), ((ids[0], ids[1], ids[3]), 500.), ((0, 0, 0), 0.)]
    for choice, level, branch, _ in roster(evaluator):
        base = evaluator.call('tdTowerBaseRangeForBranch', [choice, level, branch])
        for items, bonus in cases:
            actual = evaluator.call('tdTowerEffectiveRangeForLoadout', [choice, level, branch, *items])
            require(actual == base + (bonus if choice in ranged else 0.), 'Source family/range matrix failed')
    text = (ROOT / PATH).read_text()
    before = subprocess.check_output(['git', 'show', BASELINE + ':' + PATH], cwd=ROOT).decode()
    current_body = function_body(text, 'tdTowerEffectiveRangeForLoadout')[1]
    old_body = function_body(before, 'tdTowerEffectiveRangeForLoadout')[1]
    current_body = '\n'.join('\t' + line for line in current_body.splitlines())
    old_body = '\n'.join('\t' + line for line in old_body.splitlines())
    require(text.replace(current_body, old_body, 1) == before, 'Range change modified another inventory rule')
    require('tdTowerEffectiveRangeForLoadout(towerChoice, level, branch, item1, item2, item3)' in text, 'Tower query bypasses central rule')
    require('SetUnitAcquireRange(tower, tdTowerEffectiveRangeForLoadout(' in text, 'Acquire range bypasses central rule')
    runtime = (ROOT / 'wurst/towers/TDTowerRuntime.wurst').read_text()
    require('let diameter = tdTowerEffectiveRangeForTower(tower) * 2.0' in runtime and 'let searchRange = tdTowerEffectiveRangeForTower(source)' in runtime, 'Indicator/targeting bypasses central rule')
    require(runtime.count('tdRefreshTowerEquipmentBonuses(tower)') >= 3, 'Construct/upgrade paths lost equipment refresh')
    require('tdRefreshTowerEquipmentBonuses(tower)' in (ROOT / 'wurst/towers/TDTowerEvolutionRuntime.wurst').read_text(), 'Evolution path lost equipment refresh')
    require('tdRefreshTowerEquipmentBonuses(tower)' in (ROOT / 'wurst/pets/TDPetCombat.wurst').read_text(), 'Spirit refresh path lost equipment refresh')
    print('PASS RANGE SOURCE: all 35 tower identities × 7 loadouts; ARCHER/DRYAD only; other inventory code byte-identical')
    return evaluator


def replay(script, evaluator):
    from VerifyPetFourSlotArtifact import FourSlotRuntime
    r = FourSlotRuntime(script)
    ids = gear_ids()
    ranged = {evaluator.constant('TD_TOWER_CHOICE_ARCHER'), evaluator.constant('TD_TOWER_CHOICE_DRYAD')}
    methods = [name for name, (params, _) in r.functions.items() if name.startswith('tdRefreshTowerEquipmentBonuses') and len([x for x in params if x != 'w__wurst_stackPos']) == 1]
    require(len(methods) == 1, 'Cannot uniquely resolve public equipment refresh')
    refresh = methods[0]
    attack_ability = evaluator.constant('TD_TOWER_EQUIPMENT_ATTACK_BONUS_ABILITY_ID')
    speed_ability = evaluator.constant('TD_TOWER_EQUIPMENT_ATTACK_SPEED_BONUS_ABILITY_ID')
    cases = [((0, 0, 0), 0.), *((((x, 0, 0), bonus)) for x, bonus in zip(ids, (90., 150., 230., 340.))), ((ids[0], ids[1], ids[3]), 500.), ((0, 0, 0), 0.)]
    for choice, level, branch, unit_id in roster(evaluator):
        r.units[101]['type'] = unit_id
        base = r.invoke('tdTowerBaseRangeForBranch', choice, level, branch)
        for items, bonus in cases:
            r.executed_steps = 0
            r.units[101]['inventory'] = {slot: 2000 + slot for slot, code in enumerate(items) if code}
            for slot, code in enumerate(items):
                r.inventory_items[2000 + slot] = code
            expected = base + (bonus if choice in ranged else 0.)
            require(r.invoke('tdTowerEffectiveRangeForLoadout', choice, level, branch, *items) == expected, 'Packed loadout range mismatch')
            require(r.invoke('tdTowerEffectiveRangeForTower', 101) == expected, 'Packed inventory range mismatch')
            r.invoke(refresh, 101)
            require(r.units[101]['acquireRange'] == expected, 'Acquire range missed equip/remove/changed tower identity')
            # Test-only convenience wrappers are dead-code-eliminated; execute the production mapping.
            expected_attack = r.invoke('tdTowerAttackBonusAbilityLevel', r.invoke('tdEquipmentAttackBonusForItems', *items))
            expected_speed = min(evaluator.constant('TD_TOWER_EQUIPMENT_ATTACK_SPEED_MAX_LEVEL'), max(0, int(r.invoke('tdEquipmentAttackSpeedBonusForItems', *items) * 100. + .5)))
            require(r.units[101]['abilities'].get(attack_ability, 0) == expected_attack and r.units[101]['abilities'].get(speed_ability, 0) == expected_speed, 'Range filtering removed another item attribute')
    require(r.invoke('tdEquipmentAttackBonusForItems', ids[1], 0, 0) == 40. and r.invoke('tdEquipmentAttackBonusForItems', ids[2], 0, 0) == 80., 'Scope secondary attack changed')
    require(r.invoke('tdEquipmentAttackSpeedBonusForItems', ids[3], 0, 0) == .24, 'Scope secondary speed changed')
    print('PASS RANGE REPLAY: 245 real loadout/inventory/refresh cases, acquisition + other item attributes; identity changes recompute from current family')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', nargs='?', type=Path)
    a = p.parse_args()
    evaluator = source_check()
    if a.map:
        replay(Mpq(a.map.read_bytes()).extract('war3map.j').decode(), evaluator)
        print('MAP SHA256:', hashlib.sha256(a.map.read_bytes()).hexdigest())
    else:
        print('NOT RUN: Wurst checks/build, packed replay, native range indicator or attack behavior')


if __name__ == '__main__':
    main()
