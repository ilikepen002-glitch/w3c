#!/usr/bin/env python3
"""Verify actual packaged farmer command cells and collection icon.

Usage: python tools/VerifyPetUIArtifact.py ExampleMap.w3x
Optional resource verification: append the local Warcraft installation directory.
This checks object output/resources, not native UI rendering or dialog width.
"""
from pathlib import Path
import hashlib
import struct
import sys

from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEquipmentAbilityArtifact import ability_objects, check_ability, require


COLLECTION_ICON = r'ReplaceableTextures\CommandButtons\BTNPackBeast.blp'
EXPECTED = {
    'Pdep': (3, 0, 'E', 'ANcl'),
    'Prpr': (1, 1, 'R', 'Ahrp'),
    'A108': (2, 1, 'F', 'AEbl'),
    'A109': (3, 1, 'G', 'ANcl'),
    'Geqb': (1, 2, 'C', 'Aspb'),
    'Pcap': (2, 2, 'Q', 'ANcl'),
    'Pcol': (3, 2, 'W', 'ANcl'),
}
NATIVE_CELLS = {(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)}


def verify_icon(game_directory):
    for filename in ('War3Patch.mpq', 'War3x.mpq', 'war3.mpq'):
        archive = Mpq((game_directory / filename).read_bytes())
        if not archive.has(COLLECTION_ICON):
            continue
        data = archive.extract(COLLECTION_ICON)
        require(data[:4] in (b'BLP1', b'BLP2'), 'Collection icon is not BLP')
        width, height = struct.unpack_from('<II', data, 12)
        require((width, height) == (64, 64), 'Unexpected collection icon dimensions')
        print(f'PASS RESOURCE: {filename} / {COLLECTION_ICON}; '
              f'{len(data)} bytes; {width}x{height}; SHA256={hashlib.sha256(data).hexdigest()}')
        return
    raise ValueError('Collection icon missing from local game archives')



def field_value(fields, key, level=0):
    matches = [value for (name, lvl, _), (_, value) in fields.items()
               if name == key and lvl == level]
    require(len(matches) == 1, f'Missing/ambiguous field {key} level={level}')
    return matches[0]


