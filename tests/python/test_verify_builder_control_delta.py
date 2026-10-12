"""Immutable formal A and synthetic B-only negative fixtures; never MPQ edits."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifySemanticIconArtifact import load_objects
from VerifyDamageRankingJass import functions
import VerifyBuilderControlDelta as gate


class BuilderControlDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = Mpq(subprocess.check_output(['git', 'show', 'e340d1758c7d72c0f88df3cdb54139ec989a6fcd:ExampleMap.w3x'], cwd=ROOT))
        cls.before = artifact.extract('war3map.j').decode()
        cls.after = cls.before
        for name, old_id in gate.REINDEXED.items():
            fn = functions(cls.after)['alloc_' + name][0]
            changed = gate.ASSIGN.sub(lambda m: m[1] + str(old_id - 5) + m[4] if int(m[3]) else m[0], fn)
            cls.after = cls.after.replace(fn, changed, 1)
        thresholds = {old: old - 5 for old in gate.REINDEXED.values()}
        cls.after = gate.TYPE_TEST.sub(lambda m: m[1] + str(thresholds.get(int(m[2]), int(m[2]))), cls.after)
        cls.after = cls.after.replace(gate.OLD_GUIDE, gate.NEW_GUIDE)
        for old, new in [(15, 14), (64, 63)]:
            cls.after = cls.after.replace(f'when calling fromRawCode in TDPetData, line {old}', f'when calling fromRawCode in TDPetData, line {new}')
        cls.objects = load_objects(artifact)

    def test_exact_class_bijection_and_full_synthetic_B_jass_pass(self):
        proof = gate.prove_jass_delta(self.after, self.before)
        self.assertEqual(proof['allocators'], 81)
        self.assertEqual(len(proof['type_reindex']), 21)
        self.assertEqual(proof['type_comparisons'], 226)

    def test_inconsistent_assignment_wrong_owner_or_duplicate_type_id_rejected(self):
        needle = 'TDEnemyGuardLink_typeId[this_1] = 814'
        for changed in (self.after.replace(needle, 'TDEnemyGuardLink_typeId[this_1] = 813', 1),
                        self.after.replace(needle, 'TDEnemyGuardLink_typeId[this_1] = 813'),
                        self.after.replace('alloc_TDEnemyGuardLink takes', 'alloc_WrongOwner takes')):
            with self.subTest(), self.assertRaisesRegex(ValueError, 'allocation|allocator|unique|function set'):
                gate.prove_jass_delta(changed, self.before)

    def test_type_threshold_and_allocator_state_changes_cannot_be_normalized(self):
        for old, new in [('CallbackCounted_typeId[this_1] <= 639', 'CallbackCounted_typeId[this_1] <= 640'),
                         ('TDEnemyGuardLink_maxIndex + 1', 'TDEnemyGuardLink_maxIndex + 2')]:
            self.assertIn(old, self.after)
            with self.subTest(old=old), self.assertRaisesRegex(ValueError, 'threshold|allocator differs'):
                gate.proved_type_reindex_view(self.after.replace(old, new, 1), self.before)

    def test_stale_old_table_thresholds_cannot_pass_as_unknown_constants(self):
        for current, stale in [('Table_typeId[this_1] <= 831', 'Table_typeId[this_1] <= 836'),
                               ('Table_typeId[this_1] <= 830', 'Table_typeId[this_1] <= 835')]:
            self.assertIn(current, self.after)
            changed = self.after.replace(current, stale, 1)
            with self.subTest(stale=stale), self.assertRaisesRegex(ValueError, 'Type comparison threshold changed'):
                gate.prove_jass_delta(changed, self.before)
            with self.subTest(view_stale=stale), self.assertRaisesRegex(ValueError, 'Type comparison threshold changed'):
                gate.proved_type_reindex_view(changed, self.before)

    def test_local_alpha_rename_proves_types_and_all_use_sites(self):
        name = 'tdHandleOrcBladestormCast'; fn = functions(self.after)[name][0]
        self.assertIn('temp107', fn)
        renamed = fn.replace('temp107', 'temp9007')
        gate.prove_jass_delta(self.after.replace(fn, renamed, 1), self.before)
        for changed in (renamed.replace('local integer temp9007', 'local real temp9007'),
                        renamed.replace('temp9007 = pulseCount', 'temp9007 = pulseCount + 1'),
                        renamed.replace('temp9007, clVar', 'temp106, clVar')):
            with self.subTest(), self.assertRaisesRegex(ValueError, 'temp|outside proved'):
                gate.prove_jass_delta(self.after.replace(fn, changed, 1), self.before)

    def test_only_exact_startup_and_two_debug_lines_are_permitted(self):
        for old, new in [(gate.NEW_GUIDE, gate.NEW_GUIDE + ' changed'),
                         ('TDPetData, line 14', 'TDPetData, line 12'),
                         ('TDPetCombat, line 255', 'TDPetCombat, line 254'),
                         ('0.58', '0.59')]:
            self.assertIn(old, self.after)
            with self.subTest(old=old), self.assertRaisesRegex(ValueError, 'exact|permitted|outside proved'):
                gate.prove_jass_delta(self.after.replace(old, new, 1), self.before)

    def test_object_set_parent_and_unrelated_field_changes_are_rejected(self):
        after = deepcopy(self.objects)
        del after['abilities']['A108']; del after['abilities']['Prpr']
        for (kind, code, key), (_old, new) in gate.OBJECT_VALUES.items():
            field = after[kind][code].fields[key]
            import struct
            header = 16 if kind == 'abilities' else 8
            value = new.encode() + b'\0' if field.kind == 3 else struct.pack('<i', new)
            after[kind][code].fields[key] = replace(field, value=new, raw=field.raw[:header] + value + field.raw[-4:])
        gate.verify_object_delta(after, self.objects)
        for kind, code in [('units', 'uO6A'), ('abilities', 'A131'), ('items', 'Ibal')]:
            changed = deepcopy(after); obj = changed[kind][code]
            key = next(iter(obj.fields)); obj.fields[key] = replace(obj.fields[key], raw=b'wrong')
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, 'unrelated object field'):
                gate.verify_object_delta(changed, self.objects)
        changed = deepcopy(after);changed['abilities']['A108'] = self.objects['abilities']['A108']
        with self.assertRaisesRegex(ValueError, 'object set/order'):
            gate.verify_object_delta(changed, self.objects)
