#!/usr/bin/env python3
"""Execute final-MPQ Boss resistance JASS with bounded, fail-closed native stubs.

Usage: python tools/VerifyBossSpellResistanceArtifact.py map.w3x \
    --baseline-map baseline.w3x [--source wurst --baseline-source baseline/wurst]

Gameplay helpers, validity guards, setup/shutdown, generated listener dispatch,
DamageEvent classification/setAmount/settlement functions and priority-4 capture
execute from the extracted script. Ledger credit and rendering are capture
stubs. Native handles, collections, timers and unrelated tower/pet bridges are
stubbed; they never calculate resistance. onDamage is invoked directly after
the early phase. This does not establish real trigger timing, native shield
absorption, Warcraft spell classification or live gameplay.
"""
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyGroundUpgradeArtifact import GroundJassRuntime, _Return
from VerifyTowerUpgradeArtifact import JassScalarEvaluator, function_body, rawcode

READY = 'TDEnemyMechanicRuntime_tdEnemyMechanicsReady'
ONCE = 'TDEnemyMechanicRuntime_tdEnemySpellResistanceListenerReady'
SCALE = 'tdEnemyMechanicScaleSpellDamage'
CALLBACK = 'tdEnemyMechanicScaleNativeSpellDamage'
OBJECT_FILES = ('war3map.w3u', 'war3map.w3a', 'war3map.w3t', 'war3map.w3q')
BOSS_RESULTS = {8: 100.0, 16: 82.0, 24: 68.0, 32: 58.0}
DAMAGE_SITES = {
    'towers/TDTowerRuntime.wurst': [
        'tower.damageTarget(victim, tdEnemyMechanicScaleSpellDamage(victim, damagePerTick))',
        'source.damageTarget(victim, tdEnemyMechanicScaleSpellDamage(victim, tdGhoulCorpseExplosionDamageForBranch(tdTowerLevelForUnitTypeId(GetUnitTypeId(source)), tdTowerBranchForUnitTypeId(GetUnitTypeId(source)), tdTowerIsEvolved(source))))',
        'source.damageTarget(target, amount, true, true, tdArcherSplitArrowNativeAttackType(), DAMAGE_TYPE_NORMAL, WEAPON_TYPE_WHOKNOWS)'],
    'items/TDEquipmentCombat.wurst': [
        'source.damageTarget(target, additional)',
        'source.damageTarget(target, tdEnemyMechanicScaleSpellDamage(target, amount))'],
    'pets/TDPetCombat.wurst': ['host.damageTarget(target, amount)'],
}


def close(actual, expected, context):
    require(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10),
            f'{context}: got {actual}, expected {expected}')


def source_function(text, name):
    match = re.search(r'^(?:public )?function ' + re.escape(name) + r'\([^\n]*\n((?:[\t ]+[^\n]*\n|\n)*)', text, re.M)
    require(match is not None, f'Missing source function {name}')
    return match[1]


