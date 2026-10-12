"""Immutable official B + independently declared synthetic C read-only negatives.

The synthetic archive is a decoder facade; no MPQ bytes are edited/written.
The optional observed-C check is restricted to its exact artifact digest, so a
future unrelated stage cannot become this suite's historical fixture truth.
"""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import re
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyDamageRankingJass import functions
from VerifySemanticIconArtifact import load_objects
from VerifyBloodlustAutocastArtifact import source_body
from VerifyBloodlustDiagnostics import DIAGNOSTIC, source_line_maps
import VerifyBloodlustDelta as gate

# Independently declared approved source semantics, not current artifact JASS.
MODULE = '''package TDTowerBloodlustAutocast
import Table
import Orders
import RegisterEvents
import TDTowerData
import TDPetState

public constant int TD_BLOODLUST_CHOICE_UNKNOWN = 0
public constant int TD_BLOODLUST_CHOICE_ON = 1
public constant int TD_BLOODLUST_CHOICE_OFF = 2
constant Table tdBloodlustChoices = new Table()
boolean tdBloodlustRestoring = false
boolean tdBloodlustOrderEventsReady = false
trigger tdBloodlustOrderTrigger = CreateTrigger()

public function tdBloodlustChoiceAfterInitialization(int choice, boolean eligible) returns int
	if not eligible
		return choice
	if choice == TD_BLOODLUST_CHOICE_UNKNOWN
		return TD_BLOODLUST_CHOICE_ON
	return choice

public function tdBloodlustChoiceAfterOrder(int choice, int orderId, boolean eligible, boolean scripted) returns int
	if not eligible
		return choice
	if scripted
		return choice
	if orderId == Orders.bloodluston
		return TD_BLOODLUST_CHOICE_ON
	if orderId == Orders.bloodlustoff
		return TD_BLOODLUST_CHOICE_OFF
	return choice

public function tdBloodlustOrderForChoice(int choice, boolean eligible) returns int
	if not eligible
		return 0
	if choice == TD_BLOODLUST_CHOICE_ON
		return Orders.bloodluston
	if choice == TD_BLOODLUST_CHOICE_OFF
		return Orders.bloodlustoff
	return 0

function tdBloodlustAutocastEligible(unit tower) returns boolean
	if tower == null
		return false
	if not tower.isAlive()
		return false
	if GetUnitTypeId(tower) != TD_ORC_LEVEL_6_A_ID
		return false
	if tower.getAbilityLevel(TD_ORC_BLOODLUST_ABILITY_ID) == 0
		return false
	if tdPetBusyTowers.hasBoolean(tower.getHandleId())
		return false
	return true

public function tdRestoreBloodlustAutocast(unit tower)
	if tdBloodlustRestoring
		return
	if not tdBloodlustAutocastEligible(tower)
		return
	let orderId = tdBloodlustOrderForChoice(tdBloodlustChoices.loadInt(tower.getHandleId()), true)
	if orderId == 0
		return
	tdBloodlustRestoring = true
	tower.issueImmediateOrderById(orderId)
	tdBloodlustRestoring = false

public function tdInitializeBloodlustAutocast(unit tower)
	if not tdBloodlustAutocastEligible(tower)
		return
	let key = tower.getHandleId()
	let choice = tdBloodlustChoiceAfterInitialization(tdBloodlustChoices.loadInt(key), true)
	tdBloodlustChoices.saveInt(key, choice)
	tdRestoreBloodlustAutocast(tower)

function tdForgetBloodlustChoiceKey(int key)
	tdBloodlustChoices.removeInt(key)

public function tdForgetBloodlustAutocast(unit tower)
	if tower != null
		tdForgetBloodlustChoiceKey(tower.getHandleId())

function tdHandleBloodlustAutocastOrder()
	if tdBloodlustRestoring
		return
	let tower = GetTriggerUnit()
	if not tdBloodlustAutocastEligible(tower)
		return
	let orderId = GetIssuedOrderId()
	if orderId != Orders.bloodluston
		if orderId != Orders.bloodlustoff
			return
	let key = tower.getHandleId()
	let choice = tdBloodlustChoiceAfterOrder(tdBloodlustChoices.loadInt(key), orderId, true, false)
	tdBloodlustChoices.saveInt(key, choice)

public function tdSetupBloodlustAutocastOrders()
	if tdBloodlustOrderEventsReady
		return
	tdBloodlustOrderEventsReady = true
	tdBloodlustOrderTrigger.registerAnyUnitEvent(EVENT_PLAYER_UNIT_ISSUED_ORDER)
	tdBloodlustOrderTrigger.addAction(function tdHandleBloodlustAutocastOrder)
'''


