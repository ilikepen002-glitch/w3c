#!/usr/bin/env python3
"""Verify packaged farmer/collection UI objects and self-contained 64px icons.

Usage: python tools/VerifyPetUIArtifact.py ExampleMap.w3x
Object/layout contracts and actual MPQ resources are checked; native rendering,
portrait rendering and in-game effects remain separate playtest observations.
"""
from pathlib import Path
import ast
import hashlib
import itertools
import re
import struct
import sys

from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEquipmentAbilityArtifact import ability_objects, check_ability, require
from VerifyGroundItemArtifact import (verify_function_book,
                                      verify_global_channel_orders,
                                      unique_channel_order_count,
                                      verify_no_hunt_objects, verify_no_removed_raw_objects)

ROOT = Path(__file__).resolve().parents[1]
NORMAL_PREFIX = "ReplaceableTextures\\CommandButtons\\"
DISABLED_PREFIX = "ReplaceableTextures\\CommandButtonsDisabled\\DIS"
IMPORTED_PREFIX = "war3mapImported\\BTN"
# Current menu icons only. Old species SVGs remain archived, never bundled.
ICON_STEMS = (
    'TDPetMenuTools', 'TDPetCollection', 'TDPetPrevious', 'TDPetNext',
    'TDPetReturnBuilder', 'TDPetDeploy', 'TDPetRecall', 'TDPetCultivate',
    'TDPetInfo', 'TDPetEmptySlot', 'TDPetRelease', 'TDPetKeep', 'TDPetAdopt',
    'TDPetKeepOld', 'TDPetUseNew',
)

EXPECTED = {
    'Geqb': (3, 0, 'C', 'Aspb'),
    'Gupg': (1, 1, 'U', 'ANcl'),
    'Pcap': (1, 2, 'Q', 'ANcl'),
    'Pcol': (2, 2, 'W', 'ANcl'),
}
# Observed legacy native move/stop/hold/patrol/build cells stay unchanged.
NATIVE_CELLS = {(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)}
FARMER_ICONS = {'Geqb': 'TDPetMenuTools', 'Pcol': 'TDPetCollection', 'Pdep': 'TDPetDeploy'}
# x, y, hotkey, Channel target type, semantic icon. Base orders are allocated automatically.
COLLECTION_COMMANDS = {
    'Pc00': (0, 0, 'I', 0, 'TDPetCollection'),
    'Pc01': (1, 0, 'A', 0, 'TDPetPrevious'),
    'Pc02': (2, 0, 'D', 0, 'TDPetNext'),
    'Pc03': (3, 0, 'R', 0, 'TDPetReturnBuilder'),
    'Pc04': (0, 2, 'E', 1, 'TDPetDeploy'),
    'Pc05': (1, 2, 'Q', 0, 'TDPetRecall'),
    'Pc06': (2, 2, 'C', 0, 'TDPetCultivate'),
    'Pc07': (3, 2, 'W', 0, 'TDPetInfo'),
}
SPECIES = (
    (r'Units\Human\Phoenix\Phoenix.mdl', 'TDPetFlamePhoenix'),
    (r'Units\NightElf\FaerieDragon\FaerieDragon.mdl', 'TDPetStormFaerieDragon'),
    (r'Units\NightElf\Wisp\Wisp.mdl', 'TDPetGhostWisp'),
)
def elemental_species():
    import json
    manifest = json.loads((ROOT / 'assets/source/elemental-spirits/import-manifest.json').read_text())
    require(len(manifest['models']) == 15 and [m['suggestedSpeciesId'] for m in manifest['models']] == list(range(1, 16)),
            'Elemental model manifest species identity changed')
    return tuple((m['modelImportPath'], f'TDPetSpecies{i:02d}') for i, m in enumerate(manifest['models'], 1))


def manager_species(abilities=None, units=None):
    new = abilities is not None and any(re.fullmatch(r'L[0-9A-F]{3}', raw) and int(raw[1:], 16) >= 490 for raw in abilities)
    new |= units is not None and ('pd0D' in units or 'pv04' in units)
    return elemental_species() if new else SPECIES


SKILL_ICONS = (
    'BTNGauntletsOfOgrePower', 'BTNSteelMelee', 'BTNGlove', 'BTNBrilliance',
    'BTNCommand', 'BTNSlow', 'BTNFaerieFire', 'BTNCleavingAttack',
    'BTNCriticalStrike', 'BTNColdArrows', 'BTNDeathAndDecay', 'BTNBloodLust',
    'BTNInnerFire', 'BTNChainLightning', 'BTNImmolationOn', 'BTNCyclone',
)

SKILL_NAMES = ('坚韧之力', '战意', '疾攻', '灵感', '统御光环', '迟滞领域',
               '破甲印记', '连击蓄能', '处决追击', '分裂霜箭', '腐尸毒域',
               '狂热', '蓄力', '雷链', '火焰冲击', '风缚')
QUALITY_NAMES = ('|cffffffff白|r', '|cff40dd40绿|r', '|cff4090ff蓝|r', '|cffc060ff紫|r')


def icon_path(stem, disabled=False):
    return (DISABLED_PREFIX + 'BTN' if disabled else IMPORTED_PREFIX) + stem + '.blp'


def skill_icon_path(variant):
    if variant == 128:
        return icon_path('TDPetEmptySlot')
    name = SKILL_ICONS[(variant % 64) // 4]
    return (DISABLED_PREFIX if variant >= 64 else NORMAL_PREFIX) + name + '.blp'


def field_value(fields, key, level=0):
    matches = [value for (name, lvl, _), (_, value) in fields.items()
               if name == key and lvl == level]
    require(len(matches) == 1, f'Missing/ambiguous field {key} level={level}')
    return matches[0]


def verify_farmer_grid(abilities, units):
    require('A109' not in abilities, 'Retired farmer wage object A109 remains')
    occupied = {cell: 'native command' for cell in NATIVE_CELLS}
    for rawcode in EXPECTED:
        require(rawcode in abilities, f'Missing farmer command {rawcode}')
        fields = abilities[rawcode][1]
        cell = (field_value(fields, 'abpx'), field_value(fields, 'abpy'))
        require(cell not in occupied,
                f'{rawcode}: farmer cell overlaps {occupied.get(cell)} at {cell}')
        occupied[cell] = rawcode
    require(set(occupied) == {(x, y) for x in range(4) for y in range(3)} - {(2, 1), (3, 1), (3, 2)},
            'Farmer command grid must occupy exactly nine cells, leaving 2,1, 3,1 and 3,2 empty')
    for rawcode, (x, y, hotkey, parent) in EXPECTED.items():
        actual_parent, fields = abilities[rawcode]
        require(actual_parent == parent, f'{rawcode}: wrong parent {actual_parent}')
        actual = (field_value(fields, 'abpx'), field_value(fields, 'abpy'))
        require(actual == (x, y), f'{rawcode}: wrong farmer cell {actual}, expected {(x, y)}')
        require(field_value(fields, 'ahky') == hotkey, f'{rawcode}: wrong farmer hotkey')
    candidates = [(uid, fields) for uid, fields in units.items()
                  if set(EXPECTED).issubset(fields.get('uabi', '').split(','))]
    require(len(candidates) == 1, 'Expected exactly one farmer with all four commands')
    uid, farmer = candidates[0]
    require(farmer['uabi'].split(',') == ['AUbu', 'A117', 'Geqb',
                                        'Gupg', 'Pcap', 'Pcol'],
            f'{uid}: farmer ability attachment/order changed')
    require('A108' not in abilities and 'Prpr' not in abilities, 'Removed blink/repair objects remain')
    require('Amov' not in abilities, 'Native Amov must not be modified or disabled')
    for rawcode, stem in FARMER_ICONS.items():
        fields = abilities[rawcode][1]
        require(field_value(fields, 'aart') == icon_path(stem), f'{rawcode}: farmer icon path mismatch')
        if rawcode != 'Geqb':
            require(field_value(fields, 'arar') == icon_path(stem), f'{rawcode}: farmer research icon path mismatch')
    return uid


def verify_collection_commands(abilities, current_manager=False):
    cells, icons, orders = {}, [], []
    for rawcode in COLLECTION_COMMANDS:
        require(rawcode in abilities, f'Missing collection command {rawcode}')
        parent, fields = abilities[rawcode]
        require(parent == 'ANcl', f'{rawcode}: collection command must inherit Channel')
        cell = (field_value(fields, 'abpx'), field_value(fields, 'abpy'))
        require(cell not in cells, f'{rawcode}: collection cell overlaps {cells.get(cell)}')
        cells[cell] = rawcode
        icons.append(field_value(fields, 'aart'))
        orders.append(field_value(fields, 'Ncl6', 1))
    require(len(set(icons)) == 8, 'Collection command icons must be distinct')
    require(len(set(orders)) == 8, 'Display command base orders collide')
    for rawcode, (x, y, hotkey, target, stem) in COLLECTION_COMMANDS.items():
        fields = abilities[rawcode][1]
        require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (x, y),
                f'{rawcode}: collection command cell changed')
        require(field_value(fields, 'ahky') == hotkey, f'{rawcode}: collection command hotkey changed')
        require(field_value(fields, 'Ncl2', 1) == target, f'{rawcode}: collection target type changed')
        for field in ('aart', 'arar'):
            require(field_value(fields, field) == icon_path(stem), f'{rawcode}: {field} icon path mismatch')
    verify_global_channel_orders(abilities)
    verify_cultivation_command(abilities, current_manager=current_manager)


