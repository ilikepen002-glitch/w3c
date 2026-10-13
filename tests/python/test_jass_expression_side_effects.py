"""Interpreter semantics only: calls and later reads share live JASS globals."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from VerifyBossSpellResistanceArtifact import BossJassRuntime


class SideEffectRuntime(BossJassRuntime):
    def __init__(self):
        self.globals = {'count': 8, 'values': {0: 8}}

    def call(self, name, args):
        if name == 'resetCount':
            self.globals['count'] = 0
            return True
        if name == 'replaceArray':
            self.globals['values'] = {0: 0}
            return 0
        raise ValueError('Unexpected test call ' + name)


class JassExpressionSideEffectTests(unittest.TestCase):
    def test_same_expression_call_then_global_read_uses_updated_value(self):
        runtime = SideEffectRuntime()
        self.assertTrue(runtime.expression('resetCount() and count < 8', {}))
        self.assertEqual(runtime.globals['count'], 0)
        self.assertEqual(runtime.expression('values[replaceArray()]', {}), 0)

    def test_local_scalar_and_array_still_shadow_changed_globals(self):
        runtime = SideEffectRuntime()
        self.assertFalse(runtime.expression('resetCount() and count < 8', {'count': 8}))
        self.assertEqual(runtime.expression('values[replaceArray()]', {'values': {0: 9}}), 9)


if __name__ == '__main__':
    unittest.main(verbosity=2)
