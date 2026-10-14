#!/usr/bin/env python3
"""Replay packed corpse display lifecycle, current values and neutral native fields.
Native ability state is modeled; this is not Warcraft tooltip rendering.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEvolutionArtifact import validate_branch_displays
from VerifyEvolutionProjectionReplay import ProjectionRuntime
from VerifyTowerUpgradeArtifact import rawcode, validate_evolution_jass

CORPSE = rawcode('A116')
ROOT = Path(__file__).resolve().parents[1]


def verify(path):
    data = Path(path).read_bytes()
    mpq = Mpq(data)
    script = mpq.extract('war3map.j').decode('utf-8')
    abilities = ability_objects(mpq.extract('war3map.w3a'))
    units = unit_objects(mpq.extract('war3map.w3u'))
    validate_branch_displays(units, abilities)
    validate_evolution_jass(script, units, abilities)
    # Unchanged actual combat implementation, including pre-hit life and lethal-hit gates.
    for name in ['TDTowerRuntime', 'TDTowerCommonData', 'TDTowerCatalogData']:
        file = 'wurst/towers/' + name + '.wurst'
        before = subprocess.check_output(['git', 'show', '96bddd3d:' + file], cwd=ROOT)
        require((ROOT / file).read_bytes() == before, name + ': gameplay source changed')
    rows = []
    for uid in ['uG11', 'uG12', 'uG13', 'uG14', 'uG15', 'uG6A', 'uG6B']:
        r = ProjectionRuntime(script)
        tower = r.make_tower(7800, type_id=uid)
        expected = 3 if uid == 'uG6B' else 1
        require(r.units[tower]['abilities'][CORPSE] == expected, uid + ': wrong initial display')
        r.ability_trace.clear()
        for _ in range(3):
            r.invoke('tdEvolutionRefresh', tower)
        require(not any(name == 'SetUnitAbilityLevel' and args[1] == CORPSE for name, args in r.ability_trace), uid + ': unchanged display rewritten')
        # Native restoration/corruption gets corrected from actual rawcode, not cached tier.
        r.units[tower]['abilities'][CORPSE] = 2 if expected != 2 else 1
        r.invoke('tdEvolutionRefresh', tower)
        require(r.units[tower]['abilities'][CORPSE] == expected, uid + ': wrong repaired display')
        if uid in ('uG6A', 'uG6B'):
            r.settle()
            ticket = r.request(tower); require(ticket, uid + ': missing preview')
            r.click(ticket, confirm=False)
            require(r.units[tower]['abilities'][CORPSE] == expected, uid + ': preview cancel changed display')
            r.click(r.request(tower))
            expected = 2 if uid == 'uG6B' else 1
            require(r.units[tower]['abilities'][CORPSE] == expected, uid + ': wrong evolved display')
            r.invoke('tdEvolutionRefresh', tower)
            require(r.units[tower]['abilities'][CORPSE] == expected, uid + ': refresh reverted evolution')
        rows.append({'unit': uid, 'final_display': expected})
    for target in ('uG12', 'uG6A', 'uG6B'):
        source = 'uG11' if target == 'uG12' else 'uG15'
        r = ProjectionRuntime(script); tower = r.make_tower(7900, type_id=source)
        r.event_target = tower
        r.invoke('tdHandleTowerUpgradeStarted')
        # Engine upgrade completion swaps rawcode and restores native default level.
        r.units[tower]['type'] = rawcode(target)
        r.units[tower]['abilities'][CORPSE] = 1
        r.invoke('tdHandleTowerUpgradeFinished')
        require(r.units[tower]['abilities'][CORPSE] == (3 if target == 'uG6B' else 1), target + ': completion not projected')
        r.invoke('tdHandleTowerSellCast')
        r.make_tower(tower, type_id=source)
        require(r.units[tower]['abilities'][CORPSE] == 1 and not r.invoke('tdTowerIsEvolved', tower), 'Sold/recreated handle retained display state')
        r.invoke('tdHandleTowerUpgradeStarted')
        r.invoke('tdHandleTowerUpgradeCancelled')
        r.units[tower]['type'] = rawcode(source)
        r.units[tower]['abilities'][CORPSE] = 3
        r.drain_zero()
        require(r.units[tower]['abilities'][CORPSE] == 1, target + ': cancelled upgrade not projected')
    return {'status': 'PASS', 'sha256': hashlib.sha256(data).hexdigest(), 'nodes': rows,
            'upgrade_edges': 3, 'native_display_levels': 3,
            'combat_sources_unchanged': True, 'damage_matrix': 'tiers 1–5 and A:180; B:270; evolved B:324',
            'not_tested': 'Warcraft native rendering/input'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    report = json.dumps(verify(args.map), ensure_ascii=False, indent=2) + '\n'
    if args.output: args.output.write_text(report)
    print(report)
