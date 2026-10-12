"""Verify packaged two-command function menu and global Channel contracts.

Usage: python tools/VerifyGroundItemArtifact.py ExampleMap.w3x
Does not prove native rendering or live gameplay.
"""
from pathlib import Path
import json
import re
import sys

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects

BOOK_SPELLS = ('A119', 'Gupg')
REMOVED_CAPTURE_COMMANDS = ('Phnt', 'Pmas', 'Pfor')
REMOVED_PLAYER_COMMANDS = REMOVED_CAPTURE_COMMANDS + ('Dsta',)


def value(fields, key, level=1, column=0):
    require((key, level, column) in fields,
            f'Missing function field {key} level={level} column={column}')
    return fields[(key, level, column)][1]


def verify_no_hunt_objects(abilities, units, items=None):
    """Reject retired capture/hunt objects, parents and references everywhere."""
    for retired in REMOVED_PLAYER_COMMANDS:
        require(retired not in abilities,
                f"Removed {'capture/hunt' if retired in REMOVED_CAPTURE_COMMANDS else 'damage statistics'} ability {retired} remains as a ghost object")
        rawcode = re.compile(r'(?<![A-Za-z0-9_])' + retired + r'(?![A-Za-z0-9_])')
        for object_id, (parent, fields) in abilities.items():
            require(parent != retired, f'{object_id}: removed {retired} remains as ability parent')
            for field, (_, field_data) in fields.items():
                require(not isinstance(field_data, str) or not rawcode.search(field_data),
                        f'{object_id}: removed {retired} remains in ability field {field[0]}')
        for kind, objects in (('unit', units), ('item', items or {})):
            for object_id, fields in objects.items():
                require(object_id != retired, f'Removed {retired} remains as {kind} object')
                for field, field_data in fields.items():
                    require(not isinstance(field_data, str) or not rawcode.search(field_data),
                            f'{object_id}: removed {retired} remains in {kind} field {field}')


def verify_no_removed_raw_objects(data, extended, label):
    """Keep raw object parents, which the convenience unit parser discards."""
    from VerifySemanticIconArtifact import parse_objects
    for object_id, obj in parse_objects(data, extended).items():
        parent = obj.identity[:4].decode('ascii')
        for retired in REMOVED_PLAYER_COMMANDS:
            require(object_id != retired and parent != retired,
                    f'{object_id}: removed {retired} remains as {label} object/parent')
            pattern = re.compile(r'(?<![A-Za-z0-9_])' + retired + r'(?![A-Za-z0-9_])')
            for key, field in obj.fields.items():
                require(field.kind != 3 or not pattern.search(field.value),
                        f'{object_id}: removed {retired} remains in {label} field {key[0]}')


def verify_global_channel_orders(abilities):
    """Check every packaged Channel and every Ncl6 field, not just UI commands.

    One ability may reuse its own order across synchronization levels. Two
    different abilities must never own the same order at any level.
    """
    owners = {}
    channel_count = 0
    for object_id, (parent, fields) in abilities.items():
        orders = [(level, column, kind, order)
                  for (field, level, column), (kind, order) in fields.items()
                  if field == 'Ncl6']
        if parent == 'ANcl':
            channel_count += 1
            levels = fields.get(('alev', 0, 0), (0, 1))[1]
            require(isinstance(levels, int) and levels >= 1,
                    f'{object_id}: invalid Channel level count')
            require(len(orders) == levels and
                    {level for level, _, _, _ in orders} == set(range(1, levels + 1)),
                    f'{object_id}: Channel must define Ncl6 exactly at levels 1..{levels}')
            require(len({order for _, _, _, order in orders}) == 1,
                    f'{object_id}: Channel base order must stay consistent across all levels')
        for level, column, kind, order in orders:
            require(level >= 1 and column == 6 and kind == 3 and
                    isinstance(order, str) and re.fullmatch(r"[a-z][a-z0-9]*", order) is not None,
                    f'{object_id}: invalid Channel order encoding at level {level}')
            previous = owners.get(order)
            require(previous is None or previous == object_id,
                    f'Channel order {order!r} collides: {previous} and {object_id} '
                    f'(level {level})')
            owners[order] = object_id
    return channel_count


