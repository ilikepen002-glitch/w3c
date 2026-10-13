#!/usr/bin/env python3
"""Validate phase-A source or packed 40-item objects, never claim gameplay.

python3 tools/VerifyEquipmentPhaseA.py --source-only
python3 tools/VerifyEquipmentPhaseA.py --map ExampleMap.w3x
"""
import argparse
from collections import Counter
from pathlib import Path
import re

from ReadEquipmentCatalog import ROOT, catalog, icon_paths


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_runtime_entrypoints(root=ROOT):
    """Check the live craft entry owner and its one-way sorter dependency."""
    inventory = (root / 'wurst/items/TDInventoryRuntime.wurst').read_text()
    ground = (root / 'wurst/items/TDGroundItemRuntime.wurst').read_text()
    crafting = (root / 'wurst/items/TDCraftingRuntime.wurst').read_text()
    require('tdStartInventoryCraft(farmer)' in inventory, 'Inventory entry not connected')
    require('tdStartGroundCraft(farmer,' in crafting, 'Ground craft entry not connected in crafting runtime')
    require(re.search(r'^import TDGroundItemRuntime$', crafting, re.M),
            'Crafting runtime must import the ground sorter')
    require(not re.search(r'^import (?:public )?TDCraftingRuntime$', ground, re.M),
            'Ground sorter must not import crafting runtime')
    require('tdSetupCraftingRuntime()' not in ground,
            'Ground setup must not initialize crafting runtime')
    require('tdSortGroundEquipmentAfterUpgrade' not in crafting,
            'Ground craft must not sort unrelated equipment')
    backend = (root / 'wurst/items/TDCraftingNativeBackend.wurst').read_text()
    prepare = backend.split('override function prepareResult', 1)[1].split('override function consumeThree', 1)[0]
    require('let quality = tdItemQuality(rawcode)' in prepare and
            'tdTryPlaceItemInPile(output, lane, quality, pileCounts[quality])' in prepare,
            'Ground craft must prepare output in its result-quality lane pile')
    consume = backend.split('override function consumeThree', 1)[1].split('override function publishResult', 1)[0]
    require('if not inventory and not tdItemActualInPile(output, lane, tdItemQuality(outputId))' in consume,
            'Ground craft must revalidate the final output pile before consumption')
    registration = re.compile(r'\bregisterSpellEffectEvent\s*\(\s*TD_FARMER_GROUND_UPGRADE_ABILITY_ID\s*,')
    handler = re.compile(r'^(?:public )?function tdGroundHandleUpgrade\(', re.M)
    registrations = []
    handlers = []
    for file in (root / 'wurst').rglob('*.wurst'):
        if '_tests' in file.relative_to(root / 'wurst').parts:
            continue
        code = '\n'.join(row.split('//', 1)[0] for row in file.read_text().splitlines())
        registrations.extend([file] * len(registration.findall(code)))
        handlers.extend([file] * len(handler.findall(code)))
    expected_owner = root / 'wurst/items/TDCraftingRuntime.wurst'
    require(registrations == [expected_owner],
            'Ground upgrade spell must be registered exactly once in crafting runtime')
    require(handlers == [expected_owner],
            'Ground upgrade handler must have exactly one crafting-runtime owner')
    require('registerSpellEffectEvent(TD_FARMER_GROUND_UPGRADE_ABILITY_ID, function tdGroundHandleUpgrade)' in crafting,
            'Ground upgrade registration must connect the live crafting handler')


