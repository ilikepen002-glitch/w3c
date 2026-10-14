"""Synthetic chooser/card mutations using copied predecessor objects.
This exercises validators only; it is not a new-map or Warcraft PASS.
"""
from copy import deepcopy
from pathlib import Path
import sys, unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyEvolutionArtifact import validate_evolution_action_commands
from VerifyTowerEvolutionDelta import CHANNEL_ORDERS

class EvolutionCommandCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        original = ability_objects(Mpq((ROOT / 'ExampleMap.w3x').read_bytes()).extract('war3map.w3a'))
        cls.abilities = deepcopy(original)
        parent, fields = deepcopy(original['Pdep'])
        for field, value in [('abpx',3), ('abpy',2), ('ahky','R')]:
            fields[field,0,0] = (0 if isinstance(value,int) else 3, value)
        # A predecessor fixture may have either wage or evolution allocation.
        # Keep this synthetic action distinct without modifying real objects.
        occupied = {original[code][1]['Ncl6',1,6][1] for code in ('A133', 'Pdep')}
        fields['Ncl6',1,6] = (3, next(order for order in CHANNEL_ORDERS if order not in occupied))
        cls.abilities['AeEC'] = parent, fields
    def test_synthetic_ten_terminal_selection_cards(self):
        validate_evolution_action_commands(self.abilities)
    def mutate(self, field, value, reason, level=0, column=0):
        abilities = deepcopy(self.abilities)
        old = abilities['AeEC'][1][field,level,column]
        abilities['AeEC'][1][field,level,column] = old[0], value
        with self.assertRaisesRegex(ValueError, reason): validate_evolution_action_commands(abilities)
    def test_reject_residual_second_level_channel_fields(self):
        abilities = deepcopy(self.abilities)
        abilities['AeEC'][1]['Ncl6',2,6] = (3, 'ancestralspirit')
        with self.assertRaisesRegex(ValueError, 'residual fields'):
            validate_evolution_action_commands(abilities)
    def test_reject_combat_hotkey_collision(self):
        self.mutate('ahky', 'E', 'conflict with E')
    def test_reject_sale_command_cell_collision(self):
        self.mutate('abpy', 1, 'command cells overlap')
    def test_reject_channel_order_collision(self):
        for code in ('A133', 'Pdep'):
            with self.subTest(command=code):
                self.mutate('Ncl6', self.abilities[code][1]['Ncl6',1,6][1], 'distinct native Channel order', 1, 6)
    def test_reject_other_tower_targeting(self):
        self.mutate('Ncl2', 1, 'own-tower instant', 1, 2)

if __name__ == '__main__': unittest.main(verbosity=2)
