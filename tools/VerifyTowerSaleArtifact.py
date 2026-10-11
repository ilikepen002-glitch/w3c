#!/usr/bin/env python3
"""Verify packaged sale ability and its attachment to all 35 tower objects.
Usage: python tools/VerifyTowerSaleArtifact.py ExampleMap.w3x
"""
from pathlib import Path
import re
import sys

from GenerateTowerTerrainMask import Mpq, ROOT
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEquipmentAbilityArtifact import ability_objects, require


def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    towers = unit_objects(artifact.extract('war3map.w3u'))
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    catalog = (ROOT / 'wurst/towers/TDTowerCatalogData.wurst').read_text(encoding='utf-8')
    ids = re.findall(r"public constant int TD_(?:ARCHER|ORC|FOOT|DRYAD|GHOUL)_LEVEL_[A-Z0-9_]+_ID = '(.{4})'", catalog)
    require(len(ids) == len(set(ids)) == 35, 'Expected exactly 35 tower types')
    for tower_id in ids:
        attached = towers[tower_id]['uabi'].split(',')
        require(attached.count('A133') == 1, f'{tower_id}: sale ability attachment changed')
    parent, fields = abilities['A133']
    require(parent == 'ANcl', 'Sale ability must inherit Channel')

    def field(key, level=0, column=0):
        require((key, level, column) in fields, f'Missing sale field {key}')
        return fields[(key, level, column)][1]

    require(field('abpx') == 3 and field('abpy') == 1, 'Sale button must use free slot (3, 1)')
    require(field('ahky') == 'V', 'Sale hotkey must be V')
    require(field('Ncl2', 1, 2) == 0, 'Sale must be instant/no target')
    require(field('Ncl1', 1, 1) == 0, 'Sale must not channel')
    require(field('Ncl3', 1, 3) & 1, 'Sale button must be visible')
    require(field('amcs', 1) == 0 and field('acdn', 1) == 0, 'Sale must cost no mana or cooldown')
    order = field('Ncl6', 1, 6)
    require(bool(order), 'Missing Channel base order')
    for other_id, (other_parent, other_fields) in abilities.items():
        if other_id != 'A133' and other_parent == 'ANcl':
            for (key, _, _), (_, value) in other_fields.items():
                if key == 'Ncl6':
                    require(value != order, f'Sale shares Channel order with {other_id}')
    print('PASS: all 35 towers have A133; no-target visible V button (3, 1), zero mana/cooldown and independent Channel order verified.')
    print('NOT TESTED: native in-game sale/refund, cancelled upgrade, item drops and placement reuse.')


if __name__ == '__main__':
    main()
