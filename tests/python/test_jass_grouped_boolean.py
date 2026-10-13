"""Grouped JASS booleans are safe; ambiguous precedence still fails closed."""
import itertools
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from VerifyTowerUpgradeArtifact import JassScalarEvaluator, jass_boolean_groups_explicit
from VerifyActiveCooldownContract import ActiveJassRuntime


class GroupedJassBooleanTests(unittest.TestCase):
    def test_explicit_groups_match_independent_truth_tables(self):
        script = '''globals
endglobals
function grouped takes boolean a, boolean b, boolean c, boolean d returns boolean
    return (a and b) or (c and d)
endfunction
function nested takes boolean a, boolean b, boolean c, boolean d returns boolean
    return a and (b or c) and d
endfunction
'''
        for runtime in (JassScalarEvaluator(script), ActiveJassRuntime(script)):
            for args in itertools.product((False, True), repeat=4):
                self.assertEqual(runtime.call('grouped', list(args)), (args[0] and args[1]) or (args[2] and args[3]))
                self.assertEqual(runtime.call('nested', list(args)), args[0] and (args[1] or args[2]) and args[3])

    def test_two_nested_spirit_guards_preserve_all_boolean_inputs(self):
        for a, b, c, d in itertools.product((False, True), repeat=4):
            # Candidate admission: allowed, quality, other-slot, same-group.
            before = a and b and (c or d)
            after = False
            if a and b:
                if c or d:
                    after = True
            self.assertEqual(before, after)
            # Detail buff: same-owner, skill11, skill12, before-deadline.
            before = a and (b or c) and d
            after = False
            if a:
                if b or c:
                    if d:
                        after = True
            self.assertEqual(before, after)

    def test_ungrouped_and_partially_grouped_mixed_operators_remain_rejected(self):
        for expression in ('a and b or c', 'a or b and c', '(a and b or c)', 'a and (b or c and d)'):
            self.assertFalse(jass_boolean_groups_explicit(expression))
            script = 'globals\nendglobals\nfunction bad takes boolean a, boolean b, boolean c, boolean d returns boolean\n    return '+expression+'\nendfunction\n'
            for runtime in (JassScalarEvaluator(script), ActiveJassRuntime(script)):
                with self.assertRaisesRegex(ValueError, 'Mixed Jass and/or'):
                    runtime.call('bad', [True, False, True, False])

    def test_arguments_quotes_arithmetic_and_identifiers_do_not_forge_groups(self):
        self.assertTrue(jass_boolean_groups_explicit('f(a and b, c or d)'))
        self.assertTrue(jass_boolean_groups_explicit('f("a and b or c", commander)'))
        self.assertFalse(jass_boolean_groups_explicit('(a and b'))
        self.assertFalse(jass_boolean_groups_explicit('a and b)'))
        script = '''globals
endglobals
function arithmetic takes integer a, integer b, integer c returns boolean
    return (a + b * c > 12 and a < b) or (c == 4 and b - a == 2)
endfunction
'''
        for runtime in (JassScalarEvaluator(script), ActiveJassRuntime(script)):
            self.assertTrue(runtime.call('arithmetic', [2, 4, 4]))
            self.assertFalse(runtime.call('arithmetic', [4, 2, 1]))


if __name__ == '__main__':
    unittest.main()
