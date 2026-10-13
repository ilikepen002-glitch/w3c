#!/usr/bin/env python3
"""Builder B source and actual command/book contracts; predecessor deletions separate.

Usage: python tools/VerifyBuilderControlArtifact.py --source-only
       python tools/VerifyBuilderControlArtifact.py map.w3x
"""
from pathlib import Path
import re
import sys
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects
from VerifyUnitParentsArtifact import unit_parents
from VerifySemanticIconArtifact import parse_objects
from VerifyBuilderConstructionArtifact import validate_builder_objects
from VerifyGroundItemArtifact import verify_global_channel_orders, verify_no_hunt_objects

ROOT = Path(__file__).resolve().parents[1]
B_REMOVED = ('A108', 'Prpr')
PREDECESSOR_REMOVED = ('Dsta', 'Pmas', 'Pfor')


def field(abilities, code, key, level=0, column=0):
    require(code in abilities, 'Missing command ' + code)
    require((key, level, column) in abilities[code][1], f'{code}: missing field {key}/{level}/{column}')
    return abilities[code][1][(key, level, column)][1]


def verify_builder_function_book(abilities, units):
    verify_no_hunt_objects(abilities, units)
    for code in ('Geqb', 'A119', 'Gupg'):
        require(code in abilities, 'Missing command ' + code)
    require(abilities['Geqb'][0] == 'Aspb', 'Book must inherit Spell Book')
    require(field(abilities, 'Geqb', 'spb1', 1, 1) == 'A119', 'Book must contain only A119; no duplicate Gupg entry')
    require(field(abilities, 'Geqb', 'spb2', 1, 2) == 0, 'Book must not share cooldowns')
    require(field(abilities, 'Geqb', 'spb3', 1, 3) == 1 and field(abilities, 'Geqb', 'spb4', 1, 4) == 1,
            'Book must contain exactly one spell')
    require((field(abilities, 'Geqb', 'abpx'), field(abilities, 'Geqb', 'abpy'), field(abilities, 'Geqb', 'ahky')) == (3, 0, 'C'),
            'Book must remain 3,0/C')
    require((field(abilities, 'A119', 'abpx'), field(abilities, 'A119', 'abpy'), field(abilities, 'A119', 'ahky')) == (0, 0, 'C'),
            'A119 must remain book 0,0/C')
    require(abilities['Gupg'][0] == 'ANcl', 'Gupg must inherit Channel')
    require((field(abilities, 'Gupg', 'abpx'), field(abilities, 'Gupg', 'abpy'), field(abilities, 'Gupg', 'ahky')) == (1, 1, 'U'),
            'Gupg must occupy main bar 1,1/U')
    require(field(abilities, 'Gupg', 'Ncl2', 1, 2) == 2 and field(abilities, 'Gupg', 'Ncl3', 1, 3) & 3 == 3,
            'Gupg must retain visible point target/image')
    require(field(abilities, 'Gupg', 'aare', 1) == 144.0, 'Gupg area changed')
    candidates = [(uid, fields) for uid, fields in units.items() if 'Geqb' in fields.get('uabi', '').split(',')]
    require(len(candidates) == 1, 'Expected exactly one function-book farmer')
    uid, farmer = candidates[0]
    require(farmer['uabi'].split(',') == ['AUbu', 'A109', 'A117', 'Geqb', 'Gupg', 'Pcap', 'Pcol'],
            'Farmer exact command attachment/order changed')
    return uid, verify_global_channel_orders(abilities)


def verify_no_removed_controls(abilities, units):
    for group, codes in [('B blink/repair', B_REMOVED), ('predecessor master/rank', PREDECESSOR_REMOVED)]:
        for code in codes:
            require(code not in abilities and code not in units, f'{group}: removed object {code} remains')
            pattern = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(code) + r'(?![A-Za-z0-9_])')
            for uid, (parent, fields) in abilities.items():
                require(parent != code, f'{group}: removed parent {code} remains')
                for _, value in fields.values():
                    require(not isinstance(value, str) or not pattern.search(value), f'{group}: {uid} references removed {code}')
            for uid, fields in units.items():
                for value in fields.values():
                    require(not isinstance(value, str) or not pattern.search(value), f'{group}: {uid} references removed {code}')