class BossJassRuntime(GroundJassRuntime):
    """Reuse the existing bounded statement interpreter, with lazy JASS booleans.

    The scalar evaluator deliberately rejects mixed AND/OR precedence. Keep
    that restriction, but short-circuit evaluated branches so null/retired
    records cannot accidentally enter a generated class dispatch.
    """
    def __init__(self, script):
        JassScalarEvaluator.__init__(self, script)
        self.script = script
        self.globals = {}
        require('globals\n' in script and 'endglobals' in script, 'Missing packaged globals')
        declarations = script.split('globals\n', 1)[1].split('endglobals', 1)[0]
        for kind, array, name, initializer in re.findall(
                r'^(\w+) (array )?(\w+)(?:\s*=\s*([^\n]+))?', declarations, re.M):
            default = False if kind == 'boolean' else 0.0 if kind == 'real' else 0 if kind == 'integer' else None
            self.globals[name] = defaultdict(lambda value=default: value) if array else default
            if initializer and not array and re.fullmatch(r'(?:true|false|null|-?\d+(?:\.\d*)?)', initializer):
                self.globals[name] = {'true': True, 'false': False, 'null': None}.get(initializer, default)
                if re.fullmatch(r'-?\d+(?:\.\d*)?', initializer):
                    self.globals[name] = float(initializer) if '.' in initializer else int(initializer)
        self.globals.update({name: value for name, value in self.constants.items()
                             if re.fullmatch(r'\w+_[A-Z][A-Z0-9_]*', name)})
        for name, literal in re.findall(r'^\s*set (\w+) = ([+-]?\s*\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)\s*$', script, re.M):
            if re.fullmatch(r'\w+_[A-Z][A-Z0-9_]*', name):
                literal = literal.replace(' ', '')
                self.globals[name] = float(literal) if any(char in literal for char in '.eE') else int(literal)
        self.globals.update(JASS_MAX_ARRAY_SIZE=8192, ATTACK_TYPE_CHAOS='chaos', ATTACK_TYPE_PIERCE='pierce',
                            DAMAGE_TYPE_UNIVERSAL='universal', DAMAGE_TYPE_NORMAL='normal',
                            WEAPON_TYPE_WHOKNOWS='unknown', UNIT_STATE_MAX_LIFE='maxLife',
                            UNIT_STATE_LIFE='life', GREATER_THAN='greater')
        self.calls = Counter()
        self.execution_depth = 0
        self.executed_steps = 0
        self.scale_inputs, self.credits, self.hits, self.native_damage, self.events = [], [], [], [], []
        self.destroyed, self.groups, self.group_cursor = [], {}, {}
        self.table, self.lists = {}, {700: [], 800: []}
        self.globals['TDEnemyMechanicRuntime_tdEnemyMechanicRecordsByHandle'] = 600
        self.globals['TDEnemyMechanicRuntime_tdEnemyMechanicRecords'] = 700
        self.globals['DamageEvent_damageList'] = 800
        self.globals['DamageEvent_LIMIT_RECURSION'] = 48
        self.globals['DamageEvent_nextDamageType'] = 4
        self.globals['DamageEvent_ATTACK_TYPE_UNIVERSAL'] = 'universalAttack'
        self.units = {
            100: dict(alive=True, owner=4, type=rawcode('uB32'), life=1000.0, maxLife=2000.0,
                      lane=0, wave=32, leaked=False),
            101: dict(alive=True, owner=0, type=rawcode('uG6B'), life=1000.0, maxLife=1000.0,
                      lane=0, wave=0, leaked=False),
            102: dict(alive=True, owner=4, type=rawcode('uW01'), life=10.0, maxLife=100.0,
                      lane=0, wave=32, leaked=False),
        }
        self.active, self.defeated, self.finished, self.over = [True] * 4, [False] * 4, [False] * 4, False
        self.event_amount, self.event_source, self.event_target = 0.0, 101, 100
        self.detect = True
        self.seed_record()
        if 'ref_function_bridge_DamageEvent_onTrg' in self.globals:
            self.globals['ref_function_bridge_DamageEvent_onTrg'] = 'bridge_DamageEvent_onTrg'

    def seed_record(self, wave=32, role=3, active=True):
        self.table[100] = 10
        self.lists[700] = [10]
        for name, index, value in [
                ('TDEnemyMechanicRecord_enemy', 10, 100), ('TDEnemyMechanicRecord_state', 10, 20),
                ('TDEnemyMechanicState_typeId', 20, 1), ('TDEnemyMechanicState_link', 20, 30),
                ('TDEnemyMechanicState_active', 20, active), ('TDEnemyMechanicState_role', 20, role),
                ('TDEnemyGuardLink_lane', 30, 0), ('TDEnemyGuardLink_wave', 30, wave),
                ('TDEnemyMechanicRuntime_tdEnemyGuardLinks', wave, 30)]:
            require(name in self.globals, f'Missing packaged state array {name}')
            self.globals[name][index] = value
        require(self.globals['TDEnemyMechanicData_TD_ENEMY_ROLE_BOSS'] == 3, 'Boss role constant changed')
        require(self.globals['TDConfig_TD_ENEMY_PLAYER_ID'] == 4, 'Enemy owner constant changed')
        require(self.globals['TDConfig_TD_ACTIVE_PLAYER_COUNT'] == 4, 'Active lane constant changed')
        if 'TDPet_lane' in self.globals:
            self.globals['TDPet_lane'][500] = 0

    def expression(self, text, scope):
        text = re.sub(r'\btrue\b', 'True', text)
        text = re.sub(r'\bfalse\b', 'False', text)
        text = re.sub(r'\bnull\b', 'None', text)
        try:
            node = ast.parse(text.strip(), mode='eval').body
        except SyntaxError as exc:
            raise ValueError('Unsupported packaged expression ' + text) from exc
        ops = {type(part.op) for part in ast.walk(node) if isinstance(part, ast.BoolOp)}
        require(len(ops) <= 1, 'Mixed Jass and/or requires a Jass-specific precedence parser')
        variables = {**self.globals, **scope}
        def read(part):
            if isinstance(part, ast.BoolOp):
                if isinstance(part.op, ast.And):
                    return all(bool(read(value)) for value in part.values)
                return any(bool(read(value)) for value in part.values)
            if isinstance(part, ast.Subscript) and isinstance(part.value, ast.Name):
                require(part.value.id in variables, 'Unknown packaged array ' + part.value.id)
                return variables[part.value.id][read(part.slice)]
            if isinstance(part, ast.Call) and isinstance(part.func, ast.Name):
                require(not part.keywords, 'Packaged call has unsupported keywords')
                return self.call(part.func.id, [read(arg) for arg in part.args])
            if isinstance(part, ast.UnaryOp):
                value = read(part.operand)
                if isinstance(part.op, ast.Not): return not value
                if isinstance(part.op, ast.USub): return -value
                if isinstance(part.op, ast.UAdd): return value
            if isinstance(part, ast.BinOp):
                left, right = read(part.left), read(part.right)
                if isinstance(part.op, ast.Add): return left + right
                if isinstance(part.op, ast.Sub): return left - right
                if isinstance(part.op, ast.Mult): return left * right
                if isinstance(part.op, ast.Div):
                    return int(left / right) if type(left) is int and type(right) is int else left / right
            if isinstance(part, ast.Compare) and len(part.ops) == 1:
                left, right, op = read(part.left), read(part.comparators[0]), part.ops[0]
                if isinstance(op, ast.Eq): return left == right
                if isinstance(op, ast.NotEq): return left != right
                if isinstance(op, ast.Lt): return left < right
                if isinstance(op, ast.LtE): return left <= right
                if isinstance(op, ast.Gt): return left > right
                if isinstance(op, ast.GtE): return left >= right
            # Leaf scalars retain the existing evaluator's allow-list.
            return JassScalarEvaluator.expression(self, ast.unparse(part), variables)
        return read(node)

    def call(self, name, args):
        self.execution_depth += 1
        try:
            require(self.execution_depth <= 60, 'Packaged call depth exceeded bounded interpreter limit')
            return self.execute_call(name, args)
        finally:
            self.execution_depth -= 1

    def execute_call(self, name, args):
        self.calls[name] += 1
        if name == SCALE:
            self.scale_inputs.append(tuple(args[:2]))
        native, result = self.native(name, args)
        if native: return result
        require(name in self.functions, f'Missing packaged Boss function {name}')
        signature, lines = self.functions[name]
        require(len(args) == len(signature), f'{name}: packaged argument count changed')
        scope, branches, loops, active, index, steps = dict(zip(signature, args)), [], [], True, 0, 0
        try:
            while index < len(lines):
                steps += 1
                self.executed_steps += 1
                require(self.executed_steps <= 2000000, 'Packaged execution exceeded bounded interpreter budget')
                require(steps <= 10000, f'{name}: packaged loop did not terminate')
                line = lines[index].split('//', 1)[0].strip()
                if not line: pass
                elif line.startswith('if ') and line.endswith(' then'):
                    selected = active and bool(self.expression(line[3:-5], scope))
                    branches.append([active, selected]); active = selected
                elif line.startswith('elseif ') and line.endswith(' then'):
                    require(bool(branches), f'{name}: unmatched elseif')
                    parent, selected = branches[-1]
                    active = parent and not selected and bool(self.expression(line[7:-5], scope))
                    branches[-1][1] = selected or active
                elif line == 'else':
                    require(bool(branches), f'{name}: unmatched else')
                    parent, selected = branches[-1]
                    active, branches[-1][1] = parent and not selected, True
                elif line == 'endif':
                    require(bool(branches), f'{name}: unmatched endif')
                    active = branches.pop()[0]
                elif line == 'loop':
                    if active:
                        loops.append((index, len(branches), active))
                    else:
                        # Ground runtime's active loops are retained; skip a
                        # complete loop in an inactive conditional branch.
                        depth = 1
                        while depth:
                            index += 1
                            require(index < len(lines), 'Unclosed inactive packaged loop')
                            depth += (lines[index] == 'loop') - (lines[index] == 'endloop')
                elif line == 'endloop':
                    require(bool(loops), f'{name}: unmatched endloop')
                    loop_start, branch_depth, loop_active = loops.pop()
                    require(len(branches) == branch_depth, f'{name}: unclosed branch at loop tail')
                    index = loop_start; active = loop_active; continue
                elif active and line.startswith('exitwhen '):
                    require(bool(loops), f'{name}: exitwhen outside loop')
                    if self.expression(line[9:], scope):
                        depth = 1
                        while depth:
                            index += 1
                            require(index < len(lines), 'Unclosed packaged loop')
                            depth += (lines[index] == 'loop') - (lines[index] == 'endloop')
                        _, branch_depth, loop_active = loops.pop()
                        # exitwhen may be inside nested ifs. Its jump leaves
                        # those branches lexically inside this loop, while
                        # preserving every branch surrounding the loop.
                        del branches[branch_depth:]
                        active = loop_active
                elif active and line.startswith('return'):
                    raise _Return(self.expression(line[7:], scope) if line != 'return' else None)
                elif active and line.startswith('local '):
                    declaration = re.fullmatch(r'local (\w+) (\w+)(?: = (.*))?', line)
                    require(declaration is not None, 'Unsupported packaged local')
                    kind, key, initializer = declaration.groups()
                    scope[key] = self.expression(initializer, scope) if initializer else (0 if kind in ('real', 'integer') else False if kind == 'boolean' else None)
                elif active and line.startswith('set '):
                    key, value = line[4:].split(' = ', 1)
                    if not key.startswith('wurst_stack'):
                        self.assign(key, self.expression(value, scope), scope)
                elif active and line.startswith('call '): self.expression(line[5:], scope)
                elif active: raise ValueError(f'{name}: unsupported packaged Boss statement {line}')
                index += 1
        except _Return as returned: return returned.value
        require(not branches and not loops, f'{name}: unclosed packaged control flow')
        return None

    def native(self, name, args):
        unit = lambda handle: self.units.get(handle, dict(alive=False, type=0, owner=-1, life=0.0, maxLife=0.0))
        if name == 'error': raise ValueError('Packaged JASS error: ' + str(args[0]))
        if name == 'handle_getHandleId': return True, args[0] or 0
        if name.startswith('dispatch_Table_Table_'):
            require(args[0] == 600, 'Unexpected table handle')
            op = name.removeprefix('dispatch_Table_Table_')
            if op == 'hasInt': return True, args[1] in self.table
            if op == 'loadInt': return True, self.table.get(args[1], 0)
            if op == 'removeInt': self.table.pop(args[1], None); return True, None
            raise ValueError('Unsupported table operation ' + name)
        if name.startswith('dispatch_LinkedList_LinkedList_'):
            require(args[0] in self.lists, 'Unexpected list handle')
            values = self.lists[args[0]]
            op = name.removeprefix('dispatch_LinkedList_LinkedList_')
            if op == 'isEmpty': return True, not values
            if op == 'get': return True, values[args[1]]
            if op == 'remove': values.remove(args[1]); return True, None
            if op == 'add_1': values.append(args[2]); return True, None
            raise ValueError('Unsupported list operation ' + name)
        if name == 'GetEventDamage': return True, self.event_amount
        if name == 'GetEventDamageSource': return True, self.event_source
        if name == 'GetTriggerUnit': return True, self.event_target
        if name == 'GetUnitTypeId': return True, unit(args[0])['type']
        if name == 'unit_isAlive': return True, unit(args[0])['alive']
        if name == 'GetOwningPlayer': return True, unit(args[0])['owner']
        if name in ('Player', 'GetPlayerId'): return True, args[0]
        if name in ('widget_getLife', 'unit_getHP'): return True, unit(args[0])['life']
        if name == 'unit_getMaxHP': return True, unit(args[0])['maxLife']
        if name == 'GetUnitState':
            require(args[1] == 'maxLife', 'Unsupported native unit state')
            return True, unit(args[0])['maxLife']
        if name == 'widget_setLife':
            self.units[args[0]]['life'] = args[1]
            self.events.append(('engineLife', *args))
            return True, None
        if name == 'tdIsLaneActive': return True, self.active[args[0]]
        if name == 'tdIsLaneDefeated': return True, self.defeated[args[0]]
        if name == 'tdIsLaneFinished': return True, self.finished[args[0]]
        if name == 'tdIsLanePlayer': return True, 0 <= args[0] < 4
        if name == 'tdIsGameOver': return True, self.over
        if name == 'tdEnemyLaneId': return True, unit(args[0])['lane']
        if name == 'tdEnemyWave': return True, unit(args[0])['wave']
        if name == 'tdEnemyWasLeaked': return True, unit(args[0])['leaked']
        if name == 'tdDamageTrackTower': return True, 900 if args[0] == 101 else 0
        if name == 'dispatch_TDDamageRecord_TDDamageRecord_getLane': return True, 0
        if name == 'dispatch_TDDamageLedger_TDDamageLedger_credit':
            self.credits.append(tuple(args[1:4])); return True, None
        if name == 'tdDamageShowHit': self.hits.append(tuple(args[:2])); return True, None
        if name == 'dispatch_TDEnemyMechanicRecord_destroyTDEnemyMechanicRecord':
            self.destroyed.append(('record', args[0])); return True, None
        if name == 'dispatch_TDEnemyGuardLink_destroyTDEnemyGuardLink':
            self.destroyed.append(('link', args[0])); return True, None
        if name == 'tdEnemyMechanicSyncArmor': return True, None
        if name == 'dispatch_DamageInstance_destroyDamageInstance':
            self.destroyed.append(('damage', args[0])); return True, None
        if name in ('CreateTrigger',): return True, 1
        if name in ('trigger_addAction', 'trigger_registerUnitStateEvent', 'nullTimer', 'unit_removeAbility', 'SetUnitMoveSpeed'):
            return True, None
        if name == 'unit_getAbilityLevel': return True, 1 if args[0] == 101 else 0
        if name == 'disableDamageDetect': self.detect = False; return True, None
        if name == 'enableDamageDetect': self.detect = True; return True, None
        if name == 'UnitDamageTarget':
            self.native_damage.append(tuple(args))
            if not self.detect:
                self.units[args[1]]['life'] = 0.0
                self.units[args[1]]['alive'] = False
                return True, True
            self.emit(args[2], source=args[0], target=args[1])
            return True, True
        if name == 'CreateGroup':
            handle = len(self.groups) + 1000; self.groups[handle] = []; return True, handle
        if name == 'group_enumUnitsInRange': self.groups[args[0]] = [100]; return True, None
        if name == 'group_iterator': self.group_cursor[args[0]] = 0; return True, args[0]
        if name == 'group_hasNext': return True, self.group_cursor[args[0]] < len(self.groups[args[0]])
        if name == 'group_next':
            index = self.group_cursor[args[0]]; self.group_cursor[args[0]] += 1
            return True, self.groups[args[0]][index]
        if name in ('group_close', 'group_destr', 'DestroyEffect', 'widget_flashEffect', 'tdPetOnSplitArrowImpact', 'tdPetOnCorpseExplosion'):
            return True, None
        if name == 'AddSpecialEffect': return True, 1
        if name == 'unit_getPos': self.globals['unit_getPos_return_y'] = 0.0; return True, 0.0
        if name == 'tdPetBindingValid': return True, args[:3] == [500, 101, 1]
        if name == 'tdPetEnemyIsValid': return True, unit(args[0])['alive'] and unit(args[0])['owner'] == 4
        if name == 'tdEquipmentSourceValid': return True, args[:2] == [101, 0]
        if name == 'tdEquipmentEnemyValid': return True, unit(args[0])['alive'] and unit(args[0])['owner'] == 4 and args[1] == 0
        if name == 'tdTowerChoiceForUnitTypeId': return True, self.globals.get('TDConfig_TD_TOWER_CHOICE_GHOUL', 5)
        if name == 'tdTowerLevelForUnitTypeId': return True, 6
        if name == 'tdTowerBranchForUnitTypeId': return True, 2
        if name == 'tdTowerIsEvolved': return True, False
        return False, None

    def emit(self, signed_amount, source=101, target=100):
        """Drive real settlement bodies with an explicitly simulated boundary.

        Timers/trigger dispatch are stubbed. Calling onDamage directly proves
        settlement function behavior, not native callback timing or absorption.
        """
        self.event_amount, self.event_source, self.event_target = signed_amount, source, target
        before = self.globals['DamageInstance_maxIndex']
        self.invoke('DamageEvent_onUnreducedDamage')
        instance = self.globals['DamageInstance_maxIndex']
        require(instance > before, 'Engine did not construct a damage instance')
        result = {field: self.globals['DamageInstance_' + field][instance]
                  for field in ('amount', 'unreducedAmount', 'isCode', 'isSpell', 'id', 'lastDamageHP')}
        if signed_amount != 0.0:
            if not result['isSpell']:
                self.units[target]['life'] = max(0.0, self.units[target]['life'] - signed_amount)
            self.invoke('DamageEvent_onDamage', instance)
        result['life'] = self.units[target]['life']
        self.events.append(('event', result))
        return result

    def setup(self, ledger=False):
        self.invoke('tdSetupEnemyMechanics')
        if ledger:
            self.invoke('tdSetupDamageStatistics')
            require(self.globals['DamageEvent_firstUnreducedListeners'][4] != 0,
                    'Existing accounting listener must remain at early priority 4')

    def fill_closure(self, name, closure=6000, amount=75.0):
        """Seed compiler-generated capture arrays, without replacing callbacks."""
        body = function_body(self.script, name)
        for array in re.findall(r'\b(\w+)\[this_1\]', body):
            require(array in self.globals, 'Missing closure capture ' + array)
            stem = re.sub(r'_\d+$', '', array)
            values = dict(source=101, host=101, target=100, lane=0, amount=amount,
                          additional=amount, base=amount, extra=1.0, pet=500, generation=1,
                          proc=False, skill=-1, strength=0.0, center_x=0.0, center_y=0.0)
            require(stem in values, 'Unsupported closure capture ' + array)
            self.globals[array][closure] = values[stem]
        return closure


