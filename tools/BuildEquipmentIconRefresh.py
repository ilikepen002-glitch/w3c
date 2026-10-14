#!/usr/bin/env python3
"""Rebuild the five selected equipment atlas pairs; no image generation."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from BuildSpiritSkillIcons import ROOT,build,render
from BuildSemanticIcons import disabled_icon
MANIFEST=ROOT/'assets/source/equipment-icon-refresh/manifest.json'


def contact_sheet(output):
    manifest=json.loads(MANIFEST.read_text())
    sheet=Image.new('RGB',(1100,200),'#111922');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17)
    draw.text((15,10),'装备图标 · 5组 · 64×64原尺寸 / 禁用态 · 离线预览（非游戏截图）',font=font,fill='white')
    for index,e in enumerate(manifest['assets']):
        x=index*220;normal=render(e)
        sheet.paste(normal.convert('RGB'),(x+25,52));sheet.paste(disabled_icon(normal).convert('RGB'),(x+123,52))
        draw.text((x+18,128),e['display_name'],font=font,fill='white')
    sheet.save(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');p.add_argument('--contact-sheet',type=Path)
    args=p.parse_args();print(json.dumps(build(MANIFEST,check=args.check,expected_pairs=5)))
    if args.contact_sheet:contact_sheet(args.contact_sheet)
