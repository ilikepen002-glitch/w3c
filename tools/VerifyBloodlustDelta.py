#!/usr/bin/env python3
"""Read-only, closed C delta against immutable official B (697d0f3).

python tools/VerifyBloodlustDelta.py map.w3x --baseline-map official-B.w3x

Legacy bodies are immutable B plus independently declared, source-proven C
insertions. Added functions are small semantic lowering templates, not copies
of the current artifact. No diagnostic, number, type ID, temp or whole legacy
body is ignored. Only empty inter-function lines are layout-insignificant.
This does not execute Warcraft or rebuild/write an MPQ.
"""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifySemanticIconArtifact import load_objects
from VerifyGlobalRankingsArtifact import members, normalize_info
from VerifyDamageRankingJass import functions
from VerifyBuilderControlDelta import allocations, TYPE_TEST
from VerifyBloodlustDiagnostics import proved_diagnostic_view, source_line_maps
from VerifyBloodlustAutocastArtifact import (validate_sources, validate_choice_matrix,
                                           validate_native_bloodlust, validate_compiled_lifecycle)
from VerifyTowerUpgradeArtifact import JassScalarEvaluator

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = '697d0f3e7ce8c1ff9f1f163bcf9b72ea09afdda5'
BASE_MAP_SHA256 = 'cd720757a37f2b4ac5c58bcc7ae6dbde7fe20d1dbbf71045a1414b4fd9f4c577'
BASE_JASS_SHA256 = '65469d69a7207e17ec7d7d0dfe3054288ca6a310dcaa5a2e2fae037bc9a2c051'
SOURCE_PATHS = {
    'TDEquipmentAbilities': 'wurst/items/TDEquipmentAbilities.wurst',
    'TDTowerRuntime': 'wurst/towers/TDTowerRuntime.wurst',
    'TDEquipmentObjectGen': 'wurst/items/TDEquipmentObjectGen.wurst',
    'TDTowerBloodlustAutocast': 'wurst/towers/TDTowerBloodlustAutocast.wurst',
}
BASE_SOURCE_SHA256 = {
    'TDEquipmentAbilities': '7f61ce0dd7e0ea83dcca16524bd9d2d882df29ac6d9bbdd3a459120d585b8fa8',
    'TDTowerRuntime': '39a6a76efe9548771cc8d0c142f2b53322bf0a1a188ea986c8e97632374ad769',
    'TDEquipmentObjectGen': 'f77c09b1c3947468fb52c55196da532f0af42e3191149eb3d2b2b6472c4172ab',
}
P = 'TDTowerBloodlustAutocast_'
ABILITY = 'TDTowerCatalogData_TD_ORC_BLOODLUST_ABILITY_ID'
OLD_SUFFIX = '可自动施放。'
NEW_SUFFIX = '可自动施放，获得时默认开启，可手动关闭。'


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def read_sources(root=ROOT):
    current = {package: (Path(root) / path).read_text() for package, path in SOURCE_PATHS.items()}
    baseline = {package: subprocess.check_output(['git', 'show', BASE_COMMIT + ':' + SOURCE_PATHS[package]],
                                                cwd=root).decode() for package in BASE_SOURCE_SHA256}
    return current, baseline


def source_line(sources, package, statement, scope=None):
    """Unique exact approved statement inside its declared source function."""
    text = sources[package]
    offset = 0
    if scope:
        match = re.search(r'^(?:public )?function ' + re.escape(scope) +
                          r'\([^\n]*\)[^\n]*\n((?:\t[^\n]*\n|\n)*)', text, re.M)
        require(match is not None, 'Missing insertion source function: ' + scope)
        offset, text = match.start(1), match[1]
    sites = list(re.finditer(r'^\t*' + re.escape(statement) + r'$', text, re.M))
    require(len(sites) == 1, 'Source insertion must have one exact statement: ' + statement)
    return sources[package][:offset + sites[0].start()].count('\n') + 1


