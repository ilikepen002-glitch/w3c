"""Offline branding regressions; fixtures are never a built-map claim."""
from copy import deepcopy
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import BuildMapBrandingAssets as convert
import VerifyMapBrandingArtifact as gate
from GenerateTowerTerrainMask import Mpq
from VerifyGlobalRankingsArtifact import members, normalize_info


class Archive:
    def __init__(self, named):
        self.named = named
    def extract(self, path):
        return self.named[path.casefold()][1]


def branding_fixture():
    # Never turn the moving root map into the historical fixture oracle.
    frozen = subprocess.check_output(['git', 'show',
        '9e32bb6f5fc20d3efc5bd6a7973047364094d206:ExampleMap.w3x'], cwd=ROOT)
    baseline = members(Mpq(frozen))
    current = deepcopy(baseline)
    data = baseline['war3map.w3i'][1]
    fields, spans = gate.parse_info(data)
    values = {'name': gate.NAME + ' 20261012-2258-UTC+8',
              'title': gate.NAME + ' 20261012-2258-UTC+8',
              'description': gate.DESCRIPTION, 'loading_text': gate.DESCRIPTION}
    edits = {key: value.encode() + b'\0' for key, value in values.items()}
    edits['flags'] = struct.pack('<I', fields['flags'] & ~1)
    for key in sorted(edits, key=lambda key: spans[key][0], reverse=True):
        first, last = spans[key]; data = data[:first] + edits[key] + data[last:]
    current['war3map.w3i'] = ('war3map.w3i', data)
    script = baseline['war3map.j'][1]
    for native, old, new in [('SetMapName', fields['name'].split(' ')[0], gate.NAME),
                             ('SetMapDescription', fields['description'], gate.DESCRIPTION)]:
        old_call, new_call = f'call {native}("{old}")'.encode(), f'call {native}("{new}")'.encode()
        assert script.count(old_call) == 1
        script = script.replace(old_call, new_call)
    current['war3map.j'] = ('war3map.j', script)
    imports = baseline['war3map.imp'][1]
    version, count = struct.unpack_from('<II', imports)
    current['war3map.imp'] = ('war3map.imp', struct.pack('<II', version, count + 1) +
                              imports[8:] + b'\rwar3mapPreview.tga\0')
    for path in (*gate.TEXTURES.values(), gate.MODEL, gate.PREVIEW):
        current[path.casefold()] = (path, (ROOT / 'imports' / Path(path.replace('\\', '/'))).read_bytes())
    return Archive(current), Archive(baseline)


class BrandingAssets(unittest.TestCase):
    def test_shared_palette_full_mips_and_deterministic_conversion(self):
        source = Image.open(ROOT / 'assets/source/branding/契灵守卫战-加载背景.png')
        first = convert.loading_tiles(source); second = convert.loading_tiles(source)
        self.assertEqual(first, second)
        self.assertEqual(len({data[156:1180] for data in first.values()}), 1)
        stitched = Image.new('RGB', (1024, 768))
        for name, data in first.items():
            size = (512, 512 if name.startswith('Top') else 256)
            mips = gate.decode_loading_blp(data, size)
            self.assertEqual(len(mips), 10); self.assertEqual(mips[-1].size, (1, 1))
            self.assertEqual(data, (ROOT / 'imports' / convert.LOADING / f'Generic-Loading-{name}.blp').read_bytes())
            box = dict(convert.TILES)[name]; stitched.paste(mips[0], box[:2])
        canvas = source.convert('RGB').resize((1024, 768), Image.Resampling.LANCZOS)
        palette = canvas.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
        unsplit = canvas.quantize(palette=palette, dither=Image.Dither.NONE).convert('RGB')
        self.assertEqual(stitched.tobytes(), unsplit.tobytes(), 'Quadrant edges must exactly match the unsplit canvas')

    def test_reject_truncated_overlap_alpha_or_trailing_blp(self):
        data = (ROOT / 'imports' / convert.LOADING / 'Generic-Loading-TopLeft.blp').read_bytes()
        bad_alpha = bytearray(data); struct.pack_into('<I', bad_alpha, 8, 8)
        overlap = bytearray(data); struct.pack_into('<I', overlap, 32, 1180)
        for broken in (data[:-1], data + b'x', bytes(bad_alpha), bytes(overlap)):
            with self.assertRaises(ValueError): gate.decode_loading_blp(broken, (512, 512))

    def test_preview_opaque_uncompressed_truecolor(self):
        data = (ROOT / 'imports' / gate.PREVIEW).read_bytes()
        image = gate.decode_preview_tga(data)
        self.assertEqual(image.size, (256, 256)); self.assertEqual(image.getchannel('A').getextrema(), (255, 255))
        source = Image.open(ROOT / 'assets/source/branding/契灵守卫战-地图缩略图.png')
        self.assertEqual(data, convert.lobby_tga(source))
        broken = bytearray(data); broken[21] = 0
        with self.assertRaisesRegex(ValueError, 'opaque'): gate.decode_preview_tga(bytes(broken))

    def test_preserve_exact_loading_model_paths(self):
        data = (ROOT / 'imports' / Path(gate.MODEL.replace('\\', '/'))).read_bytes()
        self.assertEqual(gate.sha(data), convert.MODEL_SHA256)
        self.assertEqual(set(gate.model_textures(data)), set(gate.TEXTURES.values()))
        broken = bytearray(data); struct.pack_into('<I', broken, 12, 900)
        with self.assertRaisesRegex(ValueError, 'MDX800'): gate.model_textures(bytes(broken))

    def test_source_configuration_matches_exact_approved_text(self):
        self.assertEqual(set(gate.verify_source()), {name for name, _ in convert.TILES})

    def test_preview_configuration_allows_only_missing_or_strict_false(self):
        config = gate.yaml.safe_load((ROOT / 'wurst.build').read_text(encoding='utf-8'))
        flags = config['buildMapData']['optionsFlags']
        flags.pop('hideMinimapPreview', None)
        with patch.object(gate.yaml, 'safe_load', return_value=config):
            self.assertEqual(set(gate.verify_source()), {name for name, _ in convert.TILES})
            flags['hideMinimapPreview'] = False
            self.assertEqual(set(gate.verify_source()), {name for name, _ in convert.TILES})
            for invalid in (True, None, 0, 1, 'false', 'true', [], {}):
                flags['hideMinimapPreview'] = invalid
                with self.subTest(value=invalid), self.assertRaisesRegex(ValueError, 'strictly false'):
                    gate.verify_source()

    def test_loading_ratio_and_thumbnail_shape_rejected(self):
        with self.assertRaisesRegex(ValueError, '4:3'): convert.loading_tiles(Image.new('RGB', (5, 4)))
        with self.assertRaisesRegex(ValueError, 'square'): convert.lobby_tga(Image.new('RGB', (5, 4)))


