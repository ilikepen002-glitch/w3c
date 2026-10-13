#!/usr/bin/env python3
"""Targeted actual-packed spirit terminal retention, cleanup and admission gate.

All ownership, admission, terminal decisions, cleanup and timer bodies execute the
supplied map's JASS through VerifyElementalVfxArtifact.VfxRuntime. Python observes
production fields and delivers controlled native clocks/handles/collections only.
No Warcraft rendering, particle-tail, attachment-quality or FPS claim is made.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re

from GenerateTowerTerrainMask import Mpq
from VerifyElementalVfxArtifact import VfxRuntime
from VerifyPetAttackArtifact import PetAttackRuntime, near
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerUpgradeArtifact import rawcode

TERMINAL = (21, 22, 24, 30, 31, 33, 34, 38)
ORDERS = ('visual-first', 'battle-first')
EPS = 1e-7


def function_body(script, name):
    m = re.search(r'^function '+re.escape(name)+r' takes [^\n]+\n(.*?)^endfunction', script, re.M | re.S)
    require(m is not None, 'Packed mutation owner missing: '+name)
    return m


def replace_body(script, name, change):
    m = function_body(script, name)
    old = m.group(1)
    new = change(old)
    require(new != old, 'Packed mutation root unchanged: '+name)
    return script[:m.start(1)] + new + script[m.end(1):]


def insert_statement(body, statement):
    lines = body.splitlines(True)
    i = next(i for i, line in enumerate(lines) if line.strip() and not line.lstrip().startswith('local '))
    lines.insert(i, statement)
    return ''.join(lines)


class RetentionRuntime(VfxRuntime):
    """Recorder only: never implements a production admission/ownership method."""
    def __init__(self, script, order='visual-first'):
        self.order = order
        self.handles = {}
        self.helper_calls = []
        self.finishes = []
        self.destructions = []
        self.adoptions = []
        self.context_ids = set()
        self.line_births = {}
        self.destroyed_groups = []
        self.damage_cancel = None
        self.on_stack_shutdown = False
        self.on_stack_result = None
        super().__init__(script)
        self.handles.clear()
        self.helper_calls.clear()
        self.finishes.clear()
        self.destructions.clear()
        self.adoptions.clear()

    def field(self, name, identity):
        return self.globals[name][identity]

    def context(self, identity):
        p = 'TDPetCastContext_'
        scalar = ('pet', 'host', 'skill', 'stage', 'markCount', 'visualSerial', 'createdAt',
                  'expiresAt', 'victimCount', 'visualSize', 'primary', 'candidates')
        result = {name: self.field(p+name, identity) for name in scalar}
        result['id'] = identity
        result['points'] = [self.field(p+'visuals_'+str(i), identity)
                            for i in range(result['visualSize'])]
        result['targets'] = [self.field(p+'targetPositions_'+str(i), identity)
                             for i in range(result['victimCount'])]
        result['victims'] = [self.field(p+'victims_'+str(i), identity)
                             for i in range(result['victimCount'])]
        return result

    def entries(self, serial=None, detached=None):
        result = []
        for identity in self.lists[self.globals['TDCombatVisualRuntime_castLines']]:
            row = {'id': identity}
            for name in ('serial', 'source', 'lane', 'epoch', 'expiresAt', 'line', 'art',
                         'detached', 'sourceKey', 'ownerSerial', 'petSerial',
                         'trial_epoch', 'trial_generation', 'trial_token', 'trial_fromTrial'):
                row[name] = self.field('TDVisualCastLine_'+name, identity)
            if serial is not None and row['serial'] != serial:
                continue
            if detached is not None and row['detached'] != detached:
                continue
            require(bool(row['art']) != bool(row['line']), 'Expiry entry does not own exactly one native handle')
            result.append(row)
        return result

    def execute_call(self, name, args):
        if name.startswith('TDPetCastContext_visual') or name in ('TDPetCastContext_retainVisuals',
                'tdCombatVisualAdoptPetPoint', 'tdCombatVisualRetainPetLines'):
            self.helper_calls.append({'time': self.now, 'name': name, 'args': list(args)})
        before = None
        if name in ('TDPetCastContext_visualFinish', 'TDPetCastContext_onDestroy'):
            before = self.context(args[0])
        add_before = sum(1 for h in self.handles.values() if h['created'] == self.now) if name == 'TDPetCastContext_visualFinish' else 0
        value = super().execute_call(name, args)
        if name == 'new_TDPetActiveCast' and value:
            self.context_ids.add(value)
        if name == 'new_TDVisualCastLine' and value and args[3]:
            self.line_births[args[3]] = args[4]
        if name == 'tdCombatVisualAdoptPetPoint':
            self.adoptions.append({'time': self.now, 'handle': args[3], 'deadline': args[4],
                                   'serial': args[0], 'accepted': bool(value)})
        if name == 'TDPetCastContext_visualFinish':
            after = self.context(args[0])
            require(sum(1 for h in self.handles.values() if h['created'] == self.now) == add_before,
                    'visualFinish created replacement native art')
            self.finishes.append({'time': self.now, 'before': before, 'after': after,
                                  'entries': self.entries(before['visualSerial'])})
        if name == 'TDVisualCastLine_onDestroy':
            self.assert_counts()
        if name == 'TDPetCastContext_onDestroy':
            after = self.context(args[0])
            index = self.tables[self.globals['TDPetCastContext_tdPetActiveCastIndex']]
            require(index.get(before['pet'], 0) != args[0], 'Context destruction retained active index')
            require(not after['pet'] and not after['host'] and not after['primary'],
                    'Context destruction retained combat references')
            require(not any(after['points']), 'Context destruction retained a native point slot')
            require(before['candidates'] in self.destroyed_groups, 'Context destruction omitted candidate-group release')
            for target in before['targets']:
                if target:
                    require(self.field('TDPetEffectTargetPosition_references', target) <= 0,
                            'Context destruction retained target-position ownership')
            for control in self.tables[self.globals['TDEnemyControlRuntime_byHandle']].values():
                require(not (self.field('TDEnemyControlWindow_source', control) == before['host'] and
                            self.field('TDEnemyControlWindow_sourceToken', control) == args[0]),
                        'Context destruction retained control token')
            if before['skill'] in (30, 37):
                for target in before['victims']:
                    record = self.invoke('tdAuraTargetFor', target)
                    if record:
                        for entry in self.lists[self.field('TDAuraTarget_timed', record)]:
                            require(self.field('TDAuraTimedContribution_source', entry) != before['host'],
                                    'Context destruction retained timed zone slow')
            self.destructions.append({'time': self.now, 'before': before, 'after': after,
                                      'entries': self.entries(before['visualSerial'])})
        return value

    def native(self, name, args):
        if name == 'ForForce':
            self.invoke(args[1]); return True, None
        if name == 'IsUnitType' and args[1] != self.globals.get('UNIT_TYPE_DEAD'):
            require(args[0] in self.units, 'Unknown native unit-type fixture')
            return True, False
        if name in ('group_destr', 'DestroyGroup'):
            self.destroyed_groups.append(args[0])
        if name == 'destroyLLIterator':
            require(args[0] in self.iterators, 'Unknown native iterator release')
            del self.iterators[args[0]]; return True, None
        if name == 'getElapsedGameTime' and self.on_stack_shutdown and self.globals.get('TDCombatVisualRuntime_executing'):
            # Deliver the requested shutdown at the actual cleanup turn's first
            # clock boundary, after executing=true and before any iterator opens.
            # Native DestroyEffect is not modeled as reentrant gameplay delivery.
            self.on_stack_shutdown = False
            self.invoke('tdCombatVisualShutdown')
            cb = self.globals['TDCombatVisualRuntime_cleanup']
            self.on_stack_result = {'executing': self.globals['TDCombatVisualRuntime_executing'],
                                    'callback': cb,
                                    'nativeTimerDestroyed': self.timers[self.globals['CallbackPeriodic_t'][cb]]['destroyed'] if cb else None}
        if name in ('DestroyEffect', 'DestroyLightning') and args[0] in self.handles:
            require(self.handles[args[0]]['destroyed'] is None, 'Recorded native handle destroyed twice')
            self.handles[args[0]]['destroyed'] = self.now
        handled, value = super().native(name, args)
        if name in ('AddSpecialEffect', 'AddSpecialEffectTarget', 'AddLightningEx') and value:
            self.handles[value] = {'handle': value, 'created': self.now, 'destroyed': None,
                                  'native': name, 'args': list(args),
                                  'phases': list(self.phase_stack)}
        if name == 'UnitDamageTarget' and self.damage_cancel:
            action = self.damage_cancel
            self.damage_cancel = None
            action()
        return handled, value

    def tick(self, elapsed=.05):
        # Both actual 0.05 closures execute; only their native delivery order changes.
        self.now = round(self.now+elapsed, 9)
        packages = ('TDCombatVisualRuntime', 'TDPetEffectScheduler')
        if self.order == 'battle-first':
            packages = packages[::-1]
        for package in packages:
            callbacks = self.periodic_callbacks(package)
            require(len(callbacks) <= 1, 'Multiple actual '+package+' cleanup timers')
            for cb in callbacks:
                self.executed_steps = 0
                self.invoke('call_doPeriodically_'+package, cb, cb)
        self.drain_zero()
        self.assert_counts()

    def assert_counts(self, borrowed=0):
        counters = ('TDCombatVisualRuntime_castVisualCount', 'TDCombatVisualRuntime_hitVisualCount',
                    'TDCombatVisualRuntime_retainedPetPointCount', 'TDPetCastContext_visualCount',
                    'TDCombatVisualRuntime_petBuffVisualCount')
        require(all(self.globals[n] >= 0 for n in counters), 'Negative actual visual ownership counter')
        tails = self.entries()
        require(self.invoke('tdCombatVisualRetainedPetPointCount') == sum(bool(e['art']) for e in tails),
                'Retained-point diagnostic differs from actual expiry entries')
        require(self.invoke('tdPetLiveEffectVisualCount') == self.globals['TDPetCastContext_visualCount']+sum(bool(e['art']) for e in tails),
                'Transferred pet point vanished from live-total diagnostic')
        require(self.invoke('tdPetLiveEffectVisualCount') <= 128, 'Pet native-point cap expanded')
        require(self.invoke('tdCombatVisualShortCount') <= 128, 'Shared short cap expanded')
        for source in self.lists[self.globals['TDCombatVisualRuntime_sources']]:
            serial = self.field('TDVisualSource_serial', source)
            count = sum(e['detached'] and e['ownerSerial'] == serial for e in tails)
            require(self.field('TDVisualSource_detachedCount', source) == count,
                    'Source detached counter lost owner-serial fencing')
        if not borrowed:
            gear = self.invoke('tdCombatVisualGearCount')
            null_moving = sum(not self.field('Fx_fx', self.field('TDVisualMoving_fx', entry))
                              for entry in self.lists[self.globals['TDCombatVisualRuntime_moving']])
            live = len(self.visual_handles)+len(self.lightning_handles)-gear+null_moving
            require(self.invoke('tdCombatVisualShortCount') == live,
                    'Shared admission released twice or failed to follow live handles')

    def expire(self, seconds=.35):
        for _ in range(math.ceil(seconds/.05)):
            self.tick()


def packed_contract(script):
    required = ('tdCombatVisualAdoptPetPoint', 'tdCombatVisualRetainPetLines',
                'tdCombatVisualRetainedPetPointCount', 'tdPetVisualTerminal',
                'TDPetCastContext_retainVisuals', 'TDVisualCastLine_valid')
    for name in required:
        require(re.search(r'^function '+name+r' takes ', script, re.M), 'Final map lacks packed retention production method '+name)
    for field in ('pet', 'context', 'target', 'candidates', 'victims', 'targetPositions', 'controlToken'):
        require(not re.search(r'^\s*\w+ array TDVisualCastLine_'+field+r'\b', script, re.M),
                'Retained entry stores gameplay identity '+field)
    r = RetentionRuntime(script)
    require(r.four_slot_contract, 'Retention fixtures require final legal four-slot contract')
    expected = {'TDCombatVisualData_TD_VISUAL_SHORT_LIMIT': 128,
                'TDCombatVisualData_TD_VISUAL_HIT_LIMIT': 32,
                'TDCombatVisualData_TD_VISUAL_NEW_PER_SECOND': 120,
                'TDCombatVisualData_TD_VISUAL_MOVING_LIMIT': 8,
                'TDPetCastContext_TD_PET_EFFECT_VISUAL_LIMIT': 128,
                'TDPetActiveVisualData_TD_PET_VISUAL_TERMINAL_DWELL': .25}
    for name, value in expected.items():
        near(r.globals[name], value, 'Packed bound '+name)
    return expected


def fixture(script, skill, order='visual-first', trial=False, empty=False):
    r = RetentionRuntime(script, order)
    if trial:
        r.enter(8)
    p = r.pet(skill)
    if trial:
        targets = [r.target(i) for i in range(5)]
        for target in targets:
            r.units[target].update(x=100., y=0.)
    else:
        targets = list(range(102, 116))
        for target in targets:
            r.enemy(target)
    r.visible_units = [] if empty else targets
    r.now = round(r.now+1., 9)
    return r, p, targets[0]


def begin(r, p, target):
    result = r.emit(100., target=target)
    index = r.tables[r.globals['TDPetCastContext_tdPetActiveCastIndex']]
    require(p in index, 'Legal original-hit fixture did not register actual cast context')
    return index[p], result


def complete(r, p, max_seconds=6.):
    limit = r.now+max_seconds
    index = r.tables[r.globals['TDPetCastContext_tdPetActiveCastIndex']]
    while p in index and r.now < limit:
        r.tick()
    require(p not in index, 'Actual cast did not terminate within its existing deadline')
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Terminal callback kept combat task alive for art')
    require(r.destructions, 'Actual combat destructor was not recorded')
    return r.destructions[-1]


def verify_one(script, skill, order='visual-first'):
    r, p, target = fixture(script, skill, order)
    context, original = begin(r, p, target)
    destruction = complete(r, p)
    finishes = [f for f in r.finishes if f['before']['id'] == context]
    require(len(finishes) == 1, 'Normal finish helper invocation missing/duplicated '+str(skill))
    finish = finishes[0]
    tails = finish['entries']
    points = [e for e in tails if e['art']]
    require(points, 'Delivered terminal points were not adopted '+str(skill))
    require(all(e['detached'] for e in tails), 'Terminal expiry entries were not detached')
    near(destruction['time'], finish['time'], 'Combat context destruction must share terminal callback')
    require(all(not x for x in finish['after']['points']), 'Successful transfer did not null context slots')
    for point in points:
        near(point['expiresAt'], finish['time']+.25, 'Exact admitted point dwell')
        require(point['art'] in r.visual_handles, 'Adopted point was destroyed with context')
    lines = [e for e in tails if e['line']]
    for line in lines:
        require(line['line'] in r.line_births, 'Original production line deadline was not recorded')
        near(line['expiresAt'], r.line_births[line['line']], 'Detached final line deadline was extended')
    r.assert_counts()
    r.expire(.35)
    for point in points:
        handle = r.handles[point['art']]
        require(handle['destroyed'] is not None, 'Admitted terminal point never expired')
        dwell = handle['destroyed']-finish['time']
        require(.25-EPS <= dwell <= .30+EPS, 'Terminal point lacks positive bounded .25-.30 lifetime')
    for line in lines:
        end = r.handles[line['line']]['destroyed']
        require(end is not None and line['expiresAt']-EPS <= end <= line['expiresAt']+.05+EPS,
                'Final line failed its original deadline')
    if skill == 24:
        cores = [h for h in r.handles.values() if 'TDPetCastContext_visualSeedSpread' in h['phases'] and h['native'] == 'AddSpecialEffect']
        require(len(cores) == 1 and cores[0]['args'][0].endswith('MoonWellTarget.mdx'), 'Seed third pulse/spread lacks one combined core')
        require(cores[0]['destroyed']-cores[0]['created'] > 0., 'Combined third seed cue was immediately cleared')
        third = cores[0]['created']
        primaries = [h for h in r.handles.values() if h['created'] == third and 'TDPetCastContext_visualSeedPulse' in h['phases']]
        require(not primaries, 'Third seed still allocated soon-to-be-cleared primary art')
    require(not r.entries(), 'Expired terminal entries remained in manager')
    require(not r.lists[r.globals['TDCombatVisualRuntime_sources']], 'Detached-only source was not reclaimed')
    require(r.globals['TDCombatVisualRuntime_cleanup'] == 0, 'Idle visual timer remained after tail expiry')
    r.flush_fx_recycle()
    require(r.fx_pool_size() == 48, 'Immediate moving destruction did not restore locked recycler')
    return {'skill': skill, 'order': order, 'finishAt': finish['time'],
            'contextDestroyedAt': destruction['time'], 'pointCount': len(points),
            'points': [{**e, 'nativeLifetime': r.handles[e['art']]['destroyed']-r.handles[e['art']]['created'],
                        'dwellAfterContext': r.handles[e['art']]['destroyed']-finish['time']} for e in points],
            'lines': lines, 'originalHit': original, 'poolAfter': r.fx_pool_size()}


def verify_lifetimes(script):
    result = []
    for order in ORDERS:
        for skill in TERMINAL:
            result.append(verify_one(script, skill, order))
            print('retention lifetime verified', skill, order, flush=True)
    return result


def abort_fixture(script, skill, point, order='visual-first'):
    r, p, target = fixture(script, skill, order)
    c, _ = begin(r, p, target)
    if skill == 38 and point == 'synchronous-final':
        # Leave spare real victim capacity, then deliver an as-yet unseen enemy
        # on the captured fourth road segment. Earlier native scans see only the
        # original primary; no hit counter or captured route is overwritten.
        r.visible_units = [target]
    if point == 'pre-final':
        r.invoke('TDPet_recall', p)
    elif point == 'synchronous-final':
        final_stage = {21: 3, 22: 3, 24: 5, 31: 3, 33: 3, 34: 3, 38: 3}.get(skill)
        limit = r.now+6.
        while r.now < limit:
            if skill == 30:
                ready = r.now+.05 >= r.field('TDPetCastContext_expiresAt', c)-EPS
            else:
                ready = r.field('TDPetCastContext_stage', c) == final_stage
            if ready:
                if skill == 38:
                    r.units[115].update(x=r.field('TDPetCastContext_road_fourth_x', c),
                                        y=r.field('TDPetCastContext_road_fourth_y', c))
                    r.visible_units.append(115)
                r.damage_cancel = lambda: r.invoke('TDPet_recall', p)
                break
            r.tick()
        require(r.damage_cancel is not None, 'Final damage cancellation fixture missed terminal stage')
        while p in r.tables[r.globals['TDPetCastContext_tdPetActiveCastIndex']] and r.now < limit:
            r.tick()
        require(r.damage_cancel is None, 'Final-hit cancellation did not run inside native damage '+str((skill, point, order)))
    elif point == 'target-loss':
        require(skill in (21, 31), 'Target-loss fixture must use real early-exit skill')
        r.units[target].update(alive=False, life=0.)
        # Single-target primary checks remain on the existing hit-due callback.
        # Brand31's first hit is at created+1; do not invent an earlier abort.
        complete(r, p)
    elif point == 'timeout':
        r.tick(6.)
    else:
        raise ValueError('Unknown abort fixture '+point)
    require(r.invoke('tdPetEffectTaskCount') == 0 and not r.entries(detached=True),
            'Abort path retained a combat task or detached terminal art '+str((skill, point, order)))
    require(not [a for a in r.adoptions if a['accepted']], 'Abort handed off admitted points '+str((skill, point, order)))
    r.invoke('tdCombatVisualShutdown')
    r.flush_fx_recycle()
    r.assert_counts()
    return {'skill': skill, 'point': point, 'order': order, 'detached': 0}


def verify_aborts(script):
    return [abort_fixture(script, skill, point, order) for order in ORDERS for skill in TERMINAL
            for point in ('pre-final', 'synchronous-final', 'timeout')]+[
                abort_fixture(script, skill, 'target-loss', order) for order in ORDERS for skill in (21, 31)]


def verify_delivered_target_death(script):
    rows = []
    for order in ORDERS:
        r, p, target = fixture(script, 31, order)
        c, _ = begin(r, p, target)
        while r.field('TDPetCastContext_stage', c) < 3:
            r.tick()
        r.damage_cancel = lambda: r.units[target].update(alive=False, life=0.)
        complete(r, p)
        require(r.damage_cancel is None and not r.units[target]['alive'], 'Delivered-target-death native fixture missed final hit')
        tails = r.entries(detached=True)
        require(tails, 'Delivered target death incorrectly aborted source-valid impact')
        r.tick()
        require(all(e['art'] in r.visual_handles for e in tails if e['art']), 'Delivered impact retained target validity after handoff')
        r.expire(); r.flush_fx_recycle(); r.assert_counts()
        rows.append({'order': order, 'deliveredImpactSurvivedTargetDeath': True, 'targetReferencesRetained': 0})
    return rows


def verify_explicit_cleanup(script):
    results = []
    for action in ('clear-pet', 'forget-source', 'clear-lane', 'shutdown', 'recall',
                   'invalidate', 'reroll', 'work-start', 'tower-removed', 'lane-defeat'):
        r, p, target = fixture(script, 30)
        begin(r, p, target); complete(r, p)
        tails = r.entries(detached=True)
        require(tails, 'Cleanup fixture lacks terminal tail')
        r.units[201] = {**r.units[101], 'abilities': {}, 'inventory': {}, 'owner': 1}
        other = r.invoke('tdCombatVisualNewSerial')
        require(r.invoke('tdCombatVisualCreateLine', other, 201, 1, 'DRAM', 0., 0., 45., 100., 0., 45., 1., 1., 1., 1., .25), 'Independent-source line fixture failed')
        other_handle = r.entries(other)[0]['line']
        r.units[202] = {**r.units[101], 'abilities': {}, 'inventory': {}, 'owner': 0}
        require(r.invoke('tdTryEnemyControlToken', 202, 102, 0, 1., rawcode('Pfr0'), 100, 852095, 999, rawcode('Bpfr')), 'Independent control fixture failed')
        control = r.tables[r.globals['TDEnemyControlRuntime_byHandle']][102]
        r.invoke('tdEnemySlowOfferTimed', 102, 202, r.globals['TDAuraRules_TD_AURA_PET_VORTEX'], 1, .20, 1.)
        r.invoke('tdCombatVisualRefreshGear', 101, 1, rawcode('iP01'), 0, 0)
        gear = next(h for h, row in r.handles.items() if row['native'] == 'AddSpecialEffectTarget' and row['args'][1] == 101 and row['destroyed'] is None)
        if action == 'clear-pet': r.invoke('tdCombatVisualClearPet', 101)
        elif action == 'forget-source': r.invoke('tdCombatVisualForgetSource', 101)
        elif action == 'clear-lane': r.invoke('tdCombatVisualClearLane', 0)
        elif action == 'shutdown': r.invoke('tdCombatVisualShutdown')
        elif action == 'recall': r.invoke('TDPet_recall', p)
        elif action == 'invalidate': r.invoke('TDPet_invalidateCombat', p)
        elif action == 'work-start':
            r.invoke('tdPetTowerWorkStarted', 101)
            for _ in range(2):
                r.invoke('tdPetTowerWorkFinished', 101)
                require(not any(e['serial'] == tails[0]['serial'] for e in r.entries()), 'Work cancel/finish resurrected old tail')
        elif action == 'tower-removed': r.invoke('tdPetTowerRemoved', 101)
        elif action == 'lane-defeat': r.invoke('tdPetLaneDefeated', 0)
        elif action == 'reroll':
            r.globals['TDPetState_tdPetRerollStones'][0] = 1
            require(r.invoke('tdPetBeginReroll', 0, 0, 3), 'Legal reroll fixture did not begin')
            require(r.invoke('tdPetResolveRerollVersion', 0, 0, r.field('TDPet_proposalVersion', p), True), 'Legal reroll fixture did not adopt')
        require(not any(e['serial'] == tails[0]['serial'] for e in r.entries()), 'Explicit cleanup returned with detached tail '+action)
        require(all(r.handles[e['art'] or e['line']]['destroyed'] == r.now for e in tails), 'Explicit cleanup delayed native destruction '+action)
        if action != 'shutdown':
            require(other_handle in r.lightning_handles, 'Unrelated owner was erased by '+action)
        require(r.field('TDEnemyControlWindow_sourceToken', control) == 999, 'Visual/pet cleanup erased another source control')
        aura = r.invoke('tdAuraTargetFor', 102)
        require(any(r.field('TDAuraTimedContribution_source', entry) == 202 for entry in r.lists[r.field('TDAuraTarget_timed', aura)]), 'Cleanup erased another source slow')
        if action in ('clear-pet', 'recall', 'invalidate', 'reroll', 'work-start', 'tower-removed', 'lane-defeat'):
            require(gear in r.visual_handles, 'Pet-only cleanup erased independent gear '+action)
        r.invoke('tdCombatVisualShutdown'); r.assert_counts(); r.flush_fx_recycle()
        results.append({'action': action, 'synchronous': True, 'otherSourcePreserved': action != 'shutdown'})
    return results


def verify_passive_cleanup(script):
    results = []
    for order in ORDERS:
        for action in ('host-death', 'host-removal', 'owner-transfer', 'lane-inactive', 'lane-defeat',
                       'lane-finish', 'epoch', 'trial-generation', 'trial-token', 'trial-deadline'):
            trial = action.startswith('trial-')
            r, p, target = fixture(script, 31, order, trial=trial)
            begin(r, p, target); complete(r, p)
            tails = r.entries(detached=True)
            require(tails, 'Passive cleanup fixture lacks retained points '+action)
            if action == 'host-death': r.units[101].update(alive=False, life=0.)
            elif action == 'host-removal': r.call('RemoveUnit', [101])
            elif action == 'owner-transfer': r.units[101]['owner'] = 1
            elif action == 'lane-inactive': r.invoke('tdSetLaneActive', 0, False)
            elif action == 'lane-defeat': r.invoke('tdSetLaneDefeated', 0, True)
            elif action == 'lane-finish': r.invoke('tdSetLaneFinished', 0, True)
            elif action == 'epoch': r.invoke('tdResetWaveFlowState')
            elif action == 'trial-generation': r.state_call('reset')
            elif action == 'trial-token': r.globals['TDTrialState_token'][r.state] += 1
            elif action == 'trial-deadline': r.globals['TDTrialState_deadline'][r.state] = r.now
            r.tick()
            require(not r.entries(detached=True), 'Next actual .05 tick retained invalid snapshot '+action)
            require(all(r.handles[e['art'] or e['line']]['destroyed'] is not None for e in tails), 'Passive invalidation leaked native handle')
            r.invoke('tdCombatVisualShutdown'); r.flush_fx_recycle(); r.assert_counts()
            results.append({'action': action, 'order': order, 'byNextQuantum': True})
    return results


def verify_owner_reuse(script):
    results = []
    for order in ORDERS:
        r, p, target = fixture(script, 31, order)
        begin(r, p, target); complete(r, p)
        old = r.entries(detached=True)
        old_owner = r.tables[r.globals['TDCombatVisualRuntime_sourceIndex']][101]
        old_serial = r.field('TDVisualSource_serial', old_owner)
        # Low-level identity adversary: execute the real source destructor without
        # public clearDetached, then reuse its freed class ID/native source handle.
        # Normal public ForgetSource is separately covered above.
        r.invoke('dispatch_LinkedList_LinkedList_remove', r.globals['TDCombatVisualRuntime_sources'], old_owner)
        r.invoke('destroyTDVisualSource', old_owner)
        r.invoke('tdCombatVisualStartPetBuff', 101, 0, 11, r.now+6.)
        owner = r.tables[r.globals['TDCombatVisualRuntime_sourceIndex']][101]
        require(owner == old_owner and r.field('TDVisualSource_serial', owner) != old_serial, 'Source fixture did not reuse class ID with fresh monotonic serial')
        # Advance source pet generation independently, while the old entries still
        # exist. Validity must reject them and destruction must not touch new count.
        r.tick()
        require(not r.entries(detached=True), 'Old tail was accepted by reused source/class identity')
        require(r.field('TDVisualSource_detachedCount', owner) == 0, 'Old destructor decremented fresh owner count')
        require(r.globals['TDCombatVisualRuntime_petBuffVisualCount'] == 1, 'Stale owner cleanup removed new buff')
        r.invoke('tdCombatVisualClearPet', 101); r.invoke('tdCombatVisualClearPet', 101)
        r.invoke('tdCombatVisualShutdown'); r.assert_counts(); r.flush_fx_recycle()
        results.append({'order': order, 'classIdReused': owner, 'oldSerial': old_serial,
                        'freshSerial': r.field('TDVisualSource_serial', owner), 'staleEntriesRejected': len(old)})
    # Normal recall/rebind removes tails, allows an immediate new eligible context
    # and never blocks the new active index on an old detached visual serial.
    r, p, target = fixture(script, 21)
    begin(r, p, target); complete(r, p)
    old = r.entries(detached=True)
    r.invoke('TDPet_recall', p)
    r.globals['TDPet_host'][p] = 101
    r.globals['TDPet_readyAt'][p] = r.now
    begin(r, p, target)
    require(not any(e['serial'] == old[0]['serial'] for e in r.entries()), 'Rebound pet inherited old detached serial')
    r.invoke('TDPet_recall', p); r.invoke('tdCombatVisualShutdown'); r.flush_fx_recycle(); r.assert_counts()
    return results


def verify_serial_exhaustion(script):
    rows = []
    for order in ORDERS:
        for when in ('before-start', 'before-transfer'):
            r, p, target = fixture(script, 31, order)
            if when == 'before-start': r.globals['TDCombatVisualRuntime_serialCounter'] = 2147483647
            begin(r, p, target)
            if when == 'before-transfer':
                r.invoke('tdCombatVisualForgetSource', 101)
                r.globals['TDCombatVisualRuntime_serialCounter'] = 2147483647
            complete(r, p)
            require(not r.entries(detached=True), 'Serial exhaustion wrapped or retained unowned tail')
            require(r.invoke('tdCombatVisualNewSerial') == 0, 'Exhausted allocator wrapped serial')
            require(r.globals['TDCombatVisualRuntime_serialCounter'] == 2147483647, 'Serial exhaustion changed allocator identity')
            r.invoke('tdCombatVisualShutdown'); r.flush_fx_recycle(); r.assert_counts()
            rows.append({'when': when, 'order': order, 'zeroTail': True})
    return rows


def verify_partial_transfer(script):
    # Inject only the production adoption admission decision: after its first
    # accepted point, later points fail. Context nulling/destructor/manager remain
    # unmodified and execute exactly as packed, proving one owner on both paths.
    changed = replace_body(script, 'tdCombatVisualAdoptPetPoint', lambda body: insert_statement(body,
        '    if TDCombatVisualRuntime_retainedPetPointCount > 0 then\n        return false\n    endif\n'))
    r, p, target = fixture(changed, 31)
    begin(r, p, target); destruction = complete(r, p)
    accepted = [a for a in r.adoptions if a['accepted']]
    rejected = [a for a in r.adoptions if not a['accepted'] and a['handle']]
    require(len(accepted) == 1 and len(rejected) == 2, 'Partial transfer fixture did not split1 accepted/2 rejected native handles')
    require(accepted[0]['handle'] in r.visual_handles, 'Partial success was destroyed with context')
    require(all(r.handles[a['handle']]['destroyed'] == destruction['time'] for a in rejected), 'Failed adoption escaped ordinary immediate destruction')
    r.assert_counts(); r.expire(); r.flush_fx_recycle(); r.assert_counts()
    return {'accepted': 1, 'failedImmediate': 2, 'oneOwnerPerHandle': True}


def suppress_primary_optional(r):
    # Execute the ordinary source cooldown path then clear its owned art. It does
    # not change combat; nextHitVisualAt prevents the same callback's optional hit
    # from consuming the one scarce slot before the actual active fixture starts.
    r.invoke('tdCombatVisualHit', 101, 0., 0., 100., 0., 1, 0, False)
    r.invoke('tdCombatVisualClearPet', 101)


def saturate(r, count):
    acquired = 0
    while acquired < count:
        if r.invoke('tdCombatVisualAcquireCast'):
            acquired += 1
        else:
            require(r.invoke('tdCombatVisualShortCount') < 128, 'Saturation fixture exceeded desired shared count')
            r.now = float(int(r.now)+1)
    return acquired


def moving_fixture(r, count, clear=False):
    r.units[201] = {**r.units[101], 'abilities': {}, 'inventory': {}}
    serials = [r.invoke('tdCombatVisualNewSerial') for _ in range((count+1)//2)]
    for i in range(count):
        require(r.invoke('tdCombatVisualCreateMoving', serials[i//2], i%2, 201, 0,
                         'war3mapImported\\TDPetVfxSwordArray.mdx', 100., 0., 100., 0., .75),
                'Actual moving admission fixture did not fill requested capacity')
    if clear:
        for serial in serials: r.invoke('tdCombatVisualClearMoving', serial)
    return serials


def verify_core_admission(script):
    rows = []
    modes = ('normal', 'null', 'moving-live', 'moving-rate', 'moving-one', 'global-full', 'partial-one')
    for skill in (29, 33, 35):
        for mode in modes:
            r, p, target = fixture(script, skill)
            # All modes start at the same integer clock. Rate/live priming happens
            # one second earlier where required, through actual admission only.
            r.now -= 1.
            blockers = []
            borrowed = 0
            if mode in ('moving-live', 'moving-one'):
                blockers = moving_fixture(r, 8 if mode == 'moving-live' else 7)
            r.now += 1.
            if mode == 'moving-rate': blockers = moving_fixture(r, 8, clear=True)
            if mode == 'null': r.reject_visual = True
            if mode in ('global-full', 'partial-one'):
                # Align scarce-mode clocks after saturating actual production APIs.
                r.now -= 1.
                borrowed = saturate(r, 128 if mode == 'global-full' else 127)
                r.now = 11.
            if mode == 'partial-one': suppress_primary_optional(r)
            # Tokens deliberately have no native handles; each is actually admitted
            # and returned at the end, never a fake-list or fake-global fixture.
            original_assert = r.assert_counts
            if borrowed:
                r.assert_counts = lambda: original_assert(borrowed=borrowed)
            c, original = begin(r, p, target)
            prepare = [h for h in r.handles.values() if 'TDPetCastContext_visualPrepare' in h['phases'] or 'TDPetCastContext_visualStrike' in h['phases']]
            if skill == 35: r.tick()
            else: r.tick(.60 if skill == 29 else .75)
            prepare = [h for h in r.handles.values() if 'TDPetCastContext_visualPrepare' in h['phases'] or 'TDPetCastContext_visualStrike' in h['phases']]
            fallback = {29: 'BlizzardTarget.mdx', 33: 'FireBallMissile.mdx', 35: 'TDPetVfxFaultRidge.mdx'}[skill]
            native_core = [h for h in prepare if h['native'] == 'AddSpecialEffect' and h['args'][0].endswith(fallback)]
            moving_core = [h for h in prepare if h['native'] == 'AddSpecialEffectTarget' and h['args'][0].endswith(fallback)]
            if mode in ('moving-live', 'moving-rate'):
                require(native_core, 'Moving denial lost authored native core '+str(skill)+' '+mode)
                first = min(prepare, key=lambda h: (h['created'], h['handle']))
                require(first['args'][0].endswith(fallback), 'Optional ornament preceded denied-moving core '+str(skill))
            if mode == 'normal':
                require(len(moving_core) == (2 if skill == 29 else 1), 'Normal moving core count changed '+str(skill))
            if mode == 'moving-one' and skill == 29:
                freeze_core = [h for h in r.handles.values() if 'TDPetCastContext_visualFreeze' in h['phases'] and h['native'] == 'AddSpecialEffect' and h['args'][0].endswith(fallback)]
                require(len(moving_core) == 1 and len(native_core) == 1 and len(freeze_core) == 1, 'One-moving mirror did not keep its native preparation/freeze core')
            if mode in ('global-full', 'null'):
                require(not prepare, 'Global/native denial bypassed ordinary admission '+str(skill))
            complete(r, p)
            r.expire()
            r.invoke('tdCombatVisualShutdown')
            for _ in range(borrowed): r.invoke('tdCombatVisualReleaseCast')
            r.assert_counts = original_assert
            r.assert_counts(); r.flush_fx_recycle()
            rows.append({'skill': skill, 'mode': mode, 'nativeCore': len(native_core),
                         'movingCore': len(moving_core), 'originalHit': original, 'ordinaryAdmissionPreserved': True})
        # Empty area still has a central freeze boundary when both moving cores
        # are denied. The original primary remains a legal enemy but is excluded
        # only from the native enum boundary's target list.
        if skill == 29:
            r, p, target = fixture(script, skill, empty=True)
            r.now -= 1.; moving_fixture(r, 8); r.now += 1.
            begin(r, p, target); r.tick(.60)
            cores = [h for h in r.handles.values() if 'TDPetCastContext_visualFreeze' in h['phases'] and h['native'] == 'AddSpecialEffect' and h['args'][0].endswith('BlizzardTarget.mdx')]
            require(cores, 'Moving-denied empty mirror area omitted central freeze cue')
            complete(r, p); r.invoke('tdCombatVisualShutdown'); r.flush_fx_recycle(); r.assert_counts()
            rows.append({'skill': 29, 'mode': 'empty-moving-denied', 'centralFreeze': len(cores)})
    return rows


def buff_fixture(script, skill):
    r = RetentionRuntime(script)
    p = PetAttackRuntime.pet(r, [(0, 1), (17, 1), (39, 1), (skill, 1)])
    r.now = 11.
    return r, p


def verify_buff_admission(script):
    rows = []
    for skill in (11, 12):
        for mode in ('normal', 'null', 'one-live', 'one-ticket', 'global-full', 'rate-full'):
            r, p = buff_fixture(script, skill)
            r.now = 19.10
            # Gear creates an independent persistent native handle before scarce
            # cast admissions. It must remain throughout clear/replace/null tests.
            r.invoke('tdCombatVisualRefreshGear', 101, 1, rawcode('iP01'), 0, 0)
            gear_before = r.invoke('tdCombatVisualGearCount')
            borrowed = 0
            if mode in ('one-live', 'global-full'):
                borrowed = saturate(r, 127 if mode == 'one-live' else 128)
            r.now = 20.10
            if mode in ('one-ticket', 'rate-full'):
                for _ in range(119 if mode == 'one-ticket' else 120):
                    require(r.invoke('tdCombatVisualAcquireCast'), 'Creation-ticket fixture failed actual admission')
                    r.invoke('tdCombatVisualReleaseCast')
            if mode == 'null': r.reject_visual = True
            gameplay_before = {'readyAt': r.globals['TDPet_readyAt'][p], 'until': r.globals['TDPet_buffUntil'][p],
                               'power': r.globals['TDPet_buffPower'][p], 'abilities': dict(r.units[101]['abilities']),
                               'score': r.score(), 'random': list(r.random_trace)}
            # Direct public API isolates attachment-first admission from the
            # separate optional ordinary-hit layer. No Python count/list override.
            r.invoke('tdCombatVisualStartPetBuff', 101, 0, skill, r.now+6.)
            buff = r.globals['TDCombatVisualRuntime_petBuffVisualCount']
            require(buff == (1 if mode in ('normal', 'one-live', 'one-ticket') else 0),
                    'Attachment did not own scarce admission before optional burst')
            events = [h for h in r.handles.values() if h['args'][0] == r.invoke('tdCombatVisualPetBuffModel', skill)]
            if buff:
                require(len(events) == 1 and events[0]['native'] == 'AddSpecialEffectTarget', 'Buff acquired wrong native attachment')
                owner = r.tables[r.globals['TDCombatVisualRuntime_sourceIndex']][101]
                near(r.field('TDVisualSource_petBuffUntil', owner), 26.10, 'Exact six-second visual attachment')
            gameplay_after = {'readyAt': r.globals['TDPet_readyAt'][p], 'until': r.globals['TDPet_buffUntil'][p],
                              'power': r.globals['TDPet_buffPower'][p], 'abilities': dict(r.units[101]['abilities']),
                              'score': r.score(), 'random': list(r.random_trace)}
            require(gameplay_after == gameplay_before, 'Direct cosmetic buff API altered CD/native bonuses/RNG')
            bursts = [h for h in r.handles.values() if h['args'][0] == r.invoke('tdCombatVisualPetBuffStartModel', skill)]
            if mode in ('one-live', 'one-ticket'):
                require(not bursts, 'Optional start burst stole scarce attachment ticket')
            if mode == 'null':
                require(r.globals['TDCombatVisualRuntime_castVisualCount'] == borrowed, 'Native-null attachment leaked acquired admission')
            r.reject_visual = False
            r.now = 21.10
            r.invoke('tdCombatVisualStartPetBuff', 101, 0, 12 if skill == 11 else 11, r.now+6.)
            require(r.globals['TDCombatVisualRuntime_petBuffVisualCount'] <= 1, 'Replacement buff created a second source attachment')
            r.invoke('tdCombatVisualClearPet', 101)
            require(r.invoke('tdCombatVisualGearCount') == gear_before, 'Buff clearing erased independent gear')
            r.invoke('tdCombatVisualShutdown')
            for _ in range(borrowed): r.invoke('tdCombatVisualReleaseCast')
            r.assert_counts()
            rows.append({'skill': skill, 'mode': mode, 'attachment': buff, 'startBurst': len(bursts),
                         'directPublicAPI': True, 'gearIndependent': True, 'gameplayUnchanged': True})
    # Persistent cap and source replacement use actual guarded production calls.
    r, _ = buff_fixture(script, 11)
    for i in range(41):
        host = 1000+i
        r.units[host] = {**r.units[101], 'abilities': {}, 'inventory': {}}
        r.invoke('tdCombatVisualStartPetBuff', host, 0, 11, 17.)
    require(r.globals['TDCombatVisualRuntime_petBuffVisualCount'] == 40, 'Persistent attachment cap40 changed')
    r.invoke('tdCombatVisualStartPetBuff', 1000, 0, 12, 17.)
    require(r.globals['TDCombatVisualRuntime_petBuffVisualCount'] == 40, 'Replacement attachment bypassed global40')
    r.invoke('tdCombatVisualShutdown'); r.assert_counts()
    return {'matrix': rows, 'globalCap': 40, 'onePerSource': True}


def verify_on_stack_cleanup(script):
    r, p, target = fixture(script, 31)
    begin(r, p, target); complete(r, p)
    r.on_stack_shutdown = True
    r.expire()
    require(r.on_stack_result and r.on_stack_result['executing'] and not r.on_stack_result['nativeTimerDestroyed'],
            'Shutdown released native timer while its cleanup callback was on stack')
    require(r.globals['TDCombatVisualRuntime_cleanup'] == 0 and not r.periodic_callbacks('TDCombatVisualRuntime'),
            'On-stack cleanup failed to stop idle timer after returning')
    require(not r.entries() and not r.visual_handles and not r.lightning_handles
            and r.invoke('tdCombatVisualShortCount') == 0 and r.invoke('tdPetLiveEffectVisualCount') == 0,
            'On-stack shutdown returned with detached native ownership')
    r.flush_fx_recycle(); r.assert_counts()
    return r.on_stack_result


def legal_lane_pet(r, lane, host, slot, skill=31):
    pet = r.invoke('new_TDPet', lane, (skill-19)//4*3+1, 1)
    require(r.invoke('tdPetStore', lane, pet), 'Forty-source legal collection admission failed')
    for index, (owned, quality) in enumerate(((0, 1), (17, 1), (39, 1), (skill, (skill-19)%4+1))):
        r.invoke('TDPet_setSkill', pet, index, owned, quality)
        require(r.invoke('TDPet_skillAt', pet, index) == owned, 'Stress fixture violated fixed four-slot roles')
    r.globals['TDPet_level'][pet] = 3
    r.globals['TDPet_host'][pet] = host
    r.globals['TDPet_generation'][pet] = 1
    require(r.invoke('tdPetBindingValid', pet, host, 1), 'Stress native host/lane binding invalid')
    return pet


def verify_overlap_stress(script):
    rows = []
    for order in ORDERS:
        r = RetentionRuntime(script, order)
        r.now = 20.10
        pets = []
        targets = []
        for lane in range(4):
            for slot in range(10):
                host = 1000+lane*10+slot
                target = 2000+lane*10+slot
                r.units[host] = {**r.units[101], 'owner': lane, 'lane': lane, 'abilities': {}, 'inventory': {}}
                r.enemy(target, x=100., lane=lane)
                pets.append((legal_lane_pet(r, lane, host, slot), host, target))
                targets.append(target)
        r.visible_units = targets
        peaks = {'shared': 0, 'nativePet': 0, 'entries': 0}
        for pet, host, target in pets:
            r.emit(100., source=host, target=target)
        index = r.tables[r.globals['TDPetCastContext_tdPetActiveCastIndex']]
        require(len(index) == 40, 'Forty legal sources did not register forty production casts')
        first_completion = None
        while index and r.now < 26.:
            r.tick()
            peaks['shared'] = max(peaks['shared'], r.invoke('tdCombatVisualShortCount'))
            peaks['nativePet'] = max(peaks['nativePet'], r.invoke('tdPetLiveEffectVisualCount'))
            peaks['entries'] = max(peaks['entries'], len(r.entries()))
            if r.destructions and first_completion is None:
                first_completion = r.now
        require(not index and r.invoke('tdPetEffectTaskCount') == 0, 'Stress kept combat context alive for tail')
        require(first_completion is not None and r.entries(detached=True), 'Stress never observed overlapping delivered terminal tails')
        require(len(r.lists[r.globals['TDCombatVisualRuntime_sources']]) <= 40, 'Stress invented unbounded source owners')
        # New eligible attacks during the retained .25 interval. Actual cooldown
        # boundary is set as the native fixture clock input; new original-hit
        # packets and the real active-index admission execute unchanged.
        before = len(r.native_damage)
        for pet, host, target in pets[:4]:
            r.globals['TDPet_readyAt'][pet] = r.now
            r.emit(100., source=host, target=target)
            require(pet in index, 'Old visual tail blocked a new eligible active index')
        r.tick()
        require(len(index) == 4 and r.invoke('tdPetEffectTaskCount') == 4, 'Subsequent attacks were blocked during terminal dwell')
        for pet, _, _ in pets: r.invoke('TDPet_recall', pet)
        r.invoke('tdCombatVisualShutdown'); r.assert_counts(); r.flush_fx_recycle()
        require(not r.entries() and not r.lists[r.globals['TDCombatVisualRuntime_sources']], 'Stress cleanup retained owners')
        # Bucket production field increments, recorded at actual calls, remain
        # constrained even across the integer-second reset. Creations include
        # prior Fx pool initialization only if recorded; it is cleared at init.
        buckets = {}
        for handle in r.handles.values():
            window = int(handle['created'])
            buckets[window] = buckets.get(window, 0)+1
        require(all(count <= 120 for count in buckets.values()), 'Stress exceeded existing native creation windows')
        require(r.fx_pool_size() == 48 and not r.periodic_callbacks('TDCombatVisualRuntime'), 'Stress left cleanup/recycler active')
        rows.append({'order': order, 'legalSources': 40, 'overlapPeaks': peaks,
                     'nativeCreationsByIntegerSecond': buckets, 'newAttacksDuringDwell': 4,
                     'singleVisualTimerMax': 1, 'poolAfter': 48})
    return rows


def verify_caps(script):
    r = RetentionRuntime(script)
    start = r.now
    accepted = sum(r.invoke('tdCombatVisualAcquireCast') for _ in range(121))
    require(accepted == 120, 'Actual creation bucket cap120 expanded')
    r.now = start+1.
    accepted += sum(r.invoke('tdCombatVisualAcquireCast') for _ in range(9))
    require(accepted == 128 and not r.invoke('tdCombatVisualAcquireCast'), 'Actual shared short cap128 expanded')
    for _ in range(accepted): r.invoke('tdCombatVisualReleaseCast')
    r.assert_counts()
    # Per-cast native bound is exercised through the actual legal context helper.
    r, p, target = fixture(script, 31)
    c, _ = begin(r, p, target)
    r.invoke('TDPetCastContext_clearVisuals', c)
    for _ in range(9): r.invoke('TDPetCastContext_addVisual', c, 'Abilities\\Weapons\\Rifle\\RifleImpact.mdx', 100., 0.)
    require(r.field('TDPetCastContext_visualSize', c) == 8, 'Actual per-cast eight-handle cap expanded')
    r.invoke('TDPet_recall', p); r.invoke('tdCombatVisualShutdown'); r.flush_fx_recycle(); r.assert_counts()
    return {'creation': 120, 'shared': 128, 'petNative': 128, 'perCast': 8, 'moving': 8}


def reject_mutations(script):
    cases = []
    def test(name, changed, check, expected_fragment):
        try:
            check(changed)
        except (ValueError, AssertionError) as error:
            fragments = (expected_fragment,) if isinstance(expected_fragment, str) else expected_fragment
            require(any(fragment in str(error) for fragment in fragments), 'Mutation '+name+' failed for unrelated reason: '+str(error))
            cases.append({'mutation': name, 'rejected': True, 'reason': str(error)})
        else:
            raise ValueError('Packed mutation escaped oracle: '+name)
    test('disabled-adoption', replace_body(script, 'tdCombatVisualAdoptPetPoint', lambda b: insert_statement(b, '    return false\n')),
         lambda s: verify_one(s, 31), 'Delivered terminal points were not adopted')
    anchor = 'set TDPetActiveVisualData_TD_PET_VISUAL_TERMINAL_DWELL = 0.25'
    require(script.count(anchor) == 1, 'Exact compiled dwell mutation root changed')
    test('zero-dwell', script.replace(anchor, anchor.replace('0.25', '0.0'), 1),
         lambda s: verify_one(s, 31), 'Delivered terminal points were not adopted')
    test('blanket-false-result-terminal', replace_body(script, 'tdPetVisualTerminal', lambda b: insert_statement(b, '    return true\n')),
         lambda s: abort_fixture(s, 31, 'target-loss'), 'Abort path retained')
    def extend_line(body):
        pattern = r'(^\s*call dispatch_TDVisualCastLine_TDVisualCastLine_detach\((\w+),[^\n]*\n)'
        return re.sub(pattern, lambda m: m.group(1)+'    set TDVisualCastLine_expiresAt['+m.group(2)+'] = getElapsedGameTime() + 0.25\n', body, count=1, flags=re.M)
    test('extended-original-line-deadline', replace_body(script, 'tdCombatVisualRetainPetLines', extend_line),
         lambda s: verify_one(s, 21), 'Detached final line deadline was extended')
    test('missing-context-index-cleanup', replace_body(script, 'TDPetCastContext_onDestroy', lambda b: re.sub(r'^\s*call dispatch_Table_Table_removeInt\(TDPetCastContext_tdPetActiveCastIndex[^\n]*\n', '', b, count=1, flags=re.M)),
         lambda s: verify_one(s, 31), 'Context destruction retained active index')
    test('double-admission-release', replace_body(script, 'TDVisualCastLine_onDestroy', lambda b: b.replace('call tdCombatVisualReleaseCast()', 'call tdCombatVisualReleaseCast()\n    call tdCombatVisualReleaseCast()', 1)),
         lambda s: verify_one(s, 31), 'Shared admission released twice')
    test('missing-explicit-detached-clear', replace_body(script, 'tdCombatVisualClearPet', lambda b: re.sub(r'^\s*call clearDetached\([^\n]*\n', '', b, count=1, flags=re.M)),
         verify_explicit_cleanup, 'Explicit cleanup returned with detached tail')
    test('stale-owner-acceptance', replace_body(script, 'TDVisualCastLine_valid', lambda b: re.sub(r' and TDVisualSource_serial\[([^\]]+)\] == TDVisualCastLine_ownerSerial\[([^\]]+)\]', '', b, count=1)),
         verify_owner_reuse, 'Old tail was accepted')
    # Move the exact optional burst call before the persistent attachment's
    # admission. No other statements or numeric rules are touched.
    def reverse_buff(body):
        lines = body.splitlines(True)
        call = next((i for i, line in enumerate(lines) if line.strip().startswith('call addHitArt(')), None)
        require(call is not None, 'Buff-order mutation root changed')
        start = call
        while start > 0 and lines[start-1].strip().startswith('set tuple_argument'):
            start -= 1
        block = ''.join(lines[start:call+1])
        body = ''.join(lines[:start]+lines[call+1:])
        admission = re.search(r'^\s*if TDCombatVisualRuntime_petBuffVisualCount', body, re.M)
        require(admission is not None, 'Buff admission mutation root changed')
        return body[:admission.start()]+block+body[admission.start():]
    test('burst-before-attachment', replace_body(script, 'tdCombatVisualStartPetBuff', reverse_buff),
         verify_buff_admission, 'Attachment did not own scarce admission')
    for name, value, check, fragment in (
            ('TDCombatVisualData_TD_VISUAL_SHORT_LIMIT', 128, verify_caps, 'Actual shared short cap128'),
            ('TDCombatVisualData_TD_VISUAL_NEW_PER_SECOND', 120, verify_caps, 'Actual creation bucket cap120')):
        anchor = 'set '+name+' = '+str(value)
        require(script.count(anchor) == 1, 'Cap mutation root changed '+name)
        test('raised-'+name, script.replace(anchor, anchor.replace(str(value), str(value+1)), 1), check, fragment)
    test('raised-per-cast-native-limit', replace_body(script, 'TDPetCastContext_addVisual',
         lambda b: b.replace(' >= 8', ' >= 9', 1)), verify_caps,
         ('Actual per-cast eight-handle cap expanded', 'Packaged JASS error: Index out of Bounds'))
    for name, value in (('TDCombatVisualData_TD_VISUAL_HIT_LIMIT', 32),
                        ('TDCombatVisualData_TD_VISUAL_MOVING_LIMIT', 8),
                        ('TDPetCastContext_TD_PET_EFFECT_VISUAL_LIMIT', 128)):
        anchor = 'set '+name+' = '+str(value)
        require(script.count(anchor) == 1, 'Packed constant mutation root changed '+name)
        test('raised-'+name, script.replace(anchor, anchor.replace('= '+str(value), '= '+str(value+1)), 1),
             packed_contract, 'Packed bound '+name)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip-mutations', action='store_true', help='Development diagnostics only; delivery requires mutation checks.')
    parser.add_argument('--only', choices=('lifetimes', 'aborts', 'lifecycle', 'admission', 'mutations'), help='Narrow diagnostic rerun.')
    args = parser.parse_args()
    packed = args.map.read_bytes()
    script = Mpq(packed).extract('war3map.j').decode('utf-8')
    report = {'status': 'PASS', 'mapSHA256': hashlib.sha256(packed).hexdigest(),
              'packedJassSHA256': hashlib.sha256(script.encode()).hexdigest(),
              'gateSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'boundary': __doc__,
              'bounds': packed_contract(script), 'coverage': {}}
    suites = {
        'lifetimes': [('lifetimes', verify_lifetimes)],
        'aborts': [('aborts', verify_aborts), ('deliveredTargetDeath', verify_delivered_target_death)],
        'lifecycle': [('explicitCleanup', verify_explicit_cleanup), ('passiveCleanup', verify_passive_cleanup),
                      ('ownerReuse', verify_owner_reuse), ('serialExhaustion', verify_serial_exhaustion),
                      ('partialTransfer', verify_partial_transfer), ('onStackCleanup', verify_on_stack_cleanup), ('overlapStress', verify_overlap_stress)],
        'admission': [('coreAdmission', verify_core_admission), ('buffAdmission', verify_buff_admission), ('caps', verify_caps)],
        'mutations': [('compiledMutations', reject_mutations)]}
    for group, checks in suites.items():
        if args.only and args.only != group: continue
        if group == 'mutations' and args.skip_mutations: continue
        for name, check in checks:
            report['coverage'][name] = check(script)
            print('retention gate verified', name, flush=True)
    report['completeGate'] = args.only is None and not args.skip_mutations
    report['legalFixtureBoundary'] = 'All active battle fixtures use complete legal four-slot pets. Opening a fifth slot is impossible; the existing open-slot invalidation hook is source-fenced by the separate mechanics gate, not fabricated as an active-tail fixture.'
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'mapSHA256': report['mapSHA256'],
                      'completeGate': report['completeGate'], 'suites': list(report['coverage'])}, indent=2))


if __name__ == '__main__':
    main()
