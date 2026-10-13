"""Pure source strings and opt-in exact final-object mutation checks."""
from pathlib import Path
import os
import struct
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyCombinedVisualTextArtifact import SourceTextEvaluator, verify_tables
from VerifyActiveCooldownContract import read_sources
from VerifySemanticIconArtifact import parse_objects, Field


class CombinedSourceTextTests(unittest.TestCase):
    def test_source_numbers_and_all_active_scope(self):
        e = SourceTextEvaluator(read_sources())
        self.assertEqual(e.call('tdPreciseBonusPercentString', [.216]), '21.6%')
        self.assertEqual(e.call('tdTooltipNumber', [14.0]), '14')
        self.assertIn('全部主动技能', e.call('tdAuraStateTooltip', [5, 4]))
        self.assertIn('18%', e.call('tdAuraStateTooltip', [5, 4]))
        self.assertIn('基础冷却10秒', e.call('tdPetSkillDescriptionById', [15, 4]))

    def test_all_forty_item_tooltips_fit_native_utf8_byte_limit(self):
        from ReadEquipmentCatalog import catalog
        e = SourceTextEvaluator(read_sources(), ROOT)
        for entry in catalog():
            text = e.call('tdItemTooltip', [int.from_bytes(entry.rawcode.encode(), 'big')])
            with self.subTest(item=entry.rawcode):
                self.assertLessEqual(len(text.encode('utf-8')), 320)

    def test_unknown_string_method_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, 'Unclassified source string method'):
            SourceTextEvaluator({}).expression('"a".unknown()', {})


class ActualCombinedFieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        current = os.environ.get('COMBINED_CANDIDATE_MAP')
        parent = os.environ.get('COMBINED_PARENT_MAP')
        if not current or not parent:
            raise unittest.SkipTest('exact combined candidate and real parent maps required')
        cls.current = Mpq(Path(current).read_bytes()); cls.parent = Mpq(Path(parent).read_bytes())

    def mutated(self, path, code, key, value, extended):
        objects = parse_objects(self.current.extract(path), extended)
        obj = objects[code]; old = obj.fields[key]; offset = 16 if extended else 8
        encoded = value.encode() + b'\0' if old.kind == 3 else struct.pack('<i' if old.kind == 0 else '<f', value)
        obj.fields[key] = Field(key, old.kind, value, old.raw[:offset] + encoded + old.raw[-4:])
        data = struct.pack('<I', 2)
        for table in range(2):
            rows = [o for o in objects.values() if o.table == table]
            data += struct.pack('<I', len(rows)) + b''.join(o.encoded() for o in rows)
        original = self.current
        class ReadOnlyMutation:
            def extract(self, name): return data if name == path else original.extract(name)
        return ReadOnlyMutation()

    def test_exact_current_source_expected_objects_pass(self):
        self.assertTrue(verify_tables(self.current, self.parent, ROOT))

    def test_approved_text_cannot_change_source_numeric_value(self):
        changed = self.mutated('war3map.w3a', 's003', ('aub1', 1, 0), '附身塔攻击力+999。', True)
        with self.assertRaisesRegex(AssertionError, 'Source text/value mismatch'):
            verify_tables(changed, self.parent, ROOT)

    def test_unapproved_ui_text_and_native_cooldown_cannot_hide_in_text_batch(self):
        for code, key, value in (('Pm07', ('aub1', 1, 0), 'omit release risks'),
                                 ('A131', ('acdn', 41, 0), 0.0)):
            with self.subTest(code=code), self.assertRaisesRegex(AssertionError, 'Unapproved object field'):
                verify_tables(self.mutated('war3map.w3a', code, key, value, True), self.parent, ROOT)

    def test_other_boss_numeric_change_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'Unapproved object field'):
            verify_tables(self.mutated('war3map.w3u', 'uB08', ('uhpm', 0, 0), 99999, False), self.parent, ROOT)


if __name__ == '__main__': unittest.main()