def verify_pure_and_runtime(script):
    runtime = BossJassRuntime(script)
    helper = 'TDEnemyMechanicState_scaledSpellAmount'
    require(helper in runtime.functions, 'Missing real packaged state resistance helper')
    cases = 0
    for wave, role, active, amount in itertools.product(range(-1, 35), (-1, 0, 1, 2, 3, 4), (False, True), (-10.0, 0.0, 0.125, 75.0, 100.0)):
        runtime.seed_record(wave, role, active)
        expected = amount
        if wave in BOSS_RESULTS and role == 3 and active and amount > 0:
            expected = amount * (BOSS_RESULTS[wave] / 100.0)
        close(runtime.invoke(helper, 20, amount), expected,
              f'Packaged state helper wave={wave} role={role} active={active} amount={amount}')
        cases += 1
    runtime.seed_record()
    runtime.globals[READY] = True
    for displayed_wave in (1, 8, 16, 24, 32):
        require('TDState_tdGlobalWave' in runtime.globals, 'Missing actual displayed global wave')
        runtime.globals['TDState_tdGlobalWave'] = displayed_wave
        if 'TDState_tdCurrentWave' in runtime.globals:
            runtime.globals['TDState_tdCurrentWave'][0] = displayed_wave
        close(runtime.invoke(SCALE, 100, 75.0), 43.5, 'Original-wave resistance independent of displayed wave')
    for target in (None, 0, 999):
        close(runtime.invoke(SCALE, target, 75.0), 75.0, 'Unregistered/null runtime target')
    guards = [lambda r: r.globals.__setitem__(READY, False),
              lambda r: r.table.clear(),
              lambda r: r.globals['TDEnemyMechanicState_active'].__setitem__(20, False),
              lambda r: r.globals['TDEnemyMechanicRecord_enemy'].__setitem__(10, None),
              lambda r: r.units[100].update(alive=False),
              lambda r: r.units[100].update(type=0),
              lambda r: r.units[100].update(owner=0),
              lambda r: r.active.__setitem__(0, False),
              lambda r: r.defeated.__setitem__(0, True),
              lambda r: r.finished.__setitem__(0, True),
              lambda r: setattr(r, 'over', True)]
    for index, disable in enumerate(guards):
        current = BossJassRuntime(script); current.setup(); disable(current)
        close(current.invoke(SCALE, 100, 75.0), 75.0, f'Invalid runtime lifecycle guard {index}')
    for spell, code in itertools.product((False, True), repeat=2):
        current = BossJassRuntime(script); current.setup()
        require(current.invoke('tdEnemyMechanicNativeSpellEligible', spell, code) is (spell and not code),
                'Native spell/code eligibility truth table')
        instance = current.invoke('new_DamageInstance', 0, 101, 100, 75.0, spell, code, 1, 0)
        current.globals['DamageInstance_current'] = instance
        current.invoke(CALLBACK)
        close(current.globals['DamageInstance_amount'][instance], 43.5 if spell and not code else 75.0,
              'Native callback spell/code scaled exactly once')
        require(current.calls[SCALE] == int(spell and not code), 'Native callback incorrectly invoked shared scaler')
    current = BossJassRuntime(script); current.setup()
    current.globals[READY] = False
    instance = current.invoke('new_DamageInstance', 0, 101, 100, 75.0, True, False, 1, 0)
    current.globals['DamageInstance_current'] = instance
    current.invoke(CALLBACK)
    require(current.calls[SCALE] == 0, 'Shutdown native callback entered shared scaler')
    close(current.globals['DamageInstance_amount'][instance], 75.0, 'Shutdown native callback changed damage')
    return cases


