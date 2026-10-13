#!/usr/bin/env python3
"""Fresh source checks and actual packaged native Bloodlust/JASS checks.

Usage: python tools/VerifyBloodlustAutocastArtifact.py --source-only
       python tools/VerifyBloodlustAutocastArtifact.py map.w3x
Source scalar evaluation is a fail-closed inspection, not Wurst compilation.
"""
from pathlib import Path
import math
import re
import sys
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyPetUIArtifact import _integer_expression
from VerifyTowerUpgradeArtifact import JassScalarEvaluator

ROOT = Path(__file__).resolve().parents[1]
ON, OFF = 852102, 852103


def source_body(source, name):
    match = re.search(r'^(?:public )?function ' + re.escape(name) + r'\([^\n]*\)[^\n]*\n((?:\t[^\n]*\n|\n)*)', source, re.M)
    require(match is not None, 'Missing Wurst source function ' + name)
    return match[1]


def evaluate_source_choice(source, name, values):
    """Evaluate the production facade and shared scalar implementation."""
    from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
    sources = read_sources()
    sources['towers/TDTowerBloodlustAutocast.wurst'] = source
    return SourceScalarEvaluator(sources).call(name, list(values.values()))


def validate_choice_matrix(call):
    for choice in range(3):
        for eligible in (False, True):
            expected = 1 if eligible and choice == 0 else choice
            require(call('tdBloodlustChoiceAfterInitialization', {'choice': choice, 'eligible': eligible}) == expected,
                    'Bloodlust first/default/reinitialize rule changed')
            expected_order = (ON if choice == 1 else OFF if choice == 2 else 0) if eligible else 0
            require(call('tdBloodlustOrderForChoice', {'choice': choice, 'eligible': eligible}) == expected_order,
                    'Bloodlust unknown/busy/missing restore rule changed')
            for order in (ON, OFF, 851972, 0):
                for scripted in (False, True):
                    expected = choice
                    if eligible and not scripted:
                        if order == ON:
                            expected = 1
                        elif order == OFF:
                            expected = 2
                    require(call('tdBloodlustChoiceAfterOrder', {'choice': choice, 'orderId': order,
                                                              'eligible': eligible, 'scripted': scripted}) == expected,
                            'Bloodlust manual choice/script writeback rule changed')


def validate_packed_choice_matrix(script):
    """Current compiler output uses generic consumers; old facade matrix stays frozen."""
    evaluator = JassScalarEvaluator(script)
    names = {'tdBloodlustChoiceAfterInitialization': ('tdActiveAutocastChoiceAfterInitialization', [1]),
             'tdBloodlustOrderForChoice': ('tdActiveAutocastOrderForChoice', [ON, OFF]),
             'tdBloodlustChoiceAfterOrder': ('tdActiveAutocastChoiceAfterOrder', [ON, OFF])}
    validate_choice_matrix(lambda name, values: evaluator.call(names[name][0], list(values.values()) + names[name][1]))
    # UNKNOWN must remain unknown for a native whose reviewed default is zero.
    for choice in range(3):
        for eligible in (False, True):
            require(evaluator.call('tdActiveAutocastChoiceAfterInitialization', [choice, eligible, 0]) == choice,
                    'Unknown native default was forced ON')
            for order in (852076, 852077, ON, 0):
                for scripted in (False, True):
                    expected = 1 if eligible and not scripted and order == 852076 else 2 if eligible and not scripted and order == 852077 else choice
                    require(evaluator.call('tdActiveAutocastChoiceAfterOrder', [choice, order, eligible, scripted, 852076, 852077]) == expected,
                            'Independent native manual order choice changed')
            expected = (852076 if choice == 1 else 852077 if choice == 2 else 0) if eligible else 0
            require(evaluator.call('tdActiveAutocastOrderForChoice', [choice, eligible, 852076, 852077]) == expected,
                    'Independent native restore order changed')


