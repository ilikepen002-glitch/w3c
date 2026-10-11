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
                                      verify_no_hunt_objects)

ROOT = Path(__file__).resolve().parents[1]
NORMAL_PREFIX = "ReplaceableTextures\\CommandButtons\\"
DISABLED_PREFIX = "ReplaceableTextures\\CommandButtonsDisabled\\DIS"
IMPORTED_PREFIX = "war3mapImported\\BTN"
ICON_STEMS = (
    'TDPetMenuTools', 'TDPetCollection', 'TDPetPrevious', 'TDPetNext',
    'TDPetReturnBuilder', 'TDPetDeploy', 'TDPetRecall', 'TDPetCultivate',
    'TDPetInfo', 'TDPetEmptySlot', 'TDPetFlamePhoenix',
    'TDPetStormFaerieDragon', 'TDPetGhostWisp',
)
EXPECTED = {
    'Geqb': (3, 0, 'C', 'Aspb'),
    'Prpr': (1, 1, 'R', 'Ahrp'),
    'A108': (2, 1, 'F', 'AEbl'),
    'A109': (3, 1, 'G', 'ANcl'),
    'Pcap': (1, 2, 'Q', 'ANcl'),
    'Pcol': (2, 2, 'W', 'ANcl'),
    'Pdep': (3, 2, 'E', 'ANcl'),
}
# Observed legacy native move/stop/hold/patrol/build cells stay unchanged.
NATIVE_CELLS = {(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)}
FARMER_ICONS = {'Geqb': 'TDPetMenuTools', 'Pcol': 'TDPetCollection', 'Pdep': 'TDPetDeploy'}
# x, y, hotkey, Channel target type, semantic icon, original base order.
COLLECTION_COMMANDS = {
    'Pc00': (0, 0, 'I', 0, 'TDPetCollection', 'weboff'),
    'Pc01': (1, 0, 'A', 0, 'TDPetPrevious', 'web'),
    'Pc02': (2, 0, 'D', 0, 'TDPetNext', 'attributemodskill'),
    'Pc03': (3, 0, 'R', 0, 'TDPetReturnBuilder', 'auraunholy'),
    'Pc04': (0, 2, 'E', 1, 'TDPetDeploy', 'auravampiric'),
    'Pc05': (1, 2, 'Q', 0, 'TDPetRecall', 'autodispel'),
    'Pc06': (2, 2, 'C', 0, 'TDPetCultivate', 'autodispeloff'),
    'Pc07': (3, 2, 'W', 0, 'TDPetInfo', 'autodispelon'),
}
SPECIES = (
    (r'Units\Human\Phoenix\Phoenix.mdl', 'TDPetFlamePhoenix'),
    (r'Units\NightElf\FaerieDragon\FaerieDragon.mdl', 'TDPetStormFaerieDragon'),
    (r'Units\NightElf\Wisp\Wisp.mdl', 'TDPetGhostWisp'),
)
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
    occupied = {cell: 'native command' for cell in NATIVE_CELLS}
    for rawcode in EXPECTED:
        require(rawcode in abilities, f'Missing farmer command {rawcode}')
        fields = abilities[rawcode][1]
        cell = (field_value(fields, 'abpx'), field_value(fields, 'abpy'))
        require(cell not in occupied,
                f'{rawcode}: farmer cell overlaps {occupied.get(cell)} at {cell}')
        occupied[cell] = rawcode
    require(set(occupied) == {(x, y) for x in range(4) for y in range(3)},
            'Farmer command grid must fill exactly twelve distinct cells')
    for rawcode, (x, y, hotkey, parent) in EXPECTED.items():
        actual_parent, fields = abilities[rawcode]
        require(actual_parent == parent, f'{rawcode}: wrong parent {actual_parent}')
        actual = (field_value(fields, 'abpx'), field_value(fields, 'abpy'))
        require(actual == (x, y), f'{rawcode}: wrong farmer cell {actual}, expected {(x, y)}')
        require(field_value(fields, 'ahky') == hotkey, f'{rawcode}: wrong farmer hotkey')
    candidates = [(uid, fields) for uid, fields in units.items()
                  if set(EXPECTED).issubset(fields.get('uabi', '').split(','))]
    require(len(candidates) == 1, 'Expected exactly one farmer with all seven commands')
    uid, farmer = candidates[0]
    require(farmer['uabi'].split(',') == ['AHbu', 'Prpr', 'A108', 'A109', 'A117',
                                        'Geqb', 'Pcap', 'Pcol', 'Pdep'],
            f'{uid}: farmer ability attachment/order changed')
    require('Amov' not in abilities, 'Native Amov must not be modified or disabled')
    for rawcode, stem in FARMER_ICONS.items():
        fields = abilities[rawcode][1]
        require(field_value(fields, 'aart') == icon_path(stem), f'{rawcode}: farmer icon path mismatch')
        if rawcode != 'Geqb':
            require(field_value(fields, 'arar') == icon_path(stem), f'{rawcode}: farmer research icon path mismatch')
    return uid


