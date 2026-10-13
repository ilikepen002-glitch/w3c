"""Execute hot paths from an actual map; collections/engine natives are bounded stubs.

Set HOTPATH_CANDIDATE_MAP to the freshly built map. No Warcraft process is launched.
"""
from collections import Counter
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyTrialReplay import TrialJassRuntime
from VerifyPureBossArtifact import source_function


class HotpathRuntime(TrialJassRuntime):
    def __init__(self, script):
        self.operations = Counter()
        super().__init__(script)

    def native(self, name, args):
        self.operations[name] += 1
        if name == 'dispatch_LinkedList_LinkedList_remove':
            values = self.lists[args[0]]
            if args[1] not in values:
                return True, False
            values.remove(args[1])
            return True, True
        if name == 'dispatch_LinkedList_destroyLinkedList':
            # Stdlib destroys list nodes even when values remain. Volley destroys
            # its shot values first; those production destructors are not mocked.
            if args[0] not in self.lists:
                raise ValueError('Destroying unknown modeled list')
            del self.lists[args[0]]
            return True, None
        return super().native(name, args)


class HotpathSourceContracts(unittest.TestCase):
    def test_aura_target_snapshot_is_local_and_inside_try(self):
        source = (ROOT / 'wurst/auras/TDAuraRuntime.wurst').read_text(encoding='utf-8')
        refresh = source_function(source, 'tdAuraRefresh')
        scan = source_function(source, 'tdAuraOfferSource')
        for expr in ('target.getPos()', 'IsUnitType(target, UNIT_TYPE_MECHANICAL)',
                     'tdAuraCooldownTargetEligible(target)'):
            self.assertNotIn(expr, scan)
            self.assertEqual(refresh.count(expr), 1)
        self.assertIn('record.tower and tdAuraCooldownTargetEligible(target)', refresh)
        self.assertLess(refresh.index('let success = try()'), refresh.index('let targetPos'))
        self.assertLess(refresh.index('for source in tdAuraTowers'), refresh.index('record.effective = prepared'))
        self.assertIn('distance <= tdItemAuraRadius(itemId)', scan)
        self.assertIn('distance <= 600.0', scan)
        self.assertIn('distance <= 900.0', scan)

    def test_attack_reuses_validated_entry_and_clock(self):
        source = (ROOT / 'wurst/items/TDEquipmentCombat.wurst').read_text(encoding='utf-8')
        attack = source_function(source, 'tdApplyEquipmentAttack')
        self.assertEqual(attack.count('tdEquipmentDebuffFor('), 1)
        self.assertEqual(attack.count('getElapsedGameTime()'), 1)
        self.assertIn('tdApplyEquipmentArmorToEntry(entry, armor, 3.0, now)', attack)
        public = source_function(source, 'tdApplyEquipmentArmor')
        self.assertIn('tdEquipmentEnemyValid(target, lane)', public)


class HotpathPackedReplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get('HOTPATH_CANDIDATE_MAP')
        if not path:
            raise unittest.SkipTest('Fresh HOTPATH_CANDIDATE_MAP not supplied')
        cls.script = Mpq(Path(path).read_bytes()).extract('war3map.j').decode()

    def runtime(self):
        r = HotpathRuntime(self.script)
        r.initialize_match()
        r.operations.clear()
        return r

    def assert_empty_debuffs(self, r):
        self.assertFalse(r.tables[r.globals['TDEquipmentCombat_tdEquipmentDebuffsByHandle']])
        self.assertFalse(r.lists[r.globals['TDEquipmentCombat_tdEquipmentDebuffs']])

    def test_lookup_is_constant_and_forget_clears_index_before_handle_reuse(self):
        r = self.runtime()
        entry = r.invoke('tdEquipmentDebuffFor', 100, 0)
        for _ in range(100):
            self.assertEqual(r.invoke('tdEquipmentDebuffFor', 100, 0), entry)
        self.assertEqual(r.operations['new_TDEquipmentDebuff'], 1)
        self.assertEqual(r.operations['LinkedList_iterator'], 0)
        self.assertEqual(r.operations['LLIterator_next'], 0)
        r.invoke('tdForgetEquipmentEnemy', 100)
        self.assert_empty_debuffs(r)
        # A recycled numeric handle starts with fresh poison/armor/context fields.
        fresh = r.invoke('tdEquipmentDebuffFor', 100, 0)
        self.assertEqual(r.globals['TDEquipmentDebuff_armor'][fresh], 0.0)
        self.assertEqual(r.globals['TDEquipmentDebuff_poisonTicks'][fresh], 0)
        r.invoke('tdForgetEquipmentEnemy', 100)
        r.invoke('tdForgetEquipmentEnemy', 100)
        r.invoke('tdForgetEquipmentEnemy', None)
        self.assert_empty_debuffs(r)

    def test_expiry_and_death_retire_both_collections(self):
        r = self.runtime()
        r.invoke('tdApplyEquipmentArmor', 100, 0, 3.0, 1.0)
        self.assertTrue(r.tables[r.globals['TDEquipmentCombat_tdEquipmentDebuffsByHandle']])
        r.now += 1.0
        r.invoke('tdTickEquipmentDebuffs')
        self.assert_empty_debuffs(r)
        r.invoke('tdApplyEquipmentArmor', 100, 0, 3.0, 5.0)
        r.units[100]['alive'] = False
        r.invoke('tdTickEquipmentDebuffs')
        self.assert_empty_debuffs(r)

    def test_trial_cleanup_retires_index_and_captured_revision(self):
        r = self.runtime()
        r.enter(8)
        target = r.target(0)
        entry = r.invoke('tdEquipmentDebuffFor', target, 0)
        revision = r.globals['TDEquipmentDebuff_targetRevision'][entry]
        self.assertGreater(revision, 0)
        r.invoke('tdTrialRemoveTarget', r.binding(0))
        self.assert_empty_debuffs(r)

    def test_split_selection_rejects_without_allocation_and_preserves_ties(self):
        r = self.runtime()
        shots = r.invoke('new_LinkedList')
        source = 101
        r.units[source].update(x=0.0, y=0.0)
        for handle, x in ((110, 300.0), (111, 600.0), (112, 600.0), (113, 150.0), (114, 900.0)):
            r.units[handle] = {**r.units[100], 'x': x, 'y': 0.0}
        for invalid in ((0, source, 110, 2), (shots, None, 110, 2),
                        (shots, source, None, 2), (shots, source, 110, 0)):
            r.invoke('tdTryAddArcherSplitArrowShot', *invalid)
        self.assertEqual(r.operations['new_TDArcherSplitArrowShot'], 0)
        for target in (110, 111):
            r.invoke('tdTryAddArcherSplitArrowShot', shots, source, target, 2)
        initial = list(r.lists[shots])
        for target in (112, 114):
            r.invoke('tdTryAddArcherSplitArrowShot', shots, source, target, 2)
        self.assertEqual(r.lists[shots], initial)
        self.assertEqual(r.operations['new_TDArcherSplitArrowShot'], 2)
        self.assertEqual(r.operations['tdTrialCaptureContext'], 2)
        r.invoke('tdTryAddArcherSplitArrowShot', shots, source, 113, 2)
        self.assertEqual([r.globals['TDArcherSplitArrowShot_target'][shot] for shot in r.lists[shots]], [110, 113])
        self.assertEqual(r.operations['new_TDArcherSplitArrowShot'], 3)
        self.assertEqual(r.operations['dispatch_TDArcherSplitArrowShot_destroyTDArcherSplitArrowShot'], 1)
        # The production volley owns all selected shot destruction.
        volley = r.invoke('new_TDArcherSplitArrowVolley', source, 100, 0.0, shots)
        r.invoke('dispatch_TDArcherSplitArrowVolley_destroyTDArcherSplitArrowVolley', volley)
        self.assertNotIn(shots, r.lists)
        self.assertEqual(r.operations['dispatch_TDArcherSplitArrowShot_destroyTDArcherSplitArrowShot'], 3)


if __name__ == '__main__':
    unittest.main()
