#!/usr/bin/env python3
"""Compare actual baseline/candidate packed local hotpaths, with counted groups.

Engine units, enumeration sets, timers, ability state and LinkedLists are modeled;
production selectors, split constructors/impact callbacks and group-copy helpers
execute from each map. Counts are neither WC3 opcodes nor elapsed CPU/FPS.
"""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import re

from GenerateTowerTerrainMask import Mpq
from VerifyGlobalRankingsArtifact import members, normalize_info
from VerifyTowerTargetPriorityArtifact import TowerTargetRuntime, register_actual_split_listener
from VerifyTowerUpgradeArtifact import rawcode
from VerifyEquipmentAbilityArtifact import require
from VerifyDamageRankingJass import functions


class CountedRuntime(TowerTargetRuntime):
    def __init__(self, script):
        self.expressions = 0
        self.native_counts = Counter()
        self.hash_values = {}
        self.spell_ability = 0
        super().__init__(script)
        # This fixture measures split selection, independently of the default
        # non-archer scripted-priority transaction fixture in the base class.
        self.units[101]['type'] = rawcode('uA6B')

    def expression(self, text, scope):
        self.expressions += 1
        if 'try(' in text:
            self.functions['jass_try'] = self.functions['try']
            text = re.sub(r'\btry\(', 'jass_try(', text)
        return super().expression(text, scope)

    def native(self, name, args):
        self.native_counts[name] += 1
        if name == 'GetSpellAbilityId': return True, self.spell_ability
        if name == 'InitHashtable': return True, 90002
        if name == 'LoadInteger': return True, self.hash_values.get(tuple(args[:3]), 0)
        if name == 'SaveInteger': self.hash_values[tuple(args[:3])] = args[3]; return True, True
        if name == 'FlushChildHashtable':
            self.hash_values = {key: value for key, value in self.hash_values.items() if key[:2] != tuple(args[:2])}
            return True, None
        # Execute the real packed iterator, copying and destruction helpers.
        if name in ('group_iterator', 'group_next', 'group_hasNext', 'group_close', 'group_destr', 'group_clear'):
            return False, None
        if name == 'DestroyGroup':
            require(args[0] in self.live_groups, 'Group leaked/double destroyed')
            self.live_groups.remove(args[0]); return True, None
        if name == 'IsUnitInGroup': return True, args[0] in self.groups[args[1]]
        if name == 'GroupAddUnit':
            if args[1] not in self.groups[args[0]]: self.groups[args[0]].append(args[1])
            return True, True
        if name == 'FirstOfGroup': return True, self.groups[args[0]][0] if self.groups[args[0]] else None
        if name == 'GroupRemoveUnit':
            if args[1] in self.groups[args[0]]: self.groups[args[0]].remove(args[1])
            return True, None
        if name == 'GroupClear': self.groups[args[0]].clear(); return True, None
        if name == 'ForGroup':
            previous = getattr(self, 'enum_unit', None)
            for unit in self.groups[args[0]][:]:
                self.enum_unit = unit; self.invoke(args[1])
            self.enum_unit = previous
            return True, None
        if name == 'CreateForce': return True, 90001
        if name == 'ForceAddPlayer': return True, None
        if name == 'ForForce': self.invoke(args[1]); return True, None
        if name == 'DisplayTimedTextToPlayer': return True, None
        return super().native(name, args)

    def reset_counts(self):
        self.expressions = 0; self.native_counts.clear(); self.calls.clear(); self.executed_steps = 0
        self.clear_trace()

    def costs(self):
        natives = ('CreateGroup', 'DestroyGroup', 'GroupAddUnit', 'GroupRemoveUnit', 'SquareRoot',
                   'UnitItemInSlot', 'unit_getAbilityLevel', 'unit_removeAbility', 'SetUnitAbilityLevel',
                   'GetUnitX', 'GetUnitY')
        return dict(expressions=self.expressions, queries=len(self.group_queries),
                    natives={n: self.native_counts[n] for n in natives},
                    definition_calls=self.calls['tdActiveSkillDefinitionAt'])


def shot_trace(r, volley):
    if not volley: return None
    prefix = 'TDArcherSplitArrowVolley_'
    shots = r.globals[prefix + 'extraShots'][volley]
    names = sorted(n for n in r.globals if n.startswith('TDArcherSplitArrowShot_') and
                   (n.endswith(('target', 'flightTime', 'targetRevision')) or '_context_' in n))
    return dict(primary=r.globals[prefix + 'primaryTarget'][volley],
                primaryFlightTime=r.globals[prefix + 'primaryFlightTime'][volley],
                shots=[{n: r.globals[n][shot] for n in names} for shot in r.lists[shots]],
                expiry=r.invoke('tdArcherSplitArrowVolleyExpireDelay', volley))


