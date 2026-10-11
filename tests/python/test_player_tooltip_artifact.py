"""Negative tests for real packed tooltip/numeric-field verification."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from VerifyPlayerTooltipArtifact import validate


class PlayerTooltipArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mpq = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        cls.a = ability_objects(mpq.extract('war3map.w3a'))
        cls.u = unit_objects(mpq.extract('war3map.w3u'))
        cls.i = unit_objects(mpq.extract('war3map.w3t'))

    def check_bad(self, uid, level, edit, reason):
        a = deepcopy(self.a)
        fields = a[uid][1]
        text = fields['aub1', level, 0][1]
        fields['aub1', level, 0] = 3, edit(text)
        with self.assertRaisesRegex(ValueError, reason):
            validate(a, self.u, self.i)

    def test_all_packaged_tooltips_match_rules(self):
        self.assertGreater(validate(self.a, self.u, self.i), 900)

    def test_rejects_fixed_poison_text_at_last_control_level(self):
        self.check_bad('A106', 61, lambda s: s.replace('35.2%', '22%'), 'A106/61')

    def test_rejects_lost_evolved_bash_probability(self):
        self.check_bad('A113', 61, lambda s: s.replace('26.4%', '22%'), 'A113/61')

    def test_rejects_stale_cooldown_at_last_equipment_level(self):
        self.check_bad('A131', 41, lambda s: s.replace('7.2秒', '12秒'), 'A131/41')

    def test_rejects_float_truncation_pet_slow(self):
        self.check_bad('s016', 1, lambda s: s.replace('20%', '19%'), 's016')

    def test_rejects_charge_current_attack_instead_of_base(self):
        self.check_bad('s030', 1, lambda s: s.replace('基础攻击', '攻击'), 's030')

    def test_rejects_execution_exclusive_threshold(self):
        self.check_bad('s020', 1, lambda s: s.replace('不高于30%', '低于30%'), 's020')

    def test_rejects_missing_cultivation_risk(self):
        for phrase in ('不退石', '永久删除', '2%', '先召回'):
            with self.subTest(phrase=phrase):
                self.check_bad('Pc06', 1, lambda s, p=phrase: s.replace(p, ''), 'cultivation risk')

    def test_rejects_missing_required_action(self):
        a = deepcopy(self.a)
        del a['Pcap']
        with self.assertRaisesRegex(ValueError, 'Missing required action Pcap'):
            validate(a, self.u, self.i)

    def test_rejects_wrong_base_damage_die(self):
        units = deepcopy(self.u)
        units['uO6B']['utub'] = units['uO6B']['utub'].replace('186至197', '185至197')
        with self.assertRaisesRegex(ValueError, 'uO6B: base/die mismatch'):
            validate(self.a, units, self.i)


if __name__ == '__main__':
    unittest.main()
