#!/usr/bin/env python3
"""Deterministically materialize the selected imagegen atlas as 25 BTN/DISBTN pairs.

No image generation or repainting: explicit atlas crop, 64px LANCZOS resize,
grayscale/45%-brightness disabled state, and the project's BLP1 alpha8 encoder.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zlib
from PIL import Image, ImageDraw, ImageFont
from BuildEvolutionAssets import blp
from BuildSemanticIcons import disabled_icon

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'assets/source/spirit-skill-icons/manifest.json'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render(entry, root=ROOT):
    source = root / entry['source']
    if sha(source.read_bytes()) != entry['source_sha256']:
        raise ValueError('Selected atlas source hash mismatch')
    with Image.open(source) as opened:
        image = opened.convert('RGBA')
    x0, y0, x1, y1 = entry['crop']
    if not (0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height):
        raise ValueError('Invalid atlas crop')
    return image.crop((x0, y0, x1, y1)).resize((64, 64), Image.Resampling.LANCZOS)


def build(manifest_path=MANIFEST, root=ROOT, check=False, expected_pairs=25):
    manifest = json.loads(manifest_path.read_text())
    if len(manifest['assets']) != expected_pairs or len({a['name'] for a in manifest['assets']}) != expected_pairs:
        raise ValueError(f'Expected exactly {expected_pairs} selected icon pairs')
    prepared = []
    with tempfile.TemporaryDirectory(prefix='spirit-icons-') as tmp:
        temp = Path(tmp) / 'icon.blp'
        for entry in manifest['assets']:
            image = render(entry, root)
            for key, frame in [('normal', image), ('disabled', disabled_icon(image))]:
                path = root / 'imports' / entry[key].replace('\\', '/')
                if not path.resolve().is_relative_to((root / 'imports').resolve()):
                    raise ValueError('Output escapes imports')
                blp(frame, temp)
                data = temp.read_bytes()
                if sha(data) != entry[key + '_sha256']:
                    raise ValueError('Manifest output hash mismatch: ' + entry['name'])
                if check and (not path.exists() or path.read_bytes() != data):
                    raise ValueError('Non-reproducible BLP: ' + str(path))
                prepared.append((path, data))
    if not check:
        for path, data in prepared:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    # Estimate only. The packed-map gate separately measures actual MPQ blocks.
    estimate = sum(len(zlib.compress(data, 9)) for _, data in prepared)
    if estimate > manifest['max_added_mpq_bytes']:
        raise ValueError('Pre-build compressed budget exceeded')
    return {'pairs': expected_pairs, 'raw_bytes': sum(len(d) for _, d in prepared),
            'zlib_estimate_bytes': estimate, 'actual_mpq_measurement': 'requires final map'}


def contact_sheet(output, manifest_path=MANIFEST):
    manifest = json.loads(manifest_path.read_text())
    result = Image.new('RGB', (1100, 730), '#111922')
    draw = ImageDraw.Draw(result)
    font_path = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    font = ImageFont.truetype(font_path, 17)
    small = ImageFont.truetype(font_path, 13)
    draw.text((16, 9), '精灵技能图标 · 25组 · 64×64原尺寸 / 禁用态 · 离线预览（非游戏截图）',font=font,fill='white')
    for index, entry in enumerate(manifest['assets']):
        x,y = (index % 5) * 220, 48 + (index // 5) * 135
        image = render(entry)
        result.paste(image.convert('RGB'), (x+25,y))
        result.paste(disabled_icon(image).convert('RGB'), (x+123,y))
        draw.text((x+16,y+71),entry['display_name'],font=font,fill='white')
        draw.text((x+16,y+96),f"ID {entry['skill_id']:02d} · 正常 / 禁用",font=small,fill='#9cabba')
    result.save(output)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check',action='store_true')
    p.add_argument('--contact-sheet',type=Path)
    args=p.parse_args()
    print(json.dumps(build(check=args.check),ensure_ascii=False))
    if args.contact_sheet: contact_sheet(args.contact_sheet)