def verify_source(root=ROOT):
    entries = catalog(root)
    by_id = {entry.rawcode: entry for entry in entries}
    require(len(by_id) == 40, 'Duplicate equipment rawcode')
    require(Counter(entry.quality for entry in entries) == {1: 10, 2: 10, 3: 10, 4: 10},
            'Each quality must have exactly ten items')
    require(Counter(entry.line for entry in entries) == dict.fromkeys(range(1, 11), 4),
            'Each equipment line must have four items')
    for entry in entries:
        if entry.quality == 4:
            require(entry.next_id is None, entry.rawcode + ': purple has a next link')
        else:
            require(entry.next_id in by_id, entry.rawcode + ': missing explicit next link')
            next_entry = by_id[entry.next_id]
            require((next_entry.quality, next_entry.line) == (entry.quality + 1, entry.line),
                    entry.rawcode + ': next link must preserve line and advance one quality')
        if entry.aura != 'NONE':
            require(entry.aura_radius == (350, 400, 450, 550)[entry.quality - 1],
                    entry.rawcode + ': wrong aura radius')
        if entry.quality == 4:
            require(entry.primary not in ('KILL_GOLD', 'DROP_BONUS') and
                    entry.secondary not in ('KILL_GOLD', 'DROP_BONUS'),
                    entry.rawcode + ': retired economic purple returned')
    paths = icon_paths(root)
    for path in paths.values():
        if path.startswith('war3mapImported\\'):
            require((root / 'imports' / Path(path.replace('\\', '/'))).is_file(),
                    'Missing equipment asset: ' + path)
        else:
            require(path == 'ReplaceableTextures\\CommandButtons\\BTNGlove.blp',
                    'Unexpected native equipment asset: ' + path)
    ground = (root / 'wurst/items/TDGroundItemRuntime.wurst').read_text()
    crafting = (root / 'wurst/items/TDCraftingRuntime.wurst').read_text()
    backend = (root / 'wurst/items/TDCraftingNativeBackend.wurst').read_text()
    verify_runtime_entrypoints(root)
    require('GetWorldBounds' not in ground + crafting, 'Craft/sort whole-map enumeration returned')
    require('point.x - radius' in crafting and 'tdGroundPointInUpgradeCircle' in crafting,
            'Ground snapshot must be bounded and precisely filtered')
    require('tdItemFixedNextId(rawcode)' in crafting and 'tdRuntimeCraftCatalog.seal()' in crafting,
            'Live crafting must consume the same sealed forty-item catalog')
    logic = (root / 'wurst/items/TDCraftingLogic.wurst').read_text()
    require('TD_CRAFT_MODE_TWO' not in logic and '65' not in logic,
            'Retired two-item gambling logic remains')
    require('SetItemVisible(output, false)' in backend and 'tdTryPlaceItemNear(output' in backend,
            'Result must be hidden and native-position validated before consumption')
    require('tdCraftWatchedPickups.loadInt(record.handleKey) != 0' in backend,
            'Intervening pickup/drop must invalidate the captured ingredient')
    for file in (root / 'wurst/items').glob('*.wurst'):
        for number, row in enumerate(file.read_text().splitlines(), 1):
            code = row.split('//', 1)[0]
            require(not (re.search(r'\band\b', code) and re.search(r'\bor\b', code)),
                    f'{file.name}:{number}: unsafe mixed and/or expression')
    return entries, paths


def verify_map(path, root=ROOT):
    from GenerateTowerTerrainMask import Mpq
    from VerifyTowerPlacementArtifact import unit_objects
    from VerifyEquipmentAbilityArtifact import ability_objects, verify_current_equipment_abilities
    entries, paths = verify_source(root)
    archive = Mpq(path.read_bytes())
    items = unit_objects(archive.extract('war3map.w3t'))
    expected = {entry.rawcode for entry in entries}
    actual = {rawcode for rawcode in items if re.fullmatch(r'i[WGBP]\d\d', rawcode)}
    require(actual == expected, 'Packed equipment identity set is stale or incomplete')
    for entry in entries:
        fields = items[entry.rawcode]
        name = re.sub(r'\|c[0-9a-fA-F]{8}|\|r', '', fields['unam'])
        require(name == entry.name, entry.rawcode + ': packed name differs from config')
        require(fields['ilev'] == (1, 3, 5, 7)[entry.quality - 1], entry.rawcode + ': item level')
        require(fields['iico'] == paths[entry.line, entry.quality], entry.rawcode + ': icon path')
        require(fields['iabi'] == '', entry.rawcode + ': native item passive double application')
        text = fields['utub']
        require(fields.get('ides') == text, entry.rawcode + ': selected item description missing')
        for phrase in ('同塔同名限1件', '紫装不能合成' if entry.quality == 4 else '三件同品质可由工人合成'):
            require(phrase in text, entry.rawcode + ': stale tooltip ' + phrase)
    abilities = ability_objects(archive.extract('war3map.w3a'))
    verify_current_equipment_abilities(abilities)
    jass = archive.extract('war3map.j').decode('utf-8-sig')
    for function in ('tdStartInventoryCraft', 'tdStartGroundCraft'):
        require(re.search(r'call\s+\w*' + function + r'\(', jass), 'Missing packed live call: ' + function)
    require('tdGroundConsumeBatch' not in jass, 'Retired ground random-only consumer returned')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only', action='store_true')
    parser.add_argument('--map', type=Path)
    args = parser.parse_args()
    require(args.source_only != bool(args.map), 'Choose exactly one source-only or map mode')
    if args.source_only:
        verify_source()
        print('PASS STATIC A: 40 unique items, ten per quality, thirty fixed links; same catalog live wiring; bounded snapshot/placement guards; known assets')
    else:
        verify_map(args.map)
        print('PASS PACKED A: forty config-matched item objects, empty native item passives, exact icons, new live calls; legacy consumers/passives absent')
    print('NOT TESTED: native item projection, real Buff/percent semantics, gameplay, multiplayer, performance; B/C mechanisms remain separate review scope')


if __name__ == '__main__':
    main()
