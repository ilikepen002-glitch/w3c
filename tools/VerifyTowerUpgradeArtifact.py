#!/usr/bin/env python3
"""Independent, pure checks of the 35-node tower upgrade contract.

Usage: python tools/VerifyTowerUpgradeArtifact.py map.w3x
All validation functions accept parsed objects so negative tests can deepcopy
and mutate them without rebuilding or modifying a map.
"""
import ast
import math
from pathlib import Path
import re
import sys

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects

FAMILIES = 'A O H D G'.split()
COMMON = ['A118', 'A133', 'A130']
HIDDEN = {'A103', 'A107', 'A110', 'A140', 'AeSL', 'A115', 'A118'}
BRANCH_ICONS = {
    'A': ('BTNSplitShot', 'BTNTrueshotAura'),
    'O': ('BTNBloodlust', 'BTNBladestorm'),
    'H': ('BTNShieldBash', 'BTNCommandAura'),
    'D': ('BTNPoisonDart', 'BTNVinesAura'),
    'G': ('BTNFrenzy', 'BTNCorpseExplosion'),
}
IDENTITIES = {
    'A': ('Archer', 'Units\\NightElf\\Archer\\Archer.mdx', 'HeroMoonPriestess', 'Units\\NightElf\\HeroMoonPriestess\\HeroMoonPriestess.mdx'),
    'O': ('Grunt', 'Units\\Orc\\Grunt\\grunt.mdx', 'HeroBlademaster', 'Units\\Orc\\HeroBladeMaster\\HeroBladeMaster.mdx'),
    'H': ('Footman', 'Units\\Human\\Footman\\Footman.mdx', 'HeroPaladin', 'Units\\Human\\HeroPaladin\\HeroPaladin.mdx'),
    'D': ('Dryad', 'Units\\NightElf\\Dryad\\Dryad.mdx', 'KeeperOfTheGrove', 'Units\\NightElf\\HeroKeeperOfTheGrove\\HeroKeeperoftheGrove.mdx'),
    'G': ('Ghoul', 'Units\\Undead\\Ghoul\\Ghoul.mdx', 'Abomination', 'Units\\Undead\\Abomination\\Abomination.mdx'),
}
RANGES = {
    'A': [735, 770, 805, 840, 875, 900, 1020],
    'O': [550, 580, 610, 640, 670, 670, 780],
    'H': [505, 530, 555, 580, 605, 640, 720],
    'D': [650, 680, 710, 740, 800, 820, 940],
    'G': [475, 500, 525, 550, 575, 600, 650],
}
EVOLUTION_REPLACEMENTS = {
    'uA6A': {}, 'uA6B': {'A101': 'A111'},
    'uO6A': {'A102': 'A112'}, 'uO6B': {'A102': 'A112'},
    'uH6A': {'A104': 'A113'}, 'uH6B': {'A105': 'AeCM'},
    'uD6A': {'A106': 'A114'}, 'uD6B': {'A140': 'AeSL', 'A141': 'A136'},
    'uG6A': {'A107': 'A115', 'A137': 'A138'}, 'uG6B': {},
}


def expected_towers():
    result = {}
    for family in FAMILIES:
        for suffix in ['11', '12', '13', '14', '15', '6A', '6B']:
            level = int(suffix[1]) if suffix[0] == '1' else 6
            if family == 'A':
                skills = ['A100'] + (['A101'] if level >= 5 else [])
            elif family == 'O':
                skills = ['A102'] + (['A103', 'A139'] if level >= 5 else [])
                if level == 6:
                    skills += ['A131' if suffix == '6A' else 'A132']
            elif family == 'H':
                skills = ['A104'] + (['A105'] if level >= 5 else [])
            elif family == 'D':
                skills = ['A106'] + (['A140', 'A141'] if suffix == '6B' else ['A110', 'A135'] if level >= 5 else [])
            else:
                skills = ['A107', 'A137', 'A116']
            result['u' + family + suffix] = skills + COMMON
    return result


EXPECTED_TOWERS = expected_towers()


def field_value(abilities, code, field, level=0, column=0, default=None):
    require(code in abilities, f'Missing ability object {code}')
    return abilities[code][1].get((field, level, column), (None, default))[1]