def verify_no_removed_raw_controls(objects, label):
    """Check IDs, raw parents and string references in every packed object table."""
    for group, codes in [('B blink/repair', B_REMOVED), ('predecessor master/rank', PREDECESSOR_REMOVED)]:
        for code in codes:
            pattern = re.compile(r'(?<![A-Za-z0-9_])' + re.escape(code) + r'(?![A-Za-z0-9_])')
            for uid, obj in objects.items():
                require(uid != code and obj.identity[:4].decode('ascii') != code,
                        f'{group}: {label}/{uid} removed object/parent {code} remains')
                for key, item in obj.fields.items():
                    require(item.kind != 3 or not pattern.search(item.value),
                            f'{group}: {label}/{uid} references removed {code} in {key[0]}')


def verify_raw_control_tables(artifact):
    for name, extended in [('war3map.w3u', False), ('war3map.w3a', True), ('war3map.w3t', False),
                           ('war3map.w3b', False), ('war3map.w3d', True), ('war3map.w3h', False), ('war3map.w3q', True)]:
        if artifact.has(name):
            verify_no_removed_raw_controls(parse_objects(artifact.extract(name), extended), name)


def validate_control_sources(catalog, common, tower_objects, pet_data, pet_objects, item_data, item_objects, startup):
    for source in (catalog, common, tower_objects, pet_data, pet_objects):
        for token in ('TD_FARMER_BLINK_ABILITY_ID', 'TD_FARMER_REPAIR_ABILITY_ID', 'TD_FARMER_MENU_REPAIR_ABILITY_ID', 'tdFarmerBlink'):
            require(token not in source, 'Unused blink/repair source remains: ' + token)
    require('TD_FARMER_GROUND_UPGRADE_ABILITY_ID.toRawCode()' in tower_objects, 'Gupg must attach to farmer main bar')
    require('setSpellList(1, TD_FARMER_CRAFT_ABILITY_ID.toRawCode())' in item_objects, 'Book source must contain only A119')
    require('setMinimumSpells(1, 1)' in item_objects and 'setMaximumSpells(1, 1)' in item_objects, 'Book source must have exact min/max1')
    for name, value in [('tdFarmerGroundUpgradeButtonX', '1'), ('tdFarmerGroundUpgradeButtonY', '1'), ('tdFarmerGroundUpgradeHotkey', '"U"')]:
        require(re.search(r'function ' + name + r'\(\) returns \w+\n\treturn ' + re.escape(value) + r'\n', item_data),
                'Ground upgrade source position/key changed: ' + name)
    require('presetButtonPosNormal(tdFarmerGroundUpgradeButtonX(), tdFarmerGroundUpgradeButtonY())' in item_objects,
            'Ground upgrade must use main-bar position configuration')
    require('U 范围升级' in startup and 'C 背包合成' in startup and 'F 闪烁' not in startup, 'Startup controls are stale')


def main():
    require(len(sys.argv) in (2, 4), __doc__)
    if sys.argv[1] == '--source-only':
        validate_control_sources(*[(ROOT / path).read_text() for path in
                                  ('wurst/towers/TDTowerCatalogData.wurst', 'wurst/towers/TDTowerCommonData.wurst',
                                   'wurst/towers/TDTowerObjectGen.wurst', 'wurst/pets/TDPetData.wurst', 'wurst/pets/TDPetObjectGen.wurst',
                                   'wurst/items/TDItemData.wurst', 'wurst/items/TDItemObjectGen.wurst', 'wurst/TDInit.wurst')])
        print('PASS STATIC B SOURCE: blink/repair removed, main Gupg, single A119 book, updated startup guide.')
        print('Predecessor master/rank removals are inherited from formal A; no source-only result claims a new artifact.')
        return
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    verify_raw_control_tables(artifact)
    data = artifact.extract('war3map.w3u')
    units = unit_objects(data)
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    validate_builder_objects(units, unit_parents(data))
    verify_no_removed_controls(abilities, units)
    uid, channels = verify_builder_function_book(abilities, units)
    from VerifyPetUIArtifact import verify_farmer_grid, verify_collection_commands
    verify_farmer_grid(abilities, units)
    verify_collection_commands(abilities)
    print(f'PASS ARTIFACT: {uid}, exact 11 cells with 2,1 empty; Gupg main 1,1/U, book only A119; {channels} globally unique Channels.')
    if len(sys.argv) == 4:
        import json
        from VerifyBuilderControlDelta import validate_closed_control_delta
        require(sys.argv[2] == '--baseline-map', 'Expected --baseline-map')
        proof = validate_closed_control_delta(artifact, Mpq(Path(sys.argv[3]).read_bytes()))
        print('PASS B-ONLY CLOSED DELTA:', json.dumps(proof, sort_keys=True))
    print('NOT TESTED: native Warcraft 1.27a button rendering or live commands.')


if __name__ == '__main__':
    main()
