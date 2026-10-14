#!/usr/bin/env python3
"""Replay actual MPQ zone coverage, ordered combat, contribution/ref lifetimes.

Production zone/slow/weakening/group-copy functions are never substituted. The
existing interpreter supplies native units, clock/delivery, list/table primitives,
range/enumeration order, ability acceptance, and art handles. No WC3 timing/FPS or
multiplayer claim. Only interpreter safety guards are raised for legal40-source
fixtures. Inputs and hashes are explicit; this does not import old audit globals.
"""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import inspect
import json
import math
import re
import subprocess
import textwrap

from GenerateTowerTerrainMask import Mpq
from VerifyElementalVfxArtifact import VfxRuntime
from VerifyEquipmentAbilityArtifact import require
from VerifyPetAttackArtifact import near
from VerifySpiritActiveRetentionArtifact import legal_lane_pet
from VerifyTowerUpgradeArtifact import rawcode
import VerifyBossSpellResistanceArtifact as engine

# Raise instrumentation limits only, without rewriting any packed production body.
method = textwrap.dedent(inspect.getsource(engine.BossJassRuntime.execute_call))
method = method.replace('self.executed_steps <= 2000000', 'self.executed_steps <= 100000000')
method = method.replace('steps <= 10000', 'steps <= 10000000')
namespace = {}
exec(method, engine.__dict__, namespace)
engine.BossJassRuntime.execute_call = namespace['execute_call']


class ZoneRuntime(VfxRuntime):
    def __init__(self, script):
        self.gserial = 1000000
        self.enum_stack = []
        self.expressions = 0
        self.enumerated = 0
        self.spell_calls = []
        self.admission_calls = []
        self.event_trace = []
        self.control_events = []
        self.position_ids = set()
        self.damage_action = None
        super().__init__(script)
        self.spell_calls.clear()
        self.admission_calls.clear()
        self.event_trace.clear()
        self.control_events.clear()

    def expression(self, expression, scope):
        self.expressions += 1
        return super().expression(expression, scope)

    def execute_call(self, name, args):
        if name == 'tdPetStartElementActive':
            parameters = self.functions[name][0]
            require(len(args) == len(parameters) and len(args) in (30, 31)
                    and (len(args) == 30 or parameters[-1] in ('w__wurst_stackPos', 'stackPos')),
                    'Unknown packed active-admission signature/debug parameter')
            self.admission_calls.append(tuple(args[:30]))
        if name == 'tdPetSpellDamage':
            parameters = self.functions[name][0]
            require(len(args) == len(parameters) and len(args) in (5, 6)
                    and (len(args) == 5 or parameters[-1] in ('w__wurst_stackPos', 'stackPos')),
                    'Unknown packed spell signature/debug parameter')
            # The compiler-only source-location string changes when source lines move.
            # Retain all five actual gameplay parameters, in their original order.
            self.spell_calls.append((round(self.now, 9), *args[:5]))
        result = super().execute_call(name, args)
        if name == 'new_TDPetEffectTargetPosition' and result:
            self.position_ids.add(result)
        if name == 'DamageEvent_onUnreducedDamage':
            event = self.globals['DamageInstance_maxIndex']
            self.event_trace.append((round(self.now, 9), event, self.event_source,
                                    self.event_target, *(self.globals['DamageInstance_'+field][event]
                                    for field in ('id', 'amount', 'isCode', 'isSpell'))))
        return result

    def native(self, name, args):
        # Execute exact packed Group.wurst copy/iterator/next/close helpers.
        if name in ('group_iterator', 'group_hasNext', 'group_next', 'group_close',
                    'group_destr', 'group_clear', 'group_enumUnitsInRange'):
            return False, None
        if name == 'CreateGroup':
            self.gserial += 1
            self.groups[self.gserial] = []
            return True, self.gserial
        if name == 'GroupEnumUnitsInRange':
            self.groups[args[0]] = [target for target in self.visible_units
                if self.units[target]['type'] != 0 and math.hypot(
                self.units[target]['x']-args[1], self.units[target]['y']-args[2]) <= args[3]]
            self.enumerated += len(self.groups[args[0]])
            return True, None
        if name == 'ForGroup':
            for target in list(self.groups[args[0]]):
                self.enum_stack.append(target)
                try:
                    self.invoke(args[1])
                finally:
                    self.enum_stack.pop()
            return True, None
        if name == 'GetEnumUnit':
            return True, self.enum_stack[-1]
        if name == 'GroupAddUnit':
            if args[1] not in self.groups[args[0]]:
                self.groups[args[0]].append(args[1])
            return True, True
        if name == 'GroupRemoveUnit':
            if args[1] in self.groups[args[0]]:
                self.groups[args[0]].remove(args[1])
            return True, True
        if name == 'IsUnitInGroup':
            return True, args[0] in self.groups[args[1]]
        if name == 'FirstOfGroup':
            return True, self.groups[args[0]][0] if self.groups[args[0]] else None
        if name == 'GroupClear':
            self.groups[args[0]].clear()
            return True, None
        if name == 'DestroyGroup':
            del self.groups[args[0]]
            return True, None
        if name == 'IsUnitType' and args[1] == self.globals.get('UNIT_TYPE_MECHANICAL'):
            return True, self.units[args[0]].get('mechanical', False)
        handled, result = super().native(name, args)
        if name == 'dispatch_DummyCaster_DummyCaster_castTarget' and not self.reject_control:
            self.control_events.append((self.now, *args[1:5]))
        if name == 'UnitDamageTarget' and self.damage_action:
            action = self.damage_action
            self.damage_action = None
            action(self)
        return handled, result

    def field(self, name, identity):
        return self.globals[name][identity]

    def snap(self):
        return self.expressions, Counter(self.calls), self.enumerated, self.executed_steps

    def delta(self, before):
        expressions, calls, enumerated, steps = before
        delta = Counter(self.calls)-calls
        names = {'slow_refresh': 'tdEnemySlowRefreshTimed', 'slow_offer': 'tdEnemySlowOfferTimed',
                 'slow_remove': 'tdEnemySlowRemoveTimed', 'timed_new': 'new_TDAuraTimedContribution',
                 'timed_destroy': 'destroyTDAuraTimedContribution',
                 'position_new': 'new_TDPetEffectTargetPosition', 'position_acquire': 'tdPetCaptureEffectTarget',
                 'position_release': 'tdPetReleaseEffectTarget', 'position_destroy': 'destroyTDPetEffectTargetPosition',
                 'weakening_new': 'new_TDEnemyStageWeakening', 'weakening_destroy': 'destroyTDEnemyStageWeakening',
                 'weakening_offer': 'tdEnemyMechanicOfferStageWeakening',
                 'move_speed_set': 'SetUnitMoveSpeed', 'group_adds': 'GroupAddUnit',
                 'group_next': 'group_next', 'group_create': 'CreateGroup', 'group_destroy': 'DestroyGroup',
                 'damage': 'UnitDamageTarget'}
        return {'expressions': self.expressions-expressions, 'interpreter_source_lines': self.executed_steps-steps,
                'enumerated': self.enumerated-enumerated, **{key: delta[name] for key, name in names.items()}}


