"""Native gameplay constants only; never replace native inventory events."""
import unittest
from pathlib import Path
from VerifyInventoryRangeArtifact import EXPECTED
from GenerateTowerTerrainMask import Mpq

ROOT = Path(__file__).resolve().parents[2]


class InventoryRangeSourceTests(unittest.TestCase):
    def test_only_three_native_inventory_constants_are_overridden(self):
        self.assertEqual((ROOT / 'imports/war3mapMisc.txt').read_bytes(), EXPECTED)
        self.assertFalse((ROOT / 'imports/war3mapImported/war3mapMisc.txt').exists())
        original = Mpq((ROOT / 'maps/ExampleMap.source.w3x').read_bytes())
        self.assertFalse(original.has('war3mapMisc.txt'), 'Merge existing constants rather than overwrite')

    def test_farmer_and_tower_inventory_capacities_and_native_flags_unchanged(self):
        code = (ROOT / 'wurst/items/TDItemObjectGen.wurst').read_text()
        start = code.index('function tdGenerateInventoryAbility(')
        body = code[start:code.index('\nfunction ', start + 1)]
        self.assertNotIn('CastRange', body)
        self.assertIn('..setCanDropItems(1, true)', body)
        self.assertIn('..setCanGetItems(1, true)', body)
        self.assertIn('..setCanUseItems(1, canUseItems)', body)
        self.assertIn('tdGenerateInventoryAbility(TD_FARMER_INVENTORY_ABILITY_ID, 6, false)', code)
        self.assertIn('tdGenerateInventoryAbility(TD_TOWER_INVENTORY_ABILITY_ID, 3, false)', code)


if __name__ == '__main__':
    unittest.main()
