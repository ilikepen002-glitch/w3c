"""Synthetic closed-delta mutants. This is validator evidence, not a map build."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerEvolutionDelta import CHANNEL_ORDERS, expected_abilities, validate_ability_delta


class EvolutionDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = ability_objects(Mpq((ROOT / 'ExampleMap.w3x').read_bytes()).extract('war3map.w3a'))
        compact = 'AeEC' in cls.before or 'A109' in cls.before
        if 'AeEC' in cls.before:
            cls.before.pop('AeEC')
            status = cls.before['AeEV'][1]
            for key in list(status):
                if key[1] == 4: status.pop(key)
            status['alev', 0, 0] = (0, 3)
        else:
            cls.before.pop('A109', None)
        # Construct a labelled synthetic predecessor from whichever map fixture
        # is checked out; compact one allocation before sale, not game output.
        for parent, fields in cls.before.values():
            if compact and parent == 'ANcl':
                for key, (kind, order) in list(fields.items()):
                    if key[0] == 'Ncl6':
                        fields[key] = kind, CHANNEL_ORDERS[CHANNEL_ORDERS.index(order) - 1]
        cls.after = expected_abilities(cls.before)

    def reject(self, code, key, value, reason='Unrelated/incorrect evolution field'):
        current = deepcopy(self.after)
        current[code][1][key] = value
        with self.assertRaisesRegex(ValueError, reason): validate_ability_delta(current, self.before)

    def test_exact_synthetic_delta(self): validate_ability_delta(self.after, self.before)
    def test_reject_numeric_branch_change(self): self.reject('A112', ('Ocr2', 1, 2), (2, 9.0))
    def test_reject_chooser_cooldown(self): self.reject('AeEC', ('acdn', 1, 0), (2, 1.0))
    def test_reject_chooser_second_level(self):
        self.reject('AeEC', ('Ncl6', 2, 6), (3, 'absorb'), 'identity/schema')
    def test_reject_status_combat_effect(self): self.reject('AeEV', ('Ocr1', 4, 1), (2, 50.0))
    def test_reject_order_shift_waiver(self): self.reject('Pcap', ('Ncl6', 1, 6), (3, 'absorb'))
    def test_reject_insertion_not_at_first_allocation(self):
        self.reject('AeEC', ('Ncl6', 1, 6), (3, 'acidbomb'))
        before = deepcopy(self.before)
        before['A133'][1]['Ncl6', 1, 6] = (3, 'acidbomb')
        with self.assertRaisesRegex(ValueError, 'first Channel allocation'):
            validate_ability_delta(self.after, before)
    def test_reject_unrelated_direction_choice(self):
        # Existing pet object must retain all fields except the exact +1 order.
        self.reject('Pdep', ('ahky', 0, 0), (3, 'X'))
    def test_reject_extra_action(self):
        current = deepcopy(self.after); current['Zzzz'] = current['AeEC']
        with self.assertRaisesRegex(ValueError, 'catalog delta'): validate_ability_delta(current, self.before)


if __name__ == '__main__': unittest.main(verbosity=2)
