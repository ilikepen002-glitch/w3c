"""Focused actual-source workflow and exact shared-order negative contracts."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyPetManagerSource as source
import VerifyPetUIArtifact as artifact
import VerifyGroundItemArtifact as orders
from test_pet_manager_contracts import current_manager_fixture, field


def quiet(call, *args):
    with redirect_stdout(io.StringIO()):
        return call(*args)


class CurrentSourceWorkflowTests(unittest.TestCase):
    def test_real_610_ids_all_invalid_counts_pages_hotkeys_and_current_wiring(self):
        quiet(source.verify_scalar_contracts)
        quiet(source.verify_ui_workflow)
        with redirect_stdout(io.StringIO()):
            source.verify_wiring(verify_legacy_wild_scope=False)
        n = source.scalar_helpers()
        self.assertEqual([n['tdPetActionCell'](3, a) for a in (17, 18, 21, 22)], [4, 7, 8, 11])
        self.assertEqual([n['tdPetActionHotkey'](a) for a in (17, 18, 21, 22)], ['Q', 'E', 'W', 'R'])
        for a in (0, 1, 2, 3, 7, 15, 16):
            self.assertEqual(n['tdPetActionCell'](3, a), -1)

    def test_user_integer_rawcode_and_quiet_detail_summary_bytes_preserved(self):
        before = subprocess.check_output(['git', 'show', '28f16681bc07b58066f10d51e8aed7ba626fb768:wurst/pets/TDPetUIView.wurst'], cwd=ROOT)
        current = source.source('TDPetUIView')
        for name in ('tdPetPageSummary', 'tdPetShowPageSummary', 'tdPetSelectFarmer', 'retire'):
            actual = source.function_body(current, name)[1]
            if name == 'tdPetPageSummary':
                actual = actual.replace('\"\\n\" + tdPetSlotName(slot)', '\"\\n栏\" + (slot + 1)')
            if name == 'tdPetPageSummary':
                # Normalize only the exact authorized dirty/stale guard. Every
                # other historical summary byte remains protected below.
                guarded = 'if session == null or not session.active or session.dirty or session.mode != TD_PET_UI_DETAIL or not session.snapshotCurrent()'
                self.assertEqual(actual.count(guarded), 1)
                actual = actual.replace(guarded, 'if session == null or not session.active or session.mode != TD_PET_UI_DETAIL', 1)
            self.assertEqual(actual, source.function_body(before.decode(), name)[1])
        self.assertIn('宿主已有自带暴击', source.function_body(current, 'tdPetSkillRestriction')[1])
        self.assertNotIn('tdPetShowPageSummary', source.function_body(source.source('TDPetUI'), 'showPage')[1])

    def test_active_icons_and_archived_species_sources_remain_exact(self):
        quiet(source.verify_assets)

    def test_execute_real_failure_and_stale_release_routes(self):
        class Record:
            lane = 0
            released = False
        pet, replacement = Record(), Record()
        n = source.scalar_helpers()
        n.update(tdPetUISessions=[SimpleNamespace(pet=pet, page=1)], tdPetSelectedSlot=[19],
                 tdPetCancelRelease=lambda lane: None,
                 showPage=lambda lane, mode, page, slot, nonce: (mode, page, slot),
                 showCultivation=lambda lane: 'cultivation')
        text = source.source('TDPetUI').replace('\ttdPetCancelRelease(lane)\n', '\tlet _cancel = tdPetCancelRelease(lane)\n')
        text = text.replace('\t\tshowPage(', '\t\treturn showPage(').replace('\t\tshowCultivation(lane)', '\t\treturn showCultivation(lane)')
        stale = source.compile_source_helper(text, 'refreshStale', n)
        fallback = source.compile_source_helper(text, 'showDetailOrList', n)
        for current, expected in [(pet, 1), (None, 0), (replacement, 0)]:
            n['tdPetAt'] = lambda lane, slot: current
            self.assertEqual(stale(0, 4), (expected, 1, 19))
            self.assertEqual(fallback(0, 1, 19, pet), (expected, 1, 19))


class AtomicContinueSourceTests(unittest.TestCase):
    def setUp(self):
        self.pet = SimpleNamespace(released=False, skillCount=2, proposalSlot=0, proposalVersion=7,
                                   proposalRevision=3, revision=3, proposalOldSkill=0, proposalOldQuality=2,
                                   proposalSkill=1, proposalQuality=1, readyAt=88, generation=9)
        self.draws = []
        self.pet.canRollSkill = lambda slot: True
        self.pet.rollSkill = lambda slot, quality: self.draws.append(slot) or 2
        self.pet.skillAt = lambda slot: 0
        self.pet.qualityAt = lambda slot: 2
        self.n = source.scalar_helpers()
        self.n.update(tdPetAt=lambda lane, slot: self.pet, tdPetLaneCanManage=lambda lane: 0 <= lane < 4,
                      tdPetRerollStones=[2, 0, 0, 0], GetRandomInt=lambda lo, hi: 50,
                      tdPetQualityForRoll=lambda roll: 2)
        self.continue_ = source.compile_source_helper(source.source('TDPetState'), 'tdPetContinueReroll', self.n)

    def candidate_state(self):
        return tuple(getattr(self.pet, key) for key in ('proposalSlot', 'proposalVersion', 'proposalRevision', 'proposalOldSkill', 'proposalOldQuality', 'proposalSkill', 'proposalQuality', 'revision', 'skillCount', 'readyAt', 'generation'))

    def test_actual_success_charges_and_versions_once_with_owned_state_unchanged(self):
        self.assertTrue(self.continue_(0, 0, self.pet, 7, 3))
        self.assertEqual(self.n['tdPetRerollStones'][0], 1)
        self.assertEqual(self.candidate_state(), (0, 8, 3, 0, 2, 2, 2, 3, 2, 88, 9))
        self.assertEqual(self.draws, [0])
        state = self.candidate_state()
        self.assertFalse(self.continue_(0, 0, self.pet, 7, 3))
        self.assertEqual(self.candidate_state(), state)
        self.assertEqual(self.n['tdPetRerollStones'][0], 1)
        self.assertEqual(self.draws, [0])

    def test_actual_guard_failures_preserve_candidate_balance_and_do_not_draw(self):
        mutations = [('released', True), ('proposalSlot', -1), ('proposalSlot', 2), ('proposalSlot', 4),
                     ('proposalVersion', 2147483647), ('proposalRevision', 4), ('revision', 4)]
        for key, value in mutations:
            before = getattr(self.pet, key)
            setattr(self.pet, key, value)
            state = self.candidate_state()
            self.assertFalse(self.continue_(0, 0, self.pet, self.pet.proposalVersion, 3), key)
            self.assertEqual(self.candidate_state(), state)
            self.assertEqual(self.n['tdPetRerollStones'][0], 2)
            setattr(self.pet, key, before)
        for args in [(0, 0, object(), 7, 3), (0, 0, self.pet, 6, 3), (0, 0, self.pet, 0, 3), (0, 0, self.pet, 7, 4), (-1, 0, self.pet, 7, 3)]:
            state = self.candidate_state()
            self.assertFalse(self.continue_(*args))
            self.assertEqual(self.candidate_state(), state)
        for balance in (0, -1, self.n['TD_PET_MATERIAL_LIMIT'] + 1):
            self.n['tdPetRerollStones'][0] = balance
            state = self.candidate_state()
            self.assertFalse(self.continue_(0, 0, self.pet, 7, 3))
            self.assertEqual(self.candidate_state(), state)
            self.assertEqual(self.n['tdPetRerollStones'][0], balance)
        self.assertEqual(self.draws, [])

    def test_actual_missing_record_replacement_and_empty_pool_preserve_candidate(self):
        state = self.candidate_state()
        self.n['tdPetAt'] = lambda lane, slot: None
        self.assertFalse(self.continue_(0, 0, self.pet, 7, 3))
        self.n['tdPetAt'] = lambda lane, slot: SimpleNamespace(released=False)
        self.assertFalse(self.continue_(0, 0, self.pet, 7, 3))
        self.n['tdPetAt'] = lambda lane, slot: self.pet
        self.pet.canRollSkill = lambda slot: False
        self.pet.rollSkill = lambda slot, quality: -1
        self.assertFalse(self.continue_(0, 0, self.pet, 7, 3))
        self.assertEqual(self.candidate_state(), state)
        self.assertEqual(self.n['tdPetRerollStones'][0], 2)


class SharedOrderContractTests(unittest.TestCase):
    def setUp(self):
        self.abilities, _ = current_manager_fixture(elemental=True)

    def test_633_objects_and_33_unique_orders_are_distinct_budget_measures(self):
        self.assertEqual(orders.verify_global_channel_orders(self.abilities), 633)
        self.assertEqual(orders.unique_channel_order_count(self.abilities), 33)
        artifact.verify_manager_commands(self.abilities)
        artifact.verify_manager_list(self.abilities)
        artifact.verify_manager_preview(self.abilities)

    def test_only_complete_exact_61_state_cell_families_can_share_order(self):
        for change in ('missing', 'extra', 'parent', 'levels', 'cell', 'key', 'target', 'second-level-order', 'within-cell', 'across-cell', 'outside-object'):
            abilities = deepcopy(self.abilities)
            if change == 'missing': del abilities['L966']
            elif change == 'extra': abilities['L96A'] = deepcopy(abilities['L966'])
            elif change == 'parent': abilities['L001'] = ('AOcr', abilities['L001'][1])
            elif change == 'levels': field(abilities['L001'][1], 'alev', 1)
            elif change == 'cell': field(abilities['L001'][1], 'abpx', 1)
            elif change == 'key': field(abilities['L001'][1], 'ahky', 'W')
            elif change == 'target': field(abilities['L001'][1], 'Ncl2', 1, 2, 2)
            elif change in ('second-level-order', 'within-cell'):
                for level in ((2,) if change == 'second-level-order' else (1, 2)):
                    field(abilities['L001'][1], 'Ncl6', 'wrongorder', level, 6)
            elif change == 'across-cell':
                for index in (241 + offset for offset in (0, *range(1, 241, 4))):
                    for level in (1, 2): field(abilities[f'L{index:03X}'][1], 'Ncl6', 'listcell0', level, 6)
            else: field(abilities['Pm0B'][1], 'Ncl6', 'listcell0', 1, 6)
            with self.subTest(change=change), self.assertRaises(ValueError):
                orders.verify_global_channel_orders(abilities)

    def test_direct_channel_list_flags_and_timing_are_checked_in_actual_fields(self):
        for key, level, column, value in [('Ncl1', 2, 1, 1.0), ('Ncl3', 1, 3, 0), ('Ncl4', 2, 4, 1.0),
                                         ('Ncl5', 1, 5, 1), ('amcs', 2, 0, 1), ('acdn', 1, 0, 1.0),
                                         ('aher', 0, 0, 1), ('aite', 0, 0, 1)]:
            abilities = deepcopy(self.abilities)
            field(abilities['L966'][1], key, value, level, column)
            with self.subTest(field=key), self.assertRaises(ValueError):
                artifact.verify_manager_list(abilities)


if __name__ == '__main__':
    unittest.main(verbosity=2)
