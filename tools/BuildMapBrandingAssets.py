#!/usr/bin/env python3
"""Offline, deterministic loading artwork conversion; no map/build invocation.

Run from the repository root: python tools/BuildMapBrandingAssets.py
Requires Pillow. Preserve the existing MDX and real war3mapMap.blp.
"""
import hashlib
import json
from pathlib import Path
import struct

from PIL import Image, __version__ as PILLOW_VERSION

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source/branding'
LOADING = 'ui/Glues/Loading/Load-Generic'
TILES = (
    ('TopLeft', (0, 0, 512, 512)),
    ('TopRight', (512, 0, 1024, 512)),
    ('BotLeft', (0, 512, 512, 768)),
    ('BotRight', (512, 512, 1024, 768)),
)
MODEL_SHA256 = '1cc5d2cb11b6f9166ce967eb8747b0aefb15ec5ac179d1508b311b9d3eb6b693'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def loading_tiles(image):
    """Quantize the whole canvas once, including mip filtering before splitting.

    A shared palette prevents independent quadrant color shifts. Each level is
    filtered across both seams before cropping. Keep the original BLP1 alpha0
    (fully opaque), dimensions and complete ten-level mip chains.
    """
    if image.width * 3 != image.height * 4:
        raise ValueError('Loading source must have an exact 4:3 aspect ratio')
    canvas = image.convert('RGB').resize((1024, 768), Image.Resampling.LANCZOS)
    palette = canvas.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    colors = palette.getpalette()
    colors += [0] * (768 - len(colors))
    bgra = bytes(v for i in range(256)
                 for v in (colors[i * 3 + 2], colors[i * 3 + 1], colors[i * 3], 0))
    payloads = {name: [] for name, _ in TILES}
    for level in range(10):
        width = max(1, 512 >> level)
        top, bottom = max(1, 512 >> level), max(1, 256 >> level)
        mip = canvas.resize((width * 2, top + bottom), Image.Resampling.LANCZOS)
        indexed = mip.quantize(palette=palette, dither=Image.Dither.NONE)
        for name, (left, upper, _right, _lower) in TILES:
            x, y = (0 if left == 0 else width), (0 if upper == 0 else top)
            height = top if upper == 0 else bottom
            payloads[name].append(indexed.crop((x, y, x + width, y + height)).tobytes())
    result = {}
    for name, (left, upper, right, lower) in TILES:
        offsets, sizes, cursor = [], [], 1180
        for data in payloads[name]:
            offsets.append(cursor); sizes.append(len(data)); cursor += len(data)
        offsets += [0] * 6; sizes += [0] * 6
        header = b'BLP1' + struct.pack('<6I', 1, 0, right - left, lower - upper, 5, 1)
        header += struct.pack('<16I', *offsets) + struct.pack('<16I', *sizes)
        result[name] = header + bgra + b''.join(payloads[name])
    return result


def lobby_tga(image):
    if image.width != image.height:
        raise ValueError('Lobby source must be square')
    image = image.convert('RGBA').resize((256, 256), Image.Resampling.LANCZOS)
    image.putalpha(255)
    # True-color type 2, no color map/RLE, 32-bit BGRA, top-left, 8-bit alpha.
    header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, 256, 256, 32, 0x28)
    return header + image.tobytes('raw', 'BGRA')


def main():
    model = ROOT / 'imports' / LOADING / 'Load-Generic.mdx'
    if sha(model.read_bytes()) != MODEL_SHA256:
        raise ValueError('Existing loading model changed; conversion will not rewrite it')
    provenance = json.loads((SOURCE / 'prompts-v2.json').read_text(encoding='utf-8'))
    if provenance['map_name'] != '契灵守卫战' or len(provenance['images']) != 2:
        raise ValueError('Unexpected approved source manifest')
    entries = []
    for item in provenance['images']:
        path = SOURCE / item['file']
        with Image.open(path) as image:
            entries.append({**item, 'path': str(path.relative_to(ROOT)),
                            'sha256': sha(path.read_bytes()), 'size': list(image.size)})
    loading = Image.open(SOURCE / '契灵守卫战-加载背景.png')
    thumbnail = Image.open(SOURCE / '契灵守卫战-地图缩略图.png')
    outputs = []
    for name, data in loading_tiles(loading).items():
        path = ROOT / 'imports' / LOADING / f'Generic-Loading-{name}.blp'
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        outputs.append({'path': str(path.relative_to(ROOT)), 'sha256': sha(data),
                        'bytes': len(data), 'mip_count': 10, 'alpha_bits': 0})
    preview = ROOT / 'imports/war3mapPreview.tga'
    data = lobby_tga(thumbnail); preview.write_bytes(data)
    outputs.append({'path': str(preview.relative_to(ROOT)), 'sha256': sha(data),
                    'bytes': len(data), 'size': [256, 256], 'alpha_range': [255, 255]})
    manifest = {**{key: value for key, value in provenance.items() if key != 'images'},
                'conversion': 'python tools/BuildMapBrandingAssets.py',
                'pillow_version': PILLOW_VERSION, 'images': entries, 'outputs': outputs,
                'loading_model': {'path': str(model.relative_to(ROOT)), 'sha256': MODEL_SHA256},
                'real_minimap_policy': 'Do not replace war3mapMap.blp'}
    (SOURCE / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Converted four opaque BLP1 tiles with shared palette/full mips and root lobby TGA; MDX unchanged.')


if __name__ == '__main__':
    main()
