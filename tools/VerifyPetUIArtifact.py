#!/usr/bin/env python3
"""Verify packaged farmer/collection UI objects and self-contained 64px icons.

Usage: python tools/VerifyPetUIArtifact.py ExampleMap.w3x
Object/layout contracts and actual MPQ resources are checked; native rendering,
portrait rendering and in-game effects remain separate playtest observations.
"""
from pathlib import Path
import hashlib
import struct
import sys

from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEquipmentAbilityArtifact import ability_objects, check_ability, require

ROOT = Path(__file__).resolve().parents[1]
NORMAL_PREFIX = "ReplaceableTextures\\CommandButtons\\"
DISABLED_PREFIX = "ReplaceableTextures\\CommandButtonsDisabled\\DIS"
IMPORTED_PREFIX = "war3mapImported\\BTN"
ICON_STEMS = (
    'TDPetMenuTools', 'TDPetCollection', 'TDPetPrevious', 'TDPetNext',
    'TDPetReturnBuilder', 'TDPetDeploy', 'TDPetRecall', 'TDPetCultivate',
    'TDPetInfo', 'TDPetEmptySlot', 'TDPetFlamePhoenix',
    'TDPetStormFaerieDragon', 'TDPetGhostWisp',
)
EXPECTED = {
    'Geqb': (3, 0, 'C', 'Aspb'),
    'Prpr': (1, 1, 'R', 'Ahrp'),
    'A108': (2, 1, 'F', 'AEbl'),
    'A109': (3, 1, 'G', 'ANcl'),
    'Pcap': (1, 2, 'Q', 'ANcl'),
    'Pcol': (2, 2, 'W', 'ANcl'),
    'Pdep': (3, 2, 'E', 'ANcl'),
}
# Observed legacy native move/stop/hold/patrol/build cells stay unchanged.
NATIVE_CELLS = {(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)}
FARMER_ICONS = {'Geqb': 'TDPetMenuTools', 'Pcol': 'TDPetCollection', 'Pdep': 'TDPetDeploy'}
# x, y, hotkey, Channel target type, semantic icon, original base order.
COLLECTION_COMMANDS = {
    'Pc00': (0, 0, 'I', 0, 'TDPetCollection', 'web'),
    'Pc01': (1, 0, 'A', 0, 'TDPetPrevious', 'attributemodskill'),
    'Pc02': (2, 0, 'D', 0, 'TDPetNext', 'auraunholy'),
    'Pc03': (3, 0, 'R', 0, 'TDPetReturnBuilder', 'auravampiric'),
    'Pc04': (0, 2, 'E', 1, 'TDPetDeploy', 'autodispel'),
    'Pc05': (1, 2, 'Q', 0, 'TDPetRecall', 'autodispeloff'),
    'Pc06': (2, 2, 'C', 0, 'TDPetCultivate', 'autodispelon'),
    'Pc07': (3, 2, 'W', 0, 'TDPetInfo', 'autoentangle'),
}
SPECIES = (
    (r'Units\Human\Phoenix\Phoenix.mdl', 'TDPetFlamePhoenix'),
    (r'Units\NightElf\FaerieDragon\FaerieDragon.mdl', 'TDPetStormFaerieDragon'),
    (r'Units\NightElf\Wisp\Wisp.mdl', 'TDPetGhostWisp'),
)
SKILL_ICONS = (
    'BTNGauntletsOfOgrePower', 'BTNSteelMelee', 'BTNGlove', 'BTNBrilliance',
    'BTNCommand', 'BTNSlow', 'BTNFaerieFire', 'BTNCleavingAttack',
    'BTNCriticalStrike', 'BTNColdArrows', 'BTNDeathAndDecay', 'BTNBloodLust',
    'BTNInnerFire', 'BTNChainLightning', 'BTNImmolationOn', 'BTNCyclone',
)

SKILL_NAMES = ('坚韧之力', '战意', '疾攻', '灵感', '统御光环', '迟滞领域',
               '破甲印记', '连击蓄能', '处决追击', '分裂霜箭', '腐尸毒域',
               '狂热', '蓄力', '雷链', '火焰冲击', '风缚')