def validate_skill_bars(units, abilities):
    actual_towers = {uid for uid in units if re.fullmatch(r'u[A O H D G](?:1[1-5]|6[AB])'.replace(' ', ''), uid)}
    require(actual_towers == set(EXPECTED_TOWERS), 'Expected exactly 35 tower types')
    for uid, expected in EXPECTED_TOWERS.items():
        attached = units[uid].get('uabi', '').split(',')
        require(attached == expected, f'{uid}: complete skill bar mismatch {attached}; expected {expected}')
        for aid in attached:
            require(aid in abilities, f'{uid}: missing ability object {aid}')
        require('AeEV' not in attached, f'{uid}: evolution status must be dynamic')


def validate_upgrade_edges(units):
    edges = []
    for family in FAMILIES:
        chain = [f'u{family}1{level}' for level in range(1, 6)]
        for index, uid in enumerate(chain):
            expected = [chain[index + 1]] if index < 4 else [f'u{family}6A', f'u{family}6B']
            require(units[uid].get('uupt') == ','.join(expected), f'{uid}: upgrade chain mismatch')
            for successor in expected:
                require(units[successor]['uacq'] >= units[uid]['uacq'], f'{uid}->{successor}: effective range regressed')
                require(units[successor]['ua1r'] >= units[uid]['ua1r'], f'{uid}->{successor}: object range regressed')
                edges.append((uid, successor))
        for branch in 'AB':
            uid = f'u{family}6{branch}'
            require(units[uid].get('uupt') == '', f'{uid}: inherited terminal upgrade')
            require(base_dps(units[uid]) >= base_dps(units[chain[-1]]), f'{uid}: terminal basic DPS regressed')
    require(len(edges) == 30, 'Expected exactly 30 upgrade edges')
    return edges


def base_dps(fields):
    cooldown = fields.get('ua1c', 0)
    require(math.isfinite(cooldown) and cooldown > 0, 'Invalid tower attack cooldown')
    return (fields['ua1b'] + fields['ua1d'] * (fields['ua1s'] + 1) / 2) / cooldown


def validate_tower_identity(units):
    for family in FAMILIES:
        low_icon, low_model, high_icon, high_model = IDENTITIES[family]
        for index, suffix in enumerate(['11', '12', '13', '14', '15', '6A', '6B']):
            uid = 'u' + family + suffix
            fields = units[uid]
            model = low_model if index < 4 else high_model
            icon = 'ReplaceableTextures\\CommandButtons\\BTN' + (low_icon if index < 4 else high_icon) + '.blp'
            if index >= 5:
                icon = 'war3mapImported\\' + BRANCH_ICONS[family][index - 5] + '.blp'
            require(fields.get('umdl') == model, f'{uid}: model changed')
            for key in ['uico', 'ussi']:
                require(fields.get(key) == icon, f'{uid}: {key} identity mismatch')
            require(fields.get('uacq') == RANGES[family][index], f'{uid}: effective range changed')
            require(fields.get('ua1r') == RANGES[family][index] + 500, f'{uid}: equipment range buffer changed')


def validate_command_ui(units, abilities):
    normal_slots = {'A100': 0, 'A101': 1, 'A102': 0, 'A104': 0, 'A105': 1, 'A106': 0,
                    'A116': 1, 'A111': 1, 'A112': 0, 'A113': 0, 'A114': 0, 'AeCM': 1,
                    'A135': 1, 'A136': 1, 'A137': 0, 'A138': 0, 'A139': 1, 'A141': 1,
                    'A131': 2, 'A132': 2}
    for aid, x in normal_slots.items():
        require((field_value(abilities, aid, 'abpx'), field_value(abilities, aid, 'abpy')) == (x, 1), f'{aid}: wrong visible skill cell')
    for aid in ['A131', 'A132']:
        require(field_value(abilities, aid, 'ahky') == 'E', f'{aid}: wrong active skill hotkey')
        require((field_value(abilities, aid, 'aubx'), field_value(abilities, aid, 'auby')) == (2, 1), f'{aid}: wrong off-state skill cell')
        require(field_value(abilities, aid, 'auhk') == 'E', f'{aid}: wrong off-state skill hotkey')
    for aid, cell in [('A133', (3, 1)), ('A130', (2, 2)), ('AeEV', (3, 2))]:
        require((field_value(abilities, aid, 'abpx'), field_value(abilities, aid, 'abpy')) == cell, f'{aid}: shared command cell changed')
    require(field_value(abilities, 'A133', 'ahky') == 'V', 'A133: sale hotkey changed')
    require(field_value(abilities, 'A133', 'auhk') == 'V', 'A133: sale off hotkey changed')
    for uid, attached in EXPECTED_TOWERS.items():
        family, suffix = uid[1], uid[2:]
        if suffix == '11':
            index = FAMILIES.index(family)
            cell, key = [(0, 2), (1, 2), (2, 2), (0, 1), (1, 1)][index], 'QWEAS'[index]
        else:
            cell, key = ((1, 2), 'W') if suffix == '6B' else ((0, 2), 'Q')
        obj = units[uid]
        require((obj.get('ubpx'), obj.get('ubpy')) == cell, f'{uid}: wrong build/upgrade cell')
        require(obj.get('uhot') == key, f'{uid}: wrong build/upgrade hotkey')
    for uid, attached in EXPECTED_TOWERS.items():
        obj = units[uid]
        # Native hidden effects are not visible commands. Include dynamic status,
        # plus successor buttons in the selected tower's actual command card.
        commands = []
        for aid in attached + ['AeEV']:
            if aid not in HIDDEN:
                commands.append((aid, (field_value(abilities, aid, 'abpx'), field_value(abilities, aid, 'abpy')), field_value(abilities, aid, 'ahky', default='')))
        for successor in obj['uupt'].split(',') if obj['uupt'] else []:
            commands.append((successor, (units[successor]['ubpx'], units[successor]['ubpy']), units[successor]['uhot']))
        check_command_conflicts(uid, commands)


