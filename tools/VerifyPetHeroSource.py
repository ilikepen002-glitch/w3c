#!/usr/bin/env python3
"""Evaluate reserved hero scalar rules from Wurst source, without compiling.

This verifies a development checkpoint. It is deliberately not a production
skill-pool gate, compiled JASS replay, map validation, or gameplay observation.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources, rawcode, source_functions, uncomment
from VerifyEquipmentAbilityArtifact import require

ROOT = Path(__file__).resolve().parents[1]
RULES = 'pets/TDPetHeroRules.wurst'
HOSTS = ('uA6A', 'uA6B', 'uO6A', 'uO6B', 'uH6A',
         'uH6B', 'uD6A', 'uD6B', 'uG6A', 'uG6B')
POWERS = ((.08, .12, .16, .20), (.40, .60, .80, 1.00),
          (.06, .09, .12, .15), (1.0, 1.5, 2.0, 2.5),
          (.25, .375, .50, .625), (.25, .375, .50, .625),
          (.10, .15, .20, .25), (.20, .30, .40, .50),
          (.20, .30, .40, .50), (.25, .40, .55, .70))


def verify(sources):
    evaluator = SourceScalarEvaluator(sources)
    call = lambda name, *args: evaluator.call(name, list(args))
    require(evaluator.constant('TD_PET_HERO_FIRST') == 39 and
            evaluator.constant('TD_PET_HERO_LAST') == 48, 'Reserved hero ID range changed')
    for skill, host, powers in zip(range(39, 49), HOSTS, POWERS):
        require(call('tdPetHeroDefined', skill), 'Missing reserved hero identity')
        require(call('tdPetHeroHostTypeId', skill) == rawcode(host), 'Wrong exact final host')
        choice = (skill - 39) // 2 + 1
        branch = (skill - 39) % 2 + 1
        require(call('tdTowerUnitIdForLevelBranch', choice, 6, branch) == rawcode(host),
                'Hero mapping diverges from actual tower catalog')
        for other in HOSTS:
            require(call('tdPetHeroFitsRawcode', skill, rawcode(other)) == (host == other),
                    'Cross-branch hero compatibility accepted')
        for lower in ('uA11', 'uO15', 'uH15', 'uD15', 'uG15'):
            require(not call('tdPetHeroFitsRawcode', skill, rawcode(lower)),
                    'Lower tower accepted hero enhancement')
        for quality, expected in enumerate(powers, 1):
            require(math.isclose(call('tdPetHeroPower', skill, quality), expected,
                                 abs_tol=1e-9), 'Wrong approved hero quality value')
        for quality in (-1, 0, 5, 2147483647):
            require(call('tdPetHeroPower', skill, quality) == 0., 'Invalid quality has hero power')
        require(bool(call('tdPetHeroName', skill)) and bool(call('tdPetHeroHostName', skill)),
                'Missing skill/host title')
        require(call('tdPetHeroUsesBaseAttack', skill) == (skill in (44, 45, 46, 47)),
                'D/B damage basis changed')
        require(call('tdPetHeroIsSpellDamage', skill) == (skill in (40, 42, 44, 45, 46, 48)),
                'Ordinary-derived/spell hero school changed')
    for skill in (-1, 0, 38, 49, 2147483647):
        require(not call('tdPetHeroDefined', skill), 'Invalid reserved skill accepted')
        require(call('tdPetHeroHostTypeId', skill) == 0, 'Invalid skill mapped to a host')
        require(not call('tdPetHeroFitsRawcode', skill, 0), 'Invalid host zero equals accepted skill zero')
        require(call('tdPetHeroPower', skill, 4) == 0., 'Invalid skill has power')
    for incoming, expected in ((.1, False), (1., True), (1.1, True)):
        require(call('tdPetHeroOfferWins', incoming, 1., 3., 2.) == expected,
                'Weak mark/seal renewed stronger source')
    require(call('tdPetHeroOfferWins', .1, 1., 3., 3.), 'Expired mark cannot be replaced')
    require(not call('tdPetHeroOfferWins', 0., 1., 3., 4.), 'Zero offer accepted')
    require(not call('tdPetHeroOneShotLive', False, 3., 3.), 'Expiry equality accepted')
    require(not call('tdPetHeroOneShotLive', True, 3., 2.), 'Consumed ticket accepted')
    for serial in (4, 5, 6):
        require(call('tdPetHeroLaterHit', 5, serial) == (serial == 6),
                'Grant-origin hit can consume its seal')
    require(not call('tdPetHeroLaterHit', -1, 1), 'Invalid grant serial accepted')
    for grant, hit, expected in ((5, 5, True), (5, 4, False), (5, 6, False), (0, 0, False)):
        require(call('tdPetHeroGrantCanCommit', grant, hit) == expected, 'Wrong-original pending grant committed')
    for incoming, existing, expected in ((5, 4, True), (5, 5, False), (4, 5, False), (-1, 0, False)):
        require(call('tdPetHeroGrantNewer', incoming, existing) == expected, 'Stale/duplicate grant overwrote new active')
    require(call('tdPetHeroNextSerial', 2147483646) == 2147483647 and
            call('tdPetHeroNextSerial', 2147483647) == -1 and
            call('tdPetHeroNextSerial', -1) == -1, 'Original ordinal can wrap/re-enable')
    serial = call('tdPetHeroNextSerial', 4)
    grant = serial
    for code, spell, event_id, amount in ((True, False, 0, 100.),
                                         (True, False, rawcode('Pdam'), 100.),
                                         (False, True, 0, 100.),
                                         (False, False, rawcode('Tspl'), 100.),
                                         (False, False, rawcode('Pdam'), 100.),
                                         (False, False, 0, 0.)):
        if call('tdPetHeroSerialEligible', code, spell, event_id, amount):
            serial = call('tdPetHeroNextSerial', serial)
    require(not call('tdPetHeroLaterHit', grant, serial), 'Nested derived damage consumed grant-hit seal')
    require(call('tdPetHeroSerialEligible', False, False, 0, 100.), 'True original ordinal not admitted')
    serial = call('tdPetHeroNextSerial', serial)
    require(call('tdPetHeroLaterHit', grant, serial), 'Next true original did not consume seal')
    for granting, attacking, lane, completed, valid, expected in (
            (10, 11, True, True, True, True), (10, 10, True, True, True, False),
            (0, 11, True, True, True, False), (10, 0, True, True, True, False),
            (10, 11, False, True, True, False), (10, 11, True, False, True, False),
            (10, 11, True, True, False, False)):
        require(call('tdPetHeroRelayEligible', granting, attacking, lane, completed, valid) == expected,
                'Invalid same-lane relay recipient accepted')
    for real_death, trial, original, consumed, now, expected in (
            (True, False, True, False, 2., True), (False, False, True, False, 2., False),
            (True, True, True, False, 2., False), (True, False, False, False, 2., False),
            (True, False, True, True, 2., False), (True, False, True, False, 3., False)):
        require(call('tdPetHeroDeathCanPropagate', real_death, trial, original, consumed, 3., now) == expected,
                'Secondary/replaced/trial/expired seed can propagate')


def verify_mutations(sources):
    changes = (
        ("return 'uA6A'", "return 'uA6B'"),
        ('return incomingPower >= power', 'return incomingPower > 0.0'),
        ('return grantSerial >= 0 and hitSerial > grantSerial',
         'return grantSerial >= 0 and hitSerial >= grantSerial'),
        ('if not realDeath or trialTarget or not originalSeed', 'if not realDeath or trialTarget'),
        ('current >= 2147483647', 'current > 2147483647'),
        ("codeDamage or spellDamage or eventId == 'Tspl' or eventId == 'Pdam'",
         "spellDamage or eventId == 'Tspl' or eventId == 'Pdam'"),
        ('return grantSerial > 0 and grantSerial == hitSerial',
         'return grantSerial > 0 and grantSerial <= hitSerial'),
        ('return incomingSerial > 0 and incomingSerial > existingSerial',
         'return incomingSerial > 0 and incomingSerial >= existingSerial'),
    )
    for before, after in changes:
        require(sources[RULES].count(before) == 1, 'Mutation root is missing or ambiguous')
        mutated = dict(sources)
        mutated[RULES] = mutated[RULES].replace(before, after)
        try:
            verify(mutated)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('Hero source mutation escaped: ' + before)


def verify_hooks_and_lifetimes(sources):
    members = {path: source_functions(text) for path, text in sources.items()}
    body = lambda path, name, arity: members[path][name, arity][1]
    runtime = uncomment(sources['pets/TDPetHeroRuntime.wurst'])
    state = uncomment(sources['pets/TDPetHeroState.wurst'])
    effects = uncomment(sources['pets/TDPetHeroEffects.wurst'])
    setup = body('pets/TDPetHeroRuntime.wurst', 'tdPetHeroSetup', 0)
    require('if serialReady' in setup and 'serialReady = true' in setup and
            setup.count('DamageEvent.addUnreducedListener(0)') == 1,
            'Hero original ordinal setup is not idempotent/single priority0')
    for path in ('pets/TDPetHeroState.wurst', 'pets/TDPetHeroEffects.wurst', 'pets/TDPetHeroRuntime.wurst'):
        source = uncomment(sources[path])
        require('doAfter(' not in source and 'doPeriodically' not in source,
                'Hero effects added a private timing framework: ' + path)
        require('TDTrialBinding ' not in source,
                'Hero task retained a destructible trial binding: ' + path)
    require('if targetCount == 1\n\t\t\tif not tdPetEnemyIsValid' in state and
            'if counter != null\n\t\tif counter.generation != pet.generation or' in state,
            'Hero lifetime guard shape left mixed AND/OR outside bounded replay coverage')
    require(state.count('override function runEffect(') == 2 and
            effects.count('override function runEffect(') == 2 and
            'override function step(' not in state + effects,
            'Hero tasks diverged from the shared reserved-word-safe runEffect contract')
    require('extends TDPetEffectTask' in state and 'tdPetRegisterEffectTask(ticket)' in state,
            'Hero ticket is outside the shared cancellable scheduler')
    require('pet.revision != revision' in state and
            'tdPetBindingValid(pet, host, generation)' in state and
            'tdTrialContextValid(context)' in state,
            'Hero task source lifetime guards are missing')
    weak = body('pets/TDPetHeroState.wurst', 'tdPetHeroWeakSpellDamage', 5)
    require(weak.index('secondaryDepth += 1') < weak.index('tdPetSpellDamage(') <
            weak.index('secondaryDepth -= 1') and 'return' not in weak[weak.index('secondaryDepth += 1'):],
            'Secondary guard does not surround exactly the synchronous damage call')
    damage = body('pets/TDPetHeroEffects.wurst', 'tdPetHeroQueueTicketDamage', 4)
    require('tdPetHeroIsSpellDamage(ticket.skill)' in damage and
            'tdPetDamage(pet, host, generation, target, amount)' in damage and
            'tdPetSpellDamage(pet, host, generation, target, amount)' in damage,
            'One-shot damage does not dispatch the approved school')
    primary = body('pets/TDPetHeroRuntime.wurst', 'tdPetHeroCapturePrimary', 11)
    require(primary.index('tdPetHeroQueueTicketDamage(judgement') <
            primary.index('tdPetHeroCommitPendingJudgement'),
            'New judgement committed before old seal consumed')
    require('tdCaptureEquipmentTrialAoe' not in state and
            'tdPetHeroStartRoot(pet, quality, rootAmount, center, context, capturedTargets, serial)' in primary and
            'snapshot = capturedTargets' in effects and
            'tdPetHeroAreaDamage(pet, host, generation, revision, center, tdPetHeroRadius(skill), tdPetHeroTargetCap(skill), amount, context, snapshot, false)' in effects,
            'Root pulse recaptures post-fence trial identities instead of the original early3 snapshot')
    pending = body('pets/TDPetHeroState.wurst', 'tdPetHeroCommitPendingJudgement', 2)
    require('tdPetHeroGrantCanCommit(ticket.grantSerial, serial)' in pending and
            'tdPetRegisterEffectTask' not in pending and 'ticket.expiry =' not in pending and
            'tdPetHeroGrantNewer(ticket.grantSerial, active.grantSerial)' in pending,
            'Pending seal re-registers, renews expiry, or overwrites a newer original')
    accepted = body('pets/TDPetHeroRuntime.wurst', 'tdPetHeroOnShieldAccepted', 4)
    require('tdPetHeroStorePendingJudgement(judgementTicket)' in accepted and
            'tdPetQueueAttack' not in accepted,
            'Judgement still defers installation beyond the current early3')
    for name, arity in (('tdPetHeroQueueTicketDamage', 4), ('tdPetHeroPropagatePoison', 2),
                        ('tdPetHeroExplodeGroup', 2)):
        callback = body('pets/TDPetHeroEffects.wurst', name, arity)
        require(callback.index('ticket.consume()') < callback.index('tdPetQueueAttack('),
                'One-shot ticket not consumed before queue: ' + name)
    forget = body('pets/TDPetHeroRuntime.wurst', 'tdPetHeroForgetEnemy', 2)
    require(forget.index('bucket.entries.remove(ticket)') < forget.index('tdPetHeroPropagatePoison') and
            'bucket.processing = true' in forget and 'bucket.processing = false' in forget and
            'not tdPetHeroSecondaryDeathBlocked()' in forget,
            'Enemy death does not detach before reentrant one-generation work')
    shield = body('items/TDShieldRuntime.wurst', 'tdTryEquipmentShieldProc', 3)
    require(shield.count('tdPetHeroOnShieldAccepted(') == 1 and
            shield.index('tdTryShieldStun(source, target, lane, level)') <
            shield.index('tdPetHeroOnShieldAccepted(') <
            shield.index('tdEquipmentHasSpecial(source, TD_ITEM_SPECIAL_SHIELD_SPREAD)'),
            'Seal grant is not exactly after accepted PRIMARY shield proc')
    require('tdPetHeroOnShieldAccepted(' not in body('items/TDShieldRuntime.wurst', 'tdTryShieldStun', 4),
            'Generic control/spread target also grants a seal')
    storm = body('towers/TDTowerRuntime.wurst', 'tdHandleOrcBladestormCast', 0)
    require(storm.index('tdPetHeroCaptureStorm') < storm.index('doPeriodicallyCounted') and
            'if cb.isLast()\n\t\t\t\ttdPetHeroCompleteStorm' in storm,
            'Storm hero snapshot/completion is not tied to the original full cast')
    corpse = body('towers/TDTowerRuntime.wurst', 'tdHandleGhoulCorpseExplosionDamage', 0)
    require(corpse.index('source.damageTarget(') < corpse.index('tdPetHeroOnCorpseExplosionSettled('),
            'Epidemic seeding ran before original corpse damage settled')
    require('tdPetHeroOnSplitArrowImpact(source, target)' in
            body('towers/TDTowerRuntime.wurst', 'tdDealArcherSplitArrowAttackDamage', 5),
            'Final archer hero is not hooked to actual secondary impact')
    death = body('TDGame.wurst', 'tdHandleEnemyDeath', 0)
    require(death.index('tdClaimEnemyKill(enemy)') < death.index('tdPetHeroForgetEnemy(enemy, true)') <
            death.index('let wave = tdEnemyWave(enemy)'),
            'Normal real-death propagation is not between claim and rewards/cleanup')
    require('tdPetHeroConsumeRelays' in runtime and 'tdPetHeroCapturePrimary' in runtime and
            'tdPetHeroAreaDamage' in effects,
            'Hero integration entry points are missing')



def verify_hook_mutations(sources):
    changes = (
        ('pets/TDPetHeroRuntime.wurst',
         'tdPetHeroStartRoot(pet, quality, rootAmount, center, context, capturedTargets, serial)',
         'tdPetHeroStartRoot(pet, quality, rootAmount, center, context, tdCaptureEquipmentTrialAoe(pet.lane, context), serial)'),
        ('pets/TDPetHeroEffects.wurst', 'snapshot = capturedTargets',
         'snapshot = tdCaptureEquipmentTrialAoe(pet.lane, context)'),
        ('pets/TDPetHeroState.wurst', 'snapshot = tdEquipmentTrialAoeSnapshot(null, 0, null, 0, null, 0, null, 0, null, 0)',
         'snapshot = tdCaptureEquipmentTrialAoe(pet.lane, context)'),
        ('pets/TDPetHeroState.wurst',
         'if targetCount == 1\n\t\t\tif not tdPetEnemyIsValid',
         'if targetCount == 1 and not tdPetEnemyIsValid'),
        ('pets/TDPetHeroState.wurst',
         'if counter != null\n\t\tif counter.generation != pet.generation or',
         'if counter != null and counter.generation != pet.generation or'),
        ('pets/TDPetHeroState.wurst', 'override function runEffect(real now)',
         'override function step(real now)'),
    )
    for path, before, after in changes:
        require(sources[path].count(before) == 1, 'Hook mutation root missing/ambiguous: ' + before)
        mutated = dict(sources)
        mutated[path] = mutated[path].replace(before, after)
        try:
            verify_hooks_and_lifetimes(mutated)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('Hero hook mutation escaped: ' + before)

def main():
    sources = read_sources(ROOT)
    verify(sources)
    verify_mutations(sources)
    verify_hooks_and_lifetimes(sources)
    verify_hook_mutations(sources)
    print(json.dumps({'status': 'PASS', 'scope': 'Wurst scalar source evaluation only',
                      'skills': 10, 'quality_values': 40, 'scalar_mutation_cases': 8, 'hook_mutation_cases': 6,
                      'rules_sha256': hashlib.sha256(sources[RULES].encode()).hexdigest(),
                      'wurst_compile': 'not run', 'jass_replay': 'not run',
                      'map_build': 'not run', 'gameplay': 'not run'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
