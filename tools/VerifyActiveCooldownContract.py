#!/usr/bin/env python3
"""Fail-closed active-definition/source gate and real packaged MPQ/JASS gate.

Usage: python tools/VerifyActiveCooldownContract.py --source-only
       python tools/VerifyActiveCooldownContract.py map.w3x

Source evaluation consumes the production Wurst scalar functions. It is not
Wurst compilation. Object/JASS fixtures are explicitly synthetic; only the
positional map mode reads a real MPQ. No build or game is launched here.
"""
from __future__ import annotations

import argparse
import ast
from collections import namedtuple
import hashlib
import json
import math
import os
from pathlib import Path
import re

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyEquipmentInheritanceSource import lexical_tokens
from VerifySemanticIconArtifact import parse_objects
from VerifyTowerPlacementArtifact import unit_objects
from VerifyTowerUpgradeArtifact import JassScalarEvaluator, function_body
from VerifyBossSpellResistanceArtifact import BossJassRuntime

ROOT = Path(__file__).resolve().parents[1]
DATA = 'abilities/TDActiveSkillData.wurst'
OBJECT = 'abilities/TDActiveCooldownObjectGen.wurst'
RUNTIME = 'abilities/TDActiveCooldownRuntime.wurst'
ORDERS = {'bloodluston': 852102, 'bloodlustoff': 852103,
          'slowon': 852076, 'slowoff': 852077,
          'innerfireon': 852067, 'innerfireoff': 852068}


class ActiveJassRuntime(BossJassRuntime):
    """Existing bounded JASS interpreter, without unrelated Boss seed state."""
    def seed_record(self, *args, **kwargs):
        pass

    def native(self, name, args):
        if name in ('RMinBJ', 'IMinBJ'): return True, min(args)
        if name in ('RMaxBJ', 'IMaxBJ'): return True, max(args)
        if name in ('R2I', 'real_toInt'): return True, int(args[0])
        if name in ('I2R', 'int_toReal'): return True, float(args[0])
        if name in ('unit_getAbilityLevel', 'GetUnitAbilityLevel'):
            require((args[0], args[1]) in getattr(self, 'host_abilities', {}), 'Unseeded native host ability boundary')
            return True, self.host_abilities[args[0], args[1]]
        return super().native(name, args)


def rawcode(value):
    return int.from_bytes(value.encode('ascii'), 'big')


def rawstring(value):
    require(isinstance(value, int) and 0 < value <= 0xffffffff,
            f'Invalid ability rawcode {value!r}')
    return value.to_bytes(4, 'big').decode('ascii')


def uncomment(text):
    """Preserve strings and line positions; comments cannot forge contracts."""
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: m[0] if m[0][0] in '\"\'' else
                  ''.join('\n' if c == '\n' else ' ' for c in m[0]), text)


def source_functions(text):
    result = {}
    matches = list(re.finditer(r'^(?:@compiletime )?(?:public )?function (\w+)\(([^\n]*)\)([^\n]*)\n',
                              uncomment(text), re.M))
    for match in matches:
        end = match.end()
        for line in text[end:].splitlines(keepends=True):
            if line.strip() and not line[0].isspace():
                break
            end += len(line)
        args = [arg.strip().split()[-1] for arg in match[2].split(',')] if match[2].strip() else []
        result[match[1], len(args)] = (args, uncomment(text[match.end():end]))
    return result


def source_members(text):
    """Assign mutation calls to exact functions, including lifecycle members."""
    lines = uncomment(text).splitlines(keepends=True)
    result, classes = [], []
    for index, line in enumerate(lines):
        code = line.strip()
        if not code:
            continue
        indent = len(line[:len(line) - len(line.lstrip())].expandtabs(4))
        while classes and indent <= classes[-1][0]:
            classes.pop()
        declaration = re.match(r'(?:(?:public|private|protected|abstract|static)\s+)*class\s+(\w+)', code)
        if declaration:
            classes.append((indent, declaration[1]))
            continue
        declaration = re.match(r'(?:(?:@compiletime|public|private|protected|override|static)\s+)*'
                               r'(?:function\s+([\w.]+)\(([^\n]*)\)|'
                               r'(construct)\(([^\n]*)\)|(ondestroy)\b)', code)
        if not declaration:
            continue
        name = declaration[1] or declaration[3] or declaration[5]
        signature = declaration[2] or declaration[4] or ''
        params = [arg.strip().split()[-1] for arg in signature.split(',')] if signature.strip() else []
        end = index + 1
        while end < len(lines):
            next_line = lines[end]
            next_indent = len(next_line[:len(next_line) - len(next_line.lstrip())].expandtabs(4))
            if next_line.strip() and next_indent <= indent:
                break
            end += 1
        owner = classes[-1][1] + '.' + name if classes else name
        result.append((owner, params, ''.join(lines[index + 1:end])))
    return result


def require_unmodified_parameter(params, body, parameter, owner):
    require(parameter in params, 'Dynamic ability role requires actual parameter: ' + owner)
    require(not re.search(r'(?<![\w.])' + re.escape(parameter) + r'\s*(?:[+*/-]?=(?!=)|\+\+|--)', body),
            'Dynamic ability parameter rebound in approved owner: ' + owner)


def require_dynamic_role_binding(expression, params, body, owner):
    """Keep the small set of reviewed dynamic identities tied to their roots."""
    if expression == 'abilityId':
        require_unmodified_parameter(params, body, 'abilityId', owner)
        return
    if expression == 'record . abilityId':
        require_unmodified_parameter(params, body, 'record', owner)
        require(not re.search(r'\brecord\s*\.\s*abilityId\s*(?:[+*/-]?=(?!=)|\+\+|--)', body),
                'Native record identity rebound in approved owner: ' + owner)
        return
    bindings = {'displayOriginal': 'tdEvolutionDisplayOriginal(choice, branch)',
                'obsolete . abilId': 'tdSpecialStageBuff(war, previous)',
                'obsolete . buffId': 'tdSpecialStageBuff(war, previous)',
                'previousCarrier': 'tdAuraRankCarrier(identity, previousRank)',
                'previous . buffId': 'tdAuraBuff(identity, previousRank)'}
    if expression in bindings:
        root = expression.split()[0]
        writes = re.findall(r'(?<![\w.])' + re.escape(root) + r'\s*([+*/-]?=)(?!=)\s*([^\n]*)', body)
        require(len(writes) == 1 and writes[0][0] == '=' and canonical(writes[0][1]) == canonical(bindings[expression]),
                'Dynamic ability role root rebound or initializer changed: ' + owner + ':' + root)
        require(not re.search(r'\b' + re.escape(root) + r'\s*(?:\+\+|--)|\b' + re.escape(root) +
                              r'\s*\.\s*\w+\s*(?:[+*/-]?=(?!=)|\+\+|--)', body),
                'Dynamic ability role identity rebound: ' + owner + ':' + expression)
    elif expression == 'TD_WAR_INTENT_SPEED_CARRIER':
        require(not re.search(r'(?<![\w.])TD_WAR_INTENT_SPEED_CARRIER\s*(?:[+*/-]?=(?!=)|\+\+|--)', body),
                'Dynamic support carrier identity rebound: ' + owner)


def state_methods(text):
    match = re.search(r'^public class TDActiveNativeCooldownState\n((?:\t[^\n]*\n|\n)*)', text, re.M)
    require(match is not None, 'Missing shared production native cooldown state')
    body = '\n'.join(line[1:] if line.startswith('\t') else line for line in match[1].splitlines()) + '\n'
    body = re.sub(r'^construct\(', 'function construct(', body, flags=re.M)
    return source_functions(body)


class Expression:
    """Small Wurst scalar grammar, with lazy boolean/ternary evaluation."""
    OPERATORS = {'or': 1, 'and': 2, '==': 3, '!=': 3, '<': 3, '>': 3,
                 '<=': 3, '>=': 3, '+': 4, '-': 4, '*': 5, '/': 5, 'div': 5, 'mod': 5}

    def __init__(self, text):
        self.tokens = [t[0] for t in lexical_tokens(text)]
        self.index = 0

    def take(self):
        require(self.index < len(self.tokens), 'Incomplete scalar expression')
        value = self.tokens[self.index]
        self.index += 1
        return value

    def peek(self):
        return self.tokens[self.index] if self.index < len(self.tokens) else ''

    def parse(self, minimum=0):
        token = self.take()
        if token in ('not', '-', '+'):
            left = ('unary', token, self.parse(6))
        elif token == '(':
            left = self.parse()
            require(self.take() == ')', 'Unclosed scalar parentheses')
        elif token.startswith('"'):
            left = ('value', ast.literal_eval(token))
        elif token.startswith("'"):
            left = ('value', rawcode(ast.literal_eval(token)))
        elif re.fullmatch(r'\d+(?:\.\d*)?', token):
            left = ('value', float(token) if '.' in token else int(token))
        else:
            require(re.fullmatch(r'\w+', token), 'Unsupported scalar token ' + token)
            left = ('name', token)
        while True:
            token = self.peek()
            if token == '.':
                self.take()
                left = ('attribute', left, self.take())
            elif token == '(':
                self.take()
                args = []
                if self.peek() != ')':
                    while True:
                        args.append(self.parse())
                        if self.peek() != ',':
                            break
                        self.take()
                require(self.take() == ')', 'Unclosed scalar call')
                left = ('call', left, args)
            elif token in self.OPERATORS and self.OPERATORS[token] >= minimum:
                self.take()
                left = ('binary', token, left, self.parse(self.OPERATORS[token] + 1))
            elif token == '?' and minimum == 0:
                self.take()
                yes = self.parse()
                require(self.take() == ':', 'Missing scalar ternary colon')
                left = ('ternary', left, yes, self.parse())
            else:
                return left