def verify_engine_and_accounting(script, runtime_type=BossJassRuntime, boss_results=None):
    # Original historical callers keep their original factors and state oracle.
    results = BOSS_RESULTS if boss_results is None else boss_results
    scenarios = 0
    for wave, code, spell, prelife in itertools.product((8, 16, 24, 32), (False, True), (False, True), (40.0, 1000.0, 1990.0)):
        runtime = runtime_type(script); runtime.seed_record(wave); runtime.setup(ledger=True)
        runtime.units[100]['life'] = prelife
        if code: runtime.invoke('DamageEvent_setNextDamageFromCode')
        result = runtime.emit(-100.0 if spell else 100.0)
        expected = results[wave] if spell and not code else 100.0
        close(result['amount'], expected, 'Actual dependency classification/early amount')
        close(result['unreducedAmount'], expected, 'Actual early setAmount unreduced amount')
        require(result['isCode'] is code and result['isSpell'] is spell,
                'Code flag not preserved through dependency negative reclassification')
        require(runtime.calls[SCALE] == int(spell and not code), 'Dependency resistance invoked more than once')
        require(len(runtime.credits) == 1 and len(runtime.hits) == 1, 'Priority-4 ledger missing or duplicate')
        close(runtime.credits[0][1], min(expected, prelife), 'Real priority-4 effective-damage accounting')
        close(runtime.hits[0][1], min(expected, prelife), 'Real floating-hit effective-damage accounting')
        close(result['life'], max(0.0, prelife - expected),
              'Actual locked dependency HP settlement')
        if spell:
            close(result['lastDamageHP'], prelife - expected, 'Actual spell HP snapshot uses scaled amount')
        scenarios += 1
    return scenarios