def verify_function_book(abilities, units):
    verify_no_hunt_objects(abilities, units)
    for rawcode in ('Geqb',) + BOOK_SPELLS:
        require(rawcode in abilities, f'Missing function book command {rawcode}')
    book_parent, book = abilities['Geqb']
    upgrade_parent, upgrade = abilities['Gupg']
    require(book_parent == 'Aspb', 'Equipment book must inherit Spell Book')
    require(upgrade_parent == 'ANcl', 'Ground upgrade must inherit Channel')
    require(value(book, 'spb1', 1, 1) == ','.join(BOOK_SPELLS), 'Unexpected book spell list')
    require(value(book, 'spb2', 1, 2) == 0, 'Book shares spell cooldowns')
    require(value(book, 'spb3', 1, 3) == 2 and value(book, 'spb4', 1, 4) == 2,
            'Book must contain exactly two spells')
    require(value(book, 'abpx', 0) == 3 and value(book, 'abpy', 0) == 0,
            'Book must occupy farmer function cell 3,0')
    require(value(book, 'ahky', 0) == 'C', 'Book hotkey must be C')
    require(value(upgrade, 'Ncl2', 1, 2) == 2, 'Ground upgrade must target a point')
    require(value(upgrade, 'Ncl3', 1, 3) & 3 == 3,
            'Ground upgrade must be visible and show target image')
    require(value(upgrade, 'aare') == 144.0, 'Ground upgrade AoE mismatch')
    require(value(upgrade, 'ahky', 0) == 'U', 'Ground upgrade hotkey must be U')
    manual = abilities['A119'][1]
    require(value(manual, 'abpx', 0) == 0 and value(manual, 'abpy', 0) == 0,
            'Backpack craft must occupy book cell 0,0')
    require(value(upgrade, 'abpx', 0) == 1 and value(upgrade, 'abpy', 0) == 0,
            'Ground upgrade must occupy book cell 1,0')
    require(value(manual, 'ahky', 0) == 'C', 'Backpack craft hotkey must remain C')
    require(value(book, 'anam', 0) == '功能', 'Book must be named 功能')
    book_cells, book_hotkeys = {}, {}
    for rawcode in BOOK_SPELLS:
        fields = abilities[rawcode][1]
        cell = (value(fields, 'abpx', 0), value(fields, 'abpy', 0))
        hotkey = fields.get(('ahky', 0, 0), (3, ''))[1]
        require(cell not in book_cells,
                f'Function book command cells overlap: {book_cells.get(cell)} and {rawcode}')
        require(not hotkey or hotkey not in book_hotkeys,
                f'Function book command hotkeys overlap: {book_hotkeys.get(hotkey)} and {rawcode}')
        book_cells[cell] = rawcode
        if hotkey:
            book_hotkeys[hotkey] = rawcode
    channel_count = verify_global_channel_orders(abilities)
    farmer = [(rawcode, fields) for rawcode, fields in units.items()
              if 'Geqb' in fields.get('uabi', '').split(',')]
    require(len(farmer) == 1, 'Expected exactly one equipment-book farmer')
    require('A119' not in farmer[0][1]['uabi'].split(','),
            'Backpack craft still occupies farmer top-level cell')
    return farmer[0][0], channel_count


def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    units = unit_objects(artifact.extract('war3map.w3u'))
    verify_no_removed_raw_objects(artifact.extract('war3map.w3u'), False, 'unit')
    if artifact.has('war3map.w3t'):
        verify_no_removed_raw_objects(artifact.extract('war3map.w3t'), False, 'item')
        verify_no_hunt_objects(abilities, units, unit_objects(artifact.extract('war3map.w3t')))
    farmer, channel_count = verify_function_book(abilities, units)
    print('PASS ground commands:', farmer, 'book=' + ','.join(BOOK_SPELLS),
          'two distinct cells; no repeated assigned hotkeys', 'point AoE=144',
          f'{channel_count} globally unique Channel objects; no Phnt/Pmas/Pfor/Dsta ghost/attachment')
    for rawcode in ('Geqb',) + BOOK_SPELLS:
        parent, fields = abilities[rawcode]
        print(json.dumps({'id': rawcode, 'parent': parent, 'fields': [
            {'key': list(key), 'type': kind, 'value': val}
            for key, (kind, val) in fields.items()]}, ensure_ascii=False))
    print('NOT TESTED: native book rendering, range circle UI and gameplay.')


if __name__ == '__main__':
    main()
