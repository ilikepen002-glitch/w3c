#!/usr/bin/env python3
"""Label offline MDX/BLP renders; create per-species contact sheets and GIFs.
The GIF is a sequence of five offline actions, using their actual interval length.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ACTIONS = [('Display Float', 2000), ('Display Jump', 800), ('Display Spin', 1200),
           ('Display Sleep', 3000), ('Display Cast', 1200)]
BACKGROUND = (28, 34, 43, 255)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    args = p.parse_args()
    root = args.directory
    report = json.loads((root / 'sampling-report.json').read_text())
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    sheets = root / 'previews'
    sheets.mkdir(exist_ok=True)
    index = []
    for entry in report['models']:
        model = entry['model']
        directory = root / 'rendered' / model
        def render(action, i):
            source = Image.open(directory / (action.replace(' ', '-') + f'-{i:02d}.png')).convert('RGBA')
            background = Image.new('RGBA', source.size, BACKGROUND)
            background.alpha_composite(source)
            return background.convert('RGB')
        sheet = Image.new('RGB', (256 * 5, 224 * 5 + 80), BACKGROUND[:3])
        draw = ImageDraw.Draw(sheet)
        draw.text((12, 10), model + ' | Offline final MDX + original BLP; not Warcraft gameplay', font=font, fill='white')
        for col, (action, ms) in enumerate(ACTIONS):
            draw.text((col * 256 + 10, 38), f'{action} ({ms / 1000:g}s)', font=font, fill=(214, 229, 244))
            for row, i in enumerate((0, 2, 6, 10, 14)):
                sheet.paste(render(action, i), (col * 256, 70 + row * 224))
        sheet.save(sheets / (model + '-contact.png'))
        clip, durations = [], []
        for action, ms in ACTIONS:
            # One complete sequence per action. Sixteen equal frame intervals,
            # plus a short label/readability pause at its final pose.
            for i in range(17):
                frame = Image.new('RGB', (512, 496), BACKGROUND[:3])
                d = ImageDraw.Draw(frame)
                d.text((10, 8), model + ' | Offline MDX / BLP preview', font=font, fill='white')
                d.text((10, 30), f'{action} | native interval {ms / 1000:g}s', font=font, fill=(214, 229, 244))
                frame.paste(render(action, i).resize((512, 448), Image.Resampling.LANCZOS), (0, 48))
                clip.append(frame.quantize(colors=128, method=Image.Quantize.MEDIANCUT))
                durations.append(max(20, round(ms / 16 / 10) * 10) if i < 16 else 200)
        clip[0].save(sheets / (model + '-actions.gif'), save_all=True, append_images=clip[1:],
                     duration=durations, loop=0, disposal=2, optimize=False)
        index.append({'species': entry['species'], 'name': entry['name'], 'model': model,
                      'contact': model + '-contact.png', 'animation': model + '-actions.gif'})
    (sheets / 'index.json').write_text(json.dumps({'boundary': 'Offline art preview only; final MDX sampling and original BLP pixels. GIFs add 200ms end-of-action readability pauses.', 'models': index}, ensure_ascii=False, indent=2) + '\n')
    gallery = Image.new('RGB', (1280, 240 * 4 + 40), BACKGROUND[:3])
    d = ImageDraw.Draw(gallery)
    d.text((10, 10), '14 appended species | Offline MDX + BLP previews | Float / Cast midpoint pairs', font=font, fill='white')
    for i, entry in enumerate(index):
        x, y = (i % 4) * 320, (i // 4) * 240 + 40
        d.text((x + 8, y + 2), entry['model'], font=font, fill='white')
        for j, action in enumerate(('Display Float', 'Display Cast')):
            source = Image.open(root / 'rendered' / entry['model'] / (action.replace(' ', '-') + '-08.png')).convert('RGBA')
            source = source.resize((160, 140), Image.Resampling.LANCZOS)
            canvas = Image.new('RGBA', source.size, BACKGROUND)
            canvas.alpha_composite(source)
            gallery.paste(canvas.convert('RGB'), (x + j * 160, y + 30))
            d.text((x + j * 160 + 8, y + 175), action, font=font, fill=(214, 229, 244))
    gallery.save(sheets / 'all-fourteen-gallery.png')


if __name__ == '__main__':
    main()
