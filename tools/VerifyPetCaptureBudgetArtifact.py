#!/usr/bin/env python3
"""Read-only capture replay. Engine events, handles, random rolls and native
operations are controlled boundaries. Counts are interpreter expression/function
calls, never Warcraft opcodes or an assertion of a live-engine threshold."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd() / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyPetAttackArtifact import PetAttackRuntime
from VerifyTowerUpgradeArtifact import rawcode

class CaptureRuntime(PetAttackRuntime):
    expressions = 0
    def expression(self, text, scope):
        self.expressions += 1
        # The shared interpreter rejects even explicitly grouped mixed logic.
        # Preserve the exact parenthesized settle guard; do not normalize JASS.
        if text.startswith('TDPetWildState_state[') and ' or (nextState != TDPetWildState_TD_PET_WILD_CAPTURED and nextState != TDPetWildState_TD_PET_WILD_EXPIRED)' in text:
            left, right = text.split(' or ', 1)
            return self.expression(left, scope) or self.expression(right, scope)
        return super().expression(text, scope)
    def native(self, name, args):
        # Count expressions separately; permit the old finite, very large replay.
        if self.executed_steps > 1000000: self.executed_steps = 0
        if name == 'GetRandomInt':
            value = min(args[1], max(args[0], self.roll_value))
            self.random_trace.append((args[0], args[1], value))
            return True, value
        if name == 'GetTriggerUnit': return True, 101
        if name == 'GetSpellTargetUnit': return True, 102
        if name == 'widget_flashEffect': return False, None
        if name == 'DisplayTimedTextToPlayer':
            self.notices.append(args[-1]); return True, None
        if name == 'tdPetStore' and getattr(self, 'reject_store', False): return True, False
        return super().native(name, args)

def replay(script, case, roll=1, species=1):
    r = CaptureRuntime(script)
    r.roll_value, r.random_trace, r.notices = roll, [], []
    r.units[101].update(type=rawcode('uF01'), owner=0)
    r.units[102].update(type=rawcode('p01' + format(species, 'X')), owner=15)
    r.globals['TDPetRuntime_tdPetFarmers'][0] = 101
    wild = r.invoke('new_TDPetWildRecord', 102, 1 if case == 'crosslane' else 0, 1, species)
    r.globals['TDPetWildRecord_tutorial'][wild] = case != 'failure'
    r.lists[r.globals['TDPetWild_tdPetWildRecords']].append(wild)
    r.invoke('tdPetInitializeLane', 0)
    if case == 'no_ball': r.globals['TDPetState_tdPetBalls'][0] = 0
    if case == 'full':
        for _ in range(20): assert r.invoke('tdPetStore', 0, r.invoke('new_TDPet', 0, species, 1))
    r.reject_store = case == 'refund'
    before_expr, before_calls = r.expressions, sum(r.calls.values())
    r.invoke('tdPetHandleCapture')
    metrics = (r.expressions - before_expr, sum(r.calls.values()) - before_calls)
    count = r.invoke('tdPetCollectionCount', 0)
    pet = r.invoke('tdPetAt', 0, 0)
    skills = [(r.invoke('TDPet_skillAt', pet, i), r.invoke('TDPet_qualityAt', pet, i)) for i in range(r.globals['TDPet_skillCount'][pet])] if pet else []
    result = (r.invoke('tdPetBallsForLane', 0), count, skills, r.random_trace, r.notices, r.globals['TDPetState_tdPetTutorialUsed'][0], r.globals['TDPetWildState_state'][wild])
    expected = {'success': (2, 1, '捕获成功'), 'failure': (2, 0, '捕获失败'), 'no_ball': (0, 0, '捕获球不足'), 'full': (3, 20, '收藏已满'), 'crosslane': (3, 0, '本路'), 'refund': (3, 0, '已退还')}
    balls, size, notice = expected[case]
    assert result[:2] == (balls, size), (case, result)
    assert len(r.notices) == 1 and notice in r.notices[0], (case, r.notices)
    return result, metrics

def verify_four_slot_capture(result, roll, species, case):
    """New RNG is intentional; assert its own exact trajectory and legal roles."""
    from VerifyPetUIArtifact import four_slot_allowed
    if case not in ('success', 'refund'):
        expected_trace = [(1, 100, 100)] if case == 'failure' else []
        assert result[3] == expected_trace, (case, result[3])
        return
    count = 2 if roll <= 55 else 3 if roll <= 90 else 4
    quality = 1 if roll <= 45 else 2 if roll <= 75 else 3 if roll <= 95 else 4
    trace = [(1, 100, roll)]
    attribute = min(3, max(0, roll))
    attack_pool = [5, 6, 7, 8, 16, 17, 18]
    attack = attack_pool[min(6, max(0, roll))]
    expected_skills = [(attribute, quality), (attack, quality)]
    trace += [(1, 100, roll), (0, 3, attribute), (1, 100, roll), (0, 6, min(6, max(0, roll)))]
    if count >= 3:
        pool = [skill for skill in attack_pool if skill != attack] if roll <= 80 else list(range(39, 49))
        index = min(len(pool) - 1, max(0, roll))
        expected_skills.append((pool[index], quality))
        trace += [(1, 100, roll), (1, 100, roll), (0, len(pool) - 1, index)]
    if count == 4:
        elemental = 19 + ((species - 1) // 3) * 4 + quality - 1
        expected_skills.append((elemental if roll <= 50 else 11 if roll <= 75 else 12, quality))
        trace += [(1, 100, roll), (1, 100, roll)]
    assert len(trace) == {2: 5, 3: 8, 4: 10}[count]
    assert result[3] == trace, (case, roll, 'new RNG trace', result[3], trace)
    if case == 'success':
        assert result[2] == expected_skills, (case, roll, 'new skills/quality', result[2], expected_skills)
        assert all(four_slot_allowed(skill, slot) for slot, (skill, _) in enumerate(result[2])), result[2]
        assert len({skill for skill, _ in result[2]}) == count, 'Captured duplicate identity'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path); p.add_argument('--baseline', type=Path, required=True)
    args = p.parse_args()
    scripts = [Mpq(path.read_bytes()).extract('war3map.j').decode() for path in [args.baseline, args.map]]
    from VerifyDamageRankingJass import functions
    four_slots = 'tdPetSkillIsAttackPassive' in functions(scripts[1])
    for case, roll, species in [('success',1,1), ('success',60,7), ('success',95,13), ('failure',100,1), ('no_ball',1,4), ('full',1,10), ('crosslane',1,1), ('refund',1,1)]:
        old, a = replay(scripts[0],case,roll,species)
        new, b = replay(scripts[1],case,roll,species)
        if four_slots:
            # Capture shape and summary intentionally changed. Preserve atomic
            # inventory/tutorial/wild outcomes and verify the new exact draws.
            assert old[:2] == new[:2] and old[5:] == new[5:], (case, roll, old, new)
            verify_four_slot_capture(new, roll, species, case)
            if case not in ('success', 'refund'):
                assert old == new, (case, roll, old, new)
            if case in ('success', 'refund'):
                assert b[0] < 100000 and b[1] < 10000, ('Four-slot bounded interpreter work exceeded', case, b)
        else:
            assert old == new, (case, roll, old, new)
            if case in ('success','refund'): assert b[0] < a[0] / 5, ('Capture budget reduction insufficient', a, b)
        print('PASS',case,'roll',roll,'species',species,'expressions/calls',a,'->',b,flush=True)
    print('PASS: actual capture spend/refund/terminal states preserved; exact new5/8/10-draw role contract verified.' if four_slots else
          'PASS: actual capture outcome, exact RNG trace, skills/quality, spend/refund and messages preserved.')
    print('NOT a Warcraft engine reproduction; interpreter work counts are not native opcodes.')
if __name__ == '__main__': main()
