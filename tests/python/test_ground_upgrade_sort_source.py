"""Upgrade-to-sort source contracts, not compiled or Warcraft runtime proof."""
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyEquipmentPhaseA import verify_runtime_entrypoints


def code_only(source):
    return '\n'.join(row.split('//', 1)[0] for row in source.splitlines())


def function_body(source, name):
    match = re.search(r'^(?:public )?function ' + name + r'\([^\n]*\n', source, re.M)
    if not match:
        raise AssertionError('Missing function: ' + name)
    rows = []
    for row in source[match.end():].splitlines():
        if row and not row[0].isspace():
            break
        rows.append(row)
    return code_only('\n'.join(rows))


class GroundUpgradeSortSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crafting = (ROOT / 'wurst/items/TDCraftingRuntime.wurst').read_text()
        cls.ground = (ROOT / 'wurst/items/TDGroundItemRuntime.wurst').read_text()
        cls.rules = (ROOT / 'wurst/items/TDGroundItemRules.wurst').read_text()

    def test_finish_preserves_lane_and_cleans_session_before_lock_handoff(self):
        finish = function_body(self.crafting, 'tdFinishCraftSession')
        steps = ('let groundLane = tdCraftCaptureLane', 'tdCraftSession = null',
                 'tdCraftCaptureLane = -1', 'destroy session',
                 'tdItemOperationRelease()', 'tdSortGroundEquipmentAfterUpgrade(groundLane)')
        positions = [finish.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(finish.count('tdSortGroundEquipmentAfterUpgrade('), 1)

    def test_finish_sorts_zero_success_empty_and_all_cancelled_sessions(self):
        finish = function_body(self.crafting, 'tdFinishCraftSession')
        hook = finish.split('tdItemOperationRelease()', 1)[1].strip()
        self.assertEqual(hook, 'if tdIsLanePlayer(groundLane) and not tdIsGameOver()\n'
                              '\t\ttdSortGroundEquipmentAfterUpgrade(groundLane)')
        # Counts are display-only, never a prerequisite for sorting leftovers.
        conditions = '\n'.join(row.strip() for row in finish.splitlines()
                               if row.strip().startswith(('if ', 'else if ')))
        for field in ('successes', 'cancelled', 'batchCount', 'recordCount'):
            self.assertNotIn(field, conditions)

    def test_handoff_has_no_yield_or_deferred_start(self):
        path = '\n'.join((function_body(self.crafting, 'tdFinishCraftSession'),
                          function_body(self.ground, 'tdSortGroundEquipmentAfterUpgrade'),
                          function_body(self.ground, 'tdGroundStart')))
        for deferred in ('doAfter(', 'doPeriodically(', 'TriggerSleepAction(', 'PolledWait(', '.execute('):
            self.assertNotIn(deferred, path)
        start = function_body(self.ground, 'tdGroundStart')
        self.assertLess(start.index('tdItemOperationTryAcquire()'), start.index('tdGroundBusy = true'))
        self.assertLess(start.index('tdGroundSortLane = requestedLane'), start.index('EnumItemsInRect('))

    def test_inventory_and_rejected_ground_requests_do_not_start_sorting(self):
        inventory = function_body(self.crafting, 'tdStartInventoryCraft')
        self.assertNotIn('tdCraftCaptureLane =', inventory)
        self.assertNotIn('tdSortGroundEquipmentAfterUpgrade', inventory)
        ground = function_body(self.crafting, 'tdStartGroundCraft')
        self.assertNotIn('tdSortGroundEquipmentAfterUpgrade', ground)
        self.assertLess(ground.index('tdGroundItemLane(point.x, point.y) != lane'),
                        ground.index('tdCraftSession = new'))
        self.assertLess(ground.index('if not tdCraftCanStart(farmer)'), ground.index('tdCraftSession = new'))
        self.assertIn('\nint tdCraftCaptureLane = -1\n', self.crafting)
        setup = function_body(self.crafting, 'tdSetupCraftingRuntime')
        self.assertRegex(setup, r'if tdCraftSession != null\n\s+if tdIsGameOver\(\)\n\s+tdFinishCraftSession\(\)')

    def test_setup_initializes_ground_before_registering_craft_and_is_idempotent(self):
        setup = function_body(self.crafting, 'tdSetupCraftingRuntime')
        self.assertRegex(setup, r'^\tif tdCraftRuntimeReady\n\t\treturn\n\ttdCraftRuntimeReady = true')
        steps = ('tdSetupGroundItemRuntime()', 'tdSetupCraftPickupWatch()',
                 'registerSpellEffectEvent(TD_FARMER_GROUND_UPGRADE_ABILITY_ID, function tdGroundHandleUpgrade)',
                 'doPeriodically(0.03)')
        positions = [setup.index(step) for step in steps]
        self.assertEqual(positions, sorted(positions))
        ground_setup = function_body(self.ground, 'tdSetupGroundItemRuntime')
        self.assertRegex(ground_setup, r'^\tif tdGroundRuntimeReady\n\t\treturn\n\ttdGroundRuntimeReady = true')
        self.assertNotIn('tdSetupCraftingRuntime()', ground_setup)
        init = (ROOT / 'wurst/TDInit.wurst').read_text()
        self.assertIn('tdSetupInventoryRuntime()', init)
        self.assertIn('tdSetupGroundItemRuntime()', init)
        inventory_runtime = (ROOT / 'wurst/items/TDInventoryRuntime.wurst').read_text()
        self.assertIn('tdSetupCraftingRuntime()', function_body(inventory_runtime, 'tdSetupInventoryRuntime'))

    def test_sorter_has_no_direct_or_transitive_import_back_to_crafting(self):
        graph = {}
        for path in (ROOT / 'wurst').rglob('*.wurst'):
            if '_tests' in path.parts:
                continue
            source = code_only(path.read_text())
            name = re.search(r'^package (\w+)', source, re.M)[1]
            graph[name] = re.findall(r'^import (?:public )?(\w+)', source, re.M)
        self.assertIn('TDGroundItemRuntime', graph['TDCraftingRuntime'])
        pending = ['TDGroundItemRuntime']
        seen = set()
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            pending.extend(graph.get(name, []))
        self.assertNotIn('TDCraftingRuntime', seen)

    def test_periodic_sort_keeps_all_lanes_and_balls_while_upgrade_is_lane_only(self):
        setup = function_body(self.ground, 'tdSetupGroundItemRuntime')
        self.assertIn('doPeriodically(TD_GROUND_SORT_INTERVAL)', setup)
        self.assertIn('tdGroundStart(-1)', setup)
        entry = function_body(self.ground, 'tdSortGroundEquipmentAfterUpgrade')
        self.assertIn('if tdGroundRuntimeReady and tdIsLanePlayer(lane) and not tdIsGameOver()', entry)
        self.assertIn('tdGroundStart(lane)', entry)
        start = function_body(self.ground, 'tdGroundStart')
        self.assertIn('if requestedLane >= 0 and lane != requestedLane\n\t\t\tcontinue', start)
        eligibility = function_body(self.rules, 'tdGroundSortItemEligible')
        self.assertIn('sourceLane < 0 or sourceLane >= TD_ACTIVE_PLAYER_COUNT', eligibility)
        self.assertIn('pileGroup < TD_ITEM_QUALITY_WHITE or pileGroup > 5', eligibility)
        self.assertIn('if requestedLane == -1\n\t\treturn true', eligibility)
        self.assertIn('return requestedLane == sourceLane and pileGroup <= TD_ITEM_QUALITY_PURPLE', eligibility)

    def test_capture_and_dequeue_recheck_identical_mask_lane_quality_and_handle_filter(self):
        available = function_body(self.ground, 'tdGroundItemAvailable')
        self.assertIn('not tdGroundItemHandleValid(itm) or not IsItemVisible(itm)', available)
        self.assertIn('tdGroundSortItemEligible(tdGroundSortLane, tdGroundSortSourceLane(GetItemX(itm), GetItemY(itm)), quality)', available)
        self.assertIn('return tdGroundItemGroup(GetItemTypeId(itm)) == quality', available)
        capture = function_body(self.ground, 'tdGroundCaptureItem')
        self.assertIn('if tdGroundItemAvailable(itm, pileGroup)', capture)
        dequeue = function_body(self.ground, 'tdGroundProcessOne')
        self.assertLess(dequeue.index('let itm = queue.dequeue()'),
                        dequeue.index('not tdGroundItemAvailable(itm, tdGroundQuality)'))
        self.assertLess(dequeue.index('not tdGroundItemAvailable(itm, tdGroundQuality)'),
                        dequeue.index('tdTryPlaceItemInPile('))

    def test_sort_keeps_chunk_budget_and_moves_existing_handles_without_crafting(self):
        setup = function_body(self.ground, 'tdSetupGroundItemRuntime')
        self.assertIn('doPeriodically(0.03)', setup)
        self.assertIn('for _operation = 1 to 24', setup)
        self.assertIn('tdTryPlaceItemInPile(itm, lane, tdGroundQuality,', self.ground)
        self.assertIn('tdRestoreSortedItem(itm, lane, origin)', self.ground)
        for operation in ('CreateItem(', 'RemoveItem(', 'tdCommitCraftBatch(', 'tdStartGroundCraft('):
            self.assertNotIn(operation, code_only(self.ground))
        finish = function_body(self.ground, 'tdGroundFinish')
        self.assertLess(finish.index('tdGroundSortLane = -1'), finish.index('tdItemOperationRelease()'))

    def test_player_tooltip_describes_immediate_start_without_claiming_sync_completion(self):
        objects = (ROOT / 'wurst/items/TDItemObjectGen.wurst').read_text()
        self.assertIn('结束后立即开始整理本路坑道内的装备，按品质归堆', objects)
        for rule in ('新产物本次不再参与', '余1至2件、紫装、背包和捕获球不消耗',
                     '坑外产物留在操作附近，其他坑外物品不移动'):
            self.assertIn(rule, objects)


class GroundUpgradeEntryOwnerMutationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.items = self.root / 'wurst/items'
        self.items.mkdir(parents=True)
        for name in ('TDInventoryRuntime.wurst', 'TDGroundItemRuntime.wurst', 'TDCraftingRuntime.wurst'):
            shutil.copyfile(ROOT / 'wurst/items' / name, self.items / name)
        verify_runtime_entrypoints(self.root)

    def mutate(self, name, old, new, reason):
        path = self.items / name
        source = path.read_text()
        self.assertEqual(source.count(old), 1, 'Nonunique mutation needle')
        path.write_text(source.replace(old, new, 1))
        with self.assertRaisesRegex(ValueError, reason):
            verify_runtime_entrypoints(self.root)

    def test_old_ground_owner_cannot_pass_current_entry_checker(self):
        self.mutate('TDCraftingRuntime.wurst', 'tdStartGroundCraft(farmer,',
                    'tdLegacyGroundCraft(farmer,', 'Ground craft entry not connected in crafting runtime')

    def test_reverse_import_is_rejected(self):
        self.mutate('TDGroundItemRuntime.wurst', 'import TDConfig',
                    'import TDConfig\nimport TDCraftingRuntime', 'Ground sorter must not import crafting runtime')

    def test_missing_registration_is_rejected(self):
        self.mutate('TDCraftingRuntime.wurst',
                    'registerSpellEffectEvent(TD_FARMER_GROUND_UPGRADE_ABILITY_ID, function tdGroundHandleUpgrade)',
                    'skip', 'registered exactly once in crafting runtime')

    def test_duplicate_registration_outside_items_is_rejected(self):
        (self.root / 'wurst/DuplicateGroundUpgrade.wurst').write_text(
            'package DuplicateGroundUpgrade\ninit\n'
            '\tregisterSpellEffectEvent(TD_FARMER_GROUND_UPGRADE_ABILITY_ID, function tdGroundHandleUpgrade)\n')
        with self.assertRaisesRegex(ValueError, 'registered exactly once in crafting runtime'):
            verify_runtime_entrypoints(self.root)

    def test_duplicate_handler_owner_is_rejected(self):
        with (self.items / 'TDGroundItemRuntime.wurst').open('a') as stream:
            stream.write('\nfunction tdGroundHandleUpgrade() returns boolean\n\treturn false\n')
        with self.assertRaisesRegex(ValueError, 'exactly one crafting-runtime owner'):
            verify_runtime_entrypoints(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)

class GroundUpgradeCooldownOwnerTests(unittest.TestCase):
    def test_current_exact_owner_and_wrong_role_mutations(self):
        import VerifyActiveCooldownContract as gate
        sources = gate.read_sources()
        gate.verify_source(sources=sources)
        path = 'items/TDCraftingRuntime.wurst'
        needle = 'registerSpellEffectEvent(TD_FARMER_GROUND_UPGRADE_ABILITY_ID, function tdGroundHandleUpgrade)'
        self.assertIn(needle, sources[path])
        for replacement in ('registerSpellEffectEvent(TD_ORC_BLOODLUST_ABILITY_ID, function tdGroundHandleUpgrade)',
                            'registerSpellEffectEvent(TD_FARMER_GROUND_UPGRADE_ABILITY_ID, function unknown)',
                            needle + '\n\tregisterSpellEffectEvent(TD_FARMER_CRAFT_ABILITY_ID, function tdGroundHandleUpgrade)'):
            changed = dict(sources); changed[path] = sources[path].replace(needle, replacement, 1)
            with self.subTest(role=replacement), self.assertRaisesRegex(ValueError, 'Unknown spell registration owner'):
                gate.verify_source(sources=changed)