def diagnostic(sources, package, callee, statement, scope=None, reference=False):
    line = source_line(sources, package, statement, scope)
    prefix = 'via function reference ' if reference else 'when calling ' + callee + ' in '
    return '"' + prefix + package + ', line ' + str(line) + '"'


def replace_once(text, anchor, replacement):
    require(text.count(anchor) == 1, 'Baseline insertion anchor is not unique: ' + anchor.strip())
    return text.replace(anchor, replacement, 1)


def insert_after_call(text, callee, args, addition):
    sites = list(re.finditer(r'^\t+call ' + re.escape(callee + '(' + args + ', ') +
                            r'"[^"\n]*"\)\n', text, re.M))
    require(len(sites) == 1, 'Baseline lifecycle anchor changed: ' + callee)
    anchor = sites[0][0]
    return replace_once(text, anchor, anchor + addition)


def expected_legacy_functions(baseline, sources):
    """Exactly ten semantic insertion sites plus compiler initialization glue."""
    expected = {name: fn[0] for name, fn in functions(baseline).items()}
    runtime = 'TDTowerRuntime'
    sites = {
        'tdHandleTowerSellCast': ('tdForgetEquipmentAbilities', 'tower_2', 'tdForgetBloodlustAutocast', 'tdHandleTowerSellCast'),
        'tdRejectTowerConstruction': ('tdForgetEquipmentAbilities', 'tower_2', 'tdForgetBloodlustAutocast', 'tdRejectTowerConstruction'),
        'tdHandleTowerConstructionCancelled': ('tdForgetEquipmentAbilities', 'tower_2', 'tdForgetBloodlustAutocast', 'tdHandleTowerConstructionCancelled'),
        'tdHandleTowerDeath': ('tdForgetEquipmentAbilities', 'tower_2', 'tdForgetBloodlustAutocast', 'tdHandleTowerDeath'),
        'tdHandleTowerConstructionFinished': ('tdRefreshTowerEquipmentBonuses_1', 'tower_2', 'tdInitializeBloodlustAutocast', 'tdHandleTowerConstructionFinished'),
        'tdHandleTowerUpgradeFinished': ('tdRefreshTowerRangeIndicatorsForTower', 'tower_2', 'tdInitializeBloodlustAutocast', 'tdHandleTowerUpgradeFinished'),
        'call_doAfter_TDTowerRuntime_3': ('tdEvolutionRefresh', 'tower[this_1]', 'tdInitializeBloodlustAutocast', 'tdHandleTowerUpgradeCancelled'),
    }
    for name, (anchor, arg, callee, scope) in sites.items():
        diag = diagnostic(sources, runtime, callee, callee + '(tower)', scope)
        expected[name] = insert_after_call(expected[name], anchor, arg, '\tcall ' + callee + '(' + arg + ', ' + diag + ')\n')
    name = 'tdSetupDialogTrigger'
    source_line(sources, runtime, 'tdSetupBloodlustAutocastOrders()', name)
    anchor = '\tset TDTowerRuntime_tdTowerGameplayEventsReady = true\n'
    expected[name] = replace_once(expected[name], anchor, anchor + '\tcall tdSetupBloodlustAutocastOrders()\n')
    name = 'tdEquipmentSyncCooldown'
    equipment = 'TDEquipmentAbilities'
    source_line(sources, equipment, 'if tower.getAbilityLevel(abilityId) == desiredLevel', name)
    anchor = '\tset TDEquipmentCooldown_desiredLevel[record] = desiredLevel\n'
    guard = ('\tif abilityId == ' + ABILITY + ' then\n'
             '\t\tif unit_getAbilityLevel(tower_2, abilityId) == desiredLevel then\n'
             '\t\t\tset wurst_stack_depth = wurst_stack_depth - 1\n\t\t\treturn\n\t\tendif\n\tendif\n')
    expected[name] = replace_once(expected[name], anchor, anchor + guard)
    diag = diagnostic(sources, equipment, 'tdRestoreBloodlustAutocast', 'tdRestoreBloodlustAutocast(tower)', name)
    anchor = '\t\tcall unit_setAbilityLevel(tower_2, abilityId, desiredLevel)\n'
    addition = '\t\tif abilityId == ' + ABILITY + ' then\n\t\t\tcall tdRestoreBloodlustAutocast(tower_2, ' + diag + ')\n\t\tendif\n'
    expected[name] = replace_once(expected[name], anchor, anchor + addition)
    name = 'call_doPeriodically_TDEquipmentAbilities'
    diag = diagnostic(sources, equipment, 'tdRestoreBloodlustAutocast', 'tdRestoreBloodlustAutocast(record.tower)', 'tdSetupEquipmentAbilities')
    anchor = '\t\t\t\tcall unit_setAbilityLevel(TDEquipmentCooldown_tower[record], TDEquipmentCooldown_abilityId[record], TDEquipmentCooldown_desiredLevel[record])\n'
    addition = ('\t\t\t\tif TDEquipmentCooldown_abilityId[record] == ' + ABILITY + ' then\n'
                '\t\t\t\t\tcall tdRestoreBloodlustAutocast(TDEquipmentCooldown_tower[record], ' + diag + ')\n\t\t\t\tendif\n')
    expected[name] = replace_once(expected[name], anchor, anchor + addition)
    name = 'init_Orders'
    anchor = 'function init_Orders takes nothing returns boolean\n'
    expected[name] = replace_once(expected[name], anchor, anchor + '\tset Orders_bloodlustoff = 852103\n\tset Orders_bloodluston = 852102\n')
    name = 'initGlobals'
    for anchor, inserted in [
        ('\tset ref_function_tdCountPlayerTowerEnum = function tdCountPlayerTowerEnum\n', '\tset ref_function_bridge_tdHandleBloodlustAutocastOrder = function bridge_tdHandleBloodlustAutocastOrder\n'),
        ('\tset ref_function_bridge_init_TDEquipmentAbilities = function bridge_init_TDEquipmentAbilities\n', '\tset ref_function_bridge_init_TDTowerBloodlustAutocast = function bridge_init_TDTowerBloodlustAutocast\n'),
    ]:
        expected[name] = replace_once(expected[name], anchor, inserted + anchor)
    name = 'main'
    anchor = '\tcall TriggerAddCondition(initTrig, Condition(ref_function_bridge_init_TDEquipmentAbilities))\n'
    inserted = ('\tcall TriggerAddCondition(initTrig, Condition(ref_function_bridge_init_TDTowerBloodlustAutocast))\n'
                '\tif  not TriggerEvaluate(initTrig) then\n'
                '\t\tcall error("Could not initialize package TDTowerBloodlustAutocast.", "when calling error in TDTowerBloodlustAutocast, line 1")\n'
                '\tendif\n\tcall TriggerClearConditions(initTrig)\n')
    expected[name] = replace_once(expected[name], anchor, inserted + anchor)
    return expected


