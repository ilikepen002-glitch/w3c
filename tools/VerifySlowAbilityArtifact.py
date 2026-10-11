#!/usr/bin/env python3
"""Verify enemy speed bounds and all poison/aura levels in a built map.

Usage: python tools/VerifySlowAbilityArtifact.py ExampleMap.w3x
Native displacement and stacking must also be tested in Warcraft III.
"""
import math
import re
import sys
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects


def check_field(fields, field, level, column, expected):
    kind, value = fields.get((field, level, column), (None, None))
    require(kind == 2 and math.isclose(value, expected, rel_tol=1e-6, abs_tol=1e-7),
            f'{field} level {level}: got {(kind, value)}, expected {expected}')


def validate_enemy_speed(units):
    enemies = [f'uE{wave:02X}' for wave in range(1, 33)]
    enemies += [f'uS{wave:02d}' for wave in (4, 12, 20, 28)]
    enemies += [f'u{family}{wave:02d}' for family in 'GB' for wave in (8, 16, 24, 32)]
    sprint_speeds = {
        'uS12': (270, 378),
        'uS20': (280, 392),
        'uS28': (285, 399),
        'uG32': (260, 364),
    }
    require(all(enemy in units for enemy in enemies), 'required enemy objects missing')
    for enemy in enemies:
        fields = units[enemy]
        require(230 <= fields['umvs'] <= 330, f'{enemy}: unexpected base speed')
        require(fields['umis'] == 1, f'{enemy}: speed floor blocks native slows')
        if enemy in sprint_speeds:
            require((fields['umvs'], fields['umas']) == sprint_speeds[enemy],
                    f'{enemy}: expected base/max {sprint_speeds[enemy]}')
        else:
            require(fields['umas'] == fields['umvs'], f'{enemy}: speed ceiling changed')


def validate_slow_abilities(abilities):
    for ability, move, attack, dps in [('A106', .22, .16, 12), ('A114', .22, .16, 14.4)]:
        parent, fields = abilities[ability]
        require(parent == 'Aspo', f'{ability}: wrong native parent')
        require(fields[('alev', 0, 0)] == (0, 61), f'{ability}: poison levels changed')
        for level in range(1, 62):
            check_field(fields, 'Spo1', level, 1, dps)
            check_field(fields, 'Spo2', level, 2, min(.70, move * (1 + (level - 1) / 100)))
            check_field(fields, 'Spo3', level, 3, attack)
            check_field(fields, 'adur', level, 0, 5)
            check_field(fields, 'ahdu', level, 0, 1)
            require(fields[('abuf', level, 0)] == (3, 'Bspo,Bssd'), f'{ability}: native poison buffs changed')
    for ability, radius, move in [('A110', 225, .18), ('A140', 265, .18), ('AeSL', 265, .216)]:
        require(ability in abilities, f'Missing slow ability {ability}')
        parent, fields = abilities[ability]
        require(parent == 'Aasl', f'{ability}: wrong native parent')
        require(fields.get(('alev', 0, 0)) == (0, 61), f'{ability}: control levels changed')
        for level in range(1, 62):
            check_field(fields, 'Slo1', level, 1, -min(.70, move * (1 + (level - 1) / 100)))
            check_field(fields, 'Slo2', level, 2, 0)
            check_field(fields, 'aare', level, 0, radius)
            require(fields.get(('atar', level, 0)) == (3, 'enemy,ground,air,organic'), f'{ability}/{level}: targets changed')
            require(fields.get(('abuf', level, 0)) == (3, 'Basl'), f'{ability}/{level}: native slow buff changed')
    for ability, radius, move in [('A135', 225, .18), ('A141', 265, .18), ('A136', 265, .216)]:
        require(ability in abilities, f'Missing slow display {ability}')
        parent, fields = abilities[ability]
        require(parent == 'AOcr', f'{ability}: display must inherit neutral critical strike')
        require(fields.get(('alev', 0, 0)) == (0, 61), f'{ability}: display levels changed')
        for level in range(1, 62):
            for field, column, expected in [('Ocr1', 1, 0.0), ('Ocr2', 2, 1.0), ('Ocr3', 3, 0.0)]:
                check_field(fields, field, level, column, expected)
            require(fields.get(('Ocr5', level, 5)) == (0, 0), f'{ability}/{level}: display must not confer never-miss')
            text = fields.get(('aub1', level, 0), (None, ''))[1]
            percent = min(.70, move * (1 + (level - 1) / 100)) * 100
            displayed = [float(value) for value in re.findall(r'(\d+(?:\.\d+)?)%', text)]
            displayed_radius = re.search(r'周围(\d+(?:\.\d+)?)范围', text)
            require(displayed_radius is not None and float(displayed_radius[1]) == radius and len(displayed) == 1 and math.isclose(displayed[0], percent, rel_tol=1e-6, abs_tol=.001), f'{ability}/{level}: slow display radius/reduction mismatch')
    for ability, chance, bonus in [('A104', 22.0, 20), ('A113', 26.4, 24)]:
        parent, fields = abilities[ability]
        require(parent == 'AHbh', f'{ability}: wrong native Bash parent')
        require(fields[('alev', 0, 0)] == (0, 61), f'{ability}: control levels changed')
        for level in range(1, 62):
            check_field(fields, 'adur', level, 0, 2 * (1 + (level - 1) / 100))
            check_field(fields, 'ahdu', level, 0, 1 + (level - 1) / 100)
            check_field(fields, 'Hbh1', level, 1, chance)
            check_field(fields, 'Hbh2', level, 2, 1.45)
            check_field(fields, 'Hbh3', level, 3, bonus)


def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    validate_enemy_speed(unit_objects(artifact.extract('war3map.w3u')))
    validate_slow_abilities(ability_objects(artifact.extract('war3map.w3a')))
    print('PASS: enemy speed bounds; all 61 poison, 225/265-range slow, neutral display and Bash control levels and unchanged native poison damage.')
    print('NOT TESTED: native displacement, buff application, stacking, or pathing.')


if __name__ == '__main__':
    main()