def verify_pet_core(abilities, units):
    for rawcode in ('Pdep', 'Pc04'):
        targets = set(field_value(abilities[rawcode][1], 'atar', 1).split(','))
        require({'organic', 'mechanical', 'structure'}.issubset(targets),
                f'{rawcode}: deployment must target organic and mechanical towers; '
                f'actual targets={sorted(targets)}')
    capture_targets = {'neutral', 'enemy', 'ground', 'air', 'organic',
                       'invulnerable', 'vulnerable'}
    for level in range(1, 62):
        require(set(field_value(abilities['Pcap'][1], 'atar', level).split(','))
                == capture_targets,
                f'Pcap level {level}: ordinary capture target filter changed')
    models = [r'Units\Human\Phoenix\Phoenix.mdl',
              r'Units\NightElf\FaerieDragon\FaerieDragon.mdl',
              r'Units\NightElf\Wisp\Wisp.mdl']
    for species, model in enumerate(models, 1):
        display = units[f'pd0{species}']
        visual = units[f'pv0{species}']
        require(display['umdl'] == model and visual['umdl'] == model,
                f'Species {species}: incorrect dynamic model')
        require('Aloc' not in display['uabi'].split(','), 'Display must be selectable')
        require('Aloc' in visual['uabi'].split(','), 'Decoration must be non-selectable')
        require(display.get('ubdg') == 1 and display.get('uaen') == 0,
                'Display must be a stationary non-attacking building')
        require({f'Pc0{cmd}' for cmd in range(8)}.issubset(display['uabi'].split(',')),
                'Display misses native collection commands')
        for wave in range(1, 33):
            wild = units[f'p{wave:02X}{species}']
            require(wild['umdl'] == model and wild.get('uaen') == 0,
                    'Wild must use distinctive model and never attack')
            require(wild.get('ubba') == 0, 'Wild must have zero normal bounty')
    orders = []
    for cmd in range(8):
        _, fields = abilities[f'Pc0{cmd}']
        orders.append(field_value(fields, 'Ncl6', 1))
    require(len(set(orders)) == 8, 'Display command base orders collide')
    for slot in range(4):
        for variant in range(129):
            rawcode = f's{slot}{variant:02X}'
            parent, fields = abilities[rawcode]
            require(parent == 'AOcr', f'{rawcode}: skill display must be passive')
            require(not any(key == 'Ncl6' for key, _, _ in fields),
                    f'{rawcode}: passive display must not allocate channel orders')
            require(field_value(fields, 'abpx') == slot and field_value(fields, 'abpy') == 1,
                    f'{rawcode}: wrong fixed skill cell')
            if 64 <= variant < 128:
                require('CommandButtonsDisabled' in field_value(fields, 'aart'),
                        f'{rawcode}: locked skill icon must be gray')
                require('共鸣锁定' in field_value(fields, 'atp1', 1),
                        f'{rawcode}: locked skill must retain specific identity')
                require('解锁' in field_value(fields, 'aub1', 1),
                        f'{rawcode}: missing resonance explanation')
    _, book = abilities['Geqb']
    spell_list = field_value(book, 'spb1', 1).split(',')
    require({'Pmas', 'Phnt', 'Pfor'}.issubset(spell_list),
            'Equipment function menu lacks master/hunt/five-to-one entry')
    require(field_value(abilities['Pcap'][1], 'alev') == 61,
            'Capture inventory tooltip levels must cover 0..60')
    for rawcode, levels in [('Pbat', 512), ('Pbsp', 150), ('Pbar', 8)]:
        require(field_value(abilities[rawcode][1], 'alev') == levels,
                f'{rawcode}: incorrect synchronized level count')
    check_ability(abilities, 'Pbat', 'AIat', 512, 'Iatt', 0, lambda level: level)
    check_ability(abilities, 'Pbsp', 'AIsx', 150, 'Isx1', 2, lambda level: level / 100.0)
    check_ability(abilities, 'Pbar', 'AId1', 8, 'Idef', 0, lambda level: -level)
    print('PASS PET CORE OBJECTS: 96 wild, 3 selectable displays, 3 decorations; '
          '516 passive bright/gray/empty skill variants, eight distinct display command orders; '
          'function menu/master/hunt/five-to-one and 0..60 capture inventory levels.')

def main():
    require(len(sys.argv) in (2, 3), __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    units = unit_objects(artifact.extract('war3map.w3u'))
    occupied = set(NATIVE_CELLS)
    for rawcode, (x, y, key, parent) in EXPECTED.items():
        require(rawcode in abilities, f'Missing command {rawcode}')
        actual_parent, fields = abilities[rawcode]
        require(actual_parent == parent, f'{rawcode}: wrong parent {actual_parent}')
        require(fields.get(('abpx', 0, 0)) == (0, x), f'{rawcode}: wrong button X')
        require(fields.get(('abpy', 0, 0)) == (0, y), f'{rawcode}: wrong button Y')
        require(fields.get(('ahky', 0, 0)) == (3, key), f'{rawcode}: wrong hotkey')
        require((x, y) not in occupied, f'{rawcode}: cell overlaps native/another command')
        occupied.add((x, y))
    farmer_candidates = [(rawcode, fields) for rawcode, fields in units.items()
                         if set(EXPECTED).issubset(set(fields.get('uabi', '').split(',')))]
    require(len(farmer_candidates) == 1, 'Expected exactly one farmer with all seven commands')
    farmer_id, farmer = farmer_candidates[0]
    require('Ahrp' not in farmer['uabi'].split(','), 'Farmer still attaches conflicting original repair')
    require(abilities['Pcol'][1].get(('aart', 0, 0)) == (3, COLLECTION_ICON),
            'Collection icon path does not match verified resource')
    require(len(occupied) == 12, 'Farmer command grid must fill exactly twelve distinct cells')
    print(f'PASS OBJECTS: {farmer_id}; seven custom/native-cloned commands '
          'fill twelve distinct cells with observed 1.27a native commands; collection icon path matches.')
    verify_pet_core(abilities, units)
    if len(sys.argv) == 3:
        verify_icon(Path(sys.argv[2]))
    print('NOT TESTED: native rendering, actual command placement, collection icon display, native collection model/portrait/selection, passive icon cells, live skill effects.')


if __name__ == '__main__':
    main()


