"""B current source and corrected local fixtures; raw new-artifact positive separate."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from VerifyUnitParentsArtifact import unit_parents
from VerifyBuilderConstructionArtifact import validate_builder_objects
from VerifySemanticIconArtifact import load_objects
from VerifyPetUIArtifact import verify_farmer_grid, verify_collection_commands
import VerifyBuilderControlArtifact as verifier


def set_field(abilities, code, field, value, level=0, column=0):
    key = (field, level, column)
    kind = abilities[code][1].get(key, (3 if isinstance(value, str) else 0, None))[0]
    abilities[code][1][key] = (kind, value)


class BuilderControlSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [(ROOT / path).read_text() for path in
                       ('wurst/towers/TDTowerCatalogData.wurst', 'wurst/towers/TDTowerCommonData.wurst',
                        'wurst/towers/TDTowerObjectGen.wurst', 'wurst/pets/TDPetData.wurst', 'wurst/pets/TDPetObjectGen.wurst',
                        'wurst/items/TDItemData.wurst', 'wurst/items/TDItemObjectGen.wurst', 'wurst/TDInit.wurst')]

    def test_current_B_source_contract(self):
        verifier.validate_control_sources(*self.sources)

    def test_rejects_blink_repair_old_book_or_wrong_main_button_source(self):
        cases = [(0, "public constant int TD_FARMER_BLINK_ABILITY_ID = 'A108'\n", 'Unused'),
                 (3, "public constant int TD_FARMER_MENU_REPAIR_ABILITY_ID = 'Prpr'\n", 'Unused')]
        for index, added, reason in cases:
            source = self.sources.copy()
            source[index] += added
            with self.subTest(added=added), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_control_sources(*source)
        source = self.sources.copy()
        source[6] = source[6].replace('setSpellList(1, TD_FARMER_CRAFT_ABILITY_ID.toRawCode())',
                                    'setSpellList(1, TD_FARMER_CRAFT_ABILITY_ID.toRawCode() + ",Gupg")')
        with self.assertRaisesRegex(ValueError, 'only A119'):
            verifier.validate_control_sources(*source)
        source = self.sources.copy()
        source[5] = source[5].replace('function tdFarmerGroundUpgradeButtonY() returns int\n\treturn 1',
                                    'function tdFarmerGroundUpgradeButtonY() returns int\n\treturn 0')
        with self.assertRaisesRegex(ValueError, 'position/key'):
            verifier.validate_control_sources(*source)


class BuilderControlNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        cls.abilities = ability_objects(artifact.extract('war3map.w3a'))
        cls.units = unit_objects(artifact.extract('war3map.w3u'))
        # Local desired-interface fixture only, never used by raw positives.
        for code in verifier.B_REMOVED + verifier.PREDECESSOR_REMOVED:
            cls.abilities.pop(code, None)
        cls.units['uF01']['uabi'] = 'AUbu,A109,A117,Geqb,Gupg,Pcap,Pcol,Pdep'
        set_field(cls.abilities, 'Geqb', 'spb1', 'A119', 1, 1)
        set_field(cls.abilities, 'Geqb', 'spb3', 1, 1, 3)
        set_field(cls.abilities, 'Geqb', 'spb4', 1, 1, 4)
        set_field(cls.abilities, 'Gupg', 'abpx', 1)
        set_field(cls.abilities, 'Gupg', 'abpy', 1)

    def setUp(self):
        self.a, self.u = deepcopy(self.abilities), deepcopy(self.units)

    def test_corrected_fixture_accepts_exact_UI_book_and_unique_channels(self):
        verifier.verify_no_removed_controls(self.a, self.u)
        verifier.verify_builder_function_book(self.a, self.u)
        verify_farmer_grid(self.a, self.u)
        verify_collection_commands(self.a)

    def test_own_removed_ghost_objects_and_references_are_rejected(self):
        for code in verifier.B_REMOVED:
            abilities = deepcopy(self.a)
            abilities[code] = ('AEbl' if code == 'A108' else 'Ahrp', {})
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'B blink/repair.*removed object'):
                verifier.verify_no_removed_controls(abilities, self.u)
            units = deepcopy(self.u)
            units['uF01']['uabi'] += ',' + code
            with self.subTest(reference=code), self.assertRaisesRegex(ValueError, 'B blink/repair.*references removed'):
                verifier.verify_no_removed_controls(self.a, units)

    def test_predecessor_removed_objects_are_checked_separately(self):
        for code in verifier.PREDECESSOR_REMOVED:
            abilities = deepcopy(self.a)
            abilities[code] = ('ANcl', {})
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'predecessor master/rank.*removed object'):
                verifier.verify_no_removed_controls(abilities, self.u)

    def test_book_rejects_duplicate_upgrade_or_any_extra_spell(self):
        for spells in ('A119,Gupg', 'Gupg', 'A119,A119', 'A119,Pmas', 'A119,Dsta'):
            abilities = deepcopy(self.a)
            set_field(abilities, 'Geqb', 'spb1', spells, 1, 1)
            # Formal predecessor guards reject retired rawcodes before the book list.
            reason = 'removed ' + spells.split(',')[-1] + ' remains in ability field spb1' if spells in ('A119,Pmas', 'A119,Dsta') else 'only A119'
            with self.subTest(spells=spells), self.assertRaisesRegex(ValueError, reason):
                verifier.verify_builder_function_book(abilities, self.u)

    def test_book_min_and_max_must_each_be_one(self):
        for field, column in [('spb3', 3), ('spb4', 4)]:
            for count in (0, 2, 5):
                abilities = deepcopy(self.a)
                set_field(abilities, 'Geqb', field, count, 1, column)
                with self.subTest(field=field, count=count), self.assertRaisesRegex(ValueError, 'exactly one spell'):
                    verifier.verify_builder_function_book(abilities, self.u)

    def test_main_upgrade_position_and_hotkey_are_exact(self):
        for field, value in [('abpx', 2), ('abpy', 0), ('ahky', 'C')]:
            abilities = deepcopy(self.a)
            set_field(abilities, 'Gupg', field, value)
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'main bar 1,1/U'):
                verifier.verify_builder_function_book(abilities, self.u)

    def test_missing_or_duplicate_main_upgrade_attachment_is_rejected(self):
        for skills in ('AUbu,A109,A117,Geqb,Pcap,Pcol,Pdep', 'AUbu,A109,A117,Geqb,Gupg,Gupg,Pcap,Pcol,Pdep'):
            units = deepcopy(self.u)
            units['uF01']['uabi'] = skills
            with self.subTest(skills=skills), self.assertRaisesRegex(ValueError, 'exact command attachment'):
                verifier.verify_builder_function_book(self.a, units)

    def test_farmer_conflicts_and_former_blink_cell_are_rejected(self):
        import VerifyPetUIArtifact as ui
        for code in ui.EXPECTED:
            abilities = deepcopy(self.a)
            set_field(abilities, code, 'abpx', 0)
            set_field(abilities, code, 'abpy', 0)
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'farmer cell overlaps'):
                verify_farmer_grid(abilities, self.u)
        set_field(self.a, 'Gupg', 'abpx', 2)
        set_field(self.a, 'Gupg', 'abpy', 1)
        with self.assertRaisesRegex(ValueError, 'eleven cells'):
            verify_farmer_grid(self.a, self.u)

    def test_reallocated_collection_orders_are_allowed_when_globally_unique(self):
        first = verifier.field(self.a, 'Pc00', 'Ncl6', 1, 6)
        second = verifier.field(self.a, 'Pc01', 'Ncl6', 1, 6)
        set_field(self.a, 'Pc00', 'Ncl6', second, 1, 6)
        set_field(self.a, 'Pc01', 'Ncl6', first, 1, 6)
        verify_collection_commands(self.a)
        verifier.verify_global_channel_orders(self.a)

    def test_global_channel_collision_and_late_level_inconsistency_are_rejected(self):
        order = verifier.field(self.a, 'A109', 'Ncl6', 1, 6)
        self.a['Xord'] = ('ANcl', {('Ncl6', 1, 6): (3, order)})
        with self.assertRaisesRegex(ValueError, 'collides'):
            verifier.verify_global_channel_orders(self.a)
        abilities = deepcopy(self.abilities)
        set_field(abilities, 'Pcap', 'Ncl6', order, 61, 6)
        with self.assertRaisesRegex(ValueError, 'consistent across all levels|collides'):
            verifier.verify_global_channel_orders(abilities)


class BuilderControlRawObjectNegativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.objects = load_objects(Mpq((ROOT / 'ExampleMap.w3x').read_bytes()))
        for entries in cls.objects.values():
            for code in verifier.B_REMOVED + verifier.PREDECESSOR_REMOVED:
                entries.pop(code, None)
        # Correct only this in-memory worker attachment from the formal A artifact.
        worker = cls.objects['units']['uF01']
        key = ('uabi', 0, 0)
        worker.fields[key] = replace(worker.fields[key], value='AUbu,A109,A117,Geqb,Gupg,Pcap,Pcol,Pdep')

    def test_corrected_raw_fixture_accepts_every_object_table(self):
        for kind, entries in self.objects.items():
            verifier.verify_no_removed_raw_controls(entries, kind)

    def test_raw_parent_or_reference_cannot_hide_own_removed_controls(self):
        for kind in ('units', 'items', 'abilities'):
            for code in verifier.B_REMOVED:
                entries = deepcopy(self.objects[kind])
                uid = next(iter(entries)); obj = entries[uid]
                obj.identity = code.encode() + obj.identity[4:]
                with self.subTest(table=kind, parent=code), self.assertRaisesRegex(ValueError, 'B blink/repair.*removed object/parent'):
                    verifier.verify_no_removed_raw_controls(entries, kind)
                entries = deepcopy(self.objects[kind]); obj = entries[uid]
                key = next(key for key, item in obj.fields.items() if item.kind == 3)
                obj.fields[key] = replace(obj.fields[key], value=code)
                with self.subTest(table=kind, reference=code), self.assertRaisesRegex(ValueError, 'B blink/repair.*references removed'):
                    verifier.verify_no_removed_raw_controls(entries, kind)


class BuilderControlActualNewArtifactTests(unittest.TestCase):
    def test_raw_new_artifact_exact_main_bar_book_no_ghosts_and_channel_orders(self):
        artifact = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        verifier.verify_raw_control_tables(artifact)
        abilities = ability_objects(artifact.extract('war3map.w3a'))
        data = artifact.extract('war3map.w3u')
        units = unit_objects(data)
        validate_builder_objects(units, unit_parents(data))
        verifier.verify_no_removed_controls(abilities, units)
        verifier.verify_builder_function_book(abilities, units)
        verify_farmer_grid(abilities, units)
        verify_collection_commands(abilities)


if __name__ == '__main__':
    unittest.main()