FRAME = ['set wurst_stack[wurst_stack_depth] = w__wurst_stackPos',
         'set wurst_stack_depth = wurst_stack_depth + 1']
POP = 'set wurst_stack_depth = wurst_stack_depth - 1'


def guard(condition, result=''):
    return ['if ' + condition + ' then', '\t' + POP, '\treturn' + (' ' + result if result else ''), 'endif']


def jass_function(name, params, result, body, locals=(), tracked=False):
    statements = list(locals) + (FRAME if tracked else []) + body
    if tracked:
        statements += [POP] + (['return true'] if result == 'boolean' else [])
    return ('function ' + name + ' takes ' + params + ' returns ' + result + '\n' +
            ''.join('\t' + line + '\n' for line in statements) + 'endfunction')


def expected_added_functions(sources):
    """Independent semantic lowering of the small approved new module.

    Explicit guards/statements forbid extra side effects, broader eligibility,
    restored-choice writeback, wrong order audience and initialization drift.
    Diagnostic positions are proved against exact current source statements.
    """
    package = 'TDTowerBloodlustAutocast'
    def diag(callee, statement, scope):
        return diagnostic(sources, package, callee, statement, scope)
    result = {}
    def add(name, params, returns, body, locals=(), tracked=False):
        result[name] = jass_function(name, params, returns, body, locals, tracked)
    add('tdBloodlustChoiceAfterInitialization', 'integer choice, boolean eligible', 'integer',
        ['if  not eligible then', '\treturn choice', 'endif',
         'if choice == ' + P + 'TD_BLOODLUST_CHOICE_UNKNOWN then', '\treturn ' + P + 'TD_BLOODLUST_CHOICE_ON', 'endif', 'return choice'])
    add('tdBloodlustChoiceAfterOrder', 'integer choice, integer orderId, boolean eligible, boolean scripted', 'integer',
        ['if  not eligible then', '\treturn choice', 'endif', 'if scripted then', '\treturn choice', 'endif',
         'if orderId == Orders_bloodluston then', '\treturn ' + P + 'TD_BLOODLUST_CHOICE_ON', 'endif',
         'if orderId == Orders_bloodlustoff then', '\treturn ' + P + 'TD_BLOODLUST_CHOICE_OFF', 'endif', 'return choice'])
    add('tdBloodlustOrderForChoice', 'integer choice, boolean eligible', 'integer',
        ['if  not eligible then', '\treturn 0', 'endif',
         'if choice == ' + P + 'TD_BLOODLUST_CHOICE_ON then', '\treturn Orders_bloodluston', 'endif',
         'if choice == ' + P + 'TD_BLOODLUST_CHOICE_OFF then', '\treturn Orders_bloodlustoff', 'endif', 'return 0'])
    name = 'tdBloodlustAutocastEligible'
    busy = 'dispatch_Table_Table_hasBoolean(TDPetState_tdPetBusyTowers, handle_getHandleId(tower_2), ' + diag('hasBoolean', 'if tdPetBusyTowers.hasBoolean(tower.getHandleId())', name) + ')'
    body = []
    for condition in ('tower_2 == null', ' not unit_isAlive(tower_2)',
                      'GetUnitTypeId(tower_2) != TDTowerCatalogData_TD_ORC_LEVEL_6_A_ID',
                      'unit_getAbilityLevel(tower_2, ' + ABILITY + ') == 0', busy):
        body += guard(condition, 'false')
    add(name, 'unit tower_2, string w__wurst_stackPos', 'boolean', body, tracked=True)
    name = 'tdRestoreBloodlustAutocast'
    eligible = ' not tdBloodlustAutocastEligible(tower_2, ' + diag('tdBloodlustAutocastEligible', 'if not tdBloodlustAutocastEligible(tower)', name) + ')'
    load = 'dispatch_Table_Table_loadInt(' + P + 'tdBloodlustChoices, handle_getHandleId(tower_2), ' + diag('loadInt', 'let orderId = tdBloodlustOrderForChoice(tdBloodlustChoices.loadInt(tower.getHandleId()), true)', name) + ')'
    body = guard(P + 'tdBloodlustRestoring') + guard(eligible)
    body += ['set orderId = tdBloodlustOrderForChoice(' + load + ', true)'] + guard('orderId == 0')
    body += ['set ' + P + 'tdBloodlustRestoring = true', 'call unit_issueImmediateOrderById(tower_2, orderId)', 'set ' + P + 'tdBloodlustRestoring = false']
    add(name, 'unit tower_2, string w__wurst_stackPos', 'nothing', body, ['local integer orderId'], True)
    name = 'tdInitializeBloodlustAutocast'
    body = guard(' not tdBloodlustAutocastEligible(tower_2, ' + diag('tdBloodlustAutocastEligible', 'if not tdBloodlustAutocastEligible(tower)', name) + ')')
    load = 'dispatch_Table_Table_loadInt(' + P + 'tdBloodlustChoices, key_1, ' + diag('loadInt', 'let choice = tdBloodlustChoiceAfterInitialization(tdBloodlustChoices.loadInt(key), true)', name) + ')'
    body += ['set key_1 = handle_getHandleId(tower_2)', 'set choice = tdBloodlustChoiceAfterInitialization(' + load + ', true)',
             'call dispatch_Table_Table_saveInt(' + P + 'tdBloodlustChoices, key_1, choice, ' + diag('saveInt', 'tdBloodlustChoices.saveInt(key, choice)', name) + ')',
             'call tdRestoreBloodlustAutocast(tower_2, ' + diag('tdRestoreBloodlustAutocast', 'tdRestoreBloodlustAutocast(tower)', name) + ')']
    add(name, 'unit tower_2, string w__wurst_stackPos', 'nothing', body, ['local integer key_1', 'local integer choice'], True)
    name = 'tdForgetBloodlustChoiceKey'
    add(name, 'integer key_1, string w__wurst_stackPos', 'nothing',
        ['call dispatch_Table_Table_removeInt(' + P + 'tdBloodlustChoices, key_1, ' + diag('removeInt', 'tdBloodlustChoices.removeInt(key)', name) + ')'], tracked=True)
    name = 'tdForgetBloodlustAutocast'
    add(name, 'unit tower_2, string w__wurst_stackPos', 'nothing',
        ['if tower_2 != null then', '\tcall tdForgetBloodlustChoiceKey(handle_getHandleId(tower_2), ' + diag('tdForgetBloodlustChoiceKey', 'tdForgetBloodlustChoiceKey(tower.getHandleId())', name) + ')', 'endif'], tracked=True)
    name = 'tdHandleBloodlustAutocastOrder'
    body = guard(P + 'tdBloodlustRestoring') + ['set tower_2 = GetTriggerUnit()']
    body += guard(' not tdBloodlustAutocastEligible(tower_2, ' + diag('tdBloodlustAutocastEligible', 'if not tdBloodlustAutocastEligible(tower)', name) + ')')
    body += ['set orderId = GetIssuedOrderId()', 'if orderId != Orders_bloodluston then',
             '\tif orderId != Orders_bloodlustoff then', '\t\t' + POP, '\t\treturn', '\tendif', 'endif', 'set key_1 = handle_getHandleId(tower_2)']
    load = 'dispatch_Table_Table_loadInt(' + P + 'tdBloodlustChoices, key_1, ' + diag('loadInt', 'let choice = tdBloodlustChoiceAfterOrder(tdBloodlustChoices.loadInt(key), orderId, true, false)', name) + ')'
    body += ['set choice = tdBloodlustChoiceAfterOrder(' + load + ', orderId, true, false)',
             'call dispatch_Table_Table_saveInt(' + P + 'tdBloodlustChoices, key_1, choice, ' + diag('saveInt', 'tdBloodlustChoices.saveInt(key, choice)', name) + ')']
    add(name, 'string w__wurst_stackPos', 'nothing', body, ['local unit tower_2', 'local integer orderId', 'local integer key_1', 'local integer choice'], True)
    name = 'tdSetupBloodlustAutocastOrders'
    add(name, 'nothing', 'nothing',
        ['if ' + P + 'tdBloodlustOrderEventsReady then', '\treturn', 'endif', 'set ' + P + 'tdBloodlustOrderEventsReady = true',
         'call trigger_registerAnyUnitEvent(' + P + 'tdBloodlustOrderTrigger, EVENT_PLAYER_UNIT_ISSUED_ORDER)',
         'call trigger_addAction(' + P + 'tdBloodlustOrderTrigger, ref_function_bridge_tdHandleBloodlustAutocastOrder)'])
    name = 'init_TDTowerBloodlustAutocast'
    body = ['set ' + P + 'TD_BLOODLUST_CHOICE_' + key + ' = ' + str(value) for key, value in [('UNKNOWN', 0), ('ON', 1), ('OFF', 2)]]
    body += ['set ' + P + 'tdBloodlustChoices = new_Table(' + diag('new_Table', 'constant Table tdBloodlustChoices = new Table()', None) + ')',
             'set ' + P + 'tdBloodlustRestoring = false', 'set ' + P + 'tdBloodlustOrderEventsReady = false', 'set ' + P + 'tdBloodlustOrderTrigger = CreateTrigger()']
    add(name, 'string w__wurst_stackPos', 'boolean', body, tracked=True)
    add('bridge_init_TDTowerBloodlustAutocast', 'nothing', 'boolean',
        ['local boolean bridge_return = init_TDTowerBloodlustAutocast("via function reference TDTowerBloodlustAutocast, line 1")', 'return bridge_return'])
    diag_ref = diagnostic(sources, package, '', 'tdBloodlustOrderTrigger.addAction(function tdHandleBloodlustAutocastOrder)', 'tdSetupBloodlustAutocastOrders', reference=True)
    add('bridge_tdHandleBloodlustAutocastOrder', 'nothing', 'nothing', ['call tdHandleBloodlustAutocastOrder(' + diag_ref + ')'])
    return result


