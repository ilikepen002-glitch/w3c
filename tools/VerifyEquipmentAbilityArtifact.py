#!/usr/bin/env python3
"""Verify equipment ability definitions in an actual built map.

Usage: python tools/VerifyEquipmentAbilityArtifact.py ExampleMap.w3x

The installed 1.27a game defines attack-speed object alias AIsx, with engine
implementation code AIas. Custom W3A objects must inherit AIsx, not AIas.
This verifies packaged parents and every synchronization level; it does not
replace an in-game pickup/drop/re-pickup test.
"""
import math
from pathlib import Path
import struct
import sys

from GenerateTowerTerrainMask import Mpq


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ability_objects(data):
    require(len(data) >= 4, 'Truncated W3A header')
    version, = struct.unpack_from('<I', data)
    require(version == 2, f'Unsupported W3A version {version}')
    offset, objects = 4, {}
    for _ in range(2):
        count, = struct.unpack_from('<I', data, offset)
        offset += 4
        for _ in range(count):
            parent, new_id = data[offset:offset+4], data[offset+4:offset+8]
            field_count, = struct.unpack_from('<I', data, offset+8)
            offset += 12
            object_id = (new_id if new_id != b'\0'*4 else parent).decode('ascii')
            require(object_id not in objects, f'Duplicate ability object {object_id}')
            fields = {}
            for _ in range(field_count):
                key = data[offset:offset+4].decode('ascii')
                kind, level, column = struct.unpack_from('<III', data, offset+4)
                offset += 16
                if kind == 3:
                    end = data.index(0, offset)
                    value = data[offset:end].decode('utf-8')
                    offset = end+1
                else:
                    require(kind in (0, 1, 2), f'{object_id}: invalid field type {kind}')
                    value, = struct.unpack_from('<i' if kind == 0 else '<f', data, offset)
                    offset += 4
                require(offset+4 <= len(data), f'{object_id}: truncated end marker')
                offset += 4
                field = (key, level, column)
                require(field not in fields, f'{object_id}: duplicate field {field}')
                fields[field] = (kind, value)
            objects[object_id] = (parent.decode('ascii'), fields)
    require(offset == len(data), 'Unexpected trailing W3A bytes')
    return objects


def check_ability(objects, object_id, parent_id, level_count, field_id, field_kind, expected_value):
    require(object_id in objects, f'Missing equipment ability {object_id}')
    parent, fields = objects[object_id]
    require(parent == parent_id,
            f'{object_id}: parent {parent!r}, expected object alias {parent_id!r}; '
            'AIas is an engine code, not an inheritable 1.27a object alias')
    require(fields.get(('aite', 0, 0)) == (0, 1), f'{object_id}: item ability flag changed')
    # The four one-level abilities inherit their level count from the base object.
    levels = fields.get(('alev', 0, 0), (0, 1))
    require(levels == (0, level_count), f'{object_id}: expected {level_count} levels, got {levels}')
    values = {level: (column, kind, value)
              for (key, level, column), (kind, value) in fields.items() if key == field_id}
    raw_count = sum(key == field_id for key, _, _ in fields)
    require(raw_count == level_count and set(values) == set(range(1, level_count+1)),
            f'{object_id}: {field_id} must define exactly levels 1..{level_count}')
    for level in range(1, level_count+1):
        column, kind, value = values[level]
        require(column == 1 and kind == field_kind,
                f'{object_id}: invalid {field_id} encoding at level {level}')
        expected = expected_value(level)
        require(math.isfinite(value) and math.isclose(value, expected, rel_tol=1e-6, abs_tol=1e-7),
                f'{object_id}: level {level} value {value}, expected {expected}')


def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    objects = ability_objects(artifact.extract('war3map.w3a'))
    for object_id, bonus in [('A124', 0.12), ('A125', 0.20), ('A126', 0.32), ('A127', 0.48)]:
        check_ability(objects, object_id, 'AIsx', 1, 'Isx1', 2, lambda _level, value=bonus: value)
    check_ability(objects, 'A129', 'AIsx', 120, 'Isx1', 2, lambda level: level/100.0)
    check_ability(objects, 'A128', 'AIat', 128, 'Iatt', 0, lambda level: level)
    check_ability(objects, 'A134', 'AId1', 30, 'Idef', 0, lambda level: -level)
    parent, fields = objects['A131']
    require(parent == 'Ablo', 'A131: Bloodlust must retain native parent')
    require(fields.get(('alev', 0, 0)) == (0, 41), 'A131: expected 41 cooldown levels')
    for level in range(1, 42):
        cooldown = fields.get(('acdn', level, 0), (None, None))
        require(cooldown[0] == 2 and math.isclose(cooldown[1], 12 * (1 - (level - 1) / 100), rel_tol=1e-6),
                f'A131: incorrect cooldown at level {level}')
        require(fields.get(('abuf', level, 0)) == (3, 'Bblo'), f'A131: native buff missing at {level}')
    print('PASS: 5 attack-speed abilities inherit AIsx; four fixed bonuses and all 120 synchronization levels verified.')
    print('PASS: A128 inherits AIat; all 128 attack-bonus levels unchanged.')
    print('NOT TESTED: in-game ability creation and equipment pickup/drop/re-pickup.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, struct.error, OSError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
