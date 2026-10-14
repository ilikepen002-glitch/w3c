"""Narrow source checks; compiled replay is VerifyPetAttackArtifact after map build."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources


class PetQualityBalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = read_sources()
        cls.rules = SourceScalarEvaluator(cls.sources)

    def test_approved_powers_and_unchanged_other_skills(self):
        expected = {0: (40., 80., 120., 160.), 1: (.06, .12, .18, .24),
                    2: (.06, .12, .20, .30), 3: (.06, .12, .18, .24),
                    5: (.03, .04, .05, .06), 46: (.20, .30, .40, .50),
                    48: (.25, .40, .55, .70)}
        for skill, powers in expected.items():
            for quality, power in enumerate(powers, 1):
                self.assertAlmostEqual(self.rules.call('tdPetSkillPower', [skill, quality]), power)

    def test_reduce_keeps_five_stacks_and_quality_expiry(self):
        for quality in range(1, 5):
            expiry = self.rules.call('tdPetReduceDuration', [quality])
            self.assertEqual(expiry, 1. + .5 * quality)
            for hit in range(1, 7):
                self.assertEqual(self.rules.call('tdPetReduceStacks', [hit - 1, expiry, 0.]), min(hit, 5))
            self.assertEqual(self.rules.call('tdPetReduceStacks', [5, expiry, expiry]), 1)

    def test_runtime_and_player_text_use_same_quality_rule(self):
        runtime = self.sources['pets/TDPetAttackState.wurst']
        self.assertIn('entry.stacks * tdPetSkillPower(5, slowQuality) * bossFactor', runtime)
        self.assertIn('tdIsBossUnitTypeId(GetUnitTypeId(target)) ? 0.5 : 1.0', runtime)
        self.assertIn('TD_AURA_PET_REDUCE, 1,', runtime)
        rules = self.sources['pets/TDPetRules.wurst']
        self.assertNotIn('每层6%，最多5层30%', rules)
        self.assertIn('(power * 500.0 + 0.5).toInt().toString()', rules)
        combat = self.sources['pets/TDPetCombat.wurst']
        self.assertIn('abilityId == TD_PET_ATTACK_BONUS_ID ? 512 : 150', combat)
        self.assertIn('speed += pet.skillPower(2)', combat)
        self.assertIn('speed += pet.buffPower', combat)

    def test_capture_and_skill_count_distribution_remain_unchanged(self):
        counts = [self.rules.call('tdPetSkillCountForRoll', [roll]) for roll in range(1, 101)]
        self.assertEqual([counts.count(n) for n in (2, 3, 4)], [55, 35, 10])
        self.assertEqual(self.rules.call('tdPetCaptureChance', [100., 100.]), .65)


if __name__ == '__main__':
    unittest.main()
