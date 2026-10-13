#!/usr/bin/env python3
"""Execute packaged ranking scalar helpers with binary32 real semantics.

Read-only offline oracle, not a Warcraft interpreter. Only the small, pure
comparator/rank subset is supported; unknown calls and global reads fail closed.
"""
import ast
from functools import lru_cache
import itertools
import re
import struct
from VerifyEquipmentAbilityArtifact import require

TOTALS = (0.0, .125, .375, .5, .625, 1.0, 1.125, 10.0, 10.125, 1048576.125)
HELPERS = ('tdDamagePlayerPrecedes', 'tdDamageTowerPrecedes', 'tdDamagePlayerRank')
SIGNATURES = {
    HELPERS[0]: ('boolean', ('real', 'integer', 'real', 'integer')),
    HELPERS[1]: ('boolean', ('real', 'integer', 'integer', 'real', 'integer', 'integer')),
    HELPERS[2]: ('integer', ('real', 'integer', 'real', 'boolean', 'real', 'boolean', 'real', 'boolean', 'real', 'boolean')),
}


def real32(value):
    require(type(value) in (int, float), 'JASS real requires numeric input')
    return struct.unpack('<f', struct.pack('<f', value))[0]


def functions(script):
    result = {}
    for m in re.finditer(r'^function (\w+) takes ([^\n]+) returns (\w+)\n(.*?)^endfunction', script, re.M | re.S):
        require(m[1] not in result, 'Duplicate packaged function: ' + m[1])
        result[m[1]] = m
    return result


@lru_cache(maxsize=256)
def expression_node(source):
    return ast.parse(source, mode='eval').body


