"""Source-only wages regressions; packed transaction verification has its own gate."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources, uncomment

NODES = {1:60, 4:90, 7:120, 10:150, 13:180, 16:210, 19:240, 22:270, 25:300, 28:330, 31:360}

class WaveProgressWages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = read_sources()
        cls.evaluator = SourceScalarEvaluator(cls.sources)

    def test_exact_table_invalid_values_and_totals(self):
        for wave in [-2147483648, *range(-3, 70), 2147483647]:
            self.assertEqual(self.evaluator.call('tdWaveProgressWage', [wave]), NODES.get(wave, 0))
        self.assertEqual([sum(v for w,v in NODES.items() if w <= chapter) for chapter in (8,16,24,32)], [270,810,1320,2310])

    def test_settlement_claims_before_side_effects_and_uses_original_wave(self):
        body = self.evaluator.body('tdHandleWaveFinished')
        claims = [body.index(s) for s in ('tdIsWaveResolved(playerId, wave)', 'tdMarkWaveResolved(playerId, wave)', 'tdPetCreditWave(playerId, wave)', 'tdGainGold(playerId, tdWaveReward(wave) + wage)')]
        self.assertEqual(claims, sorted(claims))
        self.assertEqual(body.count('tdGainGold('), 1)
        self.assertIn('let wage = tdWaveProgressWage(wave)', body)
        for forbidden in ('tdGetGlobalWave', 'getElapsedGameTime', 'doAfter(', 'doPeriodically(', 'TriggerSleepAction'):
            self.assertNotIn(forbidden, body)
        for guard in ('tdIsLanePlayer(playerId)', 'wave < 1', 'wave > tdWaveCount()', 'tdIsGameOver()', 'tdIsLaneActive(playerId)', 'tdIsLaneDefeated(playerId)', 'tdIsLaneFinished(playerId)', 'tdPetPlayerHasLeft(playerId)'):
            self.assertIn(guard, body)
        for path, text in self.sources.items():
            if path not in ('TDWaves.wurst', 'TDGame.wurst'):
                self.assertNotIn('tdWaveProgressWage(', uncomment(text), path)

    def test_old_random_spell_button_watcher_and_diagnostic_orders_are_retired(self):
        for path, text in self.sources.items():
            source = uncomment(text)
            self.assertNotRegex(source, r'\b(?:TD_FARMER_WAGE_ABILITY_ID|td\w*FarmerWage\w*)\b', path)
            self.assertNotRegex(source, r'[\'\"]A109[\'\"]', path)
        probe = (ROOT/'tests/wurst/runtime/TDNativeNormalPlayProbe.wurst').read_text()
        for old in ('normalWageTick', 'normalWagePending', 'OrderId("absorb")', 'tdFarmerWageCooldown'):
            self.assertNotIn(old, probe)
        self.assertIn('tdWaveProgressWage(original)', probe)

    def test_original_clear_rewards_remain_explicit(self):
        expected = [100, 100, 120, 180, 140, 150, 160, 340, 180, 240, 280, 240, 280, 340, 360, 580, 500, 700, 900, 920, 750, 350, 750, 1200, 100, 600, 900, 1200, 200, 350, 700, 1500]
        actual = [self.evaluator.call('tdWaveReward',[w]) for w in range(1,33)]
        # Checked against the immutable pre-migration source, not wage formula.
        self.assertEqual(actual, expected)

if __name__ == '__main__': unittest.main()
