"""Fresh static source/invariant negatives; raw new-build JASS tests separate."""
from copy import deepcopy
from pathlib import Path
import subprocess
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
                        'wurst/towers/TDTowerRuntime.wurst', 'wurst/items/TDEquipmentObjectGen.wurst')]

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
                 ('tdRestoreBloodlustAutocast', lambda text: text + '\ttdBloodlustChoices.saveInt(1, 1)\n', 'must not write'),
                 ('tdRestoreBloodlustAutocast', lambda text: text.replace('tdBloodlustRestoring = true', 'tdBloodlustRestoring = false'), 'sync')]
        for name, change, reason in cases:
            source = self.sources.copy()
            source[0] = mutate_body(source[0], name, change)
            with self.subTest(case=name, reason=reason), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_sources(*source)

    def test_rejects_losing_busy_or_missing_choice(self):
        source = self.sources.copy()
        source[0] = mutate_body(source[0], 'tdBloodlustAutocastEligible',
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
        for old, new, reason in [('== desiredLevel', '!= desiredLevel', 'Same-level'),
                                 ('record.desiredLevel = desiredLevel', 'record.desiredLevel = desiredLevel\n\trecord.readyAt = 0.0', 'readyAt')]:
            source = self.sources.copy()
            source[1] = source[1].replace(old, new)
            with self.subTest(case=old), self.assertRaisesRegex(ValueError, reason):
                verifier.validate_sources(*source)

    def test_bladestorm_and_evolution_sources_remain_identical_to_formal_base(self):
        old = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:wurst/items/TDEquipmentObjectGen.wurst']).decode()
        self.assertEqual(verifier.source_body(self.sources[3], 'tdConfigureEquipmentBladestorm'),
                         verifier.source_body(old, 'tdConfigureEquipmentBladestorm'))
        path = 'wurst/towers/TDTowerEvolutionRuntime.wurst'
        old = subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:' + path])
        self.assertEqual((ROOT / path).read_bytes(), old)

    def test_two_independent_keys_and_retirement_use_production_choice_table(self):
        module = self.sources[0]
        body = verifier.source_body(module, 'tdBloodlustIndependentChoicesRegressionForTest')
        for token in ('firstKey = -131', 'secondKey = -132', 'saveInt(firstKey, TD_BLOODLUST_CHOICE_OFF)',
                      'saveInt(secondKey, TD_BLOODLUST_CHOICE_ON)', 'tdForgetBloodlustChoiceKey(firstKey)',
                      'tdForgetBloodlustChoiceKey(secondKey)'):
            self.assertIn(token, body)
        self.assertIn('tdBloodlustChoices.removeInt(key)', verifier.source_body(module, 'tdForgetBloodlustChoiceKey'))


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


class BloodlustActualNewArtifactTests(unittest.TestCase):
    def test_actual_new_packaged_choice_matrix_lifecycle_and_tooltips(self):
        artifact = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        verifier.validate_native_bloodlust(ability_objects(artifact.extract('war3map.w3a')), tooltips=True)
        script = artifact.extract('war3map.j').decode('utf-8')
        evaluator = JassScalarEvaluator(script)
        verifier.validate_choice_matrix(lambda name, values: evaluator.call(name, list(values.values())))
        verifier.validate_compiled_lifecycle(script)


if __name__ == '__main__':
    unittest.main()