QUALITY_NAMES = ('|cffffffff白|r', '|cff40dd40绿|r', '|cff4090ff蓝|r', '|cffc060ff紫|r')


def icon_path(stem, disabled=False):
    return (DISABLED_PREFIX + 'BTN' if disabled else IMPORTED_PREFIX) + stem + '.blp'


def skill_icon_path(variant):
    if variant == 128:
        return icon_path('TDPetEmptySlot')
    name = SKILL_ICONS[(variant % 64) // 4]
    return (DISABLED_PREFIX if variant >= 64 else NORMAL_PREFIX) + name + '.blp'


def field_value(fields, key, level=0):
    matches = [value for (name, lvl, _), (_, value) in fields.items()
               if name == key and lvl == level]
    require(len(matches) == 1, f'Missing/ambiguous field {key} level={level}')
    return matches[0]


def verify_farmer_grid(abilities, units):
    occupied = {cell: 'native command' for cell in NATIVE_CELLS}
    for rawcode in EXPECTED:
        require(rawcode in abilities, f'Missing farmer command {rawcode}')
        fields = abilities[rawcode][1]
        cell = (field_value(fields, 'abpx'), field_value(fields, 'abpy'))
        require(cell not in occupied,
                f'{rawcode}: farmer cell overlaps {occupied.get(cell)} at {cell}')
        occupied[cell] = rawcode
    require(set(occupied) == {(x, y) for x in range(4) for y in range(3)},
            'Farmer command grid must fill exactly twelve distinct cells')
    for rawcode, (x, y, hotkey, parent) in EXPECTED.items():
        actual_parent, fields = abilities[rawcode]
        require(actual_parent == parent, f'{rawcode}: wrong parent {actual_parent}')
        actual = (field_value(fields, 'abpx'), field_value(fields, 'abpy'))
        require(actual == (x, y), f'{rawcode}: wrong farmer cell {actual}, expected {(x, y)}')
        require(field_value(fields, 'ahky') == hotkey, f'{rawcode}: wrong farmer hotkey')
    candidates = [(uid, fields) for uid, fields in units.items()
                  if set(EXPECTED).issubset(fields.get('uabi', '').split(','))]
    require(len(candidates) == 1, 'Expected exactly one farmer with all seven commands')
    uid, farmer = candidates[0]
    require(farmer['uabi'].split(',') == ['AHbu', 'Prpr', 'A108', 'A109', 'A117',
                                        'Geqb', 'Pcap', 'Pcol', 'Pdep'],
            f'{uid}: farmer ability attachment/order changed')
    require('Amov' not in abilities, 'Native Amov must not be modified or disabled')
    for rawcode, stem in FARMER_ICONS.items():
        fields = abilities[rawcode][1]
        require(field_value(fields, 'aart') == icon_path(stem), f'{rawcode}: farmer icon path mismatch')
        if rawcode != 'Geqb':
            require(field_value(fields, 'arar') == icon_path(stem), f'{rawcode}: farmer research icon path mismatch')
    return uid


def verify_collection_commands(abilities):
    cells, icons, orders = {}, [], []
    for rawcode in COLLECTION_COMMANDS:
        require(rawcode in abilities, f'Missing collection command {rawcode}')
        parent, fields = abilities[rawcode]
        require(parent == 'ANcl', f'{rawcode}: collection command must inherit Channel')
        cell = (field_value(fields, 'abpx'), field_value(fields, 'abpy'))
        require(cell not in cells, f'{rawcode}: collection cell overlaps {cells.get(cell)}')
        cells[cell] = rawcode
        icons.append(field_value(fields, 'aart'))
        orders.append(field_value(fields, 'Ncl6', 1))
    require(len(set(icons)) == 8, 'Collection command icons must be distinct')
    require(len(set(orders)) == 8, 'Display command base orders collide')
    for rawcode, (x, y, hotkey, target, stem, order) in COLLECTION_COMMANDS.items():
        fields = abilities[rawcode][1]
        require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (x, y),
                f'{rawcode}: collection command cell changed')
        require(field_value(fields, 'ahky') == hotkey, f'{rawcode}: collection command hotkey changed')
        require(field_value(fields, 'Ncl2', 1) == target, f'{rawcode}: collection target type changed')
        require(field_value(fields, 'Ncl6', 1) == order, f'{rawcode}: base order changed')
        for field in ('aart', 'arar'):
            require(field_value(fields, field) == icon_path(stem), f'{rawcode}: {field} icon path mismatch')


