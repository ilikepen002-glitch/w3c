"""Narrow append-only model/rule regression and negative guard tests (no Grill)."""
import json
import math
import struct
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyAllPetDisplayArtifact import BASE, chunks, resource_check, source_check, verify_model


class AllPetDisplayAssetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = json.loads((ROOT / 'assets/source/elemental-spirits/import-manifest.json').read_text())['models'][1]
        path = 'imports/' + cls.entry['modelImportPath'].replace('\\', '/')
        cls.before = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
        cls.current = (ROOT / path).read_bytes()

    def mutate_chunk(self, tag, transform):
        data = chunks(self.current)
        data[tag] = transform(data[tag])
        return b'MDLX' + b''.join(k.encode() + struct.pack('<I', len(v)) + v for k, v in data.items())

    def test_all_fifteen_models_and_unchanged_atlases(self):
        report = resource_check()
        self.assertEqual(len(report['models']), 15)
        self.assertTrue(report['allFifteenAtlasBytesPreserved'])
        for model in report['models'][1:]:
            self.assertEqual(model['displaySequenceIndices'], [5, 6, 7, 8, 9])
            self.assertTrue(all(model['animatedNonRootBonesBySequence'].values()))

    def test_revised_cast_uses_visible_limb_rotation_and_recovers(self):
        # Complements the separately inspected offline visual panels; it is not
        # a substitute for judging the pose silhouette in those images.
        from VerifyPetDisplayArtifact import parse_mdx
        cases = [('BoulderArmGibbon', 'LeftArm', 1.20),
                 ('BrassPangolin', 'DiggingArmLeft', .95),
                 ('RootbudStag', 'FrontLeft', 1.00),
                 ('SnowManeOtter', 'FrontLeftPaw', .95),
                 ('MoltenHornSalamander', 'FrontLeft', .85)]
        for model, bone_name, angle in cases:
            data = parse_mdx((ROOT / 'imports/war3mapImported' / (model + '.mdx')).read_bytes())
            bone = next(b for b in data['bones'] if b['name'] == bone_name)
            keys = dict(bone['tracks']['KGRT']['records'])
            x, y, z, w = struct.unpack_from('<4f', keys[16000], 4)
            pitch = math.asin(max(-1., min(1., 2 * (w * y - z * x))))
            self.assertAlmostEqual(pitch, -angle, places=5)
            for frame in (15400, 16600):
                quaternion = struct.unpack_from('<4f', keys[frame], 4)
                self.assertLess(max(abs(v) for v in quaternion[:3]), 1e-6)

    def test_supported_range_is_only_runtime_rule_delta(self):
        self.assertTrue(source_check()['onlyCapabilityRangeChanged'])

    def test_original_binary_key_mutation_is_rejected(self):
        def change(data):
            value = bytearray(data)
            # First bone generic-node first translation key starts at 96+16.
            value[116] ^= 1
            return bytes(value)
        with self.assertRaisesRegex(AssertionError, 'Original 0–4 raw binary key changed'):
            verify_model(self.before, self.mutate_chunk('BONE', change), self.entry)

    def test_missing_display_sequence_is_rejected(self):
        with self.assertRaises(AssertionError):
            verify_model(self.before, self.mutate_chunk('SEQS', lambda data: data[:-132]), self.entry)

    def test_uv_geometry_mutation_is_rejected(self):
        def change(data):
            value = bytearray(data)
            offset = data.index(b'UVBS') + 8
            value[offset] ^= 1
            return bytes(value)
        with self.assertRaisesRegex(AssertionError, 'Geometry/normal/UV/topology/binding changed'):
            verify_model(self.before, self.mutate_chunk('GEOS', change), self.entry)

    def test_texture_path_mutation_is_rejected(self):
        def change(data):
            value = bytearray(data)
            value[4] = ord('X')
            return bytes(value)
        with self.assertRaisesRegex(AssertionError, 'Texture reference changed'):
            verify_model(self.before, self.mutate_chunk('TEXS', change), self.entry)


if __name__ == '__main__':
    unittest.main()
