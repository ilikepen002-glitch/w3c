"""Synthetic fixtures only: no independently redistributed third-party assets."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import RestoreKingLeoricAssets as restore
import VerifyKingLeoricArtifact as verify


def w3u(units):
    data = bytearray(struct.pack('<III', 2, 0, len(units)))
    for uid, (parent, fields) in units.items():
        data.extend(parent.encode() + uid.encode() + struct.pack('<I', len(fields)))
        for name, value in fields.items():
            kind = 3 if isinstance(value, str) else 1 if isinstance(value, float) else 0
            data.extend(name.encode() + struct.pack('<I', kind))
            data.extend(value.encode() + b'\0' if kind == 3 else struct.pack('<f' if kind == 1 else '<i', value))
            data.extend(uid.encode())
    return bytes(data)


def imp(records):
    return struct.pack('<II', 1, len(records)) + b''.join(bytes([flag]) + path.encode() + b'\0'
                                                     for flag, path in records)


class FakeMpq:
    def __init__(self, data):
        self.data = data

    def extract(self, path):
        return self.data[path]


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.originals = {'Leoric.mdx': b'synthetic mesh', 'Leoric_Portrait.mdx': b'synthetic portrait',
                          'Leoric.blp': b'synthetic texture', 'readme.html': b'synthetic readme'}
        real_manifest = json.loads(restore.MANIFEST.read_text(encoding='utf-8'))
        self.manifest = dict(real_manifest)
        self.manifest['assets'] = [dict(spec, size_bytes=len(self.originals[spec['name']]),
                                       sha256=hashlib.sha256(self.originals[spec['name']]).hexdigest())
                                   for spec in real_manifest['assets']]
        self.manifest_path = self.root / 'manifest.json'
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.archive = self.root / 'download.zip'
        self.write_zip()
        self.addCleanup(patch.stopall)
        patch.object(restore, 'ROOT', self.root).start()
        patch.object(restore, 'MANIFEST', self.manifest_path).start()
        patch.object(verify, 'ROOT', self.root).start()
        patch.object(verify, 'members', lambda m: {k.casefold(): (k, v) for k, v in m.data.items()}).start()
        (self.root / 'imports').mkdir()
        (self.root / 'imports/Credits-KingLeoric.txt').write_bytes(b'synthetic credits')
        self.units = {'uB16': ('Ocbh', {'uhpm': 6800, 'umvs': 245, 'ucol': 0.0, 'ussc': 1.0}),
                      'uB08': ('Ocbh', {'uhpm': 3200, 'ucol': 0.0})}
        self.before = {p: b'unchanged' for p in
                       ['war3map.j', 'war3map.w3a', 'war3map.w3t', 'war3map.w3e', 'war3map.wpm', 'war3mapMap.blp']}
        self.before['war3map.w3u'] = w3u(self.units)
        title = '契灵守卫战 20261013-0850-UTC+8'.encode()
        self.before['war3map.w3i'] = (struct.pack('<III', 25, 0, 0) + title + b'\0author\0description\0players\0'
                                      + b'\0'*65 + b'loading.mdx\0loading text\0' + title + b'\0tail')
        self.before['war3map.imp'] = imp([(13, 'existing.blp')])
        self.current = dict(self.before)
        self.new_units = {k: (p, dict(f)) for k, (p, f) in self.units.items()}
        self.new_units['uB16'][1].update(umdl='war3mapImported\\Leoric.mdx', usca=1.3)
        self.current['war3map.w3u'] = w3u(self.new_units)
        self.records = [(13, 'existing.blp')]
        for a in self.manifest['assets']:
            self.current[a['mpq_path']] = self.originals[a['name']]
            self.records.append((13, a['mpq_path']))
        self.current['Credits-KingLeoric.txt'] = b'synthetic credits'
        self.records.append((13, 'Credits-KingLeoric.txt'))
        self.current['war3map.imp'] = imp(self.records)

    def write_zip(self, corrupt=False):
        with zipfile.ZipFile(self.archive, 'w') as z:
            for name, data in self.originals.items():
                z.writestr('author bundle/' + name, data)
            z.writestr('other model/Leoric.blp', b'wrong texture' if corrupt else self.originals['Leoric.blp'])

    def run_restore(self, check=False):
        with contextlib.redirect_stdout(io.StringIO()):
            restore.prepare(self.archive, check)

    def run_verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            verify.validate(FakeMpq(self.current), FakeMpq(self.before), self.manifest)

    def test_restore_exact_duplicates_and_idempotence(self):
        self.run_restore(); self.run_restore(); self.run_restore(True)
        for a in self.manifest['assets']:
            self.assertEqual((self.root / a['import_path']).read_bytes(), self.originals[a['name']])

    def test_bad_duplicate_fails_before_any_writes(self):
        self.write_zip(True)
        with self.assertRaises(ValueError): self.run_restore()
        self.assertFalse((self.root / 'imports/Leoric.blp').exists())

    def test_existing_conflict_preserved_and_no_partial_restore(self):
        target = self.root / 'imports/Leoric.blp'; target.write_bytes(b'collaborator content')
        with self.assertRaises(ValueError): self.run_restore()
        self.assertEqual(target.read_bytes(), b'collaborator content')
        self.assertFalse((self.root / 'imports/war3mapImported/Leoric.mdx').exists())

    def test_check_missing_asset_fails(self):
        with self.assertRaises(ValueError): self.run_restore(True)

    def test_artifact_visual_only_pass(self):
        self.run_verify()

    def test_changed_hp_fails(self):
        self.new_units['uB16'][1]['uhpm'] = 6801
        self.current['war3map.w3u'] = w3u(self.new_units)
        with self.assertRaises(AssertionError): self.run_verify()

    def test_changed_collision_fails(self):
        self.new_units['uB16'][1]['ucol'] = 50.0
        self.current['war3map.w3u'] = w3u(self.new_units)
        with self.assertRaises(AssertionError): self.run_verify()

    def test_parent_change_fails(self):
        self.new_units['uB16'] = ('Udre', self.new_units['uB16'][1])
        self.current['war3map.w3u'] = w3u(self.new_units)
        with self.assertRaises(AssertionError): self.run_verify()

    def test_other_boss_change_fails(self):
        self.new_units['uB08'][1]['umdl'] = 'wrong.mdx'
        self.current['war3map.w3u'] = w3u(self.new_units)
        with self.assertRaises(AssertionError): self.run_verify()

    def test_jass_change_fails(self):
        self.current['war3map.j'] = b'changed gameplay'
        with self.assertRaises(AssertionError): self.run_verify()

    def test_wrong_asset_hash_fails(self):
        self.current['Leoric.blp'] += b'x'
        with self.assertRaises(AssertionError): self.run_verify()

    def test_unknown_new_resource_fails(self):
        self.current['unapproved.mdx'] = b'unknown asset'
        with self.assertRaises(AssertionError): self.run_verify()

    def test_metadata_description_change_fails(self):
        self.current['war3map.w3i'] = self.current['war3map.w3i'].replace(b'description', b'changed description')
        with self.assertRaises(AssertionError): self.run_verify()

    def test_wrong_model_separator_fails(self):
        self.new_units['uB16'][1]['umdl'] = 'war3mapImported\\\\Leoric.mdx'
        self.current['war3map.w3u'] = w3u(self.new_units)
        with self.assertRaises(AssertionError): self.run_verify()

    def test_wrong_import_flag_fails(self):
        self.current['war3map.imp'] = imp([(10 if p == 'Leoric.blp' else f, p) for f, p in self.records])
        with self.assertRaises(AssertionError): self.run_verify()

    def test_duplicate_import_alias_fails(self):
        self.current['war3map.imp'] = imp(self.records + [(13, 'leoric.blp')])
        with self.assertRaises(AssertionError): self.run_verify()


if __name__ == '__main__':
    unittest.main()
