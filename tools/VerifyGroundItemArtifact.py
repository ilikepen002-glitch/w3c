"""Verify packaged ground-upgrade commands; does not prove native rendering."""
from pathlib import Path
import json
import sys
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects

artifact = Mpq(Path(sys.argv[1]).read_bytes())
abilities = ability_objects(artifact.extract('war3map.w3a'))
units = unit_objects(artifact.extract('war3map.w3u'))
book_parent, book = abilities['Geqb']
upgrade_parent, upgrade = abilities['Gupg']
require(book_parent == 'Aspb', 'Equipment book must inherit Spell Book')
require(upgrade_parent == 'ANcl', 'Ground upgrade must inherit Channel')
def value(fields, key, level=1, column=0):
    return fields[(key, level, column)][1]
book_spells = ['A119', 'Gupg', 'Dsta', 'Pmas', 'Phnt', 'Pfor']
require(value(book, 'spb1', 1, 1) == ','.join(book_spells), 'Unexpected book spell list')
require(value(book, 'spb2', 1, 2) == 0, 'Book shares spell cooldowns')
require(value(book, 'spb3', 1, 3) == 6 and value(book, 'spb4', 1, 4) == 6, 'Book must contain exactly six spells')
require(value(book, 'abpx', 0) == 3 and value(book, 'abpy', 0) == 0, 'Book must occupy farmer function cell 3,0')
require(value(book, 'ahky', 0) == 'C', 'Book hotkey must be C')
require(value(upgrade, 'Ncl2', 1, 2) == 2, 'Ground upgrade must target a point')
require(value(upgrade, 'Ncl3', 1, 3) & 3 == 3, 'Ground upgrade must be visible and show target image')
require(value(upgrade, 'aare') == 144.0, 'Ground upgrade AoE mismatch')
require(value(upgrade, 'ahky', 0) == 'U', 'Ground upgrade hotkey must be U')
manual = abilities['A119'][1]
require(value(manual, 'abpx', 0) == 0 and value(manual, 'abpy', 0) == 0, 'Backpack craft must occupy book cell 0,0')
require(value(upgrade, 'abpx', 0) == 1 and value(upgrade, 'abpy', 0) == 0, 'Ground upgrade must occupy book cell 1,0')
require(value(manual, 'ahky', 0) == 'C', 'Backpack craft hotkey must remain C')
statistics_parent, statistics = abilities['Dsta']
require(statistics_parent == 'ANcl', 'Damage statistics must inherit Channel')
require(value(statistics, 'Ncl2', 1, 2) == 0, 'Damage statistics must be untargeted')
require(value(statistics, 'Ncl3', 1, 3) & 1 == 1, 'Damage statistics button must be visible')
require(value(statistics, 'abpx', 0) == 2 and value(statistics, 'abpy', 0) == 0, 'Damage statistics must occupy book cell 2,0')
require(value(book, 'anam', 0) == '功能', 'Book must be named 功能')
book_cells, book_hotkeys = {}, {}
for rawcode in book_spells:
    require(rawcode in abilities, f'Missing function book command {rawcode}')
    fields = abilities[rawcode][1]
    cell = (value(fields, 'abpx', 0), value(fields, 'abpy', 0))
    # Dsta intentionally has no hotkey override; check only assigned hotkeys.
    hotkey = fields.get(('ahky', 0, 0), (3, ''))[1]
    require(cell not in book_cells,
            f'Function book command cells overlap: {book_cells.get(cell)} and {rawcode}')
    require(not hotkey or hotkey not in book_hotkeys,
            f'Function book command hotkeys overlap: {book_hotkeys.get(hotkey)} and {rawcode}')
    book_cells[cell] = rawcode
    if hotkey:
        book_hotkeys[hotkey] = rawcode
for rawcode, x, hotkey, target in [('Pmas', 0, 'M', 1), ('Phnt', 1, 'H', 1), ('Pfor', 2, 'B', 0)]:
    parent, fields = abilities[rawcode]
    require(parent == 'ANcl', f'{rawcode}: function command must inherit Channel')
    require(value(fields, 'abpx', 0) == x and value(fields, 'abpy', 0) == 1,
            f'{rawcode}: wrong function book cell')
    require(value(fields, 'ahky', 0) == hotkey, f'{rawcode}: wrong function book hotkey')
    require(value(fields, 'Ncl2', 1, 2) == target, f'{rawcode}: wrong function command target')
statistics_order = value(statistics, 'Ncl6', 1, 6)
for statistics_other_id, (_, statistics_other_fields) in abilities.items():
    if statistics_other_id != 'Dsta' and ('Ncl6', 1, 6) in statistics_other_fields:
        require(value(statistics_other_fields, 'Ncl6', 1, 6) != statistics_order, f'Statistics order collides with {statistics_other_id}')
order = value(upgrade, 'Ncl6', 1, 6)
for rawcode, (_, fields) in abilities.items():
    if rawcode != 'Gupg' and ('Ncl6', 1, 6) in fields:
        require(value(fields, 'Ncl6', 1, 6) != order, f'Ground order collides with {rawcode}')
farmer = [(rawcode, fields) for rawcode, fields in units.items() if 'Geqb' in fields.get('uabi', '').split(',')]
require(len(farmer) == 1, 'Expected exactly one equipment-book farmer')
require('A119' not in farmer[0][1]['uabi'].split(','), 'Backpack craft still occupies farmer top-level cell')
print('PASS ground commands:', farmer[0][0], 'book=' + ','.join(book_spells), 'six distinct cells; no repeated assigned hotkeys', 'point AoE=144', 'unique order=' + order)
for rawcode in ['Geqb'] + book_spells:
    parent, fields = abilities[rawcode]
    print(json.dumps({'id': rawcode, 'parent': parent, 'fields': [{'key': list(key), 'type': kind, 'value': val} for key, (kind, val) in fields.items()]}, ensure_ascii=False))
print('NOT TESTED: native book rendering, range circle UI and gameplay.')

