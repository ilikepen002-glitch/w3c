"""Closed two-Boss visual allowlist: synthetic negatives and frozen asset formats."""
from copy import deepcopy
import hashlib
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyBossPairArtifact as verify
from test_king_leoric_assets import FakeMpq, w3u, imp
import test_king_leoric_assets as king_fixture


class BossPairDeltaTests(unittest.TestCase):
    def setUp(self):
        fixture = king_fixture.AssetTests(); fixture.setUp(); self.addCleanup(fixture.doCleanups)
        self.before = deepcopy(fixture.before)
        self.units = {'uB08': ('Ocbh', {'uhpm': 3200, 'umvs': 200, 'ucol': 0., 'ussc': 1.}),
                      'uB16': ('Ocbh', {'umdl': 'war3mapImported\\Leoric.mdx', 'usca': 1.3}),
                      'uB24': ('Udre', {'umdl': 'war3mapImported\\EclipseSpellweaver.mdx', 'usca': 8.}),
                      'uB32': ('Ulic', {'uhpm': 26000, 'umvs': 260, 'ucol': 0., 'ussc': 1.})}
        self.before['war3map.w3u'] = w3u(self.units)
        self.current = deepcopy(self.before); self.new_units = deepcopy(self.units)
        self.manifests = {}; self.records = [(13, 'existing.blp')]
        for code, (parent, stem, scale, bones, action, folder) in verify.TARGETS.items():
            model = 'war3mapImported\\' + stem + '.mdx'
            self.new_units[code][1].update(umdl=model, usca=scale)
            assets = []
            for role, path in [('model', model), ('texture', 'Textures\\' + stem + 'Atlas.blp')]:
                data = ('synthetic ' + code + role).encode(); self.current[path] = data
                assets.append({'role': role, 'importPath': path, 'bytes': len(data),
                               'sha256': hashlib.sha256(data).hexdigest()})
                self.records.append((13, path))
            self.manifests[code] = {'unitRawcode': code, 'baseUnitRawcode': parent, 'assets': assets,
                                    'integration': {'modelPath': model, 'scale': scale}}
        self.current['war3map.w3u'] = w3u(self.new_units)
        self.current['war3map.imp'] = imp(self.records)
        self.addCleanup(patch.stopall)
        patch.object(verify, 'members', lambda m: {k.casefold(): (k, v) for k, v in m.data.items()}).start()

    def gate(self):
        return verify.validate(FakeMpq(self.current), FakeMpq(self.before), self.manifests, verify_formats=False)

    def test_exact_two_visual_fields_and_four_assets_pass(self):
        self.assertEqual(self.gate()['scales'], {'uB08': 7.75, 'uB32': 7.0})

    def test_combat_collision_selection_route_and_parent_changes_reject(self):
        for code in verify.TARGETS:
            for key, value in [('uhpm', 1), ('umvs', 400), ('ucol', 50.), ('ussc', 3.),
                               ('umvt', 'fly'), ('uabi', 'newSkill')]:
                with self.subTest(code=code, field=key):
                    changed = deepcopy(self.new_units); changed[code][1][key] = value
                    self.current['war3map.w3u'] = w3u(changed)
                    with self.assertRaises(AssertionError): self.gate()
            changed = deepcopy(self.new_units); changed[code] = ('Nbst', changed[code][1])
            self.current['war3map.w3u'] = w3u(changed)
            with self.assertRaises(AssertionError): self.gate()

    def test_other_boss_visual_and_any_wrong_target_value_reject(self):
        for code, key, value in [('uB16', 'usca', 8.), ('uB24', 'usca', 1.5),
                                 ('uB08', 'usca', 8.), ('uB32', 'usca', 8.),
                                 ('uB08', 'umdl', 'wrong.mdx'), ('uB32', 'umdl', 'wrong.mdx')]:
            with self.subTest(code=code, field=key):
                changed = deepcopy(self.new_units); changed[code][1][key] = value
                self.current['war3map.w3u'] = w3u(changed)
                with self.assertRaises(AssertionError): self.gate()

    def test_jass_objects_terrain_and_old_asset_mutations_reject(self):
        for path in ('war3map.j', 'war3map.w3a', 'war3map.w3t', 'war3map.w3e', 'war3map.wpm', 'war3mapMap.blp'):
            with self.subTest(path=path):
                original = self.current[path]; self.current[path] += b'x'
                with self.assertRaisesRegex(AssertionError, 'Inherited'): self.gate()
                self.current[path] = original

    def test_resource_addition_removal_hash_flag_and_case_mutations_reject(self):
        valid = deepcopy(self.current)
        self.current['unexpected.mdx'] = b'x'
        with self.assertRaises(AssertionError): self.gate()
        for assets in (m['assets'] for m in self.manifests.values()):
            for spec in assets:
                path = spec['importPath']
                with self.subTest(path=path):
                    self.current = deepcopy(valid); del self.current[path]
                    with self.assertRaises(AssertionError): self.gate()
                    self.current = deepcopy(valid); self.current[path] += b'x'
                    with self.assertRaises(AssertionError): self.gate()
                    self.current = deepcopy(valid)
                    self.current['war3map.imp'] = imp([(10 if p == path else f, p) for f, p in self.records])
                    with self.assertRaises(AssertionError): self.gate()
                    self.current['war3map.imp'] = imp(self.records + [(13, path.lower())])
                    with self.assertRaises(AssertionError): self.gate()

    def test_metadata_and_existing_import_changes_reject(self):
        self.current['war3map.w3i'] = self.current['war3map.w3i'].replace(b'description', b'changed')
        with self.assertRaises(AssertionError): self.gate()
        self.current['war3map.w3i'] = self.before['war3map.w3i']
        self.current['war3map.imp'] = imp([(13, 'different.blp')] + self.records[1:])
        with self.assertRaises(AssertionError): self.gate()

    def test_manifest_target_or_scale_expansion_reject(self):
        m = deepcopy(self.manifests)
        for code in verify.TARGETS:
            self.manifests = deepcopy(m); self.manifests[code]['integration']['scale'] = 8.
            with self.assertRaises(AssertionError): self.gate()
        self.manifests = deepcopy(m); self.manifests['uB24'] = m['uB08']
        with self.assertRaises(AssertionError): self.gate()


class BossPairFrozenFormatTests(unittest.TestCase):
    def test_frozen_real_model_and_texture_sha_and_formats(self):
        for code, manifest in verify.load_manifests().items():
            packed = {}
            for a in manifest['assets']:
                b = (ROOT / a['repositoryImportPath']).read_bytes()
                self.assertEqual(len(b), a['bytes']); self.assertEqual(hashlib.sha256(b).hexdigest(), a['sha256'])
                packed[a['role']] = b
            row = verify.TARGETS[code]
            self.assertEqual(len(verify.check_formats(packed['model'], packed['texture'], row[1], row[3], row[4])['sequences']), 6)


if __name__ == '__main__': unittest.main()