def verify_zero_engine_event(script):
    for code in (False, True):
        runtime = BossJassRuntime(script)
        runtime.setup(ledger=True)
        if code:
            runtime.invoke('DamageEvent_setNextDamageFromCode')
            runtime.invoke('DamageEvent_setNextDamageId', rawcode('Pdam'))
        life = runtime.units[100]['life']
        zero = runtime.emit(0.0)
        close(zero['amount'], 0.0, 'Zero actual engine event amount')
        close(zero['life'], life, 'Zero actual engine event changed stub life')
        require(not runtime.credits and not runtime.hits,
                'Zero actual engine event produced accounting capture or hit')
        require(runtime.calls['DamageEvent_onDamage'] == 0 and runtime.calls[SCALE] == 0,
                'Zero actual engine event reached settlement or resistance')
        followup = runtime.emit(-100.0)
        close(followup['amount'], 58.0, 'Normal event after zero must still scale once')
        require(not followup['isCode'] and followup['id'] == 0 and
                len(runtime.credits) == 1 and len(runtime.hits) == 1 and runtime.calls[SCALE] == 1,
                'Zero event contaminated following classification or accounting')
    return 2


def verify_setup_lifecycle(script):
    compiled = BossJassRuntime(script)
    compiled.globals['MagicFunctions_compiletime'] = True
    compiled.setup()
    require(not compiled.globals[READY] and not compiled.globals[ONCE] and
            compiled.globals['DamageEvent_firstUnreducedListeners'][2] == 0,
            'Compiletime setup installed gameplay listener')
    runtime = BossJassRuntime(script)
    runtime.setup(); first = runtime.globals['DamageEvent_firstUnreducedListeners'][2]
    require(first != 0 and runtime.globals[ONCE], 'Runtime priority-2 listener missing')
    runtime.setup()
    require(runtime.globals['DamageEvent_firstUnreducedListeners'][2] == first and
            runtime.globals['DamageListener_next'][first] == 0, 'Repeated setup duplicated listener')
    runtime.invoke('tdEnemyMechanicsShutdown')
    require(not runtime.globals[READY] and runtime.globals[ONCE] and not runtime.table and not runtime.lists[700],
            'Shutdown left records or reset lifetime listener flag')
    close(runtime.invoke(SCALE, 100, 75.0), 75.0, 'Shutdown cannot scale')
    runtime.setup(); runtime.seed_record()
    require(runtime.globals['DamageEvent_firstUnreducedListeners'][2] == first and
            runtime.globals['DamageListener_next'][first] == 0, 'Shutdown/setup installed duplicate listener')
    close(runtime.emit(-100.0)['amount'], 58.0, 'Shutdown/setup native hit must scale once')
    runtime = BossJassRuntime(script); runtime.setup()
    runtime.units[100]['leaked'] = True
    runtime.invoke('tdEnemyMechanicUnregister', 100)
    close(runtime.invoke(SCALE, 100, 75.0), 75.0, 'Unregistered leaked enemy cannot scale')