class BrandingClosedDelta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current, cls.baseline = branding_fixture()
    def check(self, current=None):
        current = current or self.current
        with patch.object(gate, 'members', side_effect=lambda archive: archive.named):
            return gate.verify_archive(current, self.baseline)
    def changed(self, path, data):
        named = deepcopy(self.current.named); name, _ = named[path.casefold()]
        named[path.casefold()] = name, data
        return Archive(named)

    def test_closed_fixture_allows_branding_only(self):
        self.assertEqual(self.check()['display_name'], gate.NAME + ' 20261012-2258-UTC+8')

    def test_wrong_0x10_flag_clear_rejected(self):
        data = bytearray(self.current.extract('war3map.w3i')); fields, spans = gate.parse_info(data)
        struct.pack_into('<I', data, spans['flags'][0], fields['flags'] & ~0x10)
        with self.assertRaisesRegex(ValueError, 'Flags'): self.check(self.changed('war3map.w3i', bytes(data)))

    def test_restored_0x1_hidden_preview_flag_rejected(self):
        data = bytearray(self.current.extract('war3map.w3i')); fields, spans = gate.parse_info(data)
        struct.pack_into('<I', data, spans['flags'][0], fields['flags'] | 0x0001)
        with self.assertRaisesRegex(ValueError, 'Flags'): self.check(self.changed('war3map.w3i', bytes(data)))

    def test_wrong_author_or_nonmatching_title_rejected(self):
        data = self.current.extract('war3map.w3i')
        wrong_author = data.replace('留白散人'.encode(), '其他作者'.encode(), 1)
        wrong_title = data.replace(b'20261012-2258', b'20261012-2259', 1)
        for broken in (wrong_author, wrong_title):
            with self.assertRaises(ValueError): self.check(self.changed('war3map.w3i', broken))

    def test_gameplay_jass_or_real_minimap_mutation_rejected(self):
        for path in ('war3map.j', 'war3mapMap.blp', 'war3map.w3u'):
            with self.assertRaises(ValueError): self.check(self.changed(path, self.current.extract(path) + b'x'))

    def test_preview_must_use_root_exact_path_and_flag13(self):
        data = self.current.extract('war3map.imp')
        broken = data.replace(b'\rwar3mapPreview.tga\0', b'\nwar3mapPreview.tga\0')
        with self.assertRaisesRegex(ValueError, 'flag 13'): self.check(self.changed('war3map.imp', broken))
        broken = data.replace(b'war3mapPreview.tga\0', b'war3mapImported\\war3mapPreview.tga\0')
        with self.assertRaisesRegex(ValueError, 'flag 13'): self.check(self.changed('war3map.imp', broken))

    def test_historical_name_default_stays_frozen(self):
        def info(name, time):
            text = lambda value: value.encode() + b'\0'
            name += ' 20261012-' + time + '-UTC+8'
            return (struct.pack('<III', 25, 7, 6060) + text(name) + text('author') +
                    text('description') + text('1-4') + bytes(65) + text('model') +
                    text('loading') + text(name) + b'fixed-tail')
        old = info('深渊守望', '0123'); new = info(gate.NAME, '0123')
        normalize_info(old)
        with self.assertRaisesRegex(ValueError, 'timestamp'): normalize_info(new)
        normalize_info(new, expected_base_name=gate.NAME)
        with self.assertRaisesRegex(ValueError, 'timestamp'): normalize_info(old, expected_base_name=gate.NAME)
        with self.assertRaisesRegex(ValueError, 'nonempty'): normalize_info(new, expected_base_name='')


if __name__ == '__main__':
    unittest.main()
