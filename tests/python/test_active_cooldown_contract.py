"""Production-source evaluation and synthetic mutation tests, never a build.

Objects below are constructed fixtures. No test labels an old ExampleMap as
new universal-cooldown MPQ evidence or launches Wurst/Grill/Warcraft.
"""
from copy import deepcopy
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyActiveCooldownContract as v

# Independent excerpt from wurst/_wurst/Orders.wurst at the repository's
# locked stdlib tree 90b45617eda50c15703e8cb2ec3241d3c7b61816. When that checkout
# is available, the regression reads the real file instead of this excerpt.
LOCKED_ORDERS_REFERENCE = '''package Orders
public class Orders
    static constant bloodlustoff = 852103
    static constant bloodluston = 852102
    static constant innerfireoff = 852068
    static constant innerfireon = 852067
    static constant slowoff = 852077
    static constant slowon = 852076
'''


def replace_once(sources, path, old, new):
    require = unittest.TestCase().assertIn
    require(old, sources[path], 'Mutation target must exist')
    sources[path] = sources[path].replace(old, new, 1)


def extended_sources():
    sources = v.read_sources()
    marker = '\treturn tdActiveSkillDefinition(0, 0, 0, -1, 0.0, 0, 0, TD_ACTIVE_AUTOCAST_UNKNOWN)'
    extra = ('\tif index == 24\n'
             '\t\treturn tdActiveSkillDefinition(101, TD_ACTIVE_DRIVER_NATIVE_ABILITY, \'Cn03\', -1, 23.0, Orders.innerfireon, Orders.innerfireoff, TD_ACTIVE_AUTOCAST_UNKNOWN)\n'
             '\tif index == 25\n'
             '\t\treturn tdActiveSkillDefinition(102, TD_ACTIVE_DRIVER_PET_PROC, 0, 77, 31.0, 0, 0, TD_ACTIVE_AUTOCAST_UNKNOWN)\n')
    replace_once(sources, v.DATA, '\treturn 24\n', '\treturn 26\n')
    replace_once(sources, v.DATA, marker, extra + marker)
    evaluator = v.SourceScalarEvaluator(sources)
    body = evaluator.body('tdConfigureEquipmentBloodlust')
    body = body.replace('TD_ACTIVE_BLOODLUST', '101')
    sources['abilities/TDThirdNativeFixture.wurst'] = ('package TDThirdNativeFixture\nimport TDActiveSkillData\n'
        'import TDActiveCooldownObjectGen\nimport AbilityObjEditing\n'
        'public function configureThird(AbilityDefinitionBloodlust definition)\n' + body +
        '@compiletime function generateThird()\n'
        '\tlet third = new AbilityDefinitionBloodlust(\'Cn03\')\n'
        '\tconfigureThird(third)\n')
    replace_once(sources, 'towers/TDTowerCatalogData.wurst',
                 'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode()',
                 'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode() + ",Cn03"')
    return sources


def object_fixture(contract):
    evaluator = contract['evaluator']
    parents = v.source_mount_roles(evaluator, contract['towers'], contract['definitions'])
    objects = {code: (parent, {}) for code, parent in parents.items()}
    for name in evaluator.constants:
        if name.startswith(('TD_TOWER_EQUIPMENT_', 'TD_PET_')) and name.endswith(('_ABILITY_ID', '_BONUS_ID')):
            try:
                value = evaluator.constant(name)
                if isinstance(value, int) and value > 0xffffff:
                    objects.setdefault(v.rawstring(value), ('AOcr', {}))
            except ValueError:
                pass
    for code, definition in ((v.rawstring(d.abilityId), d) for d in contract['definitions'] if d.abilityId):
        parent, fields = deepcopy(contract['native_objects'][code])
        fields['alev', 0, 0] = 0, 41
        for level in range(1, 42):
            fields['acdn', level, 0] = 2, evaluator.call('tdActiveCooldownDuration', [definition.baseCooldown, (level - 1) / 100])
        objects[code] = parent, fields
    for parent, fields in objects.values():
        if parent == 'ANcl': fields['acdn', 1, 0] = 2, 0.0
    inventory = v.rawstring(evaluator.constant('TD_TOWER_INVENTORY_ABILITY_ID'))
    objects[inventory][1]['inv3', 1, 3] = 0, 0
    units = {code: {'uabi': ','.join(abilities)} for code, abilities in contract['towers'].items()}
    items = {v.rawstring(evaluator.expression(args[0], {})): {'iusa': 0, 'iabi': ''}
             for args in v.calls(evaluator.body('tdConfiguredEquipment'), 'tdEquipmentDefinition')
             if evaluator.expression(args[0], {})}
    return objects, units, items