def verify_scripted_damage(script):
    results = {}
    for label, function, args, expected, event_id in [
            ('pet spell', 'spellDamage', [500, 101, 1, 100, 75.0], 43.5, rawcode('Pdam')),
            ('pet derived attack', 'damage', [500, 101, 1, 100, 75.0], 75.0, rawcode('Pdam')),
            ('split arrow', 'tdDealArcherSplitArrowAttackDamage', [101, 100, 75.0], 75.0, rawcode('Tspl'))]:
        runtime = BossJassRuntime(script); runtime.setup(ledger=True)
        runtime.invoke(function, *args)
        require(len(runtime.native_damage) == 1, label + ': missing/extra damage segment')
        close(runtime.native_damage[0][2], expected, label + ': incorrect submitted amount')
        event = [event[1] for event in runtime.events if event[0] == 'event'][-1]
        require(event['id'] == event_id, label + ': damage ID changed')
        require(runtime.calls[SCALE] == int(label == 'pet spell'), label + ': scaling count changed')
        if label != 'split arrow':
            require(event['isCode'], label + ': original code marker changed')
            require(runtime.native_damage[0][3:] == (False, False, 'chaos', 'universal', 'unknown'),
                    label + ': original native damage parameters changed')
        else:
            require(runtime.native_damage[0][3] is True and runtime.native_damage[0][4] is True and
                    runtime.native_damage[0][5:] == ('pierce', 'normal', 'unknown'), 'Split-arrow attack parameters changed')
        results[label] = expected
    for skill in (13, 14):
        runtime = BossJassRuntime(script); runtime.setup(ledger=True)
        runtime.invoke('resolveActive', 500, 101, 1, 0.0, 0.0, skill, 1.0, 75.0)
        require(len(runtime.native_damage) == 1, f'Pet active skill {skill}: missing/extra segment')
        close(runtime.native_damage[0][2], 43.5, f'Pet active skill {skill}')
        require(runtime.calls[SCALE] == 1, f'Pet active skill {skill}: double scaling')
        event = [event[1] for event in runtime.events if event[0] == 'event'][-1]
        require(event['isCode'] and event['id'] == rawcode('Pdam'), f'Pet active skill {skill}: code tag/ID changed')
        results['pet active ' + str(skill)] = 43.5
    for function, expected, event_id in [
            ('call_doAfter_TDEquipmentCombat', 75.0, rawcode('Eadd')),
            ('call_doAfter_TDEquipmentCombat_1', 43.5, 0),
            ('call_doPeriodicallyCounted_TDPetCombat', 43.5, rawcode('Pdam')),
            ('call_doAfter_TDPetCombat', 75.0, rawcode('Pdam'))]:
        runtime = BossJassRuntime(script); runtime.setup(ledger=True)
        closure = runtime.fill_closure(function)
        arguments = [closure, 1] if 'PeriodicallyCounted' in function else [closure]
        runtime.invoke(function, *arguments)
        require(len(runtime.native_damage) == 1, function + ': missing/extra segment')
        close(runtime.native_damage[0][2], expected, function)
        event = [event[1] for event in runtime.events if event[0] == 'event'][-1]
        require(event['id'] == event_id and event['isCode'], function + ': code tag/ID changed')
        require(runtime.calls[SCALE] == int(expected == 43.5), function + ': scaling count changed')
        results[function] = expected
    runtime = BossJassRuntime(script); runtime.setup(ledger=True)
    runtime.invoke('tdPulseOrcBladestorm', 101)
    require(len(runtime.native_damage) == 1 and runtime.calls[SCALE] == 1, 'Tower storm damage count/scaling changed')
    original = runtime.scale_inputs[0][1]
    close(runtime.native_damage[0][2], original * 0.58, 'Tower storm exactly-one scaling')
    event = [event[1] for event in runtime.events if event[0] == 'event'][-1]
    require(event['isCode'] and event['id'] == 0, 'Tower storm code marker/ID changed')
    results['tower storm'] = runtime.native_damage[0][2]
    runtime = BossJassRuntime(script); runtime.setup(ledger=True)
    instance = runtime.invoke('new_DamageInstance', 0, 101, 102, 75.0, False, False, 0, 0)
    runtime.globals['DamageInstance_current'] = instance
    runtime.invoke('tdHandleGhoulCorpseExplosionDamage')
    require(len(runtime.native_damage) == 1 and runtime.calls[SCALE] == 1, 'Tower corpse damage count/scaling changed')
    close(runtime.native_damage[0][2], 36.0 * 0.58, 'Tower corpse original amount/scaling')
    event = [event[1] for event in runtime.events if event[0] == 'event'][-1]
    require(event['isCode'] and event['id'] == 0, 'Tower corpse code marker/ID changed')
    results['tower corpse'] = runtime.native_damage[0][2]
    return results


