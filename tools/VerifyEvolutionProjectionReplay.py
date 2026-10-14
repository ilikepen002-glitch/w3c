#!/usr/bin/env python3
"""Measure actual packed evolution projection writes and retain native-state repair.

Every kill runs the map's complete tdEvolutionRefresh. The interpreter models
native ability levels; it does not simulate Warcraft rendering or performance.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerEvolutionReplay import EvolutionRuntime
from VerifyTowerUpgradeArtifact import rawcode, function_body

PROGRESS, STATUS, CHOOSE = map(rawcode, ('A130', 'AeEV', 'AeEC'))


class ProjectionRuntime(EvolutionRuntime):
    def __init__(self, script):
        self.ability_trace = []
        super().__init__(script)

    def native(self, name, args):
        if name in ('unit_removeAbility', 'unit_getAbilityLevel', 'unit_addAbility') and name in self.functions:
            return False, None
        if name in ('SetUnitAbilityLevel', 'UnitRemoveAbility', 'UnitAddAbility',
                    'GetUnitAbilityLevel', 'UnitMakeAbilityPermanent'):
            self.ability_trace.append((name, list(args)))
        return super().native(name, args)

    def view(self, tower):
        return {'abilities': dict(self.units[tower]['abilities']), 'qualified': self.qualified(),
                'spent': self.is_spent(), 'evolved': self.invoke('tdTowerIsEvolved', tower)}


def kills(script):
    r = ProjectionRuntime(script)
    tower = r.make_tower(7000, type_id='uA11')
    r.ability_trace.clear()
    states, steps = [], []
    for index in range(934):
        r.executed_steps = 0
        r.invoke('tdEvolutionRecordKill', tower, 0)
        require(r.units[tower]['abilities'][PROGRESS] == index + 2, 'Kill display lost exact progress')
        states.append(r.view(tower)); steps.append(r.executed_steps)
    counts = dict(collections.Counter(name for name, _ in r.ability_trace))
    levels = dict(collections.Counter(str(args[1]) for name, args in r.ability_trace if name == 'SetUnitAbilityLevel'))
    return states, {'kills': 934, 'native_calls': counts, 'set_level_by_ability': levels,
                    'interpreter_steps_total': sum(steps), 'interpreter_steps_min': min(steps),
                    'interpreter_steps_max': max(steps)}


def repairs(script):
    r = ProjectionRuntime(script)
    tower = r.make_tower(7100)
    out = {}
    def check(label, expected_status, expected_choose):
        r.invoke('tdEvolutionRecordKill', tower, 0)
        abilities = r.units[tower]['abilities']
        require(abilities.get(STATUS, 0) == expected_status and abilities.get(CHOOSE, 0) == expected_choose,
                'Full kill refresh failed to repair actual command-card state: ' + label)
        require(abilities.get(PROGRESS, 0) > 0, 'Progress ability not restored: ' + label)
        out[label] = r.view(tower)
    for ability, level, label in ((STATUS, 0, 'missing_status'), (STATUS, 4, 'wrong_status'),
                                  (PROGRESS, 0, 'missing_progress'), (CHOOSE, 1, 'unexpected_choose')):
        r.units[tower]['abilities'][ability] = level
        check(label, 1, 0)
    r.settle()
    r.units[tower]['abilities'].pop(CHOOSE)
    check('qualified_missing_choose', 0, 1)
    r.units[tower]['abilities'][STATUS] = 4
    check('qualified_unexpected_status', 0, 1)
    r.invoke('tdEvolutionWorkStarted', tower)
    check('working_status', 2, 0)
    r.units[tower]['abilities'].pop(STATUS)
    check('working_missing_status', 2, 0)
    r.invoke('tdEvolutionWorkFinished', tower)
    check('work_finished_choose', 0, 1)
    ticket = r.request(tower)
    require(ticket, 'Qualified confirmation fixture failed')
    r.click(ticket)
    check('evolved_status', 3, 0)
    r.units[tower]['abilities'].pop(STATUS)
    check('evolved_missing_status', 3, 0)
    other = r.make_tower(7200)
    tower = other
    check('spent_other_tower', 4, 0)
    r.units[tower]['abilities'][STATUS] = 1
    check('spent_wrong_status', 4, 0)
    return out


def mutation(script):
    body = function_body(script, 'tdEvolutionRecordKill')
    changed, count = re.subn(r'^\s*call tdEvolutionRefresh\([^\n]*\)\s*$', '', body, flags=re.M)
    require(count == 1, 'Full-kill-refresh mutation target missing')
    mutant = script.replace(body, changed, 1)
    caught = False
    try: repairs(mutant)
    except ValueError as error:
        require('Full kill refresh failed to repair' in str(error), 'Mutation failed for unrelated reason')
        caught = True
    require(caught, 'Missing full kill refresh was not detected')
    return {'skipped_full_kill_refresh_detected': True}


def read_map(path):
    data = path.read_bytes()
    script = Mpq(data).extract('war3map.j').decode('utf-8')
    return script, {'path': str(path.resolve()), 'map_sha256': hashlib.sha256(data).hexdigest(),
                    'jass_sha256': hashlib.sha256(script.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-map', type=Path, required=True)
    parser.add_argument('--candidate-map', type=Path)
    parser.add_argument('--source-commit')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline, metadata = read_map(args.baseline_map)
    states, report = kills(baseline)
    baseline_repairs = repairs(baseline)
    require(report['native_calls']['SetUnitAbilityLevel'] == 1868 and report['native_calls']['UnitRemoveAbility'] == 934,
            'Baseline ability write counts differ')
    result = {'baseline': metadata, 'baseline_kills': report, 'repair_cases': list(baseline_repairs)}
    if args.candidate_map:
        candidate, metadata = read_map(args.candidate_map)
        require(metadata['jass_sha256'] != result['baseline']['jass_sha256'], 'Candidate must be newly packed')
        candidate_states, report = kills(candidate)
        require(candidate_states == states, 'Per-kill final ability/qualification state changed')
        require(repairs(candidate) == baseline_repairs, 'Repair final state differs from baseline')
        require(report['native_calls'].get('SetUnitAbilityLevel') == 934 and report['native_calls'].get('UnitRemoveAbility', 0) == 0,
                'Stable kill projections still write unchanged state')
        require(report['set_level_by_ability'] == {str(PROGRESS): 934}, 'Non-progress ability rewritten on stable kill')
        result.update(candidate=metadata, candidate_kills=report, mutation=mutation(candidate))
    root = Path(__file__).resolve().parents[1]
    result['source_commit'] = args.source_commit or subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    result['boundary'] = 'Actual supplied MPQ JASS; native levels/handles are controlled. No Warcraft rendering, native ability application timing or FPS measurement.'
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
