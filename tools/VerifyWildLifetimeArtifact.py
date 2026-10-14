#!/usr/bin/env python3
"""Replay the supplied map's wild deadline and wave gates with recorded natives.
Production state/settlement/Boss readiness and existing cleanup callbacks execute.
Native clock, handles, world enumeration, tags and collections are boundaries.
This is offline packed-JASS evidence, not Warcraft timing or rendering evidence.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyElementalVfxArtifact import VfxRuntime
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyPetUIArtifact import field_value, jass_function
from VerifyTowerPlacementArtifact import unit_objects


class WildRuntime(VfxRuntime):
    def __init__(self, script):
        self.tags = set()
        self.tags_destroyed = []
        self.spell_target = None
        self.credit_grants = []
        super().__init__(script)
        self.invoke('init_TDEnemyMechanicRuntime')
        self.invoke('tdSetupEnemyMechanics')

    def execute_call(self, name, args):
        if name == 'tdPetCreditWave':
            before = self.invoke('tdPetBallsForLane', args[0])
            value = super().execute_call(name, args)
            after = self.invoke('tdPetBallsForLane', args[0])
            self.credit_grants.append({'lane': args[0], 'wave': args[1], 'delta': after - before})
            return value
        return super().execute_call(name, args)

    def native(self, name, args):
        if name == 'GroupEnumUnitsOfPlayer':
            self.groups[args[0]] = [unit for unit, data in self.units.items() if data['owner'] == args[1]]
            return True, None
        if name == 'FirstOfGroup':
            return True, self.groups[args[0]][0] if self.groups[args[0]] else None
        if name == 'GroupRemoveUnit':
            self.groups[args[0]].remove(args[1])
            return True, None
        if name == 'DestroyGroup':
            del self.groups[args[0]]
            return True, None
        if name == 'SetUnitOwner' and self.units[args[0]]['type'] != self.globals.get('DummyRecycler_DUMMY_UNIT_ID'):
            self.units[args[0]]['owner'] = args[1]
            return True, None
        if name == 'CreateItem':
            handle = 950000 + len(self.items_created)
            self.items_created.append((handle, *args))
            self.inventory_items[handle] = args[0]
            return True, handle
        if name in ('SetItemUserData', 'SetItemVisible', 'SetItemInvulnerable'):
            require(args[0] in self.inventory_items, 'Unknown recorded native loot item')
            return True, None
        if name == 'GetKillingUnit':
            return True, 101
        if name == 'GetSpellTargetUnit':
            return True, self.spell_target
        if name == 'tdPetIsWild':
            return False, None
        if name == 'group_enumUnitsInRect':
            self.groups[args[0]] = list(self.visible_units)
            return True, None
        if name == 'ForGroup':
            for unit in list(self.groups[args[0]]):
                self.enum_unit = unit
                self.invoke(args[1])
            self.enum_unit = None
            return True, None
        if name == 'DestroyTextTag':
            require(args[0] in self.tags, 'Unknown or twice-destroyed wild marker')
            self.tags.remove(args[0])
            self.tags_destroyed.append(args[0])
            return True, None
        if name in ('SetTextTagText', 'SetTextTagPosUnit'):
            require(args[0] in self.tags, 'Wild countdown used an unowned marker')
            return True, None
        return super().native(name, args)

    def wild(self, lane=0, wave=7, appeared=0.0):
        self.now = appeared
        unit = self.call('CreateUnit', [15, self.invoke('tdPetWildUnitId', wave, 1), 0., 0., 0.])
        record = self.invoke('new_TDPetWildRecord', unit, lane, wave, 1)
        self.call('dispatch_LinkedList_LinkedList_add_1',
                  [self.globals['TDPetWild_tdPetWildRecords'], 'wild replay fixture', record])
        marker = 900000 + record
        self.tags.add(marker)
        self.globals['TDPetWildRecord_marker'][record] = marker
        self.units[unit]['userdata'] = lane * 10000 + wave * 100
        self.visible_units.append(unit)
        return record, unit, marker

    def cleanup(self):
        # Execute the actual setup and its actual existing .25 second callback.
        self.invoke('tdPetSetupWild')
        owner = self.callback_allocations['alloc_CallbackPeriodic_doPeriodically_TDPetWild'][1]
        callbacks = [cb for delay, cb in self.periodics if delay == .25 and
                     self.globals['CallbackPeriodic_typeId'][cb] == owner]
        require(len(callbacks) == 1, 'Wild lifecycle added or omitted its single existing timer')
        cb = callbacks[0]
        self.invoke('call_doPeriodically_TDPetWild', cb, cb)


def verify_wild(script):
    reports = []
    for appeared in (0.0, 10.0):
        r = WildRuntime(script)
        record, unit, marker = r.wild(appeared=appeared)
        deadline = r.globals['TDPetWildState_deadline'][record]
        require(deadline == appeared + 180., 'Wild lifetime is not appearedAt + 180')
        for offset, expected in ((179.999, True), (180., False), (180.001, False)):
            r.now = appeared + offset
            require(r.invoke('tdPetWildCanCapture', record, 0) is expected, 'Wrong strict deadline boundary')
            require(not r.invoke('tdPetWildCanCapture', record, 1), 'Wild capture crossed lanes')
        r.now = deadline
        require(not r.invoke('tdPetWildTransition', record, 1), 'Capture won at exact expiry')
        require(r.globals['TDPetWildState_state'][record] == 2, 'Exact-expiry capture failed to settle expired')
        require(not r.invoke('tdPetWildTransition', record, 2), 'Expired terminal settled twice')
        require(marker not in r.tags and r.tags_destroyed == [marker], 'Expiry marker ownership lost')
        r.cleanup()
        require(r.removals.count(unit) == 1, 'Natural expiry omitted or duplicated native removal')
        require(record not in r.lists[r.globals['TDPetWild_tdPetWildRecords']], 'Expired record remains owned')
        reports.append({'appeared': appeared, 'deadline': deadline, 'strict_boundaries': True})
    r = WildRuntime(script)
    record, unit, marker = r.wild()
    r.now = 179.999
    require(r.invoke('tdPetWildTransition', record, 1), 'Pre-deadline capture failed')
    require(not r.invoke('tdPetWildTransition', record, 2), 'Expiry overrode captured state')
    require(not r.invoke('tdPetWildTransition', record, 1), 'Capture settled twice')
    r.cleanup()
    require(r.removals.count(unit) == 1 and r.tags_destroyed == [marker], 'Captured cleanup ownership lost')
    for condition in ('dead', 'left', 'defeated', 'inactive', 'gameover'):
        r = WildRuntime(script)
        record, unit, marker = r.wild()
        if condition == 'dead': r.units[unit]['alive'] = False
        elif condition == 'left': r.invoke('tdPetMarkPlayerLeft', 0)
        elif condition == 'defeated': r.invoke('tdSetLaneDefeated', 0, True)
        elif condition == 'inactive': r.invoke('tdSetLaneActive', 0, False)
        else: r.invoke('tdSetGameOver', True)
        r.cleanup()
        require(r.removals.count(unit) == 1 and marker not in r.tags, 'Wild cleanup failed: ' + condition)
    return {'deadline_cases': reports, 'capture_first_and_expiry_first': True,
            'native_dead_leave_defeat_inactive_gameover': True}


def verify_waves(script):
    r = WildRuntime(script)
    records = [r.wild(lane=lane) for lane in range(4)]
    r.now = 10.
    for lane in range(4): r.invoke('tdSetResolvedWave', lane, 7)
    require(all(r.invoke('tdPetWildCanCapture', record, lane) for lane, (record, _, _) in enumerate(records)),
            'Missing real live wild window fixture')
    require(r.invoke('tdBossPreparationReady', 8), 'Live wild still blocks Boss 8 readiness')
    # Pending production and unresolved old wave independently still block.
    pending = r.invoke('tdFlowBeginSpawn', 2)
    require(not r.invoke('tdBossPreparationReady', 8), 'Pending old spawn gate was removed')
    r.invoke('tdFlowEndSpawn', 2, pending)
    r.invoke('tdSetResolvedWave', 1, 6)
    require(not r.invoke('tdBossPreparationReady', 8), 'Unresolved old wave gate was removed')
    r.invoke('tdSetResolvedWave', 1, 7)
    enemy = 102
    r.units[enemy].update(alive=True, type=r.invoke('tdWaveUnitId', 7), owner=4, userdata=20700)
    r.tables[r.globals['TDSpawn_tdEnemyMatchEpochs']][enemy] = r.invoke('tdFlowEpoch')
    r.visible_units.append(enemy)
    require(not r.invoke('tdBossPreparationReady', 8), 'Living old enemy gate was removed')
    r.units[enemy]['alive'] = False
    require(r.invoke('tdBossPreparationReady', 8), 'Readiness failed after old enemy cleanup')
    r.invoke('tdSetGlobalWave', 7)
    r.invoke('tdStartGlobalWave', 8)
    require(r.invoke('tdFlowIsPreparing'), 'Actual StartGlobalWave did not enter preparation')
    method = next(name for name in r.functions if name.startswith('call_doPeriodically_TDGame') and
                  'tdBossPreparationReady(' in jass_function(script, name).group(1))
    allocator = method.replace('call_', 'alloc_CallbackPeriodic_', 1)
    owner = r.callback_allocations[allocator][1]
    callback = next(cb for delay, cb in r.periodics if delay == .20 and r.globals['CallbackPeriodic_typeId'][cb] == owner)
    r.invoke(method, callback, callback)
    require(r.invoke('tdFlowIsBossActive') and r.invoke('tdGetGlobalWave') == 8,
            'Actual preparation callback did not start Boss ACTIVE')
    for record, unit, marker in records:
        require(r.globals['TDPetWildState_deadline'][record] == 180. and r.units[unit]['alive'] and marker in r.tags,
                'Boss phase removed/restarted old wild')
        require(r.units[unit]['type'] == r.invoke('tdPetWildUnitId', 7, 1), 'Cross-wave wild type/origin changed')
    # The actual preexisting milestone grant remains usable within absolute life.
    before = r.invoke('tdPetBallsForLane', 0)
    boss = r.globals['TDGame_tdBossUnits'][0]
    require(boss is not None and r.units[boss]['alive'], 'Actual Boss creation fixture missing')
    r.units[boss]['alive'] = False
    r.event_target = boss
    r.invoke('tdHandleEnemyDeath')
    require(r.invoke('tdFlowBossResult', 0, 8) == 2 and r.invoke('tdGetResolvedWave', 0) == 8,
            'Actual Boss death did not settle and resolve wave')
    require({'lane': 0, 'wave': 8, 'delta': 6} in r.credit_grants, 'Actual Boss milestone contribution is not exactly +6')
    r.now = 100.
    require(r.invoke('tdPetWildCanCapture', records[0][0], 0), 'Old wave wild unavailable before absolute expiry')
    farmer = r.call('CreateUnit', [0, r.globals['TDConfig_TD_FARMER_UNIT_ID'], 0., 0., 0.])
    r.event_target = farmer
    r.spell_target = records[0][1]
    r.random_values = [1] * 16
    balls = r.invoke('tdPetBallsForLane', 0)
    count = r.invoke('tdPetCollectionCount', 0)
    r.invoke('tdPetHandleCapture')
    require(r.invoke('tdPetCollectionCount', 0) == count + 1 and r.invoke('tdPetBallsForLane', 0) == balls - 1,
            'Actual capture did not use Boss-granted ball on old wild')
    require(r.globals['TDPetWildState_state'][records[0][0]] == 1 and
            r.removals.count(records[0][1]) == 1 and records[0][2] not in r.tags,
            'Actual cross-Boss capture did not settle/remove marker and unit')
    require(r.invoke('tdWaveClearDelay', 7) == 20. and r.invoke('tdWaveForceStartDelay', 7) == 60.,
            'Normal wave timings changed')
    require('tdPetWild' not in jass_function(script, 'tdTryScheduleNextWave').group(1), 'Wild gates normal advance')
    require('tdFlowTransitionIsHeld' in jass_function(script, 'tdResumeBossTransition').group(1), 'Trial token gate missing')
    return {'four_live_wild_boss_ready': True, 'old_enemy_pending_resolved_guards': True,
            'absolute_deadline_across_boss': True, 'boss_six_balls_usable': True,
            'normal_delays': [20, 60], 'trial_token_preserved': True}


def verify_text(data, script):
    archive = Mpq(data)
    abilities = ability_objects(archive.extract('war3map.w3a'))
    for level in range(1, 62):
        text = field_value(abilities['Pcap'][1], 'aub1', level)
        require('出现180秒后消失' in text and '成功率65%' in text, 'Capture tooltip lifetime/chance mismatch')
    units = unit_objects(archive.extract('war3map.w3u'))
    descriptions = [fields.get('ides', '') for identity, fields in units.items() if identity.startswith('p')]
    require(any('停留180秒' in value for value in descriptions if isinstance(value, str)), 'Wild object lifetime missing')
    require('野生精灵 180s' in script and '保护180秒' in script and '等待精灵捕获结束' not in script,
            'Packaged wild/Boss lifetime hints stale')
    return {'capture_tooltip_levels': 61, 'wild_and_boss_hints': True}


def verify_mutations(script):
    cases = []
    def mutate(name, transform):
        m = jass_function(script, name)
        body = transform(m.group(1))
        require(body != m.group(1), 'Missing packed mutation root: ' + name)
        return script[:m.start(1)] + body + script[m.end(1):]
    mutations = (
        ('lifetime_60', 'Wild lifetime is not appearedAt + 180', mutate('init_TDPetWildState', lambda b: re.sub(r'(set TDPetWildState_TD_PET_WILD_LIFETIME = )180(?:\.0?)?', r'\g<1>60.0', b, count=1)), verify_wild),
        ('inclusive_deadline', 'Wrong strict deadline boundary', mutate('TDPetWildState_canCapture', lambda b: b.replace('now < ', 'now <= ', 1)), verify_wild),
        ('boss_unconditionally_blocked', 'Live wild still blocks Boss 8 readiness', mutate('tdBossPreparationReady', lambda b: b.replace('not tdContinuingLanesEmpty()', 'true', 1)), verify_waves),
        ('boss_ignores_old_enemies', 'Pending old spawn gate was removed', mutate('tdBossPreparationReady', lambda b: b.replace('not tdContinuingLanesEmpty()', 'false', 1)), verify_waves),
        ('boss_ignores_resolved', 'Unresolved old wave gate was removed', mutate('tdBossPreparationReady', lambda b: re.sub(r'tdGetResolvedWave\([^)]*\) < [^\n]+ - 1', 'false', b, count=1)), verify_waves),
        ('boss_ignores_pending', 'Pending old spawn gate was removed', mutate('tdContinuingLanesEmpty', lambda b: re.sub(r'tdFlowLaneHasPendingSpawn\([^)]*\)', 'false', b, count=1)), verify_waves),
    )
    for label, expected_reason, changed, verify in mutations:
        try: verify(changed)
        except ValueError as error:
            require(str(error) == expected_reason, 'Mutation hit unrelated verifier error: ' + label + ': ' + str(error))
            cases.append({'mutation': label, 'exception_type': type(error).__name__, 'reason': str(error)})
        else: raise ValueError('Wild mutation survived actual execution: ' + label)
    return cases


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    data = args.map.read_bytes()
    script = Mpq(data).extract('war3map.j').decode('utf-8')
    report = {'wild': verify_wild(script), 'waves': verify_waves(script), 'text': verify_text(data, script),
              'mutations': verify_mutations(script),
              'status': 'PASS', 'map_sha256': hashlib.sha256(data).hexdigest(),
              'jass_sha256': hashlib.sha256(script.encode()).hexdigest(),
              'boundary': 'Recorded native clock/handles/enumeration/tags; real packed owners and gates execute; no Warcraft observation.'}
    if args.output: args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
