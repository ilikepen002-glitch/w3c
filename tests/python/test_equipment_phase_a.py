"""Independent approved-table and source-boundary checks; no engine claims."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from ReadEquipmentCatalog import catalog, icon_paths
from VerifyEquipmentPhaseA import verify_source


CHAINS = [
    ('02/02/01/01', '远望镜/精制远望镜/鹰眼望远镜/风行旗'),
    ('01/01/02/02', '战斧/精钢战斧/狂战战斧/剑圣印记'),
    ('03/05/07/04', '迅击手套/迅击护手/疾袭护腕/饥饿心核'),
    ('09/04/04/03', '盾符/镇守盾符/坚壁盾符/镇军盾徽'),
    ('08/09/08/05', '毒囊/淬毒藤囊/腐毒囊/森蚀之种'),
    ('06/03/03/06', '破甲尖刺/裂甲骨刺/碎甲战印/裂甲战鼓'),
    ('04/07/06/07', '行军旗/督军旗/统领旗/统御号角'),
    ('05/06/05/08', '猎金指环/佣兵钱袋/赏金契约/灵感法典'),
    ('07/08/09/09', '疾风鼓/疾风军鼓/劲风战鼓/疾风战鼓'),
    ('10/10/10/10', '寒霜碎晶/寒霜晶石/寒霜晶核/永霜核心'),
]
STATS = [
    [('RANGE', 90, 'NONE', 0), ('RANGE', 150, 'ATTACK', 8), ('RANGE', 230, 'ATTACK', 16), ('RANGE', 340, 'ATTACK_SPEED', .24)],
    [('ATTACK', 8, 'NONE', 0), ('ATTACK', 16, 'EXECUTE', .12), ('ATTACK', 28, 'EXECUTE', .20), ('ATTACK', 34, 'BOSS_DAMAGE', .25)],
    [('ATTACK_SPEED', .12, 'NONE', 0), ('ATTACK_SPEED', .20, 'ATTACK', 8), ('ATTACK_SPEED', .32, 'ATTACK', 16), ('ATTACK_SPEED', .48, 'ATTACK', 20)],
    [('CONTROL_POWER', .10, 'ATTACK', 4), ('CONTROL_POWER', .18, 'ATTACK', 8), ('CONTROL_POWER', .28, 'ATTACK', 16), ('CONTROL_POWER', .40, 'ATTACK', 24)],
    [('POISON', 6, 'NONE', 0), ('POISON', 12, 'ATTACK_SPEED', .08), ('POISON', 20, 'ATTACK_SPEED', .16), ('POISON', 24, 'ATTACK_SPEED', .24)],
    [('ARMOR_SHRED', 1, 'NONE', 0), ('ARMOR_SHRED', 2, 'ATTACK', 8), ('ARMOR_SHRED', 3, 'ATTACK', 16), ('NONE', 0, 'NONE', 0)],
    [('NONE', 0, 'NONE', 0)] * 4,
    [('KILL_GOLD', 1, 'NONE', 0), ('KILL_GOLD', 2, 'DROP_BONUS', 1), ('KILL_GOLD', 3, 'DROP_BONUS', 2), ('NONE', 0, 'NONE', 0)],
    [('NONE', 0, 'NONE', 0)] * 4,
    [('NONE', 0, 'NONE', 0)] * 4,
]


class EquipmentPhaseATests(unittest.TestCase):
    def test_all_forty_names_rawcodes_and_recipe_links_match_approved_table(self):
        entries = {(entry.line, entry.quality): entry for entry in catalog()}
        for line, (numbers, names) in enumerate(CHAINS, 1):
            ids = ['i' + quality + number for quality, number in zip('WGBP', numbers.split('/'))]
            for quality, name in enumerate(names.split('/'), 1):
                entry = entries[line, quality]
                self.assertEqual((entry.rawcode, entry.name), (ids[quality - 1], name))
                self.assertEqual(entry.next_id, ids[quality] if quality < 4 else None)

    def test_all_primary_secondary_stats_and_unlisted_values_are_exact(self):
        for entry in catalog():
            self.assertEqual((entry.primary, entry.primary_value, entry.secondary, entry.secondary_value),
                             STATS[entry.line - 1][entry.quality - 1])

    def test_aura_magnitudes_radii_and_specializations_are_exact(self):
        expected = {
            6: ('ARMOR_ON_HIT', [0, 0, 0, 4]),
            7: ('ATTACK', [.03, .05, .08, .12]),
            8: ('COOLDOWN', [0, 0, 0, .18]),
            9: ('ATTACK_SPEED', [.04, .07, .10, .16]),
            10: ('ENEMY_SLOW', [.06, .10, .14, .20]),
        }
        specializations = {1: 'ARCHER_ARROW', 2: 'WAR_INTENT', 3: 'CORPSE_BURST',
                           4: 'SHIELD_SPREAD', 5: 'POISON_BURST'}
        for entry in catalog():
            kind, values = expected.get(entry.line, ('NONE', [0] * 4))
            value = values[entry.quality - 1]
            self.assertEqual((entry.aura, entry.aura_value, entry.aura_radius),
                             (kind if value else 'NONE', value,
                              (350, 400, 450, 550)[entry.quality - 1] if value else 0))
            self.assertEqual(entry.specialization,
                             specializations.get(entry.line, 'NONE') if entry.quality == 4 else 'NONE')

    def test_current_source_boundary_and_existing_asset_resolution(self):
        self.assertEqual(len(verify_source()[0]), 40)
        self.assertEqual(len(icon_paths()), 40)

    def test_stale_two_item_rules_and_legacy_name_aliases_are_absent(self):
        source = '\n'.join(p.read_text() for p in (ROOT / 'wurst/items').glob('*.wurst'))
        for phrase in ('TD_CRAFT_MODE_TWO', '65%', 'tdGroundConsumeBatch', 'TD_ITEM_COMMAND_SEAL_ID',
                       'TD_ITEM_CORRUPTED_HEART_ID', 'tdTowerEquipmentDuplicateFactor'):
            self.assertNotIn(phrase, source)

    def test_native_order_is_prepare_validate_then_consume_and_publish(self):
        transaction = (ROOT / 'wurst/items/TDCraftingTransaction.wurst').read_text()
        self.assertLess(transaction.index('backend.prepareResult(resultId)'),
                        transaction.index('backend.consumeThree('))
        self.assertLess(transaction.index('backend.consumeThree('),
                        transaction.index('backend.publishResult(resultKey)'))
        backend = (ROOT / 'wurst/items/TDCraftingNativeBackend.wurst').read_text()
        consume = backend.split('override function consumeThree', 1)[1].split('override function publishResult', 1)[0]
        self.assertNotIn('UnitRemoveItem', consume.split('// No yields')[0])
        self.assertLess(consume.index('available(first'), consume.index('RemoveItem(one.itemHandle)'))

    def test_actual_projection_checks_and_no_target_means_no_move(self):
        placement = (ROOT / 'wurst/items/TDItemPlacement.wurst').read_text()
        self.assertIn('tdItemActualInPile(itm, lane, quality)', placement)
        self.assertIn('return attempted ? -1 : -2', placement)
        sorter = (ROOT / 'wurst/items/TDGroundItemRuntime.wurst').read_text()
        self.assertIn('else if index == -2', sorter)
        self.assertIn('tdRestoreSortedItem(itm, lane, origin)', sorter)
        inventory = (ROOT / 'wurst/items/TDInventoryRuntime.wurst').read_text()
        self.assertIn('tdTryPlaceItemInPile(incoming, lane, quality, 0)', inventory)
        self.assertIn('拥堵', inventory)

    def test_runtime_planning_is_budgeted_and_does_not_sync_freeze(self):
        runtime = (ROOT / 'wurst/items/TDCraftingRuntime.wurst').read_text()
        self.assertNotIn('.freeze()', runtime)
        self.assertIn('.planningStep(24)', runtime)
        self.assertIn('for _operation = 1 to 8', runtime)

    def test_inventory_delivery_uses_physical_origin_not_owner_lane(self):
        runtime = (ROOT / 'wurst/items/TDCraftingRuntime.wurst').read_text()
        inventory = runtime.split('public function tdStartInventoryCraft', 1)[1].split(
            'public function tdStartGroundCraft', 1)[0]
        self.assertIn('tdGroundItemLane(origin.x, origin.y), origin, true', inventory)
        ground = runtime.split('public function tdStartGroundCraft', 1)[1]
        self.assertIn('tdGroundItemLane(point.x, point.y) != lane', ground)


if __name__ == '__main__':
    unittest.main()
