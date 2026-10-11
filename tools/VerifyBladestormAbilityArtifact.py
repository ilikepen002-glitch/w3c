#!/usr/bin/env python3
"""Check the native Bladestorm cast range in a built map.

Usage: python tools/VerifyBladestormAbilityArtifact.py ExampleMap.w3x
The runtime damage radius is covered separately by TDTowersTests.
"""
from pathlib import Path
import struct
import sys
import math

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require


def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    objects = ability_objects(artifact.extract('war3map.w3a'))
    require('A132' in objects, 'Missing Bladestorm ability A132')
    parent, fields = objects['A132']
    require(parent == 'Aslo', f'A132: expected Slow parent Aslo, got {parent!r}')
    ranges = {key: value for key, value in fields.items() if key[0] == 'aran'}
    require(fields.get(('alev', 0, 0)) == (0, 41), 'A132: expected 41 cooldown levels')
    require(ranges == {('aran', level, 0): (2, 780.0) for level in range(1, 42)},
            'A132: all 41 cast ranges must be 780')
    for level in range(1, 42):
        require(fields.get(('Slo3', level, 3)) == (0, 1), 'A132: Always Autocast must be enabled')
        for field, column in [('Slo1', 1), ('Slo2', 2)]:
            require(fields.get((field, level, column)) == (2, 0.0),
                    f'A132: carrier {field} level {level} must not slow')
        cooldown = fields.get(('acdn', level, 0), (None, None))
        require(cooldown[0] == 2 and math.isclose(cooldown[1], 9 * (1 - (level - 1) / 100), rel_tol=1e-6),
                f'A132: incorrect cooldown at level {level}')
        require(fields.get(('abuf', level, 0)) == (3, ''), f'A132: unexpected carrier buff at {level}')
    tooltip = fields.get(('aub1', 1, 0), (None, ''))[1]
    require(isinstance(tooltip, str) and '780' in tooltip and '范围不受装备射程影响' in tooltip,
            'A132: tooltip must explain the fixed 780 spell range')
    print('PASS: A132 inherits Aslo, native range780, zero native slowing, Always Autocast, fixed-range tooltip.')
    print('NOT TESTED: runtime damage, animation, autocast, and balance in game.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, struct.error, OSError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
