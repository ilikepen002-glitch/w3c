"""Current source contract; no claim of compiled-map or native execution."""
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
from VerifyPetUIArtifact import _integer_expression

BASE = 'c597eaa8a5089d9eed8fd7d186ac07d3e89f8d2e'
RUNTIME = 'wurst/pets/TDPetRuntime.wurst'


class CaptureChance65SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = (ROOT / RUNTIME).read_text()
        cls.condition = re.search(r'^\s*if (not guaranteed and GetRandomInt\(1, 100\) > \d+)$', cls.runtime, re.M)[1]

    def test_actual_source_all_rolls_and_rng_calls_including_boundaries(self):
        for guaranteed in (False, True):
            for roll in range(1, 101):
                calls = []
                def random(low, high):
                    calls.append((low, high))
                    return roll
                failed = _integer_expression(self.condition, {'guaranteed': guaranteed}, {'GetRandomInt': random})
                self.assertEqual(failed, not guaranteed and roll > 65, (guaranteed, roll))
                self.assertEqual(calls, [] if guaranteed else [(1, 100)])
        # Explicit required boundary labels, in addition to the exhaustive matrix.
        for roll, success in ((1, True), (65, True), (66, False), (100, False)):
            self.assertEqual(not _integer_expression(self.condition, {'guaranteed': False}, {'GetRandomInt': lambda a, b: roll}), success)

    def test_tutorial_guarantee_has_original_four_states(self):
        expression = re.search(r'^\s*let guaranteed = (.+)$', self.runtime, re.M)[1]
        expression = expression.replace('wild.tutorial', 'tutorial')
        for tutorial in (False, True):
            for used in (False, True):
                self.assertEqual(_integer_expression(expression, {'tutorial': tutorial, 'tdPetTutorialUsed': {0: used}, 'lane': 0}), tutorial and not used)

    def test_runtime_diff_is_only_threshold_preserving_spend_rng_and_result_order(self):
        before = subprocess.check_output(['git', 'show', f'{BASE}:{RUNTIME}'], cwd=ROOT, text=True)
        self.assertEqual(before.count('GetRandomInt(1, 100) > 60'), 1)
        # Deployment has an independent lifecycle contract; keep capture itself closed.
        def capture(source):
            return source.split('function tdPetHandleCapture()', 1)[1].split('// A successful roll owns one reward:', 1)[0]
        self.assertEqual(capture(self.runtime), capture(before).replace('GetRandomInt(1, 100) > 60', 'GetRandomInt(1, 100) > 65'))

    def test_chance_helper_and_player_tooltip(self):
        evaluator = SourceScalarEvaluator(read_sources(ROOT))
        for life, maximum in ((100., 100.), (0., 100.), (-5., 0.), (1., 100.)):
            self.assertEqual(evaluator.call('tdPetCaptureChance', [life, maximum]), .65)
        data = (ROOT / 'wurst/pets/TDPetData.wurst').read_text()
        self.assertIn('成功率65%；首只教学精灵首次投普通球必成', data)
        self.assertIn('/60；收藏已满不扣球。野生精灵出现180秒后消失。', data)
        self.assertNotIn('成功率60%', data)


if __name__ == '__main__':
    unittest.main()