def verify_cultivation_command(abilities, current_manager=False):
    fields = abilities['Pc06'][1]
    name = '洗练 / 开栏(C)' if current_manager else '洗练 / 开栏 / 释放(C)'
    require(field_value(fields, 'anam') == name,
            f'Pc06: cultivation name must explicitly say {name}')
    require(field_value(fields, 'atp1', 1) == name,
            f'Pc06: cultivation tooltip must explicitly say {name}')
    description = field_value(fields, 'aub1', 1)
    require(all(word in description for word in (('洗练', '开栏') if current_manager else ('洗练', '开栏', '释放'))),
            'Pc06: cultivation description must explain reroll, slot opening and release')
    if current_manager:
        require('释放' not in description, 'Pc06: obsolete cultivation release entrance')
    for field in ('ahky', 'arhk', 'auhk'):
        require(field_value(fields, field) == 'C', f'Pc06: {field} cultivation hotkey must remain C')
    require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (2, 2),
            'Pc06: cultivation command must remain at 2,2')


def verify_capture_only(abilities, units, current_manager=False):
    verify_no_hunt_objects(abilities, units)
    for rawcode in ('Pcap', 'Pcol'):
        fields = abilities[rawcode][1]
        for (field, level, _), (_, text) in fields.items():
            if field in ('anam', 'atp1', 'aub1'):
                require('猎杀' not in text,
                        f'{rawcode} level {level}: obsolete wild-hunt text remains')
    for wave in range(1, 33):
        for species in range(1, len(manager_species(abilities, units)) + 1):
            rawcode = f'p{wave:02X}{species:X}'
            wild = units[rawcode]
            description = wild.get('ides', '')
            require('捕获' in description and '猎杀' not in description,
                    f'{rawcode}: wild description must say capture without obsolete hunt option')


def jass_function(script, name):
    match = re.search(r'^function ' + re.escape(name) + r' takes[^\n]*\n(.*?)^endfunction',
                      script, re.MULTILINE | re.DOTALL)
    require(match is not None, f'Missing packaged JASS function {name}')
    return match


def _integer_expression(expression, variables, functions=None):
    """Evaluate only the scalar/array-read subset used by the pet helpers."""
    require(not (re.search(r'\band\b', expression) and re.search(r'\bor\b', expression)),
            f'Ambiguous packaged scalar boolean precedence: {expression}')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, bool, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in variables:
            return variables[node.id]
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            name, index = node.value.id, visit(node.slice)
            require(name in variables and isinstance(variables[name], dict)
                    and type(index) is int and index in variables[name],
                    f'Unsupported/missing packaged scalar array read: {expression}')
            return variables[name][index]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            require(functions is not None and node.func.id in functions and not node.keywords,
                    f'Unsupported packaged scalar call: {node.func.id}')
            return functions[node.func.id](*(visit(argument) for argument in node.args))
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            left, right = visit(node.left), visit(node.right)
            return (left + right if isinstance(node.op, ast.Add) else
                    left - right if isinstance(node.op, ast.Sub) else left * right)
        if isinstance(node, ast.BoolOp):
            # JASS short-circuits, including the null-record guards before reads.
            if isinstance(node.op, ast.And):
                return all(bool(visit(value)) for value in node.values)
            return any(bool(visit(value)) for value in node.values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.Not, ast.USub)):
            result = visit(node.operand)
            return not result if isinstance(node.op, ast.Not) else -result
        if isinstance(node, ast.Compare):
            left = visit(node.left)
            for operator, operand in zip(node.ops, node.comparators):
                right = visit(operand)
                operations = {ast.Eq: lambda: left == right, ast.NotEq: lambda: left != right,
                              ast.Lt: lambda: left < right, ast.LtE: lambda: left <= right,
                              ast.Gt: lambda: left > right, ast.GtE: lambda: left >= right}
                require(type(operator) in operations, 'Unsupported scalar helper comparison')
                if not operations[type(operator)]():
                    return False
                left = right
            return True
        raise ValueError(f'Unsupported packaged scalar expression: {expression}')
    return visit(ast.parse(expression, mode='eval').body)


def _run_scalar_helper(match, arguments, constants=None, functions=None,
                       result_field=None, on_assignment=None, debug_stack=False):
    header = match.group(0).splitlines()[0]
    parameters = re.findall(r'(?:integer|boolean|unit|player|string) (\w+)', header)
    require(len(parameters) == len(arguments), 'Packaged scalar helper argument count changed')
    variables = {'true': True, 'false': False, 'null': None, **(constants or {}),
                 **dict(zip(parameters, arguments))}
    active, branches = True, []
    stack_depth = 0
    stack_pushes = 0
    stack_started = False
    for source_line in match.group(1).splitlines():
        line = source_line.split('//', 1)[0].strip()
        if not line:
            continue
        if debug_stack and line == 'set wurst_stack[wurst_stack_depth] = w__wurst_stackPos':
            require(active and stack_depth == 0 and stack_pushes == 0
                    and 'w__wurst_stackPos' in variables,
                    'Unexpected packaged scalar debug stack push')
            stack_pushes += 1
            continue
        if debug_stack and line in ('set wurst_stack_depth = wurst_stack_depth + 1',
                                    'set wurst_stack_depth = wurst_stack_depth - 1'):
            if active:
                if line.endswith('+ 1'):
                    require(not stack_started and stack_depth == 0,
                            'Unexpected packaged scalar debug stack increment')
                    stack_started = True
                    stack_depth += 1
                else:
                    require(stack_started and stack_depth == 1,
                            'Unexpected packaged scalar debug stack decrement')
                    stack_depth -= 1
                require(stack_pushes == 1 and stack_depth in (0, 1),
                        'Unbalanced packaged scalar debug stack depth')
            continue
        if line.startswith('local '):
            declaration = re.fullmatch(r'local (integer|boolean|unit|player|string) (\w+)(?: = (.*))?', line)
            require(declaration is not None, f'Unsupported packaged scalar declaration: {line}')
            kind, name, initializer = declaration.groups()
            variables[name] = (_integer_expression(initializer, variables, functions) if initializer else
                               False if kind == 'boolean' else None if kind in ('unit', 'player') else 0)
        elif line.startswith('if ') and line.endswith(' then'):
            selected = active and bool(_integer_expression(line[3:-5], variables, functions))
            branches.append([active, selected])
            active = selected
        elif line.startswith('elseif ') and line.endswith(' then'):
            require(bool(branches), 'Invalid packaged scalar elseif')
            parent, selected = branches[-1]
            active = parent and not selected and bool(_integer_expression(line[7:-5], variables, functions))
            branches[-1][1] = selected or active
        elif line == 'else':
            require(bool(branches), 'Invalid packaged scalar else')
            parent, selected = branches[-1]
            active = parent and not selected
            branches[-1][1] = True
        elif line == 'endif':
            require(bool(branches), 'Invalid packaged scalar endif')
            active = branches.pop()[0]
        elif line.startswith('return '):
            if active:
                require(not debug_stack or (stack_pushes == 1 and stack_started and stack_depth == 0),
                        'Packaged scalar return leaked debug stack frame')
                return _integer_expression(line[7:], variables, functions)
        elif line == 'return':
            if active:
                require(result_field is not None, 'Unexpected void return in scalar helper')
                return variables[result_field]
        elif line.startswith('set '):
            variable, expression = line[4:].split('=', 1)
            if active:
                variable = variable.strip()
                require(re.fullmatch(r'\w+', variable) is not None and variable in variables,
                        f'Unsupported packaged scalar assignment target: {variable}')
                variables[variable] = _integer_expression(expression.strip(), variables, functions)
                if on_assignment is not None:
                    on_assignment(variable, variables[variable])
        else:
            raise ValueError(f'Unsupported packaged scalar helper statement: {line}')
    if result_field is not None:
        return variables[result_field]
    raise ValueError('Packaged scalar helper did not return')


def verify_dialog_hotkeys(script):
    """Prove compiled mappings and the UI-to-native hotkey argument chain."""
    helper = jass_function(script, 'tdPetDialogHotkey')
    constants = {name: int(number) for name, number in re.findall(
        r'\bset (\w*TD_PET_DIALOG_\w+)\s*=\s*(-?\d+)\b', script)}
    expected = {(1, action): 48 + action for action in range(1, 5)}
    expected.update({(4, 10): 49, (4, 11): 50, (3, 14): 49, (3, 0): 50})
    for mode in range(-1, 5):
        for action in list(range(15)) + [100, 120]:
            actual = _run_scalar_helper(helper, (mode, action), constants)
            require(actual == expected.get((mode, action), 0),
                    f'Dialog hotkey mode={mode} action={action}: got {actual}, '
                    f'expected {expected.get((mode, action), 0)}')
    bridge = jass_function(script, 'addButton').group(1)
    candidates = list(re.finditer(r'^function (dialog_addButton(?:_\d+)*) takes dialog (\w+), string (\w+), integer (\w+) returns button\n(.*?)^endfunction',
                                  script, re.MULTILINE | re.DOTALL))
    require(len(candidates) == 1, 'Expected one integer-hotkey native dialog overload')
    name = candidates[0][1]
    require(re.search(re.escape(name) + r'\([^\n]*tdPetDialogHotkey\('
                      r'[^\n]*TDPetDialogSession_mode[^\n]*TDPetUI_sessions', bridge) is not None,
            'Pet UI addButton must pass session-mode hotkey to native dialog overload')
    native = candidates[0][0]
    parameters = re.search(r'takes dialog (\w+), string (\w+), integer (\w+) returns', native)
    require(parameters is not None, 'Native dialog overload lost integer hotkey parameter')
    dialog, label, hotkey = parameters.groups()
    require(f'DialogAddButton({dialog}, {label}, {hotkey})' in native,
            'Native DialogAddButton must receive the real integer hotkey')
    cultivation = jass_function(script, 'showCultivation').group(1)
    release = jass_function(script, 'showReleaseConfirmation').group(1)
    for text in ('1 保留旧技能', '2 替换新技能', ' 洗练栏'):
        require(text in cultivation, f'Packaged cultivation dialog lacks label {text}')
    for text in ('1 确认永久释放', '2 取消'):
        require(text in release, f'Packaged release dialog lacks label {text}')


