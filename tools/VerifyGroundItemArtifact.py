"""Verify packaged single-command function book and global Channel contracts.

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

BOOK_SPELLS = ('A119',)
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


def verify_list_channel_families(abilities):
    """The only shared-order exception: complete reviewed exclusive states per cell, including sparse quality-only IDs."""
    actual = {raw for raw in abilities if re.fullmatch(r'L[0-9A-F]{3}', raw)}
    if not actual:
        return {}
    quality_only = len(actual) == 610
    variants = 241 if any(int(raw[1:], 16) >= 490 for raw in actual) else 49
    offsets = (0, *range(1, 241, 4)) if quality_only else range(variants)
    expected = {f'L{cell * variants + variant:03X}' for cell in range(10) for variant in offsets}
    require(actual == expected, 'List shared-order whitelist must contain exactly its reviewed complete family')
    groups, cell_orders = {}, {}
    for cell in range(10):
        order = None
        for variant in offsets:
            raw = f'L{cell * variants + variant:03X}'
            parent, fields = abilities[raw]
            require(parent == 'ANcl' and value(fields, 'alev', 0) == 2,
                    f'{raw}: shared list family must be two-level Channel')
            require((value(fields, 'abpx', 0), value(fields, 'abpy', 0)) == (cell % 4, cell // 4),
                    f'{raw}: shared list family cell changed')
            require(value(fields, 'ahky', 0) == 'QWETASDFZX'[cell], f'{raw}: shared list family hotkey changed')
            for level in (1, 2):
                require(value(fields, 'Ncl2', level, 2) == 0, f'{raw}: shared list family must be no-target')
                current = value(fields, 'Ncl6', level, 6)
                if order is None:
                    order = current
                require(current == order, f'{raw}: shared list family order differs')
            groups[raw] = ('list-cell', cell)
        require(order not in cell_orders, 'Shared list orders collide across cells')
        cell_orders[order] = cell
    return groups


def unique_channel_order_count(abilities):
    return len({order for _, fields in abilities.values() for (key, _, _), (_, order) in fields.items() if key == 'Ncl6'})


def verify_directed_channel_families(abilities):
    """Exactly 28 green identities, fixed positions, one exclusive order per cell."""
    actual = {raw for raw in abilities if re.fullmatch(r'Pn[0-9A-F]{2}', raw)}
    if not actual:
        return {}
    green = [*range(4), *range(5, 9), 11, 12, *range(16, 19), 20, 24, 28, 32, 36, *range(39, 49)]
    require(actual == {f'Pn{skill:02X}' for skill in green}, 'Directed shared-order whitelist must be its exact 28-identity family')
    groups, cell_orders = {}, {}
    for skill in green:
        raw = f'Pn{skill:02X}'
        parent, fields = abilities[raw]
        cell = skill if skill < 4 else skill-5 if 5 <= skill <= 8 else skill-12 if 16 <= skill <= 18 else (skill-32)%8 if skill >= 39 else skill-10 if skill in (11, 12) else 0
        require(parent == 'ANcl' and value(fields, 'alev', 0) == 1, raw + ': directed family must be one-level Channel')
        require(all(level in (0, 1) for _, level, _ in fields), raw + ': directed family has residual level fields')
        require((value(fields, 'abpx', 0), value(fields, 'abpy', 0)) == (cell % 4, cell // 4) and value(fields, 'ahky', 0) == 'QWETASDFZX'[cell], raw + ': directed fixed cell/hotkey changed')
        require(value(fields, 'Ncl2', 1, 2) == 0 and value(fields, 'Ncl3', 1, 3) == 1 and value(fields, 'Ncl4', 1, 4) == 0 and value(fields, 'Ncl5', 1, 5) == 0 and value(fields, 'Ncl1', 1, 1) == 0.0, raw + ': directed command role changed')
        require(value(fields, 'amcs') == 0 and value(fields, 'acdn') == 0.0 and value(fields, 'aher', 0) == 0 and value(fields, 'aite', 0) == 0, raw + ': directed commands must be zero-CD noncombat operations')
        order = value(fields, 'Ncl6', 1, 6)
        require(cell not in cell_orders or cell_orders[cell] == order, raw + ': same-cell directed order differs')
        cell_orders[cell] = order
        groups[raw] = ('directed-cell', cell)
    require(len(cell_orders) == len(set(cell_orders.values())) == 8, 'Directed orders collide across physical cells')
    return groups


def verify_global_channel_orders(abilities):
    """Check every packaged Channel and every Ncl6 field, not just UI commands.

    One ability may reuse its own order across synchronization levels. Two
    different abilities cannot share an order, except the exact validated list
    and fixed green-choice families, exclusive within their physical cell.
    """
    owners = {}
    families = verify_list_channel_families(abilities)
    families.update(verify_directed_channel_families(abilities))
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
            owner = families.get(object_id, ('object', object_id))
            previous = owners.get(order)
            require(previous is None or previous == owner,
                    f'Channel order {order!r} collides: {previous} and {object_id} '
                    f'(level {level})')
            owners[order] = owner
    return channel_count


def verify_function_book(abilities, units):
    verify_no_hunt_objects(abilities, units)
    for rawcode in ('Geqb', 'A119', 'Gupg'):
        require(rawcode in abilities, f'Missing function book command {rawcode}')
    book_parent, book = abilities['Geqb']
    upgrade_parent, upgrade = abilities['Gupg']
    require(book_parent == 'Aspb', 'Equipment book must inherit Spell Book')
    require(upgrade_parent == 'ANcl', 'Ground upgrade must inherit Channel')
    require(value(book, 'spb1', 1, 1) == ','.join(BOOK_SPELLS), 'Book must contain only A119')
    require(value(book, 'spb2', 1, 2) == 0, 'Book shares spell cooldowns')
    require(value(book, 'spb3', 1, 3) == 1 and value(book, 'spb4', 1, 4) == 1,
            'Book must contain exactly one spell')
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
    require(value(upgrade, 'abpx', 0) == 1 and value(upgrade, 'abpy', 0) == 1,
            'Ground upgrade must occupy main bar 1,1')
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
          'one A119 spell; Geqb 3,0/C; Gupg main 1,1/U', 'point AoE=144',
          f'{channel_count} globally unique Channel objects; no Phnt/Pmas/Pfor/Dsta ghost/attachment')
    for rawcode in ('Geqb', 'A119', 'Gupg'):
        parent, fields = abilities[rawcode]
        print(json.dumps({'id': rawcode, 'parent': parent, 'fields': [
            {'key': list(key), 'type': kind, 'value': val}
            for key, (kind, val) in fields.items()]}, ensure_ascii=False))
    print('NOT TESTED: native book rendering, range circle UI and gameplay.')


if __name__ == '__main__':
    main()