class SourceScalarEvaluator:
    """Interpret only the production scalar subset; unknown code fails closed."""
    def __init__(self, sources):
        self.sources = sources
        self.orders = dict(ORDERS)
        if '__stdlib_orders__' in sources:
            self.orders.update({name: int(value) for name, value in re.findall(r'\bstatic constant (\w+)\s*=\s*(\d+)', sources['__stdlib_orders__'])})
        self.functions, self.constants, self.tuples = {}, {}, {}
        for text in sources.values():
            self.functions.update(source_functions(text))
            self.constants.update(re.findall(r'^(?:public )?constant (?:int|real|boolean|string) (\w+) = ([^\n]+)',
                                             uncomment(text), re.M))
            for name, fields in re.findall(r'^(?:public )?tuple (\w+)\(([^\n]+)\)', uncomment(text), re.M):
                self.tuples[name] = namedtuple(name, [f.strip().split()[-1] for f in fields.split(',')])
        self.methods = state_methods(sources[DATA]) if DATA in sources else {}
        self.resolved = {'true': True, 'false': False, 'null': None}

    def constant(self, name):
        if name not in self.resolved:
            require(name in self.constants, 'Unknown Wurst scalar ' + name)
            self.resolved[name] = self.expression(self.constants[name], {})
        return self.resolved[name]

    def expression(self, text, scope):
        parser = Expression(text)
        tree = parser.parse()
        require(not parser.peek(), 'Unsupported trailing scalar tokens: ' + text)
        def read(node):
            kind = node[0]
            if kind == 'value':
                return node[1]
            if kind == 'name':
                return scope[node[1]] if node[1] in scope else self.constant(node[1])
            if kind == 'attribute':
                if node[1] == ('name', 'Orders'):
                    require(node[2] in self.orders, 'Unknown autocast order; provide locked stdlib source: ' + node[2])
                    return self.orders[node[2]]
                return getattr(read(node[1]), node[2])
            if kind == 'unary':
                value = read(node[2])
                return not value if node[1] == 'not' else -value if node[1] == '-' else value
            if kind == 'ternary':
                return read(node[2] if read(node[1]) else node[3])
            if kind == 'binary':
                op, left = node[1], read(node[2])
                if op == 'and': return bool(left) and bool(read(node[3]))
                if op == 'or': return bool(left) or bool(read(node[3]))
                right = read(node[3])
                return {'==': lambda: left == right, '!=': lambda: left != right,
                        '<': lambda: left < right, '>': lambda: left > right,
                        '<=': lambda: left <= right, '>=': lambda: left >= right,
                        '+': lambda: left + right, '-': lambda: left - right,
                        '*': lambda: left * right, '/': lambda: left / right,
                        'div': lambda: int(left / right), 'mod': lambda: left % right}[op]()
            if kind == 'call':
                target, args = node[1], [read(a) for a in node[2]]
                if target[0] == 'attribute':
                    value, method = read(target[1]), target[2]
                    require(not args and method in ('toRawCode', 'toInt', 'toString'),
                            'Unsupported scalar method ' + method)
                    return rawstring(value) if method == 'toRawCode' else int(value) if method == 'toInt' else str(value)
                require(target[0] == 'name', 'Unsupported indirect scalar call')
                name = target[1]
                if name in self.tuples: return self.tuples[name](*args)
                if name in ('RMinBJ', 'IMinBJ', 'min'): return min(args)
                if name in ('RMaxBJ', 'IMaxBJ', 'max'): return max(args)
                if name == 'R2I': return int(args[0])
                if name == 'I2R': return float(args[0])
                if name == 'commaList': return ','.join(rawstring(a) for a in args)
                return self.call(name, args)
            raise ValueError('Unsupported scalar node ' + repr(node))
        return read(tree)

    def body(self, name, arity=None):
        candidates = [value for (key, n), value in self.functions.items() if key == name and (arity is None or n == arity)]
        require(len(candidates) == 1, 'Missing or ambiguous Wurst function ' + name)
        return candidates[0][1]

    def call(self, name, values, fields=None):
        require((name, len(values)) in self.functions, 'Missing Wurst scalar function ' + name)
        args, body = self.functions[name, len(values)]
        scope = {**(fields or {}), **dict(zip(args, values))}
        lines = [(len(line) - len(line.lstrip()), line.strip()) for line in body.expandtabs(4).splitlines() if line.strip()]
        def block(start, end):
            i = start
            while i < end:
                indent, line = lines[i]
                child = i + 1
                while child < end and lines[child][0] > indent: child += 1
                if line.startswith('if '):
                    selected = bool(self.expression(line[3:], scope))
                    if selected:
                        result = block(i + 1, child)
                        if result is not None: return result
                    i = child
                    while i < end and lines[i][0] == indent and lines[i][1].startswith('else'):
                        next_child = i + 1
                        while next_child < end and lines[next_child][0] > indent: next_child += 1
                        condition = not selected and (lines[i][1] == 'else' or bool(self.expression(lines[i][1][8:], scope)))
                        if condition:
                            result = block(i + 1, next_child)
                            if result is not None: return result
                            selected = True
                        i = next_child
                    continue
                if line.startswith('for '):
                    match = re.fullmatch(r'for (\w+) = (.+) to (.+)', line)
                    require(match is not None, name + ': unsupported scalar loop')
                    first, last = (int(self.expression(match[n], scope)) for n in (2, 3))
                    require(last - first < 512, name + ': scalar loop limit')
                    for value in range(first, last + 1):
                        scope[match[1]] = value
                        result = block(i + 1, child)
                        if result is not None: return result
                    i = child
                    continue
                if line.startswith('return '): return (self.expression(line[7:], scope),)
                assignment = re.fullmatch(r'(?:(?:let|var) )?(\w+) (=|\+=|-=) (.+)', line)
                require(assignment is not None, name + ': unsupported scalar statement: ' + line)
                value = self.expression(assignment[3], scope)
                scope[assignment[1]] = value if assignment[2] == '=' else scope[assignment[1]] + value if assignment[2] == '+=' else scope[assignment[1]] - value
                i += 1
            return None
        result = block(0, len(lines))
        if fields is not None:
            fields.update({key: scope[key] for key in fields})
            return None if result is None else result[0]
        require(result is not None, name + ': scalar path returned no value')
        return result[0]

    def call_state_method(self, name, fields, values):
        require((name, len(values)) in self.methods, 'Missing production state method ' + name)
        key = 'TDActiveNativeCooldownState_' + name, len(values)
        self.functions[key] = self.methods[name, len(values)]
        return self.call(key[0], values, fields)


def read_sources(root=ROOT):
    root = Path(root)
    result = {p.relative_to(root / 'wurst').as_posix(): p.read_text(encoding='utf-8')
              for p in (root / 'wurst').rglob('*.wurst') if '_tests' not in p.parts}
    lock = root / 'tools/stdlib/lock.json'
    candidates = [root / '_build/dependencies/WurstStdlib2-source']
    if lock.is_file(): candidates.append(Path(json.loads(lock.read_text(encoding='utf-8'))['source']))
    if os.environ.get('WURST_STDLIB_SOURCE'): candidates.insert(0, Path(os.environ['WURST_STDLIB_SOURCE']))
    for candidate in candidates:
        orders = candidate / 'wurst/_wurst/Orders.wurst'
        if orders.is_file():
            result['__stdlib_orders__'] = orders.read_text(encoding='utf-8')
            break
    return result


def definitions(evaluator):
    count = evaluator.call('tdActiveSkillDefinitionCount', [])
    require(isinstance(count, int) and 0 < count < 512, 'Invalid active definition count')
    body = evaluator.body('tdActiveSkillDefinitionAt')
    indices = [int(x) for x in re.findall(r'^\s*if index == (\d+)\s*$', body, re.M)]
    require(sorted(indices) == list(range(count)), 'Active definition count/enumeration mismatch')
    values = [evaluator.call('tdActiveSkillDefinitionAt', [i]) for i in range(count)]
    native = evaluator.constant('TD_ACTIVE_DRIVER_NATIVE_ABILITY')
    pet = evaluator.constant('TD_ACTIVE_DRIVER_PET_PROC')
    require(native != pet, 'Active driver identities collide')
    for value in values:
        require(value.key > 0 and value.baseCooldown > 0 and math.isfinite(value.baseCooldown), 'Invalid active key/base cooldown')
        require(value.driver in (native, pet), 'Unknown active driver')
        require(value.initialAutocastChoice in (0, 1, 2), 'Invalid initial autocast choice')
        if value.driver == native:
            rawstring(value.abilityId)
            require(value.petSkillId == -1, 'Native definition has pet skill')
            require((value.autocastOnOrder == value.autocastOffOrder == 0) or
                    (value.autocastOnOrder > 0 and value.autocastOffOrder > 0 and value.autocastOnOrder != value.autocastOffOrder),
                    'Invalid native autocast orders')
            pairs = {(order, evaluator.orders[name[:-2] + 'off']) for name, order in evaluator.orders.items()
                     if name.endswith('on') and name[:-2] + 'off' in evaluator.orders}
            require((value.autocastOnOrder, value.autocastOffOrder) in pairs or
                    (value.autocastOnOrder == value.autocastOffOrder == value.initialAutocastChoice == 0),
                    'Native autocast orders must be a verified on/off pair')
        else:
            require(value.abilityId == 0 and value.petSkillId >= 0 and value.autocastOnOrder == value.autocastOffOrder == value.initialAutocastChoice == 0,
                    'Invalid pet active definition')
    for attr, subset in [('key', values), ('abilityId', [d for d in values if d.driver == native]),
                         ('petSkillId', [d for d in values if d.driver == pet])]:
        keys = [getattr(d, attr) for d in subset]
        require(len(keys) == len(set(keys)), 'Duplicate active ' + attr)
    for value in values:
        require(evaluator.call('tdActiveSkillDefinitionForKey', [value.key]) == value, 'Active key lookup omitted definition')
        lookup = 'tdActiveSkillDefinitionForAbility' if value.driver == native else 'tdActiveSkillDefinitionForPetSkill'
        identity = value.abilityId if value.driver == native else value.petSkillId
        require(evaluator.call(lookup, [identity]) == value, 'Active driver lookup omitted definition')
    for name in ('tdActiveSkillDefinitionForKey', 'tdActiveSkillDefinitionForAbility', 'tdActiveSkillDefinitionForPetSkill'):
        require(evaluator.call(name, [-987654]).key == 0, 'Unknown active identity must be invalid')
    return values