def validate_sources(module, equipment, runtime, objects, cooldown_runtime=None, active_data=None):
    from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources, verify_runtime_sources, verify_scalar_rules, definitions
    sources = read_sources()
    sources.update({'towers/TDTowerBloodlustAutocast.wurst': module, 'items/TDEquipmentAbilities.wurst': equipment,
                    'towers/TDTowerRuntime.wurst': runtime, 'items/TDEquipmentObjectGen.wurst': objects})
    if cooldown_runtime is not None: sources['abilities/TDActiveCooldownRuntime.wurst'] = cooldown_runtime
    if active_data is not None: sources['abilities/TDActiveSkillData.wurst'] = active_data
    evaluator = SourceScalarEvaluator(sources)
    validate_choice_matrix(lambda name, values: evaluator.call(name, list(values.values())))
    verify_scalar_rules(evaluator, definitions(evaluator))
    require('constant hashtable tdActiveAutocastChoices = InitHashtable()' in module, 'Autocast needs independent unit+ability choice storage')
    restore = source_body(module, 'tdRestoreNativeActiveAutocast')
    require('saveInt' not in restore and 'tdActiveAutocastChoiceAfterInitialization' not in restore,
            'Restore must not write or initialize choice')
    require(re.search(r'tdBloodlustRestoring = true\n\ttower.issueImmediateOrderById\(orderId\)\n\ttdBloodlustRestoring = false', restore),
            'Restore needs synchronous script-order guard')
    require('loadInt(tower.getHandleId(), abilityId)' in restore and 'active.autocastOnOrder' in restore and 'active.autocastOffOrder' in restore,
            'Restore must read independent metadata-driven unit+ability choice')
    listener = source_body(module, 'tdHandleBloodlustAutocastOrder')
    require(listener.startswith('\tif tdBloodlustRestoring\n\t\treturn\n'), 'Listener must skip script writeback')
    require('issueImmediateOrder' not in listener and 'tdRestoreNativeActiveAutocast' not in listener, 'Listener must only save choice')
    for token in ('tdActiveSkillDefinitionCount()', 'tdActiveSkillDefinitionAt(index)', 'saveInt(key, active.abilityId, choice)', 'GetIssuedOrderId()'):
        require(token in listener, 'Listener must record explicit generic manual choice: ' + token)
    eligible = source_body(module, 'tdNativeActiveAutocastEligible')
    require('saveInt' not in eligible and 'flushChild' not in eligible and 'tdForgetBloodlust' not in eligible, 'Busy/missing eligibility must retain choice')
    for token in ('tower == null', 'not tower.isAlive()', 'getAbilityLevel(abilityId)', 'tdPetBusyTowers.hasBoolean', 'tdActiveSkillDefinitionForAbility(abilityId)'):
        require(token in eligible, 'Eligibility missing ' + token)
    require('EVENT_PLAYER_UNIT_ISSUED_ORDER' in module, 'Missing manual-order registration')
    require('tdSetupBloodlustAutocastOrders()' in runtime, 'Missing order setup entry')
    require(runtime.count('tdInitializeBloodlustAutocast(tower)') == 3, 'Initialization must have only three stable entrypoints')
    for name in ('tdHandleTowerConstructionFinished', 'tdHandleTowerUpgradeFinished', 'tdHandleTowerUpgradeCancelled'):
        body = source_body(runtime, name)
        require('tdInitializeBloodlustAutocast(tower)' in body, name + ': stable init missing')
        require(body.index('tdRefreshTowerEquipmentBonuses') < body.index('tdInitializeBloodlustAutocast'), name + ': initialize after equipment refresh')
    cancel = source_body(runtime, 'tdHandleTowerUpgradeCancelled')
    require(cancel.count('doAfter(0.0)') == 1 and 'finishWorkForGeneration(cancelledGeneration)' in cancel, 'Cancel must reuse existing zero-tick generation guard')
    require(cancel.index('finishWorkForGeneration') < cancel.index('tdInitializeBloodlustAutocast'), 'Cancel generation guard must precede init')
    for name in ('tdHandleTowerSellCast', 'tdRejectTowerConstruction', 'tdHandleTowerConstructionCancelled', 'tdHandleTowerDeath'):
        require('tdForgetBloodlustAutocast(tower)' in source_body(runtime, name), name + ': choice cleanup missing')
    require('tdForgetBloodlustAutocast' not in source_body(runtime, 'tdHandleTowerUpgradeStarted'), 'Upgrade start must retain choice')
    require('tdForgetBloodlustAutocast' not in source_body(equipment, 'tdForgetEquipmentAbilities'), 'Cooldown deletion must retain choice')
    require('tdActiveAutocastChoices.flushChild(key)' in source_body(module, 'tdForgetBloodlustChoiceKey'), 'Retirement must erase all handle+ability choices')
    verify_runtime_sources(evaluator)
    require('获得时默认开启，可手动关闭' in source_body(objects, 'tdConfigureEquipmentBloodlust'), 'A131 tooltip needs default/manual choice')


