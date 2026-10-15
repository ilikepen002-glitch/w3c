"""CF01-CF05 exercise the shared production interpreter with synthetic JASS.

No map is loaded and no crafting/native behavior is inferred from these fixtures.
CF06 remains explicitly pending until this reimplementation has a newly built
candidate and its real packed inventory runtime can execute catalogReady twice.
"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyGroundUpgradeArtifact import GroundJassRuntime
from VerifyTowerUpgradeArtifact import JassScalarEvaluator


class InventoryCraftControlFlowTests(unittest.TestCase):
    def runtime(self, body):
        script = 'function probe takes nothing returns nothing\n' + body + '\nendfunction\n'
        # Skip map globals/catalog initialization, not the production call,
        # expression or native implementations that these cases are testing.
        runtime = object.__new__(GroundJassRuntime)
        JassScalarEvaluator.__init__(runtime, script)
        runtime.globals = {'observed': 0}
        return runtime

    def test_cf01_inactive_nested_loop_does_not_evaluate_unknown_scalar(self):
        runtime = self.runtime('''set observed = 1
if false then
    loop
        loop
            exitwhen UnknownScalar
            set observed = UnknownScalar
        endloop
        exitwhen UnknownScalar
    endloop
else
    set observed = 2
endif''')
        expressions = []
        expression = runtime.expression
        def observed_expression(text, scope):
            expressions.append(text)
            return expression(text, scope)
        runtime.expression = observed_expression
        runtime.call('probe', [])
        self.assertEqual(runtime.globals['observed'], 2)
        self.assertFalse(any('UnknownScalar' in text for text in expressions))

    def test_cf02_exitwhen_unwinds_two_inner_ifs_and_keeps_outer_if(self):
        runtime = self.runtime('''if true then
    loop
        if true then
            if true then
                exitwhen true
            endif
        endif
    endloop
    set observed = 2
else
    set observed = 3
endif''')
        runtime.call('probe', [])
        self.assertEqual(runtime.globals['observed'], 2)

    def test_cf03_active_unknown_scalar_is_rejected(self):
        for body in ('set observed = UnknownScalar',
                     'if UnknownScalar then\nset observed = 2\nendif',
                     'loop\nexitwhen UnknownScalar\nendloop'):
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, 'Unknown Jass scalar UnknownScalar'):
                self.runtime(body).call('probe', [])

    def test_cf04_unclosed_inactive_loop_is_rejected(self):
        runtime = self.runtime('''if false then
    loop
        loop
            set observed = UnknownScalar
        endloop''')
        with self.assertRaisesRegex(ValueError, 'unclosed packaged control flow'):
            runtime.call('probe', [])

    def test_cf05_infinite_loop_is_rejected_at_existing_step_cap(self):
        runtime = self.runtime('''loop
    set observed = observed + 1
    exitwhen false
endloop''')
        with self.assertRaisesRegex(ValueError, 'packaged loop did not terminate'):
            runtime.call('probe', [])
        self.assertGreater(runtime.globals['observed'], 0)

    @unittest.skip('PENDING CF06: requires the newly built candidate and its real packed inventory runtime; no baseline-map substitution')
    def test_cf06_real_packed_catalog_ready_repeated_call_pending_candidate(self):
        pass

    def test_nested_active_loop_exit_restores_only_its_own_context(self):
        runtime = self.runtime('''local integer count = 0
if true then
    loop
        exitwhen count == 3
        loop
            if true then
                set observed = observed + 1
                exitwhen true
            endif
        endloop
        set count = count + 1
    endloop
    set observed = observed + 2
endif''')
        runtime.call('probe', [])
        self.assertEqual(runtime.globals['observed'], 5)

    def test_active_unknown_native_remains_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'Missing packaged ground function UnknownNative'):
            self.runtime('call UnknownNative()').call('probe', [])

    def test_illegal_control_flow_is_rejected_even_in_inactive_code(self):
        bodies = ('else', 'elseif true then', 'endif', 'endloop', 'exitwhen true',
                  'if false then\nloop\nendif\nendloop',
                  'if false then\nelse\nelse\nendif',
                  'if false then\nelse\nelseif true then\nendif',
                  'if false then\nloop\nendif\nreturn')
        for body in bodies:
            with self.subTest(body=body), self.assertRaisesRegex(ValueError, 'illegal packaged control flow'):
                self.runtime(body).call('probe', [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
