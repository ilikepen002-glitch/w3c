"""Fail-closed tests of trial object/icon checks, independent of compilation."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyTrialArtifact import EXPECTED, ICONS, verify_unit, verify_icons, verify_installation, verify_equipment_tooltips
from VerifySemanticIconArtifact import Field, Object

class ImportedIcons:
    def __init__(self): self.data = {name: (ROOT / 'imports' / name.replace('\\', '/')).read_bytes() for name in ICONS}
    def has(self, name): return name in self.data
    def extract(self, name): return self.data[name]

def target():
    fields = {}
    for name, value in EXPECTED.items():
        kind = 3 if isinstance(value, str) else 2 if isinstance(value, float) else 0
        fields[name, 0, 0] = Field((name, 0, 0), kind, value, b'fixture')
    return Object(1, b'narguTrG', fields)

class TrialArtifactTests(unittest.TestCase):
    def test_explicit_unit_contract(self):
        self.assertEqual(verify_unit({'uTrG': target()})['uhpm'], 1000000)
    def test_every_gameplay_override_is_required_and_exact(self):
        for field in EXPECTED:
            with self.subTest(field=field):
                obj = target(); del obj.fields[field, 0, 0]
                with self.assertRaises(ValueError): verify_unit({'uTrG': obj})
                obj = target(); obj.fields[field, 0, 0] = replace(obj.fields[field, 0, 0], value='mutant')
                with self.assertRaises(ValueError): verify_unit({'uTrG': obj})
    def test_hero_and_native_parent_change_rejected(self):
        for identity in (b'Hpal uTr', b'ugoluTrG'):
            obj = target(); obj.identity = identity
            with self.assertRaises(ValueError): verify_unit({'uTrG': obj})
    def test_packaged_icon_hash_paths_and_seven_mips(self):
        self.assertEqual(len(verify_icons(ImportedIcons())), 2)
    def test_corrupt_icons_missing_icon_and_wrong_path_rejected(self):
        for path in ICONS:
            archive = ImportedIcons(); data = bytearray(archive.data[path]); data[-1] ^= 1; archive.data[path] = bytes(data)
            with self.assertRaises(ValueError): verify_icons(archive)
            archive = ImportedIcons(); del archive.data[path]
            with self.assertRaises(ValueError): verify_icons(archive)
    def test_no_installation_never_passes_native_model_or_table(self):
        self.assertEqual(verify_installation([])['status'], 'NOT_VERIFIED')
        self.assertEqual(verify_installation([])['attack_type_table'], 'NOT_VERIFIED')
    def test_legacy009_real_trial_tooltips_remain_strict(self):
        from GenerateTowerTerrainMask import Mpq
        from trial_legacy009_fixture import map_bytes, Legacy009SourceFixture
        frozen = Legacy009SourceFixture()
        self.addCleanup(frozen.cleanup)
        mpq = Mpq(map_bytes())
        report = verify_equipment_tooltips(mpq, profile='legacy009', source_root=frozen.root)
        self.assertGreater(report['player_tooltip_numeric_cases'], 900)
        self.assertEqual({code: rule['percent'] for code, rule in report['equipment_bonus_texts'].items()},
                         {'iB02': 25, 'iP02': 45})
        class Mutated:
            def extract(self, filename):
                data = mpq.extract(filename)
                old = '普攻命中首领或金币试炼主目标时，追加本次普攻伤害的45%'.encode()
                if filename == 'war3map.w3t':
                    self_test.assertEqual(data.count(old), 1)
                    return data.replace(old, old.replace(b'45%', b'25%'), 1)
                return data
        self_test = self
        with self.assertRaisesRegex(ValueError, 'tooltip/value mismatch: iP02'):
            verify_equipment_tooltips(Mutated(), profile='legacy009', source_root=frozen.root)
        with self.assertRaisesRegex(ValueError, 'current40 equipment identity set mismatch'):
            verify_equipment_tooltips(mpq)

    def test_current_packaged_trial_bonus_text_and_percent_mutations(self):
        import os
        path = os.environ.get('TRIAL_CANDIDATE_MAP')
        if not path: self.skipTest('TRIAL_CANDIDATE_MAP is required for current40 real-MPQ mutations')
        from GenerateTowerTerrainMask import Mpq
        mpq = Mpq(Path(path).read_bytes())
        self.assertGreater(verify_equipment_tooltips(mpq)['player_tooltip_numeric_cases'], 900)
        class Mutated:
            def __init__(self, old, new): self.old, self.new = old.encode(), new.encode()
            def extract(self, filename):
                data = mpq.extract(filename)
                if filename == 'war3map.w3t': self_test.assertEqual(data.count(self.old), 1)
                return data.replace(self.old, self.new, 1) if filename == 'war3map.w3t' else data
        self_test = self
        for old, new in [('普攻命中首领或金币试炼主目标时，追加本次普攻伤害的25%', '普攻命中首领主目标时，追加本次普攻伤害的25%'),
                         ('普攻命中首领或金币试炼主目标时，追加本次普攻伤害的25%', '普攻命中首领或金币试炼主目标时，追加本次普攻伤害的45%')]:
            with self.subTest(old=old), self.assertRaisesRegex(ValueError, 'tooltip/value mismatch'):
                verify_equipment_tooltips(Mutated(old, new))

if __name__ == '__main__': unittest.main()