def casts(r):
    return r.tables[r.globals['TDPetCastContext_tdPetActiveCastIndex']]


def targets(r, cast):
    count = r.field('TDPetCastContext_victimCount', cast)
    return [r.field('TDPetCastContext_victims_'+str(slot), cast) for slot in range(count)]


def timed(r, target):
    record = r.invoke('tdAuraTargetFor', target)
    if not record:
        return []
    return sorted(tuple(r.field('TDAuraTimedContribution_'+name, entry)
                        for name in ('source', 'identity', 'rank', 'power', 'expiresAt'))
                  for entry in r.lists[r.field('TDAuraTarget_timed', record)])


def weakening(r, target):
    record = r.invoke('tdEnemyMechanicRecordFor', target)
    if not record:
        return []
    return sorted(tuple(r.field('TDEnemyStageWeakening_'+name, entry)
                        for name in ('source', 'token', 'expiresAt'))
                  for entry in r.lists[r.field('TDEnemyMechanicRecord_weakening', record)])


def battle(r, pets):
    contexts = []
    for pet, host, primary in pets:
        cast = casts(r).get(pet, 0)
        if cast:
            contexts.append((pet, host, r.field('TDPetCastContext_generation', cast),
                             r.field('TDPetCastContext_stage', cast), r.field('TDPetCastContext_nextAt', cast),
                             r.field('TDPetCastContext_expiresAt', cast), targets(r, cast),
                             [r.field('TDPetCastContext_revisions_'+str(i), cast) for i in range(len(targets(r, cast)))]))
    return {'damage': r.damage_trace, 'spell_calls': r.spell_calls, 'events': r.event_trace,
            'control': r.control_orders, 'control_events': r.control_events,
            'cd': [r.field('TDPet_readyAt', pet) for pet, _, _ in pets],
            'random': r.random_trace, 'score': r.score(), 'gold': sorted((key, value) for key, value in r.player_resources.items()),
            'contexts': contexts, 'enemies': [(target, unit['alive'], unit['life'], unit.get('speed'),
                r.invoke('tdAuraEnemySpeedFactor', target), tuple(sorted(unit.get('abilities', {}).items())),
                timed(r, target), weakening(r, target))
                for target, unit in sorted(r.units.items()) if unit.get('owner') == r.globals['TDConfig_TD_ENEMY_PLAYER_ID'] and unit['type'] != 0]}


def turn(r, time):
    r.now = time
    r.executed_steps = 0
    before = r.snap()
    callbacks = r.periodic_callbacks('TDPetEffectScheduler')
    require(len(callbacks) == 1, 'Expected one actual effect scheduler')
    r.invoke('call_doPeriodically_TDPetEffectScheduler', callbacks[0], callbacks[0])
    r.drain_zero()
    return r.delta(before)


def cleanup(r, pets):
    for pet, _, _ in pets:
        r.invoke('TDPet_recall', pet)
    require(r.invoke('tdPetEffectTaskCount') == 0 and not casts(r), 'Zone cancellation retained tasks/casts')
    require(not r.tables[r.globals['TDPetEffectTargetState_positions']], 'Zone cancellation retained position index')
    require(all(r.field('TDPetEffectTargetPosition_references', position) == 0 for position in r.position_ids),
            'Zone cancellation retained detached/retired position references')
    for target in r.units:
        require(not timed(r, target), 'Zone cancellation retained timed contribution')
        require(not weakening(r, target), 'Zone cancellation retained stage-weakening token')
    r.invoke('tdCombatVisualShutdown')
    r.flush_fx_recycle()
    return {'tasks': 0, 'casts': 0, 'position_index': 0, 'position_refs': 0, 'timed': 0, 'weakening': 0,
            'native_effects': len(r.visual_handles), 'native_lightning': len(r.lightning_handles)}