def verify_skill_fit_abilities(script):
    """Exercise all 16 skills against four actual compiled host-capability states."""
    helper = jass_function(script, 'tdPetSkillFitsAbilities')
    for skill in range(16):
        for has_split_arrow in (False, True):
            for has_corpse_explosion in (False, True):
                expected = (has_split_arrow if skill == 9 else
                            has_corpse_explosion if skill == 10 else True)
                actual = _run_scalar_helper(helper, (skill, has_split_arrow, has_corpse_explosion))
                require(actual is expected,
                        f'Pet skill fit skill={skill} split={has_split_arrow} '
                        f'corpse={has_corpse_explosion}: got {actual}, expected {expected}')


def _pet_rule_functions(script):
    """Read real compiled helpers; only power/modulo are arithmetic primitives."""
    names = ('tdPetSkillIsNumeric', 'tdPetSkillIsActive', 'tdPetSkillIsUniversal',
             'bitset_get', 'bitset_containsPow')
    helpers = {name: jass_function(script, name) for name in names}
    power = jass_function(script, 'int_pow')
    args = re.findall(r'integer (\w+)', power.group(0).splitlines()[0])
    body = re.sub(r'\s+', ' ', power.group(1)).strip()
    shape = re.fullmatch(r'local integer (\w+) = 1 local integer (\w+) = 1 '
                         r'local integer (\w+) = ' + re.escape(args[1]) +
                         r' loop exitwhen \2 > \3 set \1 = \1 \* ' + re.escape(args[0]) +
                         r' set \2 = \2 \+ 1 endloop return \1', body)
    require(shape is not None, 'Packaged int_pow no longer implements nonnegative integer power')
    def verified_power(base, exponent):
        require(base == 2 and type(exponent) is int and 0 <= exponent <= 16,
                'Packaged bitset power arguments leave verified integer subset')
        return 1 << exponent
    functions = {'int_pow': verified_power,
                 'ModuloInteger': lambda value, divisor: value % divisor}
    for name, helper in helpers.items():
        functions[name] = lambda *args, helper=helper: _run_scalar_helper(helper, args, functions=functions)
    if re.search(r'^function tdActiveSkillDefinitionCount takes', script, re.M):
        # The shared definition lookup contains a real compiled loop and tuple
        # return globals. Use the existing bounded JASS runtime instead of a
        # second Python active-skill list or the old scalar-only subset.
        from VerifyActiveCooldownContract import ActiveJassRuntime
        active_runtime = ActiveJassRuntime(script)
        active_ids = set()
        for index in range(active_runtime.invoke('tdActiveSkillDefinitionCount')):
            active_runtime.invoke('tdActiveSkillDefinitionAt', index)
            skill = active_runtime.globals['tdActiveSkillDefinitionAt_return_petSkillId']
            if skill >= 0:
                active_ids.add(skill)
        functions['tdPetSkillIsActive'] = lambda skill: active_runtime.invoke('tdPetSkillIsActive', skill)
    else:
        # Legacy fixtures have the old current16 classifier. Their independent
        # historical matrix remains intact, with no new-MPQ claim.
        active_ids = set(range(11, 16))
    for skill in range(16):
        require(functions['tdPetSkillIsNumeric'](skill) is (skill <= 3),
                f'Packaged numeric skill classification changed for {skill}')
        require(functions['tdPetSkillIsActive'](skill) is (skill in active_ids),
                f'Packaged active skill classification changed for {skill}')
        require(functions['tdPetSkillIsUniversal'](skill) is (skill >= 4 and skill not in (9, 10)),
                f'Packaged universal skill classification changed for {skill}')
        for mask in [0] + [1 << index for index in range(16)]:
            require(functions['bitset_get'](mask, skill) is bool(mask & (1 << skill)),
                    f'Packaged bitset duplicate check changed for skill={skill} mask={mask}')
    return functions


def four_slot_allowed(skill, slot, duplicate=False, has_active=False):
    """Independent fixed-role oracle; has_active cannot change a physical role."""
    if skill not in {*range(4), *range(5, 9), 11, 12, *range(16, 49)} or duplicate:
        return False
    return (0 <= skill <= 3 if slot == 0 else
            skill in (5, 6, 7, 8, 16, 17, 18) if slot == 1 else
            skill in (5, 6, 7, 8, 16, 17, 18) or 39 <= skill <= 48 if slot == 2 else
            skill in (11, 12) or 19 <= skill <= 38 if slot == 3 else False)