def residual(script):
    pieces, offset = [], 0
    for fn in functions(script).values():
        pieces.append(script[offset:fn.start()]); offset = fn.end()
    pieces.append(script[offset:])
    return ''.join(pieces)


def expected_residual(baseline):
    text = residual(baseline)
    additions = [
        ('integer Orders_move=0\n', 'integer Orders_bloodlustoff=0\ninteger Orders_bloodluston=0\n'),
        ('integer TDTowerCatalogData_TD_ARCHER_LEVEL_1_ID=0\n',
         ''.join(kind + ' ' + P + name + '=' + value + '\n' for kind, name, value in [
             ('integer', 'TD_BLOODLUST_CHOICE_OFF', '0'), ('integer', 'TD_BLOODLUST_CHOICE_ON', '0'),
             ('integer', 'TD_BLOODLUST_CHOICE_UNKNOWN', '0'), ('integer', 'tdBloodlustChoices', '0'),
             ('boolean', 'tdBloodlustOrderEventsReady', 'false'), ('trigger', 'tdBloodlustOrderTrigger', 'null'),
             ('boolean', 'tdBloodlustRestoring', 'false')])),
        ('code ref_function_tdCountPlayerTowerEnum=null\n', 'code ref_function_bridge_tdHandleBloodlustAutocastOrder=null\n'),
        ('code ref_function_bridge_init_TDEquipmentAbilities=null\n', 'code ref_function_bridge_init_TDTowerBloodlustAutocast=null\n'),
    ]
    for anchor, addition in additions:
        text = replace_once(text, anchor, addition + anchor)
    return text