def validate_native_bloodlust(abilities, tooltips=False):
    require('A131' in abilities, 'Missing A131')
    parent, fields = abilities['A131']
    require(parent == 'Ablo', 'A131 must retain Ablo parent')
    require(fields.get(('alev', 0, 0)) == (0, 41), 'A131 must retain 41 levels')
    for level in range(1, 42):
        kind, cooldown = fields.get(('acdn', level, 0), (None, None))
        require(kind == 2 and isinstance(cooldown, (int, float)) and
                math.isclose(cooldown, 12 * (1 - (level - 1) / 100), rel_tol=1e-6), f'A131 cooldown changed at {level}')
        require(fields.get(('abuf', level, 0)) == (3, 'Bblo'), f'A131 Bblo missing at {level}')
        if tooltips:
            text = fields.get(('aub1', level, 0), (None, ''))[1]
            require('获得时默认开启' in text and '可手动关闭' in text, f'A131 tooltip missing default/manual choice at {level}')


def validate_compiled_lifecycle(script):
    bodies = {m[1]: m[2] for m in re.finditer(r'^function (\w+) takes[^\n]*\n(.*?)^endfunction', script, re.M | re.S)}
    def body(name):
        require(name in bodies, 'Missing packaged function ' + name)
        return bodies[name]
    def calls(value, name): return len(re.findall(r'\bcall\s+' + re.escape(name) + r'\(', value))
    restore = body('tdRestoreNativeActiveAutocast')
    require('tdActiveAutocastChoices' in restore and re.search(r'loadInt|LoadInteger', restore), 'Packaged restore must read independent unit+ability choice')
    require('saveInt' not in restore and 'SaveInteger' not in restore, 'Packaged restore must not write choice')
    require(re.search(r'set \w*tdBloodlustRestoring = true[\s\S]*call unit_issueImmediateOrderById\([^\n]*\)[\s\S]*set \w*tdBloodlustRestoring = false', restore), 'Packaged sync guard missing')
    listener = body('tdHandleBloodlustAutocastOrder')
    require(re.search(r'if \w*tdBloodlustRestoring then(?:(?!endif)[\s\S])*?\breturn\s+endif', listener), 'Packaged listener script guard missing')
    require(re.search(r'saveInt|SaveInteger', listener) and 'GetIssuedOrderId' in listener and 'issueImmediateOrder' not in listener, 'Packaged listener must only save manual order')
    for token in ('tdActiveSkillDefinitionCount', 'tdActiveSkillDefinitionAt', 'autocastOnOrder', 'autocastOffOrder'):
        require(token in listener, 'Packaged listener missing generic metadata ' + token)
    require('EVENT_PLAYER_UNIT_ISSUED_ORDER' in body('tdSetupBloodlustAutocastOrders'), 'Packaged order registration missing')
    require('tdSetupBloodlustAutocastOrders' in body('tdSetupDialogTrigger'), 'Packaged setup call missing')
    for name in ('tdHandleTowerConstructionFinished', 'tdHandleTowerUpgradeFinished'):
        require(calls(body(name), 'tdInitializeBloodlustAutocast') == 1, name + ': init missing')
    cancel = [value for value in bodies.values() if 'finishWorkForGeneration' in value and 'tdInitializeBloodlustAutocast' in value]
    require(len(cancel) == 1, 'Packaged cancel must initialize inside generation-guarded callback')
    for token in ('unit_isAlive', 'cancelledGeneration', 'tdTowerSaleStates'): require(token in cancel[0], 'Packaged cancel missing ' + token)
    require(cancel[0].index('finishWorkForGeneration') < cancel[0].index('tdInitializeBloodlustAutocast'), 'Packaged cancel generation ordering wrong')
    require(sum(calls(value, 'tdInitializeBloodlustAutocast') for value in bodies.values()) == 3, 'Packaged initialization escaped stable sites')
    apply = body('tdApplyNativeActiveCooldownLevel')
    require(calls(apply, 'tdRestoreNativeActiveAutocast') == 1 and 'call unit_setAbilityLevel' in apply and apply.index('call unit_setAbilityLevel') < apply.index('call tdRestoreNativeActiveAutocast'), 'Packaged generic restore must follow actual setter')
    require('TDActiveNativeCooldownState_needsLevel' in apply, 'Packaged same-level/busy/deadline guard missing')
    require('readyAt' not in body('TDActiveNativeCooldownState_requestLevel'), 'Packaged refresh changed expiry')
    require('tdApplyNativeActiveCooldownLevel' in body('tdRefreshNativeActiveCooldowns'), 'Packaged direct refresh must share native apply')
    delayed = [value for name, value in bodies.items() if name.startswith('call_doPeriodically_TDActiveCooldownRuntime')]
    require(len(delayed) == 1 and 'tdApplyNativeActiveCooldownLevel' in delayed[0], 'Packaged delayed refresh must share one existing timer/apply')
    require('SetUnitAbilityLevel' in body('unit_setAbilityLevel'), 'Level wrapper must reach native setter')
    require('IssueImmediateOrderById' in body('unit_issueImmediateOrderById'), 'Order wrapper must reach native order')
    for name in ('tdHandleTowerSellCast', 'tdRejectTowerConstruction', 'tdHandleTowerConstructionCancelled', 'tdHandleTowerDeath'):
        require(calls(body(name), 'tdForgetBloodlustAutocast') == 1, name + ': packaged cleanup missing')
    require(re.search(r'flushChild|FlushChildHashtable', body('tdForgetBloodlustChoiceKey')), 'Packaged retirement must erase state')
    require('tdForgetBloodlustAutocast' not in body('tdForgetEquipmentAbilities'), 'Packaged CD deletion must retain choice')


def main():
    require(len(sys.argv) == 2, __doc__)
    if sys.argv[1] == '--source-only':
        validate_sources(*[(ROOT / path).read_text() for path in
                           ('wurst/towers/TDTowerBloodlustAutocast.wurst', 'wurst/items/TDEquipmentAbilities.wurst',
                            'wurst/towers/TDTowerRuntime.wurst', 'wurst/items/TDEquipmentObjectGen.wurst')])
        print('PASS STATIC SOURCE: scalar matrix and choice/listener/restore/lifecycle wiring; not Wurst compilation.')
        return
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    validate_native_bloodlust(ability_objects(artifact.extract('war3map.w3a')), tooltips=True)
    script = artifact.extract('war3map.j').decode('utf-8')
    validate_packed_choice_matrix(script)
    validate_compiled_lifecycle(script)
    print('PASS ARTIFACT: A131 Ablo/41 levels/Bblo; actual scalar rules and lifecycle/restore chain.')
    print('NOT TESTED: live Warcraft 1.27a autocast, native order UI or timing.')


if __name__ == '__main__':
    main()