def verify_scalar_rules(evaluator, active):
    require(evaluator.constant('TD_ACTIVE_NATIVE_LEVEL_COUNT') == 41, 'Native cooldown must have 41 physical levels')
    for personal, inspiration, aura in ((0., 0., 0.), (0., 0., .18), (0., .06, .18), (0., .12, .18),
                                      (0., .18, .18), (0., .24, .18), (.1, .12, .18), (-.1, .06, -.1)):
        expected = min(.4, max(0., personal) + max(0., inspiration) + max(0., aura))
        require(math.isclose(evaluator.call('tdFinalCooldownReduction', [personal, inspiration, aura]), expected),
                'Cooldown sources must aggregate once with the shared 40% cap')
    for value in active:
        for reduction in (-0.25, 0, .06, .12, .18, .184, .186, .24, .30, .36, .40, .42, .9):
            expected = value.baseCooldown * (1 - min(.40, max(0, reduction)))
            require(math.isclose(evaluator.call('tdActiveCooldownDuration', [value.baseCooldown, reduction]), expected, abs_tol=1e-9), 'Production duration/cap formula changed')
            require(math.isclose(evaluator.call('tdActiveCooldownReadyAt', [123., value.baseCooldown, reduction]), 123 + expected, abs_tol=1e-9), 'Production readyAt formula changed')
            level = evaluator.call('tdActiveCooldownNativeLevel', [reduction])
            require(level == int(min(.40, max(0, reduction)) * 100 + .5) + 1, 'Native level rounding/cap changed')
        if value.petSkillId >= 0:
            require(evaluator.call('tdPetSkillIsActive', [value.petSkillId]) is True, 'Pet active lookup excluded shared definition')
    require(evaluator.call('tdPetSkillIsActive', [-999]) is False, 'Unknown pet skill classified as active')
    for level in range(1, 42):
        require(math.isclose(evaluator.call('tdActiveCooldownReductionAtNativeLevel', [level]), (level - 1) / 100), 'Native level decode changed')
    for level in (-1, 0, 42, 100):
        require(evaluator.call('tdActiveCooldownNativeLevelValid', [level]) is False, 'Out-of-range native gameplay/CDR level must be rejected')
    for native in (False, True):
        for binding in (False, True):
            for unlocked in (False, True):
                require(evaluator.call('tdAuraCooldownTargetSupported', [native, binding, unlocked]) == (native or (binding and unlocked)), 'Generic aura native/binding/slot rule changed')
    for now, ready_at, actual, desired, busy in ((9., 10., 1, 41, False), (10., 10., 1, 41, True),
                                               (10., 10., 0, 41, False), (10., 10., 41, 41, False), (10., 10., 1, 41, False)):
        require(evaluator.call('tdActiveCooldownNeedsNativeLevel', [now, ready_at, actual, desired, busy]) ==
                (not busy and actual > 0 and actual != desired and now >= ready_at), 'Source same-level/busy/deadline rule changed')


# These are reviewed native roles, not CDR eligibility. Unknown parents fail
# closed, including objects which omit acdn and inherit their parent's CD.
PASSIVE_PARENTS = frozenset(('AEar', 'AHbh', 'AIat', 'AIcd', 'AId1', 'AIl2', 'AInv',
                             'AIsr', 'AIsx', 'AOcr', 'Aasl', 'Adef', 'Apiv', 'Aro1', 'Aspo'))
WRAPPER_PARENTS = {'AbilityDefinitionBloodlust': 'Ablo', 'AbilityDefinitionSlow': 'Aslo',
                   'AbilityDefinitionBladeMasterCriticalStrike': 'AOcr',
                   'AbilityDefinitionMoonPriestessTrueshotAura': 'AEar',
                   'AbilityDefinitionMountainKingBash': 'AHbh', 'AbilityDefinitionAuraSlow': 'Aasl',
                   'AbilityDefinitionSlowPoison': 'Aspo', 'AbilityDefinitionAttackSpeedIncrease': 'AIsx',
                   'AbilityDefinitionDefenseBonusPlus1': 'AId1', 'AbilityDefinitionAttackBonus': 'AIat',
                   'AbilityDefinitionInventory': 'AInv', 'AbilityDefinitionSpellBook': 'Aspb',
                   'AbilityDefinitionItemAuraCommand': 'AIcd',
                   'ChannelAbilityPreset': 'ANcl', 'AbilityDefinitionMountainKingThunderBolt': 'AHtb'}
NATIVE_EFFECTS = {'Ablo': {'setAttackSpeedIncrease': ('Blo1', 2, 1), 'setMovementSpeedIncrease': ('Blo2', 2, 2),
                          'setScalingFactor': ('Blo3', 2, 3)},
                  'Aslo': {'setMovementSpeedFactor': ('Slo1', 2, 1), 'setAttackSpeedFactor': ('Slo2', 2, 2),
                          'setAlwaysAutocast': ('Slo3', 0, 3)}}
COMMON_EFFECTS = {'setManaCost': ('amcs', 0, 0), 'setCastRange': ('aran', 2, 0),
                  'setTargetsAllowed': ('atar', 3, 0), 'setBuffs': ('abuf', 3, 0),
                  'setDurationNormal': ('adur', 2, 0), 'setDurationHero': ('ahdu', 2, 0)}


def calls(body, name):
    tokens = lexical_tokens(body)
    result = []
    for i, (token, _, kind) in enumerate(tokens):
        if token != name or kind != 'identifier' or i + 1 >= len(tokens) or tokens[i + 1][0] != '(':
            continue
        depth, args, start = 0, [], i + 2
        for j in range(i + 1, len(tokens)):
            value = tokens[j][0]
            if value == '(':
                depth += 1
            elif value == ')':
                depth -= 1
                if depth == 0:
                    if j > start: args.append(' '.join(t[0] for t in tokens[start:j]))
                    break
            elif value == ',' and depth == 1:
                args.append(' '.join(t[0] for t in tokens[start:j]))
                start = j + 1
        else:
            raise ValueError('Unbalanced source call ' + name)
        result.append(args)
    return result


def canonical(text):
    return ' '.join(token[0] for token in lexical_tokens(text))


def channel_operations(body):
    """Resolve each Channel cascade to its constructed rawcode expression."""
    variables, receiver, result = {}, None, []
    for line in uncomment(body).splitlines():
        code = line.strip()
        if not code:
            continue
        constructors = calls(line, 'ChannelAbilityPreset')
        if constructors:
            require(len(constructors) == 1, 'Ambiguous Channel operation construction')
            receiver = canonical(constructors[0][0])
            assignment = re.match(r'(?:let|var)\s+(\w+)\s*=\s*new\s+ChannelAbilityPreset\b', code)
            if assignment:
                variables[assignment[1]] = receiver
        elif not code.startswith('..'):
            direct = re.match(r'(\w+)\s*(?:$|\.\.)', code)
            receiver = variables.get(direct[1]) if direct else None
        for arguments in calls(line, 'makeUnitSpell'):
            require(receiver is not None, 'Unresolved Channel operation rawcode receiver')
            result.append((receiver, arguments))
    return result


def source_native_objects(evaluator, active):
    """Resolve standard constructors -> configuration function -> shared key."""
    native = {d.key: d for d in active if d.abilityId}
    configured = {}
    for (name, arity), (params, body) in evaluator.functions.items():
        if name == 'tdConfigureActiveNativeCooldown': continue
        for arguments in calls(body, 'tdConfigureActiveNativeCooldown'):
            require(len(arguments) == 2, 'Invalid standard object helper invocation')
            key = evaluator.expression(arguments[1], {})
            require(key in native, 'Object helper references undefined/non-native active key')
            value = native[key]
            # Direct synthetic/new generation is supported as well as the
            # existing typed configuration function facade.
            first = canonical(arguments[0])
            constructor = re.fullmatch(r'new (\w+) \( (.+) \)', first)
            candidates = []
            if constructor:
                candidates.append((constructor[1], evaluator.expression(constructor[2], {})))
            elif first in params:
                for (_, _), (_, caller) in evaluator.functions.items():
                    variables = {m[1]: (m[2], m[3]) for m in re.finditer(r'\blet (\w+) = new (\w+)\(([^\n]*)\)', caller)}
                    for invocation in calls(caller, name):
                        variable = canonical(invocation[params.index(first)])
                        if variable in variables:
                            wrapper, identity = variables[variable]
                            candidates.append((wrapper, evaluator.expression(identity, {})))
            else:
                variables = {m[1]: (m[2], m[3]) for m in re.finditer(r'\blet (\w+) = new (\w+)\(([^\n]*)\)', body)}
                require(first in variables, 'Unresolved active object helper receiver')
                wrapper, identity = variables[first]
                candidates.append((wrapper, evaluator.expression(identity, {})))
            require(candidates, 'Shared active object helper has no resolvable construction')
            for wrapper, identity in candidates:
                require(identity == value.abilityId, 'Active object rawcode/key mismatch')
                require(wrapper in WRAPPER_PARENTS, 'Unknown native active wrapper/parent')
                parent = WRAPPER_PARENTS[wrapper]
                require(parent in NATIVE_EFFECTS, 'New active parent requires explicit effect-field schema')
                code = rawstring(identity)
                require(code not in configured, 'Duplicate native active object configuration')
                fields = {}
                for method, (field, kind, column) in {**COMMON_EFFECTS, **NATIVE_EFFECTS[parent]}.items():
                    setters = calls(body, method)
                    require(len(setters) == 1 and canonical(setters[0][0]) == 'level', code + ': complete native effect field missing: ' + method)
                    for level in range(1, 42):
                        expected = evaluator.expression(setters[0][1], {'level': level})
                        fields[field, level, column] = (kind, int(expected) if kind == 0 else expected)
                configured[code] = (parent, fields)
    require(set(configured) == {rawstring(d.abilityId) for d in native.values()}, 'Native definition missing standard object helper')
    return configured