def check_command_conflicts(uid, commands):
    cells, keys = {}, {}
    for command, cell, key in commands:
        require(cell not in cells, f'{uid}: visible command cells overlap: {cells.get(cell)} and {command}')
        cells[cell] = command
        if key:
            require(key.upper() not in keys, f'{uid}: visible command hotkeys overlap: {keys.get(key.upper())} and {command}')
            keys[key.upper()] = command


def validate_branch_resources(artifact, units, abilities):
    paths = set()
    for uid in EXPECTED_TOWERS:
        if uid[2] == '6':
            paths.add(units[uid]['uico'])
            paths.add(units[uid]['ussi'])
    for aid in ['A140', 'A141']:
        for field in ['aart', 'arar']:
            paths.add(field_value(abilities, aid, field))
    for path in paths:
        require(isinstance(path, str) and path.startswith('war3mapImported\\BTN'), f'Invalid exact custom icon path {path!r}')
        require(artifact.has(path) and artifact.extract(path), f'Missing exact BTN resource {path}')
        disabled = 'ReplaceableTextures\\CommandButtonsDisabled\\DIS' + path.rsplit('\\', 1)[1]
        require(artifact.has(disabled) and artifact.extract(disabled), f'Missing exact DISBTN resource {disabled}')


def validate_upgrade_artifact(units, abilities, artifact=None):
    validate_skill_bars(units, abilities)
    edges = validate_upgrade_edges(units)
    validate_tower_identity(units)
    validate_command_ui(units, abilities)
    if artifact is not None:
        validate_branch_resources(artifact, units, abilities)
    return edges