def attack_costs(script):
    results = []
    for count in (16, 52, 104, 308):
        r = CountedRuntime(script)
        for i in range(count): r.enemy(1000 + i, life=10. + i, x=400. + i)
        r.visible_units = list(range(1000, 1000 + count))
        groups = set(r.live_groups)
        r.reset_counts(); r.attack(1000)
        cost = r.costs()
        queue = r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']]
        require(len(queue) == 1 and r.accepted == [(101, 1000)], 'Attack acceptance/queue changed')
        require(r.live_groups == groups, 'Attack leaked a private group')
        results.append(dict(enemies=count, costs=cost, trace=shot_trace(r, queue[0])))
    return results


def selection_traces(script):
    traces = []
    for tower in ('uA6B', 'uD6B', 'uO6B', 'uH6B', 'uG6B'):
        r = CountedRuntime(script); r.units[101]['type'] = rawcode(tower)
        for handle in (1000, 1001, 1002, 1003): r.enemy(handle, life=25., x=400.)
        record = r.invoke('tdTargetPriorityGet', 101)
        range_ = r.invoke('tdTowerEffectiveRangeForTower', 101)
        groups = set(r.live_groups)
        for mode in ('no_current', 'equal_current', 'invalid_current', 'strict_better_tie'):
            current = None if mode == 'no_current' else 1003
            for handle in (1000, 1001, 1002, 1003):
                r.units[handle].update(life=25., visible=True, type=rawcode('uW01'))
            if mode == 'invalid_current': r.units[1003]['visible'] = False
            if mode == 'strict_better_tie':
                if tower[1] in 'AD': r.units[1000]['life'] = r.units[1001]['life'] = 10.
                else: r.units[1000]['type'] = r.units[1001]['type'] = rawcode('uB08')
            expected = 1003 if mode == 'equal_current' else 1000
            for order in itertools.permutations((1000, 1001, 1002, 1003)):
                r.visible_units = list(order)
                actual = r.invoke('tdTargetPriorityBest', record, current, range_)
                require(actual == expected, 'Order-dependent current/HP/rank/key selection')
                require(r.live_groups == groups, 'Selector private group leaked')
                traces.append((tower, mode, order, actual))
        r.visible_units = []
        require(r.invoke('tdTargetPriorityBest', record, None, range_) is None, 'Empty selector produced target')
        require(not r.script_orders and not r.native_damage, 'Read-only selector caused order/damage side effects')
    return traces


