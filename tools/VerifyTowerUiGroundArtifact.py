"""Verify compiled tower UI, final upgrades, bloodlust and enemy attack flags.

Usage: python tools/VerifyTowerUiGroundArtifact.py map.w3x [terrain-report.json]
The optional independent terrain report also checks all 300 sorting positions.
"""
import json
import re
import sys
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEquipmentAbilityArtifact import ability_objects


def main():
    mpq = Mpq(Path(sys.argv[1]).read_bytes())
    units = unit_objects(mpq.extract('war3map.w3u'))
    abilities = {code: (parent, {(key, level): value for (key, level, column), (kind, value) in fields.items()}) for code, (parent, fields) in ability_objects(mpq.extract('war3map.w3a')).items()}
    for family in 'AOH DG'.replace(' ', ''):
        for level in range(1, 6):
            expected = f'u{family}1{level + 1}' if level < 5 else f'u{family}6A,u{family}6B'
            assert units[f'u{family}1{level}']['uupt'] == expected
        for branch in 'AB':
            code = f'u{family}6{branch}'
            assert 'uupt' in units[code], f'{code}: missing explicit upgrade override'
            assert units[code]['uupt'] == '', (code, 'inherited upgrade')
    for unit, required in [('uD6B', {'A110', 'A135'}), ('uG6A', {'A107', 'A137'}), ('uO15', {'A103', 'A139'})]:
        assert required <= set(units[unit]['uabi'].split(',')), (unit, 'missing display')
    for code, levels in [('A135', 61), ('A136', 61), ('A137', 1), ('A138', 1), ('A139', 1)]:
        parent, fields = abilities[code]
        assert parent == 'AOcr', (code, parent)
        assert fields['aher', 0] == 0 and fields['aite', 0] == 0
        assert fields['alev', 0] == levels
        assert fields['aart', 0] and fields['arar', 0]
        assert fields['abpx', 0] == (0 if code in ('A137', 'A138') else 1)
        assert fields['abpy', 0] == 1
        for level in range(1, levels + 1):
            for key, expected in [('Ocr1', 0), ('Ocr2', 1), ('Ocr3', 0), ('Ocr5', 0)]:
                assert fields[key, level] == expected, (code, key, level)
            assert fields['atp1', level] and fields['aub1', level]
    for level in range(1, 42):
        assert abilities['A131'][1]['atar', level] == 'self,structure,vulnerable'
    source = Path('wurst/TDWaves.wurst').read_text(encoding='utf-8')
    enemies = re.findall(r"constant int TD_WAVE_\w+_UNIT_ID = '(.{4})'", source)
    assert len(enemies) == 44, f'Expected all 44 enemy variants, found {len(enemies)}'
    for code in enemies:
        assert units[code]['uaen'] == 0 and units[code]['uacq'] == 0, (code, 'enemy can attack')
    if len(sys.argv) > 2:
        report = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig'))
        assert len(report['cells']) == 300
        config = Path('wurst/TDConfig.wurst').read_text(encoding='utf-8')
        rules = Path('wurst/items/TDGroundItemRules.wurst').read_text(encoding='utf-8')
        assert 'lane == 0 ? -768.0 : (lane == 3 ? -1024.0 : 1024.0)' in config
        assert '2560.0 - (pileGroup - 1) * 256.0 : -2816.0 + (pileGroup - 1) * 256.0' in config
        assert '(ModuloInteger(cell, 5) - 2) * 32.0, (cell div 5 - 1) * 32.0' in rules
        for cell in report['cells']:
            lane, group, index = cell['lane'], cell['group'], cell['index']
            x = (-768 if lane == 0 else -1024 if lane == 3 else 1024) + (index % 5 - 2) * 32
            y = (2560 - (group - 1) * 256 if lane <= 1 else -2816 + (group - 1) * 256) + (index // 5 - 1) * 32
            assert (cell['x'], cell['y']) == (x, y)
            assert not cell['pathing'] & (2 | 4 | 8)
            assert cell['heightMax'] == cell['heightMin']
    print(f'PASS: 35 tower upgrade fields; passive function/display pairs; neutral displays; 41 bloodlust levels; {len(enemies)} attack-disabled enemies.')
    if len(sys.argv) > 2:
        print('PASS: all 300 sort cells match the independently inspected source terrain coordinates.')


if __name__ == '__main__':
    main()