def verify_collection_commands(abilities):
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
    for rawcode, (x, y, hotkey, target, stem, order) in COLLECTION_COMMANDS.items():
        fields = abilities[rawcode][1]
        require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (x, y),
                f'{rawcode}: collection command cell changed')
        require(field_value(fields, 'ahky') == hotkey, f'{rawcode}: collection command hotkey changed')
        require(field_value(fields, 'Ncl2', 1) == target, f'{rawcode}: collection target type changed')
        require(field_value(fields, 'Ncl6', 1) == order, f'{rawcode}: base order changed')
        for field in ('aart', 'arar'):
            require(field_value(fields, field) == icon_path(stem), f'{rawcode}: {field} icon path mismatch')
    verify_global_channel_orders(abilities)
    verify_cultivation_command(abilities)


def verify_cultivation_command(abilities):
    fields = abilities['Pc06'][1]
    name = '洗练 / 开栏 / 释放(C)'
    require(field_value(fields, 'anam') == name,
            'Pc06: cultivation name must explicitly say 洗练 / 开栏 / 释放(C)')
    require(field_value(fields, 'atp1', 1) == name,
            'Pc06: cultivation tooltip must explicitly say 洗练 / 开栏 / 释放(C)')
    description = field_value(fields, 'aub1', 1)
    require(all(word in description for word in ('洗练', '开栏', '释放')),
            'Pc06: cultivation description must explain reroll, slot opening and release')
    for field in ('ahky', 'arhk', 'auhk'):
        require(field_value(fields, field) == 'C', f'Pc06: {field} cultivation hotkey must remain C')
    require((field_value(fields, 'abpx'), field_value(fields, 'abpy')) == (2, 2),
            'Pc06: cultivation command must remain at 2,2')


def verify_capture_only(abilities, units):
    verify_no_hunt_objects(abilities, units)
    for rawcode in ('Pcap', 'Pmas', 'Pcol'):
        fields = abilities[rawcode][1]
        for (field, level, _), (_, text) in fields.items():
            if field in ('anam', 'atp1', 'aub1'):
                require('猎杀' not in text,
                        f'{rawcode} level {level}: obsolete wild-hunt text remains')
    for wave in range(1, 33):
        for species in range(1, 4):
            rawcode = f'p{wave:02X}{species}'
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
    """Evaluate only the integer/boolean subset used by the pure pet helpers."""
    require(not (re.search(r'\band\b', expression) and re.search(r'\bor\b', expression)),
            f'Ambiguous packaged scalar boolean precedence: {expression}')
    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, bool):
            return node.value
        if isinstance(node, ast.Name) and node.id in variables:
            return variables[node.id]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            require(functions is not None and node.func.id in functions and not node.keywords,
                    f'Unsupported packaged scalar call: {node.func.id}')
            return functions[node.func.id](*(visit(argument) for argument in node.args))
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            left, right = visit(node.left), visit(node.right)
            return (left + right if isinstance(node.op, ast.Add) else
                    left - right if isinstance(node.op, ast.Sub) else left * right)
        if isinstance(node, ast.BoolOp):
            values = [bool(visit(value)) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
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
                       result_field=None, on_assignment=None):
    header = match.group(0).splitlines()[0]
    parameters = re.findall(r'(?:integer|boolean|unit|player) (\w+)', header)
    require(len(parameters) == len(arguments), 'Packaged scalar helper argument count changed')
    variables = {'true': True, 'false': False, 'null': None, **(constants or {}),
                 **dict(zip(parameters, arguments))}
    active, branches = True, []
    for source_line in match.group(1).splitlines():
        line = source_line.split('//', 1)[0].strip()
        if not line:
            continue
        if line.startswith('local '):
            declaration = re.fullmatch(r'local (integer|boolean|unit|player) (\w+)(?: = (.*))?', line)
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
                return _integer_expression(line[7:], variables, functions)
        elif line == 'return':
            if active:
                require(result_field is not None, 'Unexpected void return in scalar helper')
                return variables[result_field]
        elif line.startswith('set '):
            variable, expression = line[4:].split('=', 1)
            if active:
                variable = variable.strip()
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
    require(re.search(r'dialog_addButton_1\([^\n]*tdPetDialogHotkey\('
                      r'[^\n]*TDPetDialogSession_mode[^\n]*TDPetUI_sessions', bridge) is not None,
            'Pet UI addButton must pass session-mode hotkey to native dialog overload')
    native = jass_function(script, 'dialog_addButton_1').group(0)
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
    for skill in range(16):
        require(functions['tdPetSkillIsNumeric'](skill) is (skill <= 3),
                f'Packaged numeric skill classification changed for {skill}')
        require(functions['tdPetSkillIsActive'](skill) is (skill >= 11),
                f'Packaged active skill classification changed for {skill}')
        require(functions['tdPetSkillIsUniversal'](skill) is (skill >= 4 and skill not in (9, 10)),
                f'Packaged universal skill classification changed for {skill}')
        for mask in [0] + [1 << index for index in range(16)]:
            require(functions['bitset_get'](mask, skill) is bool(mask & (1 << skill)),
                    f'Packaged bitset duplicate check changed for skill={skill} mask={mask}')
    return functions