def split_traces(script):
    results = []
    scenarios = ['ties6', 'ties7', 'range_edge', 'impact_edge', 'empty', 'null_source', 'null_target']
    for scene in scenarios:
        r = CountedRuntime(script)
        r.enemy(1000, life=10000., x=400.)
        r.visible_units = [1000]
        if scene == 'ties7':
            r.units[101]['inventory'] = {0: 4242}; r.inventory_items[4242] = rawcode('iP01')
        range_ = r.invoke('tdTowerEffectiveRangeForTower', 101)
        speed = r.invoke('tdTowerProjectileSpeed', 1)
        if scene.startswith('ties'): positions = [500.] * 10 + [300., 300.]
        elif scene == 'range_edge': positions = [range_ - 0.001, range_, range_ + .404999, range_ + .405, range_ + .405001]
        elif scene == 'impact_edge': positions = [400. + speed * d for d in (-.01, 0., .029999, .03, .030001, .05)]
        else: positions = []
        for i, x in enumerate(positions, 1001):
            r.enemy(i, life=10000., x=x); r.visible_units.append(i)
        # The explicit enum set includes the +0.405 filter boundary deliberately;
        # actual Warcraft spatial enumeration is a declared native boundary.
        groups = set(r.live_groups)
        volley = r.invoke('tdCreateArcherSplitArrowVolley', None if scene == 'null_source' else 101,
                          None if scene == 'null_target' else 1000)
        require(r.live_groups == groups, 'Split selection leaked a private group')
        trace = shot_trace(r, volley)
        result = dict(scene=scene, volley=trace)
        if volley:
            if scene.startswith('ties'): require(len(trace['shots']) == (7 if scene == 'ties7' else 6), 'Arrow count changed')
            r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']].append(volley)
            register_actual_split_listener(r)
            r.emit(100., target=1000)
            result['immediate_damage'] = list(r.native_damage)
            result['scheduled_delays'] = [delay for delay, _ in r.scheduled]
            r.flush()
            result['all_damage'] = list(r.native_damage)
            result['events'] = list(r.emitted)
            r.invoke('tdExpireArcherSplitArrowVolley', volley)
            require(not r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']], 'Expiry queue not empty')
            require(r.globals['TDArcherSplitArrowVolley_typeId'][volley] == 0, 'Expiry did not destroy volley')
        results.append(result)
    return results


def native_traces(script):
    r = CountedRuntime(script)
    r.invoke('init_TDActiveCooldownRuntime'); r.invoke('init_TDTowerBloodlustAutocast')
    r.units[101]['type'] = rawcode('uO6B')
    abilities = []
    for index in (0, 1):
        r.invoke('tdActiveSkillDefinitionAt', index)
        abilities.append(r.globals['tdActiveSkillDefinitionAt_return_abilityId'])
    r.units[101]['abilities'] = {ability: 1 for ability in abilities}
    r.invoke('tdInitializeBloodlustAutocast', 101)
    traces = []
    def capture(label):
        records = r.lists[r.globals['TDActiveCooldownRuntime_tdNativeActiveCooldowns']]
        traces.append(dict(label=label, now=r.now, abilities=sorted(r.units[101]['abilities'].items()),
            records=[dict(ability=r.globals['TDNativeActiveCooldown_abilityId'][record],
                          desired=r.globals['TDActiveNativeCooldownState_desiredLevel'][record],
                          ready=r.globals['TDActiveNativeCooldownState_readyAt'][record]) for record in records],
            choices=sorted(r.hash_values.items()), orders=list(r.stop_orders),
            has_native=r.invoke('tdHasNativeActiveCooldown', 101)))
    r.invoke('tdRefreshNativeActiveCooldowns', 101, .18); capture('warm18')
    r.event_target = 101
    for ability in abilities:
        r.spell_ability = ability; r.invoke('tdNativeActiveSpellCast')
    capture('both_cast_actual19')
    r.now += .1; r.invoke('tdRefreshNativeActiveCooldowns', 101, .4); capture('cooling_desired41')
    busy = r.tables[r.globals['TDPetState_tdPetBusyTowers']]
    busy[101] = True
    r.now += 20.; r.invoke('tdRefreshNativeActiveCooldowns', 101, 0.0); capture('expired_but_busy')
    busy.pop(101)
    r.invoke('tdRefreshNativeActiveCooldowns', 101, .4); capture('busy_finished')
    del r.units[101]['abilities'][abilities[0]]
    r.invoke('tdRefreshNativeActiveCooldowns', 101, .18); capture('one_absent')
    r.units[101]['abilities'][abilities[0]] = 1
    r.invoke('tdRefreshNativeActiveCooldowns', 101, .18); capture('restored_ability')
    r.invoke('tdSetLaneDefeated', 0, True)
    r.invoke('tdRefreshNativeActiveCooldowns', 101, .4); capture('closed_lane')
    require(not traces[-1]['records'], 'Closed lane retained native cooldown records')
    return traces


def aura_costs(script):
    results = []
    for type_, providers in [('uA11', False), ('uA6B', True)]:
        r = CountedRuntime(script); r.invoke('init_Execute'); r.invoke('init_TDActiveCooldownRuntime')
        for lane in range(4):
            for i in range(10):
                u = 100 + lane * 10 + i; r.tower(u, type_=type_, lane=lane)
                r.units[u]['x'] = lane * 3000.
                r.units[u]['abilities'] = {rawcode('A101'): 1} if providers else {}
                r.invoke('tdAuraRegisterTarget', u, True); r.invoke('tdRefreshTowerEquipmentBonuses_1', u)
        target = r.invoke('tdAuraTargetFor', 100)
        r.invoke('tdAuraRefresh', target); r.reset_counts(); r.invoke('tdAuraRefresh', target)
        results.append(dict(scene=type_, costs=r.costs(),
                            abilities=sorted(r.units[100]['abilities'].items()),
                            native_records=list(r.lists[r.globals['TDActiveCooldownRuntime_tdNativeActiveCooldowns']])))
    return results


def snapshot(map_path):
    data = map_path.read_bytes(); script = Mpq(data).extract('war3map.j').decode('utf8')
    return dict(map_sha256=hashlib.sha256(data).hexdigest(), script_sha256=hashlib.sha256(script.encode()).hexdigest(),
                attacks=attack_costs(script), selection=selection_traces(script), splits=split_traces(script), auras=aura_costs(script), native=native_traces(script))


def compare(before, after):
    require(before['selection'] == after['selection'], 'Primary selection trace changed')
    require(before['splits'] == after['splits'], 'Split order/time/context/damage trace changed')
    require(before['native'] == after['native'], 'Native cooldown/cast/autocast/lifecycle trace changed')
    for old, new in zip(before['attacks'], after['attacks']):
        n = old['enemies']; require(old['trace'] == new['trace'], 'Attack volley trace changed')
        a, b = old['costs'], new['costs']
        require(a['queries'] == b['queries'] == 2, 'Range queries changed')
        for field, expected in [('CreateGroup', (4, 3)), ('GroupAddUnit', (2*n, n)),
                                ('GroupRemoveUnit', (2*n, 2*n)), ('SquareRoot', (3*n+1, 2*n+2))]:
            require((a['natives'][field], b['natives'][field]) == expected, 'Unexpected counted cost: ' + field)
    for old, new in zip(before['auras'], after['auras']):
        require(old['abilities'] == new['abilities'] and old['native_records'] == new['native_records'], 'Aura state changed')
        require((old['costs']['definition_calls'], new['costs']['definition_calls']) == (48, 4), 'Native catalog count changed unexpectedly')
        require(old['costs']['natives'] == new['costs']['natives'], 'Warm aura native boundary behavior changed')


def archive_delta(baseline, candidate):
    old, new = members(Mpq(baseline.read_bytes())), members(Mpq(candidate.read_bytes()))
    require(old.keys() == new.keys(), 'Archive membership changed')
    changed = sorted(name for name in old if old[name][1] != new[name][1])
    require(set(changed) <= {'war3map.j', 'war3map.w3i'}, 'Object/resource bytes changed: ' + repr(changed))
    require(normalize_info(old['war3map.w3i'][1], '契灵守卫战') == normalize_info(new['war3map.w3i'][1], '契灵守卫战'), 'Non-timestamp map info changed')
    return dict(members=len(old), changed=changed, all_other_bytes_identical=True)


def mutation_evidence(baseline, candidate, expected):
    script = Mpq(candidate.read_bytes()).extract('war3map.j').decode('utf8')
    prior_script = Mpq(baseline.read_bytes()).extract('war3map.j').decode('utf8')
    def changed_body(name, old, new):
        body = functions(script)[name][0]
        require(body.count(old) == 1, 'Mutation anchor changed: ' + name)
        return script.replace(body, body.replace(old, new, 1), 1)
    cases = [
        ('split flight-time division', changed_body('tdTryAddArcherSplitArrowShot',
             'distance / projectileSpeed', 'distance / (projectileSpeed * 2.0)'), split_traces, expected['splits']),
        ('equal-distance replacement order', changed_body('tdTryAddArcherSplitArrowShot',
             'flightTime < TDArcherSplitArrowShot_flightTime', 'flightTime <= TDArcherSplitArrowShot_flightTime'), split_traces, expected['splits']),
        ('same-tick impact cutoff', changed_body('tdHandleArcherSplitArrowDamage',
             'impactDelay <= 0.03', 'impactDelay <= 0.031'), split_traces, expected['splits']),
        ('omitted second native', changed_body('tdNativeActiveSkillDefinitionCount',
             'return 2', 'return 1'), native_traces, expected['native']),
        ('restored primary group copy', script.replace(functions(script)['tdTargetPriorityBest'][0],
             functions(prior_script)['tdTargetPriorityBest'][0], 1), attack_costs, expected['attacks']),
    ]
    rejected = []
    for name, mutated, replay, reference in cases:
        # Replay must finish successfully. Interpreter errors are never counted
        # as mutation detection; only a changed measured trace/cost is rejected.
        actual = replay(mutated)
        require(actual != reference, 'Unsafe packed mutation escaped: ' + name)
        rejected.append(dict(mutation=name, replay_completed=True, trace_or_cost_mismatch=True))
    return rejected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path); p.add_argument('--baseline', type=Path); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(); current = snapshot(args.map)
    result = dict(status='PASS_SNAPSHOT', boundary=__doc__, candidate=current)
    if args.baseline:
        previous = snapshot(args.baseline); compare(previous, current)
        result.update(status='PASS', baseline=previous, archive_delta=archive_delta(args.baseline, args.map),
                      mutations=mutation_evidence(args.baseline, args.map, current))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('baseline', 'candidate')}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
