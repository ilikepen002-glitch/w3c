"""Run the real packaged leak/death JASS with explicit native/runtime stubs.

This is offline compiled-script validation, not a Warcraft runtime playtest.
"""
import ast
from collections import defaultdict
import itertools
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq


def function(script, name):
    result = re.search(r'^function ' + re.escape(name) + r' takes (.*?) returns \w+\n(.*?)^endfunction', script, re.M | re.S)
    if not result:
        raise ValueError('Missing packaged function ' + name)
    return result


class Jass:
    """Strict interpreter for the straight-line/conditional functions under test."""
    def __init__(self, script, state, hooks):
        self.script, self.state, self.hooks = script, state, hooks

    def expression(self, text, local):
        if re.search(r'\band\b', text) and re.search(r'\bor\b', text):
            raise ValueError('Mixed boolean precedence: ' + text)
        def visit(n):
            if isinstance(n, ast.Constant):
                return n.value
            if isinstance(n, ast.Name):
                if n.id in local:
                    return local[n.id]
                return self.state[n.id]
            if isinstance(n, ast.Subscript):
                return visit(n.value)[visit(n.slice)]
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                args = [visit(a) for a in n.args]
                return self.hooks[n.func.id](*args) if n.func.id in self.hooks else self.run(n.func.id, args)
            if isinstance(n, ast.UnaryOp):
                if isinstance(n.op, ast.Not):
                    return not visit(n.operand)
                if isinstance(n.op, ast.USub):
                    return -visit(n.operand)
            if isinstance(n, ast.BinOp):
                a, b = visit(n.left), visit(n.right)
                if isinstance(n.op, ast.Add):
                    return a + b
                if isinstance(n.op, ast.Sub):
                    return a - b
            if isinstance(n, ast.BoolOp):
                return all(visit(v) for v in n.values) if isinstance(n.op, ast.And) else any(visit(v) for v in n.values)
            if isinstance(n, ast.Compare) and len(n.ops) == 1:
                a, b = visit(n.left), visit(n.comparators[0])
                for op, result in [(ast.Eq, lambda: a == b), (ast.NotEq, lambda: a != b),
                                   (ast.Lt, lambda: a < b), (ast.LtE, lambda: a <= b),
                                   (ast.Gt, lambda: a > b), (ast.GtE, lambda: a >= b)]:
                    if isinstance(n.ops[0], op):
                        return result()
            raise ValueError('Unsupported expression: ' + text)
        return visit(ast.parse(text.strip(), mode='eval').body)

    def run(self, name, args=()):
        found = function(self.script, name)
        params = re.findall(r'(?:integer|boolean|real|string|unit|player) (\w+)', found[1])
        if params and params[-1] == 'w__wurst_stackPos' and len(args) == len(params) - 1:
            args = [*args, 'offline test']
        if len(params) != len(args):
            raise ValueError('Argument mismatch: ' + name)
        local = dict(zip(params, args))
        active, branches = True, []
        for raw in found[2].splitlines():
            line = raw.strip()
            if not line or line.startswith('//') or line.startswith('set wurst_stack'):
                continue
            if line.startswith('local '):
                declaration = re.fullmatch(r'local (integer|boolean|real|string|unit|player) (\w+)(?: = (.*))?', line)
                if not declaration:
                    raise ValueError('Unsupported local: ' + line)
                kind, variable, value = declaration.groups()
                local[variable] = self.expression(value, local) if value else False if kind == 'boolean' else 0
            elif line.startswith('if ') and line.endswith(' then'):
                selected = active and bool(self.expression(line[3:-5], local))
                branches.append([active, selected]); active = selected
            elif line.startswith('elseif ') and line.endswith(' then'):
                parent, selected = branches[-1]
                active = parent and not selected and bool(self.expression(line[7:-5], local))
                branches[-1][1] = selected or active
            elif line == 'else':
                parent, selected = branches[-1]; active = parent and not selected; branches[-1][1] = True
            elif line == 'endif':
                active = branches.pop()[0]
            elif line.startswith('return'):
                if active:
                    return self.expression(line[7:], local) if line != 'return' else None
            elif line.startswith('call '):
                if active:
                    self.expression(line[5:], local)
            elif line.startswith('set '):
                if not active:
                    continue
                lhs, rhs = line[4:].split('=', 1)
                lhs = lhs.strip(); value = self.expression(rhs.strip(), local)
                array = re.fullmatch(r'(\w+)\[(.*)\]', lhs)
                if array:
                    self.state[array[1]][self.expression(array[2], local)] = value
                elif lhs in local:
                    local[lhs] = value
                else:
                    self.state[lhs] = value
            else:
                raise ValueError('Unsupported statement: ' + line)