class ScalarProgram:
    def __init__(self, script):
        all_functions = functions(script)
        self.helpers = {}
        for name in HELPERS:
            require(name in all_functions, 'Missing packaged helper: ' + name)
            m = all_functions[name]
            params = [re.fullmatch(r'(real|integer|boolean) (\w+)', p.strip()) for p in m[2].split(',')]
            require(all(params), name + ': unsupported parameter')
            result, kinds = SIGNATURES[name]
            require(m[3] == result and tuple(p[1] for p in params) == kinds, name + ': scalar signature changed')
            self.helpers[name] = (m, params)
            # Audit all statements, even unreachable tails after a return.
            declared = {p[2] for p in params} | {'true', 'false'}
            declared |= set(re.findall(r'local (?:integer|real|boolean) (\w+)', m[4]))
            for raw in m[4].splitlines():
                line = raw.split('//', 1)[0].strip()
                if not line or line in ('else', 'endif'):
                    continue
                expression = None
                if line.startswith(('if ', 'elseif ')) and line.endswith(' then'):
                    expression = line.split(' ', 1)[1][:-5]
                elif line.startswith('return '):
                    expression = line[7:]
                elif line.startswith('local '):
                    expression = line.split(' = ', 1)[1] if ' = ' in line else None
                elif line.startswith('set '):
                    assignment = re.fullmatch(r'set (\w+) = (.*)', line)
                    require(assignment and assignment[1] in declared, 'Nonlocal scalar write')
                    expression = assignment[2]
                else:
                    raise ValueError('Unsupported/non-pure scalar statement: ' + line)
                if expression is not None:
                    supported = (ast.Expression, ast.Name, ast.Load, ast.Constant, ast.Call, ast.UnaryOp,
                                 ast.Not, ast.USub, ast.BinOp, ast.Add, ast.Compare,
                                 ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
                    for node in ast.walk(expression_node(expression)):
                        require(not isinstance(node, ast.BoolOp), 'Use explicit branches, not mixed/shortcut boolean grouping')
                        require(isinstance(node, supported), 'Unsupported/non-pure scalar expression')
                        if isinstance(node, ast.Call):
                            require(name == HELPERS[2] and isinstance(node.func, ast.Name) and node.func.id == HELPERS[0],
                                    'Non-pure scalar call')
                        if isinstance(node, ast.Name):
                            require(node.id in declared or name == HELPERS[2] and node.id == HELPERS[0],
                                    'Nonlocal scalar read: ' + node.id)

    def expression(self, source, variables, depth):
        def visit(n):
            if isinstance(n, ast.Constant) and type(n.value) in (int, float, bool):
                return real32(n.value) if type(n.value) is float else n.value
            if isinstance(n, ast.Name):
                require(n.id in variables, 'Nonlocal scalar read: ' + n.id)
                return variables[n.id]
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                require(n.func.id in self.helpers and not n.keywords, 'Non-pure scalar call')
                return self.run(n.func.id, tuple(visit(a) for a in n.args), depth + 1)
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.Not, ast.USub)):
                v = visit(n.operand)
                return not v if isinstance(n.op, ast.Not) else -v
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                a, b = visit(n.left), visit(n.right)
                require(type(a) is type(b) is int, 'Only integer rank increments are supported')
                return a + b
            if isinstance(n, ast.Compare):
                require(len(n.ops) == 1, 'Chained scalar comparison')
                a, b = visit(n.left), visit(n.comparators[0])
                ops = {ast.Eq: lambda: a == b, ast.NotEq: lambda: a != b,
                       ast.Lt: lambda: a < b, ast.LtE: lambda: a <= b,
                       ast.Gt: lambda: a > b, ast.GtE: lambda: a >= b}
                require(type(n.ops[0]) in ops, 'Unsupported scalar comparison')
                return ops[type(n.ops[0])]()
            if isinstance(n, ast.BoolOp):
                raise ValueError('Use explicit branches, not mixed/shortcut boolean grouping')
            raise ValueError('Unsupported/non-pure scalar expression: ' + source)
        return visit(expression_node(source))

    def run(self, name, arguments, depth=0):
        require(depth <= 2, 'Unexpected recursive scalar helper')
        m, params = self.helpers[name]
        require(len(arguments) == len(params), 'Scalar argument count')
        variables = {'true': True, 'false': False}
        kinds = {}
        for p, value in zip(params, arguments):
            kind, variable = p.groups()
            require(type(value) is bool if kind == 'boolean' else type(value) is int if kind == 'integer' else type(value) in (int, float), 'Scalar argument type')
            variables[variable] = real32(value) if kind == 'real' else value
            kinds[variable] = kind
        active, stack = True, []
        for raw in m[4].splitlines():
            line = raw.split('//', 1)[0].strip()
            if not line:
                continue
            local = re.fullmatch(r'local (integer|real|boolean) (\w+)(?: = (.*))?', line)
            if local:
                kind, variable, initializer = local.groups()
                require(variable not in variables, 'Repeated scalar variable')
                kinds[variable] = kind
                variables[variable] = self.expression(initializer, variables, depth) if initializer else False if kind == 'boolean' else 0
            elif line.startswith('if ') and line.endswith(' then'):
                condition = self.expression(line[3:-5], variables, depth)
                require(type(condition) is bool, 'Scalar branch condition')
                stack.append([active, active and condition])
                active = active and condition
            elif line.startswith('elseif ') and line.endswith(' then'):
                require(stack, 'Unbalanced scalar elseif')
                parent, selected = stack[-1]
                condition = self.expression(line[7:-5], variables, depth)
                active = parent and not selected and condition
                stack[-1][1] = selected or active
            elif line == 'else':
                require(stack, 'Unbalanced scalar else')
                parent, selected = stack[-1]
                active = parent and not selected
                stack[-1][1] = True
            elif line == 'endif':
                require(stack, 'Unbalanced scalar endif')
                active = stack.pop()[0]
            elif line.startswith('set '):
                a = re.fullmatch(r'set (\w+) = (.*)', line)
                require(a and a[1] in kinds, 'Nonlocal scalar write')
                value = self.expression(a[2], variables, depth)
                if active:
                    variables[a[1]] = real32(value) if kinds[a[1]] == 'real' else value
            elif line.startswith('return '):
                value = self.expression(line[7:], variables, depth)
                require(type(value) is (bool if m[3] == 'boolean' else int), 'Scalar result type')
                if active:
                    return value
            else:
                raise ValueError('Unsupported/non-pure scalar statement: ' + line)
        raise ValueError('Scalar helper did not return')


def verify_comparators(script):
    p = ScalarProgram(script)
    checked = 0
    for total, other, lane, owner in itertools.product(TOTALS, TOTALS, range(4), range(4)):
        expected = (-real32(total), lane) < (-real32(other), owner)
        require(p.run(HELPERS[0], (total, lane, other, owner)) == expected, 'Player comparator oracle mismatch')
        checked += 1
        for serial, other_serial in itertools.product((1, 3, 8), repeat=2):
            expected = (-real32(total), lane, serial) < (-real32(other), owner, other_serial)
            require(p.run(HELPERS[1], (total, lane, serial, other, owner, other_serial)) == expected, 'Tower comparator oracle mismatch')
            checked += 1
    return checked


def verify_player_selection(script):
    p = ScalarProgram(script)
    checked = 0
    for totals in itertools.product((0.0, .375, .5, .625), repeat=4):
        for flags in itertools.product((False, True), repeat=4):
            lanes = [i for i in range(4) if flags[i]]
            expected = sorted(lanes, key=lambda i: (-real32(totals[i]), i))
            rows = {}
            for lane in lanes:
                args = (totals[lane], lane) + tuple(x for pair in zip(totals, flags) for x in pair)
                rank = p.run(HELPERS[2], args)
                require(0 <= rank < len(lanes) and rank not in rows, 'Duplicate/out-of-range player row')
                rows[rank] = lane
                checked += 1
            require([rows[i] for i in range(len(lanes))] == expected, 'Player selection oracle mismatch')
    return checked