def verify_skill_allowed(script):
    """Enumerate 2,176 compiled skill/slot/active/used-mask combinations."""
    helper, functions = jass_function(script, 'tdPetSkillAllowed'), _pet_rule_functions(script)
    for skill, slot, has_active, mask in itertools.product(
            range(16), range(4), (False, True), [0] + [1 << index for index in range(16)]):
        expected = (not bool(mask & (1 << skill)) and
                    (skill <= 3 if slot == 0 else
                     skill >= 4 and (slot != 1 or skill not in (9, 10)) and
                     (not has_active or skill < 11)))
        actual = _run_scalar_helper(helper, (skill, slot, mask, has_active), functions=functions)
        require(actual is expected,
                f'Pet skill allowed skill={skill} slot={slot} active={has_active} mask={mask}: '
                f'got {actual}, expected {expected}')


def verify_lane_enemy_guards(script):
    """Enumerate 256 compiled enum states, including every guard with matching wave."""
    helper = jass_function(script, 'tdLaneEnemyCheckEnum')
    field = 'TDSpawn_tdLaneEnemyCheckFound'
    for wild, same_lane, alive, enemy_owner, nonnull, found, any_wave, same_wave in itertools.product(
            (False, True), repeat=8):
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
        qualifies = (not wild and same_lane and alive and enemy_owner and nonnull and
                     not found and (any_wave or same_wave))
        actual = _run_scalar_helper(helper, (), constants, functions, field,
                                    lambda name, value: assignments.append((name, value)))
        writes = [value for name, value in assignments if name == field]
        require(actual is (found or qualifies) and writes == ([True] if qualifies else []),
                f'Lane enemy guards wild={wild} lane={same_lane} alive={alive} owner={enemy_owner} '
                f'nonnull={nonnull} found={found} anywave={any_wave} matchingwave={same_wave}: '
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


def verify_slot_icons(abilities):
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
                require('空栏' in label and '没有此栏' in description and '开栏石' in description,
                        f'{rawcode}: empty slot explanation changed')
            elif variant >= 64:
                require('共鸣锁定' in label and '空栏' not in label,
                        f'{rawcode}: locked skill must retain specific identity')
                require('解锁' in description and '已抽技能' in description,
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
                    lock_prefix = f'已抽技能，尚未生效。完成本路第{4 if slot == 2 else 8}波解锁。|n'
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
    check_ability(abilities, 'Pbat', 'AIat', 512, 'Iatt', 0, lambda level: level)
    check_ability(abilities, 'Pbsp', 'AIsx', 150, 'Isx1', 2, lambda level: level / 100.0)
    check_ability(abilities, 'Pbar', 'AId1', 8, 'Idef', 0, lambda level: -level)
    print('PASS PET CORE OBJECTS: 96 wild, 3 selectable displays, 3 decorations; '
          '516 passive bright/gray/empty skill variants, globally unique Channel orders; '
          'five-command function menu/master/five-to-one, capture-only wild descriptions, '
          'no Phnt ghost/attachment and 0..60 capture inventory levels.')

def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    units = unit_objects(artifact.extract('war3map.w3u'))
    if artifact.has('war3map.w3t'):
        verify_no_hunt_objects(abilities, unit_objects(artifact.extract('war3map.w3t')))
    farmer = verify_farmer_grid(abilities, units)
    verify_collection_commands(abilities)
    verify_species_identity(units)
    verify_slot_icons(abilities)
    verify_pet_core(abilities, units)
    verify_dialog_hotkeys(artifact.extract('war3map.j').decode('utf-8'))
    verify_skill_fit_abilities(artifact.extract('war3map.j').decode('utf-8'))
    verify_skill_allowed(artifact.extract('war3map.j').decode('utf-8'))
    verify_lane_enemy_guards(artifact.extract('war3map.j').decode('utf-8'))
    verify_imported_icons(artifact)
    require(not artifact.has(r'Units\CommandFunc.txt'), 'Global CommandFunc override is forbidden')
    print(f'PASS PET UI: {farmer}; exact 12-cell farmer grid; eight distinct collection icons, '
          'unchanged cells/hotkeys, reallocated globally unique base orders; '
          'explicit cultivation/release command; three explicit species identities; '
          '516 exact bright/locked/empty variants; real native dialog numeric hotkeys; '
          '64 compiled skill/host capability combinations; '
          '2176 compiled skill admission and 256 lane-enemy guard combinations; '
          '26 packaged 64px BTN/DIS assets match source hashes.')
    print('NOT TESTED: native rendering/portrait/selection, actual command placement and live skill effects.')


if __name__ == '__main__':
    main()
