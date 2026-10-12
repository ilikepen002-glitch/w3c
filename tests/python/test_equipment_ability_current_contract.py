"""Synthetic object-field tests, preserving every current equipment assertion."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from VerifyEquipmentAbilityArtifact import verify_current_equipment_abilities


def fixture():
    objects = {}
    for rawcode, parent, levels, field, kind, value in (
        ('A129', 'AIsx', 120, 'Isx1', 2, lambda level: level / 100),
        ('A128', 'AIat', 128, 'Iatt', 0, lambda level: level),
        ('A134', 'AId1', 30, 'Idef', 0, lambda level: -level),
    ):
        fields = {('aite', 0, 0): (0, 1), ('alev', 0, 0): (0, levels)}
        fields.update({(field, level, 1): (kind, value(level)) for level in range(1, levels + 1)})
        objects[rawcode] = parent, fields
    fields = {('alev', 0, 0): (0, 41)}
    for level in range(1, 42):
        fields['acdn', level, 0] = 2, 12 * (1 - (level - 1) / 100)
        fields['abuf', level, 0] = 3, 'Bblo'
    objects['A131'] = 'Ablo', fields
    return objects


class EquipmentAbilityContractTests(unittest.TestCase):
    def test_complete_current_objects_without_retired_passives_pass(self):
        verify_current_equipment_abilities(fixture())

    def test_engine_implementation_code_is_not_an_inheritable_parent(self):
        objects = fixture()
        objects['A129'] = 'AIas', objects['A129'][1]
        with self.assertRaisesRegex(ValueError, 'A129: parent'):
            verify_current_equipment_abilities(objects)

    def test_each_last_sync_level_is_still_checked(self):
        for rawcode, field, level in (('A129', 'Isx1', 120), ('A128', 'Iatt', 128), ('A134', 'Idef', 30)):
            with self.subTest(rawcode=rawcode):
                objects = fixture()
                kind, value = objects[rawcode][1][field, level, 1]
                objects[rawcode][1][field, level, 1] = kind, value + 1
                with self.assertRaisesRegex(ValueError, rawcode + ': level ' + str(level)):
                    verify_current_equipment_abilities(objects)

    def test_native_bloodlust_parent_buff_and_last_cooldown_remain_checked(self):
        for mutation, reason in ((('parent', 0), 'native parent'),
                                 (('abuf', 41), 'native buff missing at 41'),
                                 (('acdn', 41), 'incorrect cooldown at level 41')):
            with self.subTest(mutation=mutation):
                objects = fixture()
                if mutation[0] == 'parent':
                    objects['A131'] = 'Aslo', objects['A131'][1]
                else:
                    field, level = mutation
                    objects['A131'][1][field, level, 0] = (3, '') if field == 'abuf' else (2, 12.0)
                with self.assertRaisesRegex(ValueError, reason):
                    verify_current_equipment_abilities(objects)

    def test_every_retired_fixed_quality_passive_is_rejected(self):
        for index in range(120, 128):
            objects = fixture()
            objects[f'A{index}'] = deepcopy(objects['A128'])
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'retired fixed-quality'):
                verify_current_equipment_abilities(objects)


if __name__ == '__main__':
    unittest.main()
