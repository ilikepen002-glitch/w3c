#!/usr/bin/env python3
"""Actual packed deployment, recall and Combat facade transactions.
Only native handles/clock/collections and deliberate boundary adversaries are modeled.
Ownership, census, admission, prepare/revalidation, recall and bonus/CD aggregation
execute the supplied map's production JASS. No Warcraft rendering claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyElementalVfxArtifact import VfxRuntime
from VerifyEquipmentAbilityArtifact import require
from VerifyPetAttackArtifact import PetAttackRuntime
from VerifyPetUIArtifact import jass_function
from VerifyTowerUpgradeArtifact import rawcode


class RebindingRuntime(VfxRuntime):
    def __init__(self, script):
        self.recalls = []
        self.refreshes = []
        self.after_create = None
        self.swap_on_damage = None
        super().__init__(script)
        self.recalls.clear()
        self.refreshes.clear()

    def execute_call(self, name, args):
        if name == 'TDPet_recall': self.recalls.append(args[0])
        if name == 'tdPetRefreshHost': self.refreshes.append(args[0])
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
        if name == 'UnitDamageTarget' and self.swap_on_damage:
            action = self.swap_on_damage
            self.swap_on_damage = None
            handled, result = super().native(name, args)
            action(self)
            return handled, result
        if name == 'CreateUnit' and self.after_create:
            action = self.after_create
            self.after_create = None
            handled, unit = super().native(name, args)
            action(self)
            return handled, unit
        return super().native(name, args)

    def tower(self, handle, lane=0, type_id='uA11'):
        self.units[handle] = {**self.units[101], 'alive': True, 'owner': lane,
                              'type': rawcode(type_id), 'x': 0., 'y': 0.,
                              'abilities': {}, 'inventory': {}}
        require(self.invoke('tdTowerChoiceForUnitTypeId', self.units[handle]['type']) != 0,
                'Unknown actual tower rawcode fixture: ' + type_id)
        return handle

    def record(self, lane=0, host=None, attribute=0, ready=91.):
        pet = self.invoke('new_TDPet', lane, 1, 1)
        require(self.invoke('tdPetStore', lane, pet), 'Original collection fixture failed')
        self.invoke('TDPet_setSkill', pet, 0, attribute, 1)
        self.invoke('TDPet_setSkill', pet, 1, 17, 1)
        if host is not None:
            require(self.invoke('tdPetDeployAndRefresh', pet, host), 'Initial production deployment failed')
        # Native clock/cooldown fixture is sampled after initial placement.
        self.globals['TDPet_readyAt'][pet] = ready
        return pet

    def field(self, name, pet): return self.globals['TDPet_' + name][pet]

    def snapshot(self, pets):
        fields = ('lane', 'species', 'level', 'skillCount', 'host', 'visual', 'generation',
                  'revision', 'readyAt', 'buffUntil', 'buffSkill', 'buffPower',
                  'pendingSkill', 'pendingSerial', 'rotation', 'resolveRotation')
        return {'pets': {pet: {name: self.field(name, pet) for name in fields} for pet in pets},
                'slots': [self.invoke('tdPetAt', lane, slot) for lane in range(4) for slot in range(20)],
                'resources': dict(self.player_resources),
                'balls': [self.invoke('tdPetBallsForLane', lane) for lane in range(4)],
                'stones': [self.globals['TDPetState_tdPetRerollStones'][lane] for lane in range(4)],
                'bonuses': {unit: dict(data.get('abilities', {})) for unit, data in self.units.items()
                            if unit in (101, 201, 202, 301)}}


def run_current_gate(script, existing, *, lane=0, other_existing=0, capacity=20,
                     pet_present=True, released=False, tower_present=True,
                     alive=True, lane_allowed=True, owner=None, tower_choice=1,
                     busy=False, occupied=False, rebind=False, repeated=False):
    require(capacity == 20 and lane in (0, 1), 'Current bounded gate fixture requires 20 slots')
    r = RebindingRuntime(script)
    selected = None
    for index in range(existing):
        host = r.tower(1000 + lane * 100 + index, lane)
        record = r.record(lane)
        r.globals['TDPet_host'][record] = host
        if index == 0: selected = record
    other_lane = 1 - lane
    for index in range(other_existing):
        record = r.record(other_lane)
        r.globals['TDPet_host'][record] = r.tower(1500 + other_lane * 100 + index, other_lane)
    if not (rebind or repeated): selected = r.record(lane)
    require(selected is not None, 'Rebind fixture needs a deployed pet')
    tower = 1000 + lane * 100 if occupied or repeated else r.tower(2000 + lane, lane)
    if owner is not None: r.units[tower]['owner'] = owner
    if not alive: r.units[tower]['alive'] = False
    if not tower_choice: r.units[tower]['type'] = rawcode('hpea')
    if busy: r.tables[r.globals['TDPetState_tdPetBusyTowers']][tower] = True
    if not lane_allowed: r.invoke('tdSetLaneActive', lane, False)
    r.globals['TDPet_released'][selected] = released
    initial = r.calls.get('tdPetDeployedCount', 0)
    result = r.invoke('tdPetCanDeploy', selected if pet_present else 0, tower if tower_present else None)
    calls = [('tdPetDeployedCount', (lane, existing))] if r.calls.get('tdPetDeployedCount', 0) != initial else []
    return result, calls


def fixture(script, source=True, occupant=True, full=False):
    r = RebindingRuntime(script)
    old = r.tower(201)
    target = r.tower(202)
    a = r.record(host=old if source else None, attribute=3, ready=91.)
    b = r.record(host=target, attribute=2, ready=117.) if occupant else None
    if full:
        while r.invoke('tdPetCollectionCount', 0) < 20: r.record()
    other = r.record(lane=1, host=r.tower(301, lane=1), ready=131.)
    r.recalls.clear(); r.refreshes.clear(); r.creations.clear(); r.removals.clear()
    return r, a, b, other, old, target


def verify_transactions(script):
    reports = []
    for source in (False, True):
        for occupant in (False, True):
            for full in (False, True):
                r, a, b, other, old, target = fixture(script, source, occupant, full)
                pets = [a, other] + ([b] if b else [])
                before = r.snapshot(pets)
                old_visuals = [r.field('visual', pet) for pet in (a, b) if pet and r.field('visual', pet)]
                require(r.invoke('tdPetDeployAndRefresh', a, target), 'Legal occupied/empty rebind failed')
                require(r.field('host', a) == target and r.invoke('tdPetForHost', target) == a, 'A not sole target occupant')
                require(not source or not r.invoke('tdPetForHost', old), 'A old host not empty')
                require(not b or r.field('host', b) is None, 'B moved instead of becoming unbound')
                after = r.snapshot(pets)
                require(before['slots'] == after['slots'], 'Rebind moved/removed original collection slots')
                for pet in pets:
                    for key in ('lane', 'species', 'level', 'skillCount', 'revision', 'readyAt'):
                        require(before['pets'][pet][key] == after['pets'][pet][key], 'Rebind changed identity/skills/CD: ' + key)
                require(before['resources'] == after['resources'] and before['balls'] == after['balls'] and before['stones'] == after['stones'],
                        'Rebind spent rewards/currency/materials')
                require(r.recalls == ([b] if b else []) + [a], 'Commit did not recall B then A exactly once')
                require(len(r.creations) == 1 and all(r.removals.count(v) == 1 for v in old_visuals), 'Visual ownership not one creation/one removal')
                require(r.field('visual', a) == r.creations[0], 'Prepared visual not owned by A')
                require(r.refreshes == ([old] if source else []) + [target], 'Facade omitted immediate host refresh')
                require(before['pets'][other] == after['pets'][other], 'Other-lane pet changed')
                reports.append({'source_bound': source, 'target_occupied': occupant, 'full_20': full})
    r, a, b, other, old, target = fixture(script)
    r.globals['TDPet_pendingSkill'][a] = True
    r.globals['TDPet_rotation'][a] = 3
    before = r.snapshot([a, b, other])
    require(r.invoke('tdPetDeployAndRefresh', a, old), 'Same-pet same-host no-op failed')
    require(r.snapshot([a, b, other]) == before and not r.recalls and not r.refreshes and not r.creations and not r.removals,
            'Same-pet same-host churned state/visuals/bonuses')
    return {'matrix': reports, 'strict_same_host_noop': True}


def verify_failures(script):
    reports = []
    for kind in ('null', 'dead', 'foreign', 'not_tower', 'busy', 'unowned_a', 'released_b',
                 'duplicate_target', 'foreign_stale_b', 'duplicate_source', 'duplicate_source_same_lane', 'foreign_source', 'create_null'):
        r, a, b, other, old, target = fixture(script)
        selected = target
        if kind == 'null': selected = None
        elif kind == 'dead': r.units[target]['alive'] = False
        elif kind == 'foreign': r.units[target]['owner'] = 1
        elif kind == 'not_tower': r.units[target]['type'] = rawcode('hpea')
        elif kind == 'busy': r.invoke('tdPetTowerWorkStarted', target)
        elif kind == 'unowned_a': r.globals['TDPetState_tdPets'][0] = 0
        elif kind == 'released_b': r.globals['TDPet_released'][b] = True
        elif kind == 'duplicate_target': r.globals['TDPet_host'][other] = target
        elif kind == 'foreign_stale_b':
            r.globals['TDPetState_tdPets'][1] = 0
            r.globals['TDPetState_tdPets'][21] = b
            r.globals['TDPet_lane'][b] = 1
        elif kind == 'duplicate_source': r.globals['TDPet_host'][other] = old
        elif kind == 'duplicate_source_same_lane':
            extra = r.record()
            r.globals['TDPet_host'][extra] = old
        elif kind == 'foreign_source': r.units[old]['owner'] = 1
        elif kind == 'create_null': r.fail_creation_at = 1
        before = r.snapshot([a, b, other])
        require(not r.invoke('tdPetDeployAndRefresh', a, selected), 'Illegal/failing deploy accepted: ' + kind)
        require(r.snapshot([a, b, other]) == before and not r.recalls and not r.refreshes and not r.removals,
                'Failed deployment damaged prior state: ' + kind)
        reports.append(kind)
    # Allow migration away from a live own upgrading/paused source, as before.
    r, a, b, other, old, target = fixture(script)
    r.invoke('tdPetTowerWorkStarted', old)
    require(r.invoke('tdPetDeployAndRefresh', a, target), 'Own paused source incorrectly prohibited migration')
    adversaries = {
        'a_generation': lambda r, a, b, old, target: r.globals['TDPet_generation'].__setitem__(a, r.field('generation', a) + 1),
        'a_revision': lambda r, a, b, old, target: r.globals['TDPet_revision'].__setitem__(a, r.field('revision', a) + 1),
        'a_slot': lambda r, a, b, old, target: r.globals['TDPetState_tdPets'].__setitem__(0, 0),
        'b_generation': lambda r, a, b, old, target: r.globals['TDPet_generation'].__setitem__(b, r.field('generation', b) + 1),
        'b_released': lambda r, a, b, old, target: r.globals['TDPet_released'].__setitem__(b, True),
        'b_slot': lambda r, a, b, old, target: r.globals['TDPetState_tdPets'].__setitem__(1, 0),
        'prepared_owner': lambda r, a, b, old, target: r.units[r.creations[-1]].__setitem__('owner', 1),
        'target_dead': lambda r, a, b, old, target: r.units[target].__setitem__('alive', False),
        'target_owner': lambda r, a, b, old, target: r.units[target].__setitem__('owner', 1),
        'target_upgrade': lambda r, a, b, old, target: r.invoke('tdPetTowerWorkStarted', target),
        'epoch': lambda r, a, b, old, target: r.invoke('tdResetWaveFlowState'),
    }
    for kind, action in adversaries.items():
        r, a, b, other, old, target = fixture(script)
        observed = []
        def callback(runtime):
            action(runtime, a, b, old, target)
            observed.append(runtime.snapshot([a, b, other]))
        r.after_create = callback
        require(not r.invoke('tdPetDeployAndRefresh', a, target), 'Post-native stale transaction accepted: ' + kind)
        require(r.snapshot([a, b, other]) == observed[0], 'Stale transaction rolled back/damaged newer state: ' + kind)
        require(len(r.creations) == 1 and r.removals == r.creations and not r.refreshes,
                'Stale transaction did not reclaim only its prepared visual: ' + kind)
        require(not r.recalls or kind == 'target_upgrade' and r.recalls == [], 'Stale transaction recalled existing records')
    return {'preflight_failures': reports, 'post_native_adversaries': list(adversaries), 'paused_source_allowed': True}


def verify_lifecycle(script):
    r, a, b, other, old, target = fixture(script)
    for pet, host in ((a, old), (b, target)):
        r.globals['TDPet_buffSkill'][pet] = 11
        r.globals['TDPet_buffPower'][pet] = .30
        r.globals['TDPet_buffUntil'][pet] = r.now + 6.
        r.invoke('tdPetRefreshHost', host, 0.)
        r.invoke('tdCombatVisualStartPetBuff', host, 0, 11, r.now + 6.)
        r.globals['TDPet_pendingSkill'][pet] = True
    generation_a, generation_b = r.field('generation', a), r.field('generation', b)
    old_ready, b_ready = r.field('readyAt', a), r.field('readyAt', b)
    require(r.invoke('tdPetDeployAndRefresh', a, target), 'Active-buff rebind failed')
    require(r.field('readyAt', a) == old_ready and r.field('readyAt', b) == b_ready, 'CD reset exploited by swapping')
    for pet in (a, b):
        require(not r.field('pendingSkill', pet) and r.field('buffUntil', pet) == 0. and r.field('buffSkill', pet) == -1,
                'Recall retained pending/buff state')
    require(not r.invoke('tdPetBindingValid', a, old, generation_a) and
            not r.invoke('tdPetBindingValid', b, target, generation_b), 'Old generation remains valid after rebind')
    require(r.invoke('tdPetCooldownReduction', old) == 0. and r.invoke('tdPetCooldownReduction', target) == .06,
            'Old/new inspiration aggregation not immediate')
    attack = r.globals['TDPetData_TD_PET_ATTACK_BONUS_ID']
    speed = r.globals['TDPetData_TD_PET_SPEED_BONUS_ID']
    require(attack not in r.units[old]['abilities'] and speed not in r.units[old]['abilities'], 'Old source retained pet bonus')
    require(speed not in r.units[target]['abilities'], 'B active speed buff transferred to A')
    require('tdPetDeployAndRefresh' in jass_function(script, 'onCommand').group(1), 'Player UI bypasses Combat facade')
    return {'active_buff_pending_cancelled': True, 'old_generations_invalid': True,
            'ready_at_preserved': [old_ready, b_ready], 'immediate_inspiration_and_bonus_refresh': True,
            'player_ui_facade_route': True}


def arm_active(r, pet, skill=22, quality=4):
    r.invoke('TDPet_setSkill', pet, 2, 8, 1)
    r.invoke('TDPet_setSkill', pet, 3, skill, quality)
    r.globals['TDPet_level'][pet] = 3
    r.globals['TDPet_readyAt'][pet] = 0.
    require(r.invoke('TDPet_skillAt', pet, 3) == skill, 'Illegal active lifecycle fixture')


def active_index(r): return r.tables[r.globals['TDPetCastContext_tdPetActiveCastIndex']]


def verify_active_lifecycle(script):
    cases = []
    # Both original attacks are pending behind the real original-hit fence.
    r, a, b, other, old, target = fixture(script)
    for pet in (a, b): arm_active(r, pet)
    for unit in (102, 103): r.enemy(unit)
    r.visible_units = [102, 103]
    r.auto_post = False
    r.emit(100., source=old, target=102)
    r.emit(100., source=target, target=103)
    require(r.field('pendingSkill', a) and r.field('pendingSkill', b), 'Actual original queue fixture did not pend')
    require(r.invoke('tdPetDeployAndRefresh', a, target), 'Queued rebind failed')
    before = len(r.damage_trace)
    r.drain_zero()
    require(r.globals['TDPetAttackQueue_tdPetPendingOriginal'] == 0, 'Captured native posts did not release original fence')
    require(len(r.damage_trace) == before and not r.field('pendingSkill', a) and not r.field('pendingSkill', b),
            'Old queued attacks executed after recall/rebind')
    cases.append('both_queued_originals_cancelled')
    # A and B running casts are cancelled; the third independent source survives.
    r, a, b, other, old, target = fixture(script)
    for pet in (a, b, other): arm_active(r, pet)
    for unit, lane in ((102, 0), (103, 0), (104, 1)): r.enemy(unit, lane=lane)
    r.visible_units = [102, 103, 104]
    for host, unit in ((old, 102), (target, 103), (301, 104)): r.emit(100., source=host, target=unit)
    require(all(pet in active_index(r) for pet in (a, b, other)), 'Running-cast fixture missed actual contexts')
    ready = [r.field('readyAt', pet) for pet in (a, b)]
    require(r.invoke('tdPetDeployAndRefresh', a, target), 'Running-active rebind failed')
    require(a not in active_index(r) and b not in active_index(r) and other in active_index(r),
            'Recall failed to cancel own casts or cancelled other source')
    before = len(r.damage_trace)
    for _ in range(100): r.tick()
    require(all(hit[1] == 301 for hit in r.damage_trace[before:]), 'Old A/B cast damaged after replacement')
    require([r.field('readyAt', pet) for pet in (a, b)] == ready, 'Running rebind reset either cooldown')
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Running cast cleanup leaked scheduler task')
    r.flush_fx_recycle()
    cases.append('both_running_casts_cancelled_other_source_completes')
    # Rebinding from inside an executing damage callback obeys safe task retirement.
    r, a, b, other, old, target = fixture(script)
    arm_active(r, a, 21, 3)
    r.enemy(102); r.visible_units = [102]
    observations = []
    def on_damage(runtime):
        context = active_index(runtime)[a]
        require(runtime.invoke('tdPetDeployAndRefresh', a, target), 'On-stack rebind failed')
        observations.append({'context': context, 'executing': runtime.globals['TDPetEffectScheduler_executing'] == context,
                             'cancelled': runtime.globals['TDPetEffectTask_cancelled'][context],
                             'alive_type': runtime.globals['TDPetEffectTask_typeId'][context]})
    r.swap_on_damage = on_damage
    r.emit(100., source=old, target=102)
    for _ in range(5): r.tick()
    require(observations and observations[0]['executing'] and observations[0]['cancelled'] and observations[0]['alive_type'],
            'Executing cast was force-destroyed instead of cancelled on stack')
    require(a not in active_index(r) and r.invoke('tdPetEffectTaskCount') == 0,
            'Cancelled executing cast failed safe exit retirement')
    r.flush_fx_recycle()
    cases.append('on_stack_cancel_then_safe_exit')
    return cases


def verify_mutations(script):
    reports = []
    def mutate(name, transform):
        m = jass_function(script, name)
        body = transform(m.group(1))
        require(body != m.group(1), 'Missing rebinding mutation root: ' + name)
        return script[:m.start(1)] + body + script[m.end(1):]
    import re
    def before_first_statement(body, statement):
        lines = body.splitlines(True)
        i = next(i for i, line in enumerate(lines) if line.strip() and not line.lstrip().startswith('local '))
        lines.insert(i, statement)
        return ''.join(lines)
    deploy = jass_function(script, 'tdPetDeploy')
    candidate = re.search(r'takes integer (\w+)', deploy.group(0))[1]
    target = re.search(r', unit (\w+)', deploy.group(0))[1]
    tests = (
        ('recall_before_prepare', 'Failed deployment damaged prior state: null', mutate('tdPetDeploy', lambda b: before_first_statement(b,
         '    call TDPet_recall(' + candidate + ', "mutation early recall")\n')), verify_failures),
        ('prepared_owner_unchecked', 'Post-native stale transaction accepted: prepared_owner', mutate('tdPetDeploy',
         lambda b: re.sub(r'GetOwningPlayer\(prepared[^)]*\)', 'Player(TDPet_lane[' + candidate + '])', b, count=1)), verify_failures),
        ('source_uniqueness_unchecked', 'Illegal/failing deploy accepted: duplicate_source_same_lane', mutate('tdPetDeployCensusValid',
         lambda b: re.sub(r'sourceCount\w* <= 1', 'true', b, count=1)), verify_failures),
        ('b_recall_omitted', 'B moved instead of becoming unbound', mutate('tdPetDeploy',
         lambda b: re.sub(r'^\s*call dispatch_TDPet_TDPet_recall\([^\n]*\n', '', b, count=1, flags=re.M)), verify_transactions),
        ('cooldown_reset', 'Rebind changed identity/skills/CD: readyAt', mutate('tdPetDeploy', lambda b: b.replace('return true',
         'set TDPet_readyAt[' + candidate + '] = 0.\n    return true')), verify_transactions),
        ('omit_target_refresh', 'Facade omitted immediate host refresh', mutate('tdPetDeployAndRefresh', lambda b: re.sub(r'^\s*call tdPetRefreshHost\([^\n]*tower[^\n]*\n', '', b, flags=re.M)), verify_transactions),
    )
    for label, expected_reason, changed, verify in tests:
        try: verify(changed)
        except ValueError as error:
            require(str(error) == expected_reason, 'Mutation hit unrelated verifier error: ' + label + ': ' + str(error))
            reports.append({'mutation': label, 'exception_type': type(error).__name__, 'reason': str(error)})
        else: raise ValueError('Rebinding mutation survived actual execution: ' + label)
    return reports


def verify_rebinding(script):
    return {'transactions': verify_transactions(script), 'failures': verify_failures(script),
            'lifecycle': verify_lifecycle(script), 'active_lifecycle': verify_active_lifecycle(script),
            'mutations': verify_mutations(script)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path); p.add_argument('--output', type=Path)
    args = p.parse_args(); data = args.map.read_bytes()
    script = Mpq(data).extract('war3map.j').decode('utf-8')
    report = verify_rebinding(script)
    report.update(status='PASS', map_sha256=hashlib.sha256(data).hexdigest(),
                  jass_sha256=hashlib.sha256(script.encode()).hexdigest(),
                  boundary='Recorded engine/clock/handle/collections; actual production transaction/recall/facade; no Warcraft observation')
    if args.output: args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
