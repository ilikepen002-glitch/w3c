"""Execute the real release source in the existing bounded Python subset.

No Wurst compiler, JASS artifact, native engine, staging or map build is run.
Native match state/randomness/recall are explicit test boundaries.
"""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyPetManagerSource import compile_source_helper, function_body, scalar_helpers, source


class PurpleReleaseSourceTests(unittest.TestCase):
    def setUp(self):
        self.n = scalar_helpers()
        self.random_calls = []
        self.quality_reads = []
        self.roll = 100
        self.active = [True] * 4
        self.defeated = [False] * 4
        self.finished = [False] * 4
        self.game_over = False
        self.n.update(tdPets=[None] * 80, releaseNonce=[0] * 4,
                      releaseSlot=[-1] * 4, releasePet=[None] * 4,
                      releaseRevision=[0] * 4, releaseGeneration=[0] * 4,
                      tdPetPlayerLeft=[False] * 4, tdPetRerollStones=[0] * 4,
                      tdPetSlotStones=[0] * 4,
                      tdIsLaneActive=lambda lane: self.active[lane],
                      tdIsLaneDefeated=lambda lane: self.defeated[lane],
                      tdIsLaneFinished=lambda lane: self.finished[lane],
                      tdIsGameOver=lambda: self.game_over,
                      GetRandomInt=self.random)
        text = source('TDPetState')
        # The subset handles assignments, not void expression statements. Bind
        # exactly these existing calls to ignored locals; their bodies still run.
        # A bare procedure return is expressed as return null in this subset.
        text = text.replace('\ttdPetCancelRelease(lane)\n', '\tlet _cancel = tdPetCancelRelease(lane)\n')
        text = text.replace('\tpet.recall()\n', '\tlet _recall = pet.recall()\n')
        text = text.replace('\t\treturn\n', '\t\treturn null\n')
        for name in ('tdPetReleaseLifecycleAllows', 'tdPetReleaseGetsSlotStone'):
            compile_source_helper(source('TDPetRules'), name, self.n)
        for name in ('tdPetAt', 'tdPetCancelRelease', 'tdPetLaneCanManage', 'canReleaseRecord', 'tdPetDiscardOwned', 'tdPetConfirmRelease'):
            compile_source_helper(text, name, self.n)
        self.confirm = self.n['tdPetConfirmRelease']
        self.pet = self.record([4, 2])
        self.ticket(self.pet)

    def random(self, low, high):
        self.random_calls.append((low, high))
        return self.roll

    def record(self, qualities):
        pet = SimpleNamespace(lane=0, level=1, skillCount=len(qualities),
                              qualities=qualities + [0] * (4 - len(qualities)),
                              proposalSlot=-1, proposalQuality=0, released=False,
                              host=None, revision=7, generation=3)
        def quality():
            self.quality_reads.append(pet.released)
            return self.n['tdPetOwnedQuality'](pet.skillCount, *pet.qualities)
        def recall():
            pet.generation += 1
            pet.host = None
        pet.quality = quality
        pet.recall = recall
        return pet

    def ticket(self, pet, nonce=11):
        self.n['tdPets'][0] = pet
        self.n['releaseNonce'][0] = nonce
        self.n['releaseSlot'][0] = 0
        self.n['releasePet'][0] = pet
        self.n['releaseRevision'][0] = pet.revision
        self.n['releaseGeneration'][0] = pet.generation

    def assert_no_reward(self):
        self.assertEqual(self.n['tdPetRerollStones'][0], 0)
        self.assertEqual(self.n['tdPetSlotStones'][0], 0)

    def test_unlocked_purple_gets_exactly_one_each_without_any_random_draw(self):
        self.n['tdPetRerollStones'][0] = 8
        self.n['tdPetSlotStones'][0] = 12
        self.roll = 1  # Would have awarded an extra stone if the purple path rolled.
        self.assertTrue(self.confirm(0, 11))
        self.assertEqual((self.n['tdPetRerollStones'][0], self.n['tdPetSlotStones'][0]), (9, 13))
        self.assertEqual(self.random_calls, [])
        self.assertEqual(self.quality_reads, [False])
        self.assertTrue(self.pet.released)
        self.assertIsNone(self.n['tdPets'][0])

    def test_only_resonance_locked_third_or_fourth_purple_skill_is_included(self):
        for qualities in ([1, 2, 4], [1, 2, 3, 4]):
            with self.subTest(qualities=qualities):
                self.setUp()
                self.pet = self.record(list(qualities))
                self.ticket(self.pet)
                self.assertEqual(self.pet.level + 1, 2)
                self.assertTrue(self.confirm(0, 11))
                self.assertEqual(self.n['tdPetSlotStones'][0], 1)
                self.assertEqual(self.random_calls, [])

    def test_non_owned_array_quality_and_unadopted_candidate_do_not_count(self):
        self.pet = self.record([1, 2])
        self.pet.qualities[3] = 4  # Not an owned skill, despite stale array data.
        self.pet.proposalQuality = 4
        self.ticket(self.pet)
        self.assertTrue(self.confirm(0, 11))
        self.assertEqual(self.n['tdPetSlotStones'][0], 0)
        self.assertEqual(self.random_calls, [(1, 100)])

    def test_adopted_reroll_downgrade_uses_current_color_and_stale_ticket_fails(self):
        self.pet.qualities[0] = 2
        self.pet.revision += 1
        self.assertFalse(self.confirm(0, 11))
        self.assert_no_reward()
        self.assertEqual(self.random_calls, [])
        self.ticket(self.pet, nonce=12)
        self.assertTrue(self.confirm(0, 12))
        self.assertEqual(self.n['tdPetRerollStones'][0], 1)
        self.assertEqual(self.n['tdPetSlotStones'][0], 0)
        self.assertEqual(self.random_calls, [(1, 100)])

    def test_repeated_confirm_is_single_use_and_stale_click_preserves_newer_ticket(self):
        self.ticket(self.pet, nonce=12)
        self.assertFalse(self.confirm(0, 11))
        self.assertEqual(self.n['releaseNonce'][0], 12)
        self.assertTrue(self.confirm(0, 12))
        self.assertFalse(self.confirm(0, 12))
        self.assertEqual((self.n['tdPetRerollStones'][0], self.n['tdPetSlotStones'][0]), (1, 1))
        self.assertEqual(self.random_calls, [])

    def test_non_purple_preserves_one_random_draw_and_exact_two_percent_boundary(self):
        for roll in range(1, 101):
            with self.subTest(roll=roll):
                self.setUp()
                self.pet = self.record([1, 3])
                self.ticket(self.pet)
                self.roll = roll
                self.assertTrue(self.confirm(0, 11))
                self.assertEqual(self.n['tdPetRerollStones'][0], 1)
                self.assertEqual(self.n['tdPetSlotStones'][0], int(roll in (1, 2)))
                self.assertEqual(self.random_calls, [(1, 100)])
        for invalid in (-1, 0, 101):
            self.assertFalse(self.n['tdPetReleaseGetsSlotStone'](invalid))

    def test_failed_discard_awards_nothing_and_reads_quality_before_removal(self):
        self.n['tdPetDiscardOwned'] = lambda lane, slot: False
        self.assertFalse(self.confirm(0, 11))
        self.assert_no_reward()
        self.assertFalse(self.pet.released)
        self.assertEqual(self.quality_reads, [False])
        self.assertEqual(self.random_calls, [])
        self.assertEqual(self.n['releaseNonce'][0], 0)

    def test_identity_revision_generation_and_lifecycle_failures_never_reward(self):
        mutations = [('revision', 8), ('generation', 4), ('lane', 1),
                     ('released', True), ('host', object()), ('proposalSlot', 0)]
        for name, value in mutations:
            with self.subTest(field=name):
                self.setUp()
                setattr(self.pet, name, value)
                self.assertFalse(self.confirm(0, 11))
                self.assert_no_reward()
                self.assertEqual(self.random_calls, [])
                self.assertEqual(self.quality_reads, [])
        for replacement in (None, self.record([4])):
            self.setUp()
            self.n['tdPets'][0] = replacement
            self.assertFalse(self.confirm(0, 11))
            self.assert_no_reward()
            self.assertEqual(self.quality_reads, [])

    def test_inactive_defeated_finished_disconnected_and_ended_match_fail_without_reward(self):
        for state in ('active', 'defeated', 'finished', 'left', 'over'):
            with self.subTest(state=state):
                self.setUp()
                if state == 'active': self.active[0] = False
                elif state == 'defeated': self.defeated[0] = True
                elif state == 'finished': self.finished[0] = True
                elif state == 'left': self.n['tdPetPlayerLeft'][0] = True
                else: self.game_over = True
                self.assertFalse(self.confirm(0, 11))
                self.assert_no_reward()
                self.assertEqual(self.quality_reads, [])
                self.assertEqual(self.random_calls, [])

    def test_material_overflow_and_invalid_balances_preserve_record_without_draw(self):
        for name in ('tdPetRerollStones', 'tdPetSlotStones'):
            for value in (-1, self.n['TD_PET_MATERIAL_LIMIT']):
                with self.subTest(material=name, value=value):
                    self.setUp()
                    self.n[name][0] = value
                    self.assertFalse(self.confirm(0, 11))
                    self.assertEqual(self.n[name][0], value)
                    other = 'tdPetSlotStones' if name == 'tdPetRerollStones' else 'tdPetRerollStones'
                    self.assertEqual(self.n[other][0], 0)
                    self.assertIs(self.n['tdPets'][0], self.pet)
                    self.assertFalse(self.pet.released)
                    self.assertEqual(self.quality_reads, [])
                    self.assertEqual(self.random_calls, [])

    def test_invalid_lane_nonce_or_cancelled_ticket_never_rewards(self):
        for lane, nonce in ((-1, 11), (4, 11), (0, 0), (0, -1), (1, 11)):
            self.assertFalse(self.confirm(lane, nonce))
            self.assert_no_reward()
        self.n['tdPetCancelRelease'](0)
        self.assertFalse(self.confirm(0, 11))
        self.assert_no_reward()
        self.assertEqual(self.random_calls, [])

    def test_release_and_confirmation_tooltips_match_current_quality_rule(self):
        objects = source('TDPetObjectGen')
        self.assertEqual(objects.count('紫色精灵必得1开栏石'), 2)
        self.assertEqual(objects.count('其他品质有2%概率获得1开栏石'), 2)
        self.assertIn('须先解绑并完成洗练选择，点击后需再次确认', objects)
        self.assertIn('永久失去这只精灵，无法撤销', objects)
        self.assertIn('捕获球和已用材料不返还', objects)
        release = function_body(source('TDPetState'), 'tdPetConfirmRelease')[1]
        self.assertLess(release.index('pet.quality()'), release.index('tdPetDiscardOwned'))
        self.assertLess(release.index('tdPetDiscardOwned'), release.index('tdPetRerollStones[lane] += 1'))
        self.assertIn('if not extra\n\textra = tdPetReleaseGetsSlotStone(GetRandomInt(1, 100))', release)
        self.assertEqual(release.count('tdPetSlotStones[lane] += 1'), 1)


if __name__ == '__main__':
    unittest.main()