def source_towers(evaluator):
    result = {}
    choices = sorted({evaluator.constant(name) for name in evaluator.constants if name.startswith('TD_TOWER_CHOICE_') and name != 'TD_TOWER_CHOICE_NONE'})
    for choice in choices:
        maximum = evaluator.call('tdTowerMaxLevel', [choice])
        for level in range(1, maximum + 1):
            branches = evaluator.call('tdTowerUltimateBranchCount', [choice]) if level == maximum else 1
            for branch in range(1, branches + 1):
                uid = rawstring(evaluator.call('tdTowerUnitIdForLevelBranch', [choice, level, branch]))
                abilities = evaluator.call('tdTowerNormalAbilitiesRawcodesForBranch', [choice, level, branch]).split(',')
                abilities += [rawstring(evaluator.constant(name)) for name in ('TD_TOWER_INVENTORY_ABILITY_ID', 'TD_TOWER_SELL_ABILITY_ID', 'TD_TOWER_EVOLUTION_PROGRESS_ABILITY_ID')]
                result[uid] = abilities
    require(result, 'No resolvable tower hosts')
    return result


def source_mount_roles(evaluator, towers, active):
    """Reverse the real mount table and constructor roles, never assume zero CD."""
    parents = {}
    for (name, _), (params, body) in evaluator.functions.items():
        for wrapper in (*WRAPPER_PARENTS, 'AbilityDefinition'):
            for arguments in calls(body, wrapper):
                first = arguments[0]
                identities = []
                if first in params:
                    index = params.index(first)
                    for (_, _), (_, caller) in evaluator.functions.items():
                        for invocation in calls(caller, name):
                            try:
                                identities.append(evaluator.expression(invocation[index], {}))
                            except ValueError:
                                # Non-scalar UI/data objects never enter the
                                # tower mounting contract. Mounted unknown IDs
                                # still fail below; this is not a zero-CD guess.
                                pass
                else:
                    try:
                        identities.append(evaluator.expression(first, {}))
                    except ValueError:
                        pass
                parent = rawstring(evaluator.expression(arguments[1], {})) if wrapper == 'AbilityDefinition' else WRAPPER_PARENTS[wrapper]
                for identity in identities:
                    if isinstance(identity, int) and identity:
                        code = rawstring(identity)
                        require(code not in parents or parents[code] == parent, 'Conflicting generated parent for ' + code)
                        parents[code] = parent
    native = {rawstring(d.abilityId) for d in active if d.abilityId}
    mounts = {code for abilities in towers.values() for code in abilities}
    # Replacement data is evaluated before build, and checked again against
    # actual MPQ/JASS. Native rawcodes cannot enter a passive replacement path.
    for name in ('tdEvolutionSkillReplacement', 'tdEvolutionSkillOriginal', 'tdEvolutionDisplayReplacement', 'tdEvolutionDisplayOriginal'):
        for choice in range(1, 6):
            for branch in (1, 2):
                identity = evaluator.call(name, [choice, branch])
                if identity:
                    code = rawstring(identity)
                    require(code not in native, 'Native active replacement/remount lacks engine CD migration')
                    mounts.add(code)
    for code in mounts:
        require(code in parents, 'Undefined/unresolved mounted ability object: ' + code)
        if code not in native:
            # The only tower-owned management Channel is the zero-CD sell
            # command. Farmer salary/craft/UI responsibilities cannot migrate
            # to a tower merely by reusing their owner function or parent.
            tower_command = parents[code] == 'ANcl' and code == rawstring(evaluator.constant('TD_TOWER_SELL_ABILITY_ID'))
            require(parents[code] in PASSIVE_PARENTS or tower_command,
                    'Undefined mounted combat active/unknown parent: ' + code + ':' + parents[code])
    native_ids = {d.abilityId for d in active if d.abilityId}
    removal_roles = {('towers/TDTowerEvolutionRuntime.wurst', 'tdEvolutionRefresh'): {'tdEvolutionSkillOriginal ( choice , branch )', 'displayOriginal'},
                     ('items/TDInventoryRuntime.wurst', 'tdSetTowerEquipmentAbilityLevel'): {'abilityId'},
                     ('items/TDEquipmentSpecialState.wurst', 'tdSpecialSyncBuff'): {'obsolete . abilId', 'obsolete . buffId'},
                     ('items/TDEquipmentSpecialState.wurst', 'tdEquipmentSpecialSyncStages'): {'TD_WAR_INTENT_SPEED_CARRIER'},
                     ('auras/TDAuraState.wurst', 'tdAuraSyncDisplayedRank'): {'previousCarrier', 'previous . buffId'},
                     ('pets/TDPetCombat.wurst', 'setBonus'): {'abilityId'}}
    setter_roles = {('items/TDInventoryRuntime.wurst', 'tdSetTowerEquipmentAbilityLevel'): {'abilityId'},
                    ('items/TDEquipmentAbilities.wurst', 'tdEquipmentSyncControl'): {'abilityId'},
                    ('pets/TDPetCombat.wurst', 'setBonus'): {'abilityId'},
                    (RUNTIME, 'tdApplyNativeActiveCooldownLevel'): {'record . abilityId'}}
    parameter_roles = {('items/TDInventoryRuntime.wurst', 'tdSetTowerEquipmentAbilityLevel'),
                       ('items/TDEquipmentAbilities.wurst', 'tdEquipmentSyncControl'),
                       ('pets/TDPetCombat.wurst', 'setBonus')}
    for path, source in evaluator.sources.items():
        members = source_members(source)
        for owner, params, body in members:
            if (path, owner) in parameter_roles:
                require(params == ['tower', 'abilityId', 'level'], 'Dynamic support owner parameter contract changed: ' + path + ':' + owner)
                require_unmodified_parameter(params, body, 'abilityId', path + ':' + owner)
        for methods, roles, unknown, violation in [
                (('removeAbility', 'UnitRemoveAbility'), removal_roles, 'Unknown dynamic native removal/migration source: ', 'Native active removal/remount lacks engine CD migration'),
                (('setAbilityLevel', 'SetUnitAbilityLevel'), setter_roles, 'Unknown dynamic native level write: ', 'Native active level write bypasses readyAt runtime: ')]:
            for method in methods:
                accounted = 0
                for owner, params, body in members:
                    for arguments in calls(body, method):
                        accounted += 1
                        expression = canonical(arguments[0] if method in ('removeAbility', 'setAbilityLevel') else arguments[1])
                        try:
                            identity = evaluator.expression(expression, {})
                        except (ValueError, AttributeError):
                            require(expression in roles.get((path, owner), set()), unknown + path + ':' + owner)
                            require_dynamic_role_binding(expression, params, body, path + ':' + owner)
                            continue
                        require(identity not in native_ids, violation + path + ':' + owner)
                require(accounted == len(calls(source, method)), 'Unclassified outside-function native mutation: ' + path + ':' + method)
        for name in ('tdSetTowerEquipmentAbilityLevel', 'setBonus', 'tdEquipmentSyncControl'):
            accounted = sum(owner.rsplit('.', 1)[-1] == name for owner, _, _ in members)
            for owner, _, body in members:
                for arguments in calls(body, name):
                    accounted += 1
                    require(len(arguments) >= 2, 'Invalid support ability call: ' + name)
                    try:
                        identity = evaluator.expression(arguments[1], {})
                    except (ValueError, AttributeError):
                        raise ValueError('Unresolved dynamic support ability source: ' + path + ':' + owner + ':' + name)
                    require(identity not in native_ids, 'Native active support mount lacks engine CD migration')
            require(accounted == len(calls(source, name)), 'Unclassified outside-function support ability call: ' + path + ':' + name)
    return parents