class JassScalarEvaluator:
    """Fail-closed evaluator for the compiler's scalar if/set/return subset.

    This is static evaluation, not execution of the map or arbitrary Python.
    Only whitelisted AST operations and declared Jass scalar functions work.
    Mixed and/or expressions are rejected: Jass gives OR higher precedence
    than AND, unlike Python. This subset never guesses their interpretation.
    """
    def __init__(self, script):
        self.functions = {}
        for match in re.finditer(r'^function (\w+) takes ([^\n]*?) returns \w+\n(.*?)^endfunction', script, re.M | re.S):
            name, signature, body = match.groups()
            args = [] if signature == 'nothing' else [arg.strip().split()[-1] for arg in signature.split(',')]
            self.functions[name] = (args, [line.strip() for line in body.splitlines()])
        self.constants = {name: float(value) if '.' in value else int(value)
                          for name, value in re.findall(r'^\s*set (\w+) = (-?\d+(?:\.\d+)?)\s*$', script, re.M)}

    def expression(self, text, scope):
        text = re.sub(r'\btrue\b', 'True', text)
        text = re.sub(r'\bfalse\b', 'False', text)
        text = re.sub(r'\bnull\b', 'None', text)
        text = text.strip()
        try:
            node = ast.parse(text, mode='eval').body
        except SyntaxError as exc:
            raise ValueError(f'Unsupported scalar Jass expression {text}') from exc
        bool_ops = {type(part.op) for part in ast.walk(node) if isinstance(part, ast.BoolOp)}
        require(len(bool_ops) <= 1, 'Mixed Jass and/or requires a Jass-specific precedence parser')
        def read(node):
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Name):
                require(node.id in scope or node.id in self.constants, f'Unknown Jass scalar {node.id}')
                return scope[node.id] if node.id in scope else self.constants[node.id]
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                return self.call(node.func.id, [read(arg) for arg in node.args])
            if isinstance(node, ast.UnaryOp):
                value = read(node.operand)
                if isinstance(node.op, ast.Not): return not value
                if isinstance(node.op, ast.USub): return -value
                if isinstance(node.op, ast.UAdd): return value
            if isinstance(node, ast.BoolOp):
                values = [bool(read(value)) for value in node.values]
                if isinstance(node.op, ast.And): return all(values)
                if isinstance(node.op, ast.Or): return any(values)
            if isinstance(node, ast.BinOp):
                left, right = read(node.left), read(node.right)
                if isinstance(node.op, ast.Add): return left + right
                if isinstance(node.op, ast.Sub): return left - right
                if isinstance(node.op, ast.Mult): return left * right
                if isinstance(node.op, ast.Div): return left / right
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left, right, op = read(node.left), read(node.comparators[0]), node.ops[0]
                if isinstance(op, ast.Eq): return left == right
                if isinstance(op, ast.NotEq): return left != right
                if isinstance(op, ast.Lt): return left < right
                if isinstance(op, ast.LtE): return left <= right
                if isinstance(op, ast.Gt): return left > right
                if isinstance(op, ast.GtE): return left >= right
            raise ValueError(f'Unsupported scalar Jass node {ast.dump(node)}')
        return read(node)

    def call(self, name, args):
        require(name in self.functions, f'Missing Jass function {name}')
        signature, lines = self.functions[name]
        require(len(args) == len(signature), f'{name}: wrong scalar argument count')
        scope = dict(zip(signature, args))
        stack = []
        active = True
        for line in lines:
            if line.startswith('if ') and line.endswith(' then'):
                condition = bool(self.expression(line[3:-5], scope)) if active else False
                stack.append([active, condition])
                active = active and condition
            elif line.startswith('elseif ') and line.endswith(' then'):
                require(stack, f'{name}: unmatched elseif')
                parent, previous = stack[-1]
                condition = bool(self.expression(line[7:-5], scope)) if parent and not previous else False
                stack[-1][1] = previous or condition
                active = parent and condition
            elif line == 'else':
                require(stack, f'{name}: unmatched else')
                parent, previous = stack[-1]
                active = parent and not previous
                stack[-1][1] = True
            elif line == 'endif':
                require(stack, f'{name}: unmatched endif')
                active = stack.pop()[0]
            elif active and line.startswith('return '):
                return self.expression(line[7:], scope)
            elif active and line.startswith('set '):
                key, value = line[4:].split(' = ', 1)
                require('[' not in key, f'{name}: non-scalar assignment')
                scope[key] = self.expression(value, scope)
            elif active and line.startswith('local '):
                declaration = line[6:].split(' ', 1)[1]
                if ' = ' in declaration:
                    key, value = declaration.split(' = ', 1)
                    scope[key] = self.expression(value, scope)
                else:
                    scope[declaration] = 0
            elif active and line and not line.startswith('//'):
                raise ValueError(f'{name}: unsupported scalar Jass statement {line}')
        raise ValueError(f'{name}: scalar path returned no value')


def rawcode(value):
    return int.from_bytes(value.encode('ascii'), 'big') if value else 0


def function_body(script, name):
    match = re.search(r'^function ' + re.escape(name) + r' takes [^\n]*\n(.*?)^endfunction', script, re.M | re.S)
    require(match is not None, f'Missing Jass function {name}')
    return match[1]


