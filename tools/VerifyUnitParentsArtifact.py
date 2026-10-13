#!/usr/bin/env python3
"""Check built map unit parents against the target game's actual unit catalog.

Usage: python VerifyUnitParentsArtifact.py ExampleMap.w3x path/to/War3Patch.mpq
The archive must contain the effective Units/UnitData.slk for the target game.
This catches valid-looking W3U definitions whose nonexistent parents cannot spawn.
"""
import re
import struct
import sys
from pathlib import Path
from GenerateTowerTerrainMask import Mpq


def unit_parents(data):
    version, = struct.unpack_from('<I', data)
    if version != 2:
        raise ValueError(f'Unsupported W3U version {version}')
    offset, parents = 4, {}
    for _ in range(2):
        count, = struct.unpack_from('<I', data, offset)
        offset += 4
        for _ in range(count):
            parent, new_id = data[offset:offset+4], data[offset+4:offset+8]
            fields, = struct.unpack_from('<I', data, offset+8)
            offset += 12
            object_id = (new_id if new_id != b'\0'*4 else parent).decode('ascii')
            if object_id in parents:
                raise ValueError(f'Duplicate unit {object_id}')
            parents[object_id] = parent.decode('ascii')
            for _ in range(fields):
                kind, = struct.unpack_from('<I', data, offset+4)
                offset += 8
                if kind == 3:
                    offset = data.index(0, offset) + 1
                elif kind in (0, 1, 2):
                    offset += 4
                else:
                    raise ValueError(f'{object_id}: unsupported field kind {kind}')
                offset += 4
    if offset != len(data):
        raise ValueError('Unexpected W3U trailing data')
    return parents


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    artifact, unit_archive = map(Path, sys.argv[1:])
    slk = Mpq(unit_archive.read_bytes()).extract('Units\\UnitData.slk')
    native_ids = set(re.findall(rb'^C;X1;Y\d+;K"([^"]{4})"', slk, re.M))
    if len(native_ids) < 100:
        raise ValueError(f'Could not parse target unit catalog: {unit_archive}')
    parents = unit_parents(Mpq(artifact.read_bytes()).extract('war3map.w3u'))
    missing = [(child, parent) for child, parent in parents.items()
               if parent.encode('ascii') not in native_ids]
    if missing:
        raise ValueError(f'Missing native unit parents in {unit_archive}: {missing}')
    print(f'PASS: {len(parents)} packaged units use valid case-sensitive parents; '
          f'{len(native_ids)} native IDs from {unit_archive.name}.')
    print('NOT TESTED: native creation, inherited stats, movement and visuals.')


if __name__ == '__main__':
    main()