def prove_jass_delta(script, baseline, current_sources, baseline_sources):
    require(digest(baseline) == BASE_JASS_SHA256, 'C requires immutable official B JASS')
    require(set(baseline_sources) == set(BASE_SOURCE_SHA256) and set(current_sources) == set(SOURCE_PATHS), 'C source package set changed')
    for package, expected in BASE_SOURCE_SHA256.items():
        require(digest(baseline_sources[package]) == expected, 'C requires frozen B source: ' + package)
    validate_sources(*[current_sources[p] for p in ('TDTowerBloodlustAutocast', 'TDEquipmentAbilities', 'TDTowerRuntime', 'TDEquipmentObjectGen')])
    view, diagnostics = proved_diagnostic_view(script, baseline,
                                               {p: current_sources[p] for p in baseline_sources}, baseline_sources)
    before, after = functions(baseline), functions(view)
    added = expected_added_functions(current_sources)
    require(set(after) == set(before) | set(added) and not (set(before) & set(added)), 'C JASS function set changed')
    # The newly earlier restore call moves this pre-existing native wrapper
    # ahead of cooldown declarations. Its full body remains immutable below.
    order = list(before)
    order.remove('unit_issueImmediateOrderById')
    order.insert(order.index('unit_setAbilityLevel'), 'unit_issueImmediateOrderById')
    require([name for name in after if name in before] == order, 'C legacy function order changed')
    require(allocations(view) == allocations(baseline), 'C named allocator identities/IDs changed')
    require(TYPE_TEST.findall(view) == TYPE_TEST.findall(baseline), 'C type comparisons changed')
    expected = expected_legacy_functions(baseline, current_sources)
    for name in before:
        require(after[name][0] == expected[name], 'C legacy JASS changed outside exact insertion: ' + name)
    for name, text in added.items():
        require(after[name][0] == text, 'C added function semantic template changed: ' + name)
    # Blank inter-function separators grow with the thirteen additions. All
    # declarations, native signatures and other nonempty residual text are exact.
    nonempty = lambda text: [line for line in text.splitlines() if line.strip()]
    require(nonempty(residual(view)) == nonempty(expected_residual(baseline)), 'C globals/native/residual text changed')
    evaluator = JassScalarEvaluator(script)
    validate_choice_matrix(lambda name, values: evaluator.call(name, list(values.values())))
    validate_compiled_lifecycle(script)
    return {'legacy_functions': len(before), 'added_functions': len(added),
            'insertion_functions': sum(expected[n] != before[n][0] for n in before),
            'diagnostic_relocations': len(diagnostics), 'allocators': len(allocations(script)),
            'type_comparisons': len(TYPE_TEST.findall(script)), 'local_temp_alpha': {}}