def change_source_function(text, name, old, new):
    body = source_body(text, name)
    return text.replace(body, gate.replace_once(body, old, new), 1)


def synthetic_sources(before):
    sources = dict(before, TDTowerBloodlustAutocast=MODULE)
    equipment = sources['TDEquipmentAbilities'].replace('import TDState\n', 'import TDState\nimport TDTowerBloodlustAutocast\n')
    name = 'tdEquipmentSyncCooldown'
    anchor = '\trecord.desiredLevel = desiredLevel\n'
    equipment = change_source_function(equipment, name, anchor, anchor + '\tif abilityId == TD_ORC_BLOODLUST_ABILITY_ID\n\t\tif tower.getAbilityLevel(abilityId) == desiredLevel\n\t\t\treturn\n')
    anchor = '\t\ttower.setAbilityLevel(abilityId, desiredLevel)\n'
    equipment = change_source_function(equipment, name, anchor, anchor + '\t\tif abilityId == TD_ORC_BLOODLUST_ABILITY_ID\n\t\t\ttdRestoreBloodlustAutocast(tower)\n')
    anchor = '\t\t\t\t\trecord.tower.setAbilityLevel(record.abilityId, record.desiredLevel)\n'
    equipment = change_source_function(equipment, 'tdSetupEquipmentAbilities', anchor, anchor + '\t\t\t\t\tif record.abilityId == TD_ORC_BLOODLUST_ABILITY_ID\n\t\t\t\t\t\ttdRestoreBloodlustAutocast(record.tower)\n')
    sources['TDEquipmentAbilities'] = equipment
    runtime = sources['TDTowerRuntime'].replace('import TDDamageRuntime\n', 'import TDDamageRuntime\nimport TDTowerBloodlustAutocast\n')
    for name in ('tdHandleTowerSellCast', 'tdRejectTowerConstruction', 'tdHandleTowerConstructionCancelled', 'tdHandleTowerDeath'):
        anchor = '\ttdForgetEquipmentAbilities(tower)\n'
        runtime = change_source_function(runtime, name, anchor, anchor + '\ttdForgetBloodlustAutocast(tower)\n')
    for name, anchor in [('tdHandleTowerConstructionFinished', '\ttdRefreshTowerEquipmentBonuses(tower)\n'),
                         ('tdHandleTowerUpgradeFinished', '\ttdRefreshTowerRangeIndicatorsForTower(tower)\n'),
                         ('tdHandleTowerUpgradeCancelled', '\t\ttdEvolutionRefresh(tower)\n')]:
        runtime = change_source_function(runtime, name, anchor, anchor + ('\t\t' if 'Cancelled' in name else '\t') + 'tdInitializeBloodlustAutocast(tower)\n')
    anchor = '\ttdTowerGameplayEventsReady = true\n'
    runtime = change_source_function(runtime, 'tdSetupDialogTrigger', anchor, anchor + '\ttdSetupBloodlustAutocastOrders()\n')
    sources['TDTowerRuntime'] = runtime
    objects = sources['TDEquipmentObjectGen']
    name = 'tdConfigureEquipmentBloodlust'
    sources['TDEquipmentObjectGen'] = change_source_function(objects, name, gate.OLD_SUFFIX, gate.NEW_SUFFIX)
    return sources