def verify_skill_allowed(script):
    """Enumerate current compiled roles and retain the legacy 2,176-mask oracle."""
    if re.search(r'^function tdPetSkillDefined takes', script, re.M):
        from VerifyActiveCooldownContract import ActiveJassRuntime
        r = ActiveJassRuntime(script)
        n = phase_one_catalog(); count = n['TD_PET_SKILL_COUNT']
        four_slots = 'tdPetSkillIsAttackPassive' in r.functions
        require(four_slots == ('tdPetSkillIsAttackPassive' in n), 'Compiled/source fixed-slot generation mismatch')
        numeric_live = 'tdPetSkillIsNumeric' in r.functions
        if not numeric_live:
            require(count == 49 and r.globals.get('TDPetData_TD_PET_SKILL_COUNT') == 49
                    and not re.search(r'\btdPetSkillIsNumeric\(', script),
                    'Missing numeric classifier is only legal when final catalog DCE removes every use')
        for skill, slot, duplicate, has_active in itertools.product(range(-1, count + 2), range(-1, 5), (False, True), (False, True)):
            # Each identity is an independent bounded fixture, never a cumulative budget reset.
            if slot == -1 and not duplicate and not has_active:
                r = ActiveJassRuntime(script)
            require(r.invoke('tdPetSkillDefined', skill) is n['tdPetSkillDefined'](skill), 'Compiled/source defined skill identity mismatch')
            if numeric_live:
                require(r.invoke('tdPetSkillIsNumeric', skill) is n['tdPetSkillIsNumeric'](skill), 'Compiled/source numeric classification mismatch')
            require(r.invoke('tdPetSkillIsActive', skill) is n['tdPetSkillIsActive'](skill), 'Compiled/source active classification mismatch')
            require(r.invoke('tdPetSkillIsUniversal', skill) is n['tdPetSkillIsUniversal'](skill), 'Compiled/source universal classification mismatch')
            expected = n['tdPetSkillAllowed'](skill, slot, duplicate, has_active)
            if four_slots:
                require(n['tdPetSkillIsAttackPassive'](skill) is (skill in (5, 6, 7, 8, 16, 17, 18)), 'Source attack-passive classification mismatch')
                require(r.invoke('tdPetSkillIsAttackPassive', skill) is (skill in (5, 6, 7, 8, 16, 17, 18)), 'Compiled attack-passive classification mismatch')
                require(expected is four_slot_allowed(skill, slot, duplicate, has_active), 'Source fixed-slot admission differs from independent oracle')
            require(r.invoke('tdPetSkillAllowed', skill, slot, duplicate, has_active) is expected, f'Pet skill allowed skill={skill} slot={slot} duplicate={duplicate} active={has_active}')
        if count == 49:
            for species, skill, slot, duplicate in itertools.product(range(0, 17), range(-1, 51), range(4), (False, True)):
                if skill == -1 and slot == 0 and not duplicate:
                    r = ActiveJassRuntime(script)
                expected = n['tdPetSkillAllowedForSpecies'](skill, slot, species, duplicate)
                if four_slots:
                    element = (skill - 19) // 4 + 1 if 19 <= skill <= 38 else 0
                    independent = 1 <= species <= 15 and four_slot_allowed(skill, slot, duplicate) and (element == 0 or element == (species - 1) // 3 + 1)
                    require(expected is independent, 'Source species/fixed-slot admission differs from independent oracle')
                require(r.invoke('tdPetSkillAllowedForSpecies', skill, slot, species, duplicate) is expected,
                        'Compiled own-element slot admission changed')
        for skill in (0, 16, 31, 32, 40, 127, 255):
            for position in range(4):
                values = [skill + 1, skill + 2, skill + 3, skill + 4]
                require(r.invoke('tdPetSkillOwned', skill, *values) is False, 'Full-integer nonduplicate identity truncation')
                values[position] = skill
                require(r.invoke('tdPetSkillOwned', skill, *values) is True, 'Full-integer duplicate identity/owned-slot truncation')
        return
    helper, functions = jass_function(script, 'tdPetSkillAllowed'), _pet_rule_functions(script)
    for skill, slot, has_active, mask in itertools.product(
            range(16), range(4), (False, True), [0] + [1 << index for index in range(16)]):
        expected = (not bool(mask & (1 << skill)) and
                    (skill <= 3 if slot == 0 else
                     skill >= 4 and (slot != 1 or skill not in (9, 10)) and
                     (not has_active or not functions['tdPetSkillIsActive'](skill))))
        actual = _run_scalar_helper(helper, (skill, slot, mask, has_active), functions=functions)
        require(actual is expected,
                f'Pet skill allowed skill={skill} slot={slot} active={has_active} mask={mask}: '
                f'got {actual}, expected {expected}')


def verify_lane_enemy_guards(script, require_match_registry=False):
    """Enumerate every existing guard, plus registration when present.

    Only the exact compiler diagnostic-only trailing-string signature is
    accepted. It is executed with balanced debug-stack validation, not erased.
    """
    helper = jass_function(script, 'tdLaneEnemyCheckEnum')
    header = helper.group(0).splitlines()[0]
    if header == 'function tdLaneEnemyCheckEnum takes nothing returns nothing':
        arguments, debug_stack = (), False
    else:
        require(header == 'function tdLaneEnemyCheckEnum takes string w__wurst_stackPos returns nothing',
                'Lane enemy guards unexpected compiler signature')
        arguments, debug_stack = ('offline lane-enemy guard matrix',), True
    registered = 'tdEnemyBelongsToCurrentMatch(' in helper.group(1)
    require(not require_match_registry or registered, 'Lane enemy guards missing current-match registration')
    if registered:
        # Compiler-local suffixes change when unrelated closures capture `enemy`.
        # Bind the guard to the actual GetEnumUnit result, never an arbitrary null check.
        enum_bindings = re.findall(r'^\s*(?:set|local unit) (\w+) = GetEnumUnit\(\)\s*$', helper.group(1), re.M)
        require(len(enum_bindings) == 1, 'Lane enemy guards ambiguous enum-unit binding')
        require(re.search(r'\b' + re.escape(enum_bindings[0]) + r'\s*==\s*null\b', helper.group(1)),
                'Lane enemy guards missing explicit null rejection')
    field = 'TDSpawn_tdLaneEnemyCheckFound'
    for wild, same_lane, alive, enemy_owner, nonnull, found, any_wave, same_wave, same_match in itertools.product(
            (False, True), (False, True), (False, True), (False, True),
            (False, True), (False, True), (False, True), (False, True),
            (False, True) if registered else (True,)):
        assignments = []
        enemy = 1 if nonnull else None
        constants = {'TDConfig_TD_ENEMY_PLAYER_ID': 4,
                     'TDSpawn_tdLaneEnemyCheckPlayer': 2,
                     'TDSpawn_tdLaneEnemyCheckWave': 0 if any_wave else 7,
                     field: found}
        functions = {'GetEnumUnit': lambda: enemy,
                     'tdPetIsWild': lambda unit: wild,
                     'unit_isAlive': lambda unit: alive,
                     'GetOwningPlayer': lambda unit: 4 if enemy_owner else 5,
                     'Player': lambda player: player,
                     'tdEnemyLaneId': lambda unit: 2 if same_lane else 3,
                     'tdEnemyWave': lambda unit: 7 if same_wave else 8}
        if registered:
            functions['tdEnemyBelongsToCurrentMatch'] = lambda unit, provenance: unit is not None and same_match
        qualifies = (not wild and same_lane and alive and enemy_owner and nonnull and
                     not found and same_match and (any_wave or same_wave))
        actual = _run_scalar_helper(helper, arguments, constants, functions, field,
                                    lambda name, value: assignments.append((name, value)), debug_stack=debug_stack)
        writes = [value for name, value in assignments if name == field]
        require(actual is (found or qualifies) and writes == ([True] if qualifies else []),
                f'Lane enemy guards wild={wild} lane={same_lane} alive={alive} owner={enemy_owner} '
                f'nonnull={nonnull} found={found} anywave={any_wave} matchingwave={same_wave} registered={same_match}: '
                f'found={actual}, writes={writes}')


def verify_species_identity(units):
    for species, (model, stem) in enumerate(SPECIES, 1):
        uid = f'pd0{species}'
        require(uid in units, f'Missing species display {uid}')
        display = units[uid]
        require(display.get('umdl') == model, f'{uid}: species model mismatch')
        for field in ('uico', 'ussi'):
            require(display.get(field) == icon_path(stem), f'{uid}: {field} species icon mismatch')
        require(display.get('uabi', '').split(',') == ['Avul'] + list(COLLECTION_COMMANDS),
                f'{uid}: collection command attachment/order changed')


def is_phase_one_ui(abilities):
    fields = abilities.get('s000', abilities.get('s00B', (None, {})))[1]
    levels = [value for (key, level, _), (_, value) in fields.items() if key == 'alev' and level == 0]
    require(len(levels) <= 1, 'Ambiguous skill display level count')
    return levels == [4]


def phase_one_catalog():
    """Current production IDs/names/icons; never expose future unimplemented skills."""
    from VerifyPetManagerSource import scalar_helpers, compile_source_helper, source
    n = scalar_helpers()
    compile_source_helper(source('TDPetUIData'), 'tdPetSkillIconName', n, 1)
    compile_source_helper(source('TDPetUIData'), 'tdPetSkillIconPath', n, 2)
    from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources, definitions
    active_ids = {d.petSkillId for d in definitions(SourceScalarEvaluator(read_sources())) if d.petSkillId >= 0}
    n['tdPetSkillIsActive'] = lambda skill: skill in active_ids
    compile_source_helper(source('TDPetRules'), 'tdPetSkillIsUniversal', n, 1)
    compile_source_helper(source('TDPetRules'), 'tdPetSkillAllowed', n, 4)
    compile_source_helper(source('TDPetData'), 'tdPetSpeciesElement', n, 1)
    compile_source_helper(source('TDPetElementData'), 'tdPetSkillElement', n, 1)
    compile_source_helper(source('TDPetRules'), 'tdPetSkillAllowedForSpecies', n, 4)
    return n


def verify_phase_one_slots(abilities):
    n = phase_one_catalog()
    count, empty = n['TD_PET_SKILL_COUNT'], n['TD_PET_SLOT_EMPTY']
    expected = set()
    for slot in range(4):
        for variant in range(empty + 1):
            is_empty = variant == empty
            skill, locked = variant % count, variant >= count and not is_empty
            if not is_empty and (not n['tdPetSkillAllowed'](skill, slot, False, False) or (locked and slot < 2)):
                continue
            rawcode = f's{slot}{variant:02X}'; expected.add(rawcode)
            require(rawcode in abilities, 'Missing legal skill display ' + rawcode)
            parent, fields = abilities[rawcode]
            require(parent == 'AOcr', rawcode + ': passive display parent')
            require(field_value(fields, 'alev') == (1 if is_empty else 4), rawcode + ': quality must live in levels')
            require(not any(key == 'Ncl6' for key, _, _ in fields), rawcode + ': display consumed Channel order')
            require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (slot, 1), rawcode + ': fixed slot position')
            for field in ('aher', 'aite', 'achd'):
                require(field_value(fields, field) == 0, rawcode + ': unsafe display flag ' + field)
            require(field_value(fields, 'areq') == '', rawcode + ': unexpected requirements')
            icon = icon_path('TDPetEmptySlot') if is_empty else n['tdPetSkillIconPath'](skill, locked)
            require(field_value(fields, 'aart') == icon, rawcode + ': bright/locked/empty icon mismatch')
            require(field_value(fields, 'anam') == ('空栏' if is_empty else n['tdPetSkillNameById'](skill)), rawcode + ': skill identity name')
            for quality in range(1, 2 if is_empty else 5):
                require(field_value(fields, 'Ocr1', quality) == 0.0 and field_value(fields, 'Ocr2', quality) == 1.0, rawcode + ': accidental combat effect')
                label = '空栏' if is_empty else QUALITY_NAMES[quality - 1] + ' ' + n['tdPetSkillNameById'](skill) + (' [共鸣锁定]' if locked else '')
                if count == 49:
                    slot_name = ('属性栏', '攻击被动栏', '强化栏', '自动主动栏')[slot] if 'tdPetSkillIsAttackPassive' in n else '主动栏' if slot == 0 else '被动栏' + str(slot)
                    label = '空' + slot_name if is_empty else slot_name + ' · ' + label
                require(field_value(fields, 'atp1', quality) == label, rawcode + ': quality/identity tooltip')
                description = field_value(fields, 'aub1', quality)
                if is_empty:
                    require('新增' in description and '1开栏石' in description and '最多4栏' in description and '共鸣锁定' not in description, rawcode + ': empty slot rules')
                elif locked:
                    bright = abilities[f's{slot}{skill:02X}'][1]
                    prefix = f'技能已获得；共鸣锁定，完成本路第{4 if slot == 2 else 8}波解锁。|n'
                    require(description == prefix + field_value(bright, 'aub1', quality), rawcode + ': locked strength/description')
                else:
                    require('共鸣锁定' not in description + label, rawcode + ': bright mislabeled locked')
                    if 'tdPetSkillIsAttackPassive' in n and slot == 3:
                        require('冷却就绪后，下一次有效普攻自动释放' in description, rawcode + ': missing automatic active trigger rule')
    actual = {raw for raw in abilities if re.fullmatch(r's[0-3][0-9A-F]{2}', raw)}
    require(actual == expected, 'Illegal, retired or missing slot objects: ' + repr(actual ^ expected))
    return len(expected)


