"""Scoped boss scale contract; does not prove perceived size in Warcraft."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BossVisualScaleSourceTests(unittest.TestCase):
    def test_only_leoric_is_five_times_larger(self):
        source = (ROOT / 'wurst/TDWaves.wurst').read_text()
        expected = {8: ('RiftwindHunter', 7.75), 16: ('Leoric', 6.5),
                    24: ('EclipseSpellweaver', 8.0), 32: ('UncrownedAbyssKing', 7.0)}
        for wave, (model, scale) in expected.items():
            block = source.split(f'new UnitDefinition(TD_WAVE_{wave}_BOSS_UNIT_ID,', 1)[1]
            block = block.split('new UnitDefinition(', 1)[0].split('\n\n', 1)[0]
            with self.subTest(wave=wave):
                self.assertIn(f'..setModelFile("war3mapImported\\\\{model}.mdx")', block)
                self.assertEqual(float(re.search(r'\.\.setScalingValue\(([^)]+)\)', block)[1]), scale)
                self.assertNotIn('setCollisionSize', block)
        self.assertEqual(6.5, 1.3 * 5)


if __name__ == '__main__':
    unittest.main()