def verify_species_identity(units):
    for species, (model, stem) in enumerate(SPECIES, 1):
        uid = f'pd0{species}'
        require(uid in units, f'Missing species display {uid}')
        display = units[uid]
        require(display.get('umdl') == model, f'{uid}: species model mismatch')
        for field in ('uico', 'ussi'):
            require(display.get(field) == icon_path(stem), f'{uid}: {field} species icon mismatch')
        require(display.get('uabi', '').split(',') == ['Avul'] + list(COLLECTION_COMMANDS),
                f'{uid}: collection command attachment/order changed')


def verify_slot_icons(abilities):
    for slot in range(4):
        for variant in range(129):
            rawcode = f's{slot}{variant:02X}'
            require(rawcode in abilities, f'Missing passive slot variant {rawcode}')
            parent, fields = abilities[rawcode]
            require(parent == 'AOcr', f'{rawcode}: skill display must be passive')
            require(not any(key == 'Ncl6' for key, _, _ in fields),
                    f'{rawcode}: passive display must not allocate channel orders')
            require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (slot, 1),
                    f'{rawcode}: wrong fixed skill cell')
            require(field_value(fields, 'Ocr1', 1) == 0.0 and field_value(fields, 'Ocr2', 1) == 1.0,
                    f'{rawcode}: passive display must have no critical-strike combat effect')
            for field in ('aher', 'aite', 'achd'):
                require(field_value(fields, field) == 0, f'{rawcode}: passive display flag {field} changed')
            require(field_value(fields, 'areq') == '', f'{rawcode}: passive display must have no requirements')
            state = 'empty slot' if variant == 128 else 'locked skill' if variant >= 64 else 'bright skill'
            require(field_value(fields, 'aart') == skill_icon_path(variant), f'{rawcode}: {state} icon mismatch')
            label, description = field_value(fields, 'atp1', 1), field_value(fields, 'aub1', 1)
            if variant == 128:
                require('共鸣锁定' not in label + description,
                        f'{rawcode}: empty slot must not be resonance locked')
                require('空栏' in label and '没有此栏' in description and '开栏石' in description,
                        f'{rawcode}: empty slot explanation changed')
            elif variant >= 64:
                require('共鸣锁定' in label and '空栏' not in label,
                        f'{rawcode}: locked skill must retain specific identity')
                require('解锁' in description and '已抽技能' in description,
                        f'{rawcode}: missing resonance explanation')
            else:
                require('共鸣锁定' not in label and '空栏' not in label,
                        f'{rawcode}: bright skill mislabeled as empty/locked')
            if variant < 128:
                base_variant = variant % 64
                expected_label = QUALITY_NAMES[base_variant % 4] + ' ' + SKILL_NAMES[base_variant // 4]
                if variant >= 64:
                    expected_label += ' [共鸣锁定]'
                    bright_fields = abilities[f's{slot}{base_variant:02X}'][1]
                    lock_prefix = f'已抽技能，尚未生效。完成本路第{4 if slot == 2 else 8}波解锁。|n'
                    require(description == lock_prefix + field_value(bright_fields, 'aub1', 1),
                            f'{rawcode}: locked skill description mismatch')
                require(label == expected_label and field_value(fields, 'anam') == expected_label,
                        f'{rawcode}: skill/quality identity label changed')
            else:
                require(label == field_value(fields, 'anam') == '空栏', f'{rawcode}: empty slot label changed')


def decode_icon_blp(data, path):
    # All project-generated icons are BLP1 palettized alpha8 with seven mips.
    require(len(data) >= 1180 and data[:4] == b'BLP1', f'{path}: invalid/truncated BLP1')
    compression, alpha, width, height, kind, has_mips = struct.unpack_from('<6I', data, 4)
    require((compression, alpha, kind, has_mips) == (1, 8, 5, 1),
            f'{path}: unsupported BLP1 encoding; expected palette/alpha8/mips')
    require((width, height) == (64, 64), f'{path}: icon must be 64x64')
    offsets = struct.unpack_from('<16I', data, 28)
    sizes = struct.unpack_from('<16I', data, 92)
    previous_end = 1180
    for level in range(16):
        if level >= 7:
            require(offsets[level] == sizes[level] == 0, f'{path}: unexpected extra mip {level}')
            continue
        count = max(1, width >> level) * max(1, height >> level)
        require(sizes[level] == count * 2, f'{path}: mip {level} alpha8 payload size mismatch')
        require(offsets[level] == previous_end and offsets[level] + sizes[level] <= len(data),
                f'{path}: mip {level} out of bounds or overlaps')
        previous_end = offsets[level] + sizes[level]
    require(previous_end == len(data), f'{path}: trailing BLP bytes')
    indices = data[offsets[0]:offsets[0] + 4096]
    alphas = data[offsets[0] + 4096:offsets[0] + 8192]
    rgba = []
    for index, opacity in zip(indices, alphas):
        blue, green, red, _ = data[156 + index * 4:160 + index * 4]
        rgba.append((red, green, blue, opacity))
    require(any(pixel[3] for pixel in rgba), f'{path}: icon is fully transparent')
    require(len(set(rgba)) > 4, f'{path}: icon has no usable artwork')
    return rgba


def verify_imported_icons(artifact, root=ROOT):
    hashes = {False: {}, True: {}}
    for stem in ICON_STEMS:
        pixels = {}
        for disabled in (False, True):
            path = icon_path(stem, disabled)
            require(artifact.has(path), f'Missing packaged pet UI icon: {path}')
            data = artifact.extract(path)
            source = root / 'imports' / Path(path.replace('\\', '/'))
            require(source.is_file(), f'Missing source pet UI icon: {source.relative_to(root)}')
            require(data == source.read_bytes(), f'{path}: packaged icon hash differs from source')
            digest = hashlib.sha256(data).hexdigest()
            require(digest not in hashes[disabled],
                    f'{path}: duplicate semantic icon artwork with {hashes[disabled].get(digest)}')
            hashes[disabled][digest] = path
            pixels[disabled] = decode_icon_blp(data, path)
            print(f'PASS RESOURCE: {path}; BLP1 palette/alpha8, 64x64, 7 mips; SHA256={digest}')
        normal, gray = pixels[False], pixels[True]
        require(all(r == g == b for r, g, b, _ in gray), f'{stem}: disabled icon must be grayscale')
        require(sum(r + g + b for r, g, b, _ in gray) <
                sum(r + g + b for r, g, b, _ in normal) * 0.60,
                f'{stem}: disabled icon must be visibly dimmer than normal')
    require(not set(hashes[False]) & set(hashes[True]), 'Normal and disabled icons must differ')
    return hashes


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
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    units = unit_objects(artifact.extract('war3map.w3u'))
    farmer = verify_farmer_grid(abilities, units)
    verify_collection_commands(abilities)
    verify_species_identity(units)
    verify_slot_icons(abilities)
    verify_pet_core(abilities, units)
    verify_imported_icons(artifact)
    require(not artifact.has(r'Units\CommandFunc.txt'), 'Global CommandFunc override is forbidden')
    print(f'PASS PET UI: {farmer}; exact 12-cell farmer grid; eight distinct collection icons, '
          'unchanged cells/hotkeys/base orders; three explicit species identities; '
          '516 exact bright/locked/empty variants; 26 packaged 64px BTN/DIS assets match source hashes.')
    print('NOT TESTED: native rendering/portrait/selection, actual command placement and live skill effects.')


if __name__ == '__main__':
    main()
