"""Target-priority source/tool negatives; real-map positives require explicit input."""
from pathlib import Path
import sys
import unittest
from python_check_inputs import candidate_map

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyTowerTargetPriorityArtifact as gate


class TowerTargetPrioritySourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = gate.source_files(ROOT / 'wurst')

    def test_unique_attacked_and_sparse_source_contract(self):
        report = gate.verify_source_contract(self.sources)
        self.assertTrue(report['unique_attacked_wrapper'])
        self.assertEqual(report['local_selector_count'], 1)
        self.assertEqual(report['shared_recovery_timer_count'], 1)

    def test_real_source_scalar_rules_absolute_hp_and_strict_ties(self):
        namespace = gate.source_scalar_namespace(self.sources)
        report = gate.verify_rules(lambda name, *args: namespace[name](*args))
        self.assertEqual(report['comparator_cases'], 2304)
        self.assertEqual(report['family_policies'], [1, 2, 2, 1, 2])


    def test_retired_route_priority_has_no_active_source_symbols(self):
        report=gate.verify_source_contract(self.sources)
        self.assertFalse(report['route_progress_or_speed_priority'])
        with self.assertRaisesRegex(ValueError,'Retired route interception'):
            changed=dict(self.sources)
            changed[gate.RULES] += '\npublic constant real TD_TARGET_PRIORITY_EMERGENCY_SECONDS = 3.0\n'
            gate.verify_source_contract(changed)

    def test_source_mutations_fail_closed(self):
        rejected = gate.verify_source_mutations(self.sources)
        self.assertGreaterEqual(len(rejected), 16)
        self.assertIn('queue before verdict', rejected)
        self.assertIn('recovery floor lost', rejected)

    def test_source_only_cannot_claim_an_actual_map(self):
        with self.assertRaisesRegex(ValueError, 'cannot also claim a map'):
            gate.verify_artifact(Path('/unused.w3x'), ROOT / 'wurst', source_only=True)

    def test_mutation_interpreter_faults_are_never_rejection_evidence(self):
        for error in (KeyError('missing function'), ValueError('unknown native'), ZeroDivisionError('bad fixture')):
            with self.assertRaisesRegex(ValueError, 'not rejection evidence'):
                gate.mutation_failure_evidence('fixture',error,['expected semantic assertion'])
        evidence=gate.mutation_failure_evidence('fixture',ValueError('expected semantic assertion'),
                                                ['expected semantic assertion'])
        self.assertEqual(evidence['exception_type'],'ValueError')
        self.assertEqual(evidence['reason'],'expected semantic assertion')

    def test_unverified_baseline_rejected_before_replay(self):
        with self.assertRaisesRegex(ValueError, 'explicitly verified formal'):
            gate.verify_baseline_no_selection('', '', '0' * 64)


    def test_jass_or_binds_above_and_per_group_and_argument(self):
        parse = gate.jass_boolean_expression
        self.assertEqual(parse('a and b or c'), '(a) and (b or c)')
        self.assertEqual(parse('a or b and c'), '(a or b) and (c)')
        self.assertEqual(parse('f(a and b or c, "and or", d or e and q)'),
                         'f((a) and (b or c), "and or",(d or e) and (q))')
        self.assertEqual(parse('(a and b) or c'), '(a and b) or c')
        for malformed in ('a(', 'a)'):
            with self.assertRaises(ValueError):
                parse(malformed)


class TowerTargetPriorityPackedTests(unittest.TestCase):
    def test_explicit_actual_mpq_transactions_and_mutations(self):
        report = gate.verify_artifact(candidate_map(), ROOT / 'wurst')
        self.assertEqual(report['status'], 'PASS')
        self.assertTrue(report['actual_mpq_executed'])
        self.assertEqual(len(report['packed_catalog_rawcodes']), 35)
        self.assertFalse(report['base_policy_without_route_override']['route_progress_or_speed_priority'])
        self.assertTrue(all(case['route_or_speed_reads']==0 for case in report['base_policy_without_route_override']['cases']))
        self.assertEqual(len(report['packed_mutations_rejected']),9)
        self.assertEqual(report['sparse_recovery']['parked_sources'], 40)
        self.assertEqual(report['sparse_recovery']['max_queries_per_tick'], 4)


if __name__ == '__main__':
    unittest.main()