def compiled_fixture(contract):
    """Synthetic JASS plumbing with scalar bodies copied from actual Wurst.

    This is a mutation harness, not compiler output. Real map mode separately
    reads war3map.j and runs the full legacy guard gate on that actual script.
    """
    evaluator = contract['evaluator']
    definitions = contract['definitions']
    fields = definitions[0]._fields
    globals_ = ['integer ' + name + ' = ' + str(evaluator.constant(name))
                for name in evaluator.constants if name.startswith('TD_ACTIVE_')]
    globals_ += [('real' if field == 'baseCooldown' else 'integer') + ' tdActiveSkillDefinitionAt_return_' + field for field in fields if field != 'key']
    globals_ += ['integer array TDActiveNativeCooldownState_desiredLevel', 'real array TDActiveNativeCooldownState_readyAt']
    functions = []
    def add(name, signature, result, body):
        functions.append('function ' + name + ' takes ' + signature + ' returns ' + result + '\n' + body + '\nendfunction\n')
    add('tdActiveSkillDefinitionCount', 'nothing', 'integer', '\treturn ' + str(len(definitions)))
    branches = []
    for index, definition in enumerate(definitions):
        branches.append('\tif index == ' + str(index) + ' then')
        branches.extend('\t\tset tdActiveSkillDefinitionAt_return_' + field + ' = ' + str(getattr(definition, field)) for field in fields if field != 'key')
        branches.extend(['\t\treturn ' + str(definition.key), '\tendif'])
    branches.extend('\tset tdActiveSkillDefinitionAt_return_' + field + ' = ' + str(-1 if field == 'petSkillId' else 0) for field in fields if field != 'key')
    branches.append('\treturn 0')
    add('tdActiveSkillDefinitionAt', 'integer index', 'integer', '\n'.join(branches))
    add('tdPetSkillIsActive', 'integer skill', 'boolean',
        '\tlocal integer index = 0\n\tloop\n\t\texitwhen index >= tdActiveSkillDefinitionCount()\n'
        '\t\tcall tdActiveSkillDefinitionAt(index)\n'
        '\t\tif tdActiveSkillDefinitionAt_return_driver == TD_ACTIVE_DRIVER_PET_PROC and tdActiveSkillDefinitionAt_return_petSkillId == skill then\n\t\t\treturn true\n\t\tendif\n'
        '\t\tset index = index + 1\n\tendloop\n\treturn false')
    def copy_scalar(name, signature, result):
        body = evaluator.body(name)
        lines, levels = [], []
        for line in body.splitlines():
            if not line.strip(): continue
            indent = len(line) - len(line.lstrip('\t'))
            while levels and indent <= levels[-1]:
                lines.append('\t' * levels.pop() + 'endif')
            if line.strip().startswith('if '):
                lines.append(line + ' then')
                levels.append(indent)
            else:
                lines.append(line)
        while levels: lines.append('\t' * levels.pop() + 'endif')
        add(name, signature, result, '\n'.join(lines))
    copy_scalar('tdActiveCooldownDuration', 'real baseCooldown, real reduction', 'real')
    copy_scalar('tdActiveCooldownReadyAt', 'real now, real baseCooldown, real reduction', 'real')
    copy_scalar('tdActiveCooldownCanApply', 'real now, real readyAt', 'boolean')
    copy_scalar('tdActiveCooldownNeedsNativeLevel', 'real now, real readyAt, integer actualLevel, integer desiredLevel, boolean busy', 'boolean')
    # Valid-level decode is the exact production return expression; the source
    # guard and all 1..41 decoding cases are checked separately above.
    decode = evaluator.body('tdActiveCooldownReductionAtNativeLevel').strip().splitlines()[-1]
    add('tdActiveCooldownReductionAtNativeLevel', 'integer actualLevel', 'real', decode.replace('physicalLevel', 'actualLevel'))
    for method, signature, result in [('requestLevel', 'integer this, integer nextLevel', 'nothing'),
                                      ('startCast', 'integer this, real now, real baseCooldown, integer actualLevel', 'nothing'),
                                      ('needsLevel', 'integer this, real now, integer actualLevel, boolean busy', 'boolean')]:
        body = evaluator.methods[method, len(signature.split(',')) - 1][1].strip()
        body = re.sub(r'\b(desiredLevel|readyAt)\b', lambda match: 'TDActiveNativeCooldownState_' + match[1] + '[this]', body)
        if not body.startswith('return '): body = 'set ' + body
        add('TDActiveNativeCooldownState_' + method, signature, result, '\t' + body)
    add('new_TDNativeActiveCooldown', 'unit tower, integer abilityId', 'integer', '\tset TDActiveNativeCooldownState_desiredLevel[1] = unit_getAbilityLevel(tower, abilityId)\n\tset TDActiveNativeCooldownState_readyAt[1] = 0.0\n\treturn 1')
    add('tdHasNativeActiveCooldown', 'unit tower', 'boolean', '\tlocal integer count = tdActiveSkillDefinitionCount()\n\treturn unit_getAbilityLevel(tower, tdActiveSkillDefinitionAt(0)) > 0')
    add('tdRefreshNativeActiveCooldowns', 'unit tower, real personalReduction', 'nothing', '\tlocal integer count = tdActiveSkillDefinitionCount()\n\tlocal integer active = tdActiveSkillDefinitionAt(0)\n\tlocal integer actual = unit_getAbilityLevel(tower, active)\n\tcall tdApplyNativeActiveCooldownLevel(1, 0.0)')
    add('tdHostActiveCooldownReduction', 'unit tower', 'real', '\treturn tdFinalCooldownReduction(0.0, tdPetCooldownReduction(tower), tdAuraPower(tower, 5))')
    add('tdAuraCooldownTargetEligible', 'unit target', 'boolean', '\treturn tdPetBindingValid(1, target, 1) and tdPetUnlockedSlots(1) > 0 and tdPetSkillFitsHost(77, target) and tdPetSkillIsActive(77) and tdHasNativeActiveCooldown(target)')
    add('tdSetupEquipmentAbilities', 'nothing', 'nothing', '\tcall tdSetupNativeActiveCooldowns()')
    add('tdForgetEquipmentAbilities', 'unit tower', 'nothing', '\tcall tdForgetNativeActiveCooldowns(tower)')
    add('tdSetupNativeActiveCooldowns', 'nothing', 'nothing', '\tcall registerAnyUnitEvent(EVENT_PLAYER_UNIT_SPELL_EFFECT)\n\tcall doPeriodically(0.10)')
    add('call_doPeriodically_TDActiveCooldownRuntime_fixture', 'nothing', 'nothing', '\tcall tdApplyNativeActiveCooldownLevel(1, 30.0)')
    add('tdNativeActiveSpellCast', 'nothing', 'nothing', '\tlocal integer key = tdActiveSkillDefinitionForAbility(0)\n\tlocal integer actualLevel = unit_getAbilityLevel(null, key)\n\tcall TDActiveNativeCooldownState_startCast(1, 10.0, 23.0, actualLevel)')
    add('tdApplyNativeActiveCooldownLevel', 'integer record, real now', 'nothing', '\tlocal boolean busy = tdPetBusyTowers()\n\tif not TDActiveNativeCooldownState_needsLevel(record, now, 1, busy) then\n\t\treturn\n\tendif\n\tcall unit_setAbilityLevel(null, 0, 41)\n\tcall tdRestoreNativeActiveAutocast(null, 0)')
    add('tdStartScriptActiveCooldown', 'unit tower, integer key, real now', 'real', '\treturn tdActiveCooldownReadyAt(now, 31.0, tdHostActiveCooldownReduction(tower))')
    return 'globals\n' + '\n'.join(globals_) + '\nendglobals\n' + '\n'.join(functions)


class ActiveSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = v.read_sources()
        cls.contract = v.verify_source(sources=cls.sources)

    def reject(self, path, old, new, reason=None):
        sources = self.sources.copy()
        replace_once(sources, path, old, new)
        with self.assertRaisesRegex(ValueError, reason or '.'):
            v.verify_source(sources=sources)

    def test_current_source_uses_real_definitions_and_consumers(self):
        self.assertEqual(len(self.contract['definitions']), self.contract['evaluator'].call('tdActiveSkillDefinitionCount', []))
        self.assertEqual(len(self.contract['towers']), 35)

    def test_manager_list_zero_cd_role_rejects_positive_cd_or_receiver_rebinding(self):
        self.reject('pets/TDPetObjectGen.wurst', 'presetCooldown(lvl -> 0.0)',
                    'presetCooldown(lvl -> 1.0)', 'zero-CD')
        self.reject('pets/TDPetObjectGen.wurst',
                    '\tlistAbility..setLevels(levels)',
                    '\tlistAbility = new AbilityDefinitionBloodlust(TD_ORC_BLOODLUST_ABILITY_ID)\n\tlistAbility..setLevels(levels)',
                    'receiver rebound')

    def test_manager_list_cannot_configure_native_or_borrow_other_order(self):
        self.reject('pets/TDPetObjectGen.wurst',
                    'variant == 0 ? anchor : new AbilityDefinitionIllidanChannel(tdPetListAbilityId(cell, species, quality, ownedCount))',
                    'new AbilityDefinitionBloodlust(TD_ORC_BLOODLUST_ABILITY_ID)', 'binding changed')
        self.reject('pets/TDPetObjectGen.wurst', 'let order = anchor.getOrderString()',
                    'let order = "bloodlust"', 'binding changed')

    def test_manager_list_role_rejects_unknown_caller_and_true_active_rawcode(self):
        sources = self.sources.copy()
        sources['abilities/TDUnreviewedListCaller.wurst'] = (
            'package TDUnreviewedListCaller\nfunction bypass()\n'
            '\tlistCommand(new AbilityDefinitionBloodlust(TD_ORC_BLOODLUST_ABILITY_ID), 0, "bloodlust", "", "", 2)\n')
        with self.assertRaisesRegex(ValueError, 'outside its exact UI role'):
            v.verify_source(sources=sources)
        self.reject('pets/TDPetData.wurst',
                    "return tdPetHex3Rawcode('L000', index, 2410)",
                    'return TD_ORC_BLOODLUST_ABILITY_ID', 'rawcode escaped')

    def test_manager_list_family_cannot_escape_cell_states_or_mount_on_combat_tower(self):
        self.reject('pets/TDPetObjectGen.wurst', 'for variant = 0 to TD_PET_LIST_VARIANTS - 1',
                    'for variant = 0 to TD_PET_LIST_VARIANTS', 'family changed')
        self.reject('towers/TDTowerCatalogData.wurst', 'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode()',
                    'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode() + ",L000"', 'mounted')

    def test_no_stdlib_fallback_orders_match_independent_locked_reference(self):
        sources = self.sources.copy()
        reference = sources.pop('__stdlib_orders__', LOCKED_ORDERS_REFERENCE)
        # Parse the reference independently. Expected values must never come
        # from verifier.ORDERS or from the evaluator's copied fallback table.
        expected = {name: int(value) for name, value in re.findall(r'\bstatic constant (\w+)\s*=\s*(\d+)', reference)}
        fallback = v.SourceScalarEvaluator(sources)
        for name in ('bloodluston', 'bloodlustoff', 'slowon', 'slowoff', 'innerfireon', 'innerfireoff'):
            self.assertIn(name, expected)
            self.assertEqual(fallback.expression('Orders.' + name, {}), expected[name], name)
        sources['__stdlib_orders__'] = reference
        locked = v.SourceScalarEvaluator(sources)
        self.assertEqual(v.definitions(fallback), v.definitions(locked))

    def test_third_native_and_new_pet_only_change_definition_object_and_mount(self):
        sources = extended_sources()
        self.assertEqual(sources[v.RUNTIME], self.sources[v.RUNTIME])
        self.assertEqual(sources['auras/TDAuraRuntime.wurst'], self.sources['auras/TDAuraRuntime.wurst'])
        self.assertEqual(sources['pets/TDPetRules.wurst'], self.sources['pets/TDPetRules.wurst'])
        contract = v.verify_source(sources=sources)
        evaluator = contract['evaluator']
        self.assertTrue(evaluator.call('tdPetSkillIsActive', [77]))
        self.assertEqual(evaluator.call('tdActiveSkillDefinitionForAbility', [v.rawcode('Cn03')]).baseCooldown, 23)
        self.assertAlmostEqual(evaluator.call('tdActiveCooldownReadyAt', [50, 31, .4]), 68.6)
        self.assertEqual(v.verify_objects(contract, *object_fixture(contract))['native_actives'], 3)

    def test_missing_definition_and_wrong_count_are_rejected(self):
        self.reject(v.DATA, 'if index == 6', 'if index == 66', 'count/enumeration')
        self.reject(v.DATA, '\treturn 24\n', '\treturn 25\n', 'count/enumeration')
        sources = extended_sources()
        replace_once(sources, v.DATA, '\treturn 26\n', '\treturn 24\n')
        with self.assertRaisesRegex(ValueError, 'count/enumeration'): v.verify_source(sources=sources)

    def test_duplicate_key_rawcode_pet_identity_and_nonpositive_cd_are_rejected(self):
        for old, new in [('TD_ACTIVE_BLADESTORM, TD_ACTIVE_DRIVER_NATIVE', 'TD_ACTIVE_BLOODLUST, TD_ACTIVE_DRIVER_NATIVE'),
                         ('TD_ORC_BLADESTORM_ABILITY_ID, -1, 9.0', 'TD_ORC_BLOODLUST_ABILITY_ID, -1, 9.0'),
                         ('0, 12, 14.0', '0, 11, 14.0'), ('-1, 12.0, Orders', '-1, 0.0, Orders')]:
            with self.subTest(mutation=old): self.reject(v.DATA, old, new)

    def test_unknown_driver_orders_and_invalid_unknown_fallback_are_rejected(self):
        self.reject(v.DATA, 'TD_ACTIVE_DRIVER_NATIVE_ABILITY, TD_ORC_BLOODLUST', '99, TD_ORC_BLOODLUST', 'driver')
        self.reject(v.DATA, 'Orders.bloodlustoff', 'Orders.bloodluston', 'orders')
        self.reject(v.DATA, 'tdActiveSkillDefinition(0, 0, 0, -1, 0.0', 'tdActiveSkillDefinition(1, 0, 0, -1, 0.0', 'invalid')

    def test_source_formulas_are_evaluated_and_mutations_fail(self):
        self.reject(v.DATA, 'RMinBJ(0.40, RMaxBJ(0.0, reduction))', 'RMinBJ(0.60, RMaxBJ(0.0, reduction))', 'formula')
        self.reject(v.DATA, 'return now + tdActiveCooldownDuration', 'return now - tdActiveCooldownDuration', 'readyAt')
        self.reject(v.DATA, '* 100.0 + 0.5', '* 100.0 + 0.1', 'rounding')

    def test_independent_cooldown_write_and_object_helper_bypass_are_rejected(self):
        self.reject('items/TDEquipmentObjectGen.wurst', 'tdConfigureActiveNativeCooldown(definition, TD_ACTIVE_BLOODLUST)',
                    'definition.setCooldown(1, 12.0)', 'cooldown write')
        self.reject('towers/TDTowerObjectGen.wurst', 'tdConfigureEquipmentBloodlust(equipmentBloodlust)',
                    'equipmentBloodlust.presetCooldown(lvl -> 12.0)', 'presetCooldown')

    def test_direct_native_mount_and_unknown_inherited_parent_fail(self):
        for constructor in ("new AbilityDefinitionBloodlust('Xnew')", "new AbilityDefinition('Xnew', 'Xpar')"):
            sources = self.sources.copy()
            sources['abilities/TDBypassFixture.wurst'] = 'package TDBypassFixture\n@compiletime function generateBypass()\n\t' + constructor + '\n'
            replace_once(sources, 'towers/TDTowerCatalogData.wurst', 'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode()',
                         'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode() + ",Xnew"')
            with self.subTest(constructor=constructor), self.assertRaisesRegex(ValueError, 'Undefined mounted combat active/unknown parent'):
                v.verify_source(sources=sources)

    def test_undefined_mount_even_without_constructor_is_rejected(self):
        self.reject('towers/TDTowerCatalogData.wurst', 'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode()',
                    'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode() + ",Xnew"', 'Undefined/unresolved mounted')

    def test_direct_native_removal_and_unknown_dynamic_mount_are_rejected(self):
        for statement, reason in [('tower.removeAbility(TD_ORC_BLOODLUST_ABILITY_ID)', 'removal/remount'),
                                  ('UnitRemoveAbility(tower, TD_ORC_BLOODLUST_ABILITY_ID)', 'removal/remount'),
                                  ('tower.setAbilityLevel(TD_ORC_BLOODLUST_ABILITY_ID, 41)', 'bypasses readyAt'),
                                  ('SetUnitAbilityLevel(tower, TD_ORC_BLOODLUST_ABILITY_ID, 41)', 'bypasses readyAt'),
                                  ('tower.setAbilityLevel(unknownDynamicId, 41)', 'Unknown dynamic native level'),
                                  ('tower.addPermanentAbility(unknownDynamicId, 1)', 'Unknown dynamic ability mount'),
                                  ('tower.removeAbility(unknownDynamicId)', 'Unknown dynamic native removal')]:
            sources = self.sources.copy()
            sources['abilities/TDBypassFixture.wurst'] = 'package TDBypassFixture\npublic function bypass(unit tower)\n\t' + statement + '\n'
            with self.subTest(statement=statement), self.assertRaisesRegex(ValueError, reason): v.verify_source(sources=sources)

    def test_native_local_alias_cannot_borrow_an_approved_file_role(self):
        for statement in ('tower.removeAbility(abilityId)', 'UnitRemoveAbility(tower, abilityId)',
                          'tower.setAbilityLevel(abilityId, 41)', 'SetUnitAbilityLevel(tower, abilityId, 41)'):
            sources = self.sources.copy()
            sources['items/TDInventoryRuntime.wurst'] += (
                '\nfunction bypassViaLocalName(unit tower)\n'
                '\tlet abilityId = TD_ORC_BLOODLUST_ABILITY_ID\n\t' + statement + '\n')
            with self.subTest(statement=statement), self.assertRaisesRegex(ValueError, 'Unknown dynamic native'):
                v.verify_source(sources=sources)
        sources = self.sources.copy()
        sources['items/TDInventoryRuntime.wurst'] += (
            '\nclass LocalNameBypass\n\tfunction tdSetTowerEquipmentAbilityLevel(unit tower, int abilityId, int level)\n'
            '\t\ttower.removeAbility(abilityId)\n')
        with self.assertRaisesRegex(ValueError, 'Unknown dynamic native'):
            v.verify_source(sources=sources)

    def test_approved_support_owner_cannot_rebind_its_ability_parameter(self):
        for path, name in [('items/TDInventoryRuntime.wurst', 'tdSetTowerEquipmentAbilityLevel'),
                           ('items/TDEquipmentAbilities.wurst', 'tdEquipmentSyncControl'),
                           ('pets/TDPetCombat.wurst', 'setBonus')]:
            for binding in ('abilityId = TD_ORC_BLOODLUST_ABILITY_ID', 'let abilityId = TD_ORC_BLOODLUST_ABILITY_ID'):
                signature = 'function ' + name + '(unit tower, int abilityId, int level)\n'
                with self.subTest(owner=name, binding=binding):
                    self.reject(path, signature, signature + '\t' + binding + '\n', 'parameter rebound')
        self.reject('items/TDInventoryRuntime.wurst',
                    'function tdSetTowerEquipmentAbilityLevel(unit tower, int abilityId, int level)',
                    'function tdSetTowerEquipmentAbilityLevel(unit tower, int abilityId, int level, int bypass)',
                    'parameter contract changed')

    def test_verified_dynamic_identity_fields_and_roots_cannot_be_rebound(self):
        signature = 'function tdApplyNativeActiveCooldownLevel(TDNativeActiveCooldown record, real now)\n'
        self.reject(v.RUNTIME, signature, signature + '\trecord.abilityId = TD_ORC_BLOODLUST_ABILITY_ID\n', 'record identity')
        self.reject(v.RUNTIME, signature, signature +
                    '\trecord = tdNativeActiveCooldownFor(record.tower, TD_ORC_BLOODLUST_ABILITY_ID)\n', 'parameter rebound')
        self.reject(v.RUNTIME, signature, signature +
                    '\tSetUnitAbilityLevel(record.tower, record.abilityId, 41)\n', 'sole actual native setter')
        for path, old, extra, indent in [
                ('auras/TDAuraState.wurst', 'let carrier = tdAuraRankCarrier(identity, rank)',
                 'carrier = TD_ORC_BLOODLUST_ABILITY_ID', 1),
                ('auras/TDAuraState.wurst', 'let failedBuff = tdAuraBuff(identity, rank)',
                 'failedBuff.buffId = TD_ORC_BLOODLUST_ABILITY_ID', 4),
                ('auras/TDAuraState.wurst', 'let previousCarrier = tdAuraRankCarrier(identity, previousRank)',
                 'previousCarrier = TD_ORC_BLOODLUST_ABILITY_ID', 2),
                ('items/TDEquipmentSpecialState.wurst', 'let obsolete = tdSpecialStageBuff(war, previous)',
                 'obsolete.abilId = TD_ORC_BLOODLUST_ABILITY_ID', 2),
                ('towers/TDTowerEvolutionRuntime.wurst', 'let displayOriginal = tdEvolutionDisplayOriginal(choice, branch)',
                 'displayOriginal = TD_ORC_BLOODLUST_ABILITY_ID', 3)]:
            with self.subTest(role=extra):
                self.reject(path, old, old + '\n' + '\t' * indent + extra, 'role .*rebound')
        self.reject('auras/TDAuraState.wurst', 'let previousCarrier = tdAuraRankCarrier(identity, previousRank)',
                    'let previousCarrier = TD_ORC_BLOODLUST_ABILITY_ID', 'initializer changed')

    def test_support_helper_calls_must_have_resolvable_non_native_ids(self):
        for helper in ('tdSetTowerEquipmentAbilityLevel', 'tdEquipmentSyncControl', 'setBonus'):
            sources = self.sources.copy()
            sources['items/TDInventoryRuntime.wurst'] += (
                '\nfunction bypassViaSupportAlias(unit tower)\n'
                '\tlet abilityId = TD_ORC_BLOODLUST_ABILITY_ID\n'
                '\t' + helper + '(tower, abilityId, 41)\n')
            with self.subTest(helper=helper), self.assertRaisesRegex(ValueError, 'Unresolved dynamic support ability'):
                v.verify_source(sources=sources)

    def test_channel_operation_binds_rawcode_cooldown_and_actual_host_scope(self):
        sources = self.sources.copy()
        replace_once(sources, 'towers/TDTowerObjectGen.wurst',
                     '\tnew ChannelAbilityPreset(TD_TOWER_SELL_ABILITY_ID, 1, true)',
                     "\tnew ChannelAbilityPreset('Cn04', 1, true)\n"
                     '\t..makeUnitSpell(0, 180.0)\n'
                     '\tnew ChannelAbilityPreset(TD_TOWER_SELL_ABILITY_ID, 1, true)')
        replace_once(sources, 'towers/TDTowerCatalogData.wurst',
                     'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode()',
                     'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode() + ",Cn04"')
        with self.assertRaisesRegex(ValueError, 'operation rawcode/cooldown role'):
            v.verify_source(sources=sources)
        # The retired salary rawcode cannot return as a tower-hosted operation.
        self.reject('towers/TDTowerCatalogData.wurst', 'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode()',
                    'return TD_ARCHER_SPLIT_ARROW_ABILITY_ID.toRawCode() + "," + TD_FARMER_WAGE_ABILITY_ID.toRawCode()',
                    'Retired manual/random farmer wage production entry')
        self.reject('towers/TDTowerObjectGen.wurst', '..makeUnitSpell(0, 0.0)',
                    '..makeUnitSpell(0, 180.0)', 'operation rawcode/cooldown role')

    def test_retired_farmer_wage_object_and_hidden_mount_are_rejected(self):
        contract = v.verify_source(sources=self.sources)
        abilities, units, items = object_fixture(contract)
        abilities['A109'] = ('ANcl', {('acdn', 1, 0): (2, 180.0)})
        with self.assertRaisesRegex(ValueError, 'Retired farmer wage'):
            v.verify_objects(contract, abilities, units, items)
        abilities.pop('A109')
        units['wageFixture'] = {'uabi': 'A109'}
        with self.assertRaisesRegex(ValueError, 'Retired farmer wage'):
            v.verify_objects(contract, abilities, units, items)

    def test_class_cooldown_writer_and_direct_object_mount_are_rejected(self):
        sources = self.sources.copy()
        sources['abilities/TDBypassFixture.wurst'] = 'package TDBypassFixture\nclass Bypass\n\tfunction mutate(AbilityDefinition ability)\n\t\tability.setCooldown(1, 10.0)\n'
        with self.assertRaisesRegex(ValueError, 'Unclassified class'): v.verify_source(sources=sources)
        self.reject('towers/TDTowerObjectGen.wurst', 'setNormalAbilities(abilities + ","', 'setNormalAbilities(abilities + ",Xnew,"', 'direct tower ability')
        self.reject('items/TDItemObjectGen.wurst', '..setActivelyUsed(false)', '..setActivelyUsed(true)', 'item active driver')
        self.reject('items/TDItemObjectGen.wurst', 'tdGenerateInventoryAbility(TD_TOWER_INVENTORY_ABILITY_ID, 3, false)',
                    'tdGenerateInventoryAbility(TD_TOWER_INVENTORY_ABILITY_ID, 3, true)', 'inventory source')

    def test_native_evolution_replacement_is_rejected_before_build(self):
        self.reject('towers/TDTowerEvolutionRuntime.wurst', 'return TD_ORC_PERFECT_CRIT_ABILITY_ID', 'return TD_ORC_BLOODLUST_ABILITY_ID', 'replacement/remount')

    def test_runtime_and_aura_old_eligibility_lists_are_rejected(self):
        self.reject(v.RUNTIME, 'active.driver == TD_ACTIVE_DRIVER_NATIVE_ABILITY and tower.getAbilityLevel(active.abilityId) > 0',
                    'tower.getAbilityLevel(TD_ORC_BLOODLUST_ABILITY_ID) > 0 or tower.getAbilityLevel(TD_ORC_BLADESTORM_ABILITY_ID) > 0', 'metadata-driven|whitelist')
        self.reject('auras/TDAuraRuntime.wurst', 'tdPetSkillIsActive(skill)', 'skill >= 11 and skill <= 15', 'whitelist')
        self.reject('pets/TDPetRules.wurst', 'tdActiveSkillDefinitionForPetSkill(skill).driver == TD_ACTIVE_DRIVER_PET_PROC', 'skill >= 11 and skill <= 15')

    def test_pet_readyat_bypass_duplicate_aura_and_missing_binding_slot_fit_fail(self):
        self.reject('pets/TDPetCombat.wurst', 'pet.readyAt = tdStartScriptActiveCooldown(host, tdActiveSkillDefinitionForPetSkill(activeSkill).key, getElapsedGameTime())',
                    'pet.readyAt = getElapsedGameTime() + 10.0', 'bypasses shared')
        self.reject(v.RUNTIME, 'tdAuraPower(tower, TD_AURA_EQUIPMENT_COOLDOWN))',
                    'tdAuraPower(tower, TD_AURA_EQUIPMENT_COOLDOWN) + tdAuraPower(tower, TD_AURA_EQUIPMENT_COOLDOWN))', 'once|Duplicate')
        self.reject('auras/TDAuraRules.wurst', 'RMaxBJ(0.0, aura)', 'RMaxBJ(0.0, aura) * 2.0', 'aggregate once')
        for old, new in [('tdPetBindingValid(pet, target, pet.generation)', 'true'),
                         ('tdPetUnlockedSlots(pet.level)', 'pet.skillCount'),
                         ('tdPetSkillFitsHost(skill, target)', 'true')]:
            with self.subTest(guard=old): self.reject('auras/TDAuraRuntime.wurst', old, new, 'guard')

    def test_native_readyat_actuallevel_busy_samelevel_and_one_timer_are_guarded(self):
        self.reject(v.DATA, 'tdActiveCooldownReductionAtNativeLevel(actualLevel)', 'tdActiveCooldownReductionAtNativeLevel(desiredLevel)', 'actual physical')
        self.reject(v.DATA, 'desiredLevel = nextLevel', 'desiredLevel = nextLevel\n\t\treadyAt = 0.0', 'retain readyAt')
        self.reject(v.RUNTIME, 'if not record.needsLevel(now, actualLevel, busy)', 'if false', 'bypasses expiry')
        self.reject(v.RUNTIME, 'doPeriodically(0.10)', 'doPeriodically(0.05)', 'one native')
        self.reject(v.OBJECT, 'definition.getLevels() != 1', 'definition.getLevels() < 1', 'object contract')

    def test_unknown_spell_registration_is_rejected(self):
        sources = self.sources.copy()
        sources['abilities/TDBypassFixture.wurst'] = "package TDBypassFixture\npublic function unknown()\n\tregisterSpellEffectEvent('Xnew', function unknown)\n"
        with self.assertRaisesRegex(ValueError, 'Unknown spell registration owner'): v.verify_source(sources=sources)

    def test_comments_cannot_forge_missing_contracts(self):
        self.reject('auras/TDAuraRuntime.wurst', 'tdPetSkillFitsHost(skill, target)', 'true /* tdPetSkillFitsHost(skill, target) */', 'guard')

    def test_cli_source_only_explicitly_disclaims_compilation_and_new_mpq(self):
        result = subprocess.run([sys.executable, str(ROOT / 'tools/VerifyActiveCooldownContract.py'), '--source-only'], capture_output=True, text=True, check=True)
        self.assertIn('PASS SOURCE', result.stdout)
        self.assertIn('NOT EXECUTED: Wurst compilation/tests, new MPQ/JASS', result.stdout)


class ProductionNativeStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.evaluator = v.SourceScalarEvaluator(v.read_sources())

    def test_real_state_methods_lock_actual_cast_then_refresh_only_next_cast(self):
        e = self.evaluator
        state = {'desiredLevel': 0, 'readyAt': 0.0}
        e.call_state_method('construct', state, [1])
        e.call_state_method('requestLevel', state, [41])
        e.call_state_method('startCast', state, [10, 23, 1])
        self.assertEqual(state['readyAt'], 33)
        # Aura/item/inspiration transitions all reach the same production
        # requestLevel method; no Python state-transition formula is mirrored.
        for level in (19, 1, 25, 41, 13, 1, 41):
            e.call_state_method('requestLevel', state, [level])
            self.assertEqual(state['readyAt'], 33)
            self.assertFalse(e.call_state_method('needsLevel', state, [32.99, 1, False]))
        self.assertFalse(e.call_state_method('needsLevel', state, [33, 1, True]))
        self.assertFalse(e.call_state_method('needsLevel', state, [33, 0, False]))
        self.assertFalse(e.call_state_method('needsLevel', state, [33, 41, False]))
        self.assertTrue(e.call_state_method('needsLevel', state, [33, 1, False]))
        e.call_state_method('startCast', state, [34, 23, 41])
        self.assertAlmostEqual(state['readyAt'], 47.8)

    def test_mutated_state_guard_is_executed_not_shadowed_by_python_model(self):
        sources = v.read_sources()
        replace_once(sources, v.DATA, 'actualLevel == desiredLevel', 'actualLevel != desiredLevel')
        e = v.SourceScalarEvaluator(sources)
        self.assertTrue(e.call_state_method('needsLevel', {'desiredLevel': 1, 'readyAt': 10}, [11, 1, False]))


class SyntheticPackagedObjectMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = v.verify_source(sources=extended_sources())
        cls.fixture = object_fixture(cls.contract)

    def test_complete_synthetic_objects_for_three_native_actives_pass(self):
        self.assertEqual(v.verify_objects(self.contract, *deepcopy(self.fixture))['native_actives'], 3)

    def test_every_native_physical_cooldown_level_is_required(self):
        for code in self.contract['native_objects']:
            for level in range(1, 42):
                objects, units, items = deepcopy(self.fixture)
                del objects[code][1]['acdn', level, 0]
                with self.subTest(code=code, level=level), self.assertRaisesRegex(ValueError, 'incomplete cooldown'):
                    v.verify_objects(self.contract, objects, units, items)

    def test_mana_target_buff_range_effect_duration_and_parent_mutations_fail(self):
        for field, wrong in [('amcs', (0, 1)), ('atar', (3, 'self')), ('abuf', (3, '')), ('aran', (2, 123.)), ('Blo1', (2, .99)), ('adur', (2, 1.))]:
            objects, units, items = deepcopy(self.fixture)
            column = 1 if field == 'Blo1' else 0
            objects['Cn03'][1][field, 41, column] = wrong
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'non-CD effect'): v.verify_objects(self.contract, objects, units, items)
        objects, units, items = deepcopy(self.fixture)
        objects['Cn03'] = 'Xpar', objects['Cn03'][1]
        with self.assertRaisesRegex(ValueError, 'native parent'): v.verify_objects(self.contract, objects, units, items)

    def test_inherited_positive_or_unknown_parent_without_acdn_is_not_zero(self):
        for parent in ('Ablo', 'Aslo', 'Xpar'):
            contract = dict(self.contract)
            contract['towers'] = deepcopy(contract['towers'])
            host = next(iter(contract['towers']))
            contract['towers'][host].append('Xnew')
            objects, units, items = deepcopy(self.fixture)
            units[host]['uabi'] += ',Xnew'
            objects['Xnew'] = parent, {}
            with self.subTest(parent=parent), self.assertRaisesRegex(ValueError, 'Unknown mounted parent/inherited CD'):
                v.verify_objects(contract, objects, units, items)

    def test_explicit_positive_cd_on_passive_parent_is_rejected(self):
        objects, units, items = deepcopy(self.fixture)
        code = next(code for code, (parent, _) in objects.items() if parent == 'AOcr')
        objects[code][1]['acdn', 1, 0] = 2, 5.
        with self.assertRaisesRegex(ValueError, 'Undefined mounted combat active'): v.verify_objects(self.contract, objects, units, items)

    def test_missing_object_unreachable_host_and_item_active_are_rejected(self):
        objects, units, items = deepcopy(self.fixture)
        del objects['Cn03']
        with self.assertRaisesRegex(ValueError, 'no packaged object'): v.verify_objects(self.contract, objects, units, items)
        objects, units, items = deepcopy(self.fixture)
        next(iter(items.values()))['iusa'] = 1
        with self.assertRaisesRegex(ValueError, 'item active driver unsupported'): v.verify_objects(self.contract, objects, units, items)
        objects, units, items = deepcopy(self.fixture)
        next(iter(items.values()))['iabi'] = 'Cn03'
        with self.assertRaisesRegex(ValueError, 'item active driver unsupported'): v.verify_objects(self.contract, objects, units, items)

    def test_inventory_use_and_additional_physical_effect_growth_are_rejected(self):
        objects, units, items = deepcopy(self.fixture)
        code = v.rawstring(self.contract['evaluator'].constant('TD_TOWER_INVENTORY_ABILITY_ID'))
        objects[code][1]['inv3', 1, 3] = 0, 1
        with self.assertRaisesRegex(ValueError, 'inventory'): v.verify_objects(self.contract, objects, units, items)
        objects, units, items = deepcopy(self.fixture)
        for level in range(1, 42): objects['Cn03'][1]['Data', level, 9] = 2, float(level)
        with self.assertRaisesRegex(ValueError, 'changed non-CD'): v.verify_objects(self.contract, objects, units, items)


class SyntheticCompiledMutationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = v.verify_source(sources=extended_sources())
        cls.script = compiled_fixture(cls.contract)

    def test_synthetic_tuple_scalar_state_and_call_chain_fixture_passes(self):
        v.verify_compiled_core(self.contract, self.script)

    def test_synthetic_debug_stack_argument_and_compiler_spacing_keep_strict_actual_level(self):
        diagnostic = '"when calling tdActiveCooldownReductionAtNativeLevel in TDActiveSkillData, line 101"'
        script = self.script.replace('tdActiveCooldownReductionAtNativeLevel(actualLevel)',
                                     'tdActiveCooldownReductionAtNativeLevel(actualLevel, ' + diagnostic + ')', 1)
        script = script.replace('function tdActiveCooldownReductionAtNativeLevel takes integer actualLevel returns real',
                                'function tdActiveCooldownReductionAtNativeLevel takes integer actualLevel, string w__wurst_stackPos returns real', 1)
        script = script.replace('if not TDActiveNativeCooldownState_needsLevel(',
                                'if  not TDActiveNativeCooldownState_needsLevel(', 1)
        v.verify_compiled_core(self.contract, script)
        with self.assertRaisesRegex(ValueError, 'actual level'):
            v.verify_compiled_core(self.contract, script.replace('actualLevel, ' + diagnostic,
                                   'TDActiveNativeCooldownState_desiredLevel[this], ' + diagnostic, 1))
        with self.assertRaisesRegex(ValueError, 'actual level'):
            v.verify_compiled_core(self.contract, script.replace(diagnostic, 'unknownArgument()', 1))

    def test_synthetic_real_form_orders_initialization_is_executed_and_mutations_rejected(self):
        # Model the observed real compiler form, with zero declarations and a
        # package initializer. These values are the independent locked reference.
        values = {'bloodluston': 852102, 'bloodlustoff': 852103,
                  'slowon': 852076, 'slowoff': 852077}
        script = self.script.replace('endglobals', ''.join(
            'integer Orders_' + name + '=0\n' for name in values) + 'endglobals', 1)
        for name, value in values.items():
            field = 'autocastOnOrder' if name.endswith('on') else 'autocastOffOrder'
            old = 'set tdActiveSkillDefinitionAt_return_' + field + ' = ' + str(value)
            self.assertIn(old, script)
            script = script.replace(old, 'set tdActiveSkillDefinitionAt_return_' + field + ' = Orders_' + name, 1)
        initializer = ('function init_Orders takes nothing returns boolean\n' + ''.join(
            '\tset Orders_' + name + ' = ' + str(value) + '\n' for name, value in values.items()) + '\treturn true\nendfunction\n')
        script += initializer
        v.verify_compiled_core(self.contract, script)
        with self.assertRaisesRegex(ValueError, 'tuple differs'):
            v.verify_compiled_core(self.contract, script.replace('set Orders_bloodluston = 852102', 'set Orders_bloodluston = 852101', 1))
        with self.assertRaisesRegex(ValueError, 'Missing packaged Orders initialization'):
            v.verify_compiled_core(self.contract, script.replace(initializer, ''))

    def test_compiled_metadata_and_scalar_mutations_fail(self):
        for old, new, reason in [('return 26\n', 'return 24\n', 'active count'),
                                 ('tdActiveSkillDefinitionAt_return_baseCooldown = 23.0', 'tdActiveSkillDefinitionAt_return_baseCooldown = 24.0', 'tuple differs'),
                                 ('RMinBJ(0.40, RMaxBJ(0.0, reduction))', 'RMinBJ(0.60, RMaxBJ(0.0, reduction))', 'scalar duration')]:
            self.assertIn(old, self.script)
            with self.subTest(mutation=old), self.assertRaisesRegex(ValueError, reason):
                v.verify_compiled_core(self.contract, self.script.replace(old, new, 1))

    def test_compiled_actuallevel_refresh_busy_init_timer_restore_mutations_fail(self):
        cases = [('tdActiveCooldownReductionAtNativeLevel(actualLevel)', 'tdActiveCooldownReductionAtNativeLevel(TDActiveNativeCooldownState_desiredLevel[this])', 'actual level'),
                 ('set TDActiveNativeCooldownState_desiredLevel[this] = nextLevel', 'set TDActiveNativeCooldownState_desiredLevel[this] = nextLevel\n\tset TDActiveNativeCooldownState_readyAt[this] = 0.0', 'refresh reset'),
                 ('if not TDActiveNativeCooldownState_needsLevel(record, now, 1, busy) then', 'if false then', 'bypasses busy'),
                 ('call tdSetupNativeActiveCooldowns()', 'call obsoleteSetup()', 'runtime init'),
                 ('doPeriodically(0.10)', 'doPeriodically(0.05)', 'timer period'),
                 ('call unit_setAbilityLevel(null, 0, 41)', 'call unit_setAbilityLevel(null, 0, 41)\n\tcall SetUnitAbilityLevel(null, 0, 19)', 'set/restore'),
                 ('call tdRestoreNativeActiveAutocast(null, 0)', 'call obsoleteRestore(null, 0)', 'set/restore')]
        for old, new, reason in cases:
            self.assertIn(old, self.script)
            with self.subTest(mutation=old), self.assertRaisesRegex(ValueError, reason):
                v.verify_compiled_core(self.contract, self.script.replace(old, new, 1))

    def test_compiled_legacy_aura_whitelist_and_missing_binding_fail(self):
        for old, new, reason in [('tdPetBindingValid(1, target, 1)', 'true', 'aura guard'),
                                 ('tdPetUnlockedSlots(1)', '1', 'aura guard'),
                                 ('return unit_getAbilityLevel(tower, tdActiveSkillDefinitionAt(0)) > 0', 'return unit_getAbilityLevel(tower, TD_ORC_BLOODLUST_ABILITY_ID) > 0', 'generic native|whitelist')]:
            with self.subTest(mutation=old), self.assertRaisesRegex(ValueError, reason):
                v.verify_compiled_core(self.contract, self.script.replace(old, new, 1))


if __name__ == '__main__': unittest.main()