def verify_runtime_sources(evaluator):
    native_source = evaluator.sources[RUNTIME]
    identity_writes = []
    for owner, params, body in source_members(native_source):
        for receiver, operator, expression in re.findall(r'\b(\w+)\s*\.\s*abilityId\s*([+*/-]?=)(?!=)\s*([^\n]*)', body):
            require(owner == 'TDNativeActiveCooldown.construct' and params == ['tower', 'abilityId'] and
                    receiver == 'this' and operator == '=' and canonical(expression) == 'abilityId',
                    'Native record identity write outside immutable constructor: ' + owner)
            identity_writes.append(owner)
    require(identity_writes == ['TDNativeActiveCooldown.construct'], 'Native record identity initialization contract changed')
    for name in ('tdHasNativeActiveCooldown', 'tdRefreshNativeActiveCooldowns'):
        body = evaluator.body(name)
        for token in ('tdActiveSkillDefinitionCount()', 'tdActiveSkillDefinitionAt(', 'TD_ACTIVE_DRIVER_NATIVE_ABILITY', 'getAbilityLevel('):
            require(token in body, name + ': missing metadata-driven native consumer ' + token)
    for path, names in [(RUNTIME, ('tdHasNativeActiveCooldown', 'tdRefreshNativeActiveCooldowns')),
                        ('auras/TDAuraRuntime.wurst', ('tdAuraCooldownTargetEligible',))]:
        for name in names:
            body = evaluator.body(name)
            require(not re.search(r'TD_ORC_(?:BLOODLUST|BLADESTORM)_ABILITY_ID|\bskill\s*(?:>=|<=|==)\s*(?:11|15)', body), name + ': legacy cooldown eligibility whitelist')
    host = evaluator.body('tdHostActiveCooldownReduction')
    for token in ('tdFinalCooldownReduction(', 'tdEquipmentEffectForItems(', 'tdPetCooldownReduction(', 'tdAuraPower('):
        require(len(calls(host, token[:-1])) == 1, 'Host cooldown source must be accumulated once: ' + token)
    require(host.count('TD_AURA_EQUIPMENT_COOLDOWN') == 1, 'Duplicate aura cooldown contribution')
    refresh = evaluator.body('tdRefreshNativeActiveCooldowns')
    require(calls(refresh, 'tdFinalCooldownReduction') == [['personalReduction', 'tdPetCooldownReduction ( tower )', 'tdAuraPower ( tower , TD_AURA_EQUIPMENT_COOLDOWN )']],
            'Native refresh must use excluded-loadout personal snapshot and accumulate aura once')
    aura = evaluator.body('tdAuraCooldownTargetEligible')
    for token in ('tdPetBindingValid(pet, target, pet.generation)', 'tdPetUnlockedSlots(pet.level)',
                  'pet.skillCount', 'tdPetSkillFitsHost(skill, target)', 'tdPetSkillIsActive(skill)', 'tdHasNativeActiveCooldown(target)'):
        require(token in aura, 'Aura active eligibility missing binding/slot/metadata guard: ' + token)
    require('tdActiveSkillDefinitionForPetSkill(skill)' in evaluator.body('tdPetSkillIsActive'), 'Pet classifier must consume shared metadata, not old eligibility whitelist')
    require('aggregate.offer(TD_AURA_PET_COMMAND' not in evaluator.body('tdAuraOfferSource') and 'aggregate.offer(TD_AURA_PET_STASIS' not in evaluator.body('tdAuraOfferSource'), 'Retired pet aura source scan remains')
    pet_attack = evaluator.body('onAttack')
    for token in ('tdPetBindingValid(pet, host, pet.generation)', 'tdPetUnlockedSlots(pet.level)',
                  'tdPetSkillIsActive(skill)', 'tdPetBindingValid(pet, host, generation)', 'pet.pendingSerial == pendingSerial', 'if not found'):
        require(token in pet_attack, 'Pet successful active missing binding/slot/generation/target guard: ' + token)
    helper = evaluator.body('tdConfigureActiveNativeCooldown')
    for token in ('tdActiveSkillDefinitionForKey(activeKey)', 'active.driver', 'definition.getNewId()',
                  'definition.getLevels() != 1', 'TD_ACTIVE_NATIVE_LEVEL_COUNT', 'tdActiveCooldownDuration(', 'tdActiveCooldownReductionAtNativeLevel(level)'):
        require(token in helper, 'Native object contract missing ' + token)
    require(len(calls(helper, 'setCooldown')) == 1, 'Shared object helper must own one cooldown write')
    require(native_source.count('doPeriodically(0.10)') == 1, 'Exactly one native 0.10 timer required')
    require('EVENT_PLAYER_UNIT_SPELL_EFFECT' in native_source, 'Missing generic native cast event')
    # Only the cast handler may set an established native deadline. Constructor
    # initialization is permitted, refresh/timer writes are not.
    writes = []
    for path, source in evaluator.sources.items():
        for match in re.finditer(r'(?<!\w)(\w+)\.readyAt\s*(=|\+=|-=)\s*([^\n]+)', uncomment(source)):
            receiver, operator, expression = match.groups()
            require(operator == '=', 'Script active deadline cannot be incrementally rewritten: ' + path)
            if path == 'pets/TDPetCombat.wurst':
                require(receiver == 'pet' and expression.startswith('tdStartScriptActiveCooldown('), 'Script active readyAt bypasses shared runtime')
            else:
                raise ValueError('Unclassified script readyAt write: ' + path)
            writes.append(path)
    require(writes.count('pets/TDPetCombat.wurst') == 1, 'Missing pet cooldown ownership write')
    methods = state_methods(evaluator.sources[DATA])
    start_cast = methods['startCast', 3][1]
    require(canonical(start_cast) == canonical('readyAt = tdActiveCooldownReadyAt(now, baseCooldown, tdActiveCooldownReductionAtNativeLevel(actualLevel))'),
            'Native readyAt must use cast actual physical level and unified deadline')
    require(canonical(methods['requestLevel', 1][1]) == canonical('desiredLevel = nextLevel'), 'Refresh must retain readyAt')
    require('tdActiveCooldownNeedsNativeLevel(now, readyAt, actualLevel, desiredLevel, busy)' in methods['needsLevel', 3][1], 'Native state bypasses expiry/same-level/busy guard')
    require(native_source.count('.startCast(') == 1 and 'record.startCast(getElapsedGameTime(), active.baseCooldown, actualLevel)' in evaluator.body('tdNativeActiveSpellCast'), 'Native deadline owner must be successful actual-level cast')
    apply = evaluator.body('tdApplyNativeActiveCooldownLevel')
    require('if not record.needsLevel(now, actualLevel, busy)' in apply, 'Native setter bypasses expiry/same-level/busy guard')
    require(len(calls(native_source, 'setAbilityLevel')) == 1 and not calls(native_source, 'SetUnitAbilityLevel') and
            apply.index('tower.setAbilityLevel(') < apply.index('tdRestoreNativeActiveAutocast('),
            'Generic restore must follow sole actual native setter; raw runtime setter unsupported')
    for token in ('tdPetBusyTowers.hasBoolean(tower.getHandleId())', 'tdActiveCooldownNativeLevelValid(actualLevel)', 'tdActiveCooldownNativeLevelValid(record.desiredLevel)'):
        require(token in apply, 'Native setter missing busy/physical-level rejection guard: ' + token)
    require(native_source.count('iter.remove()') == 2 and native_source.count('destroy record') == 2,
            'Native records may retire only at explicit forget or invalid host, never temporary absence')
    start = evaluator.body('tdStartScriptActiveCooldown')
    for token in ('tdActiveSkillDefinitionForKey(', 'TD_ACTIVE_DRIVER_PET_PROC', 'tdActiveCooldownReadyAt(', 'tdHostActiveCooldownReduction('):
        require(token in start, 'Script cooldown entry missing ' + token)
    require('tdStartScriptActiveCooldown' in evaluator.sources['pets/TDPetCombat.wurst'], 'Pet success branch not connected')
    require('tdSetupNativeActiveCooldowns()' in evaluator.body('tdSetupEquipmentAbilities'), 'Missing runtime setup facade')
    require('tdForgetNativeActiveCooldowns(tower)' in evaluator.body('tdForgetEquipmentAbilities'), 'Missing runtime cleanup facade')


def verify_manager_list_zero_cooldown(evaluator):
    """Only the reviewed 10x49 mutually exclusive, zero-CD UI list family."""
    path = 'pets/TDPetObjectGen.wurst'
    source = evaluator.sources[path]
    owners = source_functions(source)
    require(('listCommand', 5) in owners, 'Missing manager list zero-CD owner')
    params, body = owners['listCommand', 5]
    require(params == ['listAbility', 'cell', 'order', 'name', 'icon'] and
            'function listCommand(AbilityDefinitionIllidanChannel listAbility, int cell, string order, string name, string icon)' in source,
            'Manager list zero-CD signature changed')
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    require(lines and lines[0].startswith('listAbility..') and all(line.startswith('..') for line in lines[1:]),
            'Manager list zero-CD receiver rebound or independent code added')
    require(calls(body, 'presetCooldown') == [[canonical('lvl -> 0.0')]] and
            calls(body, 'presetManaCost') == [[canonical('lvl -> 0')]] and
            calls(body, 'presetBaseOrderID') == [[canonical('lvl -> order')]], 'Manager list must retain exact zero-CD shared-order role')
    generator = evaluator.body('tdGeneratePetObjects')
    expected_bindings = {
        'anchor': 'new ChannelAbilityPreset(tdPetListAbilityId(cell, 0, 0, 0), 2, true)',
        'order': 'anchor.getOrderString()',
        'listAbility': 'variant == 0 ? anchor : new AbilityDefinitionIllidanChannel(tdPetListAbilityId(cell, species, quality, ownedCount))',
    }
    for variable, expression in expected_bindings.items():
        values = re.findall(r'(?<![\w.])' + variable + r'\s*(?:=|\+=|-=)\s*([^\n]+)', generator)
        require(len(values) == 1 and canonical(values[0]) == canonical(expression),
                'Manager list rawcode/receiver/order binding changed: ' + variable)
    require('for cell = 0 to 9' in generator and 'for variant = 0 to 48' in generator,
            'Manager list physical-cell/state family changed')
    require(calls(generator, 'listCommand') == [['listAbility', 'cell', 'order', 'label', 'icon']],
            'Manager list helper has unknown caller/arguments')
    expected_calls = [[canonical(part) for part in
                       ('AbilityDefinitionIllidanChannel listAbility', 'int cell', 'string order', 'string name', 'string icon')],
                      ['listAbility', 'cell', 'order', 'label', 'icon']]
    for owner_path, text in evaluator.sources.items():
        require(calls(text, 'listCommand') == (expected_calls if owner_path == path else []),
                'Manager list helper used outside its exact UI role: ' + owner_path)
    for cell in range(10):
        states = [(0, 0, 0)] + [(species, quality, count) for species in range(1, 4)
                                for quality in range(1, 5) for count in range(1, 5)]
        for variant, args in enumerate(states):
            require(evaluator.call('tdPetListAbilityId', [cell, *args]) == rawcode(f'L{cell * 49 + variant:03X}'),
                    'Manager list helper rawcode escaped its mutually exclusive UI family')


