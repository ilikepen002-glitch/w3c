#!/usr/bin/env python3
"""All 22 legal four-slot actives, real packed battle traces under visual quotas.
Only the existing replay's native clock/handles/collections/engine callbacks are
boundaries. Damage, CD, RNG, targets, control and visual admissions execute JASS.
No Warcraft rendering, attachment placement or FPS assertion.
"""
from pathlib import Path
import argparse
import hashlib
import json
from GenerateTowerTerrainMask import Mpq
from VerifyElementalVfxArtifact import VfxRuntime, moving
from VerifyPetAttackArtifact import PetAttackRuntime
from VerifyEquipmentAbilityArtifact import require

SKILLS = (11, 12, *range(19, 39))
MODES = ('normal', 'null', 'full', 'moving-live', 'moving-rate', 'one-live', 'one-rate')


def reserve(r, count):
    accepted = sum(r.invoke('tdCombatVisualAcquireCast') for _ in range(count))
    require(accepted == count, 'Actual visual reservation failed '+str((count, accepted)))
    return accepted


def setup_mode(r, mode):
    held = 0
    # Identical 20.10 cast clock for every baseline/candidate/quota fixture.
    r.now = 19.10
    if mode in ('full', 'one-live'):
        held += reserve(r, 120)
    r.now = 20.10
    if mode == 'null':
        r.reject_visual = True
    elif mode in ('full', 'one-live'):
        held += reserve(r, 8 if mode == 'full' else 7)
    elif mode == 'one-rate':
        held += reserve(r, 119)
    elif mode in ('moving-live', 'moving-rate'):
        serials = [r.invoke('tdCombatVisualNewSerial') for _ in range(4)]
        for serial in serials:
            for slot in (0, 1):
                require(r.invoke('tdCombatVisualCreateMoving', serial, slot, 101, 0,
                                 'war3mapImported\\TDPetVfxSwordArray.mdx', 0., 0., 100., 0., .75),
                        'Actual moving quota fixture could not reach eight')
        if mode == 'moving-rate':
            for serial in serials:
                r.invoke('tdCombatVisualClearMoving', serial)
            require(moving(r) == 0, 'Moving rate fixture retained live ownership')
        return held, serials
    return held, []


def state(r, pet):
    return {
        'at': round(r.now, 6),
        'taskCount': r.invoke('tdPetEffectTaskCount'),
        'active': r.invoke('TDPet_skillAt', pet, 3),
        'pending': r.globals['TDPet_pendingSkill'][pet],
        'readyAt': r.globals['TDPet_readyAt'][pet],
        'buffUntil': r.globals['TDPet_buffUntil'][pet],
        'buffSkill': r.globals['TDPet_buffSkill'][pet],
        'buffPower': r.globals['TDPet_buffPower'][pet],
        'rotation': r.globals['TDPet_resolveRotation'][pet],
        'hostAbilities': sorted(r.units[101]['abilities'].items()),
        'targets': [(target, r.units[target]['life'], r.units[target]['alive'], r.units[target]['speed'])
                    for target in range(102, 117)],
    }


def run(script, skill, mode):
    r = VfxRuntime(script)
    if skill in (11, 12):
        pet = PetAttackRuntime.pet(r, [(0, 1), (17, 1), (39, 1), (skill, 1)])
    else:
        pet = r.pet(skill)
    require(r.globals['TDPet_skillCount'][pet] == 4, 'Incomplete four-slot active fixture')
    require(sum(r.invoke('tdPetSkillIsActive', r.invoke('TDPet_skillAt', pet, slot))
                for slot in range(4)) == 1, 'Active fixture violated one-active contract')
    for target in range(102, 116):
        r.enemy(target)
    r.enemy(116, lane=1)
    r.visible_units = list(range(102, 117))
    held, moving = setup_mode(r, mode)
    original = r.emit(100.)
    states = [state(r, pet)]
    for frame in range(130):
        r.tick()
        # A bonus refresh at fixed native turns establishes the actual six-second
        # buff deadline without borrowing the visual lifetime as gameplay state.
        if skill in (11, 12) and frame in (118, 119, 120, 129):
            r.invoke('tdPetRefreshHost', 101, 0.)
        states.append(state(r, pet))
    trace = {
        'original': original,
        'damage': r.damage_trace,
        'controls': r.control_orders,
        'states': states,
        'rng': r.random_trace,
        'score': r.score(),
        'gold': sorted(r.player_resources.items()),
        'orders': r.orders,
    }
    require(r.invoke('tdPetEffectTaskCount') == 0, 'Active battle ownership did not finish')
    for serial in moving:
        r.invoke('tdCombatVisualClearMoving', serial)
    for _ in range(held):
        r.invoke('tdCombatVisualReleaseCast')
    r.invoke('tdCombatVisualShutdown')
    r.flush_fx_recycle()
    require(not r.visual_handles and not r.lightning_handles and r.invoke('tdCombatVisualShortCount') == 0,
            'Visual mode leaked actual native/shared ownership '+str((skill, mode)))
    return trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    script = Mpq(args.map.read_bytes()).extract('war3map.j').decode()
    base = Mpq(args.baseline.read_bytes()).extract('war3map.j').decode()
    records = []
    baseline_traces = []
    for skill in SKILLS:
        expected = run(base, skill, 'normal')
        trace_hash = hashlib.sha256(json.dumps(expected,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        baseline_traces.append({'skill':skill,'traceSHA256':trace_hash,'trace':expected})
        for mode in MODES:
            actual = run(script, skill, mode)
            require(actual == expected, 'Visual quota changed ordered battle trace '+str((skill, mode)))
            records.append({'skill': skill, 'mode': mode, 'identical': True,
                            'hits': len(actual['damage']), 'ticksCompared': len(actual['states']),
                            'traceSHA256':hashlib.sha256(json.dumps(actual,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
        print('all22 battle/quotas verified', skill, flush=True)
    result = {'status': 'PASS', 'skills': list(SKILLS), 'modes': list(MODES), 'cases': records,
              'baselineTraces':baseline_traces,
              'mapSHA256': hashlib.sha256(args.map.read_bytes()).hexdigest(),
              'baselineSHA256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
              'boundary': __doc__}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('cases','baselineTraces')}, indent=2))


if __name__ == '__main__':
    main()
