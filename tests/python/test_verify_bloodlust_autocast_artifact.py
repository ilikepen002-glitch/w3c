"""Fresh static source/invariant negatives; raw new-build JASS tests separate."""
from copy import deepcopy
from pathlib import Path
import subprocess
import os
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTowerUpgradeArtifact import JassScalarEvaluator
import VerifyBloodlustAutocastArtifact as verifier


def mutate_body(source, name, transform):
    body = verifier.source_body(source, name)
    replacement = transform(body)
    if replacement == body:
        raise ValueError('Mutation must change ' + name)
    return source.replace(body, replacement, 1)


class BloodlustStaticSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = [(ROOT / path).read_text() for path in
                       ('wurst/towers/TDTowerBloodlustAutocast.wurst', 'wurst/items/TDEquipmentAbilities.wurst',
                        'wurst/towers/TDTowerRuntime.wurst', 'wurst/items/TDEquipmentObjectGen.wurst',
                        'wurst/abilities/TDActiveCooldownRuntime.wurst', 'wurst/abilities/TDActiveSkillData.wurst')]

    def test_actual_current_source_scalar_matrix_and_lifecycle(self):
        verifier.validate_sources(*self.sources)

    def test_rejects_wrong_first_manual_or_unknown_restore_rule(self):
        for name in ('tdBloodlustChoiceAfterInitialization', 'tdBloodlustChoiceAfterOrder', 'tdBloodlustOrderForChoice'):
            source = self.sources.copy()
            source[0] = mutate_body(source[0], name, lambda _: '\treturn 0\n')
            with self.subTest(helper=name), self.assertRaises(ValueError):
                verifier.validate_sources(*source)

    def test_rejects_listener_writeback_or_order_issue_and_restore_initializing(self):
        cases = [('tdHandleBloodlustAutocastOrder', lambda text: text.replace('if tdBloodlustRestoring', 'if false'), 'script writeback'),
                 ('tdHandleBloodlustAutocastOrder', lambda text: text + '\ttower.issueImmediateOrderById(Orders.bloodluston)\n', 'only save'),
                 ('tdRestoreNativeActiveAutocast', lambda text: text + '\ttdActiveAutocastChoices.saveInt(1, 1, 1)\n', 'must not write'),
                 ('tdRestoreNativeActiveAutocast', lambda text: text.replace('tdBloodlustRestoring = true', 'tdBloodlustRestoring = false'), 'sync')]
        for name, change, reason in cases:
            source = self.sources.copy()
            source[0] = mutate_body(source[0], name, change)
            with self.subTest(case=name, reason=reason), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_sources(*source)

    def test_rejects_losing_busy_or_missing_choice(self):
        source = self.sources.copy()
        source[0] = mutate_body(source[0], 'tdNativeActiveAutocastEligible',
                               lambda text: text + '\ttdForgetBloodlustAutocast(tower)\n')
        with self.assertRaisesRegex(ValueError, 'retain choice'):
            verifier.validate_sources(*source)

    def test_each_retirement_must_erase_choice(self):
        for name in ('tdHandleTowerSellCast', 'tdRejectTowerConstruction', 'tdHandleTowerConstructionCancelled', 'tdHandleTowerDeath'):
            source = self.sources.copy()
            source[2] = mutate_body(source[2], name, lambda text: text.replace('\ttdForgetBloodlustAutocast(tower)\n', ''))
            with self.subTest(retirement=name), self.assertRaisesRegex(ValueError, 'cleanup missing'):
                verifier.validate_sources(*source)

    def test_rejects_stale_cancel_or_second_async_delay(self):
        for old, new in [('finishWorkForGeneration(cancelledGeneration)', 'finishWork()'),
                         ('\t\ttdInitializeBloodlustAutocast(tower)', '\t\tdoAfter(0.0) ->\n\t\t\ttdInitializeBloodlustAutocast(tower)')]:
            source = self.sources.copy()
            source[2] = source[2].replace(old, new)
            with self.subTest(case=old), self.assertRaisesRegex(ValueError, 'generation guard'):
                verifier.validate_sources(*source)

    def test_same_level_set_and_expiry_reset_are_rejected(self):
        for old, new in [('actualLevel == desiredLevel', 'actualLevel != desiredLevel'),
                         ('desiredLevel = nextLevel', 'desiredLevel = nextLevel\n\t\treadyAt = 0.0')]:
            source = self.sources.copy()
            source[5] = source[5].replace(old, new)
            with self.subTest(case=old), self.assertRaises(ValueError): verifier.validate_sources(*source)

    def test_bladestorm_native_effects_and_evolution_remain_preserved(self):
        from VerifyActiveCooldownContract import verify_source, read_sources
        sources = read_sources()
        sources['items/TDEquipmentObjectGen.wurst'] = self.sources[3]
        expected = verify_source(sources=sources)['native_objects']['A132']
        artifact = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        parent, fields = ability_objects(artifact.extract('war3map.w3a'))['A132']
        self.assertEqual(parent, expected[0])
        for key, value in expected[1].items():
            self.assertEqual(fields[key], value)
        path = 'wurst/towers/TDTowerEvolutionRuntime.wurst'
        old = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:' + path])
        self.assertEqual((ROOT / path).read_bytes(), old)

    def test_two_independent_keys_and_retirement_use_production_choice_table(self):
        module = self.sources[0]
        body = verifier.source_body(module, 'tdBloodlustIndependentChoicesRegressionForTest')
        for token in ('firstKey = -131', 'secondKey = -132', 'saveInt(firstKey, TD_ORC_BLOODLUST_ABILITY_ID, TD_ACTIVE_AUTOCAST_OFF)',
                      'saveInt(secondKey, TD_ORC_BLOODLUST_ABILITY_ID, TD_ACTIVE_AUTOCAST_ON)', 'tdForgetBloodlustChoiceKey(firstKey)',
                      'tdForgetBloodlustChoiceKey(secondKey)'):
            self.assertIn(token, body)
        self.assertIn('tdActiveAutocastChoices.flushChild(key)', verifier.source_body(module, 'tdForgetBloodlustChoiceKey'))


class BloodlustNativeInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.abilities = ability_objects(Mpq((ROOT / 'ExampleMap.w3x').read_bytes()).extract('war3map.w3a'))

    def test_formal_predecessor_keeps_native_ablo_41_levels_and_bblo(self):
        verifier.validate_native_bloodlust(self.abilities)

    def test_rejects_wrong_native_parent_or_level_count(self):
        abilities = deepcopy(self.abilities)
        abilities['A131'] = ('ANcl', abilities['A131'][1])
        with self.assertRaisesRegex(ValueError, 'Ablo'):
            verifier.validate_native_bloodlust(abilities)
        abilities = deepcopy(self.abilities)
        abilities['A131'][1][('alev', 0, 0)] = (0, 1)
        with self.assertRaisesRegex(ValueError, '41 levels'):
            verifier.validate_native_bloodlust(abilities)

    def test_each_native_level_rejects_cooldown_change_or_missing_buff(self):
        for level in range(1, 42):
            for field, value, reason in [('acdn', (2, 0.0), 'cooldown changed'), ('abuf', (3, ''), 'Bblo missing')]:
                abilities = deepcopy(self.abilities)
                abilities['A131'][1][(field, level, 0)] = value
                with self.subTest(level=level, field=field), self.assertRaisesRegex(ValueError, reason):
                    verifier.validate_native_bloodlust(abilities)


@unittest.skipUnless(os.environ.get('W3C_ACTIVE_COOLDOWN_MAP'), 'New universal-cooldown MPQ not built; set W3C_ACTIVE_COOLDOWN_MAP explicitly')
class BloodlustActualNewArtifactTests(unittest.TestCase):
    def test_actual_new_packaged_choice_matrix_lifecycle_and_tooltips(self):
        artifact = Mpq(Path(os.environ['W3C_ACTIVE_COOLDOWN_MAP']).read_bytes())
        verifier.validate_native_bloodlust(ability_objects(artifact.extract('war3map.w3a')), tooltips=True)
        script = artifact.extract('war3map.j').decode('utf-8')
        verifier.validate_packed_choice_matrix(script)
        verifier.validate_compiled_lifecycle(script)

    def test_actual_generic_choice_mutation_still_rejected(self):
        from VerifyTowerUpgradeArtifact import function_body
        script = Mpq(Path(os.environ['W3C_ACTIVE_COOLDOWN_MAP']).read_bytes()).extract('war3map.j').decode()
        body = function_body(script, 'tdActiveAutocastChoiceAfterInitialization')
        self.assertIn('return initialChoice', body)
        changed = script.replace(body, body.replace('return initialChoice', 'return 0', 1), 1)
        with self.assertRaisesRegex(ValueError, 'first/default/reinitialize'):
            verifier.validate_packed_choice_matrix(changed)


if __name__ == '__main__':
    unittest.main()