def verify_inventory(evaluator):
    """Every cooldown/registration/dynamic mount gets an explicit owner role."""
    # Non-tower Channel operations have fixed responsibilities. Additional
    # operations require their owner role to be reviewed rather than silently
    # being added to a CDR exclusion list.
    verify_manager_list_zero_cooldown(evaluator)
    operation_roles = {
        ('towers/TDTowerObjectGen.wurst', 'tdGenerateTowerAbilities'): {
            'TD_FARMER_WAGE_ABILITY_ID': 'tdFarmerWageCooldown ( )', 'TD_TOWER_SELL_ABILITY_ID': '0.0'},
        ('items/TDItemObjectGen.wurst', 'tdGenerateCraftAbility'): {'TD_FARMER_CRAFT_ABILITY_ID': '0.50'},
        ('items/TDItemObjectGen.wurst', 'tdGenerateGroundEquipmentCommands'): {'TD_FARMER_GROUND_UPGRADE_ABILITY_ID': '0.50'},
        ('pets/TDPetObjectGen.wurst', 'command'): {'abilityId': '0.0'},
        ('pets/TDPetObjectGen.wurst', 'tdGeneratePetObjects'): {
            'TD_PET_CAPTURE_ABILITY_ID': '0.0', 'tdPetListAbilityId ( cell , species , quality )': '0.0'},
    }
    # Dynamic support mounts only, with the exact data source preserved. A new
    # arbitrary ability in one of these owners is still rejected.
    dynamic_roles = {
        ('towers/TDTowerEvolutionRuntime.wurst', 'tdEvolutionRefresh'): {'replacement , 1', 'tdEvolutionDisplayReplacement ( choice , branch ) , 1', 'TD_TOWER_EVOLUTION_PROGRESS_ABILITY_ID , 1', 'TD_TOWER_EVOLUTION_STATUS_ABILITY_ID , 1'},
        ('items/TDInventoryRuntime.wurst', 'tdSetTowerEquipmentAbilityLevel'): {'abilityId , level'},
        ('pets/TDPetCombat.wurst', 'setBonus'): {'abilityId , clamped'},
    }
    simple_dynamic_paths = {'items/TDEquipmentSpecialState.wurst', 'auras/TDAuraState.wurst', 'pets/TDPetUIView.wurst', 'pets/TDPetAttackState.wurst', 'enemies/TDBossDarkTideRuntime.wurst'}
    support_owners = {('items/TDEquipmentSpecialState.wurst', 'tdSpecialSyncBuff'),
                      ('items/TDEquipmentSpecialState.wurst', 'tdEquipmentSpecialSyncStages'),
                      ('auras/TDAuraState.wurst', 'tdAuraSyncDisplayedRank'), ('pets/TDPetUIView.wurst', 'tdPetRenderPage')}
    registered_paths = {'towers/TDTowerRuntime.wurst', 'items/TDGroundItemRuntime.wurst', 'items/TDInventoryRuntime.wurst', 'pets/TDPetRuntime.wurst', 'pets/TDPetUI.wurst'}
    cooldowns = 0
    bare_deadline_roles = {DATA: ['0.0', 'tdActiveCooldownReadyAt(now, baseCooldown, tdActiveCooldownReductionAtNativeLevel(actualLevel))'],
                           'pets/TDPetState.wurst': ['0.0'],
                           'items/TDShieldRules.wurst': ['0.0', 'tdShieldWindowUntil(now, boss, control)', 'previous']}
    for path, source in evaluator.sources.items():
        require(not re.search(r'\b(?:Blz\w*Cooldown\w*|EX\w*Ability\w*|ResetCooldown)\s*\(', uncomment(source)),
                'Unsupported native cooldown reset/late-engine API: ' + path)
        bare = [canonical(match[1]) for match in re.finditer(r'(?<![\w.])readyAt\s*(?:=|\+=|-=)\s*([^\n]+)', uncomment(source))]
        require(sorted(bare) == sorted(canonical(value) for value in bare_deadline_roles.get(path, [])),
                'Unclassified/bypassed bare script deadline owner: ' + path)
        owners = source_functions(source)
        for method in ('setCooldown', 'presetCooldown', 'makeUnitSpell', 'registerSpellEffectEvent',
                       'registerSpellCastEvent', 'registerSpellFinishEvent', 'registerSpellChannelEvent', 'registerSpellEndcastEvent'):
            accounted = sum(len(calls(body, method)) for _, body in owners.values())
            require(len(calls(source, method)) == accounted, 'Unclassified class/outside-function cooldown or registration: ' + path + ':' + method)
        for (name, _), (_, body) in owners.items():
            for arguments in calls(body, 'setCooldown'):
                permitted = (path == OBJECT and name == 'tdConfigureActiveNativeCooldown') or (
                    path == 'items/TDEquipmentSpecialObjectGen.wurst' and name == 'tdConfigureShieldStun' and canonical(','.join(arguments)) == 'level , 0.0')
                require(permitted, 'Unclassified/bypassed cooldown write: ' + path + ':' + name)
                cooldowns += 1
            require(not calls(body, 'presetCooldown') or (path, name) == ('pets/TDPetObjectGen.wurst', 'listCommand'),
                    'Independent presetCooldown bypasses shared contract: ' + path + ':' + name)
            if calls(body, 'makeUnitSpell'):
                roles = operation_roles.get((path, name), {})
                require(roles, 'Unclassified operation cooldown: ' + path + ':' + name)
                operations = channel_operations(body)
                require(len(operations) == len(calls(body, 'makeUnitSpell')), 'Unresolved Channel operation ownership')
                for identity, arguments in operations:
                    require(canonical(arguments[0]) == '0', 'Unexpected operation mana/cooldown driver')
                    expression = canonical(arguments[1])
                    require(identity in roles and roles[identity] == expression,
                            'Unclassified operation rawcode/cooldown role: ' + path + ':' + name + ':' + identity)
            for method in ('addAbility', 'addPermanentAbility', 'UnitAddAbility'):
                for arguments in calls(body, method):
                    expression = canonical(' , '.join(arguments))
                    known = expression in dynamic_roles.get((path, name), set())
                    known |= (path == 'items/TDEquipmentCombat.wurst' and expression == 'TD_EQUIPMENT_ARMOR_SHRED_ABILITY_ID')
                    known |= (path == 'pets/TDPetCombat.wurst' and expression == 'TD_PET_ARMOR_ID')
                    known |= (path == 'enemies/TDBossDarkTideRuntime.wurst' and expression == 'TD_BOSS_DARK_TIDE_ABILITY_ID')
                    if (path, name) in support_owners:
                        support = {'items/TDEquipmentSpecialState.wurst': ['desired.abilId', 'TD_WAR_INTENT_SPEED_CARRIER'],
                                   'auras/TDAuraState.wurst': ['carrier'], 'pets/TDPetUIView.wurst': ['session.abilities[cell]'],
                                   'enemies/TDBossDarkTideRuntime.wurst': ['TD_BOSS_DARK_TIDE_ABILITY_ID']}[path]
                        known |= canonical(arguments[0]) in {canonical(x) for x in support}
                    require(known, 'Unknown dynamic ability mount: ' + path + ':' + name + ':' + expression)
            for arguments in calls(body, 'registerSpellEffectEvent'):
                ground_craft_owner = (path == 'items/TDCraftingRuntime.wurst' and name == 'tdSetupCraftingRuntime' and
                                      arguments == ['TD_FARMER_GROUND_UPGRADE_ABILITY_ID', 'function tdGroundHandleUpgrade'])
                require(path in registered_paths or ground_craft_owner, 'Unknown spell registration owner: ' + path)
                first = arguments[0]
                if re.fullmatch(r'TD_\w+', first):
                    identity = evaluator.constant(first)
                    # Farmer/management registrations must remain tied to their
                    # named ownership, not a new arbitrary combat ability.
                    require(identity in {d.abilityId for d in definitions(evaluator)} or re.search(r'FARMER|TOWER_SELL|PET_(?:CAPTURE|COLLECTION|DEPLOY)', first), 'Undefined combat spell registration: ' + first)
                else:
                    require(path == 'pets/TDPetUI.wurst' and first.startswith(('tdPetManagerCommandId (', 'tdPetListAbilityId (')), 'Unknown dynamic spell registration: ' + first)
            for method in ('registerSpellCastEvent', 'registerSpellFinishEvent', 'registerSpellChannelEvent', 'registerSpellEndcastEvent'):
                require(not calls(body, method), 'Unknown spell registration mechanism: ' + path + ':' + method)
        for arguments in calls(source, 'registerAnyUnitEvent'):
            if any('EVENT_PLAYER_UNIT_SPELL_' in arg for arg in arguments):
                require(path in {RUNTIME, 'pets/TDPetUI.wurst'} and arguments == ['EVENT_PLAYER_UNIT_SPELL_EFFECT'], 'Unknown generic combat spell registration: ' + path)
                if path == 'pets/TDPetUI.wurst':
                    setup = evaluator.body('tdPetSetupUI')
                    require(setup.count('managerCommandTrigger.registerAnyUnitEvent(EVENT_PLAYER_UNIT_SPELL_EFFECT)') == 1
                            and setup.count('managerCommandTrigger.addAction(function onManagerSpell)') == 1
                            and canonical(evaluator.body('onManagerSpell')) == canonical('onCommand()')
                            and sum('EVENT_PLAYER_UNIT_SPELL_' in arg for args in calls(source, 'registerAnyUnitEvent') for arg in args) == 1
                            and 'session.admitCommand' in evaluator.body('onCommand'),
                            'Manager bridge bypasses caster/session authority')
        # Methods in classes are outside source_functions. Inspect those exact
        # support owners separately; adding a new call elsewhere fails closed.
        total = sum(len(calls(body, method)) for _, body in owners.values() for method in ('addAbility', 'addPermanentAbility', 'UnitAddAbility'))
        all_calls = sum(len(calls(source, method)) for method in ('addAbility', 'addPermanentAbility', 'UnitAddAbility'))
        if all_calls != total:
            require(path in simple_dynamic_paths, 'Unclassified class dynamic ability mount: ' + path)
            allowed = {'items/TDEquipmentSpecialState.wurst': ['desired.abilId', 'TD_WAR_INTENT_SPEED_CARRIER'],
                       'auras/TDAuraState.wurst': ['carrier'], 'pets/TDPetUIView.wurst': ['session.abilities[cell]'],
                       'pets/TDPetAttackState.wurst': ['TD_PET_ARMOR_ID'],
                       'enemies/TDBossDarkTideRuntime.wurst': ['TD_BOSS_DARK_TIDE_ABILITY_ID']}[path]
            for method in ('addAbility', 'addPermanentAbility', 'UnitAddAbility'):
                for arguments in calls(source, method):
                    require(canonical(arguments[0]) in {canonical(x) for x in allowed}, 'Unknown support dynamic ability source')
    require(cooldowns == 2, 'Cooldown write ownership inventory changed')
    item = evaluator.body('tdGenerateEquipmentItem')
    require(calls(item, 'setActivelyUsed') == [['false']] and calls(item, 'setAbilities') == [['tdItemPassiveAbilityRawcodes ( itemId )']],
            'Equipment native item active driver unsupported')
    inventories = calls(evaluator.body('tdGenerateEquipmentSupportObjects'), 'tdGenerateInventoryAbility')
    require(['TD_TOWER_INVENTORY_ABILITY_ID', '3', 'false'] in inventories,
            'Tower inventory source must not enable item use')
    tower_mount = canonical('abilities + "," + TD_TOWER_INVENTORY_ABILITY_ID.toRawCode() + "," + TD_TOWER_SELL_ABILITY_ID.toRawCode() + "," + TD_TOWER_EVOLUTION_PROGRESS_ABILITY_ID.toRawCode()')
    farmer_mount = canonical('TD_FARMER_BUILD_ABILITY_ID.toRawCode() + "," + TD_FARMER_WAGE_ABILITY_ID.toRawCode() + "," + TD_FARMER_INVENTORY_ABILITY_ID.toRawCode() + "," + TD_FARMER_EQUIPMENT_BOOK_ABILITY_ID.toRawCode() + "," + TD_FARMER_GROUND_UPGRADE_ABILITY_ID.toRawCode() + "," + TD_PET_CAPTURE_ABILITY_ID.toRawCode() + "," + TD_PET_COLLECTION_ABILITY_ID.toRawCode() + "," + TD_PET_DEPLOY_ABILITY_ID.toRawCode()')
    for path, source in evaluator.sources.items():
        for arguments in calls(source, 'setNormalAbilities'):
            if path == 'towers/TDTowerObjectGen.wurst':
                require(canonical(arguments[0]) in (tower_mount, farmer_mount), 'Unclassified direct tower ability mounting bypasses catalog')
            else:
                require(path in ('pets/TDPetObjectGen.wurst', 'TDWaves.wurst', 'trial/TDTrialObjectGen.wurst'), 'Unknown unit/tower ability mounting owner: ' + path)


