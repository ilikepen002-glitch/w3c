"""Strict visual-scope synthetic negatives plus frozen real-format tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyEclipseBossArtifact as verify
from test_king_leoric_assets import FakeMpq, w3u, imp
import test_king_leoric_assets as king_fixture

class EclipseVisualDeltaTests(unittest.TestCase):
    def setUp(self):
        fixture = king_fixture.AssetTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.before = deepcopy(fixture.before)
        self.units = {'uB24': ('Udre', {'uhpm': 11000, 'umvs': 230, 'ucol': 0., 'ussc': 1.}),
                      'uB16': ('Ocbh', {'uhpm': 6800, 'ucol': 0.})}
        self.before['war3map.w3u'] = w3u(self.units)
        self.current = deepcopy(self.before)
        self.new_units = deepcopy(self.units); self.new_units['uB24'][1].update(umdl='war3mapImported\\EclipseSpellweaver.mdx', usca=8.0)
        self.current['war3map.w3u'] = w3u(self.new_units)
        self.manifest = json.loads(verify.MANIFEST.read_text(encoding='utf-8'))
        for spec in self.manifest['assets']:
            data = ('synthetic ' + spec['role']).encode(); self.current[spec['importPath']] = data
            spec['bytes'] = len(data); spec['sha256'] = hashlib.sha256(data).hexdigest()
        self.records = [(13, 'existing.blp')] + [(13, x['importPath']) for x in self.manifest['assets']]
        self.current['war3map.imp'] = imp(self.records)
        self.addCleanup(patch.stopall)
        patch.object(verify, 'members', lambda m: {k.casefold(): (k, v) for k, v in m.data.items()}).start()

    def run_gate(self):
        return verify.validate(FakeMpq(self.current), FakeMpq(self.before), self.manifest, check_formats=False)

    def test_exact_visual_only_scope_passes(self): self.assertEqual(self.run_gate()['status'], 'PASS')

    def test_any_combat_collision_route_or_selection_field_change_rejects(self):
        for key, value in (('uhpm', 1), ('umvs', 400), ('ucol', 50.), ('ussc', 2.), ('umvt', 'fly'), ('uabi', 'newSkill')):
            with self.subTest(key=key):
                changed = deepcopy(self.new_units); changed['uB24'][1][key] = value
                self.current['war3map.w3u'] = w3u(changed)
                with self.assertRaisesRegex(AssertionError, 'Nonvisual'): self.run_gate()

    def test_other_unit_and_parent_change_rejects(self):
        for units in (dict(self.new_units, uB24=('Ulic', self.new_units['uB24'][1])),
                      dict(self.new_units, uB16=('Ocbh', {'uhpm': 1, 'ucol': 0.}))):
            self.current['war3map.w3u'] = w3u(units)
            with self.assertRaises(AssertionError): self.run_gate()

    def test_wrong_visual_values_reject(self):
        for key, value in (('umdl', 'wrong.mdx'), ('usca', 1.5)):
            changed=deepcopy(self.new_units); changed['uB24'][1][key]=value; self.current['war3map.w3u']=w3u(changed)
            with self.assertRaisesRegex(AssertionError, 'Wrong model'): self.run_gate()

    def test_jass_and_existing_resources_reject_changes(self):
        for path in ('war3map.j', 'war3map.w3a', 'war3map.w3e'):
            original=self.current[path]; self.current[path]=b'changed'
            with self.assertRaisesRegex(AssertionError, 'Inherited'): self.run_gate()
            self.current[path]=original

    def test_unapproved_asset_addition_or_removal_rejects(self):
        self.current['unknown.mdx']=b'x'
        with self.assertRaisesRegex(AssertionError, 'addition/removal'): self.run_gate()
        del self.current['unknown.mdx']; del self.current[self.manifest['assets'][0]['importPath']]
        with self.assertRaisesRegex(AssertionError, 'addition/removal'): self.run_gate()

    def test_wrong_bytes_flag_and_case_alias_rejects(self):
        p=self.manifest['assets'][0]['importPath']; original=self.current[p]; self.current[p]+=b'x'
        with self.assertRaisesRegex(AssertionError, 'hash'): self.run_gate()
        self.current[p]=original; self.current['war3map.imp']=imp([(10 if path==p else f,path) for f,path in self.records])
        with self.assertRaisesRegex(AssertionError, 'flag'): self.run_gate()
        self.current['war3map.imp']=imp(self.records+[(13,p.lower())])
        with self.assertRaises(AssertionError): self.run_gate()

    def test_metadata_description_change_rejects(self):
        self.current['war3map.w3i']=self.current['war3map.w3i'].replace(b'description',b'changed')
        with self.assertRaisesRegex(AssertionError, 'Metadata'): self.run_gate()

    def scale_fixture(self):
        self.before = deepcopy(self.current)
        old_units = deepcopy(self.new_units); old_units['uB24'][1]['usca'] = 1.5
        self.before['war3map.w3u'] = w3u(old_units)

    def run_scale_gate(self):
        return verify.validate(FakeMpq(self.current), FakeMpq(self.before), self.manifest,
                               check_formats=False, scale_only=True)

    def test_scale_only_exact_single_field_passes(self):
        self.scale_fixture()
        self.assertEqual(self.run_scale_gate()['visualScale'], 8.0)

    def test_scale_only_rejects_model_assets_imports_and_combat_changes(self):
        self.scale_fixture()
        valid = deepcopy(self.current)
        for path in ('war3map.j', 'war3map.w3a', 'war3map.w3e', 'war3map.imp') + tuple(s['importPath'] for s in self.manifest['assets']):
            with self.subTest(resource=path):
                self.current = deepcopy(valid); self.current[path] += b'x'
                with self.assertRaises(AssertionError): self.run_scale_gate()
        for key, value in (('umdl', 'wrong.mdx'), ('usca', 1.5), ('usca', 7.99), ('uhpm', 1),
                           ('ucol', 50.), ('ussc', 2.), ('umvt', 'fly'), ('umvs', 400), ('uabi', 'newSkill')):
            with self.subTest(field=key, value=value):
                self.current = deepcopy(valid); changed = deepcopy(self.new_units); changed['uB24'][1][key] = value
                self.current['war3map.w3u'] = w3u(changed)
                with self.assertRaises(AssertionError): self.run_scale_gate()
        self.current = deepcopy(valid); changed = deepcopy(self.new_units); changed['uB24'][1]['usca'] = 8
        self.current['war3map.w3u'] = w3u(changed)
        with self.assertRaisesRegex(AssertionError, 'encoding'): self.run_scale_gate()
        self.current = deepcopy(valid); changed = deepcopy(self.new_units); changed['uB16'][1]['usca'] = 8.0
        self.current['war3map.w3u'] = w3u(changed)
        with self.assertRaises(AssertionError): self.run_scale_gate()
        self.current = deepcopy(valid); self.current['new.mdx'] = b'x'
        with self.assertRaises(AssertionError): self.run_scale_gate()

class EclipseFrozenFormatTests(unittest.TestCase):
    def test_frozen_real_model_and_texture_formats(self):
        m=json.loads(verify.MANIFEST.read_text(encoding='utf-8')); assets={s['role']:(ROOT/s['repositoryImportPath']).read_bytes() for s in m['assets']}
        for s in m['assets']:
            self.assertEqual(hashlib.sha256(assets[s['role']]).hexdigest(),s['sha256'])
        self.assertEqual(len(verify.check_model(assets['model'],assets['texture'])['sequences']),6)

if __name__=='__main__': unittest.main()