def synthetic_jass(before, current_sources, old_sources):
    expected = gate.expected_legacy_functions(before, current_sources)
    old_functions = functions(before)
    maps = source_line_maps({p: current_sources[p] for p in old_sources}, old_sources)
    # Only sites present in immutable B get source-proved forward relocation.
    for name, old in old_functions.items():
        prefixes = {m[1] for m in DIAGNOSTIC.finditer(old[0])}
        def relocate(match):
            if match[1] not in prefixes or match[2] not in maps:
                return match[0]
            return '"' + match[1] + str(maps[match[2]][int(match[3])]) + '"'
        expected[name] = DIAGNOSTIC.sub(relocate, expected[name])
    order = list(old_functions)
    order.remove('unit_issueImmediateOrderById')
    order.insert(order.index('unit_setAbilityLevel'), 'unit_issueImmediateOrderById')
    bodies = [expected[name] for name in order] + list(gate.expected_added_functions(current_sources).values())
    return gate.expected_residual(before) + '\n\n' + '\n\n'.join(bodies) + '\n'


def synthetic_objects(before):
    objects = deepcopy(before)
    for level in range(1, 42):
        key = ('aub1', level, 0)
        field = objects['abilities']['A131'].fields[key]
        value = field.value[:-len(gate.OLD_SUFFIX)] + gate.NEW_SUFFIX
        objects['abilities']['A131'].fields[key] = replace(field, value=value, raw=field.raw[:16] + value.encode() + b'\0' + field.raw[-4:])
    return objects


def encode_abilities(objects):
    data = bytearray(struct.pack('<I', 2))
    for table in (0, 1):
        group = [obj for obj in objects.values() if obj.table == table]
        data += struct.pack('<I', len(group))
        for obj in group:
            data += obj.encoded()
    return bytes(data)


class DecodedArchive:
    """In-memory extract-only facade, deliberately no MPQ writer."""
    def __init__(self, baseline, replacements):
        self.baseline, self.replacements = baseline, replacements
    def extract(self, name):
        return self.replacements.get(name, self.baseline.extract(name))


class BloodlustClosedDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifact = Mpq(subprocess.check_output(['git', 'show', gate.BASE_COMMIT + ':ExampleMap.w3x'], cwd=ROOT))
        cls.before = cls.artifact.extract('war3map.j').decode()
        cls.old_sources = {p: subprocess.check_output(['git', 'show', gate.BASE_COMMIT + ':' + gate.SOURCE_PATHS[p]], cwd=ROOT).decode() for p in gate.BASE_SOURCE_SHA256}
        cls.sources = synthetic_sources(cls.old_sources)
        cls.after = synthetic_jass(cls.before, cls.sources, cls.old_sources)
        cls.old_objects = load_objects(cls.artifact)
        cls.objects = synthetic_objects(cls.old_objects)
        cls.resources = gate.members(cls.artifact)
        cls.replacements = {'war3map.j': cls.after.encode(), 'war3map.w3a': encode_abilities(cls.objects['abilities'])}

    def prove(self, script=None, sources=None):
        return gate.prove_jass_delta(script if script is not None else self.after, self.before,
                                    sources if sources is not None else self.sources, self.old_sources)

    def mutate_function(self, name, old, new):
        fn = functions(self.after)[name][0]
        changed = gate.replace_once(fn, old, new)
        return self.after.replace(fn, changed, 1)

    def archive_proof(self, resource_changes=None):
        replacements = dict(self.replacements)
        replacements.update(resource_changes or {})
        archive = DecodedArchive(self.artifact, replacements)
        resources = dict(self.resources)
        for name, data in replacements.items():
            resources[name.casefold()] = (name, data)
        with patch.object(gate, 'members', side_effect=lambda obj: resources if obj is archive else self.resources):
            return gate.validate_closed_bloodlust_delta(archive, self.artifact, self.sources, self.old_sources)

    def test_immutable_B_derived_synthetic_C_full_closed_archive_passes(self):
        proof = self.archive_proof()
        self.assertEqual((proof['resources'], proof['tooltip_fields']), (140, 41))
        self.assertEqual((proof['legacy_functions'], proof['added_functions'], proof['insertion_functions']), (1588, 13, 13))
        self.assertEqual((proof['allocators'], proof['type_comparisons'], proof['local_temp_alpha']), (81, 226, {}))
        self.assertEqual(proof['diagnostic_relocations'], 288)

    def test_read_only_exact_frozen_official_C_artifact(self):
        # Later features replace the root map. History remains the exact official
        # C input; missing history or wrong bytes fails instead of skipping.
        data = subprocess.check_output(['git', 'show', 'b7e3d051e98c2b18caafed4ab6e036700a6ee64c:ExampleMap.w3x'], cwd=ROOT)
        self.assertEqual(gate.digest(data), '55e8decccc5fada5b3dd21c854ad44a2203c73b64e1fcc1d10bd380bd48daadf')
        sources, old_sources = gate.read_sources()
        proof = gate.validate_closed_bloodlust_delta(Mpq(data), self.artifact, sources, old_sources)
        self.assertEqual(proof['diagnostic_relocations'], 288)

    def test_every_retirement_and_initialization_insertion_is_required(self):
        sites = [('tdHandleTowerSellCast', 'tdForgetBloodlustAutocast'),
                 ('tdRejectTowerConstruction', 'tdForgetBloodlustAutocast'),
                 ('tdHandleTowerConstructionCancelled', 'tdForgetBloodlustAutocast'),
                 ('tdHandleTowerDeath', 'tdForgetBloodlustAutocast'),
                 ('tdHandleTowerConstructionFinished', 'tdInitializeBloodlustAutocast'),
                 ('tdHandleTowerUpgradeFinished', 'tdInitializeBloodlustAutocast'),
                 ('call_doAfter_TDTowerRuntime_3', 'tdInitializeBloodlustAutocast'),
                 ('tdSetupDialogTrigger', 'tdSetupBloodlustAutocastOrders')]
        for name, callee in sites:
            fn = functions(self.after)[name][0]
            removed = re.sub(r'^\t+call ' + callee + r'\([^\n]*\)\n', '', fn, flags=re.M)
            self.assertNotEqual(removed, fn)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'exact insertion'):
                self.prove(self.after.replace(fn, removed, 1))

    def test_legacy_changed_bodies_are_not_whole_function_allowlisted(self):
        mutations = [('tdHandleTowerSellCast', 'refund)', 'refund + 1)'),
                     ('call_doAfter_TDTowerRuntime_3', 'cancelledGeneration[this_1]', 'cancelledGeneration[this_1] + 1'),
                     ('tdEquipmentSyncCooldown', 'unit_getAbilityLevel(tower_2, abilityId) == desiredLevel', 'unit_getAbilityLevel(tower_2, abilityId) != desiredLevel'),
                     ('call_doPeriodically_TDEquipmentAbilities', 'getElapsedGameTime(), TDEquipmentCooldown_readyAt[record]', 'getElapsedGameTime(), 0.0'),
                     ('tdSetupEquipmentAbilities', '0.10', '0.11')]
        for name, old, new in mutations:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'exact insertion'):
                self.prove(self.mutate_function(name, old, new))

    def test_unrelated_legacy_numeric_behavior_and_native_wrapper_are_exact(self):
        for name, old, new in [('unit_issueImmediateOrderById', 'IssueImmediateOrderById(this_1, id)', 'IssueImmediateOrderById(this_1, 852102)'),
                               ('tdHandleOrcBladestormCast', 'pulseCount', 'pulseCount + 1')]:
            fn = functions(self.after)[name][0]
            self.assertIn(old, fn)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'exact insertion'):
                self.prove(self.after.replace(fn, fn.replace(old, new, 1), 1))

    def test_allocator_and_type_comparison_changes_are_not_normalized(self):
        for old, new, error in [('TDEnemyGuardLink_typeId[this_1] = 814', 'TDEnemyGuardLink_typeId[this_1] = 813', 'allocator'),
                                ('Table_typeId[this_1] <= 830', 'Table_typeId[this_1] <= 835', 'type comparisons')]:
            self.assertIn(old, self.after)
            with self.subTest(old=old), self.assertRaisesRegex(ValueError, error):
                self.prove(self.after.replace(old, new, 1))

    def test_temp_rename_type_and_use_changes_are_rejected_without_needed_alpha(self):
        fn = functions(self.after)['tdHandleOrcBladestormCast'][0]
        self.assertIn('temp102', fn)
        for changed in (fn.replace('temp102', 'temp9007'), fn.replace('local integer temp102', 'local real temp102'), fn.replace('temp102 = pulseCount', 'temp102 = pulseCount + 1')):
            with self.subTest(), self.assertRaisesRegex(ValueError, 'exact insertion'):
                self.prove(self.after.replace(fn, changed, 1))

    def test_old_diagnostic_stale_wrong_line_and_prefix_cannot_be_ignored(self):
        fn = functions(self.after)['alloc_TDEquipmentCooldown'][0]
        old_fn = functions(self.before)['alloc_TDEquipmentCooldown'][0]
        now = next(m for m in DIAGNOSTIC.finditer(fn) if m[2] == 'TDEquipmentAbilities')
        prior = next(m for m in DIAGNOSTIC.finditer(old_fn) if m[1] == now[1])
        self.assertNotEqual(now[3], prior[3])
        for changed in (fn.replace(now[0], prior[0]), fn.replace(now[0], now[0].replace('line ' + now[3], 'line 999')),
                        fn.replace(now[0], now[0].replace('when calling ', 'when calling wrong_'))):
            with self.subTest(), self.assertRaisesRegex(ValueError, 'diagnostic|Diagnostic'):
                self.prove(self.after.replace(fn, changed, 1))

    def test_new_diagnostic_must_match_exact_source_statement(self):
        name = 'tdHandleTowerConstructionFinished'
        fn = functions(self.after)[name][0]
        site = next(m for m in DIAGNOSTIC.finditer(fn) if 'tdInitializeBloodlustAutocast' in m[1])
        with self.assertRaisesRegex(ValueError, 'exact insertion'):
            self.prove(self.after.replace(fn, fn.replace(site[0], site[0].replace('line ' + site[3], 'line 999')), 1))
        sources = deepcopy(self.sources)
        sources['TDTowerRuntime'] = sources['TDTowerRuntime'].replace('\ttdInitializeBloodlustAutocast(tower)\n', '\ttdInitializeBloodlustAutocast(other)\n', 1)
        with self.assertRaises(ValueError):
            self.prove(sources=sources)

    def test_new_guard_eligibility_manual_order_and_restore_side_effects_are_closed(self):
        cases = [('tdBloodlustAutocastEligible', 'GetUnitTypeId(tower_2) !=', 'GetUnitTypeId(tower_2) =='),
                 ('tdBloodlustAutocastEligible', 'unit_getAbilityLevel(tower_2, ' + gate.ABILITY + ') == 0', 'unit_getAbilityLevel(tower_2, ' + gate.ABILITY + ') > 0'),
                 ('tdRestoreBloodlustAutocast', 'tdBloodlustRestoring = true', 'tdBloodlustRestoring = false'),
                 ('tdHandleBloodlustAutocastOrder', 'orderId, true, false)', 'orderId, true, true)'),
                 ('tdSetupBloodlustAutocastOrders', 'EVENT_PLAYER_UNIT_ISSUED_ORDER', 'EVENT_PLAYER_UNIT_ISSUED_TARGET_ORDER'),
                 ('tdForgetBloodlustChoiceKey', 'dispatch_Table_Table_removeInt', 'dispatch_Table_Table_removeBoolean'),
                 ('tdInitializeBloodlustAutocast', 'key_1, choice,', 'key_1, 1,')]
        for name, old, new in cases:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'semantic template'):
                self.prove(self.mutate_function(name, old, new))
        for name in ('tdRestoreBloodlustAutocast', 'tdHandleBloodlustAutocastOrder'):
            with self.subTest(extra_side_effect=name), self.assertRaisesRegex(ValueError, 'semantic template'):
                self.prove(self.mutate_function(name, 'endfunction', '\tcall RemoveUnit(tower_2)\nendfunction'))

    def test_globals_init_glue_function_set_native_signature_and_order_are_exact(self):
        for old, new in [('Orders_bloodluston=0', 'Orders_bloodluston=852102'),
                         ('\tset Orders_bloodluston = 852102', '\tset Orders_bloodluston = 852103'),
                         ('native UnitAlive takes unit id returns boolean', 'native UnitAlive takes unit id returns integer'),
                         ('Could not initialize package TDTowerBloodlustAutocast.', 'Could not initialize package Wrong.'),
                         ('function tdRestoreBloodlustAutocast takes', 'function unexpectedRestore takes')]:
            self.assertIn(old, self.after)
            with self.subTest(old=old), self.assertRaises(ValueError):
                self.prove(self.after.replace(old, new, 1))
        fn = functions(self.after)['tdHandleTowerUpgradeStarted'][0]
        with self.assertRaisesRegex(ValueError, 'function set'):
            self.prove(self.after.replace(fn, '', 1))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.prove(self.after + '\n' + fn)

    def test_all_41_tooltips_only_exact_suffix_change_is_permitted(self):
        self.assertEqual(gate.verify_object_delta(self.objects, self.old_objects), 41)
        for level in range(1, 42):
            for transform in (lambda f: replace(f, value=f.value + ' extra'), lambda f: replace(f, raw=f.raw[:-4] + b'BAD!')):
                objects = dict(self.objects)
                objects['abilities'] = dict(self.objects['abilities'])
                obj = self.objects['abilities']['A131']
                objects['abilities']['A131'] = replace(obj, fields=dict(obj.fields))
                key = ('aub1', level, 0)
                objects['abilities']['A131'].fields[key] = transform(obj.fields[key])
                with self.subTest(level=level), self.assertRaisesRegex(ValueError, 'exact suffix'):
                    gate.verify_object_delta(objects, self.old_objects)

    def test_native_ability_unrelated_object_fields_and_object_sets_are_immutable(self):
        for kind, code, key in [('abilities', 'A131', ('acdn', 1, 0)), ('abilities', 'A132', ('aub1', 1, 0)),
                               ('units', 'uO6A', ('uabi', 0, 0)), ('items', 'Ibal', next(iter(self.objects['items']['Ibal'].fields)))]:
            objects = deepcopy(self.objects)
            field = objects[kind][code].fields[key]
            objects[kind][code].fields[key] = replace(field, raw=field.raw + b'x')
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'unrelated object field'):
                gate.verify_object_delta(objects, self.old_objects)
        objects = deepcopy(self.objects)
        objects['abilities']['A131'].identity = b'ANclA131'
        with self.assertRaisesRegex(ValueError, 'object identity'):
            gate.verify_object_delta(objects, self.old_objects)
        objects = deepcopy(self.objects); del objects['abilities']['A132']
        with self.assertRaisesRegex(ValueError, 'object set/order'):
            gate.verify_object_delta(objects, self.old_objects)

    def test_resources_and_W3I_are_closed_not_broad_ignored(self):
        for name in ('war3map.w3u', '(listfile)', 'war3map.w3i'):
            old = self.artifact.extract(name)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'resource|metadata|W3I|timestamp'):
                self.archive_proof({name: old + b'x'})


if __name__ == '__main__':
    unittest.main()
