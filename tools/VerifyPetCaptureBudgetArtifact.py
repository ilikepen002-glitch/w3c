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

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path); p.add_argument('--baseline', type=Path, required=True)
    args = p.parse_args()
    scripts = [Mpq(path.read_bytes()).extract('war3map.j').decode() for path in [args.baseline, args.map]]
    for case, roll, species in [('success',1,1), ('success',60,7), ('success',95,13), ('failure',100,1), ('no_ball',1,4), ('full',1,10), ('crosslane',1,1), ('refund',1,1)]:
        old, a = replay(scripts[0],case,roll,species)
        new, b = replay(scripts[1],case,roll,species)
        assert old == new, (case, roll, old, new)
        if case in ('success','refund'): assert b[0] < a[0] / 5, ('Capture budget reduction insufficient', a, b)
        print('PASS',case,'roll',roll,'species',species,'expressions/calls',a,'->',b,flush=True)
    print('PASS: actual capture outcome, exact RNG trace, skills/quality, spend/refund and messages preserved. NOT a Warcraft engine reproduction.')
if __name__ == '__main__': main()