def verify_object_delta(current, baseline):
    require(set(current) == set(baseline), 'C object table set changed')
    changed = []
    for kind, old_objects in baseline.items():
        objects = current[kind]
        require(list(objects) == list(old_objects), 'C object set/order changed: ' + kind)
        for code, old in old_objects.items():
            obj = objects[code]
            require((obj.table, obj.identity, list(obj.fields)) == (old.table, old.identity, list(old.fields)), 'C object identity/field order changed: ' + code)
            for key, prior in old.fields.items():
                field = obj.fields[key]
                if kind == 'abilities' and code == 'A131' and key[0] == 'aub1':
                    require(key in [('aub1', level, 0) for level in range(1, 42)] and prior.kind == field.kind == 3,
                            'C A131 tooltip field type/level changed')
                    require(prior.value.endswith(OLD_SUFFIX) and prior.value.count(OLD_SUFFIX) == 1,
                            'B A131 tooltip suffix is not exact')
                    expected = prior.value[:-len(OLD_SUFFIX)] + NEW_SUFFIX
                    require(field.value == expected and field.raw == prior.raw[:16] + expected.encode() + b'\0' + prior.raw[-4:],
                            'C A131 tooltip changed beyond exact suffix')
                    changed.append(key)
                else:
                    require(field == prior, 'C unrelated object field changed: ' + code + '/' + key[0])
    require(changed == [('aub1', level, 0) for level in range(1, 42)], 'C requires exactly 41 A131 tooltip replacements')
    return len(changed)


