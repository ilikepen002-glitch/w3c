"""Raw artifact positive and explicitly corrected in-memory negative fixtures."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import re
import sys
import struct
import subprocess
import unittest
from python_check_inputs import candidate_map
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects
from VerifyUnitParentsArtifact import unit_parents
import VerifyBuilderConstructionArtifact as verifier
from VerifySemanticIconArtifact import Field, load_objects


class ArtifactFixture:
    map_path = staticmethod(lambda: ROOT / 'ExampleMap.w3x')
    @classmethod
    def setUpClass(cls):
        artifact = Mpq(cls.map_path().read_bytes())
        data = artifact.extract('war3map.w3u')
        cls.units, cls.parents = unit_objects(data), unit_parents(data)
        cls.script = artifact.extract('war3map.j').decode('utf-8')


class BuilderConstructionActualArtifactTests(ArtifactFixture, unittest.TestCase):
    map_path = staticmethod(candidate_map)
    def test_actual_native_builder_and_all_towers(self):
        verifier.validate_builder_objects(self.units, self.parents)
        verifier.validate_construction_jass(self.script)


class BuilderConstructionSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = [(ROOT / path).read_text() for path in
                      ('wurst/towers/TDTowerCatalogData.wurst', 'wurst/towers/TDTowerCommonData.wurst',
                       'wurst/towers/TDTowerObjectGen.wurst', 'wurst/towers/TDTowerRuntime.wurst')]

    def test_actual_source_contract(self):
        verifier.validate_builder_source(*self.source)

    def test_source_rejects_wrong_race_ability_default_repair_or_zero_build_time(self):
        for index, old, new, reason in [(0, "'AUbu'", "'AHbu'", 'AUbu'),
                                        (1, 'return Race.Undead', 'return Race.Human', 'Undead'),
                                        (2, 'setDefaultActiveAbility("")', 'setDefaultActiveAbility("Ahrp")', 'missing'),
                                        (2, 'setBuildTime(2 + level)', 'setBuildTime(0)', '2\\+level')]:
            source = self.source.copy()
            source[index] = source[index].replace(old, new)
            with self.subTest(case=old), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_builder_source(*source)


class BuilderConstructionNegativeTests(ArtifactFixture, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.units = deepcopy(cls.units)
        worker = cls.units['uF01']
        worker['urac'], worker['udaa'] = 'undead', ''
        worker['uabi'] = worker['uabi'].replace('AHbu', 'AUbu').replace(',Prpr', '')

    def test_corrected_fixture_is_valid(self):
        verifier.validate_builder_objects(self.units, self.parents)
        verifier.validate_construction_jass(self.script)

    def test_rejects_wrong_worker_race_build_or_repair(self):
        abilities = self.units['uF01']['uabi']
        for field, value, reason in [('urac', 'human', 'race must be undead'),
                                     ('uabi', abilities.replace('AUbu', 'AHbu'), 'exactly one AUbu'),
                                     ('uabi', abilities + ',Prpr', 'must not attach'),
                                     ('uabi', abilities + ',Ahrp', 'must not attach'),
                                     ('uabi', abilities + ',AHbu', 'must not attach'),
                                     ('udaa', 'Ahrp', 'clear default repair')]:
            units = deepcopy(self.units)
            units['uF01'][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_builder_objects(units, self.parents)

    def test_rejects_changed_parent_or_model(self):
        parents = self.parents.copy()
        parents['uF01'] = 'uaco'
        with self.assertRaisesRegex(ValueError, 'hpea parent/model'):
            verifier.validate_builder_objects(self.units, parents)
        units = deepcopy(self.units)
        units['uF01']['umdl'] = 'Units\\Undead\\Acolyte\\Acolyte.mdx'
        with self.assertRaisesRegex(ValueError, 'inherited peasant model'):
            verifier.validate_builder_objects(units, self.parents)

    def test_all_35_towers_reject_zero_time_wrong_race_food_path_or_upgrade(self):
        for uid in verifier.TOWER_IDS:
            for field, value, reason in [('ubld', 0, 'build time'), ('urac', 'undead', 'tower race'),
                                         ('ufoo', 0, 'population'), ('upat', '', 'pathing'), ('uupt', 'uF01', 'upgrade chain')]:
                units = deepcopy(self.units)
                units[uid][field] = value
                with self.subTest(unit=uid, field=field), self.assertRaisesRegex(ValueError, re.escape(uid) + '.*' + reason):
                    verifier.validate_builder_objects(units, self.parents)

    def test_each_native_hook_is_required(self):
        for event in ('CONSTRUCT_START', 'CONSTRUCT_FINISH', 'CONSTRUCT_CANCEL', 'UPGRADE_START', 'UPGRADE_FINISH', 'UPGRADE_CANCEL'):
            script = self.script.replace('EVENT_PLAYER_UNIT_' + event, 'REMOVED_EVENT')
            with self.subTest(event=event), self.assertRaisesRegex(ValueError, event):
                verifier.validate_construction_jass(script)


class BuilderConstructionDeltaNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Immutable formal predecessor, never the current root artifact.
        data = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                                        'a1293716c6b06b31e4b1cb9625efe3d9db3da572:ExampleMap.w3x'])
        cls.before = load_objects(Mpq(data))
        cls.after = deepcopy(cls.before)
        worker = cls.after['units']['uF01']
        marker = worker.fields[('uabi', 0, 0)].raw[-4:]
        fields = {}
        def string_field(key, value):
            return Field((key, 0, 0), 3, value, key.encode() + struct.pack('<I', 3) + value.encode() + b'\0' + marker)
        for key, value in worker.fields.items():
            if key == ('uabi', 0, 0):
                for code, text in [('urac', 'undead'), ('udaa', ''), ('uabi', verifier.A_WORKER_ABILITIES)]:
                    fields[(code, 0, 0)] = string_field(code, text)
            else:
                fields[key] = value
        worker.fields = fields

    def test_corrected_A_only_fixture_passes(self):
        verifier.validate_worker_only_delta(self.after, self.before)

    def test_wrong_race_repair_attachment_or_field_encoding_is_rejected(self):
        for key, change in [('urac', 'human'), ('udaa', 'Ahrp'), ('uabi', verifier.A_WORKER_ABILITIES + ',Prpr')]:
            after = deepcopy(self.after)
            field = after['units']['uF01'].fields[(key, 0, 0)]
            after['units']['uF01'].fields[(key, 0, 0)] = replace(field, value=change)
            with self.subTest(field=key), self.assertRaisesRegex(ValueError, 'value/encoding'):
                verifier.validate_worker_only_delta(after, self.before)
        after = deepcopy(self.after)
        key = ('urac', 0, 0)
        field = after['units']['uF01'].fields[key]
        after['units']['uF01'].fields[key] = replace(field, raw=field.raw[:-4] + b'XXXX')
        with self.assertRaisesRegex(ValueError, 'value/encoding'):
            verifier.validate_worker_only_delta(after, self.before)

    def test_any_other_object_change_or_worker_field_order_is_rejected(self):
        for kind, code in [('units', 'uA11'), ('abilities', 'A131'), ('items', 'Ibal')]:
            after = deepcopy(self.after)
            obj = after[kind][code]
            key = next(iter(obj.fields))
            obj.fields[key] = replace(obj.fields[key], raw=obj.fields[key].raw + b'x')
            with self.subTest(object=code), self.assertRaisesRegex(ValueError, 'unrelated object'):
                verifier.validate_worker_only_delta(after, self.before)
        after = deepcopy(self.after)
        after['units']['uF01'].fields = dict(reversed(list(after['units']['uF01'].fields.items())))
        with self.assertRaisesRegex(ValueError, 'field set/order'):
            verifier.validate_worker_only_delta(after, self.before)

    def test_object_addition_or_worker_parent_change_is_rejected(self):
        after = deepcopy(self.after)
        after['units']['Xbad'] = deepcopy(after['units']['uF01'])
        with self.assertRaisesRegex(ValueError, 'object set/order'):
            verifier.validate_worker_only_delta(after, self.before)
        after = deepcopy(self.after)
        after['units']['uF01'].identity = b'uaco' + b'uF01'
        with self.assertRaisesRegex(ValueError, 'parent/table'):
            verifier.validate_worker_only_delta(after, self.before)


if __name__ == '__main__':
    unittest.main()
