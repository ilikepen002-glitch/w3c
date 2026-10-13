"""Packaged tower upgrades plus deepcopy negative regressions.

The real-artifact positives deliberately reject pre-repair maps. No fixture
normalization can make the actual packaged positive checks pass.
"""
from copy import deepcopy
from pathlib import Path
import re
import sys
import unittest
from python_check_inputs import candidate_map

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from VerifySlowAbilityArtifact import validate_slow_abilities
from VerifyEvolutionArtifact import validate_branch_displays
import VerifyTowerUpgradeArtifact as verifier


class TowerUpgradeArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = Mpq((candidate_map()).read_bytes())
        cls.units = unit_objects(cls.artifact.extract('war3map.w3u'))
        cls.abilities = ability_objects(cls.artifact.extract('war3map.w3a'))
        cls.script = cls.artifact.extract('war3map.j').decode('utf-8')

    def test_actual_35_node_30_edge_contract(self):
        self.assertEqual(len(verifier.validate_upgrade_artifact(self.units, self.abilities, self.artifact)), 30)

    def test_actual_all_61_slow_poison_bash_levels(self):
        validate_slow_abilities(self.abilities)

    def test_actual_ten_evolution_sets_and_branch_only_damage_paths(self):
        verifier.validate_evolution_jass(self.script, self.units, self.abilities)

    def test_each_35_node_rejects_every_missing_skill(self):
        for uid, expected in verifier.EXPECTED_TOWERS.items():
            for missing in expected:
                with self.subTest(unit=uid, ability=missing):
                    units = deepcopy(self.units)
                    units[uid]['uabi'] = ','.join(aid for aid in expected if aid != missing)
                    with self.assertRaisesRegex(ValueError, re.escape(f'{uid}: complete skill bar mismatch')):
                        verifier.validate_skill_bars(units, self.abilities)

    def test_every_terminal_rejects_old_skill_drop_and_variant_overlap(self):
        for uid in verifier.EVOLUTION_REPLACEMENTS:
            with self.subTest(unit=uid):
                units = deepcopy(self.units)
                units[uid]['uabi'] += ',A100'
                with self.assertRaisesRegex(ValueError, 'complete skill bar mismatch'):
                    verifier.validate_skill_bars(units, self.abilities)
        for uid, replacements in verifier.EVOLUTION_REPLACEMENTS.items():
            for old, new in replacements.items():
                with self.subTest(unit=uid, old=old, new=new):
                    units = deepcopy(self.units)
                    units[uid]['uabi'] += ',' + new
                    with self.assertRaisesRegex(ValueError, 'complete skill bar mismatch'):
                        verifier.validate_skill_bars(units, self.abilities)

    def test_every_node_rejects_reordering_duplicate_or_dynamic_status(self):
        for uid, expected in verifier.EXPECTED_TOWERS.items():
            for mutation in [list(reversed(expected)), expected + [expected[0]], expected + ['AeEV']]:
                with self.subTest(unit=uid, skills=mutation):
                    units = deepcopy(self.units)
                    units[uid]['uabi'] = ','.join(mutation)
                    with self.assertRaisesRegex(ValueError, 'complete skill bar mismatch'):
                        verifier.validate_skill_bars(units, self.abilities)

    def test_missing_unit_or_ability_object_is_rejected(self):
        for uid in verifier.EXPECTED_TOWERS:
            units = deepcopy(self.units)
            del units[uid]
            with self.subTest(unit=uid), self.assertRaisesRegex(ValueError, 'exactly 35 tower types'):
                verifier.validate_skill_bars(units, self.abilities)
        for aid in {aid for skills in verifier.EXPECTED_TOWERS.values() for aid in skills}:
            abilities = self.abilities.copy()
            del abilities[aid]
            with self.subTest(ability=aid), self.assertRaisesRegex(ValueError, 'missing ability object'):
                verifier.validate_skill_bars(self.units, abilities)

    def test_all_30_upgrade_edges_reject_missing_successor(self):
        for family in verifier.FAMILIES:
            for level in range(1, 6):
                uid = f'u{family}1{level}'
                targets = self.units[uid]['uupt'].split(',')
                for missing in targets:
                    units = deepcopy(self.units)
                    units[uid]['uupt'] = ','.join(target for target in targets if target != missing)
                    with self.subTest(unit=uid, target=missing), self.assertRaisesRegex(ValueError, 'upgrade chain mismatch'):
                        verifier.validate_upgrade_edges(units)

    def test_all_30_upgrade_edges_reject_range_retreat(self):
        for family in verifier.FAMILIES:
            for level in range(1, 6):
                uid = f'u{family}1{level}'
                for target in self.units[uid]['uupt'].split(','):
                    for field in ['uacq', 'ua1r']:
                        units = deepcopy(self.units)
                        units[target][field] = units[uid][field] - 1
                        with self.subTest(edge=(uid, target), field=field), self.assertRaisesRegex(ValueError, 'range regressed'):
                            verifier.validate_upgrade_edges(units)

    def test_all_ten_terminals_reject_basic_dps_retreat(self):
        for uid in verifier.EVOLUTION_REPLACEMENTS:
            units = deepcopy(self.units)
            units[uid]['ua1c'] = 1000.0
            with self.subTest(unit=uid), self.assertRaisesRegex(ValueError, 'terminal basic DPS regressed'):
                verifier.validate_upgrade_edges(units)

    def test_all_35_unit_command_cells_and_hotkeys(self):
        for uid in verifier.EXPECTED_TOWERS:
            for field, bad in [('ubpx', 3), ('ubpy', 0), ('uhot', 'Z')]:
                units = deepcopy(self.units)
                units[uid][field] = bad
                with self.subTest(unit=uid, field=field), self.assertRaisesRegex(ValueError, 'wrong build/upgrade'):
                    verifier.validate_command_ui(units, self.abilities)

    def copy_ability(self, aid):
        # Share immutable unmodified objects, deepcopy the one negative target.
        abilities = self.abilities.copy()
        abilities[aid] = deepcopy(self.abilities[aid])
        return abilities

    @staticmethod
    def change_field(abilities, code, field, value, level=0, column=0):
        original = abilities[code][1].get((field, level, column))
        kind = original[0] if original else 3 if isinstance(value, str) else 2 if isinstance(value, float) else 0
        abilities[code][1][(field, level, column)] = (kind, value)

    def test_active_normal_off_cells_and_hotkeys(self):
        for aid in ['A131', 'A132']:
            for field, bad, reason in [('abpx', 1, 'visible skill cell'), ('abpy', 2, 'visible skill cell'),
                                       ('aubx', 1, 'off-state skill cell'), ('auby', 2, 'off-state skill cell'),
                                       ('ahky', 'Q', 'active skill hotkey'), ('auhk', 'W', 'off-state skill hotkey')]:
                abilities = self.copy_ability(aid)
                self.change_field(abilities, aid, field, bad)
                with self.subTest(ability=aid, field=field), self.assertRaisesRegex(ValueError, reason):
                    verifier.validate_command_ui(self.units, abilities)

    def test_all_visible_passive_skill_cells_are_rejected_when_moved(self):
        visible = {aid for skills in verifier.EXPECTED_TOWERS.values() for aid in skills}
        visible -= verifier.HIDDEN | set(verifier.COMMON) | {'A131', 'A132'}
        visible |= {'A111', 'A112', 'A113', 'A114', 'AeCM', 'A136', 'A138'}
        for aid in visible:
            for field, bad in [('abpx', 3), ('abpy', 0)]:
                abilities = self.copy_ability(aid)
                self.change_field(abilities, aid, field, bad)
                with self.subTest(ability=aid, field=field), self.assertRaisesRegex(ValueError, 'wrong visible skill cell'):
                    verifier.validate_command_ui(self.units, abilities)

    def test_two_level_split_corpse_displays_must_be_zero_effect(self):
        validate_branch_displays(self.units, self.abilities)
        for aid in ['A100', 'A116']:
            for level in [1, 2]:
                for field, column, bad in [('Ocr1', 1, 1.0), ('Ocr2', 2, 1.2), ('Ocr3', 3, 1.0), ('Ocr5', 5, 1)]:
                    abilities = self.copy_ability(aid)
                    self.change_field(abilities, aid, field, bad, level, column)
                    with self.subTest(ability=aid, level=level, field=field), self.assertRaisesRegex(ValueError, 'display carrier has combat effect'):
                        validate_branch_displays(self.units, abilities)
            abilities = self.copy_ability(aid)
            self.change_field(abilities, aid, 'alev', 1)
            with self.subTest(ability=aid), self.assertRaisesRegex(ValueError, 'normal/evolved display levels'):
                validate_branch_displays(self.units, abilities)

    def test_evolved_split_and_corpse_tooltips_cannot_hide_or_invent_strengthening(self):
        for aid, text, reason in [('A100', '主箭伤害提高20%，6目标', 'extra-arrow-only gain'),
                                  ('A116', '尸爆36点伤害', '43.2 damage')]:
            abilities = self.copy_ability(aid)
            self.change_field(abilities, aid, 'aub1', text, 2)
            with self.subTest(ability=aid), self.assertRaisesRegex(ValueError, reason):
                validate_branch_displays(self.units, abilities)

    def test_each_remaining_custom_btn_and_disbtn_must_be_packaged(self):
        class BlockOneResource:
            def __init__(self, original, blocked):
                self.original, self.blocked = original, blocked
            def has(self, path):
                return path != self.blocked and self.original.has(path)
            def extract(self, path):
                return self.original.extract(path)
        icons = {verifier.field_value(self.abilities, aid, field)
                 for aid in ['A140', 'A141'] for field in ['aart', 'arar']}
        icons |= {'ReplaceableTextures\\CommandButtonsDisabled\\DIS' + icon.rsplit('\\', 1)[1] for icon in list(icons)}
        for missing in icons:
            with self.subTest(resource=missing), self.assertRaisesRegex(ValueError, 'Missing exact (?:BTN|DISBTN) resource'):
                verifier.validate_branch_resources(BlockOneResource(self.artifact, missing), self.units, self.abilities)

    def test_native_branch_icons_are_not_map_imports(self):
        for uid in verifier.EVOLUTION_REPLACEMENTS:
            normal = self.units[uid]['uico']
            self.assertTrue(normal.startswith(verifier.NATIVE_ICON_PREFIX))
            disabled = 'ReplaceableTextures\\CommandButtonsDisabled\\DIS' + normal.rsplit('\\', 1)[1]
            self.assertFalse(self.artifact.has(normal))
            self.assertFalse(self.artifact.has(disabled))

    def test_scalar_evaluator_rejects_mixed_jass_boolean_precedence(self):
        evaluator = verifier.JassScalarEvaluator('')
        with self.assertRaisesRegex(ValueError, 'Jass-specific precedence parser'):
            evaluator.expression('(a or b) and c', {'a': True, 'b': False, 'c': True})

    def test_pure_command_conflict_checks(self):
        for commands, reason in [([('A131', (2, 1), 'E'), ('A132', (2, 1), 'R')], 'cells overlap'),
                                 ([('A131', (2, 1), 'E'), ('uO6A', (0, 2), 'E')], 'hotkeys overlap')]:
            with self.assertRaisesRegex(ValueError, reason):
                verifier.check_command_conflicts('uO15', commands)

    def test_each_final_identity_field_is_specific_and_each_low_identity_retained(self):
        for uid in verifier.EXPECTED_TOWERS:
            for field in ['uico', 'ussi', 'umdl']:
                units = deepcopy(self.units)
                units[uid][field] = 'ReplaceableTextures\\CommandButtons\\BTNWrong.blp'
                with self.subTest(unit=uid, field=field), self.assertRaisesRegex(ValueError, 'identity mismatch|model changed'):
                    verifier.validate_tower_identity(units)

    def test_all_183_slow_levels_reject_radius_sign_buff_and_targets_changes(self):
        for aid in ['A110', 'A140', 'AeSL']:
            for level in range(1, 62):
                for field, column, value, reason in [('aare', 0, 999.0, 'aare level'),
                                                    ('Slo1', 1, .18, 'Slo1 level'),
                                                    ('abuf', 0, 'Bspo', 'native slow buff changed'),
                                                    ('atar', 0, 'enemy,ground', 'targets changed')]:
                    abilities = self.copy_ability(aid)
                    self.change_field(abilities, aid, field, value, level, column)
                    with self.subTest(ability=aid, level=level, field=field), self.assertRaisesRegex(ValueError, reason):
                        validate_slow_abilities(abilities)

    def test_all_183_slow_display_levels_reject_combat_effect_or_false_radius(self):
        for aid in ['A135', 'A141', 'A136']:
            for level in range(1, 62):
                for field, column, value, reason in [('Ocr1', 1, 1.0, 'Ocr1 level'),
                                                    ('Ocr2', 2, 1.2, 'Ocr2 level'),
                                                    ('aub1', 0, '周围999范围移动速度降低18%', 'display radius/reduction mismatch')]:
                    abilities = self.copy_ability(aid)
                    self.change_field(abilities, aid, field, value, level, column)
                    with self.subTest(ability=aid, level=level, field=field), self.assertRaisesRegex(ValueError, reason):
                        validate_slow_abilities(abilities)

    def mutate_function(self, name, mutation):
        original = verifier.function_body(self.script, name)
        changed = mutation(original)
        self.assertNotEqual(original, changed, f'Negative case did not mutate {name}')
        return self.script.replace(original, changed, 1)

    def test_jass_rejects_evolution_replacement_rawcode_regression(self):
        name = 'TDTowerCatalogData_TD_DRYAD_WIDE_SLOW_ABILITY_ID'
        old = verifier.rawcode('A140')
        pattern = rf'(set {name} = ){old}\b'
        script, count = re.subn(pattern, rf'\g<1>{verifier.rawcode("A110")}', self.script)
        self.assertEqual(count, 1)
        with self.assertRaisesRegex(ValueError, 'Jass evolution mapping mismatch'):
            verifier.validate_evolution_jass(script, self.units, self.abilities)

    def test_jass_rejects_branch_only_multiplier_leaks(self):
        for name, reason in [('tdArcherSplitArrowDamageMultiplier', 'Jass split multiplier leaks'),
                             ('tdGhoulCorpseExplosionDamageForBranch', 'Jass corpse damage leaks')]:
            script = self.mutate_function(name, lambda body: re.sub(r'branch == \w+', 'true', body))
            with self.subTest(helper=name), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_evolution_jass(script, self.units, self.abilities)

    def test_jass_rejects_damage_path_detached_from_verified_helper(self):
        for handler, helper in [('tdHandleArcherSplitArrowDamage', 'tdArcherSplitArrowDamageMultiplier'),
                                ('tdHandleGhoulCorpseExplosionDamage', 'tdGhoulCorpseExplosionDamageForBranch')]:
            script = self.mutate_function(handler, lambda body: body.replace(helper + '(', 'unverifiedDamageHelper('))
            with self.subTest(handler=handler), self.assertRaisesRegex(ValueError, 'damage handler does not consume'):
                verifier.validate_evolution_jass(script, self.units, self.abilities)

    def test_jass_rejects_verified_helpers_whose_values_are_discarded(self):
        for handler, mutation, reason in [
            ('tdHandleArcherSplitArrowDamage', lambda body: re.sub(r'(call tdDealArcherSplitArrowAttackDamage\(\w+, \w+, )attackDamage_\d+', r'\g<1>1.0', body), 'immediate extra-arrow damage'),
            ('tdHandleGhoulCorpseExplosionDamage', lambda body: body.replace('call unit_damageTarget_1(', 'call discarded_damage_value('), 'corpse helper result does not reach damage'),
        ]:
            script = self.mutate_function(handler, mutation)
            with self.subTest(handler=handler), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_evolution_jass(script, self.units, self.abilities)

    def test_jass_rejects_delayed_callback_discarding_stored_extra_arrow_damage(self):
        body = verifier.function_body(self.script, 'tdHandleArcherSplitArrowDamage')
        callback = re.search(r'alloc_CallbackSingle_(\w+)\(', body)
        self.assertIsNotNone(callback)
        script = self.mutate_function('call_' + callback[1], lambda value: re.sub(r'attackDamage\[\w+\]', '1.0', value))
        with self.assertRaisesRegex(ValueError, 'delayed extra-arrow callback does not consume'):
            verifier.validate_evolution_jass(script, self.units, self.abilities)

    def test_jass_rejects_extra_removal_and_main_arrow_rewrite(self):
        for function, line, reason in [('tdEvolutionRefresh', '\n call unit_removeAbility(tower_2, 1093742897)\n', 'remove only selected'),
                                      ('tdHandleArcherSplitArrowDamage', '\n call DamageEvent_setAmount(999.0)\n', 'primary-arrow damage')]:
            script = self.mutate_function(function, lambda body: body + line)
            with self.subTest(function=function), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_evolution_jass(script, self.units, self.abilities)

    def test_jass_rejects_six_target_final_split_arrow(self):
        script = self.mutate_function('tdArcherSplitArrowTargetCount', lambda body: body.replace('clampedLevel + 1', 'clampedLevel'))
        with self.assertRaisesRegex(ValueError, 'seven total targets'):
            verifier.validate_evolution_jass(script, self.units, self.abilities)


if __name__ == '__main__':
    unittest.main(verbosity=2)
