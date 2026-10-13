"""Read-only packed-icon regressions; mutations never modify a real map.

Object fixtures are parsed from the repository artifact then only approved icon
fields are normalized. Full actual-map validation is the verifier CLI with an
explicit frozen predecessor; fixtures do not claim that the current map passed.
"""
from copy import deepcopy
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
import importlib
import io
import json
import struct
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq, crypt, mpq_hash
from BuildEvolutionAssets import blp
import VerifySemanticIconArtifact as verifier


def replace_field(objects, kind, rawcode, field, value, level=0, column=0):
    obj = objects[kind][rawcode]
    key = field, level, column
    old = obj.fields.get(key)
    data_kind = 3 if isinstance(value, str) else 0
    header = field.encode('ascii') + struct.pack('<I', data_kind)
    if kind == 'abilities':
        header += struct.pack('<II', level, column)
    value_bytes = value.encode('utf-8') + b'\0' if data_kind == 3 else struct.pack('<i', value)
    marker = old.raw[-4:] if old else obj.identity[4:]
    obj.fields[key] = verifier.Field(key, data_kind, value, header + value_bytes + marker)


def serialize_objects(objects):
    output = bytearray(struct.pack('<I', 2))
    for table in range(2):
        selected = [obj for obj in objects.values() if obj.table == table]
        output.extend(struct.pack('<I', len(selected)))
        for obj in selected:
            output.extend(obj.encoded())
    return bytes(output)


def mpq_bytes(members):
    """Small genuine v0 archive fixture with real encrypted hash/block tables."""
    members = dict(members)
    members['(listfile)'] = ('\r\n'.join(members) + '\r\n(listfile)\r\n').encode()
    hash_count = 1
    while hash_count < len(members) * 2:
        hash_count *= 2
    hashes = [(0xFFFFFFFF, 0xFFFFFFFF, 0xFFFF, 0xFFFF, 0xFFFFFFFF)] * hash_count
    payload, blocks = bytearray(), []
    for index, (name, data) in enumerate(members.items()):
        blocks.append((32 + len(payload), len(data), len(data), 0x81000000))
        payload.extend(data)
        bucket = mpq_hash(name, 0) % hash_count
        while hashes[bucket][4] != 0xFFFFFFFF:
            bucket = (bucket + 1) % hash_count
        hashes[bucket] = (mpq_hash(name, 1), mpq_hash(name, 2), 0, 0, index)
    hash_offset = 32 + len(payload)
    block_offset = hash_offset + hash_count * 16
    hash_data = b''.join(struct.pack('<IIHHI', *record) for record in hashes)
    block_data = b''.join(struct.pack('<IIII', *record) for record in blocks)
    archive_size = block_offset + len(block_data)
    header = struct.pack('<4sIIHHIIII', b'MPQ\x1a', 32, archive_size, 0, 3,
                         hash_offset, block_offset, hash_count, len(blocks))
    return header + payload + crypt(hash_data, mpq_hash('(hash table)', 3), True) + crypt(
        block_data, mpq_hash('(block table)', 3), True)


def import_bytes(names):
    return struct.pack('<II', 1, len(names)) + b''.join(
        b'\r' + name.encode('utf-8') + b'\0' for name in names)


def test_image(seed):
    image = Image.new('RGBA', (80, 72))
    image.putdata([((x * 11 + seed * 17) % 256, (y * 13 + seed * 7) % 256,
                    (x * y + seed * 23) % 256, 30 + (x + y + seed) % 226)
                   for y in range(72) for x in range(80)])
    return image


class ObjectDeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        artifact = Mpq((ROOT / 'ExampleMap.w3x').read_bytes())
        cls.baseline = verifier.load_objects(artifact)
        cls.corrected = deepcopy(cls.baseline)
        for (kind, rawcode, (field, level, column)), path in verifier.BINDINGS.items():
            replace_field(cls.corrected, kind, rawcode, field, path, level, column)

    def setUp(self):
        self.objects = deepcopy(self.corrected)

    def test_exact_bindings_and_only_permitted_binary_delta_pass(self):
        verifier.verify_object_delta(self.objects, self.baseline)
        self.assertEqual(len(verifier.EQUIPMENT), 26)
        self.assertEqual(len(verifier.expected_asset_contract()), 30)
        self.assertEqual(len([key for key in verifier.BINDINGS
                              if key[0] == 'units' and key[1].startswith('p')]), 192)
        self.assertIn(('units', 'p203', ('ussi', 0, 0)), verifier.BINDINGS)

    def test_parser_preserves_binary_fields_and_object_order(self):
        for kind, (_, extended) in verifier.OBJECT_FILES.items():
            encoded = serialize_objects(self.objects[kind])
            parsed = verifier.parse_objects(encoded, extended)
            self.assertEqual(encoded, serialize_objects(parsed))
            self.assertEqual(parsed, self.objects[kind])

    def test_rejects_every_equipment_misbinding(self):
        for rawcode in verifier.EQUIPMENT:
            with self.subTest(rawcode=rawcode):
                objects = deepcopy(self.corrected)
                replace_field(objects, 'items', rawcode, 'iico', verifier.icon_path('TDItemShortBow')
                              if rawcode != 'iW01' else verifier.icon_path('TDItemSteelLongbow'))
                with self.assertRaisesRegex(ValueError, 'exact global icon binding mismatch'):
                    verifier.verify_object_delta(objects, self.baseline)

    def test_rejects_critical_strike_using_sword_dance(self):
        for rawcode in ('A102', 'A112'):
            replace_field(self.objects, 'abilities', rawcode, 'aart', verifier.icon_path('TDTowerSwordDance'))
            with self.subTest(rawcode=rawcode), self.assertRaisesRegex(ValueError, rawcode):
                verifier.verify_bindings(self.objects)
            self.objects = deepcopy(self.corrected)

    def test_rejects_action_reuse_and_research_misbinding(self):
        for rawcode in verifier.ACTIONS:
            objects = deepcopy(self.corrected)
            replace_field(objects, 'abilities', rawcode, 'arar', verifier.icon_path('TDActionGroundUpgrade')
                          if rawcode != 'Gupg' else verifier.icon_path('TDActionCaptureOrb'))
            with self.subTest(rawcode=rawcode), self.assertRaisesRegex(ValueError, rawcode):
                verifier.verify_bindings(objects)

    def test_rejects_missing_wild_portrait_for_each_wave_and_species(self):
        for wave in range(1, 33):
            for species in range(1, 4):
                rawcode = f'p{wave:02X}{species}'
                objects = deepcopy(self.corrected)
                del objects['units'][rawcode].fields['ussi', 0, 0]
                with self.subTest(rawcode=rawcode), self.assertRaisesRegex(ValueError, rawcode):
                    verifier.verify_bindings(objects)

    def test_rejects_native_bloodlust_pollution_bright_and_locked(self):
        for slot in range(4):
            for variant in (44, 47, 108, 111):
                objects = deepcopy(self.corrected)
                rawcode = f's{slot}{variant:02X}'
                replace_field(objects, 'abilities', rawcode, 'aart', verifier.icon_path('TDTowerBloodlust', variant >= 64))
                with self.subTest(rawcode=rawcode), self.assertRaisesRegex(ValueError, 'native BloodLust icon polluted'):
                    verifier.verify_object_delta(objects, self.baseline)

    def test_rejects_arbitrary_icon_change_on_unapproved_object(self):
        replace_field(self.objects, 'abilities', 'Pc00', 'aart', verifier.icon_path('TDActionCaptureOrb'))
        with self.assertRaisesRegex(ValueError, 'forbidden non-icon or non-allowlisted'):
            verifier.verify_object_delta(self.objects, self.baseline)

    def test_rejects_non_icon_change_on_allowed_object(self):
        replace_field(self.objects, 'abilities', 'A102', 'ahky', 'Z')
        with self.assertRaisesRegex(ValueError, 'forbidden non-icon or non-allowlisted'):
            verifier.verify_object_delta(self.objects, self.baseline)

    def test_rejects_entire_pet_slot_change_including_order(self):
        for rawcode in ('s000', 's180', 's37F'):
            objects = deepcopy(self.corrected)
            obj = objects['abilities'][rawcode]
            obj.fields = dict(reversed(list(obj.fields.items())))
            with self.subTest(rawcode=rawcode), self.assertRaisesRegex(ValueError, 'wholly identical'):
                verifier.verify_object_delta(objects, self.baseline)

    def test_rejects_pcap_functional_change_at_first_middle_last_level(self):
        for level in (1, 31, 61):
            objects = deepcopy(self.corrected)
            replace_field(objects, 'abilities', 'Pcap', 'aub1', 'changed functional tooltip', level)
            with self.subTest(level=level), self.assertRaisesRegex(ValueError, 'forbidden non-icon'):
                verifier.verify_object_delta(objects, self.baseline)

    def test_rejects_pcap_icon_at_functional_level(self):
        replace_field(self.objects, 'abilities', 'Pcap', 'aart', verifier.icon_path('TDActionCaptureOrb'), 61)
        with self.assertRaisesRegex(ValueError, 'global, not level-specific'):
            verifier.verify_bindings(self.objects)

    def test_rejects_parent_identity_and_object_set_changes(self):
        self.objects['abilities']['A102'].identity = b'Axxx' + b'A102'
        with self.assertRaisesRegex(ValueError, 'identity/parent/table'):
            verifier.verify_object_delta(self.objects, self.baseline)
        self.objects = deepcopy(self.corrected)
        del self.objects['items']['iW07']
        with self.assertRaises((ValueError, KeyError)):
            verifier.verify_object_delta(self.objects, self.baseline)

    def test_rejects_icon_metadata_or_endmarker_change(self):
        obj = self.objects['abilities']['A102']
        key = ('aart', 0, 0)
        field = obj.fields[key]
        obj.fields[key] = replace(field, raw=field.raw[:-4] + b'nope')
        with self.assertRaisesRegex(ValueError, 'icon encoding metadata changed'):
            verifier.verify_object_delta(self.objects, self.baseline)

    def test_parser_rejects_duplicate_field_truncation_and_trailer(self):
        obj = next(iter(self.corrected['abilities'].values()))
        field = next(iter(obj.fields.values())).raw
        data = struct.pack('<II', 2, 0) + struct.pack('<I', 1) + obj.identity + struct.pack('<I', 2) + field * 2
        with self.assertRaisesRegex(ValueError, 'duplicate field'):
            verifier.parse_objects(data, True)
        valid = serialize_objects(self.corrected['items'])
        for invalid in (valid[:-1], valid + b'x'):
            with self.assertRaises(ValueError):
                verifier.parse_objects(invalid, False)


class PackedPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'imports').mkdir()
        self.names = [verifier.icon_path('TDActionCaptureOrb')]
        self.data = {name: b'test' for name in self.names}
        (self.root / 'imports' / Path(self.names[0].replace('\\', '/'))).parent.mkdir(parents=True)
        (self.root / 'imports' / Path(self.names[0].replace('\\', '/'))).write_bytes(b'test')

    def tearDown(self):
        self.temp.cleanup()

    def artifact(self, names=None, data=None):
        members = dict(self.data if data is None else data)
        members['war3map.imp'] = import_bytes(self.names if names is None else names)
        return Mpq(mpq_bytes(members))

    def test_genuine_mpq_read_and_unique_import_paths_pass(self):
        artifact = self.artifact()
        self.assertEqual(artifact.extract(self.names[0].lower()), b'test')
        verifier.verify_paths(artifact, self.root)

    def test_rejects_each_obsolete_tower_normal_and_disabled_path(self):
        for stem in verifier.TOWER_STEMS:
            for disabled in (False, True):
                old = verifier.icon_path(stem, disabled)
                with self.subTest(old=old), self.assertRaisesRegex(ValueError, 'Obsolete tower/native collision'):
                    verifier.verify_paths(self.artifact(self.names + [old], {**self.data, old: b'old'}), self.root)

    def test_rejects_old_collision_case_insensitively_even_hidden_from_listfile(self):
        old = verifier.icon_path('Bloodlust', True).swapcase()
        artifact = self.artifact(self.names, {**self.data, old: b'pollution'})
        # Hiding an entry's name must not make direct MPQ hash lookup pass.
        original = artifact.extract
        artifact.extract = lambda name: b'war3map.imp\r\n(listfile)\r\n' if name == '(listfile)' else original(name)
        with self.assertRaisesRegex(ValueError, 'Obsolete tower/native collision'):
            verifier.verify_paths(artifact, self.root)

    def test_rejects_stale_old_path_listing_without_an_mpq_member(self):
        artifact = self.artifact()
        original = artifact.extract
        old = verifier.icon_path('Bloodlust', True).swapcase()
        artifact.extract = lambda name: original(name) + (old + '\r\n').encode() if name == '(listfile)' else original(name)
        self.assertFalse(artifact.has(old))
        with self.assertRaisesRegex(ValueError, 'Obsolete tower/native collision'):
            verifier.verify_paths(artifact, self.root)

    def test_rejects_native_normal_bloodlust_resource_override(self):
        path = verifier.NATIVE + 'BTNBloodLust.blp'
        with self.assertRaisesRegex(ValueError, 'Obsolete tower/native collision'):
            verifier.verify_paths(self.artifact(self.names + [path], {**self.data, path: b'pollution'}), self.root)

    def test_rejects_old_collision_filesystem_import_case_insensitively(self):
        old = self.root / 'imports' / Path(verifier.icon_path('Bloodlust', True).swapcase().replace('\\', '/'))
        old.parent.mkdir(parents=True)
        old.write_bytes(b'pollution')
        with self.assertRaisesRegex(ValueError, 'Obsolete tower/native collision'):
            verifier.verify_paths(self.artifact(), self.root)

    def test_rejects_casefold_duplicate_import_manifest(self):
        with self.assertRaisesRegex(ValueError, 'war3map.imp: casefold duplicate'):
            verifier.verify_paths(self.artifact(self.names + [self.names[0].swapcase()]), self.root)

    def test_rejects_casefold_duplicate_mpq_listfile_and_hash_entry(self):
        duplicate = self.names[0].swapcase()
        artifact = self.artifact(self.names, {**self.data, duplicate: b'other'})
        with self.assertRaisesRegex(ValueError, 'MPQ listfile: casefold duplicate'):
            verifier.verify_paths(artifact, self.root)
        original = artifact.extract
        artifact.extract = lambda name: b'war3map.imp\r\n(listfile)\r\n' if name == '(listfile)' else original(name)
        with self.assertRaisesRegex(ValueError, 'MPQ hash table: duplicate'):
            verifier.verify_paths(artifact, self.root)

    def test_rejects_casefold_duplicate_filesystem_import(self):
        duplicate = self.root / 'imports' / Path(self.names[0].swapcase().replace('\\', '/'))
        duplicate.parent.mkdir(parents=True)
        duplicate.write_bytes(b'other')
        with self.assertRaisesRegex(ValueError, 'imports: casefold duplicate'):
            verifier.verify_paths(self.artifact(), self.root)

    def test_rejects_doubled_prefix_separator_and_path_traversal(self):
        for path in ('war3mapImported\\\\BTNBad.blp', 'war3mapImported/BTNBad.blp', '../BTNBad.blp'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'Non-canonical'):
                verifier.unique_paths([path], 'test')


class BlpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        image = test_image(1).resize((64, 64), Image.Resampling.LANCZOS)
        cls.image = image
        path = Path(cls.temp.name) / 'normal.blp'
        blp(image, path)
        cls.data = path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_all_seven_mips_decode_to_independent_source_palette_and_alpha(self):
        decoded = verifier.decode_blp(self.data, 'test.blp')
        expected = verifier.expected_pixels(self.image)
        self.assertEqual(len(decoded), 7)
        for actual, wanted in zip(decoded, expected):
            self.assertEqual(actual.tobytes(), wanted.tobytes())

    def test_rejects_missing_overlapping_wrong_size_extra_and_truncated_mip(self):
        for offset, value in ((28 + 6 * 4, 0), (28 + 3 * 4, 1180),
                              (92 + 5 * 4, 1), (28 + 7 * 4, 1)):
            data = bytearray(self.data)
            struct.pack_into('<I', data, offset, value)
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                verifier.decode_blp(bytes(data), 'test.blp')
        with self.assertRaises(ValueError):
            verifier.decode_blp(self.data[:-1], 'test.blp')

    def test_rejects_missing_alpha_encoding_and_fully_transparent_payload(self):
        data = bytearray(self.data)
        struct.pack_into('<I', data, 8, 0)
        with self.assertRaisesRegex(ValueError, 'alpha8/mips'):
            verifier.decode_blp(bytes(data), 'test.blp')
        data = bytearray(self.data)
        data[1180 + 4096:1180 + 8192] = b'\0' * 4096
        with self.assertRaisesRegex(ValueError, 'fully transparent'):
            verifier.decode_blp(bytes(data), 'test.blp')

    def test_read_only_import_does_not_invoke_generators(self):
        # Importing verifier has no filesystem-writing/build side effects.
        importlib.reload(verifier)
        self.assertEqual(self.data, (Path(self.temp.name) / 'normal.blp').read_bytes())


class ResourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.manifest = {'schemaVersion': 1, 'assets': [], 'towerMigrations': [], 'preservedPetUI': []}
        cls.members, baseline_members = {}, {}
        specifications = [('assets', name, stem, rawcodes)
                          for name, (stem, rawcodes) in verifier.expected_asset_contract().items()]
        specifications += [('towerMigrations', name, 'TDTower' + name, set()) for name in verifier.TOWER_STEMS]
        specifications += [('preservedPetUI', name, name, set()) for name in verifier.PET_STEMS]
        for seed, (category, name, stem, rawcodes) in enumerate(specifications, 1):
            source = cls.root / 'sources' / f'{name}.png'
            source.parent.mkdir(exist_ok=True)
            test_image(seed).save(source)
            entry = {'name': name, 'normal': verifier.icon_path(stem), 'disabled': verifier.icon_path(stem, True),
                     'source': str(source.relative_to(cls.root)), 'crop': [0, 0, 80, 72],
                     'source_sha256': verifier.sha(source.read_bytes()), 'rawcodes': sorted(rawcodes)}
            image = verifier.source_icon(entry, cls.root)
            for disabled in (False, True):
                key = 'disabled' if disabled else 'normal'
                path = cls.root / 'imports' / Path(entry[key].replace('\\', '/'))
                blp(verifier.disabled_image(image) if disabled else image, path)
                data = path.read_bytes()
                cls.members[entry[key]] = data
                entry[key + '_sha256'] = verifier.sha(data)
                if category != 'assets':
                    old = verifier.icon_path(name, disabled) if category == 'towerMigrations' else entry[key]
                    baseline_members[old] = data
                    if category == 'towerMigrations':
                        entry['old_' + key] = old
            cls.manifest[category].append(entry)
        cls.names = list(cls.members)
        cls.members['war3map.imp'] = import_bytes(cls.names)
        cls.baseline = Mpq(mpq_bytes(baseline_members))
        cls.artifact = Mpq(mpq_bytes(cls.members))
        cls.paths = verifier.verify_paths(cls.artifact, cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def verify(self, artifact=None, manifest=None, paths=None):
        return verifier.verify_resources(artifact or self.artifact, self.baseline, self.root,
                                         manifest or self.manifest, paths or self.paths)

    def test_all_30_new_11_migrated_and_13_preserved_pairs_pass_real_mpq(self):
        decoded = self.verify()
        self.assertEqual(len(decoded), 108)

    def test_cli_verifies_real_mpq_objects_and_resources_without_mutating_inputs(self):
        predecessor = verifier.load_objects(Mpq((ROOT / 'ExampleMap.w3x').read_bytes()))
        corrected = deepcopy(predecessor)
        for (kind, rawcode, (field, level, column)), path in verifier.BINDINGS.items():
            replace_field(corrected, kind, rawcode, field, path, level, column)
        old_members = self.baseline.members()
        members = dict(self.members)
        for kind, (path, _extended) in verifier.OBJECT_FILES.items():
            old_members[path] = serialize_objects(predecessor[kind])
            members[path] = serialize_objects(corrected[kind])
        with tempfile.TemporaryDirectory() as outside:
            directory = Path(outside)
            before, after = directory / 'baseline.w3x', directory / 'final.w3x'
            before.write_bytes(mpq_bytes(old_members))
            after.write_bytes(mpq_bytes(members))
            manifest = directory / 'manifest.json'
            manifest.write_text(json.dumps(self.manifest))
            sheet = directory / 'offline.png'
            snapshot = {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
            output = io.StringIO()
            with redirect_stdout(output):
                verifier.main([str(after), '--baseline-map', str(before), '--root', str(self.root),
                               '--manifest', str(manifest), '--contact-sheet', str(sheet)])
            self.assertIn('FINAL MAP SHA256: ' + verifier.sha(after.read_bytes()), output.getvalue())
            self.assertIn('OFFLINE NON-GAMEPLAY CONTACT SHEET:', output.getvalue())
            self.assertTrue(sheet.is_file())
            self.assertEqual(snapshot, {path: path.read_bytes() for path in self.root.rglob('*') if path.is_file()})

    def test_rejects_wrong_packed_bytes_even_when_manifest_hash_changed(self):
        entry = self.manifest['assets'][0]
        path = entry['normal']
        members = deepcopy(self.members)
        members[path] = members[path][:-1] + bytes([members[path][-1] ^ 1])
        with self.assertRaisesRegex(ValueError, 'packed bytes differ from imports'):
            self.verify(Mpq(mpq_bytes(members)))

    def test_rejects_changed_alpha_and_mip_pixels_even_with_matching_imports_and_hash(self):
        entry = self.manifest['assets'][0]
        path = entry['normal']
        local = self.root / 'imports' / Path(path.replace('\\', '/'))
        original = local.read_bytes()
        offsets = struct.unpack_from('<16I', original, 28)
        for level in (0, 3, 6):
            for alpha in (False, True):
                manifest = deepcopy(self.manifest)
                data = bytearray(original)
                count = (64 >> level) ** 2
                offset = offsets[level] + (count if alpha else 0)
                data[offset] ^= 0x7F
                members = deepcopy(self.members)
                members[path] = bytes(data)
                local.write_bytes(data)
                manifest['assets'][0]['normal_sha256'] = verifier.sha(data)
                try:
                    with self.subTest(level=level, alpha=alpha), self.assertRaisesRegex(ValueError, 'pixels/alpha mismatch'):
                        self.verify(Mpq(mpq_bytes(members)), manifest)
                finally:
                    local.write_bytes(original)

    def test_rejects_changed_preserved_tower_and_pet_bytes_even_with_matching_hash(self):
        for category in ('towerMigrations', 'preservedPetUI'):
            manifest = deepcopy(self.manifest)
            entry = manifest[category][0]
            path = entry['normal']
            local = self.root / 'imports' / Path(path.replace('\\', '/'))
            original = local.read_bytes()
            data = bytearray(original)
            data[1180 + 4096] ^= 1
            members = deepcopy(self.members)
            members[path] = bytes(data)
            local.write_bytes(data)
            entry['normal_sha256'] = verifier.sha(data)
            try:
                with self.subTest(category=category), self.assertRaisesRegex(ValueError, 'preserved baseline artwork bytes changed'):
                    self.verify(Mpq(mpq_bytes(members)), manifest)
            finally:
                local.write_bytes(original)

    def test_rejects_missing_packed_resource_and_manifest_binding_mutations(self):
        members = deepcopy(self.members)
        del members[self.manifest['assets'][0]['normal']]
        with self.assertRaisesRegex(ValueError, 'Missing exact imported/packed'):
            self.verify(Mpq(mpq_bytes(members)))
        for key, value in (('normal', verifier.icon_path('TDItemWrong')), ('rawcodes', ['iW03'])):
            manifest = deepcopy(self.manifest)
            manifest['assets'][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'manifest .* mismatch'):
                self.verify(manifest=manifest)

    def test_rejects_source_hash_wrong_crop_or_absent_source(self):
        for key, value in (('source_sha256', '0' * 64), ('crop', [0, 0, 9999, 9999]),
                           ('source', '/tmp/outside.png')):
            manifest = deepcopy(self.manifest)
            manifest['assets'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.verify(manifest=manifest)

    def test_contact_sheet_uses_decoded_map_pixels_and_stays_outside_repo(self):
        decoded = self.verify()
        with tempfile.TemporaryDirectory() as outside:
            target = verifier.contact_sheet(decoded, self.manifest, 'a' * 64,
                                            Path(outside) / 'offline.png', self.root)
            self.assertTrue(target.is_file())
            with Image.open(target) as image:
                self.assertEqual(image.size, (1792, 2730))
        with self.assertRaisesRegex(ValueError, 'outside repository'):
            verifier.contact_sheet(decoded, self.manifest, 'a' * 64, self.root / 'bad.png', self.root)


if __name__ == '__main__':
    unittest.main()
