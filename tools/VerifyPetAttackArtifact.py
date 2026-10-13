#!/usr/bin/env python3
"""Replay the exact packed spirit-passive/native damage chain, with explicit natives.

No formula-only Python substitute, Warcraft launch, FPS or native armor simulation.
D=40/100/160 are native post-armor event inputs; engine callbacks/life deduction,
clock, native handles/groups/orders and random values are controlled boundaries.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyEquipmentCombatReplay import EquipmentTrialRuntime
from VerifyTowerPlacementArtifact import unit_objects
from VerifyTowerUpgradeArtifact import rawcode
from VerifyBuilderControlDelta import allocations
from VerifyDamageRankingJass import functions
from VerifyPetUIArtifact import field_value, verify_skill_allowed, verify_phase_one_slots, verify_phase_one_preview


def near(actual, expected, label):
    require(math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-5), f'{label}: {actual}, expected {expected}')


class PetAttackRuntime(EquipmentTrialRuntime):
    def __init__(self, script):
        super().__init__(script)
        self.roll = .99
        self.emitted = []
        self.visible_units = []
        self.timer_trace = []
        self.pumping_zero = False
        self.auto_post = True
        self.final_catalog = self.globals.get('TDPetData_TD_PET_SKILL_COUNT') == 49
        self.visual_handles = {}
        self.lightning_handles = {}
        self.visual_serial = 100000
        self.initialize_match()
        self.timer_trace.clear()
        self.invoke('tdSetupDamageStatistics')
        self.invoke('tdPetSetupCombat')
        for host in (101,):
            self.units[host].update(abilities={}, inventory={}, x=0., y=0.)
        self.units[102].update(life=10000., maxLife=10000., userdata=100, wave=1, speed=260., defaultSpeed=260., x=0., y=0.)
        ledger = self.globals['TDDamageState_tdDamageLedger']
        self.ledger = ledger
        require(self.globals['DamageEvent_firstUnreducedListeners'][3] != 0 and
                self.globals['DamageEvent_firstUnreducedListeners'][4] != 0 and
                self.globals['DamageEvent_firstListeners'][3] != 0,
                'Actual early priority3 pet / priority4 ledger not registered')

    def native(self, name, args):
        if name == 'GetRandomReal': return True, self.roll
        if name == 'UnitDamageTarget' and getattr(self,'after_damage_action',None):
            handled,result=super().native(name,args)
            action=self.after_damage_action;self.after_damage_action=None
            if action=='gameover': self.invoke('tdSetGameOver',True)
            else: self.invoke('TDPet_recall',action)
            return handled,result
        if name == 'nullTimer': return False, None  # Execute the packed wrapper into doAfter(0).
        if name == 'doPeriodically':
            self.timer_serial += 1
            self.timers[self.timer_serial] = {'destroyed':False, 'closure':args[1], 'periodic':True}
            self.globals['CallbackPeriodic_t'][args[1]] = self.timer_serial
            self.periodics.append(tuple(args[:2])); return True, args[1]
        if name == 'doAfter':
            self.timer_serial += 1
            self.timers[self.timer_serial] = {'destroyed':False, 'closure':args[1]}
            self.globals['CallbackSingle_t'][args[1]] = self.timer_serial
            self.scheduled.append((args[0], args[1]))
            self.timer_trace.append(('schedule', args[0], args[1]))
            return True, args[1]
        if name == 'timer_release':
            require(args[0] in self.timers, 'Unknown controlled native closure timer')
            timer = self.timers[args[0]]
            callback = timer['closure']
            self.scheduled = [(delay, cb) for delay, cb in self.scheduled if cb != callback]
            timer['destroyed'] = True
            self.timer_trace.append(('release', callback))
            return True, None
        if name == 'dispatch_LinkedList_LinkedList_remove':
            values = self.lists[args[0]]
            if args[1] not in values: return True, False
            values.remove(args[1]); return True, True
        if name == 'dispatch_LinkedList_destroyLinkedList':
            # Stdlib destruction clears list nodes, not element objects. The
            # split case below separately proves each shot was destroyed first.
            require(args[0] in self.lists, 'Destroying unknown modeled list')
            del self.lists[args[0]]
            return True, None
        if name == 'dispatch_LinkedList_LinkedList_add_1':
            signature = self.functions[name][0]
            require(len(args) == len(signature) and len(args) in (2, 3), 'Packed list-add signature changed')
            require(len(args) == 2 or signature[1] in ('w__wurst_stackPos', 'stackPos'),
                    'Unknown packed generic list-add parameter')
            self.lists[args[0]].append(args[-1]); return True, None
        if name in ('AddSpecialEffect', 'AddSpecialEffectTarget'):
            self.visual_serial += 1
            self.visual_handles[self.visual_serial] = tuple(args[:3])
            return True, self.visual_serial
        if name == 'AddLightningEx':
            self.visual_serial += 1
            self.lightning_handles[self.visual_serial] = tuple(args)
            return True, self.visual_serial
        if name == 'SetLightningColor':
            require(args[0] in self.lightning_handles, 'Unknown lightning color owner')
            return True, True
        if name == 'DestroyLightning':
            require(args[0] in self.lightning_handles, 'Unknown/double-owned lightning destruction')
            del self.lightning_handles[args[0]]; return True, True
        if name == 'vec2_getTerrainZ':
            # Actual native terrain height is a controlled flat-map boundary.
            require(name in self.functions and len(args) in (2, 3), 'Unknown terrain tuple lowering')
            return True, 0.0
        if name == 'DestroyEffect':
            require(args[0] in self.visual_handles, 'Unknown/double-owned visual destruction')
            del self.visual_handles[args[0]]; return True, None
        if name == 'SetUnitAcquireRange':
            self.units[args[0]]['acquireRange'] = args[1]; return True, None
        if name in ('tdPetOnSplitArrowImpact', 'tdPetOnCorpseExplosion'):
            return False, None
        return super().native(name, args)

    def run_timer(self, callback):
        self.scheduled = [(delay, cb) for delay, cb in self.scheduled if cb != callback]
        self.timer_trace.append(('run', callback))
        result = super().run_timer(callback)
        # ClosureTimers' native expired-timer bridge destroys CallbackSingle
        # AFTER its real captured call. Execute that exact packed destructor too.
        if self.globals['CallbackSingle_typeId'][callback] != 0:
            self.invoke('dispatch_CallbackSingle_destroyCallbackSingle', callback)
        return result

    def drain_zero(self):
        # Native timer delivery is modeled, not replaced by a synchronous onDamage call.
        # Equal deadlines are deliberately registration-ordered. Thus an early zero
        # pet timer reproduces the regression before the library's later nullTimer.
        if self.pumping_zero:
            return
        self.pumping_zero = True
        try:
            count = 0
            while any(delay == 0. for delay, _ in self.scheduled):
                index = next(i for i, (delay, _) in enumerate(self.scheduled) if delay == 0.)
                _, callback = self.scheduled.pop(index)
                self.run_timer(callback)
                count += 1
                require(count <= 500, 'Zero-deadline callback chain exceeded bounded replay')
        finally:
            self.pumping_zero = False

    def emit(self, amount, source=101, target=102):
        if amount < 0.:
            # Native spell state-trigger delivery remains an explicit boundary of
            # the existing harness; all original attacks/additions here are physical.
            result = super().emit(amount, source, target)
            self.emitted.append((source, target, result.copy()))
            return result
        self.event_amount, self.event_source, self.event_target = amount, source, target
        before = self.globals['DamageInstance_maxIndex']
        self.invoke('DamageEvent_onUnreducedDamage')
        instance = self.globals['DamageInstance_maxIndex']
        require(instance > before, 'Packed DamageEvent did not construct the physical event')
        result = {field: self.globals['DamageInstance_' + field][instance]
                  for field in ('amount', 'isCode', 'isSpell', 'id', 'lastDamageHP')}
        if 'DamageInstance_unreducedAmount' in self.globals:
            result['unreducedAmount']=self.globals['DamageInstance_unreducedAmount'][instance]
        else:
            require('DamageEvent_getUnreducedAmount' not in self.functions,
                    'Live unreduced getter lacks its packed backing field')
        require(not result['isSpell'], 'Positive native fixture unexpectedly became spell damage')
        if amount != 0.:
            self.units[target]['life'] = max(0., self.units[target]['life'] - amount)
            if self.units[target]['life'] <= 0.:
                self.units[target]['alive'] = False
        self.emitted.append((source, target, result.copy()))
        if self.auto_post:
            self.drain_zero()
        result['life'] = self.units[target]['life']
        self.events.append(('event', result))
        return result

    def pet(self, skills, host=101, slot=0, level=3):
        if self.final_catalog:
            active = [(skill, quality) for skill, quality in skills if self.invoke('tdPetSkillIsActive', skill)]
            passive = [(skill, quality) for skill, quality in skills if not self.invoke('tdPetSkillIsActive', skill)]
            require(len(active) <= 1 and len(passive) <= 3, 'Fixture exceeds one active/three passive contract')
            chosen = active[0] if active else (11, 1)
            element = self.invoke('tdPetSkillElement', chosen[0])
            species = (element - 1) * 3 + 1 if element else 1
            ordered = [chosen, *passive]
        else:
            species = 1
            ordered = [(0, 1), *skills]
        pet = self.invoke('new_TDPet', 0, species, 1)
        require(self.invoke('tdPetStore', 0, pet), 'Actual pet store fixture failed')
        for index, (skill, quality) in enumerate(ordered):
            self.invoke('TDPet_setSkill', pet, index, skill, quality)
            require(self.invoke('TDPet_skillAt', pet, index) == skill, 'Illegal fixture skill/slot')
            require(self.invoke('TDPet_qualityAt', pet, index) == quality, 'Illegal fixture quality')
        self.globals['TDPet_level'][pet] = level
        self.globals['TDPet_host'][pet] = host
        self.globals['TDPet_generation'][pet] = 1
        require(self.invoke('tdPetBindingValid', pet, host, 1), 'Actual pet binding gate rejected fixture')
        return pet

    def tick_effects(self, elapsed=.05):
        self.now += elapsed
        callbacks = [cb for interval, cb in self.periodics if interval == .05 and
                     self.globals['CallbackPeriodic_typeId'][cb] ==
                     allocations(self.script)['alloc_CallbackPeriodic_doPeriodically_TDPetEffectScheduler'][1]]
        require(len(callbacks) == 1, 'Final catalog must use one shared effect scheduler')
        self.invoke('call_doPeriodically_TDPetEffectScheduler', callbacks[0], callbacks[0])
        self.drain_zero()

    def score(self):
        return self.invoke('TDDamageLedger_playerTotal', self.ledger, 0)

    def flush(self):
        count = 0
        while any(delay <= 0.011 for delay, _ in self.scheduled):
            index = min((i for i, (delay, _) in enumerate(self.scheduled) if delay <= 0.011),
                        key=lambda i: (self.scheduled[i][0], i))
            _, callback = self.scheduled.pop(index)
            self.run_timer(callback)
            count += 1
            require(count <= 500, 'Short-deadline callback chain exceeded bounded replay')


def verify_native_critical_catalog(abilities, units, baseline=None):
    mounted = {ability for unit in units.values() for ability in unit.get('uabi', '').split(',') if ability}
    # Evolution attaches real abilities dynamically, not in static uabi.
    from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources, rawstring
    evaluator = SourceScalarEvaluator(read_sources())
    for choice in range(1, 6):
        for branch in (1, 2):
            replacement = evaluator.call('tdEvolutionSkillReplacement', [choice, branch])
            if replacement:
                mounted.add(rawstring(replacement))
    critical = set()
    for code in mounted:
        if code not in abilities or abilities[code][0] != 'AOcr':
            continue
        fields = abilities[code][1]
        level_fields = [value for (key, level, _), (_, value) in fields.items() if key == 'alev' and level == 0]
        require(len(level_fields) <= 1, code + ': ambiguous critical levels')
        levels = level_fields[0] if level_fields else 1
        if any(field_value(fields, 'Ocr1', level) > 0 for level in range(1, levels + 1)):
            critical.add(code)
    require(critical == {'A102', 'A112'}, 'Unclassified mounted native critical ability: ' + repr(critical))
    for code, multiplier, bonus in (('A102', 2.2, 18.0), ('A112', 2.64, 21.6)):
        require(abilities[code][0] == 'AOcr', code + ': native critical parent changed')
        near(field_value(abilities[code][1], 'Ocr1', 1), 25.0, code + ': native chance')
        near(field_value(abilities[code][1], 'Ocr2', 1), multiplier, code + ': native multiplier')
        near(field_value(abilities[code][1], 'Ocr3', 1), bonus, code + ': native bonus')
        if baseline is not None:
            require(abilities[code] == baseline[code], code + ': native critical fields changed')
    return sorted(critical)


def verify_resolve(script):
    records = []
    for quality in range(1, 5):
        for native in (40., 100., 160.):
            r = PetAttackRuntime(script); pet = r.pet([(17, quality)])
            before = r.score(); hp = r.units[102]['life']
            amounts = [r.emit(native)['amount'] for _ in range(10)]
            expected = native * (1.3 + .2 * quality)
            for index, amount in enumerate(amounts, 1):
                near(amount, expected if index in (5, 10) else native, 'Nth actual event amount')
            near(hp - r.units[102]['life'], native * 8 + expected * 2, 'Actual native compensation and HP')
            near(r.score() - before, native * 8 + expected * 2, 'Exactly-once real damage ledger')
            require(not r.native_damage, 'Resolve created a separate damageTarget segment')
            require(r.globals['TDPet_resolveRotation'][pet] == 0, 'Bounded tenth-hit counter')
            records.append({'quality': quality, 'native_D': native, 'fifth_tenth': expected})
    for critical in ('A102', 'A112'):
        r = PetAttackRuntime(script); pet = r.pet([(17, 4)])
        r.units[101]['abilities'][rawcode(critical)] = 1
        require(not r.invoke('tdPetSkillFitsHost', 17, 101), 'Native critical host shows compatible')
        for _ in range(10): near(r.emit(100.)['amount'], 100., 'Native critical untouched event')
        require(r.globals['TDPet_resolveRotation'][pet] == 0, 'Native critical advanced resolve')
    for blocked in ('paused', 'unbound', 'locked'):
        r = PetAttackRuntime(script)
        pet = r.pet([(16, 1), (17, 4)], level=1 if blocked == 'locked' else 3)
        if blocked == 'paused': r.globals['TDPet_paused'][pet] = True
        if blocked == 'unbound': r.globals['TDPet_host'][pet] = None
        for _ in range(5): near(r.emit(100.)['amount'], 100., 'Blocked resolve')
        require(r.globals['TDPet_resolveRotation'][pet] == 0, 'Blocked resolve counter')
    r = PetAttackRuntime(script); pet = r.pet([(17, 4)])
    for _ in range(4): r.emit(1.)
    score = r.score(); r.units[102]['life'] = 150.
    event = r.emit(100.)
    near(event['amount'], 210., 'Overkill final amount')
    near(r.score() - score, 150., 'Overkill pre-HP ledger cap')
    near(r.units[102]['life'], 0., 'Overkill HP')
    boss_physical=[]
    for wave in (8,16,24,32):
        r=PetAttackRuntime(script);pet=r.pet([(17,4)])
        r.units[102].update(type=rawcode(f'uB{wave:02d}'),life=10000.,maxLife=10000.,wave=wave,userdata=wave*100)
        r.invoke('tdSetupEnemyMechanics');r.invoke('tdEnemyMechanicRegister',102,0,wave,3)
        require(r.invoke('tdEnemyMechanicIsRegistered',102),'Actual Boss mechanic registration failed')
        r.globals['TDPet_resolveRotation'][pet]=4
        near(r.emit(100.)['amount'],210.,'Boss physical main must bypass spell resistance')
        near(r.units[102]['life'],9790.,'Boss physical resolve HP')
        boss_physical.append({'wave':wave,'physical_D':100.,'final_main':210.})
    # Final earth-rift's first85%D segment replaces retired active14's85%D case.
    # The same spell-wrapper/code-physical boundary must scale registered Boss once.
    r=PetAttackRuntime(script);pet=r.pet([(38 if r.final_catalog else 14,4)])
    r.units[102].update(type=rawcode('uB32'),life=10000.,maxLife=10000.,wave=32,userdata=3200)
    r.invoke('tdSetupEnemyMechanics');r.invoke('tdEnemyMechanicRegister',102,0,32,3)
    r.visible_units=[102];r.emit(100.);r.flush()
    if r.final_catalog:r.tick_effects()
    require(len(r.native_damage)==1,'Actual ground active lost its first spell segment')
    near(r.native_damage[0][2],49.3,'Active85%D times Boss32 factor0.58 once')
    near(r.units[102]['life'],9850.7,'Original100 plus once-scaled active49.3 HP')
    if r.final_catalog:
        r.invoke('TDPet_invalidateCombat',pet)
        require(r.invoke('tdPetEffectTaskCount')==0 and not r.visual_handles,'Boss first-stage fixture leaked later stages/visuals')
    return {'native_inputs':records,'native_critical_exclusions':2,'paused_unbound_locked':3,
            'overkill_cap':150.,'registered_Boss_physical_main':boss_physical,'registered_Boss_active_once':49.3,
            'spell_fixture':'Final skill38 first85%D stage; later stages explicitly cancelled' if r.final_catalog else 'Legacy skill14 single85%D stage'}


def verify_passives_and_sampling(script):
    r = PetAttackRuntime(script); pet = r.pet([(16, 4), (7, 4), (17, 4)])
    r.roll = 0.0
    for _ in range(20):
        r.emit(100.); r.flush()
    amounts = [hit[2] for hit in r.native_damage]
    require(amounts.count(100.) == 20 and sum(math.isclose(x, 85., abs_tol=1e-5) for x in amounts) == 5,
            'Combo/charge did not remain one original-D segment each')
    require(r.globals['TDPet_rotation'][pet] == 0 and r.globals['TDPet_resolveRotation'][pet] == 0,
            'Tagged additions recursively advanced pet counters')
    for _, _, event in r.emitted:
        if event['id'] == rawcode('Pdam'):
            require(event['isCode'] and not event['isSpell'], 'Physical additional lost Pdam/code classification')
    # Exact pre-hit boundaries and a primary hit crossing each boundary.
    cases = []
    for skill, life, expected in ((8,30.,50.), (8,30.01,0.), (8,35.,0.),
                                  (18,65.,0.), (18,65.01,30.), (18,70.,30.)):
        r = PetAttackRuntime(script); r.pet([(skill, 4)])
        r.units[102].update(life=life, maxLife=100.)
        r.emit(10.); r.flush()
        amounts = [hit[2] for hit in r.native_damage]
        require(len(amounts) == int(expected > 0), 'Pre-hit boundary extra segment count')
        if expected: near(amounts[0], expected / 10., 'Pre-hit fraction snapshot')
        cases.append({'skill':skill,'pre_life':life,'D':10.,'extra':expected/10.})
    # Real equipment priority1 snapshot must not inherit priority3 resolve.
    r = PetAttackRuntime(script); pet = r.pet([(17, 4)])
    r.inventory_items[90001] = rawcode('iP02'); r.units[101]['inventory'] = {0:90001}
    # iP02 is Boss-only; use an actual whitelisted Boss, not the ordinary uW01.
    r.units[102].update(type=rawcode('uB08'), life=2000., wave=8, userdata=800)
    r.invoke('tdSetupEquipmentCombat')
    r.globals['TDPet_resolveRotation'][pet] = 4
    score = r.score(); r.emit(100.); r.flush()
    near(r.emitted[0][2]['amount'], 210., 'Current amplified event')
    require(len(r.native_damage) == 1, 'Equipment extra count changed')
    near(r.native_damage[0][2], 25., 'Equipment sampled immutable 100 before resolve')
    near(r.score() - score, 235., 'Current + original-base equipment ledger')
    return {'twenty_hit_combo_segments':20,'charge_segments':5,'resolve_samples':4,
            'pre_hit_boundaries':cases,'equipment_priority1_extra':25.}


def verify_split_original_basis(script):
    r = PetAttackRuntime(script); r.invoke('init_TDTowerRuntime')
    r.units[101]['type'] = rawcode('uA6A')
    r.units[101]['abilities'][rawcode('A100')] = 1
    r.units[106] = {**r.units[102], 'abilities': {}, 'life': 10000., 'alive': True}
    pet = r.pet([(17, 4)]); r.globals['TDPet_resolveRotation'][pet] = 4
    shots = r.invoke('new_LinkedList')
    shot = r.invoke('new_TDArcherSplitArrowShot', 106, 0.)
    r.lists[shots].append(shot)
    volley = r.invoke('new_TDArcherSplitArrowVolley', 101, 102, 0., shots)
    r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']].append(volley)
    # Register the actual production callback class from its existing setup owner.
    setup = functions(script)['tdSetupDialogTrigger'][4]
    match = re.search(r'set (\w+) = (alloc_DamageListener_addListener_TDTowerRuntime)\(', setup)
    require(match is not None and re.search(r'call DamageEvent_addListener\(0, ' + re.escape(match[1]) + r'\)', setup), 'Original split listener wiring changed')
    listener = r.invoke(match[2]); r.invoke('construct_DamageListener', listener)
    r.invoke('DamageEvent_addListener', 0, listener)
    r.emit(100.)
    near(next(event['amount'] for _, target, event in r.emitted if target == 102 and event['id'] == 0), 210., 'Split host resolve primary')
    require(len(r.native_damage) == 1, 'Real split callback segment count')
    near(r.native_damage[0][2], 100., 'Split immutable originalD, not210')
    require(any(event['id'] == rawcode('Tspl') for _, _, event in r.emitted), 'Split lost original recursion-exclusion tag')
    require(r.globals['TDPet_resolveRotation'][pet] == 0, 'Split recursively advanced resolve')
    r.invoke('tdExpireArcherSplitArrowVolley', volley)
    require(not r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']], 'Consumed split volley leaked')
    require(r.globals['TDArcherSplitArrowShot_typeId'][shot] == 0 and
            r.globals['TDArcherSplitArrowVolley_typeId'][volley] == 0 and shots not in r.lists,
            'Consumed split shot/volley/list was not destroyed')
    return {'primary_final': 210., 'split_original_base': 100., 'tag': 'Tspl', 'pending_volley_count': 0,
            'fixture_boundary': 'Native pre-created volley/shot handles, production constructors, callback allocator/dispatch, consumption and damage execution; visual launching is outside this basis test.'}



def register_tower_listener(runtime, priority):
    setup = functions(runtime.script)['tdSetupDialogTrigger'][4]
    # Select an allocator only when the SAME typed temporary is passed to the
    # requested priority; do not manufacture a test-only corpse callback.
    matches = re.findall(r'set (\w+) = (alloc_DamageListener_addListener_TDTowerRuntime(?:_\d+)?)\([^\n]*\)'
                         r'(?:(?!set \1 =).)*?call DamageEvent_addListener\(' + str(priority) + r', \1\)', setup, re.S)
    require(len(matches) == 1, 'No unique real tower listener for priority ' + str(priority))
    listener = runtime.invoke(matches[0][1])
    runtime.invoke('construct_DamageListener', listener)
    runtime.invoke('DamageEvent_addListener', priority, listener)


def verify_phase_fence_source(sources=None):
    from VerifyActiveCooldownContract import read_sources, uncomment
    sources = read_sources() if sources is None else sources
    # The locked dependency skips all post listeners after abortCurrent. We do
    # not pretend to support it; any new production caller requires protocol review.
    for path, body in sources.items():
        require(not re.search(r'\babortCurrent\s*\(', uncomment(body)),
                'Production abort skips original post and requires phase-fence review: ' + path)
    combat = uncomment(sources['pets/TDPetCombat.wurst'])
    stable = ('return tdPetDamageSourceEligible(DamageEvent.isCode(), DamageEvent.isSpell(), '
              'DamageEvent.getId()) and DamageEvent.getUnreducedOriginalAmount() > 0.0')
    require(stable in combat, 'Original early/post stable predicate changed')
    require(combat.count('if tdPetOriginalPhaseEvent()') == 2 and
            combat.count('DamageEvent.addUnreducedListener(3)') == 1 and
            combat.count('DamageEvent.addListener(3)') == 1 and
            combat.count('tdPetBeginOriginalPhase()') == 1 and
            combat.count('tdPetEndOriginalPhase()') == 1,
            'Original phase listeners/predicate are not exactly paired')
    require('tdPetQueueAttack(pet castTo int)' in combat and 'doAfter(0.' not in combat,
            'Pet early capture bypassed the post-owned queue')
    queue = uncomment(sources['pets/TDPetAttackQueue.wurst'])
    require(queue.count('doAfter(') == 1 and
            'else if tdPetPendingOriginal == 0 and not queuedAttacks.isEmpty() and dispatchTimer == null' in queue and
            'while tdPetPendingOriginal == 0 and not queuedAttacks.isEmpty() and not tdIsGameOver()' in queue,
            'Queue dispatch lacks causal post wake or execution fence')
    if 'public function tdPetWakeIdleAttackQueue()' in queue:
        require(queue.count('tdPetWakeIdleAttackQueue()') == 3 and
                queue.index('queuedAttacks.add(new TDPetQueuedAttack(owner, callback))') <
                queue.index('tdPetWakeIdleAttackQueue()', queue.index('public function tdPetQueueAttack')) and
                'tdPetWakeIdleAttackQueue()' in queue[queue.index('public function tdPetEndOriginalPhase'):],
                'Queue idle/post wake ownership changed')
    require(queue.index('dispatchTimer = null', queue.index('function dispatchQueuedAttacks')) <
            queue.index('packet.callback.call()') and
            queue.index('queuedAttacks.remove(packet)', queue.index('function dispatchQueuedAttacks')) <
            queue.index('packet.callback.call()'), 'Dispatch is not consumed before reentrant callback')
    require('tdPetPendingOriginal = 0' not in queue[queue.index('function tdPetClearAttackQueue'):],
            'Cleanup erased in-flight original phases')
    runtime = uncomment(sources['pets/TDPetRuntime.wurst'])
    if 'tdPetShutdownEffects()' in runtime:
        require('doAfter(4.0)' not in runtime and
                runtime.index('tdPetClearAttackQueue()') < runtime.index('tdPetShutdownEffects()') <
                runtime.index('if not tdPetCanDestroyMatchRecords()') < runtime.index('destroy pet', runtime.index('tdPetShutdownEffects()')),
                'Match record destruction precedes explicit pending/effect cleanup')
        require('return tdPetEffectTaskCount() == 0 and tdPetPendingOriginal == 0 and not tdPetAttackQueueBusy()' in runtime and
                'dispatching = true' in queue and 'dispatching = false' in queue and
                queue.index('dispatching = true') < queue.index('packet.callback.call()') < queue.index('dispatching = false', queue.index('packet.callback.call()')),
                'Match destruction lost effect/original/current-packet idle proof')
    else:
        require(runtime.count('tdPetClearAttackQueue()') == 2 and
                runtime.index('tdPetClearAttackQueue()', runtime.index('doAfter(4.0)')) <
                runtime.index('destroy pet', runtime.index('doAfter(4.0)')),
                'Match record destruction can retain queued pet references')
    state = uncomment(sources['pets/TDPetState.wurst'])
    require(state.count('tdPetCancelQueuedAttacks(this castTo int)') == 2,
            'Pet invalidation/destruction lost owner queue cleanup')
    return True


def verify_phase_fence_compiled(script):
    require(not re.search(r'\bcall DamageEvent_abortCurrent\s*\(', script),
            'Packed production abort skips original post')
    all_functions = functions(script)
    predicate = all_functions['tdPetOriginalPhaseEvent'][4]
    for getter in ('DamageEvent_isCode', 'DamageEvent_isSpell', 'DamageEvent_getId',
                   'DamageEvent_getUnreducedOriginalAmount'):
        require(getter + '(' in predicate, 'Packed stable predicate lost ' + getter)
    require(not re.search(r'(?:tdPetForHost|tdPetBindingValid|unit_isAlive|GetUnitTypeId|GetOwningPlayer|DamageEvent_getAmount)\(', predicate),
            'Packed stable predicate depends on mutable target/binding/current amount')
    begin = [body[4] for body in all_functions.values() if 'call tdPetBeginOriginalPhase(' in body[4]]
    end = [body[4] for body in all_functions.values() if 'call tdPetEndOriginalPhase(' in body[4]]
    require(len(begin) == len(end) == 1 and 'tdPetOriginalPhaseEvent(' in begin[0] and
            'tdPetOriginalPhaseEvent(' in end[0], 'Packed listener pair changed')
    require(not re.search(r'(?:tdPetBindingValid|unit_isAlive|tdPetForHost)\(', end[0]),
            'Post fence checks a mutable binding/target')
    return {'production_abort_callers':0, 'stable_listener_pair':True}


def verify_post_timer_order(script):
    key = 'TDPetAttackQueue_tdPetPendingOriginal'
    queue_key = 'TDPetAttackQueue_queuedAttacks'
    if 'function tdPetHeroOnCorpseExplosionSettled takes' in script:
        require('function tdPetOnCorpseExplosion takes' not in script and
                not re.search(r'\btdPetOnCorpseExplosion\(', script),
                'Final retired corpse-pet helper still has a packed owner/caller')
        require('tdPetHeroOnCorpseExplosionSettled(' in functions(script)['tdHandleGhoulCorpseExplosionDamage'][4],
                'Final corpse settlement lost its actual production post branch')
        settled = 'tdPetHeroOnCorpseExplosionSettled'
    else:
        require('function tdPetOnCorpseExplosion takes' in script,
                'Neither reviewed corpse-settlement callback is packed')
        settled = 'tdPetOnCorpseExplosion'
    def pending(r): return r.globals[key]
    def queued(r): return len(r.lists[r.globals[queue_key]])
    def runtime(skills=((16,4),(7,4))):
        r=PetAttackRuntime(script);r.auto_post=False
        pet=r.pet(list(skills));r.roll=0.
        return r,pet
    def corpse(candidate):
        r=PetAttackRuntime(candidate);r.auto_post=False
        r.units[101]['type']=rawcode('uG6B')
        r.units[101]['abilities'][rawcode('A116')]=1
        r.units[102].update(life=250.,maxLife=1000.)
        r.units[106]={**r.units[102],'life':10000.,'maxLife':10000.,'abilities':{}}
        r.visible_units=[102,106]
        pet=r.pet([(16,4),(7,4)]);r.globals['TDPet_rotation'][pet]=3;r.roll=0.
        register_tower_listener(r,2)
        r.emit(100.)
        return r
    r=corpse(script)
    near(r.units[102]['life'],150.,'Native main leaves original HP150')
    require(pending(r)==1 and queued(r)==1 and not r.native_damage,
            'Early capture ran side effects before original post')
    original_post=r.scheduled[0][1]
    r.run_timer(original_post)
    require(pending(r)==0 and queued(r)==1 and not r.native_damage,
            'Post3 failed to release a deferred consumed queue')
    r.flush()
    near(r.units[102]['life'],0.,'Combo100 and charge85 subsequently kill')
    require(r.calls[settled]==0 and not any(hit[1]==106 for hit in r.native_damage),
            'Pet additions made original corpse listener misattribute the kill')
    # Explicitly attempt dispatch before original post, independent of timer
    # deadlines/FIFO. The real fence must preserve the entire unconsumed queue.
    r=corpse(script);r.invoke('dispatchQueuedAttacks')
    require(pending(r)==1 and queued(r)==1 and not r.native_damage,
            'A premature dispatcher crossed an in-flight original phase')
    # Read-only packed guard mutation demonstrates the exact 250/100 regression.
    body=functions(script)['dispatchQueuedAttacks'][4]
    changed,count=re.subn(r'\b'+key+r' == 0\b','true',body)
    require(count==1,'No unique packed dispatch execution fence')
    broken=corpse(script.replace(body,changed,1));broken.invoke('dispatchQueuedAttacks');broken.flush()
    require(broken.calls[settled]>0 and any(hit[1]==106 for hit in broken.native_damage),
            'Removing the compiled execution fence failed to expose corpse regression')
    # Two identical source/target/D native hits can post in reverse order. There
    # is no source/target/D matching, and no job executes after only one post.
    r,pet=runtime();r.globals['TDPet_rotation'][pet]=2
    r.emit(100.);r.emit(100.);posts=[cb for _,cb in r.scheduled]
    require(pending(r)==2 and queued(r)==2,'Identical originals did not capture two phases')
    r.run_timer(posts[1]);require(pending(r)==1 and not r.native_damage,'Reverse first post released work')
    r.run_timer(posts[0]);require(pending(r)==0 and not r.native_damage,'Last post ran work inline')
    r.flush()
    require(len(r.native_damage)==3 and pending(r)==0 and queued(r)==0,
            'Identical reverse posts lost/doubled combo or charge, or code recursion entered fence')
    # A no-pet original arriving between wake and dispatch still blocks the old
    # queued job. The attempted dispatch consumes no packet, and its post wakes anew.
    r,pet=runtime(((16,4),));r.emit(100.);r.run_timer(r.scheduled[0][1])
    dispatcher=r.scheduled[0][1]
    r.units[106]={**r.units[101],'abilities':{},'inventory':{}}
    r.emit(100.,source=106);new_post=r.scheduled[-1][1]
    r.run_timer(dispatcher)
    require(pending(r)==1 and queued(r)==1 and not r.native_damage,
            'A new no-pet original was ignored by dispatch fence')
    r.run_timer(new_post);r.flush()
    require(pending(r)==0 and queued(r)==0 and len(r.native_damage)==1,
            'No-pet post failed to wake old queued work')
    # Lifecycle/target state can change before post, but must never leak a phase.
    for action in ('recall','invalidate','destroy','dead_target','removed_target'):
        r,pet=runtime(((16,4),));r.emit(100.);post=r.scheduled[0][1]
        if action=='recall':r.invoke('TDPet_recall',pet)
        if action=='invalidate':r.invoke('TDPet_invalidateCombat',pet)
        if action=='destroy':r.invoke('dispatch_TDPet_destroyTDPet',pet)
        if action=='dead_target':r.units[102].update(life=0.,alive=False)
        if action=='removed_target':r.units[102].update(type=0,alive=False)
        r.run_timer(post);r.flush()
        require(pending(r)==0 and queued(r)==0 and not r.native_damage,
                'Mutable lifecycle/target caused phase leak: '+action)
    # Full code/spell/zero exclusions are checked elsewhere. A nested tagged code
    # event while an original is pending cannot consume that original's fence.
    r,pet=runtime(((16,4),));r.emit(100.);main_post=r.scheduled[0][1]
    r.invoke('DamageEvent_setNextDamageFromCode');r.invoke('DamageEvent_setNextDamageId',rawcode('Pdam'))
    r.emit(10.);code_post=r.scheduled[-1][1];r.run_timer(code_post)
    require(pending(r)==1,'Nested code post consumed native original phase')
    r.run_timer(main_post);r.flush();require(pending(r)==0,'Native post did not close after code recursion')
    # Terminal cleanup reclaims callbacks before records while retaining in-flight
    # phase count. A late real post decrements it naturally, without underflow.
    r,pet=runtime(((16,4),));r.emit(100.);post=r.scheduled[0][1]
    r.over=True;r.invoke('tdSetGameOver',True);r.invoke('tdPetClearAttackQueue')
    require(pending(r)==1 and queued(r)==0,'Terminal cleanup erased in-flight phase or retained packets')
    r.invoke('dispatch_TDPet_destroyTDPet',pet);r.run_timer(post)
    require(pending(r)==0 and not r.native_damage,'Late terminal post touched a retired pet or leaked phase')
    # Native damage can synchronously cause lifecycle work after the first extra.
    # The captured proc is consumed, but no stale buff/CD may be written afterwards.
    for action in ('gameover','recall'):
        r=PetAttackRuntime(script);pet=r.pet([(16,4),(11,4)]);r.roll=0.
        r.after_damage_action='gameover' if action=='gameover' else pet
        r.emit(100.);r.flush()
        near(r.globals['TDPet_readyAt'][pet],0.,'Synchronous '+action+' preserved active CD')
        near(r.globals['TDPet_buffUntil'][pet],0.,'Synchronous '+action+' rejected old buff')
        require(not r.globals['TDPet_pendingSkill'][pet],'Captured proc pending survived '+action)
    r=PetAttackRuntime(script)
    try:r.invoke('tdPetEndOriginalPhase')
    except ValueError as error:require('underflow' in str(error),'Unexpected underflow failure')
    else:raise ValueError('Original phase underflow did not fail closed')
    return {'native_pre_HP':250.,'native_D':100.,'original_post_HP':150.,'later_combo_charge':[100.,85.],
            'original_corpse_neighbour_hits':0,'compiled_execution_fence_mutation_reproduced':True,
            'same_source_target_D_reverse_posts':2,'new_no_pet_hit_before_dispatch':True,
            'lifecycle_or_target_changes':5,'nested_code_excluded':True,'terminal_late_post_closes':True,
            'underflow_fail_closed':True,'synchronous_extra_then_terminal_or_recall_blocks_old_active':2,
            'boundary':'Actual packed early/post/listener/queue/closure/destruction functions. Manual native timer deliveries explicitly reverse original posts and attempt dispatch before pending posts; these causal cases do not assume exact deadlines or FIFO. Default unrelated flush uses deadline/index order. No Warcraft timer observation.'}


def verify_source_rejection_and_cancellation(script):
    r = PetAttackRuntime(script); pet = r.pet([(7, 4), (17, 4)])
    for kind in ('code', 'spell', 'split', 'pet', 'zero'):
        if kind == 'code': r.invoke('DamageEvent_setNextDamageFromCode')
        if kind == 'split': r.invoke('DamageEvent_setNextDamageId', rawcode('Tspl'))
        if kind == 'pet': r.invoke('DamageEvent_setNextDamageId', rawcode('Pdam'))
        r.emit(-10. if kind == 'spell' else 0. if kind == 'zero' else 10.)
        require(r.globals['TDPet_rotation'][pet] == 0 and r.globals['TDPet_resolveRotation'][pet] == 0,
                'Non-original/zero event advanced attack counters: ' + kind)
        require(r.globals['TDPetAttackQueue_tdPetPendingOriginal']==0,
                'Excluded event left an unmatched original phase: '+kind)
    for action in ('TDPet_recall', 'TDPet_invalidateCombat', 'tdPetTowerWorkStarted'):
        r = PetAttackRuntime(script); pet = r.pet([(7, 4), (17, 4)])
        for _ in range(3): r.emit(1.)
        r.globals['TDPet_readyAt'][pet] = 99.
        r.invoke(action, 101 if action == 'tdPetTowerWorkStarted' else pet)
        require(r.globals['TDPet_rotation'][pet] == 0 and r.globals['TDPet_resolveRotation'][pet] == 0,
                'Lifecycle counter not reset: ' + action)
        near(r.globals['TDPet_readyAt'][pet], 99., 'Lifecycle preserved cooldown')
    # Captured additional damage cannot execute after a generation change.
    r = PetAttackRuntime(script); pet = r.pet([(16, 4)]); r.roll=0.;r.auto_post=False
    r.emit(100.); require(r.scheduled, 'No real queued additional callback')
    r.invoke('TDPet_invalidateCombat', pet); r.flush()
    require(not r.native_damage, 'Old generation additional executed')
    return {'non_original_or_zero':5,'counter_reset_actions':3,'cancelled_additional_segments':0,
            'miss_invulnerable_boundary':'Native miss/invulnerability may provide no damage event or a zero event; no-event input executes no sampler, and the actual zero-event path is replayed without counter/phase increments. Native miss/absorption behavior itself is not emulated.'}


def verify_debuffs(script):
    r = PetAttackRuntime(script); a = r.pet([(6,4)])
    r.units[106] = {**r.units[101], 'abilities':{}, 'inventory':{}}
    b = r.pet([(6,1)],host=106)
    r.emit(1.,source=101); near(r.units[102]['abilities'][rawcode('Pbar')],8,'Strong armor')
    r.now += 2.; r.emit(1.,source=106)
    near(r.units[102]['abilities'][rawcode('Pbar')],8,'Weak cannot renew or replace strong')
    r.now += 1.; r.invoke('tdPetExpireAttackDebuffs')
    near(r.units[102]['abilities'][rawcode('Pbar')],2,'Strong expiry restores still-valid weak')
    r.invoke('TDPet_invalidateCombat',b);r.invoke('tdPetExpireAttackDebuffs')
    require(rawcode('Pbar') not in r.units[102]['abilities'],'Invalid last source retained armor')
    r = PetAttackRuntime(script); pet = r.pet([(5,4)])
    factors = []
    for hit in range(1,7):
        r.emit(1.)
        factor = r.invoke('tdAuraEnemySpeedFactor',102);factors.append(factor)
        near(factor,1.-.06*min(hit,5),'Reduce source stacks')
    r.invoke('DamageEvent_setNextDamageId',rawcode('Tspl'));r.emit(1.)
    near(r.invoke('tdAuraEnemySpeedFactor',102),.70,'Split arrow did not stack reduce')
    r.units[103]={**r.units[102],'abilities':{},'life':10000.}
    r.emit(1.,target=103)
    near(r.invoke('tdAuraEnemySpeedFactor',103),.94,'New target owns first layer')
    r.now += 3.;r.invoke('tdPetExpireAttackDebuffs');r.emit(1.)
    near(r.invoke('tdAuraEnemySpeedFactor',102),.94,'Exact expiry restarts first stack')
    # Same name max; other identities sum then cap; invalidating one source leaves another.
    r.units[106]={**r.units[101],'abilities':{},'inventory':{}}
    other=r.pet([(5,1)],host=106)
    for _ in range(5):r.emit(1.,source=106)
    near(r.invoke('tdAuraEnemySpeedFactor',102),.70,'Same name highest source only')
    r.invoke('TDPet_invalidateCombat',other);r.invoke('tdPetExpireAttackDebuffs')
    near(r.invoke('tdAuraEnemySpeedFactor',102),.94,'Removing one source preserves other')
    r.invoke('tdEnemySlowOfferTimed',102,106,13,4,.85,3.)
    near(r.invoke('tdAuraEnemySpeedFactor',102),.25,'Different name sums capped at75%')
    # Real Boss type classification, same source stacks, fixed half-strength.
    r = PetAttackRuntime(script);r.pet([(5,4)])
    for _ in range(5):r.emit(1.,target=100)
    near(r.invoke('tdAuraEnemySpeedFactor',100),.85,'Boss five stacks halved15%')
    r.invoke('tdPetForgetEnemy',100)
    require(not r.lists[r.globals['TDPetAttackState_targets']],'Explicit target exit leaked pet records')
    return {'armor_fallback':[8,8,2,0], 'six_hit_slow_factors':factors,'boss_five_layer_factor':.85,
            'same_name_max_other_name_sum_cap':.25,'cleared_target_records':0}


def verify_trial(script):
    r=PetAttackRuntime(script);r.enter(8);target=r.target(0);pet=r.pet([(17,4)])
    r.globals['TDPet_resolveRotation'][pet]=4
    r.units[target]['life']=15.
    r.emit(100.,target=target)
    near(r.units[target]['life'],1000000.-210.,'Priority0 refill before priority3 resolve')
    near(r.state_call('total',0),210.,'Priority4 trial final amount')
    near(r.score(),0.,'Trial never enters ordinary ledger')
    # Actual single-batch death does not replenish. A separate low-level registry
    # adversary covers both new and reused handles against actual snapshot guards.
    def ground(candidate, reused):
        r=PetAttackRuntime(candidate);r.auto_post=False
        # Fx-enabled maps prewarm native dummy units before trial admission.
        # Count real entry targets and zero death creations against each baseline.
        before_enter=len(r.creations);r.enter(8)
        created=r.creations[before_enter:]
        require(len(created)==20 and len(set(created))==20 and r.state_call('targetCount')==20 and
                all(unit is not None and r.units[unit]['type']==rawcode('uTrG') for unit in created),
                'Single-batch entry did not create exactly twenty real trial targets')
        target=r.target(0);pet=r.pet([(38 if r.final_catalog else 14,4)])
        original=[r.target(i) for i in range(5)]
        for unit in original:r.units[unit].update(x=0.,y=0.)
        r.visible_units=original[:]
        old_revision=r.globals['TDTrialBinding_revision'][r.binding(0)]
        r.emit(100.,target=target)
        original_post=r.scheduled[-1][1];r.run_timer(original_post)
        require(not r.native_damage,'Ground proc ran inline before target replacement fixture')
        before_death=len(r.creations)
        r.units[target]['alive']=False;r.event_target=target;r.invoke('tdTrialOnTargetDeath')
        require(r.slots[0]==0 and r.state_call('targetCount')==19 and len(r.creations)==before_death,'Single-batch death replenished the ground target')
        replacement=r.adversarial_rebind(0,reused)
        new_revision=r.globals['TDTrialBinding_revision'][r.binding(0)]
        require((replacement==target) is reused and new_revision>old_revision,'Trial replacement fixture did not issue expected handle/revision')
        r.units[replacement].update(x=0.,y=0.);r.visible_units=[replacement,*original[1:]]
        r.flush()
        if r.final_catalog:r.tick_effects()
        require(len(r.native_damage)==4 and all(hit[1]!=replacement for hit in r.native_damage),'Old ground proc hit replacement identity or lost live old neighbours')
        for hit in r.native_damage:near(hit[2],85.,'Ground proc immutable originalD')
        if r.final_catalog:
            r.invoke('TDPet_invalidateCombat',pet)
            require(r.invoke('tdPetEffectTaskCount')==0 and not r.visual_handles,'Trial first-stage fixture leaked later stages/visuals')
        return {'registry_adversary':True,'same_handle':reused,'new_revision':new_revision,'old_snapshot_neighbour_hits':4,'replacement_hits':0}
    replacements=[ground(script,False),ground(script,True)]
    guard=functions(script)['tdEquipmentTrialAoeVictimValid'][4]
    broken=script.replace(guard,'\treturn true\n',1)
    try:ground(broken,True)
    except ValueError as error:
        require('Old ground proc hit replacement identity' in str(error),'Unrelated trial identity mutation failure: '+str(error))
    else:raise ValueError('Removing the actual trial identity guard survived reused-handle replay')
    return {'refilled_HP':999790.,'trial_final_credit':210.,'old_snapshot_neighbour_hits':4,'replacement_hits':0,
            'replacement_cases':replacements,'identity_guard_removal_rejected':True,
            'spell_fixture':'Final skill38 first85%D stage; later stages explicitly cancelled' if r.final_catalog else 'Legacy skill14 single85%D stage'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map',type=Path)
    parser.add_argument('--baseline',type=Path)
    args=parser.parse_args()
    artifact=Mpq(args.map.read_bytes());script=artifact.extract('war3map.j').decode('utf-8')
    require('function tdPetSkillDefined takes' in script,'This gate requires the packed integer spirit catalog')
    abilities=ability_objects(artifact.extract('war3map.w3a'));units=unit_objects(artifact.extract('war3map.w3u'))
    before=ability_objects(Mpq(args.baseline.read_bytes()).extract('war3map.w3a')) if args.baseline else None
    verify_phase_fence_source();verify_skill_allowed(script); slots=verify_phase_one_slots(abilities);verify_phase_one_preview(abilities)
    report={'sha256':hashlib.sha256(args.map.read_bytes()).hexdigest(),'legal_slot_objects':slots,
            'native_critical_catalog':verify_native_critical_catalog(abilities,units,before),
            'resolve':verify_resolve(script),'additional_and_sampling':verify_passives_and_sampling(script),
            'split_original_basis':verify_split_original_basis(script),'phase_fence_contract':verify_phase_fence_compiled(script),'post_timer_order':verify_post_timer_order(script),
            'source_and_lifecycle':verify_source_rejection_and_cancellation(script),
            'debuffs':verify_debuffs(script),'trial':verify_trial(script),
            'boundary':'Exact packed DamageEvent early/onDamage chain and production pet/ledger/slow functions. Native post-armor D, engine clock/callbacks/life subtraction/handles/groups/random are explicit boundaries. No Warcraft/FPS/native visual claim.'}
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
