"""Narrow deployment-gate artifact and fail-closed scalar-subset regressions."""
from pathlib import Path
import re
import sys
import unittest
from python_check_inputs import candidate_map

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyPetDeploymentArtifact import packaged_script, run_gate, verify_gate
from VerifyPetUIArtifact import _integer_expression, _run_scalar_helper, jass_function

DEBUG_SCALAR = '''function scalar takes integer pet, string w__wurst_stackPos returns boolean
    set wurst_stack[wurst_stack_depth] = w__wurst_stackPos
    set wurst_stack_depth = wurst_stack_depth + 1
    if pet == 0 or released[pet] then
        set wurst_stack_depth = wurst_stack_depth - 1
        return false
    endif
    set wurst_stack_depth = wurst_stack_depth - 1
    return check("controlled dependency")
endfunction
'''


class ScalarSubsetTests(unittest.TestCase):
    def run_scalar(self, script=DEBUG_SCALAR, pet=1):
        return _run_scalar_helper(jass_function(script, 'scalar'), (pet, 'fixture'),
                                  {'released': {1: False, 2: True}},
                                  {'check': lambda text: text == 'controlled dependency'},
                                  debug_stack=True)

    def test_array_reads_strings_and_exact_balanced_stack(self):
        self.assertIs(self.run_scalar(), True)
        self.assertIs(self.run_scalar(pet=2), False)

    def test_null_guard_short_circuits_before_missing_record_read(self):
        self.assertIs(self.run_scalar(pet=0), False)
        self.assertIs(_integer_expression('false and missing[9]', {'false': False}), False)

    def test_missing_or_noninteger_array_reads_fail_closed(self):
        for expression in ('released[9]', 'released["x"]', 'missing[1]'):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                _integer_expression(expression, {'released': {1: False}})

    def test_unknown_function_statement_or_assignment_fails_closed(self):
        for old, new in [('check("controlled dependency")', 'unknown("controlled dependency")'),
                         ('return check', 'call UnknownNative()\n    return check'),
                         ('return check', 'set unknown = 1\n    return check')]:
            with self.subTest(replacement=new), self.assertRaises(ValueError):
                self.run_scalar(DEBUG_SCALAR.replace(old, new))

    def test_unrecognized_or_unbalanced_debug_stack_fails_closed(self):
        for old, new in [
            ('= w__wurst_stackPos', '= "unexpected"'),
            ('wurst_stack_depth + 1', 'wurst_stack_depth + 2'),
            ('set wurst_stack_depth = wurst_stack_depth - 1', ''),
        ]:
            with self.subTest(replacement=new), self.assertRaises(ValueError):
                self.run_scalar(DEBUG_SCALAR.replace(old, new))


class ActualDeploymentGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = packaged_script(candidate_map())

    def test_real_packaged_gate_counts_guards_and_rebind(self):
        verify_gate(self.script)

    def test_restoring_three_pet_total_cap_is_detected(self):
        match = jass_function(self.script, 'tdPetCanDeploy')
        pet = re.search(r'takes integer (\w+)', match.group(0)).group(1)
        body = match.group(1)
        self.assertIn('return true', body)
        changed = body.replace('return true',
                               f'return tdPetDeployedCount(TDPet_lane[{pet}]) < 3')
        script = self.script[:match.start(1)] + changed + self.script[match.end(1):]
        self.assertIs(run_gate(self.script, 3)[0], True)
        self.assertIs(run_gate(script, 3)[0], False)
        with self.assertRaisesRegex(ValueError, 'still consults a lane-wide count dependency'):
            verify_gate(script)


if __name__ == '__main__':
    unittest.main(verbosity=2)