class Harness:
    def __init__(self, script, lives=20):
        self.events = []
        self.units = {1: dict(alive=True, leaked=False, owner=4, wild=False, lane=0, wave=8, kind='boss'),
                      2: dict(alive=True, leaked=False, owner=4, wild=False, lane=0, wave=8, kind='boss')}
        self.active = [True, True, False, False]
        self.finished = [False] * 4; self.defeated = [False] * 4
        self.over = False; self.trigger = 1; self.reenter = False
        constants = {name: int(value) for name, value in re.findall(r'\bset (TDWaves_TD_WAVE_\w+_UNIT_ID) = (\d+)', script)}
        self.types = {'normal': constants['TDWaves_TD_WAVE_8_UNIT_ID'],
                      'elite': constants['TDWaves_TD_WAVE_4_ELITE_UNIT_ID'],
                      'guard': constants['TDWaves_TD_WAVE_8_GUARD_UNIT_ID'],
                      'boss': constants['TDWaves_TD_WAVE_8_BOSS_UNIT_ID']}
        self.state = dict(constants, true=True, false=False, null=None, TDConfig_TD_ENEMY_PLAYER_ID=4,
                          TDState_tdLives=[lives, 20, 20, 20])
        def record(name):
            return lambda *args: self.events.append((name, *args))
        hooks = {name: record(name) for name in ['DisplayTimedTextToPlayer', 'tdForgetEquipmentEnemy',
            'tdEnemyMechanicUnregister', 'tdSetResolvedWave', 'tdPetLaneDefeated', 'tdEvolutionClearLaneEffects',
            'tdClearLaneEnemies', 'tdShowDefeatDialog', 'tdBroadcast', 'tdRefreshHud', 'tdTryScheduleNextWave']}
        def forbidden(*args):
            raise AssertionError('Leaked/dead/invalid enemy entered kill reward path')
        hooks.update({name: forbidden for name in ['tdEquipmentKillRewardsFor', 'tdGainGold', 'tdAddScore',
            'tdHandleEnemyDrop', 'tdPetHandleEnemyBallDrop', 'tdEvolutionRecordKill']})
        hooks.update(Player=lambda p: p, unit_isAlive=lambda u: self.units[u]['alive'],
            tdEnemyWasLeaked=lambda u: self.units[u]['leaked'], GetOwningPlayer=lambda u: self.units[u]['owner'],
            tdPetIsWild=lambda u: self.units[u]['wild'], tdIsGameOver=lambda: self.over,
            tdEnemyLaneId=lambda u: self.units[u]['lane'], tdEnemyWave=lambda u: self.units[u]['wave'],
            tdIsLanePlayer=lambda p: 0 <= p < 4, tdIsLaneActive=lambda p: self.active[p],
            tdIsLaneDefeated=lambda p: self.defeated[p], tdIsLaneFinished=lambda p: self.finished[p],
            GetUnitTypeId=lambda u: self.types[self.units[u]['kind']], tdGetLives=lambda p: self.state['TDState_tdLives'][p],
            tdMarkEnemyLeaked=self.mark, tdSetLaneDefeated=self.defeat, unit_kill=self.kill,
            tdHandleGameResolved=self.resolve, GetTriggerUnit=lambda: self.trigger, int_toString=str)
        # Execute the real compiled feedback overload, including its amount argument.
        self.vm = Jass(script, self.state, hooks)

    def mark(self, u):
        self.events.append(('mark', u)); self.units[u]['leaked'] = True
    def defeat(self, p, value):
        self.events.append(('defeat', p)); self.defeated[p] = value
    def kill(self, u):
        self.events.append(('kill', u)); self.units[u]['alive'] = False
        self.trigger = u
        self.vm.run('tdHandleEnemyDeath')
        if self.reenter:
            self.reenter = False
            self.leak(2)
    def resolve(self, *args):
        self.events.append(('resolve',))
        self.over = all(not a or f or d for a, f, d in zip(self.active, self.finished, self.defeated))
    def leak(self, u=1):
        self.vm.run('tdHandleEnemyLeak', [u])
    def count(self, event):
        return sum(e[0] == event for e in self.events)


class LeakLifeArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = Mpq((ROOT / 'ExampleMap.w3x').read_bytes()).extract('war3map.j').decode('utf-8')

    def test_all_44_actual_enemy_rawcodes(self):
        h = Harness(self.script)
        ids = [(k, v) for k, v in h.state.items() if k.startswith('TDWaves_TD_WAVE_')]
        self.assertEqual(len(ids), 44)
        for name, rawcode in ids:
            expected = 3 if '_BOSS_' in name else 2 if '_ELITE_' in name or '_GUARD_' in name else 1
            self.assertEqual(h.vm.run('tdEnemyLeakLifeCost', [rawcode]), expected, name)

    def test_each_kind_remaining_lives_and_synchronous_death(self):
        for kind, cost in [('normal', 1), ('elite', 2), ('guard', 2), ('boss', 3)]:
            for lives in (1, 2, 3, 20):
                with self.subTest(kind=kind, lives=lives):
                    h = Harness(self.script, lives); h.units[1]['kind'] = kind; h.leak()
                    self.assertEqual(h.state['TDState_tdLives'], [max(0, lives-cost), 20, 20, 20])
                    self.assertIn(('DisplayTimedTextToPlayer', 0, 0.0, 0.0, 5.0,
                                   f'生命 -{cost}，剩余 {max(0, lives-cost)}'), h.events)
                    self.assertEqual(h.count('kill'), 1)
                    self.assertLess(h.events.index(('mark', 1)), h.events.index(('kill', 1)))
                    self.assertEqual(h.count('tdShowDefeatDialog'), int(lives <= cost))
                    self.assertFalse(h.over, 'Other active lane must keep running')
                    before = list(h.events); h.leak(); self.assertEqual(h.events, before)

    def test_every_ineligible_guard_blocks_direct_calls(self):
        for case in ('null', 'dead', 'leaked', 'owner', 'wild', 'gameover', 'negative_lane', 'invalid_lane', 'inactive', 'defeated', 'finished'):
            with self.subTest(case=case):
                h = Harness(self.script)
                if case == 'dead': h.units[1]['alive'] = False
                if case == 'leaked': h.units[1]['leaked'] = True
                if case == 'owner': h.units[1]['owner'] = 0
                if case == 'wild': h.units[1]['wild'] = True
                if case == 'gameover': h.over = True
                if case == 'negative_lane': h.units[1]['lane'] = -1
                if case == 'invalid_lane': h.units[1]['lane'] = 4
                if case == 'inactive': h.active[0] = False
                if case == 'defeated': h.defeated[0] = True
                if case == 'finished': h.finished[0] = True
                h.leak(None if case == 'null' else 1)
                self.assertEqual(h.events, []); self.assertEqual(h.state['TDState_tdLives'][0], 20)

    def test_fatal_reentrant_other_enemy_settles_only_once(self):
        for lives in (1, 2):
            h = Harness(self.script, lives); h.reenter = True; h.active[1] = False; h.leak()
            self.assertEqual(h.state['TDState_tdLives'][0], 0)
            self.assertEqual(h.count('kill'), 1); self.assertEqual(h.count('defeat'), 1)
            self.assertEqual(h.count('tdShowDefeatDialog'), 1); self.assertEqual(h.count('resolve'), 1)
            self.assertLess(h.events.index(('defeat', 0)), h.events.index(('kill', 1)))
            self.assertTrue(h.over)

    def test_debug_negative_amount_and_zero_floor(self):
        h = Harness(self.script, 1)
        h.vm.run('tdLoseLife', [0, -10000]); self.assertEqual(h.state['TDState_tdLives'][0], 10001)
        h.vm.run('tdLoseLife', [0, 10002]); self.assertEqual(h.state['TDState_tdLives'][0], 0)
        h.vm.run('tdLoseLife', [0, 3]); self.assertEqual(h.state['TDState_tdLives'][0], 0)

    def test_regressions_reject_broken_compiled_mutations(self):
        def replace_body(script, name, mutate):
            match = function(script, name)
            body = mutate(match[2])
            self.assertNotEqual(body, match[2], name + ' mutation must alter real artifact')
            return script[:match.start(2)] + body + script[match.end(2):]
        def check_boss(script):
            h = Harness(script, 2); h.leak()
            self.assertEqual(h.state['TDState_tdLives'][0], 0)
        def check_normal(script):
            h = Harness(script); h.units[1]['kind'] = 'normal'; h.leak()
            self.assertEqual(h.state['TDState_tdLives'][0], 19)
        def check_leaked(script):
            h = Harness(script); h.units[1]['leaked'] = True; h.leak()
            self.assertEqual(h.events, [])
        def check_mark(script):
            Harness(script).leak()
        def check_text(script):
            h = Harness(script); h.leak()
            self.assertIn(('DisplayTimedTextToPlayer', 0, 0.0, 0.0, 5.0, '生命 -3，剩余 17'), h.events)
        def mark_after_kill(body):
            line = re.search(r'^.*call tdMarkEnemyLeaked\([^\n]*\n', body, re.M)[0]
            body = body.replace(line, '')
            return re.sub(r'(^.*call unit_kill\([^\n]*\n)', lambda m: m[0] + line, body, count=1, flags=re.M)
        mutations = [
            ('fixed one', 'tdEnemyLeakLifeCost', lambda b: '\treturn 1\n', check_boss),
            ('wave-wide boss', 'tdHandleEnemyLeak', lambda b: re.sub(r'GetUnitTypeId\([^)]*\)',
                 'TDWaves_TD_WAVE_8_BOSS_UNIT_ID', b), check_normal),
            ('leaked guard', 'tdHandleEnemyLeak', lambda b: re.sub(r' or tdEnemyWasLeaked\([^)]*\)', '', b), check_leaked),
            ('mark too late', 'tdHandleEnemyLeak', mark_after_kill, check_mark),
            ('negative lives', 'tdLoseLife', lambda b: re.sub(r'\tif .*?\tendif\n', '', b, flags=re.S), check_boss),
            ('fixed feedback one', 'tdHandleEnemyLeak', lambda b: re.sub(r'(tdLeakLifeText\w*\()lifeCost,',
                 r'\g<1>1,', b), check_text),
        ]
        for label, name, mutate, check in mutations:
            with self.subTest(mutation=label):
                script = replace_body(self.script, name, mutate)
                with self.assertRaises((AssertionError, ValueError)):
                    check(script)


if __name__ == '__main__':
    unittest.main()