def validate_evolution_jass(script, units, abilities):
    evaluator = JassScalarEvaluator(script)
    for family_index, family in enumerate(FAMILIES, 1):
        for branch_index, branch in enumerate('AB', 1):
            uid = f'u{family}6{branch}'
            mapping = {}
            for old_func, new_func in [('tdEvolutionSkillOriginal', 'tdEvolutionSkillReplacement'),
                                       ('tdEvolutionDisplayOriginal', 'tdEvolutionDisplayReplacement')]:
                old = evaluator.call(old_func, [family_index, branch_index])
                new = evaluator.call(new_func, [family_index, branch_index])
                require(bool(old) == bool(new), f'{uid}: incomplete evolution replacement pair')
                if new:
                    mapping[old] = new
            expected = {rawcode(old): rawcode(new) for old, new in EVOLUTION_REPLACEMENTS[uid].items()}
            require(mapping == expected, f'{uid}: Jass evolution mapping mismatch')
            attached = [rawcode(aid) for aid in units[uid]['uabi'].split(',')]
            for old, new in mapping.items():
                require(attached.count(old) == 1, f'{uid}: evolution original missing or duplicated')
                require(new not in attached, f'{uid}: evolved variant already attached')
                attached[attached.index(old)] = new
            expected_evolved = [rawcode(EVOLUTION_REPLACEMENTS[uid].get(aid, aid)) for aid in EXPECTED_TOWERS[uid]]
            require(attached == expected_evolved, f'{uid}: evolved skill set loses non-selected skill')
            require(len(attached) == len(set(attached)), f'{uid}: evolved skills duplicated')
            for aid in EVOLUTION_REPLACEMENTS[uid].values():
                require(aid in abilities, f'{uid}: missing evolved ability {aid}')
            for evolved in [False, True]:
                split = evaluator.call('tdEvolutionSplitArrowDisplayLevel', [family_index, branch_index, evolved])
                corpse = evaluator.call('tdEvolutionCorpseDisplayLevel', [family_index, branch_index, evolved])
                require(split == (2 if family == 'A' and branch == 'A' and evolved else 1), f'{uid}: split display evolution leaks')
                require(corpse == (2 if family == 'G' and branch == 'B' and evolved else 1), f'{uid}: corpse display evolution leaks')
    for level in range(1, 7):
        for branch in [0, 1, 2]:
            for evolved in [False, True]:
                split = evaluator.call('tdArcherSplitArrowDamageMultiplier', [level, branch, evolved])
                corpse = evaluator.call('tdGhoulCorpseExplosionDamageForBranch', [level, branch, evolved])
                require(math.isclose(split, 1.2 if level == 6 and branch == 1 and evolved else 1.0), f'Jass split multiplier leaks: level={level}, branch={branch}, evolved={evolved}')
                require(math.isclose(corpse, 43.2 if level == 6 and branch == 2 and evolved else 36.0), f'Jass corpse damage leaks: level={level}, branch={branch}, evolved={evolved}')
    require(evaluator.call('tdArcherSplitArrowTargetCount', [6]) == 7, 'Jass six-tier split arrow must have seven total targets')
    refresh = function_body(script, 'tdEvolutionRefresh')
    for fragment in ['tdEvolutionSkillReplacement(choice, branch)', 'tdEvolutionSkillOriginal(choice, branch)',
                     'tdEvolutionDisplayOriginal(choice, branch)', 'tdEvolutionDisplayReplacement(choice, branch)',
                     'tdEvolutionSplitArrowDisplayLevel(choice, branch, TDEvolutionTower_evolved[record])', 'tdEvolutionCorpseDisplayLevel(choice, branch, TDEvolutionTower_evolved[record])']:
        require(fragment in refresh, f'Jass evolution runtime does not consume {fragment}')
    require(len(re.findall(r'call unit_removeAbility\(', refresh)) == 2, 'Jass evolution must remove only selected effect/display')
    require(re.search(r'call unit_removeAbility\([^,]+, tdEvolutionSkillOriginal\(choice, branch\)\)', refresh), 'Jass evolution original is not removed')
    require(re.search(r'call unit_removeAbility\([^,]+, displayOriginal\)', refresh), 'Jass evolution selected display is not removed')
    require(re.search(r'call unit_addPermanentAbility\([^,]+, replacement, 1\)', refresh), 'Jass evolution replacement is not added')
    require(re.search(r'call unit_addPermanentAbility\([^,]+, tdEvolutionDisplayReplacement\(choice, branch\), 1\)', refresh), 'Jass evolution replacement display is not added')
    for handler, helper in [('tdHandleArcherSplitArrowDamage', 'tdArcherSplitArrowDamageMultiplier'),
                            ('tdHandleGhoulCorpseExplosionDamage', 'tdGhoulCorpseExplosionDamageForBranch')]:
        body = function_body(script, handler)
        require(helper + '(' in body, f'Jass damage handler does not consume {helper}')
        require('tdTowerLevelForUnitTypeId(GetUnitTypeId(' in body and 'tdTowerBranchForUnitTypeId(GetUnitTypeId(' in body and 'tdTowerIsEvolved(' in body, f'{handler}: multiplier does not use actual level/branch/evolution')
        require(re.search(r'call ' + handler + r'\(', script), f'{handler}: damage callback is not wired')
    split_body = function_body(script, 'tdHandleArcherSplitArrowDamage')
    split_assignment = re.search(r'set (\w+) = DamageEvent_getUnreducedAmount\(\) \* tdArcherSplitArrowDamageMultiplier\(tdTowerLevelForUnitTypeId\(GetUnitTypeId\((\w+)\)\), tdTowerBranchForUnitTypeId\(GetUnitTypeId\(\2\)\), tdTowerIsEvolved\(\2,', split_body)
    require(split_assignment is not None, 'Jass split damage path detached from unreduced extra-arrow multiplier')
    damage_variable, source_variable = split_assignment.groups()
    require(re.search(r'call tdDealArcherSplitArrowAttackDamage\(' + source_variable + r', \w+, ' + damage_variable + r',', split_body), 'Jass split multiplier result does not reach immediate extra-arrow damage')
    require(re.search(r'set attackDamage\[\w+\] = ' + damage_variable + r'\b', split_body), 'Jass split multiplier result does not reach delayed extra-arrow damage')
    require(len(re.findall(r'set ' + damage_variable + r' =', split_body)) == 1, 'Jass split multiplier result is overwritten before damage')
    callback = re.search(r'alloc_CallbackSingle_(\w+)\(', split_body)
    require(callback is not None, 'Jass delayed extra-arrow callback is not allocated')
    callback_name = 'call_' + callback[1]
    callback_body = function_body(script, callback_name)
    require(re.search(r'call tdDealArcherSplitArrowAttackDamage\(\w+\[(\w+)\], \w+\[\1\], attackDamage\[\1\],', callback_body), 'Jass delayed extra-arrow callback does not consume stored multiplier result')
    require(re.search(r'call ' + re.escape(callback_name) + r'\(', script), 'Jass delayed extra-arrow callback is not wired')

    for setter in ['DamageEvent_setAmount(', 'DamageEvent_setDamage(', 'BlzSetEventDamage(']:
        require(setter not in split_body, 'Jass split evolution changes primary-arrow damage')
    corpse_body = function_body(script, 'tdHandleGhoulCorpseExplosionDamage')
    require(re.search(r'call unit_damageTarget(?:_\d+)?\((\w+), \w+, tdGhoulCorpseExplosionDamageForBranch\(tdTowerLevelForUnitTypeId\(GetUnitTypeId\(\1\)\), tdTowerBranchForUnitTypeId\(GetUnitTypeId\(\1\)\), tdTowerIsEvolved\(\1,', corpse_body), 'Jass corpse helper result does not reach damage')
    pet_corpse = function_body(script, 'tdPetOnCorpseExplosion')
    require(re.search(r'set (\w+) = tdGhoulCorpseExplosionDamage\(\) \* power', pet_corpse), 'Jass pet poison domain must retain base corpse damage times power')
    require('tdGhoulCorpseExplosionDamageForBranch(' not in pet_corpse, 'Jass pet poison domain must not inherit evolved corpse multiplier')
    # Both tooltip upgrades have to run after the selected-effect block ends:
    # archer A and ghoul B deliberately have no effect replacement.
    lines = refresh.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == 'if replacement != 0 then')
    depth, end = 0, None
    for index in range(start, len(lines)):
        line = lines[index].strip()
        if line.startswith('if ') and line.endswith(' then'): depth += 1
        if line == 'endif': depth -= 1
        if depth == 0:
            end = index
            break
    require(end is not None, 'Jass selected-effect replacement block is unclosed')
    for helper in ['tdEvolutionSplitArrowDisplayLevel(', 'tdEvolutionCorpseDisplayLevel(']:
        require(any(helper in line for line in lines[end + 1:]), f'Jass {helper} must work when effect replacement is zero')



def main():
    require(len(sys.argv) == 2, __doc__)
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    units = unit_objects(artifact.extract('war3map.w3u'))
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    validate_upgrade_artifact(units, abilities, artifact)
    validate_evolution_jass(artifact.extract('war3map.j').decode('utf-8'), units, abilities)
    print('PASS: exact 35 tower skill bars; 30 non-regressive upgrade edges; 10 terminal basic DPS; build/upgrade and visible-command cells/hotkeys; branch BTN/DISBTN resources.')
    print('NOT TESTED: native command rendering, in-game combat, balance or pathing.')


if __name__ == '__main__':
    main()