def setup(script, count=1, mixed=False, skill=30, n=52, mechanics=False):
    r = ZoneRuntime(script)
    r.now = 20.10
    pets = []
    visible = []
    for lane in range((count+9)//10):
        for i in range(n):
            target = 2000+lane*100+i
            r.enemy(target, x=lane*1500.+100.+i*.1, lane=lane)
            if mechanics:
                r.units[target].update(type=rawcode('uB32'), userdata=lane*10000+3200, wave=32)
            visible.append(target)
        for slot in range(min(10, count-lane*10)):
            host = 1000+lane*10+slot
            r.units[host] = {**r.units[101], 'x': lane*1500., 'owner': lane, 'lane': lane,
                             'abilities': {}, 'inventory': {}}
            actual_skill = 37 if mixed and slot % 2 else skill
            pet = legal_lane_pet(r, lane, host, slot, actual_skill)
            pets.append((pet, host, 2000+lane*100))
    r.visible_units = visible
    if mechanics:
        r.invoke('tdSetupEnemyMechanics')
        for target in visible:
            r.invoke('tdEnemyMechanicRegister', target, r.units[target]['lane'], 32, 3)
            require(r.invoke('tdEnemyMechanicIsRegistered', target), 'Actual mechanic record was not created')
    for _, host, target in pets:
        r.emit(100., source=host, target=target)
    require(len(casts(r)) == count, 'Legal source admission count differs')
    return r, pets


def overlap(script, count, mixed=False, skill=30, mechanics=False):
    r, pets = setup(script, count, mixed, skill, mechanics=mechanics)
    first = turn(r, 20.15)
    initial = battle(r, pets)
    steady = turn(r, 20.35)
    current = battle(r, pets)
    require(steady['slow_offer'] == count*12 and steady['group_adds'] == count*52,
            'Original per-source coverage/real group clone changed')
    for pet, _, _ in pets:
        require(len(targets(r, casts(r)[pet])) == 12, 'Zone coverage cap changed')
    pulse = turn(r, 20.60)
    pulse_battle = battle(r, pets)
    return {'first': first, 'steady': steady, 'pulse': pulse, 'trace': [initial, current, pulse_battle],
            'cleanup': cleanup(r, pets)}


def coverage_order(script, candidate=False):
    r, pets = setup(script, n=13)
    turn(r, 20.15)
    pet = pets[0][0]
    cast = casts(r)[pet]
    original = targets(r, cast)
    saved = {}
    for slot, target in enumerate(original):
        position = r.field('TDPetCastContext_targetPositions_'+str(slot), cast)
        r.globals['TDPetCastContext_hitCounts_'+str(slot)][cast] = slot+1
        r.globals['TDPetCastContext_controlled_'+str(slot)][cast] = bool(slot % 2)
        r.globals['TDPetCastContext_lastPositionX_'+str(slot)][cast] = 500.+slot
        r.globals['TDPetCastContext_lastPositionY_'+str(slot)][cast] = 600.+slot
        saved[target] = (position, 500.+slot, 600.+slot)
    # These two arrays belong to other skills and retain physical-slot history.
    # Zone cannot move or clear them, even in unused tail slots / zero coverage.
    legacy = lambda: ([r.field('TDPetCastContext_hitCounts_'+str(i), cast) for i in range(12)],
                      [r.field('TDPetCastContext_controlled_'+str(i), cast) for i in range(12)])
    original_legacy = legacy()
    order = list(reversed(r.visible_units))
    r.visible_units = order
    change = turn(r, 20.35)
    selected = order[:12]
    require(targets(r, cast) == selected, 'New zone order/cap differs from original native enumeration')
    if candidate:
        for slot, target in enumerate(selected):
            position = r.field('TDPetCastContext_targetPositions_'+str(slot), cast)
            require(r.field('TDPetEffectTargetPosition_target', position) == target,
                    'Parallel target-position slot detached from reordered unit')
            require(r.field('TDPetCastContext_revisions_'+str(slot), cast) ==
                    r.field('TDPetEffectTargetPosition_revision', position), 'Parallel revision slot is stale')
            if target in saved:
                actual = (position, r.field('TDPetCastContext_lastPositionX_'+str(slot), cast),
                          r.field('TDPetCastContext_lastPositionY_'+str(slot), cast))
                require(actual == saved[target], 'Zone permutation did not move complete zone-owned slot')
            near(r.field('TDPetCastContext_zoneSlowPowers_'+str(slot), cast), .25,
                 'Reordered zone power detached from retained target')
        require(change['position_acquire'] == 1 and change['position_release'] == 1,
                'Thirteenth victim turnover rebuilt unchanged position ownership')
    # Reorder exactly the same set before an even-stage pulse.
    r.visible_units = [*selected[::2], *selected[1::2], order[12]]
    expected = r.visible_units[:12]
    turn(r, 20.60)
    require([hit[2] for hit in r.damage_trace] == expected, 'Vortex pulse ignored new enumeration order')
    require(legacy() == original_legacy, 'Zone reordered legacy hit/control physical slots')
    pulse_state = battle(r, pets)
    r.visible_units = []
    turn(r, 20.85)
    require(not targets(r, cast) and legacy() == original_legacy,
            'Empty zone coverage cleared legacy hit/control tail slots')
    trace = [pulse_state, battle(r, pets)]
    # Fixture-only sentinel position components are deliberately not battle state.
    return {'change': change, 'trace': trace, 'cleanup': cleanup(r, pets)}


def identity_retirement(script, candidate=False, revision=False):
    r, pets = setup(script, n=12)
    turn(r, 20.15)
    cast = casts(r)[pets[0][0]]
    target = targets(r, cast)[0]
    position = r.field('TDPetCastContext_targetPositions_0', cast)
    if revision:
        r.globals['TDPetEffectTargetPosition_revision'][position] += 1
        r.globals['TDPetCastContext_revisions_0'][cast] += 1
    else:
        r.units[target]['alive'] = False
        r.invoke('tdPetForgetEnemy', target)
        require(r.field('TDPetEffectTargetPosition_retired', position), 'Actual death did not retire shared target')
        r.units[target]['alive'] = True
    counts = turn(r, 20.35)
    if candidate:
        require(counts['position_acquire'] == 1 and counts['position_release'] == 1,
                'Retired/revision-changed identity was incorrectly retained as intersection')
    trace = battle(r, pets)
    return {'counts': counts, 'trace': trace, 'cleanup': cleanup(r, pets)}


def strength_and_expiry(script):
    r, pets = setup(script, count=2, mixed=True, n=12, mechanics=True)
    turn(r, 20.15)
    turn(r, 20.35)
    target = 2000
    near(r.invoke('tdAuraEnemySpeedFactor', target), .8, 'Boss independent vortex/seal composition')
    near(r.invoke('tdEnemyMechanicScaleSpellDamage', target, 100.), 66.4, 'Actual seal weakening not active')
    seal = pets[1]
    token = casts(r)[seal[0]]
    rows = weakening(r, target)
    require(len(rows) == 1 and rows[0][:2] == (seal[1], token), 'Seal failed to retain original source/token')
    near(rows[0][2], 20.65, 'Seal failed to renew original source/token deadline')
    # Remove the stronger vortex source, preserving weaker seal and its same token.
    r.invoke('TDPet_recall', pets[0][0])
    near(r.invoke('tdAuraEnemySpeedFactor', target), .925, 'Strong source removal failed to expose weaker source')
    deadline = rows[0][2]
    r.now = deadline-.01
    r.invoke('tdEnemySlowRefreshTimed', target)
    near(r.invoke('tdAuraEnemySpeedFactor', target), .925, 'Remaining source expired early')
    near(r.invoke('tdEnemyMechanicScaleSpellDamage', target, 100.), 66.4, 'Seal weakening expired early')
    before = battle(r, pets)
    r.now = deadline
    r.invoke('tdEnemySlowRefreshTimed', target)
    near(r.invoke('tdAuraEnemySpeedFactor', target), 1., 'Timed contribution survived exact expiry')
    near(r.invoke('tdEnemyMechanicScaleSpellDamage', target, 100.), 58., 'Weakening survived exact expiry')
    after = battle(r, pets)
    return {'trace': [before, after], 'cleanup': cleanup(r, pets)}


def same_identity_strength(script):
    r, pets = setup(script, n=12)
    turn(r, 20.15)
    target = 2000
    identity = r.globals['TDAuraRules_TD_AURA_PET_VORTEX']
    weak = 101
    r.invoke('tdEnemySlowOfferTimed', target, weak, identity, 1, .10, .60)
    turn(r, 20.35)
    near(r.invoke('tdAuraEnemySpeedFactor', target), .75, 'Weak same-identity source suppressed strong coverage')
    weak_deadline = next(entry[-1] for entry in timed(r, target) if entry[0] == weak)
    r.invoke('TDPet_recall', pets[0][0])
    near(r.invoke('tdAuraEnemySpeedFactor', target), .90, 'Strong same-identity source removal erased weak source')
    require(len(timed(r, target)) == 1 and timed(r, target)[0][0] == weak,
            'Strong source cleanup changed another source identity')
    before = battle(r, pets)
    r.now = weak_deadline
    r.invoke('tdEnemySlowRefreshTimed', target)
    near(r.invoke('tdAuraEnemySpeedFactor', target), 1., 'Weaker source expired on wrong deadline')
    after = battle(r, pets)
    return {'trace': [before, after], 'cleanup': cleanup(r, pets)}


def cancellation(script, action):
    r, pets = setup(script, n=12)
    turn(r, 20.15)
    pet, host, _ = pets[0]
    if action in ('death-in-pulse', 'remove-in-pulse', 'move-in-pulse', 'recall-in-pulse', 'generation-in-pulse'):
        def deliver(runtime):
            if action == 'recall-in-pulse':
                runtime.invoke('TDPet_recall', pet)
            elif action == 'generation-in-pulse':
                runtime.invoke('TDPet_invalidateCombat', pet)
            elif action == 'move-in-pulse':
                runtime.units[2005]['x'] = 1000.
            else:
                runtime.units[2005]['alive'] = False
                runtime.invoke('tdPetForgetEnemy', 2005)
                if action == 'remove-in-pulse':
                    runtime.call('RemoveUnit', [2005])
        r.damage_action = deliver
        turn(r, 20.35)
        turn(r, 20.60)
        require(len(r.damage_trace) == (1 if action in ('recall-in-pulse', 'generation-in-pulse') else 11 if action != 'move-in-pulse' else 12),
                'Synchronous damage interruption changed later hit decisions')
    else:
        if action == 'owner':
            r.units[host]['owner'] = 1
        elif action == 'host-remove':
            r.call('RemoveUnit', [host])
        elif action == 'lane':
            r.invoke('tdSetLaneActive', 0, False)
        elif action == 'gameover':
            r.invoke('tdSetGameOver', True)
        elif action == 'epoch':
            r.invoke('tdResetWaveFlowState')
        elif action == 'revision':
            r.globals['TDPet_revision'][pet] += 1
        else:
            raise ValueError(action)
        turn(r, 20.35)
        require(not casts(r) and not r.native_damage, 'Invalid source continued zone lifetime: '+action)
    trace = battle(r, pets)
    return {'trace': trace, 'cleanup': cleanup(r, pets)}


def filtering_boundaries(script):
    r, pets = setup(script, n=16)
    r.units[2000]['x'] = 380.  # center100 + radius280, exact inclusive boundary
    r.units[2001]['x'] = 380.001
    r.units[2002]['x'] = 379.999
    r.units[2003]['userdata'] = 10100
    r.units[2004]['mechanical'] = True
    r.units[2005].update(type=rawcode('uB32'), wave=32, userdata=3200)
    turn(r, 20.15)
    cast = casts(r)[pets[0][0]]
    require(2000 in targets(r, cast) and 2001 not in targets(r, cast) and 2002 in targets(r, cast)
            and 2003 not in targets(r, cast) and 2004 in targets(r, cast), 'Native range/lane/mechanical contract differs')
    near(r.invoke('tdAuraEnemySpeedFactor', 2005), .875, 'Boss slow did not retain half power')
    r.units[2000]['x'] = 380.001
    r.units[2001]['x'] = 380.
    turn(r, 20.35)
    require(2000 not in targets(r, cast) and 2001 in targets(r, cast), 'Boundary entering/leaving membership is stale')
    turn(r, 20.60)
    trace = battle(r, pets)
    return {'trace': trace, 'cleanup': cleanup(r, pets)}


def refresh_repairs(script):
    r, pets = setup(script, n=12)
    turn(r, 20.15)
    target = 2000
    identity = r.globals['TDAuraRules_TD_AURA_PET_VORTEX']
    extra_source = 101
    r.invoke('tdEnemySlowOfferTimed', target, extra_source, identity, 1, .40, .10)
    r.invoke('tdAuraBuff', identity, 1)
    carrier = r.globals['tdAuraBuff_return_abilId']
    r.units[target]['abilities'].pop(carrier, None)
    r.units[target]['speed'] = 260.
    counts = turn(r, 20.35)
    require(carrier in r.units[target]['abilities'], 'Intersection offer skipped native carrier repair')
    near(r.invoke('tdAuraEnemySpeedFactor', target), .75, 'Intersection renewal skipped expiry aggregation')
    near(r.units[target]['speed'], 195., 'Intersection renewal skipped actual speed repair')
    require(len(timed(r, target)) == 1, 'Expired unrelated source survived retained offer refresh')
    rows = timed(r, target)
    near(rows[0][-1], 20.65, 'Retained offer did not refresh now plus .30')
    turn(r, 20.60)
    return {'counts': counts, 'trace': battle(r, pets), 'cleanup': cleanup(r, pets)}


def boss_type_change(script, candidate=False):
    r, pets = setup(script, n=12)
    turn(r, 20.15)
    target = 2000
    original_type = r.units[target]['type']
    r.units[target].update(type=rawcode('uB32'), userdata=3200, wave=32)
    counts = turn(r, 20.35)
    near(r.invoke('tdAuraEnemySpeedFactor', target), .875, 'Live Boss type change retained stale full slow')
    require(len(timed(r, target)) == 1, 'Live type change kept old power under the same source/identity')
    if candidate:
        require(counts['timed_new'] == 1 and counts['timed_destroy'] == 1,
                'Changed exact slow key was incorrectly retained')
    r.units[target].update(type=original_type, userdata=100, wave=1)
    turn(r, 20.60)
    near(r.invoke('tdAuraEnemySpeedFactor', target), .75, 'Live normal type restoration retained half slow')
    require(len(timed(r, target)) == 1, 'Type restoration duplicated source/identity contributions')
    return {'counts': counts, 'trace': battle(r, pets), 'cleanup': cleanup(r, pets)}


def trial_retirement(script, reused=False, reset=False):
    r = ZoneRuntime(script)
    r.enter(8)
    pet = r.pet(30)
    original = [r.target(index) for index in range(5)]
    for target in original:
        r.units[target].update(x=100., y=0.)
    r.visible_units = original[:]
    r.emit(100., target=original[0])
    turn(r, r.now+.05)
    old = original[0]
    r.units[old]['alive'] = False
    r.event_target = old
    r.invoke('tdTrialOnTargetDeath')
    if reset:
        r.state_call('reset')
    else:
        replacement = r.adversarial_rebind(0, reused=reused)
        r.units[replacement].update(x=100., y=0.)
        r.visible_units = [replacement, *original[1:]]
    turn(r, r.now+.25)
    turn(r, r.now+.25)
    if not reset:
        require(len(r.damage_trace) == 4 and all(hit[2] != replacement for hit in r.damage_trace),
                'Trial replacement entered previously captured AOE identity')
    else:
        require(not casts(r) and not r.damage_trace, 'Trial generation reset retained old cast')
    pets = [(pet, 101, original[0])]
    trace = battle(r, pets)
    return {'trace': trace, 'cleanup': cleanup(r, pets)}


def id_reuse(script):
    r, pets = setup(script, n=12)
    turn(r, 20.15)
    old = casts(r)[pets[0][0]]
    pet, host, target = pets[0]
    old_cd = r.field('TDPet_readyAt', pet)
    r.invoke('TDPet_invalidateCombat', pet)
    require(not casts(r), 'Old generation active index survived invalidation')
    # Resume the same legal host and deliberately authorize the next fixture attack.
    # Native cooldown is not changed by production; boundary only permits a new cast here.
    r.globals['TDPet_readyAt'][pet] = r.now
    r.emit(100., source=host, target=target)
    fresh = casts(r)[pet]
    require(fresh == old, 'Low-level cast fixture did not actually reuse freed class ID')
    turn(r, r.now+.05)
    require(all(timed(r, target) for target in range(2000, 2012)), 'Fresh generation lost its slow ownership')
    r.invoke('tdPetCancelEffectTasks', 999999)
    require(casts(r)[pet] == fresh, 'Unrelated cancellation erased reused cast')
    trace = battle(r, pets)
    return {'old_cd': old_cd, 'class_id_reused': fresh, 'trace': trace, 'cleanup': cleanup(r, pets)}


def generation_admission(script):
    """Exercise actual deferred cancellation and both same-host admission fences.

    Old cleanup cannot overlap fresh ownership: an executing old cast retains the
    active index until the scheduler destroys it. Only then can a valid fresh
    generation enter. Stale generation requests never enter the fresh lifetime.
    The explicit start calls exercise the packed admission boundary with the old
    immutable snapshots; the fixture does not alter pending, cooldown or scheduler.
    """
    r, pets = setup(script, n=12)
    turn(r, 20.15)
    pet, host, target = pets[0]
    old = casts(r)[pet]
    old_generation = r.field('TDPetCastContext_generation', old)
    ready = r.field('TDPet_readyAt', pet)
    # Preserve every original admitted value, including the five trial identities
    # and road points, instead of manufacturing an easier second context.
    require(len(r.admission_calls) == 1, 'Fixture initial original-hit admission was not unique')
    args = list(r.admission_calls[0])
    require(len(args) == 30, 'Actual active admission snapshot arity changed')
    observations = []

    def start(generation):
        values = args[:]
        values[2] = generation
        return r.invoke('tdPetStartElementActive', *values)

    def cancel_on_stack(runtime):
        runtime.invoke('TDPet_invalidateCombat', pet)
        fresh_generation = runtime.field('TDPet_generation', pet)
        require(fresh_generation != old_generation and casts(runtime).get(pet) == old,
                'Executing cancellation bypassed deferred old-cast ownership')
        require(not start(fresh_generation), 'Fresh generation entered before old executing cleanup')
        require(casts(runtime).get(pet) == old, 'Rejected on-stack admission displaced old active index')
        observations.append(('deferred-cancel', old_generation, fresh_generation,
                             len(timed(runtime, target)), runtime.field('TDPet_readyAt', pet)))

    r.damage_action = cancel_on_stack
    turn(r, 20.35)
    turn(r, 20.60)
    require(len(r.damage_trace) == 1 and not casts(r) and not timed(r, target),
            'Old executing generation did not finish exact original cancellation cleanup')
    require(not start(old_generation) and not casts(r), 'Old generation entered after its cleanup')
    fresh_generation = r.field('TDPet_generation', pet)
    require(start(fresh_generation), 'Fresh generation was blocked after old cleanup completed')
    fresh = casts(r)[pet]
    require(fresh == old, 'Deferred cleanup fixture did not force actual class ID reuse')
    turn(r, 20.65)
    rows = timed(r, target)
    require(rows and all(timed(r, target) for target in range(2000, 2012)),
            'Fresh generation failed to acquire its new coverage')
    require(not start(old_generation), 'Stale generation request entered fresh ownership lifetime')
    require(casts(r).get(pet) == fresh and timed(r, target) == rows
            and r.field('TDPet_readyAt', pet) == ready,
            'Late stale-generation request erased fresh index/contribution or changed cooldown')
    observations.append(('fresh-retained', fresh_generation, r.field('TDPet_readyAt', pet), rows))
    return {'admission': observations, 'class_id_reused': fresh, 'trace': battle(r, pets),
            'cleanup': cleanup(r, pets)}


def cross_skill_reuse(script, origin=28, zones=(30,), mode='exit', ending='recall'):
    """Real skills populate legacy slots, then zone and a consumer reuse one ID.

    No legacy field is injected. The original line28 writes nonuniform hit counts;
    roots26 writes controlled flags. All admission, hits, control and cleanup run
    the actual packed functions. Only legal native clock/order/positions vary.
    """
    r = ZoneRuntime(script)
    r.now = 20.10
    host = 1000
    r.units[host] = {**r.units[101], 'x': 0., 'owner': 0, 'lane': 0, 'abilities': {}, 'inventory': {}}
    original_order = list(range(2000, 2012))
    for target in original_order:
        r.enemy(target, x=100.+(target-2000)*.1, lane=0)
    r.visible_units = original_order[:]
    pets, ids, snapshots, zone_legacy = [], [], [], []

    def admit(skill, when):
        r.now = when
        pet = legal_lane_pet(r, 0, host, len(pets), skill)
        r.emit(100., source=host, target=2000)
        pets.append((pet, host, 2000))
        cast = casts(r)[pet]
        ids.append(cast)
        return pet, cast

    def legacy(cast):
        return ([r.field('TDPetCastContext_hitCounts_'+str(i), cast) for i in range(12)],
                [r.field('TDPetCastContext_controlled_'+str(i), cast) for i in range(12)])

    pet, cast = admit(origin, 20.10)
    turn(r, 20.15)
    if origin == 28:
        turn(r, 20.75)
        require(legacy(cast)[0] == [2]*8+[0]*4, 'Real line28 did not populate nonuniform legacy hit counts')
    else:
        require(origin == 26 and sum(legacy(cast)[1]) == 6, 'Real roots26 did not populate six legacy control flags')
    original_legacy = legacy(cast)
    snapshots.append(battle(r, pets))
    r.invoke('TDPet_recall', pet)
    require(not casts(r), 'Origin skill did not release its real cast ID')
    for index, skill in enumerate(zones):
        created = 21.10+index
        pet, cast = admit(skill, created)
        turn(r, round(created+.05, 9))
        if mode == 'exit':
            for target in original_order:
                r.units[target]['x'] = 1000.
        else:
            r.visible_units = list(reversed(original_order))
        turn(r, round(created+.30, 9))
        zone_legacy.append(legacy(cast))
        snapshots.append(battle(r, pets))
        if ending == 'natural':
            for tick in range(7, 83):
                turn(r, round(created+tick*.05, 9))
            require(pet not in casts(r), 'Zone natural endpoint failed to free reused cast ID')
        elif ending == 'invalidate':
            r.invoke('TDPet_invalidateCombat', pet)
        else:
            r.invoke('TDPet_recall', pet)
        require(not casts(r), 'Zone termination retained cast')
        zone_legacy.append(legacy(cast))
        # Natural/invalid cancellation ends the cast but does not unbind its pet.
        # Recall through production before legally assigning another pet to host.
        if ending != 'recall':
            r.invoke('TDPet_recall', pet)
        for target in original_order:
            r.units[target]['x'] = 100.+(target-2000)*.1
        r.visible_units = original_order[:]
    when = round(r.now+1., 9)
    pet, cast = admit(26, when)
    before_damage, before_control = len(r.damage_trace), len(r.control_orders)
    turn(r, round(when+.05, 9))
    require(len(set(ids)) == 1, 'Cross-skill fixture did not actually reuse the same freed class ID')
    expected_hits = 4 if origin == 28 else 12
    require(len(r.damage_trace)-before_damage == expected_hits,
            'Subsequent segment changed legacy-hit behavior after zone class ID reuse')
    controls = r.control_orders[before_control:]
    expected_control_targets = original_order[6:] if origin == 26 else original_order[8:]
    require([control[-1] for control in controls] == expected_control_targets,
            'Subsequent roots changed actual control targets after zone class ID reuse')
    require(all(value == original_legacy for value in zone_legacy),
            'Zone changed legacy physical slots across real skill ID reuse')
    snapshots.append(battle(r, pets))
    return {'class_ids': ids, 'legacy_before_zone': original_legacy,
            'final_segment_damage': r.damage_trace[before_damage:],
            'final_segment_controls': controls, 'zone_legacy': zone_legacy,
            'trace': snapshots, 'cleanup': cleanup(r, pets)}


def completion(script):
    r, pets = setup(script, n=12)
    for tick in range(1, 83):
        turn(r, round(20.10+tick*.05, 9))
    require(len(r.damage_trace) == 96 and not casts(r), 'Original 0.5s damage/4s endpoint count changed')
    trace = battle(r, pets)
    return {'trace': trace, 'cleanup': cleanup(r, pets)}


def cases(script, candidate=False):
    result = {}
    print('zone cases candidate=' + str(candidate), flush=True)
    for count in (1, 2, 10, 40):
        print('zone overlap', count, flush=True)
        result['overlap-'+str(count)] = overlap(script, count)
    for count in (2, 10, 40):
        print('zone mixed', count, flush=True)
        result['mixed-'+str(count)] = overlap(script, count, mixed=True)
    result['actual-seal-mechanic'] = overlap(script, 2, skill=37, mechanics=True)
    result['order-thirteenth'] = coverage_order(script, candidate)
    result['retired-resurrection'] = identity_retirement(script, candidate)
    result['revision-mismatch'] = identity_retirement(script, candidate, revision=True)
    result['strength-expiry'] = strength_and_expiry(script)
    result['same-identity-strength'] = same_identity_strength(script)
    result['filtering-boundaries'] = filtering_boundaries(script)
    result['live-boss-type-change'] = boss_type_change(script, candidate)
    result['intersection-refresh-repairs'] = refresh_repairs(script)
    for action in ('death-in-pulse', 'remove-in-pulse', 'move-in-pulse', 'recall-in-pulse', 'generation-in-pulse',
                   'owner', 'host-remove', 'lane', 'gameover', 'epoch', 'revision'):
        result[action] = cancellation(script, action)
    for reused in (False, True):
        result['trial-reused' if reused else 'trial-new'] = trial_retirement(script, reused)
    result['trial-reset'] = trial_retirement(script, reset=True)
    result['cast-id-reuse'] = id_reuse(script)
    result['generation-admission'] = generation_admission(script)
    for origin, zones, mode, ending in (
            (28, (30,), 'exit', 'recall'), (28, (37,), 'exit', 'invalidate'),
            (28, (30,), 'reverse', 'recall'), (28, (30, 37), 'exit', 'recall'),
            (26, (30,), 'reverse', 'recall'), (26, (37,), 'exit', 'invalidate'),
            (28, (30,), 'reverse', 'natural'), (26, (37,), 'reverse', 'natural')):
        label = 'cross-skill-'+str(origin)+'-'+'.'.join(map(str, zones))+'-'+mode+'-'+ending
        print('zone', label, flush=True)
        result[label] = cross_skill_reuse(script, origin, zones, mode, ending)
    result['completion'] = completion(script)
    return result


def replace_body(script, name, modify):
    match = re.search(r'^function '+re.escape(name)+r' takes [^\n]+\n(.*?)^endfunction', script, re.M | re.S)
    require(match is not None, 'Mutation function absent: '+name)
    body = match.group(1)
    changed = modify(body)
    require(changed != body, 'Mutation did not change its exact packed root: '+name)
    return script[:match.start(1)]+changed+script[match.end(1):]


def clear_legacy_slot(body, field):
    match = re.search(r'^[ \t]*call TDPetCastContext_revisions_set\([^\n]+\n', body, re.M)
    require(match is not None, 'Exact zone tail-slot setter absent for legacy mutation')
    line = match.group(0).replace('TDPetCastContext_revisions_set', 'TDPetCastContext_'+field+'_set')
    if field == 'controlled':
        line = line.replace(', 0, "', ', false, "')
    return body+line


def swap_legacy_slots(body, field):
    getters = re.findall(r'TDPetCastContext_victims_get\(([^,]+), ([^,]+), "[^"\n]+"\)', body)
    require(len(getters) >= 2 and getters[0][0] == getters[1][0], 'Exact zone swap getter shape changed')
    owner, first = getters[0]
    second = getters[1][1]
    value_type = 'boolean' if field == 'controlled' else 'integer'
    getter = 'TDPetCastContext_'+field+'_get'
    setter = 'TDPetCastContext_'+field+'_set'
    return ('\tlocal '+value_type+' mutationLegacy\n'+body+
            '\tset mutationLegacy = '+getter+'('+owner+', '+first+', "mutation legacy read")\n'+
            '\tcall '+setter+'('+owner+', '+first+', '+getter+'('+owner+', '+second+', "mutation legacy read"), "mutation legacy write")\n'+
            '\tcall '+setter+'('+owner+', '+second+', mutationLegacy, "mutation legacy write")\n')


def mutations(script):
    rows = []
    tests = [
        ('retired-intersection', 'tdPetZoneCoverageReusable',
         lambda body: re.sub(r'\(?\s*not retired(?:_\d+)?\s*\)?\s+and\s+', '', body), lambda mutant: identity_retirement(mutant, True)),
        ('skip-permutation', 'TDPetCastContext_swapZoneVictimSlots',
         lambda body: re.sub(r'^[ \t]*(?:set TDPetCastContext_|call TDPetCastContext_[A-Za-z0-9_]+_set)[^\n]+\n', '', body, flags=re.M),
         lambda mutant: coverage_order(mutant, True)),
        ('forget-parallel-position', 'TDPetCastContext_swapZoneVictimSlots',
         lambda body: re.sub(r'^[ \t]*(?:set TDPetCastContext_targetPositions_|call TDPetCastContext_targetPositions_set)[^\n]+\n', '', body, flags=re.M),
         lambda mutant: coverage_order(mutant, True)),
        ('skip-revision', 'tdPetZoneCoverageReusable',
         lambda body: re.sub(r'retainedRevision(?:_\d+)? == sampledRevision(?:_\d+)?', 'true', body),
         lambda mutant: identity_retirement(mutant, True, revision=True)),
        ('skip-owner', 'tdPetBindingValid',
         lambda body: re.sub(r'GetPlayerId\(GetOwningPlayer\(host(?:_\d+)?\)\) == TDPet_lane\[pet(?:_\d+)?\] and ', '', body),
         lambda mutant: cancellation(mutant, 'owner')),
        ('skip-retained-offer', 'TDPetCastContext_zone',
         lambda body: re.sub(r'^[ \t]*call (?:dispatch_TDPetCastContext_)?TDPetCastContext_slow\([^\n]+\n', '', body, flags=re.M),
         lambda mutant: refresh_repairs(mutant)),
        ('skip-expiry-refresh', 'tdEnemySlowRefreshTimed',
         lambda body: re.sub(r'^[ \t]*call tdEnemySlowExpire\([^\n]+\n', '', body, flags=re.M),
         lambda mutant: refresh_repairs(mutant)),
        ('late-zone-tick', 'TDPetCastContext_zone',
         lambda body: body.replace(' * 0.25', ' * 0.30'), lambda mutant: completion(mutant)),
        ('old-generation-overlap-admission', 'tdPetStartElementActive',
         lambda body: re.sub(r'^[ \t]*if dispatch_Table_Table_hasInt\(TDPetCastContext_tdPetActiveCastIndex[^\n]+\n'
                             r'.*?^[ \t]*endif\n', '', body, count=1, flags=re.M | re.S),
         generation_admission),
        ('old-generation-stale-admission', 'tdPetBindingValid',
         lambda body: re.sub(r'TDPet_generation\[pet(?:_\d+)?\] == generation(?:_\d+)? and ', '', body),
         generation_admission),
        ('clear-legacy-hitcounts', 'TDPetCastContext_forgetZoneVictim',
         lambda body: clear_legacy_slot(body, 'hitCounts'),
         lambda mutant: cross_skill_reuse(mutant, 28, (30,), 'exit')),
        ('clear-legacy-controlled', 'TDPetCastContext_forgetZoneVictim',
         lambda body: clear_legacy_slot(body, 'controlled'),
         lambda mutant: cross_skill_reuse(mutant, 26, (37,), 'exit')),
        ('swap-legacy-hitcounts', 'TDPetCastContext_swapZoneVictimSlots',
         lambda body: swap_legacy_slots(body, 'hitCounts'),
         lambda mutant: cross_skill_reuse(mutant, 28, (30,), 'reverse')),
        ('swap-legacy-controlled', 'TDPetCastContext_swapZoneVictimSlots',
         lambda body: swap_legacy_slots(body, 'controlled'),
         lambda mutant: cross_skill_reuse(mutant, 26, (30,), 'reverse')),
    ]
    for label, name, modify, check in tests:
        mutant = replace_body(script, name, modify)
        try:
            check(mutant)
        except (ValueError, AssertionError) as error:
            rows.append({'mutation': label, 'rejected': True, 'reason': str(error)})
        else:
            raise ValueError('Zone mutation escaped: '+label)
    return rows


def metadata(path):
    data = path.read_bytes()
    script = Mpq(data).extract('war3map.j').decode()
    return script, {'map': str(path.resolve()), 'map_sha256': hashlib.sha256(data).hexdigest(),
                    'jass_sha256': hashlib.sha256(script.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-map', type=Path, required=True)
    parser.add_argument('--candidate-map', type=Path)
    parser.add_argument('--baseline-only', action='store_true')
    parser.add_argument('--baseline-report', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.baseline_only != bool(args.candidate_map), 'Choose candidate comparison or explicit baseline-only')
    baseline, base_meta = metadata(args.baseline_map)
    try:
        commit = subprocess.check_output(['git', '-C', str(Path(__file__).resolve().parents[1]),
                                          'rev-parse', 'HEAD'], text=True).strip()
    except subprocess.CalledProcessError:
        commit = None
    report = {'status': 'BASELINE ONLY' if args.baseline_only else 'PASS', 'source_commit': commit,
              'boundary': __doc__, 'baseline': base_meta, 'cases': []}
    report['verification_tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if args.baseline_report:
        cached = json.loads(args.baseline_report.read_text())
        require(cached['status'] == 'BASELINE ONLY' and cached['baseline'] == base_meta
                and cached['verification_tool_sha256'] == report['verification_tool_sha256'],
                'Baseline cache does not match actual MPQ or exact verifier source')
        before = cached['baseline_cases']
    else:
        before = cases(baseline)
    if args.baseline_only:
        report['baseline_cases'] = before
    else:
        candidate, candidate_meta = metadata(args.candidate_map)
        report['candidate'] = candidate_meta
        after = cases(candidate, candidate=True)
        for label, expected in before.items():
            actual = after[label]
            require(json.dumps(actual['trace'], sort_keys=True) == json.dumps(expected['trace'], sort_keys=True),
                    'Exact combat/state trace changed: '+label)
            require(actual['cleanup'] == expected['cleanup'], 'Final lifecycle cleanup differs: '+label)
            if label.startswith(('overlap-', 'mixed-')) or label == 'actual-seal-mechanic':
                count = 2 if label == 'actual-seal-mechanic' else int(label.split('-')[1])
                require(expected['steady']['slow_refresh'] == count*24, 'Baseline expected24 refresh per source failed')
                require(actual['steady']['slow_refresh'] == count*12 and actual['steady']['timed_new'] == 0
                        and actual['steady']['timed_destroy'] == 0 and actual['steady']['position_acquire'] == 0
                        and actual['steady']['position_release'] == 0, 'Candidate stable delta budget failed: '+label)
                if label == 'actual-seal-mechanic':
                    require(actual['steady']['weakening_new'] == 0 and actual['steady']['weakening_destroy'] == 0
                            and actual['steady']['weakening_offer'] == 24, 'Actual seal token was rebuilt rather than renewed')
            report['cases'].append({'case': label, 'trace_equal': True, 'baseline': expected, 'candidate': actual})
            print('zone packed verified', label, flush=True)
        report['compiled_mutations'] = mutations(candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(report['status'], len(report.get('cases', [])), 'zone cases', flush=True)


if __name__ == '__main__':
    main()
