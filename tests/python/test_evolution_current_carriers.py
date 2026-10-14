"""Real current-map carriers plus precise field mutants; no game-input claim."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from python_check_inputs import candidate_map

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifySlowAbilityArtifact import validate_slow_abilities
from VerifyEvolutionArtifact import validate_tower_aura_carriers, validate_production_script_boundary


class CurrentEvolutionCarriers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.abilities = ability_objects(Mpq(candidate_map().read_bytes()).extract('war3map.w3a'))

    def reject(self, validator, code, key, value):
        changed = self.abilities.copy()
        changed[code] = deepcopy(changed[code])
        kind = changed[code][1][key][0]
        changed[code][1][key] = kind, value
        with self.assertRaises(ValueError):
            validator(changed)

    def test_actual_current_source_and_rank_carriers(self):
        validate_slow_abilities(self.abilities)
        validate_tower_aura_carriers(self.abilities)

    def test_all_poison_levels_reject_native_damage_control_duration_buff_or_target_change(self):
        for code in ('A106', 'AhDP', 'A114'):
            for level in range(1, 62):
                for field, column, value in [('Spo1', 1, 1.0), ('Spo2', 2, .22),
                                              ('Spo3', 3, .22), ('adur', 0, 1.0),
                                              ('ahdu', 0, 2.0), ('abuf', 0, ''),
                                              ('atar', 0, 'self')]:
                    with self.subTest(code=code, level=level, field=field):
                        self.reject(validate_slow_abilities, code, (field, level, column), value)

    def test_all_bash_levels_reject_reactivated_native_effect(self):
        for code in ('A104', 'A113'):
            for level in range(1, 62):
                for field, column, value in [('Hbh1', 1, 22.0), ('Hbh2', 2, 1.45),
                                              ('Hbh3', 3, 20.0), ('adur', 0, 2.0),
                                              ('ahdu', 0, 1.0), ('abuf', 0, 'Bspo'),
                                              ('atar', 0, 'self')]:
                    with self.subTest(code=code, level=level, field=field):
                        self.reject(validate_slow_abilities, code, (field, level, column), value)

    def test_visible_aura_sources_reject_range_double_application(self):
        for code in ('A101', 'A111', 'A105', 'AeCM'):
            bonus = 'Ear1' if self.abilities[code][0] == 'AEar' else 'Cac1'
            for key, value in [((bonus, 1, 1), .18), (('atar', 1, 0), 'friend'),
                               (('abuf', 1, 0), 'BM01'), (('aare', 1, 0), 901.0)]:
                with self.subTest(code=code, key=key):
                    self.reject(validate_tower_aura_carriers, code, key, value)

    def test_each_rank_level_rejects_percentage_target_buff_radius_or_visibility_change(self):
        for code, (parent, fields) in self.abilities.items():
            if '百分比载体' not in fields.get(('anam', 0, 0), (None, ''))[1]:
                continue
            bonus = 'Ear1' if parent == 'AEar' else 'Cac1'
            for level in (1, 2):
                for key, value in [((bonus, level, 1), 1.0), (('atar', level, 0), 'friend'),
                                   (('abuf', level, 0), ''), (('aare', level, 0), 900.0)]:
                    with self.subTest(code=code, key=key):
                        self.reject(validate_tower_aura_carriers, code, key, value)
            self.reject(validate_tower_aura_carriers, code, ('abpy', 0, 0), 1)

    def test_production_native_cooldown_is_allowed_but_each_diagnostic_probe_is_rejected(self):
        validate_production_script_boundary('function new_TDNativeActiveCooldown takes nothing returns nothing\nendfunction')
        for path in (ROOT / 'tests/wurst/runtime').glob('TDNative*Probe.wurst'):
            with self.subTest(probe=path.stem), self.assertRaises(ValueError):
                validate_production_script_boundary('function init_' + path.stem + ' takes nothing returns nothing\nendfunction')


if __name__ == '__main__':
    unittest.main(verbosity=2)
