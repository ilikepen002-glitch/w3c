"""Static/negative fixtures for the ten branch emblems; no new-build claim.

The real-artifact positive remains in test_verify_tower_upgrade_artifact.py.
Here only icon fields of a copied predecessor are set to the expected new
contract, so the new validators can be exercised before the serial build.
"""
from copy import deepcopy
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEquipmentAbilityArtifact import ability_objects
import VerifyTowerUpgradeArtifact as verifier
import VerifySemanticIconArtifact as semantic


class BranchIconSeparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        cls.original_units = unit_objects(cls.map.extract('war3map.w3u'))
        cls.units = deepcopy(cls.original_units)
        cls.abilities = ability_objects(cls.map.extract('war3map.w3a'))
        for family, names in verifier.BRANCH_ICONS.items():
            for branch, name in zip('AB', names):
                for field in ('uico', 'ussi'):
                    cls.units['u' + family + '6' + branch][field] = verifier.NATIVE_ICON_PREFIX + name + '.blp'

    def test_ten_distinct_native_choices_match_source_constants(self):
        source = (ROOT / 'wurst/towers/TDTowerBalanceData.wurst').read_text()
        body = source.split('public function tdTowerIconPathForBranch', 1)[1].split('\npublic function', 1)[0]
        names = re.findall(r'Icons\.bTN(\w+)', body)
        expected = [name[3:] for pair in verifier.BRANCH_ICONS.values() for name in pair]
        self.assertEqual(set(names), set(expected))
        self.assertEqual(len(names), 10)
        self.assertEqual(len(set(names)), 10)
        self.assertIn('return tdTowerIconPath(towerChoice, level)', body)
        self.assertNotIn('SkillIconPath', body)
        for family, names in verifier.BRANCH_ICONS.items():
            for branch, name in zip('AB', names):
                rawcode = 'u' + family + '6' + branch
                self.assertEqual(semantic.BINDINGS['units', rawcode, ('uico', 0, 0)],
                                 verifier.NATIVE_ICON_PREFIX + name + '.blp')

    def test_expected_icon_fixture_changes_only_twenty_unit_fields(self):
        permitted = {(uid, field) for uid in verifier.EVOLUTION_REPLACEMENTS for field in ('uico', 'ussi')}
        for uid, fields in self.original_units.items():
            for field, value in fields.items():
                if (uid, field) not in permitted:
                    self.assertEqual(self.units[uid][field], value)
        verifier.validate_tower_identity(self.units)
        verifier.validate_command_ui(self.units, self.abilities)
        verifier.validate_branch_resources(self.map, self.units, self.abilities)

    def test_each_branch_rejects_co_visible_base_evolved_and_status_icons(self):
        for family in verifier.FAMILIES:
            ids = set(verifier.EXPECTED_TOWERS['u' + family + '15']) | {'AeEV'}
            for branch in 'AB':
                ids.update(verifier.EXPECTED_TOWERS['u' + family + '6' + branch])
                ids.update(verifier.EVOLUTION_REPLACEMENTS['u' + family + '6' + branch].values())
            for aid in ids:
                icon = verifier.field_value(self.abilities, aid, 'aart', default='')
                if not icon:
                    continue
                for branch in 'AB':
                    units = deepcopy(self.units)
                    units['u' + family + '6' + branch]['uico'] = icon
                    with self.subTest(family=family, branch=branch, ability=aid):
                        with self.assertRaisesRegex(ValueError, 'reuses co-visible'):
                            verifier.validate_command_ui(units, self.abilities)

    def test_each_pair_rejects_same_emblem(self):
        for family in verifier.FAMILIES:
            units = deepcopy(self.units)
            units['u' + family + '6B']['uico'] = units['u' + family + '6A']['uico']
            with self.subTest(family=family), self.assertRaisesRegex(ValueError, 'share icon'):
                verifier.validate_command_ui(units, self.abilities)

    def test_native_normal_and_disabled_shadowing_is_rejected(self):
        class ShadowOne:
            def __init__(self, path): self.path = path
            def has(inner, path): return path == inner.path or self.map.has(path)
            def extract(inner, path): return self.map.extract(path)
        for family, names in verifier.BRANCH_ICONS.items():
            for name in names:
                normal = verifier.NATIVE_ICON_PREFIX + name + '.blp'
                disabled = 'ReplaceableTextures\\CommandButtonsDisabled\\DIS' + name + '.blp'
                for path in (normal, disabled):
                    with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'shadowed by import'):
                        verifier.validate_branch_resources(ShadowOne(path), self.units, self.abilities)


if __name__ == '__main__':
    unittest.main()