def verify_source(root=ROOT, sources=None):
    sources = read_sources(root) if sources is None else sources
    evaluator = SourceScalarEvaluator(sources)
    active = definitions(evaluator)
    verify_scalar_rules(evaluator, active)
    verify_runtime_sources(evaluator)
    verify_inventory(evaluator)
    native_objects = source_native_objects(evaluator, active)
    towers = source_towers(evaluator)
    source_mount_roles(evaluator, towers, active)
    mounts = {code for values in towers.values() for code in values}
    require(set(native_objects) <= mounts, 'Native shared definition has no reachable tower host')
    return {'definitions': active, 'evaluator': evaluator, 'native_objects': native_objects, 'towers': towers}


def verify_objects(contract, abilities, units, items, dynamic_mounts=()):
    evaluator = contract['evaluator']
    native = {rawstring(d.abilityId): d for d in contract['definitions'] if d.abilityId}
    mounted = set()
    for uid, expected in contract['towers'].items():
        require(uid in units, 'Missing packaged tower host ' + uid)
        actual = units[uid].get('uabi', '').split(',')
        require(actual == expected, uid + ': packaged/source ability mounting mismatch')
        mounted.update(actual)
    require(not (set(dynamic_mounts) & set(native)), 'Native active dynamic remount lacks engine CD migration')
    mounted.update(dynamic_mounts)
    # Evolution is the only current ability replacement path. Refuse active
    # replacement until 1.27a engine CD migration has an explicit contract.
    for name in ('tdEvolutionSkillReplacement', 'tdEvolutionSkillOriginal', 'tdEvolutionDisplayReplacement', 'tdEvolutionDisplayOriginal'):
        for choice in range(1, 6):
            for branch in (1, 2):
                identity = evaluator.call(name, [choice, branch])
                if identity:
                    code = rawstring(identity)
                    require(code not in native, 'Native active replacement/remount lacks engine CD migration')
                    mounted.add(code)
    # Class support carriers are finite role tables generated from real source.
    for name in evaluator.constants:
        if name.startswith(('TD_TOWER_EQUIPMENT_', 'TD_PET_')) and name.endswith(('_ABILITY_ID', '_BONUS_ID')):
            try:
                value = evaluator.constant(name)
                if isinstance(value, int) and value > 0xffffff: mounted.add(rawstring(value))
            except ValueError:
                continue
    for code in mounted:
        require(code in abilities, 'Mounted ability has no packaged object: ' + code)
        parent, fields = abilities[code]
        positive = any(key == 'acdn' and value[1] > 0 for (key, _, _), value in fields.items())
        if code not in native:
            require(not positive, 'Undefined mounted combat active with positive CD: ' + code)
            # ANcl requires explicit zero cooldown, since native inheritance is
            # not evidence of zero. Passive parents have reviewed role schemas.
            if parent == 'ANcl':
                require(fields.get(('acdn', 1, 0)) == (2, 0.0), 'Unclassified inherited Channel CD: ' + code)
            else:
                require(parent in PASSIVE_PARENTS, 'Unknown mounted parent/inherited CD: ' + code + ':' + parent)
    for code, definition in native.items():
        require(code in mounted and code in abilities, 'Shared native active missing object/reachable host: ' + code)
        expected_parent, expected_fields = contract['native_objects'][code]
        parent, fields = abilities[code]
        require(parent == expected_parent, code + ': native parent changed')
        require(fields.get(('alev', 0, 0)) == (0, 41), code + ': expected 41 cooldown levels')
        cooldowns = {(level, column): (kind, value) for (field, level, column), (kind, value) in fields.items() if field == 'acdn'}
        require(set(cooldowns) == {(i, 0) for i in range(1, 42)}, code + ': incomplete cooldown physical levels')
        for level in range(1, 42):
            kind, value = cooldowns[level, 0]
            expected = evaluator.call('tdActiveCooldownDuration', [definition.baseCooldown, evaluator.call('tdActiveCooldownReductionAtNativeLevel', [level])])
            require(kind == 2 and math.isfinite(value) and math.isclose(value, expected, rel_tol=1e-6), code + f': cooldown changed at {level}')
        for field, expected in expected_fields.items():
            actual = fields.get(field)
            equal = actual is not None and actual[0] == expected[0] and (math.isclose(actual[1], expected[1], rel_tol=1e-6, abs_tol=1e-7) if expected[0] in (1, 2) else actual[1] == expected[1])
            require(equal, code + ': native non-CD effect/encoding changed: ' + repr(field))
        # Any additional level-bearing effects must also be complete/invariant.
        level_fields = {field for field, level, _ in fields if level > 0} - {'acdn', 'atp1', 'aub1', 'aut1', 'auu1'}
        for field in level_fields:
            entries = {(level, column): value for (key, level, column), value in fields.items() if key == field}
            columns = {column for level, column in entries}
            require(set(entries) == {(level, column) for level in range(1, 42) for column in columns}, code + ': incomplete non-CD effect levels: ' + field)
            for column in columns:
                require(all(entries[level, column] == entries[1, column] for level in range(1, 42)), code + ': physical CDR changed non-CD effect: ' + field)
    catalog = evaluator.body('tdConfiguredEquipment')
    item_ids = {rawstring(evaluator.expression(args[0], {})) for args in calls(catalog, 'tdEquipmentDefinition') if evaluator.expression(args[0], {})}
    require(item_ids, 'No source equipment catalog')
    for code in item_ids:
        require(code in items, 'Missing packaged equipment item: ' + code)
        fields = items[code]
        require(fields.get('iusa') == 0 and fields.get('iabi', '') == '', code + ': native item active driver unsupported')
    inventory = rawstring(evaluator.constant('TD_TOWER_INVENTORY_ABILITY_ID'))
    require(abilities[inventory][1].get(('inv3', 1, 3)) == (0, 0), 'Tower inventory must not enable item use')
    return {'tower_hosts': len(contract['towers']), 'native_actives': len(native), 'equipment_items': len(item_ids)}


def compiled_dynamic_mounts(contract, script):
    """Resolve the current runtime role tables from actual packaged JASS."""
    runtime = ActiveJassRuntime(script)
    for name in ('init_TDAuraObjectIds', 'init_TDEquipmentSpecialObjectIds'):
        require(name in runtime.functions, 'Missing packaged support role initialization: ' + name)
        runtime.invoke(name)
    result = set()
    count = contract['evaluator'].constant('TD_AURA_ID_COUNT')
    for identity in range(1, count + 1):
        for rank in range(1, 5):
            value = runtime.invoke('tdAuraRankCarrier', identity, rank)
            if value: result.add(rawstring(value))
    for war, stages in ((True, range(1, 5)), (False, range(1, 3))):
        for stage in stages:
            runtime.invoke('tdSpecialStageBuff', war, stage)
            value = runtime.globals['tdSpecialStageBuff_return_abilId']
            if value: result.add(rawstring(value))
    for suffix in ('TD_WAR_INTENT_SPEED_CARRIER', 'TD_BOSS_DARK_TIDE_ABILITY_ID'):
        candidates = [value for name, value in runtime.globals.items() if name.endswith('_' + suffix)]
        require(len(candidates) == 1 and candidates[0], 'Unresolved packaged dynamic support rawcode: ' + suffix)
        result.add(rawstring(candidates[0]))
    for name in ('tdEvolutionSkillReplacement', 'tdEvolutionSkillOriginal', 'tdEvolutionDisplayReplacement', 'tdEvolutionDisplayOriginal'):
        for choice in range(1, 6):
            for branch in (1, 2):
                actual = runtime.invoke(name, choice, branch)
                require(actual == contract['evaluator'].call(name, [choice, branch]), 'Packaged/source evolution dynamic mounting mismatch')
                if actual: result.add(rawstring(actual))
    return result


