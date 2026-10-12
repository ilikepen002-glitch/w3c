"""Ordinary-only capture regressions; synthetic mutations never rewrite a map.

Historical-runtime tests pair the immutable formal C artifact with source from
that same commit. They never apply mutable current-source diagnostics to an old
script, and do not claim a new current-stage build.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
FORMAL_C_COMMIT = 'b7e3d051e98c2b18caafed4ab6e036700a6ee64c'
FORMAL_C_MAP_SHA256 = '55e8decccc5fada5b3dd21c854ad44a2203c73b64e1fcc1d10bd380bd48daadf'
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
import VerifyCaptureRemovalArtifact as removal
import VerifySemanticIconArtifact as semantic
from VerifyInheritedJassAliases import inherited_script_view
from test_verify_semantic_icon_artifact import import_bytes, mpq_bytes, replace_field, serialize_objects


class CaptureRemovalObjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This is the fixed formal A historical delta, independent of later B maps.
        data = subprocess.check_output(['git', 'show', '0a476154e7269ee0a1c8e619c1349f31ba17b36b:ExampleMap.w3x'], cwd=ROOT)
        current = semantic.load_objects(Mpq(data))
        for rawcode in removal.REMOVED:
            current['abilities'].pop(rawcode, None)
        for key, value in removal.BOOK_VALUES.items():
            replace_field(current, 'abilities', 'Geqb', key[0], value, key[1], key[2])
        before = deepcopy(current)
        for rawcode in removal.REMOVED:
            obj = deepcopy(before['abilities']['Pcol'])
            obj.identity = b'ANcl' + rawcode.encode()
            before['abilities'][rawcode] = obj
        cls.current = {kind: {rawcode: deepcopy(obj) for rawcode, obj in objects.items()
                              if rawcode not in removal.REMOVED}
                       for kind, objects in before.items()}
        # Only allocator relationships are synthesized, never automatic indexes.
        prior = [current['abilities'][rawcode].fields[('Ncl6', 1, 6)].value
                 for rawcode in removal.COLLECTION] + ['fixtureorderone', 'fixtureordertwo']
        for rawcode, order in zip(removal.REMOVED + removal.COLLECTION, prior):
            replace_field(before, 'abilities', rawcode, 'Ncl6', order, 1, 6)
        for field, value, column in [('spb1', 'A119,Gupg,Dsta,Pmas,Pfor', 1),
                                   ('spb3', 5, 3), ('spb4', 5, 4)]:
            replace_field(before, 'abilities', 'Geqb', field, value, 1, column)
        cls.baseline = before

    def setUp(self):
        self.objects = deepcopy(self.current)
        self.before = deepcopy(self.baseline)

    def test_exact_removal_and_allocator_relationship_pass(self):
        removal.verify_removal_objects(self.objects, self.before)

    def test_legacy_icon_delta_still_rejects_object_removal(self):
        with self.assertRaisesRegex(ValueError, 'object set changed'):
            semantic.verify_object_delta(self.objects, self.before)

    def test_rejects_retained_removed_ability_or_other_deletion(self):
        for rawcode in ('Pmas', 'Pfor', 'Pcol'):
            objects = deepcopy(self.objects)
            if rawcode in removal.REMOVED:
                objects['abilities'][rawcode] = deepcopy(self.before['abilities'][rawcode])
            else:
                del objects['abilities'][rawcode]
            with self.subTest(rawcode=rawcode), self.assertRaisesRegex(ValueError, 'object set/order'):
                removal.verify_removal_objects(objects, self.before)

    def test_rejects_unrelated_fields_unit_item_parents_and_native_aeth(self):
        for kind, rawcode, field, value in [('abilities', 'Pcap', 'aub1', 'changed'),
                                           ('units', 'p011', 'uabi', ''),
                                           ('items', 'Ibal', 'unam', 'changed')]:
            objects = deepcopy(self.objects)
            replace_field(objects, kind, rawcode, field, value, 1 if kind == 'abilities' else 0)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'unrelated object changed'):
                removal.verify_removal_objects(objects, self.before)
        for kind, rawcode in [('units', 'uA11'), ('items', 'Ibal')]:
            for retired in removal.REMOVED:
                objects = deepcopy(self.objects)
                objects[kind][rawcode].identity = retired.encode() + rawcode.encode()
                with self.subTest(kind=kind, retired=retired), self.assertRaisesRegex(ValueError, 'identity/parent/table'):
                    removal.verify_removal_objects(objects, self.before)

    def test_raw_ghost_gate_rejects_unit_and_item_parents(self):
        from VerifyGroundItemArtifact import verify_no_removed_raw_objects
        for kind, rawcode in [('units', 'uA11'), ('items', 'Ibal')]:
            for retired in ('Phnt', 'Pmas', 'Pfor'):
                objects = deepcopy(self.objects[kind])
                objects[rawcode].identity = retired.encode() + rawcode.encode()
                with self.subTest(kind=kind, retired=retired), self.assertRaisesRegex(ValueError, 'removed ' + retired + ' remains as .*object/parent'):
                    verify_no_removed_raw_objects(serialize_objects(objects), False, kind)

    def test_rejects_wrong_book_fields_or_arbitrary_unique_order(self):
        for rawcode, field, value, level, column in [
                ('Geqb', 'spb4', 5, 1, 4), ('Geqb', 'aub1', 'changed', 1, 0),
                ('Pc03', 'Ncl6', 'attack', 1, 6)]:
            objects = deepcopy(self.objects)
            replace_field(objects, 'abilities', rawcode, field, value, level, column)
            with self.subTest(rawcode=rawcode, field=field), self.assertRaisesRegex(ValueError, 'wrong approved removal value'):
                removal.verify_removal_objects(objects, self.before)

    def test_rejects_metadata_or_field_order_drift(self):
        obj = self.objects['abilities']['Pc00']
        key = ('Ncl6', 1, 6)
        obj.fields[key] = replace(obj.fields[key], raw=obj.fields[key].raw[:-4] + b'nope')
        with self.assertRaisesRegex(ValueError, 'metadata changed'):
            removal.verify_removal_objects(self.objects, self.before)
        objects = deepcopy(self.current)
        obj = objects['abilities']['Geqb']
        obj.fields = dict(reversed(list(obj.fields.items())))
        with self.assertRaisesRegex(ValueError, 'field set/order changed'):
            removal.verify_removal_objects(objects, self.before)


class CaptureRemovalMemberTests(unittest.TestCase):
    def setUp(self):
        self.before_members = {'terrain': b'fixed terrain', 'unrelated.blp': b'fixed artwork',
                               'war3map.w3a': b'before objects', 'war3map.j': b'ordinary capture',
                               'war3map.w3i': b'20261011-2345-UTC+8\0other\0' + b'20261011-2345-UTC+8'}
        self.before_members.update({path: b'retired artwork' for path in removal.REMOVED_IMPORTS})
        names = list(removal.REMOVED_IMPORTS) + ['unrelated.blp']
        self.before_members['war3map.imp'] = import_bytes(names)
        self.members = {path: data for path, data in self.before_members.items()
                        if path not in removal.REMOVED_IMPORTS}
        self.members['war3map.imp'] = import_bytes(['unrelated.blp'])
        self.members['war3map.w3a'] = b'after objects'
        self.members['war3map.w3i'] = b'20261012-0010-UTC+8\0other\0' + b'20261012-0010-UTC+8'
        self.baseline = Mpq(mpq_bytes(self.before_members))

    def verify(self):
        removal.verify_removal_members(Mpq(mpq_bytes(self.members)), self.baseline)

    def test_only_four_imports_objects_script_and_timestamp_pass(self):
        self.verify()

    def test_rejects_retired_import_extra_member_and_unrelated_resource_drift(self):
        for path, data, reason in [(removal.REMOVED_IMPORTS[0], b'retired', 'member delta'),
                                   ('extra.blp', b'extra', 'member delta'),
                                   ('terrain', b'changed', 'unrelated packaged resource')]:
            with self.subTest(path=path):
                self.setUp()
                self.members[path] = data
                with self.assertRaisesRegex(ValueError, reason):
                    self.verify()

    def test_rejects_metadata_import_flags_and_master_script_ghosts(self):
        for path, data, reason in [
                ('war3map.w3i', self.members['war3map.w3i'] + b'changed', 'metadata changed'),
                ('war3map.imp', import_bytes(['wrong.blp']), 'Import manifest changed'),
                ('war3map.j', b'call tdPetHandleForge()', 'Obsolete capture gameplay'),
                ('war3map.j', str(int.from_bytes(b'Pmas', 'big')).encode(), 'Removed Pmas')]:
            with self.subTest(path=path, reason=reason):
                self.setUp()
                self.members[path] = data
                with self.assertRaisesRegex(ValueError, reason):
                    self.verify()


SCALAR_SCRIPT = '''function tdPetSpendCaptureBall takes integer lane_2, boolean validTarget returns boolean
    if not tdIsLanePlayer(lane_2) or not validTarget or tdPetCollectionCount(lane_2) >= TDPetData_TD_PET_COLLECTION_LIMIT then
        return false
    endif
    return tdPetTakeBall(lane_2)
endfunction
function tdPetHandleCapture takes nothing returns boolean
    if not tdPetSpendCaptureBall(lane_2, true) then
        return false
    endif
    set guaranteed = TDPetWildRecord_tutorial[wild] and not TDPetState_tdPetTutorialUsed[lane_2]
    if TDPetWildRecord_tutorial[wild] then
        set TDPetState_tdPetTutorialUsed[lane_2] = true
    endif
    if not guaranteed and GetRandomInt(1, 100) > 60 then
        return false
    endif
    if not tdPetStore(lane_2, pet) then
        call tdPetAddBall(lane_2)
        call tdPetSyncBallAbility(lane_2)
        return false
    endif
    return false
endfunction
'''


class CaptureRemovalConditionTests(unittest.TestCase):
    """Synthetic scalar fixtures validate the gate, not the produced game script."""
    def test_scalar_gate_checks_complete_rule_matrices(self):
        removal.verify_spend_and_attempt(SCALAR_SCRIPT)

    def test_rejects_spend_tutorial_roll_and_refund_regressions(self):
        for old, new, reason in [
                ('>= TDPetData_TD_PET_COLLECTION_LIMIT', '> TDPetData_TD_PET_COLLECTION_LIMIT', 'spend precondition/charge'),
                ('TDPetWildRecord_tutorial[wild] and', 'TDPetWildRecord_tutorial[wild] or', 'Tutorial first-attempt'),
                ('GetRandomInt(1, 100) > 60', 'GetRandomInt(1, 100) > 61', 'sixty-percent roll'),
                ('call tdPetAddBall(lane_2)', '// removed refund', 'refund and synchronize')]:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                removal.verify_spend_and_attempt(SCALAR_SCRIPT.replace(old, new, 1))

    def test_generated_temp_indexes_are_normalized_but_references_and_types_remain(self):
        old = 'function f takes nothing returns nothing\n    local real temp79\n    local string temp80\n    set temp79 = 1.0\n    set temp80 = "text"\nendfunction'
        equivalent = old.replace('temp79', 'temp78').replace('temp80', 'temp79')
        self.assertEqual(removal.canonical_packaged_function(old), removal.canonical_packaged_function(equivalent))
        self.assertNotEqual(removal.canonical_packaged_function(old), removal.canonical_packaged_function(equivalent.replace('local real', 'local integer')))
        self.assertNotEqual(removal.canonical_packaged_function(old), removal.canonical_packaged_function(equivalent.replace('set temp78', 'set temp79')))


class CaptureRemovalSourceTests(unittest.TestCase):
    def test_all_gameplay_master_objects_handlers_text_are_gone(self):
        paths = list((ROOT / 'wurst/pets').glob('*.wurst')) + [ROOT / 'wurst/items/TDItemObjectGen.wurst']
        text = '\n'.join(path.read_text() for path in paths)
        for obsolete in ('TD_PET_MASTER_ABILITY_ID', 'TD_PET_FORGE_ABILITY_ID', 'tdPetMasterBalls',
                         'tdPetForgeMasterBall', 'tdPetHandleMaster', 'tdPetHandleForge',
                         'tdPetHandleCaptureWithBall', '大师球', '五合一'):
            self.assertNotIn(obsolete, text)

    def test_capture_and_inherited_deploy_protections_remain(self):
        runtime = (ROOT / 'wurst/pets/TDPetRuntime.wurst').read_text()
        self.assertIn('let guaranteed = wild.tutorial and not tdPetTutorialUsed[lane]', runtime)
        self.assertIn('if not guaranteed and GetRandomInt(1, 100) > 60', runtime)
        self.assertIn('tdPetAddBall(lane)', runtime)
        self.assertNotIn('TD_PET_DEPLOY_LIMIT', runtime)
        objects = (ROOT / 'wurst/pets/TDPetObjectGen.wurst').read_text()
        self.assertIn('..setNormalAbilities("Aeth")', objects)
        self.assertIn('每座塔可上阵1只精灵', objects)
        self.assertNotIn('每路最多上阵3只', objects)

    def test_exact_four_dedicated_imports_absent_shared_source_retained(self):
        for path in removal.REMOVED_IMPORTS:
            self.assertFalse((ROOT / 'imports' / path.replace('\\', '/')).exists(), path)
        self.assertTrue((ROOT / 'assets/source/semantic-icons/actions-sheet-v2-source.png').exists())


class CaptureRemovalHistoricalRuntimeTests(unittest.TestCase):
    """Preserve the real formal C capture oracle independently of later stages."""
    @classmethod
    def setUpClass(cls):
        data = subprocess.check_output(['git', 'show', '0384ccddcfdbaa868f773573c1f7403fe809d3e2:ExampleMap.w3x'], cwd=ROOT)
        cls.before = Mpq(data).extract('war3map.j').decode('utf-8')
        c_data = subprocess.check_output(['git', 'show', FORMAL_C_COMMIT + ':ExampleMap.w3x'], cwd=ROOT)
        if hashlib.sha256(c_data).hexdigest() != FORMAL_C_MAP_SHA256:
            raise AssertionError('Immutable formal C artifact digest changed')
        script = Mpq(c_data).extract('war3map.j').decode('utf-8')
        # Formal B changed compiler class IDs; prove named allocators and every
        # comparison against immutable formal A, without weakening the historic
        # capture-only delta gate or changing actual behavior-oracle input.
        from VerifyBuilderControlDelta import proved_type_reindex_view
        a_data = subprocess.check_output(['git', 'show', 'e340d1758c7d72c0f88df3cdb54139ec989a6fcd:ExampleMap.w3x'], cwd=ROOT)
        a_script = Mpq(a_data).extract('war3map.j').decode('utf-8')
        cls.actual = script
        # C source insertion shifts diagnostics only at proved unchanged lines;
        # the historical B class/delta rule remains untouched.
        from VerifyBloodlustDiagnostics import proved_diagnostic_view
        b_data = subprocess.check_output(['git', 'show', '697d0f3e7ce8c1ff9f1f163bcf9b72ea09afdda5:ExampleMap.w3x'], cwd=ROOT)
        b_script = Mpq(b_data).extract('war3map.j').decode('utf-8')
        paths = {'TDEquipmentAbilities': 'wurst/items/TDEquipmentAbilities.wurst',
                 'TDTowerRuntime': 'wurst/towers/TDTowerRuntime.wurst'}
        before_sources = {name: subprocess.check_output(['git', 'show', '697d0f3e7ce8c1ff9f1f163bcf9b72ea09afdda5:' + path], cwd=ROOT).decode() for name, path in paths.items()}
        # Both artifact and source are frozen C. Current Boss or later source
        # insertions are validated by their own delta, never this historical one.
        current_sources = {name: subprocess.check_output(['git', 'show', FORMAL_C_COMMIT + ':' + path], cwd=ROOT).decode() for name, path in paths.items()}
        cls.formal_sources, cls.b_sources, cls.b_script = current_sources, before_sources, b_script
        diagnostic_view, cls.proved_diagnostics = proved_diagnostic_view(script, b_script, current_sources, before_sources)
        class_view, cls.proved_class_ids = proved_type_reindex_view(diagnostic_view, a_script)
        cls.current, cls.proved_aliases = inherited_script_view(class_view, cls.before)

    def test_historical_diagnostics_reject_mismatched_source_pair(self):
        from VerifyBloodlustDiagnostics import proved_diagnostic_view
        mismatched = dict(self.formal_sources)
        mismatched['TDTowerRuntime'] = '// later-stage source insertion\n' + mismatched['TDTowerRuntime']
        with self.assertRaisesRegex(ValueError, 'Diagnostic source-line provenance changed'):
            proved_diagnostic_view(self.actual, self.b_script, mismatched, self.b_sources)

    def test_actual_packaged_capture_and_inherited_lifecycle_pass(self):
        removal.verify_spend_and_attempt(self.actual)
        from VerifyPetDeploymentArtifact import verify_gate
        verify_gate(self.actual)
        removal.verify_capture_runtime(self.current, self.before)

    def test_actual_boss_resistance_and_engine_functions_remain_inherited(self):
        removal.verify_inherited_boss(self.current, self.before)

    def test_rejects_inherited_boss_scale_mutation(self):
        from VerifyPetUIArtifact import jass_function
        body = jass_function(self.current, 'tdWaveBossSpellDamageTakenFactor').group(0)
        changed = self.current.replace(body, body.replace('0.58', '0.59'), 1)
        self.assertNotEqual(changed, self.current)
        with self.assertRaisesRegex(ValueError, 'Inherited Boss resistance/engine function changed'):
            removal.verify_inherited_boss(changed, self.before)

    def test_rejects_unrelated_inventory_and_wild_lifecycle_mutations(self):
        from VerifyPetUIArtifact import jass_function
        for name, reason in [('tdPetAddBall', 'Unrelated ordinary'), ('tdPetWildTravelSpeed', 'Wild lifecycle changed')]:
            body = jass_function(self.current, name).group(0)
            changed = self.current.replace(body, body.replace('\n', '\n    // mutation\n', 1), 1)
            with self.subTest(function=name), self.assertRaisesRegex(ValueError, reason):
                removal.verify_capture_runtime(changed, self.before)


class CaptureRemovalCurrentManagerTests(unittest.TestCase):
    def test_current_twenty_slot_ordinary_spend_tutorial_roll_and_refund(self):
        script = Mpq((ROOT / 'ExampleMap.w3x').read_bytes()).extract('war3map.j').decode('utf-8')
        self.assertIn('set TDPetData_TD_PET_COLLECTION_LIMIT = 20', script)
        removal.verify_spend_and_attempt(script, capacity=20)


if __name__ == '__main__':
    unittest.main()
