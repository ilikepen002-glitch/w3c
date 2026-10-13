#!/usr/bin/env python3
"""Verify only the approved corpse radius; keep damage, trigger and prices separate."""
import argparse
from pathlib import Path
import subprocess
from GenerateTowerTerrainMask import Mpq
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyPetManagerSource import function_body
from VerifyTowerUpgradeArtifact import JassScalarEvaluator

ROOT = Path(__file__).resolve().parents[1]


def rules(call):
    require(call('tdGhoulCorpseExplosionRadius') == 220., 'Corpse radius must be 220')
    require(call('tdGhoulCorpseExplosionDamage') == 180., 'Corpse base damage changed')
    require(call('tdGhoulCorpseExplosionLifeThreshold') == .25, 'Corpse trigger threshold changed')
    for level in range(1, 7):
        for branch in (1, 2):
            for evolved in (False, True):
                expected = 216. if level == 6 and branch == 2 and evolved else 180.
                require(call('tdGhoulCorpseExplosionDamageForBranch', level, branch, evolved) == expected, 'Corpse branch damage changed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', nargs='?', type=Path)
    args = parser.parse_args()
    evaluator = SourceScalarEvaluator(read_sources())
    rules(lambda name, *values: evaluator.call(name, list(values)))
    path = 'wurst/towers/TDTowerRuntime.wurst'
    current = function_body((ROOT / path).read_text(), 'tdHandleGhoulCorpseExplosionDamage')[1]
    old = function_body(subprocess.check_output(['git', 'show', '4567e0d:' + path], cwd=ROOT).decode(), 'tdHandleGhoulCorpseExplosionDamage')[1]
    require(current == old, 'Corpse trigger, victims, damage or callback logic changed')
    require('g.enumUnitsInRange(center, tdGhoulCorpseExplosionRadius())' in current, 'Corpse runtime bypasses the common radius')
    print('PASS CORPSE SOURCE: radius220; threshold25%; damage180/216; unchanged native enumeration/trigger body')
    if args.map:
        artifact = Mpq(args.map.read_bytes())
        script = artifact.extract('war3map.j').decode()
        jass = JassScalarEvaluator(script)
        rules(lambda name, *values: jass.call(name, list(values)))
        body = '\n'.join(jass.functions['tdHandleGhoulCorpseExplosionDamage'][1])
        require('tdGhoulCorpseExplosionRadius()' in body and 'group_enumUnitsInRange(' in body, 'Packed corpse enumeration no longer uses common radius')
        abilities = ability_objects(artifact.extract('war3map.w3a'))
        for level, damage in ((1, 180), (2, 216)):
            text = abilities['A116'][1]['aub1', level, 0][1]
            require('不高于25%' in text and '220范围' in text and f'{damage}伤害' in text, 'Packed corpse display mismatch')
        print('PASS CORPSE ARTIFACT: actual JASS radius220 and unchanged damage matrix; both native display levels say220')
    else:
        print('NOT RUN: Wurst checks/build, actual-map validation, Warcraft native victim enumeration')


if __name__ == '__main__':
    main()