def verify_compiled_core(contract, script):
    """Inspect actual packed call chains and evaluate actual scalar functions."""
    runtime = ActiveJassRuntime(script)
    # Actual Wurst Orders constants may be assigned by package initialization,
    # rather than inlined. Execute the real initializer, never seed expected IDs.
    if any(name.startswith('Orders_') for name in runtime.globals):
        require('init_Orders' in runtime.functions, 'Missing packaged Orders initialization')
        runtime.invoke('init_Orders')
    require(runtime.invoke('tdActiveSkillDefinitionCount') == len(contract['definitions']), 'Packaged active count differs from source')
    for index, definition in enumerate(contract['definitions']):
        primary = runtime.invoke('tdActiveSkillDefinitionAt', index)
        for field in definition._fields:
            key = 'tdActiveSkillDefinitionAt_return_' + field
            # The first tuple field may be returned directly; the remaining
            # fields use compiler-generated tuple return globals.
            actual = primary if field == 'key' else runtime.globals.get(key)
            require(actual == getattr(definition, field), 'Packaged active tuple differs: ' + field)
        if definition.petSkillId >= 0:
            require(runtime.invoke('tdPetSkillIsActive', definition.petSkillId), 'Packaged pet definition excluded by classifier')
    for definition in contract['definitions']:
        for reduction in (-.1, 0, .18, .40, .8):
            expected = contract['evaluator'].call('tdActiveCooldownDuration', [definition.baseCooldown, reduction])
            require(math.isclose(runtime.invoke('tdActiveCooldownDuration', definition.baseCooldown, reduction), expected), 'Packaged scalar duration differs')
            require(math.isclose(runtime.invoke('tdActiveCooldownReadyAt', 20, definition.baseCooldown, reduction), 20 + expected), 'Packaged readyAt differs')
    for name in ('tdHasNativeActiveCooldown', 'tdRefreshNativeActiveCooldowns'):
        body = function_body(script, name)
        for token in ('tdActiveSkillDefinitionCount', 'tdActiveSkillDefinitionAt', 'unit_getAbilityLevel'):
            require(token in body, 'Packaged generic native consumer missing ' + token)
        require('TD_ORC_BLOODLUST_ABILITY_ID' not in body and 'TD_ORC_BLADESTORM_ABILITY_ID' not in body, 'Packaged legacy native whitelist')
    host = function_body(script, 'tdHostActiveCooldownReduction')
    for token in ('tdFinalCooldownReduction(', 'tdPetCooldownReduction(', 'tdAuraPower('):
        require(host.count(token) == 1, 'Packaged duplicate/missing cooldown source ' + token)
    aura = function_body(script, 'tdAuraCooldownTargetEligible')
    for token in ('tdPetBindingValid', 'tdPetUnlockedSlots', 'tdPetSkillFitsHost', 'tdPetSkillIsActive', 'tdHasNativeActiveCooldown'):
        require(token in aura, 'Packaged aura guard missing ' + token)
    require('tdSetupNativeActiveCooldowns' in function_body(script, 'tdSetupEquipmentAbilities'), 'Packaged runtime init missing')
    require('tdForgetNativeActiveCooldowns' in function_body(script, 'tdForgetEquipmentAbilities'), 'Packaged runtime cleanup missing')
    require('EVENT_PLAYER_UNIT_SPELL_EFFECT' in function_body(script, 'tdSetupNativeActiveCooldowns'), 'Packaged cast event missing')
    callbacks = re.findall(r'^function (\w*call_doPeriodically_TDActiveCooldownRuntime\w*) takes [^\n]*\n(.*?)^endfunction', script, re.M | re.S)
    require(len(callbacks) == 1, 'Packaged native cooldown must keep one periodic callback')
    require(re.search(r'\b0\.1(?:0)?\b', function_body(script, 'tdSetupNativeActiveCooldowns')), 'Packaged timer period changed')
    require('tdStartScriptActiveCooldown' in script and 'tdActiveSkillDefinitionForAbility' in script, 'Packaged generic pet/cast lookup missing')
    cast = function_body(script, 'tdNativeActiveSpellCast')
    for token in ('tdActiveSkillDefinitionForAbility', 'unit_getAbilityLevel', 'TDActiveNativeCooldownState_startCast'):
        require(token in cast, 'Packaged cast/actual-level chain missing ' + token)
    state_cast = function_body(script, 'TDActiveNativeCooldownState_startCast')
    decode = calls(state_cast, 'tdActiveCooldownReductionAtNativeLevel')
    require('tdActiveCooldownReadyAt(' in state_cast and len(decode) == 1 and
            re.fullmatch(r'actualLevel\w*', decode[0][0]) and
            (len(decode[0]) == 1 or (len(decode[0]) == 2 and re.fullmatch(
                r'"when calling tdActiveCooldownReductionAtNativeLevel in TDActiveSkillData, line \d+"', decode[0][1]))),
            'Packaged cast deadline must use actual level')
    require('desiredLevel' not in state_cast, 'Packaged cast uses desired level')
    request = function_body(script, 'TDActiveNativeCooldownState_requestLevel')
    require('readyAt' not in request, 'Packaged refresh reset readyAt')
    needs = function_body(script, 'TDActiveNativeCooldownState_needsLevel')
    require('tdActiveCooldownNeedsNativeLevel(' in needs, 'Packaged state bypasses deadline guard')
    apply = function_body(script, 'tdApplyNativeActiveCooldownLevel')
    require('TDActiveNativeCooldownState_needsLevel' in apply and 'tdPetBusyTowers' in apply, 'Packaged setter bypasses busy/deadline guard')
    guard = re.search(r'if\s+not\s+(?:dispatch_)?\w*needsLevel\([^\n]+\) then(.*?)endif', apply, re.S)
    require(guard is not None and re.search(r'\breturn\b', guard[1]) and 'setAbilityLevel' not in guard[1],
            'Packaged setter must branch-return on rejected deadline guard')
    require(apply.count('call unit_setAbilityLevel(') == 1 and not calls(apply, 'SetUnitAbilityLevel') and
            apply.count('call tdRestoreNativeActiveAutocast(') == 1 and
            apply.index('call unit_setAbilityLevel(') < apply.index('call tdRestoreNativeActiveAutocast('),
            'Packaged native set/restore ordering changed')
    require('readyAt' not in callbacks[0][1] and 'readyAt' not in function_body(script, 'tdRefreshNativeActiveCooldowns'), 'Packaged refresh/timer rewrites deadline')
    for name in ('tdNativeActiveSpellCast', 'tdRefreshNativeActiveCooldowns', 'tdSetupNativeActiveCooldowns'):
        body = function_body(script, name)
        require('unit_setAbilityLevel' not in body and not calls(body, 'SetUnitAbilityLevel'),
                'Packaged native level write bypasses shared apply: ' + name)
    for now, ready_at, actual, desired, busy in ((9.,10.,1,41,False), (10.,10.,1,41,True), (10.,10.,0,41,False), (10.,10.,41,41,False), (10.,10.,1,41,False)):
        require(runtime.invoke('tdActiveCooldownNeedsNativeLevel', now, ready_at, actual, desired, busy) == (not busy and actual > 0 and actual != desired and now >= ready_at), 'Packaged same-level/busy/deadline rule changed')
    # Execute the real packed state methods, including an actual!=desired cast.
    ability = next(d.abilityId for d in contract['definitions'] if d.abilityId)
    runtime.host_abilities = {(101, ability): 1}
    state = runtime.invoke('new_TDNativeActiveCooldown', 101, ability)
    runtime.invoke('TDActiveNativeCooldownState_requestLevel', state, 41)
    runtime.invoke('TDActiveNativeCooldownState_startCast', state, 10., 23., 1)
    require(runtime.globals['TDActiveNativeCooldownState_readyAt'][state] == 33., 'Packaged actual-level cast state changed')
    runtime.invoke('TDActiveNativeCooldownState_requestLevel', state, 19)
    require(runtime.globals['TDActiveNativeCooldownState_readyAt'][state] == 33., 'Packaged desired refresh reset locked state')
    require(not runtime.invoke('TDActiveNativeCooldownState_needsLevel', state, 32.99, 1, False), 'Packaged state applied early')


def verify_compiled(contract, script):
    verify_compiled_core(contract, script)
    # Keep the repository's independent legacy JASS boolean precedence gate.
    from VerifyPetUIArtifact import verify_skill_fit_abilities, verify_skill_allowed, verify_lane_enemy_guards
    verify_skill_fit_abilities(script)
    verify_skill_allowed(script)
    verify_lane_enemy_guards(script, require_match_registry=True)


def verify_mpq(path, root=ROOT):
    contract = verify_source(root)
    data = Path(path).read_bytes()
    artifact = Mpq(data)
    script = artifact.extract('war3map.j').decode('utf-8')
    dynamic = compiled_dynamic_mounts(contract, script)
    parsed_items = parse_objects(artifact.extract('war3map.w3t'), extended=False)
    items = {code: {key[0]: field.value for key, field in obj.fields.items()} for code, obj in parsed_items.items()}
    result = verify_objects(contract, ability_objects(artifact.extract('war3map.w3a')),
                            unit_objects(artifact.extract('war3map.w3u')), items, dynamic)
    verify_compiled(contract, script)
    return {**result, 'dynamic_support_mounts': len(dynamic), 'sha256': hashlib.sha256(data).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path, nargs='?')
    parser.add_argument('--map', type=Path, dest='named_map')
    parser.add_argument('--source-only', action='store_true')
    parser.add_argument('--source-root', type=Path, default=ROOT)
    args = parser.parse_args()
    require(not (args.map and args.named_map), 'Specify map path only once')
    args.map = args.map or args.named_map
    require(args.source_only != (args.map is not None), 'Choose exactly one of --source-only or a real map path')
    if args.source_only:
        result = verify_source(args.source_root)
        print(f'PASS SOURCE: {len(result["definitions"])} shared definitions; generic consumers, source ownership and {len(result["towers"])} host mounts.')
        print('NOT EXECUTED: Wurst compilation/tests, new MPQ/JASS, Warcraft engine.')
    else:
        print('PASS REAL MPQ/JASS:', verify_mpq(args.map, args.source_root))
        print('NOT EXECUTED: Warcraft engine/native autocast timing.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, TypeError, AttributeError) as exc:
        raise SystemExit('FAIL: ' + str(exc))
