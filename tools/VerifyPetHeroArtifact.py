#!/usr/bin/env python3
"""Replay phase-three heroes from one final map's actual packed JASS.

Uses the frozen phase-one replay engine (6512d54 or newer). No Wurst compile,
map build or Warcraft launch. Native post-armor input, clock, handle allocator,
collections, tower impact/completion and accepted-shield notifications, and
synchronous death delivery are
explicit boundaries. Hero guards, queues, tasks, consume/index transactions,
trial bindings/revisions and tagged damage run from the supplied artifact.
This is not a gameplay, native armor, stun or timing/performance simulation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyPetAttackArtifact import PetAttackRuntime, near
from VerifyPetHeroSource import HOSTS, POWERS
from VerifyTowerUpgradeArtifact import rawcode
from VerifyBuilderControlDelta import allocations

CONTEXT_FIELDS = ('generation', 'token', 'fromTrial')
STORM_FIELDS = ('ownerKey', 'generation', 'revision', 'quality',
                'context_epoch', 'context_generation', 'context_token', 'context_fromTrial',
                'targets_first', 'targets_firstRevision', 'targets_second', 'targets_secondRevision',
                'targets_third', 'targets_thirdRevision', 'targets_fourth', 'targets_fourthRevision',
                'targets_fifth', 'targets_fifthRevision')
SNAPSHOT_FIELDS = ('firstRevision', 'second', 'secondRevision', 'third',
                   'thirdRevision', 'fourth', 'fourthRevision', 'fifth', 'fifthRevision')


class HeroRuntime(PetAttackRuntime):
    def __init__(self, script):
        super().__init__(script)
        self.invoke('tdPetHeroSetup')
        self.invoke('tdPetSetupEffectScheduler')
        self.death_trace = []
        self.callback_allocations = allocations(script)
        require(self.globals['DamageEvent_firstUnreducedListeners'][0] != 0,
                'Actual original ordinal early0 listener not registered')
        self.units[102]['userdata'] = 100

    def native(self, name, args):
        # Reject inherited Boss harness shortcuts for production hero eligibility.
        if name in ('tdTowerChoiceForUnitTypeId', 'tdTowerLevelForUnitTypeId',
                    'tdTowerBranchForUnitTypeId', 'tdEnemyLaneId', 'tdEnemyWave',
                    'tdEnemyWasLeaked', 'tdEnemyDeathWasSettled'):
            return False, None
        if name.startswith('tdPetHero') or name in ('tdPetDamage', 'tdPetSpellDamage',
                                                    'tdPetAoeVictimValid'):
            return False, None
        return super().native(name, args)

    def expression(self, text, scope):
        try:
            return super().expression(text, scope)
        except ValueError as error:
            if str(error) == 'Mixed Jass and/or requires a Jass-specific precedence parser':
                raise ValueError(str(error) + ': ' + text) from error
            raise

    def seed_current_record(self, wave=24, role=3, active=True):
        super().seed_record(wave, role, active)
        # State/lane/wave are controlled fixtures. Execute the CURRENT record
        # constructor too, including its new empty stage-weakening list.
        record = self.invoke('new_TDEnemyMechanicRecord', 100, 20)
        self.table[100] = record
        self.lists[700] = [record]

    def emit(self, amount, source=101, target=102):
        # Delivery occurs INSIDE UnitDamageTarget for code damage: this is the
        # controlled native death edge, not a library asynchronous-post guess.
        auto_post = self.auto_post
        self.auto_post = False
        was_alive = self.units[target]['alive']
        try:
            result = super().emit(amount, source, target)
            if was_alive and not self.units[target]['alive'] and self.units[target]['type'] != 0:
                if not self.invoke('tdTrialIsTargetType', target):
                    leaked = self.invoke('tdEnemyWasLeaked', target)
                    if not self.invoke('tdEnemyDeathWasSettled', target):
                        self.invoke('tdMarkEnemyKilled', target)
                    blocked = self.invoke('tdPetHeroSecondaryDeathBlocked')
                    self.invoke('tdPetHeroForgetEnemy', target, not leaked)
                    self.death_trace.append((target, blocked))
        finally:
            self.auto_post = auto_post
        if auto_post:
            self.drain_zero()
        return result

    def pet(self, skills, host=101, slot=0, level=3):
        if self.four_slot_contract:
            require(len(skills) == 1 and 39 <= skills[0][0] <= 48,
                    'Four-role hero fixture requires exactly one hero in slot2')
            pet = super().pet(skills, host=host, slot=slot, level=level)
            require(self.invoke('TDPet_skillAt', pet, 2) == skills[0][0],
                    'Production slot2 rejected hero passive fixture')
        else:
            pet = self.invoke('new_TDPet', 0, 1, 1)
            require(self.invoke('tdPetStore', 0, pet), 'Actual collection rejected hero fixture')
            # Historical phase-two maps retain their published active0 contract.
            self.invoke('TDPet_setSkill', pet, 0, 11, 1)
            for index, (skill, quality) in enumerate(skills, 1):
                self.invoke('TDPet_setSkill', pet, index, skill, quality)
                require(self.invoke('TDPet_skillAt', pet, index) == skill,
                        'Production slot contract rejected hero passive fixture')
            self.globals['TDPet_level'][pet] = level
            self.globals['TDPet_host'][pet] = host
            self.globals['TDPet_generation'][pet] = 1
        # Isolate hero behavior without replacing the actual active eligibility.
        self.globals['TDPet_readyAt'][pet] = self.now + 1000.
        require(self.invoke('tdPetBindingValid', pet, host, 1), 'Actual binding rejected hero fixture')
        return pet

    def setup_pet(self, skill, quality=4, host=101):
        self.units[host] = {**self.units[101], 'type': rawcode(HOSTS[skill - 39]),
                            'abilities': {}, 'inventory': {}, 'x': 0., 'y': 0.}
        return self.pet([(skill, quality)], host)

    def enemy(self, target, life=10000., x=0., y=0., lane=0):
        self.units[target] = {**self.units[102], 'alive': True, 'life': life,
                              'maxLife': life, 'abilities': {}, 'x': x, 'y': y,
                              'userdata': lane * 10000 + 100, 'lane': lane}

    def tuple_call(self, name, fields, *arguments):
        first = self.invoke(name, *arguments)
        return (first, *(self.globals[name + '_return_' + field] for field in fields))

    def capture(self, pet, skill, serial, target=102, amount=100.):
        context = self.tuple_call('tdTrialCaptureContext', CONTEXT_FIELDS, target)
        snapshot = self.tuple_call('tdCaptureEquipmentTrialAoe', SNAPSHOT_FIELDS, 0, *context)
        self.invoke('tdPetHeroCapturePrimary', pet, self.globals['TDPet_host'][pet],
                    target, skill, 4, amount, self.units[target]['life'], amount,
                    serial, *context, *snapshot)

    def tick(self, elapsed):
        self.now += elapsed
        for package in ('TDCombatVisualRuntime', 'TDPetEffectScheduler'):
            allocation = self.callback_allocations.get('alloc_CallbackPeriodic_doPeriodically_' + package)
            if allocation is None:
                require(package == 'TDCombatVisualRuntime', 'Battle callback allocator missing')
                continue
            array, type_id = allocation
            require(array == 'CallbackPeriodic_typeId', 'Unknown actual periodic allocator')
            callbacks = sorted({cb for interval, cb in self.periodics if interval == .05 and
                                self.globals[array][cb] == type_id and
                                not self.timers[self.globals['CallbackPeriodic_t'][cb]]['destroyed']})
            require(len(callbacks) == 1 if package == 'TDPetEffectScheduler' else len(callbacks) <= 1,
                    'Shared periodic callback ownership changed')
            for cb in callbacks:
                self.executed_steps = 0
                self.invoke('call_doPeriodically_' + package, cb, cb)
        self.drain_zero()

    def owner_ticket(self, pet, skill):
        return self.invoke('tdPetHeroOwnerTicket', pet, skill)


def verify_catalog(script):
    r = HeroRuntime(script)
    for skill, host, powers in zip(range(39, 49), HOSTS, POWERS):
        require(r.invoke('tdPetSkillDefined', skill), 'Final map hero missing from valid catalog')
        require(not r.invoke('tdPetSkillIsActive', skill), 'Hero enhancement consumes active slot')
        require(r.invoke('tdPetHeroHostTypeId', skill) == rawcode(host), 'Final host map changed')
        for candidate in (*HOSTS, 'uA11', 'uO15', 'uH15', 'uD15', 'uG15'):
            r.units[101]['type'] = rawcode(candidate)
            require(r.invoke('tdPetSkillFitsHost', skill, 101) == (candidate == host),
                    'Final compatibility facade accepts wrong final branch/lower tower')
        require(not r.invoke('tdPetSkillFitsHost', skill, None), 'Null host accepts hero enhancement')
        for quality, power in enumerate(powers, 1):
            near(r.invoke('tdPetSkillPower', skill, quality), power, 'Final quality facade')
        require(r.invoke('tdPetHeroIsSpellDamage', skill) == (skill in (40, 42, 44, 45, 46, 48)),
                'Final damage school changed')
    for code, spell, event_id, amount in ((True, False, 0, 100.), (False, True, 0, 100.),
                                        (False, False, rawcode('Pdam'), 100.),
                                        (False, False, rawcode('Tspl'), 100.),
                                        (False, False, 0, 0.)):
        require(not r.invoke('tdPetHeroSerialEligible', code, spell, event_id, amount),
                'Compiled original ordinal accepts nested code/spell/ID/zero boundary')
    require(r.invoke('tdPetHeroSerialEligible', False, False, 0, 100.), 'Compiled real original not admitted')
    require(r.invoke('tdPetHeroNextSerial', 2147483647) == -1 and
            r.invoke('tdPetHeroNextSerial', -1) == -1, 'Compiled original ordinal can wrap/re-enable')
    for retired in (4, 9, 10, 13, 14, 15):
        require(not r.invoke('tdPetSkillDefined', retired), 'Retired final catalog skill remains live')
    require(sum(bool(r.invoke('tdPetSkillDefined', skill)) for skill in range(49)) == 43,
            'Final catalog does not contain exactly 43 legal identities')
    return {'actual_final_catalog': 43, 'hero_passives': 10, 'quality_values': 40,
            'compiled_serial_boundaries': 8}


def verify_root_snapshot(script):
    cases = []
    for reused_handle in (False, True):
        r = HeroRuntime(script)
        r.auto_post = False
        r.enter(8)
        pet = r.setup_pet(46)
        original = [r.target(slot) for slot in range(5)]
        for target in original:
            r.units[target].update(x=0., y=0.)
        for _ in range(4):
            r.emit(1., target=original[0])
            r.drain_zero()
        r.emit(1., target=original[0])
        require(not r.native_damage, 'Root pulse ran inline at original early3')
        # Death leaves slot1 empty. An explicit identity-registry adversary changes
        # only that captured identity before post, without allowing ACTIVE refill.
        old = original[1]
        token = r.state_call('getToken')
        generation = r.state_call('getGeneration')
        old_revision = r.globals['TDTrialBinding_revision'][r.binding(1)]
        before_creations = len(r.creations)
        before_scheduled = list(r.scheduled)
        before_count = r.state_call('targetCount')
        r.units[old]['alive'] = False
        r.event_target = old
        r.invoke('tdTrialOnTargetDeath')
        require(r.slots[1] == 0 and r.state_call('targetCount') == before_count - 1
                and len(r.creations) == before_creations and r.scheduled == before_scheduled,
                'Actual death refilled/scheduled replenishment instead of leaving one vacant slot')
        replacement = r.adversarial_rebind(1, reused=reused_handle)
        r.units[replacement].update(x=0., y=0.)
        require(r.state_call('getToken') == token and r.state_call('getGeneration') == generation,
                'Controlled identity adversary changed the round instead of one identity')
        require(r.globals['TDTrialBinding_revision'][r.binding(1)] != old_revision,
                'Controlled registry fixture did not advance the identity revision')
        require((replacement == old) == reused_handle, 'Native allocator reuse fixture differs')
        r.drain_zero()
        require(not r.native_damage, 'Root ignored its .5-second warning')
        r.tick(.5)
        victims = [hit[1] for hit in r.native_damage]
        require(len(victims) == 3 and replacement not in victims,
                'Root chased a same-token slot replacement or lost its three-target cap')
        require(set(victims) <= set(original) - {old}, 'Root admitted an uncaptured trial identity')
        for hit in r.native_damage:
            near(hit[2], r.invoke('tdPetHeroBaseAttack', 101) * .5, 'Trial root no Boss scale')
        r.invoke('TDPet_invalidateCombat', pet)
        require(r.invoke('tdPetEffectTaskCount') == 0, 'Source cancel leaked root/counter tasks')
        cases.append({'same_token_identity_registry_adversary': True,
                      'production_death_refilled': False,
                      'native_handle_reused': reused_handle, 'adversary_hits': 0,
                      'captured_old_hits': 3, 'cancelled_task_count': 0})
    for reset in (False, True):
        r = HeroRuntime(script)
        r.enter(8)
        pet = r.setup_pet(46)
        original = [r.target(slot) for slot in range(5)]
        for target in original:
            r.units[target].update(x=0., y=0.)
        for _ in range(5):
            r.emit(1., target=original[0])
        generation = r.state_call('getGeneration')
        if reset:
            # Actual TDInit reset/re-registration; do not rebuild package tables,
            # clear scheduled callbacks or replace the shared scheduler.
            r.invoke('tdStartGame')
            for lane in range(4):
                r.invoke('tdSetLaneActive', lane, True)
            r.enter(24)
            require(r.state_call('getGeneration') > generation and r.state_call('getRound') == 2,
                    'Actual reset did not create a new trial generation/round')
            r.visible_units = [r.target(slot) for slot in range(5)]
            for target in r.visible_units:
                r.units[target].update(x=0., y=0.)
        else:
            r.invoke('tdTrialClearTargets')
            require(r.state_call('targetCount') == 0, 'Actual clear retained trial identities')
        r.tick(.5)
        r.invoke('TDPet_invalidateCombat', pet)
        require(not r.native_damage and r.invoke('tdPetEffectTaskCount') == 0,
                'Cleared/reset root hit a new identity or source cancel leaked a task')
        cases.append({'actual_reset_new_round' if reset else 'actual_clear': True,
                      'damage': 0, 'cancelled_task_count': 0,
                      'package_globals_reinitialized': False})
    return cases


def verify_judgement(script):
    r = HeroRuntime(script)
    pet = r.setup_pet(43)
    r.auto_post = False
    # Accepted shield notification is a native success boundary; actual pending/
    # early3/derived DamageEvent/queue functions remain untouched and execute JASS.
    r.enemy(103)
    r.enemy(104)
    for serial, primary in ((1, 102), (2, 103), (3, 104)):
        r.invoke('tdPetHeroOnShieldAccepted', 101, primary, 100., serial)
        r.emit(100., target=primary)
        active = r.owner_ticket(pet, 43)
        require(active != 0 and r.globals['TDPetHeroTicket_grantSerial'][active] == serial,
                'Current-original pending seal did not become the next-hit active')
        require(not r.native_damage, 'Seal extra escaped original post fence')
        if serial == 1:
            current = r.invoke('tdPetHeroCurrentOriginalSerial')
            r.invoke('tdPetSpellDamage', pet, 101, 1, 102, 1.)
            require(r.invoke('tdPetHeroCurrentOriginalSerial') == current,
                    'Nested code/spell damage advanced the original ordinal')
            require(r.owner_ticket(pet, 43) == active, 'Nested derived hit consumed current grant')
            r.native_damage.clear()
    # Two later originals have consumed seal1/2, despite hit3 preceding hit2 post.
    r.drain_zero()
    require(len(r.native_damage) == 2, 'Consecutive original seals missed/doubled a consumption')
    for hit in r.native_damage:
        near(hit[2], 62.5, 'Self judgement ordinary derived D')
    # A live zero-target charge must survive a scheduler visit, rather than
    # accidentally running the single-target context guard at targetCount zero.
    active = r.owner_ticket(pet, 43)
    r.tick(.05)
    require(r.owner_ticket(pet, 43) == active, 'Scheduler prematurely destroyed a zero-target self seal')
    # An older accepted notification can never overwrite grant3, nor extend expiry.
    expiry = r.globals['TDPetHeroTicket_expiry'][active]
    r.invoke('tdPetHeroOnShieldAccepted', 101, 102, 100., 2)
    r.capture(pet, 43, 2)
    require(r.owner_ticket(pet, 43) == active and r.globals['TDPetHeroTicket_expiry'][active] == expiry,
            'Stale pending seal replaced/refreshed a newer active seal')
    r.tick(2.)
    require(not r.owner_ticket(pet, 43), 'Self seal lived beyond its success-time expiry')
    r.invoke('TDPet_invalidateCombat', pet)
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Pending/active seal cancelled twice or leaked')
    return {'grant_origin_hits': 0, 'consecutive_pre_post_consumptions': 2,
            'nested_derived_consumptions': 0, 'stale_grant_replacements': 0,
            'cancelled_tasks': 0, 'accepted_order_native_boundary': True}


def verify_school_and_moon(script):
    results = {}
    for skill in (40, 41):
        r = HeroRuntime(script)
        r.setup_pet(skill)
        r.seed_current_record(wave=24, role=3, active=True)
        r.globals['TDEnemyMechanicRuntime_tdEnemyMechanicsReady'] = True
        r.units[100].update(life=10000., maxLife=10000., x=0., y=0.)
        if skill == 41:
            r.emit(100., target=100)
            expected = 15.
        else:
            for _ in range(5):
                r.emit(100., target=100)
            require(not r.native_damage, 'Moon marking hit consumed its own mark')
            r.units[106] = {**r.units[101], 'type': rawcode('uA11'), 'abilities': {}, 'inventory': {}}
            r.emit(100., source=106, target=100)  # No spirit attached to receiver.
            expected = 68.
        require(len(r.native_damage) == 1 and r.native_damage[0][0] == 101,
                'Hero derivative ownership left its actual granting host')
        near(r.native_damage[0][2], expected, 'Boss stage scale once / ordinary school')
        event = [event for source, target, event in r.emitted if event['isCode']][-1]
        require(event['id'] == rawcode('Pdam'), 'Hero derivative lost Pdam/code classification')
        results[str(skill)] = {'boss_wave24_damage': expected, 'grant_host': 101,
                               'code_and_Pdam': True}
    return results



def verify_secondary_death_edges(script):
    r = HeroRuntime(script)
    first = r.setup_pet(45)
    other = r.setup_pet(45, host=106)
    epidemic = r.setup_pet(48, host=107)
    for target in (103, 104, 105, 108, 109):
        r.enemy(target)
    r.units[109].update(alive=False, life=0.)
    for _ in range(4):
        r.emit(1., target=102)
    r.visible_units = [103, 104]
    r.emit(10000., target=102)
    require(r.invoke('tdPetHeroTargetInfected', 103), 'Idle queue did not start weak poison')
    # A later original source can seed an already weak-infected target. This is
    # the mixed state whose death must retire ALL sources without a new generation.
    for _ in range(4):
        r.emit(1., source=106, target=103)
    r.visible_units = [103]
    r.invoke('tdPetHeroOnCorpseExplosionSettled', 107, 109, 0., 0.)
    require(r.owner_ticket(other, 45) and r.owner_ticket(epidemic, 48), 'Mixed original infection fixture missing')
    r.units[103]['life'] = 1.
    r.native_damage.clear()
    r.tick(1.)
    require((103, True) in r.death_trace, 'Weak poison death was outside synchronous depth guard')
    require(not r.owner_ticket(other, 45) and not r.owner_ticket(epidemic, 48),
            'Weak poison death did not consume other-source original bud and epidemic group')
    require(not r.invoke('tdPetHeroSecondaryDeathBlocked'), 'Weak poison leaked secondary depth')
    require(len(r.native_damage) == 2, 'Mixed secondary death started an extra propagation/explosion')
    r.visible_units = [104, 108]
    for _ in range(4):
        r.emit(1., source=106, target=105)
    r.emit(10000., source=106, target=105)
    require(r.invoke('tdPetHeroTargetInfected', 108),
            'Later independent normal death remained blocked by leaked secondary depth')
    for pet in (first, other, epidemic):
        r.invoke('TDPet_invalidateCombat', pet)
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Mixed infection cancellation leaked tasks')

    r = HeroRuntime(script)
    first = r.setup_pet(48)
    other = r.setup_pet(48, host=106)
    r.enemy(103, life=1.)
    r.enemy(104)
    r.units[104].update(alive=False, life=0.)
    r.visible_units = [102]
    r.invoke('tdPetHeroOnCorpseExplosionSettled', 101, 104, 0., 0.)
    r.visible_units = [103]
    r.invoke('tdPetHeroOnCorpseExplosionSettled', 106, 104, 0., 0.)
    r.emit(10000., target=102)
    require(len(r.native_damage) == 1 and (103, True) in r.death_trace,
            'Weak epidemic killing another group caused a second explosion')
    require(not r.owner_ticket(other, 48) and not r.invoke('tdPetHeroSecondaryDeathBlocked'),
            'Secondary epidemic did not cleanup/restore its depth')
    for pet in (first, other):
        r.invoke('TDPet_invalidateCombat', pet)
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Epidemic cancellation leaked tasks')
    return {'weak_poison_kills_other_source_bud_and_group': 'cleanup only',
            'weak_epidemic_kills_another_group': 'cleanup only',
            'later_independent_death_propagates': True, 'cancelled_tasks': 0}


def verify_hunt(script):
    cases = []
    for label in ('lethal', 'nonlethal_then_extra_kill', 'zero', 'removed', 'leak'):
        r = HeroRuntime(script)
        pet = r.setup_pet(47)
        r.auto_post = False
        r.units[102].update(life=100., maxLife=100.)
        if label == 'leak':
            r.invoke('tdMarkEnemyLeaked', 102)
        r.emit(0. if label == 'zero' else 50. if label == 'nonlethal_then_extra_kill' else 100.)
        if label == 'nonlethal_then_extra_kill':
            r.invoke('tdPetDamage', pet, 101, 1, 102, 100.)
        if label == 'removed':
            r.units[102]['type'] = 0  # Controlled native removal before original post.
        r.drain_zero()
        granted = bool(r.owner_ticket(pet, 47))
        require(granted == (label == 'lethal'), 'Hunt falsely granted/missed primary lethal charge: ' + label)
        if granted:
            r.enemy(104)
            r.native_damage.clear()
            r.emit(1., target=104)
            r.drain_zero()
            require(len(r.native_damage) == 1, 'Hunt next-hit charge did not consume exactly once')
            near(r.native_damage[0][2], r.invoke('tdPetHeroBaseAttack', 101) * .5, 'Hunt ordinary B')
        r.invoke('TDPet_invalidateCombat', pet)
        require(r.invoke('tdPetEffectTaskCount') == 0, 'Hunt cancellation leaked its charge')
        cases.append({'case': label, 'grant': granted})
    return cases


def verify_frost_and_relay(script):
    r = HeroRuntime(script)
    strong = r.setup_pet(39)
    weak = r.setup_pet(39, quality=1, host=106)
    r.invoke('tdPetHeroOnSplitArrowImpact', 106, 102)
    r.invoke('tdPetHeroOnSplitArrowImpact', 101, 102)
    near(r.invoke('tdAuraEnemySpeedFactor', 102), .8, 'Final split impact 20% slow')
    require(not r.native_damage, 'Frost enhancement generated another arrow/damage')
    r.invoke('TDPet_invalidateCombat', strong)
    near(r.invoke('tdAuraEnemySpeedFactor', 102), .92, 'Cancel preserved other source 8% frost')
    r.tick(2.)
    near(r.invoke('tdAuraEnemySpeedFactor', 102), 1., 'Frost exact two-second expiry')
    r.invoke('TDPet_invalidateCombat', weak)
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Frost source cancellation leaked tasks')
    r = HeroRuntime(script)
    r.setup_pet(39)
    r.invoke('tdPetHeroOnSplitArrowImpact', 101, 100)
    near(r.invoke('tdAuraEnemySpeedFactor', 100), .9, 'Boss final split frost half strength')

    r = HeroRuntime(script)
    giver = r.setup_pet(44)
    weak = r.setup_pet(44, quality=1, host=109)
    r.units[106] = {**r.units[101], 'type': rawcode('uA11'), 'x': 20., 'abilities': {}, 'inventory': {}}
    r.units[107] = {**r.units[106], 'owner': 1, 'x': 1.}
    r.visible_units = [107, 106]
    r.invoke('tdPetHeroOnShieldAccepted', 101, 102, 100., 1)
    seal = r.invoke('tdPetHeroRecipientSeal', 106)
    require(seal and not r.invoke('tdPetHeroRecipientSeal', 107), 'Relay chose a cross-lane tower')
    expiry = r.globals['TDPetHeroTicket_expiry'][seal]
    r.tick(.05)
    require(r.invoke('tdPetHeroRecipientSeal', 106) == seal, 'Scheduler prematurely destroyed a zero-target friendly seal')
    r.visible_units = [106]
    r.invoke('tdPetHeroOnShieldAccepted', 109, 102, 100., 1)
    require(r.invoke('tdPetHeroRecipientSeal', 106) == seal and
            r.globals['TDPetHeroTicket_expiry'][seal] == expiry, 'Weak relay renewed stronger seal')
    r.emit(1.)  # Grant-origin hit cannot consume a friendly recipient's seal.
    require(not r.native_damage, 'Friendly seal fired during granting original')
    r.emit(100., source=106)
    require(len(r.native_damage) == 1 and r.native_damage[0][0] == 101,
            'No-pet recipient did not consume exactly one actual granting-source seal')
    near(r.native_damage[0][2], r.invoke('tdPetHeroBaseAttack', 101) * .625, 'Relay granting B')
    r.invoke('tdPetHeroOnShieldAccepted', 101, 102, 100., 3)
    r.invoke('tdPetHeroTowerInvalidated', 106)
    r.native_damage.clear()
    r.emit(100., source=106)
    require(not r.native_damage, 'Invalidated recipient still consumed a seal')
    for pet in (giver, weak):
        r.invoke('TDPet_invalidateCombat', pet)
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Relay source cancel leaked tasks')
    return {'frost_normal_factor': .8, 'boss_factor': .9, 'other_source_survives': .92,
            'frost_expiry_seconds': 2, 'relay_no_pet_recipient': True,
            'relay_weak_renewals': 0, 'invalidated_recipient_hits': 0}


def verify_idle_storm_and_native_poison_death(script):
    cases = []
    for label in ('full_completion', 'native_cancel', 'source_generation'):
        r = HeroRuntime(script)
        pet = r.setup_pet(42)
        for target in range(103, 110):
            r.enemy(target)
        r.visible_units = list(range(103, 110))
        context = r.tuple_call('tdTrialCaptureContext', CONTEXT_FIELDS, 102)
        cast = r.tuple_call('tdPetHeroCaptureStorm', STORM_FIELDS, 101, *context)
        if label == 'native_cancel':
            r.invoke('tdPetHeroCancelStorm', 101)
        if label == 'source_generation':
            r.invoke('TDPet_invalidateCombat', pet)
        r.invoke('tdPetHeroCompleteStorm', 101, *cast)
        require(not r.native_damage, 'Storm tail escaped shared asynchronous queue')
        r.drain_zero()  # NO later original attack is delivered.
        expected = 6 if label == 'full_completion' else 0
        require(len(r.native_damage) == expected, 'Idle storm completion/cancel contract failed: ' + label)
        for hit in r.native_damage:
            near(hit[2], 87.5, 'Original full storm one tail per-tick35 quality4')
        cases.append({'case': label, 'idle_tail_hits': expected})
    r = HeroRuntime(script)
    pet = r.setup_pet(45)
    for target in (103, 104, 105):
        r.enemy(target)
    for _ in range(4):
        r.emit(1.)
    r.visible_units = [103, 104, 105]
    r.units[102].update(alive=False, life=0.)
    r.invoke('tdMarkEnemyKilled', 102)
    r.invoke('tdPetHeroForgetEnemy', 102, True)  # Controlled ORIGINAL native poison death.
    r.drain_zero()  # NO later original attack is delivered.
    infected = [target for target in (103, 104, 105) if r.invoke('tdPetHeroTargetInfected', target)]
    require(len(infected) == 2, 'Idle native poison death missed or exceeded two weak targets')
    r.tick(1.)
    r.tick(1.)
    require(len(r.native_damage) == 4, 'Weak poison did not deliver exactly two ticks to two targets')
    for hit in r.native_damage:
        near(hit[2], r.invoke('tdPetHeroBaseAttack', 101) * .25, 'Weak poison B budget')
    r.invoke('TDPet_invalidateCombat', pet)
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Idle poison source cancel leaked tasks')
    return {'storm': cases, 'original_native_poison_death_idle_targets': 2,
            'weak_poison_total_ticks': 4, 'next_original_required': False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data = args.map.read_bytes()
    script = Mpq(data).extract('war3map.j').decode('utf-8')
    report = {'catalog': verify_catalog(script), 'root_trial_snapshot': verify_root_snapshot(script),
              'judgement': verify_judgement(script), 'damage_school_and_no_pet_moon': verify_school_and_moon(script),
              'one_generation_secondary_deaths': verify_secondary_death_edges(script),
              'hunt_primary_lethal': verify_hunt(script),
              'frost_and_friendly_seal': verify_frost_and_relay(script),
              'idle_storm_and_original_native_death': verify_idle_storm_and_native_poison_death(script)}
    report.update(status='PASS', map_sha256=hashlib.sha256(data).hexdigest(),
                  jass_sha256=hashlib.sha256(script.encode()).hexdigest(),
                  tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope='Actual final-map packed JASS with explicit bounded native boundaries',
                  native_boundaries=['post-armor original D and life deduction',
                                     'clock and callback delivery', 'handles and collections',
                                     'native tower impact/full-storm/corpse-completion notifications',
                                     'accepted primary-shield notification',
                                     'synchronous UnitDamageTarget death delivery',
                                     'controlled low-level trial identity-registry adversary; no ACTIVE refill'],
                  replay_dependencies={name: hashlib.sha256((Path(__file__).parent / name).read_bytes()).hexdigest()
                                       for name in ('VerifyPetAttackArtifact.py', 'VerifyTrialReplay.py',
                                                    'VerifyBossSpellResistanceArtifact.py',
                                                    'VerifyEquipmentCombatReplay.py', 'VerifyPureBossArtifact.py',
                                                    'VerifyPetHeroSource.py')},
                  warcraft_engine='not run')
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(encoded)
    print(encoded, end='')


if __name__ == '__main__':
    main()
