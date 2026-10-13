"""Wild-only visual sizing contract; this does not prove in-game appearance."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PetWildVisibilitySourceTests(unittest.TestCase):
    def test_five_times_wild_size_preserves_other_displays_and_pathing(self):
        source = (ROOT / 'wurst/pets/TDPetObjectGen.wurst').read_text()
        wild = source.split('new UnitDefinition(tdPetWildUnitId(wave, species)', 1)[1].split('new ItemDefinition(', 1)[0]
        self.assertIn('..setScalingValue(4.25)', wild)
        self.assertEqual(4.25, 0.85 * 5)
        self.assertIn('..setNormalAbilities("Aeth")', wild)
        self.assertIn('..setCollisionSize(0.0)', wild)
        attached = source.split('new UnitDefinition(tdPetVisualUnitId(species)', 1)[1].split('\n', 1)[0]
        self.assertIn('..setScalingValue(0.45)', attached)
        display = source.split('function displayUnit(', 1)[1].split('\nfunction ', 1)[0]
        self.assertIn('..setScalingValue(0.65)', display)
        runtime = (ROOT / 'wurst/pets/TDPetWild.wurst').read_text()
        self.assertIn('creature.setPathing(false)', runtime)
        self.assertIn('SetUnitInvulnerable(creature, true)', runtime)


if __name__ == '__main__':
    unittest.main()