def verify_slot_icons(abilities, current_manager=False):
    if is_phase_one_ui(abilities):
        return verify_phase_one_slots(abilities)
    for slot in range(4):
        for variant in range(129):
            rawcode = f's{slot}{variant:02X}'
            require(rawcode in abilities, f'Missing passive slot variant {rawcode}')
            parent, fields = abilities[rawcode]
            require(parent == 'AOcr', f'{rawcode}: skill display must be passive')
            require(not any(key == 'Ncl6' for key, _, _ in fields),
                    f'{rawcode}: passive display must not allocate channel orders')
            require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (slot, 1),
                    f'{rawcode}: wrong fixed skill cell')
            require(field_value(fields, 'Ocr1', 1) == 0.0 and field_value(fields, 'Ocr2', 1) == 1.0,
                    f'{rawcode}: passive display must have no critical-strike combat effect')
            for field in ('aher', 'aite', 'achd'):
                require(field_value(fields, field) == 0, f'{rawcode}: passive display flag {field} changed')
            require(field_value(fields, 'areq') == '', f'{rawcode}: passive display must have no requirements')
            state = 'empty slot' if variant == 128 else 'locked skill' if variant >= 64 else 'bright skill'
            require(field_value(fields, 'aart') == skill_icon_path(variant), f'{rawcode}: {state} icon mismatch')
            label, description = field_value(fields, 'atp1', 1), field_value(fields, 'aub1', 1)
            if variant == 128:
                require('共鸣锁定' not in label + description,
                        f'{rawcode}: empty slot must not be resonance locked')
                require('空栏' in label and '新增' in description and '1开栏石' in description and '最多4栏' in description,
                        f'{rawcode}: empty slot explanation changed')
            elif variant >= 64:
                require('共鸣锁定' in label and '空栏' not in label,
                        f'{rawcode}: locked skill must retain specific identity')
                require('解锁' in description and '技能已获得' in description,
                        f'{rawcode}: missing resonance explanation')
            else:
                require('共鸣锁定' not in label and '空栏' not in label,
                        f'{rawcode}: bright skill mislabeled as empty/locked')
            if variant < 128:
                base_variant = variant % 64
                expected_label = QUALITY_NAMES[base_variant % 4] + ' ' + SKILL_NAMES[base_variant // 4]
                if variant >= 64:
                    expected_label += ' [共鸣锁定]'
                    bright_fields = abilities[f's{slot}{base_variant:02X}'][1]
                    lock_prefix = (f'技能已获得；共鸣锁定，完成本路第{4 if slot == 2 else 8}波解锁。|n' if current_manager else f'技能已获得，尚未生效。完成本路第{4 if slot == 2 else 8}波解锁。|n')
                    require(description == lock_prefix + field_value(bright_fields, 'aub1', 1),
                            f'{rawcode}: locked skill description mismatch')
                require(label == expected_label and field_value(fields, 'anam') == expected_label,
                        f'{rawcode}: skill/quality identity label changed')
            else:
                require(label == field_value(fields, 'anam') == '空栏', f'{rawcode}: empty slot label changed')


def decode_icon_blp(data, path):
    # All project-generated icons are BLP1 palettized alpha8 with seven mips.
    require(len(data) >= 1180 and data[:4] == b'BLP1', f'{path}: invalid/truncated BLP1')
    compression, alpha, width, height, kind, has_mips = struct.unpack_from('<6I', data, 4)
    require((compression, alpha, kind, has_mips) == (1, 8, 5, 1),
            f'{path}: unsupported BLP1 encoding; expected palette/alpha8/mips')
    require((width, height) == (64, 64), f'{path}: icon must be 64x64')
    offsets = struct.unpack_from('<16I', data, 28)
    sizes = struct.unpack_from('<16I', data, 92)
    previous_end = 1180
    for level in range(16):
        if level >= 7:
            require(offsets[level] == sizes[level] == 0, f'{path}: unexpected extra mip {level}')
            continue
        count = max(1, width >> level) * max(1, height >> level)
        require(sizes[level] == count * 2, f'{path}: mip {level} alpha8 payload size mismatch')
        require(offsets[level] == previous_end and offsets[level] + sizes[level] <= len(data),
                f'{path}: mip {level} out of bounds or overlaps')
        previous_end = offsets[level] + sizes[level]
    require(previous_end == len(data), f'{path}: trailing BLP bytes')
    indices = data[offsets[0]:offsets[0] + 4096]
    alphas = data[offsets[0] + 4096:offsets[0] + 8192]
    rgba = []
    for index, opacity in zip(indices, alphas):
        blue, green, red, _ = data[156 + index * 4:160 + index * 4]
        rgba.append((red, green, blue, opacity))
    require(any(pixel[3] for pixel in rgba), f'{path}: icon is fully transparent')
    require(len(set(rgba)) > 4, f'{path}: icon has no usable artwork')
    return rgba


def verify_imported_icons(artifact, root=ROOT):
    hashes = {False: {}, True: {}}
    for stem in ICON_STEMS:
        pixels = {}
        for disabled in (False, True):
            path = icon_path(stem, disabled)
            require(artifact.has(path), f'Missing packaged pet UI icon: {path}')
            data = artifact.extract(path)
            source = root / 'imports' / Path(path.replace('\\', '/'))
            require(source.is_file(), f'Missing source pet UI icon: {source.relative_to(root)}')
            require(data == source.read_bytes(), f'{path}: packaged icon hash differs from source')
            digest = hashlib.sha256(data).hexdigest()
            require(digest not in hashes[disabled],
                    f'{path}: duplicate semantic icon artwork with {hashes[disabled].get(digest)}')
            hashes[disabled][digest] = path
            pixels[disabled] = decode_icon_blp(data, path)
            print(f'PASS RESOURCE: {path}; BLP1 palette/alpha8, 64x64, 7 mips; SHA256={digest}')
        normal, gray = pixels[False], pixels[True]
        require(all(r == g == b for r, g, b, _ in gray), f'{stem}: disabled icon must be grayscale')
        require(sum(r + g + b for r, g, b, _ in gray) <
                sum(r + g + b for r, g, b, _ in normal) * 0.60,
                f'{stem}: disabled icon must be visibly dimmer than normal')
    require(not set(hashes[False]) & set(hashes[True]), 'Normal and disabled icons must differ')
    return hashes


def verify_elemental_resources(artifact, root=ROOT):
    import json
    model_manifest = json.loads((root / 'assets/source/elemental-spirits/import-manifest.json').read_text())
    require(len(model_manifest['models']) == 15, 'Missing final original model family')
    for model in model_manifest['models']:
        for key, sha in (('modelImportPath', 'modelSha256'), ('requiredTextureImportPath', 'textureSha256')):
            path = model[key]
            require(artifact.has(path), 'Missing elemental model/atlas: ' + path)
            data = artifact.extract(path)
            require(hashlib.sha256(data).hexdigest() == model[sha] and
                    data == (root / 'imports' / path.replace('\\', '/')).read_bytes(),
                    'Elemental model/atlas differs from approved final SHA: ' + path)
    ui = json.loads((root / 'assets/source/elemental-spirits/ui-manifest.json').read_text())
    expected = {f'TDPetSpecies{s:02d}' for s in range(1, 16)}
    expected |= {f'TDPetSpecies{s:02d}Q{q}' for s in range(1, 16) for q in range(1, 5)}
    require(len(ui['assets']) == 75 and {a['name'] for a in ui['assets']} == expected,
            'Elemental UI must include exact 15+60 quality-only combinations')
    for species in range(1, 16):
        for quality in range(1, 5):
            for count in range(1, 5):
                stem = f'TDPetSpecies{species:02d}Q{quality}N{count}'
                for path in (icon_path(stem), DISABLED_PREFIX + stem + '.blp'):
                    require(not artifact.has(path), 'Obsolete count UI still packaged: ' + path)
    for entry in ui['assets']:
        pixels = {}
        for state in ('normal', 'disabled'):
            source = root / entry[state]; path = entry[state].removeprefix('imports/').replace('/', '\\')
            require(artifact.has(path), 'Missing elemental UI icon: ' + path)
            data = artifact.extract(path)
            require(data == source.read_bytes() and hashlib.sha256(data).hexdigest() == entry[state + 'Sha256'],
                    'Elemental UI icon differs from reviewed SHA: ' + path)
            pixels[state] = decode_icon_blp(data, path)
        require(all(r == g == b for r, g, b, _ in pixels['disabled']), 'Elemental DIS icon is not grayscale')
    print('PASS ELEMENTAL RESOURCES: 15 final MDX800 + 15 exact BLP atlases + 75 BTN/DIS pairs; source/MPQ SHA match')


def verify_pet_core(abilities, units):
    verify_capture_only(abilities, units)
    verify_function_book(abilities, units)
    for rawcode in ('Pdep', 'Pc04'):
        targets = set(field_value(abilities[rawcode][1], 'atar', 1).split(','))
        require({'organic', 'mechanical', 'structure'}.issubset(targets),
                f'{rawcode}: deployment must target organic and mechanical towers; '
                f'actual targets={sorted(targets)}')
    capture_targets = {'neutral', 'enemy', 'ground', 'air', 'organic',
                       'invulnerable', 'vulnerable'}
    for level in range(1, 62):
        require(set(field_value(abilities['Pcap'][1], 'atar', level).split(','))
                == capture_targets,
                f'Pcap level {level}: ordinary capture target filter changed')
    models = [r'Units\Human\Phoenix\Phoenix.mdl',
              r'Units\NightElf\FaerieDragon\FaerieDragon.mdl',
              r'Units\NightElf\Wisp\Wisp.mdl']
    for species, model in enumerate(models, 1):
        display = units[f'pd0{species}']
        visual = units[f'pv0{species}']
        require(display['umdl'] == model and visual['umdl'] == model,
                f'Species {species}: incorrect dynamic model')
        require('Aloc' not in display['uabi'].split(','), 'Display must be selectable')
        require('Aloc' in visual['uabi'].split(','), 'Decoration must be non-selectable')
        require(display.get('ubdg') == 1 and display.get('uaen') == 0,
                'Display must be a stationary non-attacking building')
        require({f'Pc0{cmd}' for cmd in range(8)}.issubset(display['uabi'].split(',')),
                'Display misses native collection commands')
        for wave in range(1, 33):
            wild = units[f'p{wave:02X}{species}']
            require(wild['umdl'] == model and wild.get('uaen') == 0,
                    'Wild must use distinctive model and never attack')
            require(wild.get('ubba') == 0, 'Wild must have zero normal bounty')
    require(field_value(abilities['Pcap'][1], 'alev') == 61,
            'Capture inventory tooltip levels must cover 0..60')
    for rawcode, levels in [('Pbat', 512), ('Pbsp', 150), ('Pbar', 8)]:
        require(field_value(abilities[rawcode][1], 'alev') == levels,
                f'{rawcode}: incorrect synchronized level count')
    check_ability(abilities, 'Pbat', 'AIat', 512, 'Iatt', 0, lambda level: level * 5)
    check_ability(abilities, 'Pbsp', 'AIsx', 150, 'Isx1', 2, lambda level: level / 100.0)
    check_ability(abilities, 'Pbar', 'AId1', 8, 'Idef', 0, lambda level: -level)
    print('PASS PET CORE OBJECTS: 96 wild, 3 selectable displays, 3 decorations; '
          '516 passive bright/gray/empty skill variants, globally unique Channel orders; '
          'single A119 function book and main-bar Gupg/ordinary capture, capture-only wild descriptions, '
          'no Phnt/Pmas/Pfor ghost/attachment and 0..60 capture inventory levels.')

# Current manager contract. The older eight-button/dialog helpers above are
# retained only for historical mutation fixtures; main never calls them.
MANAGER_COMMANDS = {
    'Pc00': (0, 0, 'I', 0, 'TDPetCollection'),
    'Pc01': (1, 0, 'A', 0, 'TDPetPrevious'),
    'Pc02': (2, 0, 'D', 0, 'TDPetNext'),
    'Pc03': (3, 0, 'R', 0, 'TDPetReturnBuilder'),
    'Pc04': (0, 2, 'E', 1, 'TDPetDeploy'),
    'Pc05': (1, 2, 'Q', 0, 'TDPetRecall'),
    'Pc06': (2, 2, 'C', 0, 'TDPetCultivate'),
    'Pc07': (3, 2, 'W', 0, 'TDPetInfo'),
    'Pm00': (2, 2, 'C', 0, 'TDPetNext'),
    'Pm01': (3, 2, 'R', 0, 'TDPetReturnBuilder'),
    'Pm02': (0, 0, 'Q', 0, 'TDPetCultivate'),
    'Pm03': (1, 0, 'W', 0, 'TDPetCultivate'),
    'Pm04': (2, 0, 'E', 0, 'TDPetCultivate'),
    'Pm05': (3, 0, 'T', 0, 'TDPetCultivate'),
    'Pm06': (0, 2, 'O', 0, 'TDPetEmptySlot'),
    'Pm07': (3, 2, 'W', 0, 'TDPetRelease'),
    'Pm08': (2, 2, 'C', 0, 'TDPetInfo'),
    'Pm09': (0, 1, 'Q', 0, 'TDPetKeepOld'),
    'Pm0A': (3, 1, 'E', 0, 'TDPetUseNew'),
    'Pm0B': (0, 2, 'Y', 0, 'TDPetRelease'),
    'Pm0C': (1, 2, 'N', 0, 'TDPetKeep'),
    'Pm0D': (0, 2, 'W', 0, 'TDPetCultivate'),
    'Pm0E': (3, 2, 'R', 0, 'TDPetInfo'),
    'Pm0F': (1, 2, 'L', 0, 'TDPetCultivate'),
    'Pm10': (0, 0, 'Q', 0, 'TDPetCultivate'),
    'Pm11': (1, 0, 'W', 0, 'TDPetCultivate'),
    'Pm12': (2, 0, 'E', 0, 'TDPetCultivate'),
    'Pm13': (3, 0, 'T', 0, 'TDPetCultivate'),
    'Pm14': (3, 2, 'R', 0, 'TDPetInfo'),
    'Pm15': (0, 2, 'N', 0, 'TDPetNext'),
    'Pm16': (1, 2, 'P', 0, 'TDPetPrevious'),
    'Pm17': (0, 1, 'Q', 0, 'TDPetKeepOld'),
    'Pm18': (3, 1, 'E', 0, 'TDPetUseNew'),
}
PAGE_ACTIONS = {
    0: list(range(100, 110)) + [8, 9],
    1: list(range(7)) + [15],
    2: [10, 11, 12, 13, 14, 16, 9, 23],
    3: [17, 18, 21, 22],
    4: [19, 20, 9],
    5: [24, 25, 26, 27, 28],
    6: list(range(200, 208)) + [29, 30, 28],
    7: [31, 32, 22],
}
LIST_KEYS = 'QWETASDFZX'


def manager_rawcode(action):
    return f'Pc{action:02X}' if action < 8 else f'Pm{action - 8:02X}'


def expected_action_cell(mode, action):
    if action not in PAGE_ACTIONS.get(mode, []):
        return -1
    if mode == 0:
        return action - 100 if action >= 100 else action + 2
    if mode == 6 and action >= 200:
        return action - 200
    rawcode = manager_rawcode(action)
    x, y = MANAGER_COMMANDS[rawcode][:2]
    return y * 4 + x


def verify_manager_commands(abilities):
    for rawcode, (x, y, key, target, stem) in MANAGER_COMMANDS.items():
        require(rawcode in abilities, f'Missing manager command {rawcode}')
        parent, fields = abilities[rawcode]
        require(parent == 'ANcl', f'{rawcode}: manager command must inherit Channel')
        require(field_value(fields, 'alev') == 1, f'{rawcode}: expected one command level')
        require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (x, y),
                f'{rawcode}: manager cell changed')
        require(field_value(fields, 'ahky') == key, f'{rawcode}: manager hotkey changed')
        require(field_value(fields, 'Ncl2', 1) == target, f'{rawcode}: manager target changed')
        for field in ('aart', 'arar'):
            require(field_value(fields, field) == icon_path(stem), f'{rawcode}: {field} icon path mismatch')
    for mode, actions in PAGE_ACTIONS.items():
        cells, keys = set(), set()
        for action in actions:
            if action >= 200:
                cell, key = action - 200, LIST_KEYS[action - 200]
            elif action >= 100:
                cell, key = action - 100, LIST_KEYS[action - 100]
            else:
                x, y, key = MANAGER_COMMANDS[manager_rawcode(action)][:3]
                cell = y * 4 + x
            require(cell not in cells, f'Manager mode {mode}: overlapping cell {cell}')
            require(key not in keys, f'Manager mode {mode}: duplicate hotkey {key}')
            cells.add(cell)
            keys.add(key)
        skill_cells = {4, 5, 6, 7} if mode in (1, 2) else {0, 1, 2, 3} if mode in (3, 7) else set()
        require(not cells & skill_cells, f'Manager mode {mode}: passive skill overlap')
    verify_cultivation_command(abilities, current_manager=True)
    require(field_value(abilities['Pm09'][1], 'anam') == '保留原技能', 'Keep choice must name the original skill')
    require(field_value(abilities['Pm0A'][1], 'anam') == '换成新技能', 'Adopt choice must name the new skill')
    verify_global_channel_orders(abilities)
    require(unique_channel_order_count(abilities) <= 335, "Global unique Channel orders exceed the native order pool")


