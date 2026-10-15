"""Synthetic result-journal/comparison regressions; no real map acceptance."""
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import ComparePythonCheckResults as comparison
spec = importlib.util.spec_from_file_location('python_checks_result_test_runner', ROOT / 'tools/Run-PythonChecks.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class PythonCheckResultTests(unittest.TestCase):
    def run_fixture(self, source, groups=None, arguments=(), setup=None):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / 'test_result_stub.py').write_text(source)
            report = home / 'results.json'
            artifact = home / 'synthetic-input.w3x'
            artifact.write_bytes(b'synthetic runner input, not an MPQ')
            output = io.StringIO()
            sys.modules.pop('test_result_stub', None)
            try:
                with patch.object(runner, 'TEST_DIR', home), patch.object(runner, 'CLASS_GROUPS', groups or {'regression': ['test_result_stub.Cases']}), patch.object(runner, 'METHOD_GROUPS', {}), patch.dict(os.environ, {'RESULT_TEST_OUTPUT': str(report)}), redirect_stdout(output):
                    if setup:
                        setup(home, report)
                    code = runner.main(['test_result_stub', '--results-json', str(report), *arguments])
            finally:
                sys.modules.pop('test_result_stub', None)
            return code, json.loads(report.read_text()), output.getvalue()

    def reports(self):
        source = 'import unittest\nclass Cases(unittest.TestCase):\n def test_ok(self): pass\n'
        code, baseline, _ = self.run_fixture(source)
        self.assertEqual(code, 0)
        baseline['run_label'] = 'baseline'
        baseline['artifact'] = {'path': 'synthetic-baseline.w3x', 'sha256': 'a' * 64}
        candidate = deepcopy(baseline)
        candidate['run_label'] = 'candidate'
        candidate['artifact'] = {'path': 'synthetic-candidate.w3x', 'sha256': 'b' * 64}
        return baseline, candidate

    def failed(self, report, message='new failure'):
        report['methods'][0].update(outcome='FAIL', exceptions=[dict(type='builtins.AssertionError', message=message, traceback='AssertionError: ' + message)])
        report['summary'].update(passed=0, failures=1)
        report.update(status='FAILED', exit_code=1)

    def compare(self, baseline, candidate):
        return comparison.compare_reports(baseline, candidate, baseline['verification_manifest'])

    def test_records_all_method_outcomes_exact_exception_text_and_subtest_errors(self):
        source = '''import unittest
class Cases(unittest.TestCase):
 def test_pass(self): pass
 def test_fail(self): self.fail('precise failure text')
 def test_error(self): raise ValueError('precise error text')
 @unittest.skip('precise skip reason')
 def test_skip(self): pass
 @unittest.expectedFailure
 def test_expected(self): self.fail('expected failure text')
 @unittest.expectedFailure
 def test_unexpected(self): pass
 def test_subtests(self):
  with self.subTest(value=1): raise ValueError('first subtest error')
  with self.subTest(value=2): self.fail('second subtest failure')
'''
        code, report, output = self.run_fixture(source)
        self.assertEqual(code, 1)
        self.assertTrue(report['terminal'])
        self.assertEqual(report['exit_code'], code)
        rows = {row['id'].rsplit('.', 1)[-1]: row for row in report['methods']}
        self.assertEqual({key: row['outcome'] for key, row in rows.items()}, dict(test_pass='PASS', test_fail='FAIL', test_error='ERROR', test_skip='SKIP', test_expected='EXPECTED_FAILURE', test_unexpected='UNEXPECTED_SUCCESS', test_subtests='ERROR'))
        self.assertIn('precise failure text', rows['test_fail']['exceptions'][0]['traceback'])
        self.assertEqual(rows['test_skip']['reason'], 'precise skip reason')
        self.assertEqual([event['outcome'] for event in rows['test_subtests']['subtests']], ['ERROR', 'FAIL'])
        self.assertTrue(all(row['executed'] for row in rows.values()))
        self.assertIn('START [regression]', output)
        self.assertIn('tools/Run-PythonChecks.py', report['verification_manifest'])

    def test_unclassified_and_missing_map_remain_not_covered_not_skipped(self):
        source = '''import unittest
class MapCases(unittest.TestCase):
 def test_map(self): raise AssertionError('must not execute')
class Unknown(unittest.TestCase):
 def test_unknown(self): raise AssertionError('must not execute')
'''
        code, report, _ = self.run_fixture(source, {'map': ['test_result_stub.MapCases']})
        self.assertEqual(code, 2)
        self.assertEqual(report['summary']['not_covered'], 2)
        self.assertEqual(report['summary']['skipped'], 0)
        self.assertEqual({row['outcome'] for row in report['methods']}, {'NOT_COVERED'})
        self.assertTrue(all(not row['executed'] for row in report['methods']))

    def test_fixture_errors_and_fixture_skips_bind_every_blocked_method(self):
        for operation, expected, code in (('raise RuntimeError("fixture precise error")', 'FIXTURE_ERROR', 1),
                                          ('raise unittest.SkipTest("fixture precise skip")', 'FIXTURE_SKIP', 0)):
            source = 'import unittest\nclass Cases(unittest.TestCase):\n @classmethod\n def setUpClass(cls): ' + operation + '\n def test_a(self): pass\n def test_b(self): pass\n'
            with self.subTest(operation=operation):
                actual, report, _ = self.run_fixture(source)
                self.assertEqual(actual, code)
                self.assertEqual(report['summary']['run'], 0)
                self.assertEqual({row['outcome'] for row in report['methods']}, {expected})
                self.assertEqual(len(report['fixtures']), 1)
                if expected == 'FIXTURE_ERROR':
                    self.assertIn('fixture precise error', report['methods'][0]['exceptions'][0]['traceback'])

    def test_nonterminal_placeholder_is_visible_before_a_test_finishes(self):
        source = '''import json, os, unittest
from pathlib import Path
class Cases(unittest.TestCase):
 def test_running(self):
  report = json.loads(Path(os.environ['RESULT_TEST_OUTPUT']).read_text())
  self.assertFalse(report['terminal'])
  self.assertIsNone(report['exit_code'])
'''
        code, report, _ = self.run_fixture(source)
        self.assertEqual(code, 0)
        self.assertTrue(report['terminal'])

    def test_verifier_source_change_during_run_is_a_reported_error(self):
        source = '''import unittest
from pathlib import Path
class Cases(unittest.TestCase):
 def test_mutate(self):
  path = Path(__file__)
  path.write_text(path.read_text() + '\\n# changed fixture source\\n')
'''
        code, report, _ = self.run_fixture(source)
        self.assertEqual(code, 1)
        self.assertIn('Python verifier/test inputs changed during tests', report['issues'])
        self.assertIn('verification_manifest_after', report)

    def test_final_report_write_failure_is_nonzero_and_keeps_nonterminal_placeholder(self):
        original = runner.write_results_json
        calls = []
        def fail_final(path, document):
            calls.append(document['terminal'])
            if document['terminal']:
                raise OSError('precise final write failure')
            original(path, document)
        with patch.object(runner, 'write_results_json', side_effect=fail_final):
            code, report, output = self.run_fixture('import unittest\nclass Cases(unittest.TestCase):\n def test_ok(self): pass\n')
        self.assertEqual(code, 1)
        self.assertEqual(calls, [False, True])
        self.assertFalse(report['terminal'])
        self.assertIn('STATUS FAILED (results recording error)', output)

    def test_teardown_fixture_failure_does_not_overwrite_method_success(self):
        source = '''import unittest
class Cases(unittest.TestCase):
 def test_ok(self): pass
 @classmethod
 def tearDownClass(cls): raise RuntimeError('precise teardown failure')
'''
        code, report, _ = self.run_fixture(source)
        self.assertEqual(code, 1)
        self.assertEqual(report['methods'][0]['outcome'], 'PASS')
        self.assertEqual(report['fixtures'][0]['outcome'], 'ERROR')
        self.assertIn('precise teardown failure', report['fixtures'][0]['exception']['traceback'])

    def test_discovery_exception_keeps_full_text_and_failed_terminal_status(self):
        code, report, _ = self.run_fixture('raise RuntimeError("precise import failure")\n')
        self.assertEqual(code, 1)
        self.assertEqual(report['status'], 'FAILED')
        self.assertIn('precise import failure', report['discovery_errors'][0]['traceback'])
        self.assertEqual(report['summary']['selected'], 0)

    def test_comparison_lists_new_persistent_and_resolved_failures_without_green_claim(self):
        baseline, candidate = self.reports()
        self.failed(candidate)
        result = self.compare(baseline, candidate)
        self.assertTrue(result['comparable'])
        self.assertEqual(result['exit_code'], 1)
        self.assertEqual(result['new_failures'], [candidate['methods'][0]['id']])
        baseline['methods'] = deepcopy(candidate['methods'])
        baseline['summary'] = deepcopy(candidate['summary'])
        baseline.update(status='FAILED', exit_code=1)
        result = self.compare(baseline, candidate)
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(len(result['persistent_failures']), 1)
        self.assertEqual(result['candidate']['exit_code'], 1)
        self.assertNotIn('PASS', result['status'])
        candidate['methods'][0].update(outcome='PASS', exceptions=[])
        candidate['summary'].update(passed=1, failures=0)
        candidate.update(status='PASSED_SELECTED', exit_code=0)
        self.assertEqual(len(self.compare(baseline, candidate)['resolved_failures']), 1)

    def test_fail_to_skip_is_coverage_loss_and_never_a_resolved_failure(self):
        baseline, candidate = self.reports()
        self.failed(baseline)
        candidate['methods'][0].update(outcome='SKIP', reason='withheld evidence')
        candidate['summary'].update(passed=0, skipped=1)
        result = self.compare(baseline, candidate)
        self.assertEqual(result['exit_code'], 2)
        self.assertEqual(result['resolved_failures'], [])
        self.assertEqual(len(result['coverage_loss']), 1)

    def test_changed_exception_on_existing_failure_is_a_new_failure(self):
        baseline, candidate = self.reports()
        self.failed(baseline, 'missing old function')
        self.failed(candidate, 'new broken invariant')
        result = self.compare(baseline, candidate)
        self.assertEqual(len(result['new_failures']), 1)
        self.assertEqual(result['changed_methods'][0]['baseline']['exceptions'][0]['message'], 'missing old function')

    def test_added_deleted_regrouped_methods_and_source_sha_mismatch_are_incomparable(self):
        baseline, candidate = self.reports()
        old = candidate['methods'][0]['id']
        candidate['methods'][0]['id'] = 'test_result_stub.Cases.test_new'
        candidate['selection']['methods'][0]['id'] = candidate['methods'][0]['id']
        result = self.compare(baseline, candidate)
        self.assertFalse(result['comparable'])
        self.assertEqual(result['deleted_methods'], [old])
        self.assertEqual(len(result['added_methods']), 1)
        baseline, candidate = self.reports()
        candidate['methods'][0]['group'] = 'source'
        candidate['selection']['methods'][0]['group'] = 'source'
        self.assertEqual(len(self.compare(baseline, candidate)['changed_groups']), 1)
        baseline, candidate = self.reports()
        candidate['verification_manifest']['tools/Run-PythonChecks.py'] = '0' * 64
        result = self.compare(baseline, candidate)
        self.assertEqual(result['exit_code'], 2)
        self.assertIn('Final runner/verifier/test SHA manifests differ', result['reasons'])

    def test_comparison_rejects_unconfirmed_or_forged_identity_inputs(self):
        for mutation in ('nonterminal', 'duplicate', 'unknown_outcome', 'missing_exception', 'wrong_exit', 'wrong_label', 'missing_artifact', 'different_request', 'different_disk'):
            baseline, candidate = self.reports()
            disk = baseline['verification_manifest']
            if mutation == 'nonterminal': candidate['terminal'] = False
            if mutation == 'duplicate': candidate['methods'].append(deepcopy(candidate['methods'][0]))
            if mutation == 'unknown_outcome': candidate['methods'][0]['outcome'] = 'MAGIC_PASS'
            if mutation == 'missing_exception': candidate['methods'][0]['exceptions'] = [{'message': 'lost traceback'}]
            if mutation == 'wrong_exit': candidate['exit_code'] = 1
            if mutation == 'wrong_label': candidate['run_label'] = 'baseline'
            if mutation == 'missing_artifact': candidate['artifact']['sha256'] = None
            if mutation == 'different_request': candidate['selection']['requested']['groups'] = ['source']
            if mutation == 'different_disk': disk = {**disk, 'tools/extra.py': '0' * 64}
            with self.subTest(mutation=mutation):
                try:
                    result = comparison.compare_reports(baseline, candidate, disk)
                except ValueError:
                    self.assertIn(mutation, ('nonterminal', 'duplicate', 'unknown_outcome', 'missing_exception', 'wrong_exit'))
                else:
                    self.assertFalse(result['comparable'])
                    self.assertEqual(result['exit_code'], 2)

    def test_cli_writes_and_compares_same_final_inputs_with_explicit_synthetic_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            reports = []
            for role in ('baseline', 'candidate'):
                artifact = home / (role + '.w3x')
                artifact.write_bytes(('synthetic ' + role + ', not MPQ').encode())
                report = home / (role + '.json')
                reports.append(report)
                command = [sys.executable, '-u', str(ROOT / 'tools/Run-PythonChecks.py'),
                           'test_inventory_craft_control_flow.InventoryCraftControlFlowTests.test_cf03_active_unknown_scalar_is_rejected',
                           '--group', 'regression', '--candidate-map', str(artifact), '--run-label', role, '--results-json', str(report)]
                result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = home / 'comparison.json'
            result = subprocess.run([sys.executable, '-u', str(ROOT / 'tools/ComparePythonCheckResults.py'),
                                     '--baseline', str(reports[0]), '--candidate', str(reports[1]), '--output-json', str(output)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            document = json.loads(output.read_text())
            self.assertTrue(document['comparable'])
            self.assertEqual(document['status'], 'COMPARABLE_NO_NEW_FAILURES')
            self.assertFalse(document['same_artifact'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