def verify_source_contract(root, baseline_root=None):
    root = Path(root)
    actual = {}
    for path in sorted(root.rglob('*.wurst')):
        # Check only production truth, never staged tests or dependencies.
        if any(part in ('_tests', '_build', 'dependencies') for part in path.relative_to(root).parts): continue
        lines = [line.strip() for line in path.read_text(encoding='utf-8').splitlines()
                 if not line.lstrip().startswith('//')]
        damage = [line for line in lines if re.search(r'\b(?:damageTarget|UnitDamageTarget)\(', line)]
        if damage: actual[path.relative_to(root).as_posix()] = damage
    require(actual == DAMAGE_SITES, 'Production damage call-site inventory changed: ' + repr(actual))
    pet = (root / 'pets/TDPetCombat.wurst').read_text(encoding='utf-8')
    wrapper = source_function(pet, 'spellDamage')
    require(wrapper.strip() == 'damage(pet, host, generation, target, tdEnemyMechanicScaleSpellDamage(target, amount))',
            'Pet spell wrapper changes original damage or scales more than once')
    require('tdEnemyMechanicScaleSpellDamage' not in source_function(pet, 'damage'), 'Original pet damage was scaled')
    require('damage(pet, host, generation, target, base * extra)' in source_function(pet, 'onAttack'),
            'Pet combo/execute derived attack changed')
    require('spellDamage(pet, source, generation, target, amount)' in source_function(pet, 'tdPetOnCorpseExplosion'),
            'Pet corpse poison bypasses resistance wrapper')
    active = source_function(pet, 'resolveActive')
    require('spellDamage(pet, host, generation, victim, base * power)' in active and 'if skill == 15' in active,
            'Pet active spell paths changed')
    runtime = (root / 'enemies/TDEnemyMechanicRuntime.wurst').read_text(encoding='utf-8')
    state = (root / 'enemies/TDEnemyMechanicState.wurst').read_text(encoding='utf-8')
    region = source_function(runtime, SCALE) + source_function(runtime, CALLBACK)
    require(not re.search(r'\b(?:SetUnitState|UnitDamageTarget|SetWidgetLife|SetUnitLife|CreateUnit)\(|\.(?:setLife|setHP|damageTarget)\(', region),
            'Forbidden post-damage HP compensation or extra damage in resistance adapters')
    require('tdEnemySpellResistanceListenerReady = false' not in source_function(runtime, 'tdEnemyMechanicsShutdown'),
            'Shutdown resets the persistent listener flag')
    require(not re.search(r'(?i)probe|bracer|AIsr', runtime + state), 'Resistance introduces probe or native bracers')
    forbidden_file = re.compile(r'\b(?:SetUnitState|SetWidgetLife|SetUnitLife|SetUnitMaxState|UnitDamageTarget)\(|\.(?:setLife|setHP|setMaxHP|abortCurrent|setNextDamageElement|setNextDamageType)\(')
    for relative in ('enemies/TDEnemyMechanicRuntime.wurst', 'enemies/TDEnemyMechanicState.wurst',
                     'towers/TDTowerRuntime.wurst', 'items/TDEquipmentCombat.wurst', 'pets/TDPetCombat.wurst'):
        code = '\n'.join(line for line in (root / relative).read_text(encoding='utf-8').splitlines()
                         if not line.lstrip().startswith('//'))
        require(not forbidden_file.search(code), 'Forbidden HP/abort/type/element compensation in ' + relative)
    if baseline_root is not None:
        baseline_root = Path(baseline_root)
        current_paths = {path.relative_to(root) for path in root.rglob('*.wurst') if '_tests' not in path.parts}
        previous_paths = {path.relative_to(baseline_root) for path in baseline_root.rglob('*.wurst') if '_tests' not in path.parts}
        require(current_paths == previous_paths, 'Production source file inventory changed')
        forbidden = re.compile(r"\b(?:SetUnitState|UnitDamageTarget|SetWidgetLife|SetUnitLife|SetUnitMaxState|CreateUnit)\(|\.(?:setLife|setHP|setMaxHP)\(|(?i:probe|bracer|AIsr)|\.(?:abortCurrent|setNextDamageElement|setNextDamageType)\(|'\w{4}'")
        for relative in current_paths:
            current = (root / relative).read_text(encoding='utf-8')
            previous = (baseline_root / relative).read_text(encoding='utf-8')
            code_lines = lambda text: Counter(line.strip() for line in text.splitlines()
                                             if line.strip() and not line.lstrip().startswith('//'))
            for added in (code_lines(current) - code_lines(previous)):
                require(not forbidden.search(added),
                        'Forbidden new damage/HP/object compensation or probe: ' + str(relative) + ': ' + added)
        protected = ('TDGame.wurst', 'TDState.wurst', 'TDSpawn.wurst', 'TDConfig.wurst',
                     'towers/TDTowerObjectGen.wurst', 'towers/TDTowerBalanceData.wurst',
                     'towers/TDTowerCatalogData.wurst', 'items/TDItemData.wurst',
                     'damage/TDDamageRuntime.wurst', 'damage/TDDamageState.wurst')
        for relative in protected:
            require((root / relative).read_bytes() == (baseline_root / relative).read_bytes(),
                    'Protected economy/victory/catalog/object source changed: ' + relative)
        wave = (root / 'TDWaves.wurst').read_text(encoding='utf-8')
        baseline_wave = (baseline_root / 'TDWaves.wurst').read_text(encoding='utf-8')
        strip_comments = lambda text: '\n'.join(line.rstrip() for line in text.splitlines() if not line.lstrip().startswith('//'))
        require(strip_comments(wave) == strip_comments(baseline_wave), 'Wave economy/HP/config data changed')
    return sum(map(len, actual.values()))