def verify_directed_objects(abilities):
    green = [*range(4), *range(5, 9), 11, 12, *range(16, 19), 20, 24, 28, 32, 36, *range(39, 49)]
    expected = {f'Pn{skill:02X}' for skill in green}
    actual = {raw for raw in abilities if re.fullmatch(r'Pn[0-9A-F]{2}', raw)}
    require(actual == expected and len(actual) == 28, 'Directed choices require exactly 28 fixed-position identities')
    require(not any(re.fullmatch(r'N[0-9A-F]{3}', raw) for raw in abilities), 'Unapproved skill x8 choice-variant library')
    orders = {}
    for skill in green:
        raw = f'Pn{skill:02X}'
        parent, fields = abilities[raw]
        cell = skill if skill < 4 else skill-5 if 5 <= skill <= 8 else skill-12 if 16 <= skill <= 18 else (skill-32)%8 if skill >= 39 else skill-10 if skill in (11, 12) else 0
        require(parent == 'ANcl' and field_value(fields, 'alev') == 1, raw + ': one-level green Channel expected')
        require(all(level in (0, 1) for _, level, _ in fields), raw + ': residual second-level fields are forbidden')
        for name in ('Ncl1', 'Ncl2', 'Ncl3', 'Ncl4', 'Ncl5', 'Ncl6', 'amcs', 'acdn', 'aran'):
            column = int(name[-1]) if name.startswith('Ncl') else 0
            require([(level, data) for field, level, data in fields if field == name] == [(1, column)], raw + ': Channel field must exist exactly at level one: ' + name)
        require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (cell%4, cell//4), raw + ': fixed directory position changed')
        require(field_value(fields, 'ahky') == LIST_KEYS[cell] and field_value(fields, 'Ncl2', 1) == 0, raw + ': choice key/target changed')
        require('3洗练石' in field_value(fields, 'aub1', 1) and QUALITY_NAMES[1] in field_value(fields, 'atp1', 1), raw + ': cost/green tooltip missing')
        order = field_value(fields, 'Ncl6', 1)
        if cell in orders:
            require(orders[cell] == order, 'Directed identity allocated an extra per-variant order')
        orders[cell] = order
    require(len(orders) == len(set(orders.values())) == 8, 'Eight fixed choice cells require eight distinct orders')


def verify_manager_list(abilities):
    species = manager_species(abilities=abilities)
    quality_only = len(species) == 15
    variants = 1 + (4 if quality_only else 16) * len(species)
    for cell in range(10):
        for variant in range(variants):
            rawcode = f'L{cell * 241 + (0 if variant == 0 else 1 + (variant - 1) * 4):03X}' if quality_only else f'L{cell * variants + variant:03X}'
            require(rawcode in abilities, f'Missing fixed collection state {rawcode}')
            parent, fields = abilities[rawcode]
            require(parent == 'ANcl' and field_value(fields, 'alev') == 2,
                    f'{rawcode}: expected two-level native list Channel')
            require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (cell % 4, cell // 4),
                    f'{rawcode}: incorrect physical list cell')
            require(field_value(fields, 'ahky') == LIST_KEYS[cell], f'{rawcode}: wrong list hotkey')
            for flag in ('aher', 'aite'):
                require(field_value(fields, flag) == 0, f'{rawcode}: list must be a non-item unit ability')
            stem = 'TDPetEmptySlot' if variant == 0 else (species[(variant - 1) // 4][1] + f'Q{(variant - 1) % 4 + 1}' if quality_only else '')
            if not quality_only and variant:
                stem = species[(variant - 1) // 16][1] + f'Q{((variant - 1) % 16) // 4 + 1}N{(variant - 1) % 4 + 1}'
            for field in ('aart', 'arar'):
                require(field_value(fields, field) == icon_path(stem), f'{rawcode}: quality/empty icon mismatch')
            for level in (1, 2):
                for key, expected in (('Ncl1', 0.0), ('Ncl3', 1), ('Ncl4', 0.0), ('Ncl5', 0), ('amcs', 0), ('acdn', 0.0)):
                    require(field_value(fields, key, level) == expected, f'{rawcode}: unsafe list field {key} level {level}')
                number = f'{(level - 1) * 10 + cell + 1:02d}'
                label, description = field_value(fields, 'atp1', level), field_value(fields, 'aub1', level)
                require(label.startswith(number + ' · ') and label.endswith(f'({LIST_KEYS[cell]})'),
                        f'{rawcode} level {level}: fixed number/hotkey tooltip mismatch')
                require(field_value(fields, 'Ncl2', level) == 0, f'{rawcode}: list must be no-target')
                if variant == 0:
                    require('空位' in label and '捕获' in description,
                            f'{rawcode}: empty fixed slot must be explained')
                else:
                    quality = (variant - 1) % 4 if quality_only else ((variant - 1) % 16) // 4
                    require(QUALITY_NAMES[quality] in label,
                            f'{rawcode}: owned quality label missing')
                    if quality_only:
                        require(description == '查看技能数量、技能详情、上阵或培养。', f'{rawcode}: list detail hint mismatch')
                    else:
                        require(str((variant - 1) % 4 + 1) + '个技能' in description, f'{rawcode}: historical owned skill count missing')
    expected_ids = ({f'L{cell * 241 + offset:03X}' for cell in range(10) for offset in (0, *range(1, 241, 4))}
                    if quality_only else {f'L{i:03X}' for i in range(10 * variants)})
    require({raw for raw in abilities if re.fullmatch(r'L[0-9A-F]{3}', raw)} == expected_ids,
            'Expected exact complete collection Channel family')
    require(not any(re.fullmatch(r'Pl[0-9A-F]{2}', raw) for raw in abilities), 'Retired Pl list objects remain')


def verify_phase_one_preview(abilities):
    n = phase_one_catalog(); count = n['TD_PET_SKILL_COUNT']; expected = set()
    for position, skill in itertools.product(range(2), range(count)):
        if not n['tdPetSkillDefined'](skill):
            continue
        rawcode = f'Ps{position * count + skill:02X}'; expected.add(rawcode)
        require(rawcode in abilities, 'Missing implemented preview ' + rawcode)
        parent, fields = abilities[rawcode]
        require(parent == 'AOcr' and field_value(fields, 'alev') == 4, rawcode + ': comparison quality levels')
        require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (0 if position == 0 else 3, 0), rawcode + ': comparison position')
        require(field_value(fields, 'aart') == n['tdPetSkillIconPath'](skill, False), rawcode + ': comparison icon')
        require(not any(key == 'Ncl6' for key, _, _ in fields), rawcode + ': comparison Channel order')
        for field in ('aher', 'aite', 'achd'):
            require(field_value(fields, field) == 0, rawcode + ': unsafe comparison flag')
        require(field_value(fields, 'areq') == '', rawcode + ': comparison requirements')
        for quality in range(1, 5):
            label = ('旧：' if position == 0 else '新：') + QUALITY_NAMES[quality - 1] + ' ' + n['tdPetSkillNameById'](skill)
            require(field_value(fields, 'atp1', quality) == label, rawcode + ': preview identity')
            require(field_value(fields, 'Ocr1', quality) == 0.0 and field_value(fields, 'Ocr2', quality) == 1.0, rawcode + ': preview combat effect')
    require({raw for raw in abilities if re.fullmatch(r'Ps[0-9A-F]{2}', raw)} == expected, 'Preview must expose exactly implemented definitions')


def verify_manager_preview(abilities):
    phase_one = is_phase_one_ui(abilities)
    if phase_one:
        verify_phase_one_preview(abilities)
    for position, skill in itertools.product(range(2), range(16)):
        if phase_one:
            continue
        rawcode = f'Ps{position * 16 + skill:02X}'
        require(rawcode in abilities, f'Missing comparison passive {rawcode}')
        parent, fields = abilities[rawcode]
        require(parent == 'AOcr' and field_value(fields, 'alev') == 4,
                f'{rawcode}: expected four-quality passive comparison')
        require(not any(key == 'Ncl6' for key, _, _ in fields), f'{rawcode}: comparison allocates Channel order')
        require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (0 if position == 0 else 3, 0),
                f'{rawcode}: wrong comparison cell')
        require(field_value(fields, 'aart') == NORMAL_PREFIX + SKILL_ICONS[skill] + '.blp',
                f'{rawcode}: wrong comparison skill icon')
        for field in ('aher', 'aite', 'achd'):
            require(field_value(fields, field) == 0, f'{rawcode}: unsafe comparison flag {field}')
        require(field_value(fields, 'areq') == '', f'{rawcode}: comparison has requirements')
        for quality in range(1, 5):
            label = ('旧：' if position == 0 else '新：') + QUALITY_NAMES[quality - 1] + ' ' + SKILL_NAMES[skill]
            require(field_value(fields, 'atp1', quality) == label, f'{rawcode}: comparison identity mismatch')
            require(field_value(fields, 'Ocr1', quality) == 0.0 and field_value(fields, 'Ocr2', quality) == 1.0,
                    f'{rawcode}: comparison must have zero combat effect')
            description = field_value(fields, 'aub1', quality)
            require('摘要' not in description, f'{rawcode}: comparison must not depend on screen notes')
    require(phase_one or len([raw for raw in abilities if re.fullmatch(r'Ps[0-9A-F]{2}', raw)]) == 32,
            'Expected exactly 32 comparison passives')
    for position in range(2):
        rawcode = f'Pa{position:02X}'
        require(rawcode in abilities, f'Missing static preview arrow {rawcode}')
        parent, fields = abilities[rawcode]
        require(parent == 'AOcr' and field_value(fields, 'alev') == 1, f'{rawcode}: arrow must be passive')
        require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (position + 1, 0), f'{rawcode}: arrow cell changed')
        require(field_value(fields, 'aart') == icon_path('TDPetNext'), f'{rawcode}: arrow artwork changed')
        require(not any(key == 'Ncl6' for key, _, _ in fields), f'{rawcode}: arrow allocates order')
        require(field_value(fields, 'Ocr1', 1) == 0.0 and field_value(fields, 'Ocr2', 1) == 1.0, f'{rawcode}: arrow combat effect')
        for key in ('aher', 'aite', 'achd'):
            require(field_value(fields, key) == 0, f'{rawcode}: unsafe arrow flag')
        require(field_value(fields, 'areq') == '', f'{rawcode}: arrow requirements')
    require({raw for raw in abilities if re.fullmatch(r'Pa[0-9A-F]{2}', raw)} == {'Pa00', 'Pa01'}, 'Unexpected preview arrow object')


def verify_manager_units(units):
    species_models = manager_species(units=units)
    expected = {'pd00': (species_models[2][0], 'TDPetCollection')}
    for species, (model, stem) in enumerate(species_models):
        for quality in range(1, 5):
            expected[f'pd{species * 4 + quality:02X}'] = (model, stem + f'Q{quality}')
    actual = {raw for raw in units if re.fullmatch(r'pd[0-9A-F]{2}', raw)}
    require(actual == set(expected), 'Expected exactly list + complete species/quality prototypes')
    for rawcode, (model, stem) in expected.items():
        fields = units[rawcode]
        require(fields.get('umdl') == model, f'{rawcode}: display model mismatch')
        for field in ('uico', 'ussi'):
            require(fields.get(field) == icon_path(stem), f'{rawcode}: display quality icon mismatch')
        require(fields.get('uabi', '').split(',') == ['Avul'],
                f'{rawcode}: base display must contain only Avul; runtime owns page mounting')
        require(fields.get('ubdg') == 1 and fields.get('uaen') == 0 and fields.get('umvs') == 0 and fields.get('ufoo') == 0,
                f'{rawcode}: display must be stationary/noncombat/zero-food building')
        for field in ('ubui', 'utra', 'uupt', 'upat'):
            require(fields.get(field, '') == '', f'{rawcode}: display exposes native build/train/upgrade/pathing')


def verify_manager_farmer(abilities, units):
    verify_farmer_grid(abilities, units)
    candidates = [(raw, fields) for raw, fields in units.items()
                  if {'Pcap', 'Pcol'}.issubset(fields.get('uabi', '').split(','))]
    require(len(candidates) == 1, 'Expected one farmer with capture and collection entrances')
    rawcode, farmer = candidates[0]
    require(field_value(abilities['Pcap'][1], 'ahky') == 'Q', 'Farmer Q capture must remain')
    require(field_value(abilities['Pcol'][1], 'ahky') == 'W', 'Farmer W collection must remain')
    require('20' in field_value(abilities['Pcol'][1], 'aub1', 1), 'Collection entrance must advertise twenty slots')
    require('Pdep' not in farmer.get('uabi', '').split(','), 'Tower detail must not remain on farmer')
    require('Pmas' not in abilities and 'Pfor' not in abilities,
            'Predecessor master/forge removal must be preserved on final integrated map')
    ghost = re.compile(r'(?<![A-Za-z0-9_])(?:Pmas|Pfor)(?![A-Za-z0-9_])')
    for object_id, (_, fields) in abilities.items():
        require(not any(isinstance(value, str) and ghost.search(value)
                        for _, value in fields.values()), f'{object_id}: removed master/forge reference remains')
    for object_id, fields in units.items():
        require(not any(isinstance(value, str) and ghost.search(value) for value in fields.values()),
                f'{object_id}: removed master/forge unit attachment remains')
    require('TD_PET_DEPLOY_LIMIT' not in (ROOT / 'wurst/pets/TDPetData.wurst').read_text(),
            'Removed lane-wide three-spirit cap must stay absent')
    return rawcode


def verify_manager_jass(script):
    # JASS vardecl permits local arrays. Syntax/allocator compatibility is checked
    # by the locked LegacyJass runner; local-array storage is not a newer native.
    constants = {name: int(number) for name, number in re.findall(r'\bset (\w*TD_PET_\w+)\s*=\s*(-?\d+)\b', script)}
    helper = jass_function(script, 'tdPetActionCell')
    for mode in range(-1, 9):
        for action in range(-1, 210):
            actual = _run_scalar_helper(helper, (mode, action), constants)
            require(actual == expected_action_cell(mode, action),
                    f'Packaged page whitelist mode={mode} action={action}: {actual}')
    for name in ('onCommand', 'showCultivation', 'showReleaseConfirmation', 'tdPetRenderPage',
                 'tdPetCloseManager', 'onSelected', 'onDeselected'):
        body = jass_function(script, name).group(1)
        require(not any(native in body for native in ('DialogDisplay', 'DialogCreate', 'Blz', 'Dz')),
                f'{name}: non-native/pause-based manager UI is forbidden')
    bridge = jass_function(script, 'onCommand').group(1)
    for text in ('TDPetUIView_tdPetDisplays', 'tdPetDisplayOwners', 'admitCommand',
                 'GetUnitAbilityLevel', 'tdPetResolveRerollVersion'):
        require(text in bridge, f'Packaged command bridge missing {text}')
    render = jass_function(script, 'tdPetRenderPage').group(1)
    require('addPermanentAbility' in render and 'tdPetDisplayOwners' in render and 'GetLocalPlayer' in render,
            'Renderer must mount synchronized page before local selection')
    invalidate = jass_function(script, 'tdPetRefreshDisplay').group(1)
    require('createUnit' not in invalidate and 'tdPetRenderPage' not in invalidate and 'SelectUnit' not in invalidate,
            'Polling must only invalidate, never rebuild or select')
    farmer = jass_function(script, 'onDeploy').group(1)
    require('tdPetDeploy(' not in farmer, 'Farmer bypasses manager binding session')
    require(re.search(r'\bset TDPetData_TD_PET_COLLECTION_LIMIT\s*=\s*20\b', script),
            'Packaged collection capacity must be twenty')
    require('TDPetData_TD_PET_DEPLOY_LIMIT' not in script, 'Packaged lane-wide cap remains')


def verify_manager_core(abilities, units):
    targets = {'neutral', 'enemy', 'ground', 'air', 'organic', 'invulnerable', 'vulnerable'}
    require(field_value(abilities['Pcap'][1], 'alev') == 61, 'Capture must cover inventory 0..60')
    for level in range(1, 62):
        require(set(field_value(abilities['Pcap'][1], 'atar', level).split(',')) == targets,
                f'Pcap level {level}: capture target filter changed')
    deploy_targets = set(field_value(abilities['Pc04'][1], 'atar', 1).split(','))
    require({'organic', 'mechanical', 'structure'}.issubset(deploy_targets),
            'Manager binding must target organic/mechanical towers')
    for species, (model, _) in enumerate(manager_species(abilities, units), 1):
        visual = units[f'pv{species:02X}']
        require(visual.get('umdl') == model and 'Aloc' in visual.get('uabi', '').split(','),
                'Decorative spirit must retain species model and non-selectability')
        for wave in range(1, 33):
            rawcode = f'p{wave:02X}{species:X}'
            wild = units[rawcode]
            require(wild.get('umdl') == model and wild.get('uaen') == 0 and wild.get('ubba') == 0,
                    f'{rawcode}: wild model/noncombat/zero bounty changed')
    check_ability(abilities, 'Pbat', 'AIat', 512, 'Iatt', 0, lambda level: level * 5)
    check_ability(abilities, 'Pbsp', 'AIsx', 150, 'Isx1', 2, lambda level: level / 100.0)
    check_ability(abilities, 'Pbar', 'AId1', 10 if len(manager_species(abilities, units)) == 15 else 8, 'Idef', 0, lambda level: -level)


def verify_manager_objects(abilities, units):
    verify_manager_commands(abilities)
    verify_manager_list(abilities)
    verify_directed_objects(abilities)
    verify_manager_preview(abilities)
    verify_manager_units(units)
    # Require exact legal slots and all qualities; preserve frozen predecessor support.
    verify_slot_icons(abilities, current_manager=True)
    require(not set(abilities) & {raw for raw in units if raw.startswith('pd')},
            'Manager ability and unit rawcodes collide')
    verify_no_hunt_objects(abilities, units)
    species_count = len(manager_species(abilities, units))
    variants = 1 + (4 if species_count == 15 else 16) * species_count
    require(len(MANAGER_COMMANDS) + 10 * variants == (643 if species_count == 15 else 523), 'Manager Channel object budget changed')


def verify_global_rawcode_uniqueness(artifact):
    # Strict decoder rejects duplicate objects/fields before dictionaries can
    # hide them; identities are checked across every actual object table.
    from VerifySemanticIconArtifact import parse_objects
    files = {'war3map.w3u': False, 'war3map.w3t': False, 'war3map.w3b': False,
             'war3map.w3a': True, 'war3map.w3h': False,
             'war3map.w3q': True, 'war3map.w3d': True}
    owners = {}
    for path, extended in files.items():
        if not artifact.has(path):
            continue
        for rawcode in parse_objects(artifact.extract(path), extended):
            require(rawcode not in owners, f'Global rawcode {rawcode} collides: {owners.get(rawcode)} and {path}')
            owners[rawcode] = path
    require(bool(owners), 'No actual object tables found')
    print(f'PASS GLOBAL RAWCODES: {len(owners)} unique strict-decoded object identities')


def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    verify_global_rawcode_uniqueness(artifact)
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    units = unit_objects(artifact.extract('war3map.w3u'))
    verify_no_removed_raw_objects(artifact.extract('war3map.w3u'), False, 'unit')
    if artifact.has('war3map.w3t'):
        verify_no_removed_raw_objects(artifact.extract('war3map.w3t'), False, 'item')
        verify_no_hunt_objects(abilities, units, unit_objects(artifact.extract('war3map.w3t')))
    farmer = verify_manager_farmer(abilities, units)
    verify_manager_objects(abilities, units)
    verify_manager_core(abilities, units)
    # Wild object layout and skill rules remain independent of collection UI.
    verify_capture_only(abilities, units, current_manager=True)
    script = artifact.extract('war3map.j').decode('utf-8')
    verify_manager_jass(script)
    verify_skill_fit_abilities(script)
    verify_skill_allowed(script)
    verify_lane_enemy_guards(script)
    verify_imported_icons(artifact)
    if len(manager_species(abilities, units)) == 15:
        verify_elemental_resources(artifact)
    require(not artifact.has(r'Units\CommandFunc.txt'), 'Global CommandFunc override is forbidden')
    species_count = len(manager_species(abilities, units))
    channels = len(MANAGER_COMMANDS) + 28 + 10 * (1 + (4 if species_count == 15 else 16) * species_count)
    passives = verify_phase_one_slots(abilities) if is_phase_one_ui(abilities) else 550
    prototypes = 1 + species_count * 4
    print(f'PASS PET MANAGER: {farmer}; 20 fixed slots/two pages; {channels} Channels + {passives} slot displays; '
          f'{prototypes} runtime-mounted display prototypes; all page cells/hotkeys/targets; '
          'native synchronized session bridge; packaged BTN/DIS assets match source.')
    print('NOT TESTED: live rendering/selection/queued network events, actual placement, performance or skill effects.')


if __name__ == '__main__':
    main()
