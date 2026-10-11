"""Real packaged ground-upgrade positives and deliberately bad JASS mutations."""
from copy import deepcopy
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerUpgradeArtifact import function_body
import VerifyGroundUpgradeArtifact as verifier


def replace_body(script, name, body):
    match = re.search(r'^function ' + re.escape(name) + r' takes[^\n]*\n(.*?)^endfunction', script, re.M | re.S)
    return script[:match.start(1)] + body + script[match.end(1):]


class GroundUpgradeArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        cls.script = artifact.extract('war3map.j').decode('utf-8')
        cls.abilities = ability_objects(artifact.extract('war3map.w3a'))

    def test_actual_guaranteed_triples_and_backpack_probability(self):
        verifier.verify_rule_matrix(self.script)

    def test_actual_256_availability_states_and_capture_guards(self):
        verifier.verify_capture_guards(self.script)

    def test_actual_independent_600_coordinates_and_144_145_boundaries(self):
        verifier.verify_geometry(self.script)

    def test_actual_123_batches_no_cascade_leftovers_and_real_coordinates(self):
        self.assertEqual(verifier.verify_upgrade_batches(self.script), 123)

    def test_actual_stale_ingredients_new_drop_busy_cast_lanes_and_game_over(self):
        verifier.verify_lifecycle_guards(self.script)

    def test_actual_sort_retains_four_lanes_five_groups_and_handles(self):
        verifier.verify_sort_preserved(self.script)

    def test_actual_full_contract_and_object_tooltip(self):
        self.assertEqual(verifier.verify_ground_upgrade(self.script), 123)
        verifier.verify_tooltip(self.abilities)

    def test_old_pair_rule_is_rejected(self):
        body = function_body(self.script, 'tdGroundCraftBatchSize')
        changed = body.replace('\treturn 0\n', '\tif count == 2 then\n\t\treturn 2\n\tendif\n\treturn 0\n')
        self.assertNotEqual(changed, body)
        with self.assertRaisesRegex(ValueError, 'pair/invalid quality'):
            verifier.verify_rule_matrix(replace_body(self.script, 'tdGroundCraftBatchSize', changed))

    def test_old_pair_consumption_path_is_rejected(self):
        body = function_body(self.script, 'tdGroundProcessOne')
        changed = body.replace('\t\tset TDGroundItemRuntime_tdGroundFirst = null',
                               '\t\tcall tdGroundConsumeBatch(null, "bad pair mutation")\n\t\tset TDGroundItemRuntime_tdGroundFirst = null', 1)
        self.assertNotEqual(changed, body)
        with self.assertRaisesRegex(ValueError, 'pair-consumption path'):
            verifier.verify_ground_upgrade(replace_body(self.script, 'tdGroundProcessOne', changed))

    def test_product_reenqueue_is_rejected_even_on_an_overlapping_target(self):
        body = function_body(self.script, 'tdGroundConsumeBatch')
        line = next(line for line in body.splitlines() if line.strip().startswith('call CreateItem('))
        changed_line = line.replace('call CreateItem(', 'call dispatch_LinkedList_LinkedList_add_1(TDGroundItemRuntime_tdGroundQueues[nextQuality], "bad cascade mutation", itemToIndex(CreateItem(') + '))'
        changed = body.replace(line, changed_line)
        with self.assertRaisesRegex(ValueError, 'reentered|triple/leftover|no-cascade'):
            verifier.verify_upgrade_batches(replace_body(self.script, 'tdGroundConsumeBatch', changed))

    def test_old_capture_mixed_boolean_precedence_is_rejected(self):
        old = '''	local item itm = GetEnumItem()
	local integer pileGroup = tdGroundItemGroup(GetItemTypeId(itm))
	if pileGroup > 0 and ( not TDGroundItemRuntime_tdGroundCrafting) or pileGroup < TDItemData_TD_ITEM_QUALITY_PURPLE and tdGroundItemAvailable(itm, pileGroup) then
		call dispatch_LinkedList_LinkedList_add_1(TDGroundItemRuntime_tdGroundQueues[pileGroup], "bad grouping mutation", itemToIndex(itm))
	endif
'''
        with self.assertRaisesRegex(ValueError, 'ambiguous mixed JASS boolean precedence'):
            verifier.verify_ground_upgrade(replace_body(self.script, 'tdGroundCaptureItem', old))

    def test_missing_lane_and_circle_filters_are_rejected(self):
        body = function_body(self.script, 'tdGroundItemAvailable')
        changes = [re.sub(r'if tdGroundItemLane\([^\n]+ then', 'if false then', body),
                   re.sub(r'return tdGroundPointInUpgradeCircle\([^\n]+', 'return true', body)]
        for changed in changes:
            with self.subTest(body=changed):
                self.assertNotEqual(changed, body)
                with self.assertRaisesRegex(ValueError, 'availability guard mismatch'):
                    verifier.verify_capture_guards(replace_body(self.script, 'tdGroundItemAvailable', changed))

    def test_missing_owned_and_hidden_filters_are_rejected(self):
        body = function_body(self.script, 'tdGroundItemAvailable')
        for old in ('IsItemOwned(itm)', '( not IsItemVisible(itm))'):
            with self.subTest(guard=old):
                self.assertIn(old, body)
                with self.assertRaisesRegex(ValueError, 'availability guard mismatch'):
                    verifier.verify_capture_guards(replace_body(self.script, 'tdGroundItemAvailable', body.replace(old, 'false')))

    def test_each_missing_preconsume_ingredient_guard_is_rejected(self):
        body = function_body(self.script, 'tdGroundConsumeBatch')
        for item in ('TDGroundItemRuntime_tdGroundFirst', 'TDGroundItemRuntime_tdGroundSecond', 'third'):
            condition = ('not tdGroundItemAvailable(third, TDGroundItemRuntime_tdGroundQuality)' if item == 'third' else
                         '( not tdGroundItemAvailable(' + item + ', TDGroundItemRuntime_tdGroundQuality))')
            self.assertIn(condition, body)
            with self.subTest(item=item), self.assertRaises(ValueError):
                verifier.verify_lifecycle_guards(replace_body(self.script, 'tdGroundConsumeBatch', body.replace(condition, 'false')))

    def test_missing_gameover_null_third_and_duplicate_guards_are_rejected(self):
        body = function_body(self.script, 'tdGroundConsumeBatch')
        changes = [body.replace('tdIsGameOver()', 'false'),
                   body.replace('third == null', 'false').replace('not tdGroundItemAvailable(third, TDGroundItemRuntime_tdGroundQuality)', 'false'),
                   re.sub(r'if TDGroundItemRuntime_tdGroundFirst == TDGroundItemRuntime_tdGroundSecond[^\n]+ then', 'if false then', body)]
        for changed in changes:
            with self.subTest(body=changed):
                self.assertNotEqual(changed, body)
                with self.assertRaises(ValueError):
                    verifier.verify_lifecycle_guards(replace_body(self.script, 'tdGroundConsumeBatch', changed))

    def test_each_missing_removal_wrong_product_quality_and_wrong_position_is_rejected(self):
        body = function_body(self.script, 'tdGroundConsumeBatch')
        changes = [body.replace('\tcall RemoveItem(' + item + ')\n', '')
                   for item in ('TDGroundItemRuntime_tdGroundFirst', 'TDGroundItemRuntime_tdGroundSecond', 'third')]
        changes += [body.replace('tdCraftResultQuality(TDGroundItemRuntime_tdGroundQuality)', 'TDGroundItemRuntime_tdGroundQuality'),
                    body.replace('tdGroundItemPilePosition(TDGroundItemRuntime_tdGroundCasterLane,', 'tdGroundItemPilePosition(1,')]
        for changed in changes:
            with self.subTest(body=changed):
                self.assertNotEqual(changed, body)
                with self.assertRaisesRegex(ValueError, 'triple/leftover|quality mismatch|coordinate mismatch'):
                    verifier.verify_upgrade_batches(replace_body(self.script, 'tdGroundConsumeBatch', changed))

    def test_missing_busy_or_foreign_target_cast_guard_is_rejected(self):
        body = function_body(self.script, 'tdGroundHandleUpgrade')
        changes = [body.replace('if TDGroundItemRuntime_tdGroundBusy then', 'if false then'),
                   re.sub(r'if tdGroundItemLane\([^\n]+ then', 'if false then', body)]
        for changed in changes:
            with self.subTest(body=changed):
                self.assertNotEqual(changed, body)
                with self.assertRaisesRegex(ValueError, 'active snapshot|other-lane cast'):
                    verifier.verify_lifecycle_guards(replace_body(self.script, 'tdGroundHandleUpgrade', changed))

    def test_old_ground_tooltip_is_rejected(self):
        abilities = deepcopy(self.abilities)
        abilities['Gupg'][1][('aub1', 1, 0)] = (3, '余 2 件按 65% 成功率合成，失败材料损毁；产物继续合成至紫装。')
        with self.assertRaisesRegex(ValueError, 'Ground tooltip'):
            verifier.verify_tooltip(abilities)

    def test_changed_pile_helper_and_radius_cannot_validate_themselves(self):
        body = function_body(self.script, 'tdGroundItemPileCenter')
        self.assertIn('768.0', body)
        with self.assertRaisesRegex(ValueError, 'fixed four-lane coordinate oracle mismatch'):
            verifier.verify_geometry(replace_body(self.script, 'tdGroundItemPileCenter', body.replace('768.0', '700.0')))
        changed = self.script.replace('set TDGroundItemRules_TD_GROUND_UPGRADE_RADIUS = 144.0',
                                      'set TDGroundItemRules_TD_GROUND_UPGRADE_RADIUS = 143.0')
        self.assertNotEqual(changed, self.script)
        with self.assertRaisesRegex(ValueError, '144 boundary'):
            verifier.verify_geometry(changed)

    def test_interpreter_array_integer_division_and_fail_closed_boolean_subset(self):
        runtime = verifier.GroundJassRuntime(self.script)
        self.assertEqual(runtime.expression('7 / 5', {}), 1)
        self.assertEqual(runtime.expression('7 / 5.0', {}), 1.4)
        self.assertEqual(runtime.expression('TDItemData_tdItemQualitySizes[2]', {}), 8)
        with self.assertRaisesRegex(ValueError, 'Jass-specific precedence parser'):
            runtime.expression('(true or false) and true', {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