def validate_closed_bloodlust_delta(current, baseline, current_sources, baseline_sources):
    require(digest(baseline.data) == BASE_MAP_SHA256, 'C requires immutable official B map')
    after, before = members(current), members(baseline)
    require(set(after) == set(before), 'C MPQ resource set changed')
    for key, (old_name, old) in before.items():
        name, data = after[key]
        require(name == old_name, 'C MPQ resource spelling changed')
        if name in ('war3map.w3a', 'war3map.j'):
            continue
        if name == 'war3map.w3i':
            require(normalize_info(data) == normalize_info(old), 'C metadata changed beyond two display timestamps')
        else:
            require(data == old, 'C unrelated resource changed: ' + name)
    fields = verify_object_delta(load_objects(current), load_objects(baseline))
    validate_native_bloodlust(ability_objects(current.extract('war3map.w3a')), tooltips=True)
    proof = prove_jass_delta(current.extract('war3map.j').decode(), baseline.extract('war3map.j').decode(), current_sources, baseline_sources)
    return dict(proof, resources=len(after), tooltip_fields=fields)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map')
    parser.add_argument('--baseline-map', required=True)
    args = parser.parse_args()
    sources, old_sources = read_sources()
    proof = validate_closed_bloodlust_delta(Mpq(Path(args.map).read_bytes()), Mpq(Path(args.baseline_map).read_bytes()), sources, old_sources)
    print('PASS CLOSED C DELTA:', proof)
    print('NOT TESTED: live Warcraft autocast UI/native order timing; no build, deployment or MPQ write performed.')


if __name__ == '__main__':
    main()
