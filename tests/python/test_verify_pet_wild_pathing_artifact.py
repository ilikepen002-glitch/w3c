"""Focused native-Aeth contract tests; in-memory greens do not prove a rebuild."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from VerifyUnitParentsArtifact import unit_parents
import VerifyPetWildPathingArtifact as verifier


class WildPathingArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Immutable pre-fix release: these tests stay meaningful after rebuilding.
        data = subprocess.check_output(['git', 'show', '529ac30:ExampleMap.w3x'], cwd=ROOT)
        cls.archive = Mpq(data)
        cls.baseline_units = unit_objects(cls.archive.extract('war3map.w3u'))
        cls.parents = unit_parents(cls.archive.extract('war3map.w3u'))
        cls.baseline_abilities = ability_objects(cls.archive.extract('war3map.w3a'))
        cls.script = cls.archive.extract('war3map.j').decode('utf-8')

    def setUp(self):
        self.units = deepcopy(self.baseline_units)
        self.abilities = deepcopy(self.baseline_abilities)
        for uid in verifier.WILD_IDS:
            self.units[uid]['uabi'] = 'Aeth'

    def test_actual_release_retains_aeth_and_ordinary_capture_contract(self):
        archive = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        data = archive.extract('war3map.w3u')
        verifier.verify_wild_units(unit_objects(data), unit_parents(data))
        verifier.verify_capture_contract(ability_objects(archive.extract('war3map.w3a')))
        script = archive.extract('war3map.j').decode('utf-8')
        verifier.verify_runtime(script, script)

    def test_actual_pre_fix_mpq_is_red_for_missing_aeth(self):
        with self.assertRaisesRegex(ValueError, 'p011: wild uabi must be exactly Aeth'):
            verifier.verify_archive(self.archive, self.archive)
        self.assertEqual(sum(self.baseline_units[uid]['uabi'] == '' for uid in verifier.WILD_IDS), 96)

    def test_in_memory_single_field_fix_is_green(self):
        verifier.verify_wild_units(self.units, self.parents)
        verifier.verify_capture_contract(self.abilities)
        self.assertEqual(verifier.verify_unit_diff(self.units, self.parents,
                                                  self.baseline_units, self.parents), 0)
        self.assertGreater(verifier.verify_runtime(self.script, self.script), 0)

    def test_each_of_96_wild_ability_omissions_is_rejected(self):
        for uid in sorted(verifier.WILD_IDS):
            with self.subTest(unit=uid):
                self.units[uid]['uabi'] = ''
                with self.assertRaisesRegex(ValueError, uid + ': wild uabi'):
                    verifier.verify_wild_units(self.units, self.parents)
                self.units[uid]['uabi'] = 'Aeth'

    def test_rejects_locust_invisible_ghost_and_runtime_duplicate(self):
        for abilities in ('Aloc', 'Agho', 'Aeth,Aloc', 'Aeth,Agho', 'Aeth,Aeth', 'Aeth,Avul'):
            with self.subTest(abilities=abilities):
                self.units['p011']['uabi'] = abilities
                with self.assertRaisesRegex(ValueError, 'uabi must be exactly Aeth'):
                    verifier.verify_wild_units(self.units, self.parents)

    def test_rejects_missing_extra_and_mislabeled_wild_objects(self):
        for mode in ('missing', 'extra', 'mislabeled'):
            with self.subTest(mode=mode):
                units = deepcopy(self.units)
                if mode == 'missing':
                    del units['p011']
                else:
                    units['p001' if mode == 'extra' else 'zzzz'] = deepcopy(units['p011'])
                with self.assertRaisesRegex(ValueError, 'exactly 96'):
                    verifier.verify_wild_units(units, self.parents)

    def test_rejects_parent_or_collision_change(self):
        parents = dict(self.parents, p011='ewsp')
        with self.assertRaisesRegex(ValueError, 'parent must remain hpea'):
            verifier.verify_wild_units(self.units, parents)
        self.units['p011']['ucol'] = 1.0
        with self.assertRaisesRegex(ValueError, 'zero collision changed'):
            verifier.verify_wild_units(self.units, self.parents)

    def test_rejects_native_override_and_custom_aeth_parent(self):
        for uid, parent in (('Aeth', 'Aeth'), ('Zeth', 'Aeth')):
            with self.subTest(rawcode=uid):
                abilities = deepcopy(self.abilities)
                abilities[uid] = (parent, {})
                with self.assertRaisesRegex(ValueError, 'Aeth must not be overridden'):
                    verifier.verify_capture_contract(abilities)

    def test_each_capture_level_and_required_target_is_guarded(self):
        for uid, count in (('Pcap', 61),):
            for level in range(1, count + 1):
                for missing in sorted(verifier.REQUIRED_TARGETS):
                    with self.subTest(ability=uid, level=level, target=missing):
                        fields = self.abilities[uid][1]
                        old = fields[('atar', level, 0)]
                        fields[('atar', level, 0)] = (3, ','.join(
                            target for target in old[1].split(',') if target != missing))
                        with self.assertRaisesRegex(ValueError, uid + f' level {level}: .*target mask'):
                            verifier.verify_capture_contract(self.abilities)
                        fields[('atar', level, 0)] = old

    def test_rejects_capture_level_count_target_type_and_missing_mask(self):
        for uid in ('Pcap',):
            for key, value, reason in ((('alev', 0, 0), (0, 2), 'level count'),
                                       (('Ncl2', 1, 2), (0, 0), 'unit-targeted'),
                                       (('atar', 1, 0), None, 'target masks')):
                with self.subTest(ability=uid, field=key):
                    abilities = deepcopy(self.abilities)
                    if value is None:
                        del abilities[uid][1][key]
                    else:
                        abilities[uid][1][key] = value
                    with self.assertRaisesRegex(ValueError, reason):
                        verifier.verify_capture_contract(abilities)

    def test_diff_allows_only_coordinated_wild_icons_and_wurs(self):
        self.units['p011']['uico'] = 'icon.blp'
        self.units['p011']['ussi'] = 'icon.blp'
        self.units['uF01']['wurs'] = 99
        self.assertEqual(verifier.verify_unit_diff(self.units, self.parents,
                                                  self.baseline_units, self.parents), 2)

    def test_diff_rejects_nonwild_fields_and_wild_gameplay_changes(self):
        for uid, key, value in (('uF01', 'uabi', 'Aeth'), ('uF01', 'uico', 'icon.blp'),
                                ('p011', 'umvs', 121), ('p011', 'umvt', 'fly'),
                                ('p011', 'ubdg', 1), ('p011', 'ides', 'changed')):
            with self.subTest(unit=uid, field=key):
                units = deepcopy(self.units)
                units[uid][key] = value
                with self.assertRaisesRegex(ValueError, 'Unapproved packaged unit change'):
                    verifier.verify_unit_diff(units, self.parents, self.baseline_units, self.parents)

    def test_diff_requires_exact_96_empty_to_aeth_changes(self):
        self.units['p011']['uabi'] = ''
        with self.assertRaisesRegex(ValueError, 'exactly 96 wild uabi changes'):
            verifier.verify_unit_diff(self.units, self.parents, self.baseline_units, self.parents)

    def test_runtime_rejects_changed_capture_route_and_cleanup(self):
        for name in ('tdPetSpawnWild', 'tdPetWildTravelSpeed', 'tdPetHandleCaptureWithBall',
                     'construct_TDPetWildState', 'call_doPeriodically_TDPetWild'):
            with self.subTest(function=name):
                body = verifier.jass_functions(self.script)[name]
                changed = self.script.replace(body, body.replace('\n', '\n\t// mutation\n', 1), 1)
                with self.assertRaisesRegex(ValueError, 'wild/capture/route function changed'):
                    verifier.verify_runtime(changed, self.script)

    def test_runtime_rejects_pause_removal_and_pathing_reversal_even_in_reference(self):
        for statement, reason in (('call PauseUnit(creature, true)', 'must not pause'),
                                  ("call unit_removeAbility(creature, 'Aeth')", 'must not pause'),
                                  ("call unit_addAbility(creature, 'Aeth')", 'must not pause'),
                                  ('call unit_setPathing(creature, true)', 're-enable pathing')):
            with self.subTest(statement=statement):
                changed = self.script.replace('call unit_setPathing(creature, false)',
                                               'call unit_setPathing(creature, false)\n\t' + statement, 1)
                with self.assertRaisesRegex(ValueError, reason):
                    verifier.verify_runtime(changed, changed)

    def test_runtime_rejects_new_dummy_pause_caller(self):
        changed = self.script + '\nfunction bad takes unit creature returns nothing\n' \
                                '\tcall unit_pause(creature)\nendfunction\n'
        with self.assertRaisesRegex(ValueError, 'Unexpected pause/dummy call sites for unit_pause'):
            verifier.verify_runtime(changed, changed)

    def test_runtime_rejects_recycling_wild_as_fx_dummy(self):
        changed = self.script.replace('set Fx_dummy[this_1] = null',
                                       'set Fx_dummy[this_1] = TDPetWildRecord_creature[1]', 1)
        with self.assertRaisesRegex(ValueError, 'FX dummy assignment changed'):
            verifier.verify_runtime(changed, changed)

    def test_wild_source_has_one_native_attachment_and_preserved_collision(self):
        source = (ROOT / 'wurst/pets/TDPetObjectGen.wurst').read_text(encoding='utf-8')
        wild = source.split('new UnitDefinition(tdPetWildUnitId(wave, species)', 1)[1]
        wild = wild.split('\n\tnew ItemDefinition', 1)[0]
        self.assertEqual(wild.count('..setNormalAbilities("Aeth")'), 1)
        self.assertNotIn('Aloc', wild)
        self.assertNotIn('Agho', wild)
        self.assertIn('..setCollisionSize(0.0)', wild)
        self.assertIn('..setSpeedBase(120)', wild)
        self.assertIn('..setSpeedMinimum(1)', wild)
        self.assertIn('..setSpeedMaximum(150)', wild)


if __name__ == '__main__':
    unittest.main(verbosity=2)