def canonical_function(script, name):
    match = re.search(r'^function ' + re.escape(name) + r' takes ([^\n]+) returns (\w+)\n(.*?)^endfunction', script, re.M | re.S)
    require(match is not None, 'Missing protected JASS function ' + name)
    signature, result, body = match.groups()
    parameters = [] if signature == 'nothing' else [part.strip().split() for part in signature.split(',')]
    parameters = [parts for parts in parameters if parts[-1] != 'w__wurst_stackPos']
    locals_ = re.findall(r'^\s*local (\w+) (\w+)', body, re.M)
    names = {parts[-1]: 'v' + str(index) for index, parts in enumerate(parameters + locals_)}
    lines = []
    for line in body.splitlines():
        if re.match(r'\s*set wurst_stack', line): continue
        line = re.sub(r'"when (?:calling|constructing)[^"\n]*"', '"debug"', line)
        line = re.sub(r'\b\w+\b', lambda match: names.get(match[0], match[0]), line)
        lines.append(' '.join(line.split()))
    return tuple(parts[0] for parts in parameters), result, '\n'.join(lines)


def verify_baseline(script, artifact, baseline_script, baseline_artifact):
    digests = {}
    for member in OBJECT_FILES:
        require(artifact.has(member) == baseline_artifact.has(member), 'Object member presence changed: ' + member)
        if artifact.has(member):
            current, previous = artifact.extract(member), baseline_artifact.extract(member)
            require(current == previous, 'Full object data changed: ' + member)
            digests[member] = hashlib.sha256(current).hexdigest()
    forbidden_call = re.compile(r'\b(?:UnitDamageTarget|widget_setLife|SetWidgetLife|SetUnitState|SetUnitLife|SetUnitMaxState|DamageEvent_abortCurrent|DamageEvent_setNextDamageElement|DamageEvent_setNextDamageType)\(')
    current_functions = JassScalarEvaluator(script).functions
    previous_functions = JassScalarEvaluator(baseline_script).functions
    for name, (_, lines) in current_functions.items():
        current_count = Counter(match[0] for line in lines for match in forbidden_call.finditer(line))
        previous_count = Counter(match[0] for line in previous_functions.get(name, ([], []))[1]
                                 for match in forbidden_call.finditer(line))
        require(not (current_count - previous_count), 'Forbidden new packaged damage/HP/abort/type/element compensation in ' + name)
    functions = JassScalarEvaluator(baseline_script).functions
    protected = [name for name in functions if re.match(
        r'td(?:Wave|GainGold|SpendGold|GetGold|AddScore|GetScore|SetLives|GetLives|HandleGameResolved|HandleEnemyDeath|MarkEnemyLeaked|TryScheduleNextWave|ShowVictory|ShowDefeat|LaneVictory|LaneDefeat|DamageCaptureHit|SetupDamageStatistics|EffectiveDamage)' , name)]
    require(len(protected) >= 30, 'Baseline lacks expected economy/victory/wave functions')
    for name in protected:
        require(canonical_function(script, name) == canonical_function(baseline_script, name),
                'Protected economy/victory/wave JASS changed: ' + name)
    return digests, len(protected)


def verify_compiled_structure(script):
    functions = JassScalarEvaluator(script).functions
    require(all(name in functions for name in (SCALE, CALLBACK, 'tdEnemyMechanicNativeSpellEligible',
            'TDEnemyMechanicState_scaledSpellAmount', 'spellDamage')), 'Missing packaged resistance API')
    for name in (SCALE, CALLBACK, 'TDEnemyMechanicState_scaledSpellAmount', 'spellDamage'):
        body = function_body(script, name)
        require(not re.search(r'\b(?:UnitDamageTarget|widget_setLife|SetUnitState|CreateUnit)\(', body),
                'Forbidden compensation/extra damage in packaged resistance helper ' + name)
    expected_owners = {'damage', 'tdPulseOrcBladestorm', 'tdHandleGhoulCorpseExplosionDamage',
                       'tdDealArcherSplitArrowAttackDamage', 'call_doAfter_TDEquipmentCombat',
                       'call_doAfter_TDEquipmentCombat_1'}
    actual_owners = {name for name, (_, lines) in functions.items()
                     if any(re.search(r'\bcall unit_damageTarget(?:_\d+)?\(', line) for line in lines)}
    require(actual_owners == expected_owners, 'Packaged exhaustive production damage-site inventory changed')
    raw_owners = {name for name, (_, lines) in functions.items()
                  if any(re.search(r'\bcall UnitDamageTarget\(', line) for line in lines)}
    require(raw_owners == {'unit_damageTarget', 'unit_damageTarget_1', 'DamageEvent_onDamage'},
            'Unexpected native damage compensation/probe call')
    return len(actual_owners)


def verify_artifact(map_path, baseline_map, source=None, baseline_source=None):
    artifact = Mpq(Path(map_path).read_bytes())
    baseline = Mpq(Path(baseline_map).read_bytes())
    script = artifact.extract('war3map.j').decode('utf-8')
    baseline_script = baseline.extract('war3map.j').decode('utf-8')
    digests, protected = verify_baseline(script, artifact, baseline_script, baseline)
    sites = verify_compiled_structure(script)
    if source is not None: verify_source_contract(source, baseline_source)
    pure = verify_pure_and_runtime(script)
    engine = verify_engine_and_accounting(script)
    zero = verify_zero_engine_event(script)
    verify_setup_lifecycle(script)
    paths = verify_scripted_damage(script)
    return dict(map_sha256=hashlib.sha256(Path(map_path).read_bytes()).hexdigest(),
                jass_sha256=hashlib.sha256(artifact.extract('war3map.j')).hexdigest(),
                state_cases=pure, engine_accounting_cases=engine, damage_sites=sites,
                zero_event_cases=zero,
                protected_functions=protected, object_sha256=digests, scripted_paths=paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map')
    parser.add_argument('--baseline-map', required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--baseline-source', type=Path)
    args = parser.parse_args()
    require(not args.baseline_source or args.source, '--baseline-source requires --source')
    result = verify_artifact(args.map, args.baseline_map, args.source, args.baseline_source)
    print('PASS final MPQ Boss resistance: actual helper/adapters/listener/setup/settlement functions and accounting capture/handoff executed; full objects and protected economy/victory unchanged')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    print('NOT TESTED: real trigger/timer timing, native shield absorption, Warcraft spell classification, UI or live gameplay; ledger credit and rendering are capture stubs.')


if __name__ == '__main__': main()
