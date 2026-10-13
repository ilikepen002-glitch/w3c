"""Fast runner fixtures plus input-routing negatives; no Wurst/compiler/map build."""
from contextlib import redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('python_checks_runner', ROOT / 'tools/Run-PythonChecks.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

# Every legacy hardcoded current-map reader gets a direct-unittest regression.
CURRENT_MAP_READERS = (
    'test_aura_target_artifact.AuraTargetArtifactTests.test_actual_equipment_tower_pet_matrix_and_wind_application',
    'test_global_rankings_artifact.ActualArtifactTests.test_final_real_comparators',
    'test_ground_upgrade_artifact.GroundUpgradeArtifactTests.test_actual_full_contract_and_object_tooltip',
    'test_leak_life_artifact.LeakLifeArtifactTests.test_all_44_actual_enemy_rawcodes',
    'test_pet_compiled_rule_guards.PetCompiledRuleGuardTests.test_actual_all_2176_skill_admission_combinations',
    'test_pet_deployment_artifact.ActualDeploymentGateTests.test_real_packaged_gate_counts_guards_and_rebind',
    'test_pet_skill_fits_artifact.PetSkillFitsArtifactTests.test_actual_all_64_skill_and_host_capability_combinations',
    'test_verify_bloodlust_autocast_artifact.BloodlustActualNewArtifactTests.test_actual_new_packaged_choice_matrix_lifecycle_and_tooltips',
    'test_verify_bloodlust_autocast_artifact.BloodlustActualNewArtifactTests.test_actual_generic_choice_mutation_still_rejected',
    'test_verify_bloodlust_autocast_artifact.BloodlustStaticSourceTests.test_bladestorm_native_effects_and_evolution_remain_preserved',
    'test_verify_builder_construction_artifact.BuilderConstructionActualArtifactTests.test_actual_native_builder_and_all_towers',
    'test_verify_builder_control_artifact.BuilderControlActualNewArtifactTests.test_raw_new_artifact_exact_main_bar_book_no_ghosts_and_channel_orders',
    'test_verify_map_artifacts.BaselineArtifactTests.test_evolution_accepts_complete_inherited_skill_bars',
    'test_verify_pet_ui_artifact.PetUIArtifactTests.test_actual_farmer_grid_is_eleven_cells_with_empty_blink_slot',
    'test_verify_tower_upgrade_artifact.TowerUpgradeArtifactTests.test_actual_35_node_30_edge_contract',
)


class PythonChecksTests(unittest.TestCase):
    def run_fixture(self, modules, arguments, groups=None):
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for name, source in modules.items():
                (home / (name + '.py')).write_text(source)
                sys.modules.pop(name, None)
            try:
                with patch.object(runner, 'TEST_DIR', home), patch.object(runner, 'CLASS_GROUPS', groups or {'source': ['test_stub.Cases']}), patch.object(runner, 'METHOD_GROUPS', {}), redirect_stdout(output):
                    code = runner.main([str(home / arg) if arg.endswith('.py') else arg for arg in arguments])
            finally:
                for name in modules:
                    sys.modules.pop(name, None)
        return code, output.getvalue()

    def test_module_file_and_method_selection_are_exact_and_deduplicated(self):
        modules = {'test_stub': 'import unittest\nclass Cases(unittest.TestCase):\n def test_a(self): pass\n def test_b(self): pass\n',
                   'test_unrelated': 'raise RuntimeError("must not be imported")\n'}
        for args in (['test_stub'], ['test_stub.py'], ['tests.python.test_stub'], ['test_stub', 'test_stub.Cases.test_a']):
            with self.subTest(args=args):
                code, text = self.run_fixture(modules, args)
                self.assertEqual(code, 0, text)
                self.assertIn('selected=2 run=2 passed=2', text)
        code, text = self.run_fixture(modules, ['test_stub.Cases.test_b'])
        self.assertEqual(code, 0, text)
        self.assertIn('selected=1 run=1 passed=1', text)
        self.assertNotIn('Cases.test_a', text)

    def test_all_discovers_each_module_and_filter_preserves_category(self):
        modules = {'test_stub': 'import unittest\nclass Cases(unittest.TestCase):\n def test_ok(self): pass\n',
                   'test_other': 'import unittest\nclass Other(unittest.TestCase):\n def test_ok(self): pass\n'}
        groups = {'source': ['test_stub.Cases'], 'regression': ['test_other.Other']}
        code, text = self.run_fixture(modules, ['--all'], groups)
        self.assertEqual(code, 0, text)
        self.assertIn('selected=2 run=2', text)
        code, text = self.run_fixture(modules, ['--all', '--group', 'source'], groups)
        self.assertEqual(code, 0, text)
        self.assertIn('selected=1 run=1', text)
        self.assertIn('MAP COVERAGE passed=0 selected=0; NOT REQUESTED', text)

    def test_fail_error_skip_expected_and_unexpected_have_explicit_counts(self):
        source = '''import unittest
class Cases(unittest.TestCase):
 def test_pass(self): pass
 def test_fail(self): self.fail('deliberate')
 def test_error(self): raise RuntimeError('deliberate')
 @unittest.skip('deliberate skip')
 def test_skip(self): pass
 @unittest.expectedFailure
 def test_expected(self): self.fail('expected')
 @unittest.expectedFailure
 def test_unexpected(self): pass
'''
        code, text = self.run_fixture({'test_stub': source}, ['--all'])
        self.assertEqual(code, 1, text)
        self.assertIn('run=6 passed=1 failures=1 errors=1 skipped=1 expected_failures=1 unexpected_successes=1', text)
        self.assertIn('deliberate skip', text)

    def test_subtest_failure_cannot_be_reported_as_pass(self):
        source = 'import unittest\nclass Cases(unittest.TestCase):\n def test_sub(self):\n  with self.subTest(case=1): self.fail("bad")\n'
        code, text = self.run_fixture({'test_stub': source}, ['--all'])
        self.assertEqual(code, 1, text)
        self.assertIn('run=1 passed=0 failures=1', text)
        self.assertIn('FAIL [source]', text)

    def test_class_setup_error_and_skip_are_reported_even_without_test_start(self):
        for operation, expected, code in [('raise RuntimeError("broken setup")', 'errors=1 skipped=0', 1), ('raise unittest.SkipTest("missing fixture")', 'errors=0 skipped=1', 0)]:
            source = 'import unittest\nclass Cases(unittest.TestCase):\n @classmethod\n def setUpClass(cls): '+operation+'\n def test_ok(self): pass\n'
            actual, text = self.run_fixture({'test_stub': source}, ['--all'])
            self.assertEqual(actual, code, text)
            self.assertIn('run=0 passed=0', text)
            self.assertIn(expected, text)
            self.assertIn('FIXTURE ', text)
            self.assertIn('Cases.setUpClass', text)

    def test_import_error_unknown_member_and_empty_selection_are_nonzero(self):
        code, text = self.run_fixture({'test_stub': 'raise ImportError("missing dependency")'}, ['--all'])
        self.assertEqual(code, 1, text)
        self.assertIn('missing dependency', text)
        code, text = self.run_fixture({'test_stub': 'import unittest'}, ['test_stub.Missing'])
        self.assertEqual(code, 1, text)
        self.assertIn('errors=1', text)
        code, text = self.run_fixture({'test_stub': 'import unittest'}, ['--all'])
        self.assertEqual(code, 1, text)
        self.assertIn('Selection contains no tests', text)

    def test_unclassified_test_is_visible_not_run_even_with_group_filter(self):
        source = 'import unittest\nclass Unknown(unittest.TestCase):\n def test_bad(self): raise AssertionError("must not execute")\n'
        code, text = self.run_fixture({'test_stub': source}, ['--all', '--group', 'source'])
        self.assertEqual(code, 2, text)
        self.assertIn('NOT COVERED [unclassified]', text)
        self.assertIn('run=0 passed=0', text)
        self.assertIn('not_covered=1', text)

    def test_list_never_runs_fixtures_and_lists_unclassified(self):
        source = 'import unittest\nclass Unknown(unittest.TestCase):\n @classmethod\n def setUpClass(cls): raise AssertionError("no fixture")\n def test_ok(self): pass\n'
        code, text = self.run_fixture({'test_stub': source}, ['--all', '--list'])
        self.assertEqual(code, 0, text)
        self.assertIn('[unclassified] test_stub.Unknown.test_ok', text)
        self.assertNotIn('no fixture', text)

    def test_shared_setup_teardown_and_test_timings_are_separate(self):
        source = '''import time, unittest
def setUpModule(): time.sleep(.002)
def tearDownModule(): pass
class Cases(unittest.TestCase):
 @classmethod
 def setUpClass(cls): time.sleep(.002)
 @classmethod
 def tearDownClass(cls): pass
 def test_ok(self): time.sleep(.001)
'''
        code, text = self.run_fixture({'test_stub': source}, ['--all'])
        self.assertEqual(code, 0, text)
        for label in ('PREP ', 'TEST ', 'FIXTURE ', 'SLOWEST 10', 'setUpModule', 'tearDownModule', 'setUpClass', 'tearDownClass'):
            self.assertIn(label, text)

    def test_map_requires_cli_input_even_if_old_environment_is_set(self):
        source = 'import unittest\nclass Cases(unittest.TestCase):\n def test_bad(self): raise AssertionError("must not execute")\n'
        with patch.dict(os.environ, {name: str(ROOT / 'ExampleMap.w3x') for name in runner.MAP_ENV}):
            code, text = self.run_fixture({'test_stub': source}, ['--all'], {'map': ['test_stub.Cases']})
        self.assertEqual(code, 2, text)
        self.assertIn('actual map requires explicit --candidate-map', text)
        self.assertIn('run=0', text)
        self.assertIn('not_covered=1', text)

    def test_same_explicit_candidate_reaches_every_existing_environment_interface(self):
        source = '''import hashlib, os, unittest
from pathlib import Path
class Cases(unittest.TestCase):
 def test_input(self):
  names = ('PYTHON_CANDIDATE_MAP', 'TRIAL_CANDIDATE_MAP', 'EQUIPMENT_CANDIDATE_MAP', 'HOTPATH_CANDIDATE_MAP', 'PURE_BOSS_CANDIDATE_MAP', 'W3C_ACTIVE_COOLDOWN_MAP', 'COMBINED_CANDIDATE_MAP')
  paths = {os.environ[name] for name in names}
  self.assertEqual(len(paths), 1)
  data = Path(paths.pop()).read_bytes()
  self.assertEqual(data, b'unique stub map')
  self.assertEqual(hashlib.sha256(data).hexdigest(), os.environ['TRIAL_CANDIDATE_MAP_SHA256'])
  self.assertEqual(os.environ['PURE_BOSS_BASELINE_SOURCE'], 'separate historical baseline')
  self.assertEqual(os.environ['COMBINED_PARENT_MAP'], 'separate real parent')
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.w3x'; path.write_bytes(b'unique stub map')
            with patch.dict(os.environ, {'PURE_BOSS_BASELINE_SOURCE': 'separate historical baseline', 'COMBINED_PARENT_MAP': 'separate real parent'}):
                code, text = self.run_fixture({'test_stub': source}, ['--all', '--candidate-map', str(path)], {'map': ['test_stub.Cases']})
        self.assertEqual(code, 0, text)
        self.assertIn('MAP COVERAGE passed=1 selected=1', text)

    def test_invalid_or_wrong_digest_candidate_never_runs_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.w3x'; path.write_bytes(b'stub')
            for args in (['--candidate-map', str(path / 'absent')], ['--candidate-map', directory], ['--candidate-map', str(path), '--candidate-sha256', '0' * 64]):
                code, text = self.run_fixture({'test_stub': ''}, ['--all', *args])
                self.assertEqual(code, 2, text)
                self.assertIn('INPUT ERROR', text)

    def test_changed_candidate_fails_after_tests(self):
        source = 'import os, unittest\nfrom pathlib import Path\nclass Cases(unittest.TestCase):\n def test_mutation(self): Path(os.environ["PYTHON_CANDIDATE_MAP"]).write_bytes(b"changed")\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.w3x'; path.write_bytes(b'stub')
            code, text = self.run_fixture({'test_stub': source}, ['--all', '--candidate-map', str(path)], {'map': ['test_stub.Cases']})
        self.assertEqual(code, 1, text)
        self.assertIn('Candidate bytes changed during tests', text)

    def test_deleted_candidate_is_a_reported_error_not_an_uncaught_exception(self):
        source = 'import os, unittest\nfrom pathlib import Path\nclass Cases(unittest.TestCase):\n def test_delete(self): Path(os.environ["PYTHON_CANDIDATE_MAP"]).unlink()\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.w3x'; path.write_bytes(b'stub')
            code, text = self.run_fixture({'test_stub': source}, ['--all', '--candidate-map', str(path)], {'map': ['test_stub.Cases']})
        self.assertEqual(code, 1, text)
        self.assertIn('INPUT ERROR', text)
        self.assertIn('STATUS FAILED', text)

    def test_missing_extra_map_evidence_is_not_silently_ignored(self):
        source = 'import unittest\nclass PureBossActualCompiledTests(unittest.TestCase):\n def test_actual_same_source_compiled_hook_harness(self): raise AssertionError("must not run")\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.w3x'; path.write_bytes(b'stub')
            with patch.dict(os.environ, {'PURE_BOSS_HOOK_HARNESS_MAP': ''}):
                code, text = self.run_fixture({'test_stub': source}, ['--all', '--candidate-map', str(path)], {'map': ['test_stub.PureBossActualCompiledTests']})
        self.assertEqual(code, 2, text)
        self.assertIn('missing additional evidence: PURE_BOSS_HOOK_HARNESS_MAP', text)
        self.assertIn('STATUS INCOMPLETE', text)

    def test_skipped_map_is_incomplete_nonzero(self):
        source = 'import unittest\nclass Cases(unittest.TestCase):\n @unittest.skip("missing extra evidence")\n def test_skip(self): pass\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.w3x'; path.write_bytes(b'stub')
            code, text = self.run_fixture({'test_stub': source}, ['--all', '--candidate-map', str(path)], {'map': ['test_stub.Cases']})
        self.assertEqual(code, 2, text)
        self.assertIn('skipped=1', text)
        self.assertIn('MAP COVERAGE passed=0 selected=1', text)

    def test_direct_unittest_all_legacy_readers_skip_without_candidate(self):
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in CURRENT_MAP_READERS)
        with patch.dict(os.environ, {name: '' for name in runner.MAP_ENV}):
            result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        self.assertEqual(len(result.skipped), len(CURRENT_MAP_READERS))
        self.assertEqual(result.errors, [])
        self.assertEqual(result.failures, [])
        self.assertTrue(all('NOT COVERED' in reason for _, reason in result.skipped))

    def test_direct_unittest_each_legacy_reader_rejects_missing_explicit_path_not_root(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'unique-absent-candidate.w3x')
            for name in CURRENT_MAP_READERS:
                with self.subTest(reader=name), patch.dict(os.environ, {name: path for name in runner.MAP_ENV}):
                    suite = unittest.defaultTestLoader.loadTestsFromName(name)
                    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
                    self.assertEqual(len(result.errors), 1, (name, result.errors))
                    self.assertIn('unique-absent-candidate.w3x', result.errors[0][1])
                    self.assertEqual(result.skipped, [])

    def test_direct_trial_tests_no_longer_pass_with_missing_input(self):
        names = [name for name, group in runner.METHOD_GROUPS.items() if name.startswith('test_trial_replay.') and group == 'map']
        suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in names)
        with patch.dict(os.environ, {'TRIAL_CANDIDATE_MAP': ''}):
            result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        self.assertEqual(len(result.skipped), 4)
        self.assertEqual(result.errors, [])

    def test_cd_categories_and_mixed_bloodlust_method_follow_actual_inputs(self):
        expected = {
            'ActiveSourceContractTests': 'source', 'ProductionNativeStateTests': 'source',
            'SyntheticPackagedObjectMutationTests': 'regression', 'SyntheticCompiledMutationTests': 'regression',
        }
        for owner, group in expected.items():
            suite = unittest.defaultTestLoader.loadTestsFromName('test_active_cooldown_contract.' + owner)
            tests = list(runner.flatten(suite))
            self.assertTrue(tests)
            self.assertEqual({runner.group_for(test) for test in tests}, {group}, owner)
        suite = unittest.defaultTestLoader.loadTestsFromName(
            'test_verify_bloodlust_autocast_artifact.BloodlustStaticSourceTests')
        for test in runner.flatten(suite):
            expected = 'map' if test._testMethodName == 'test_bladestorm_native_effects_and_evolution_remain_preserved' else 'source'
            self.assertEqual(runner.group_for(test), expected, test.id())

    def test_cd_direct_unittest_keeps_its_explicit_environment_without_generic_fallback(self):
        name = 'test_verify_bloodlust_autocast_artifact.BloodlustActualNewArtifactTests.test_actual_new_packaged_choice_matrix_lifecycle_and_tooltips'
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'cd-explicit-absent.w3x')
            environment = {key: '' for key in runner.MAP_ENV}
            environment['W3C_ACTIVE_COOLDOWN_MAP'] = path
            with patch.dict(os.environ, environment):
                result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName(name))
            self.assertEqual(len(result.errors), 1)
            self.assertIn('cd-explicit-absent.w3x', result.errors[0][1])
            environment['W3C_ACTIVE_COOLDOWN_MAP'] = ''
            environment['PYTHON_CANDIDATE_MAP'] = str(ROOT / 'ExampleMap.w3x')
            with patch.dict(os.environ, environment):
                result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName(name))
            self.assertEqual(len(result.skipped), 1)
            self.assertEqual(result.errors, [])
            self.assertIn('W3C_ACTIVE_COOLDOWN_MAP', result.skipped[0][1])

    def test_combined_parent_remains_separate_required_evidence(self):
        source = 'import unittest\nclass Combined(unittest.TestCase):\n def test_objects(self): raise AssertionError("must not run")\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'candidate.w3x'; path.write_bytes(b'stub')
            with patch.dict(runner.CLASS_MAP_INPUTS, {'test_stub.Combined': ('COMBINED_PARENT_MAP',)}), patch.dict(os.environ, {'COMBINED_PARENT_MAP': ''}):
                code, text = self.run_fixture({'test_stub': source}, ['--all', '--candidate-map', str(path)], {'map': ['test_stub.Combined']})
        self.assertEqual(code, 2, text)
        self.assertIn('missing additional evidence: COMBINED_PARENT_MAP', text)
        self.assertIn('run=0', text)
        self.assertIn('STATUS INCOMPLETE', text)

    def test_integrated_new_classes_have_explicit_input_categories(self):
        expected = {
            'test_aura_target_artifact.AuraTargetArtifactTests': 'map',
            'test_combined_visual_text_artifact.CombinedSourceTextTests': 'source',
            'test_combined_visual_text_artifact.ActualCombinedFieldTests': 'map',
            'test_ground_upgrade_sort_source.GroundUpgradeSortSourceTests': 'source',
            'test_ground_upgrade_sort_source.GroundUpgradeEntryOwnerMutationTests': 'source',
            'test_ground_upgrade_sort_source.GroundUpgradeCooldownOwnerTests': 'source',
            'test_player_selected_item_description.SelectedItemDescriptionSourceTests': 'source',
            'test_king_leoric_assets.AssetTests': 'regression',
        }
        for owner, group in expected.items():
            tests = list(runner.flatten(unittest.defaultTestLoader.loadTestsFromName(owner)))
            self.assertTrue(tests)
            self.assertEqual({runner.group_for(test) for test in tests}, {group}, owner)

    def test_cli_exit_code_and_real_small_module(self):
        command = [sys.executable, str(ROOT / 'tools/Run-PythonChecks.py')]
        result = subprocess.run(command + ['test_pet_deployment_artifact.ScalarSubsetTests'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('run=5 passed=5', result.stdout)
        result = subprocess.run(command + ['test_pet_skill_fits_artifact.PetSkillFitsArtifactTests'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('not_covered=1', result.stdout)


if __name__ == '__main__':
    unittest.main()
