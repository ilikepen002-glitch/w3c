#!/usr/bin/env python3
"""Build 15 actual model portraits, 60 quality and 240 owned-count BLP1 icons.
Uses final MDX Portrait renders and unchanged v5 SVG frame/count outlines.
Only renders asset files; never invokes Wurst, staging, map build or the game.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from PIL import Image, ImageEnhance, ImageOps, __version__ as PILLOW_VERSION
from BuildEvolutionAssets import blp
from BuildPetUiAssets import decode_blp
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/elemental-spirits'
MANIFEST=SOURCE/'ui-manifest.json'
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def render_svg(portrait, quality, count):
    suffix=(f'Q{quality}' if quality else '')+(f'N{count}' if count else '')
    template=ROOT/f'assets/source/pet-ui/TDPetFlamePhoenix{suffix}.svg'
    root=ET.fromstring(template.read_bytes())
    children=list(root)
    art=next(n for n in children if n.tag==f'{{{NS}}}g')
    index=children.index(art)
    root.remove(art)
    image=ET.Element(f'{{{NS}}}image',{'x':'6','y':'6','width':'52','height':'52','href':'data:image/png;base64,'+base64.b64encode(portrait.read_bytes()).decode()})
    root.insert(index,image)
    return ET.tostring(root)

def build(inkscape):
    assets=[]
    with tempfile.TemporaryDirectory(prefix='td-element-icons-') as directory:
        temp=Path(directory)
        for species in range(1,16):
            source=SOURCE/f'portraits/species-{species:02d}.png'
            assert source.is_file()
            for quality,count in [(0,0),*((q,0) for q in range(1,5)),*((q,n) for q in range(1,5) for n in range(1,5))]:
                stem=f'TDPetSpecies{species:02d}'+(f'Q{quality}' if quality else '')+(f'N{count}' if count else '')
                svg=temp/'icon.svg';png=temp/'icon.png'
                svg.write_bytes(render_svg(source,quality,count))
                subprocess.run([inkscape,str(svg),'--export-type=png',f'--export-filename={png}','--export-width=256','--export-height=256'],check=True,capture_output=True)
                with Image.open(png) as rendered:
                    normal=rendered.convert('RGBA').resize((64,64),Image.Resampling.LANCZOS)
                assert normal.getchannel('A').getextrema()==(255,255)
                normal_path=ROOT/f'imports/war3mapImported/BTN{stem}.blp'
                disabled_path=ROOT/f'imports/ReplaceableTextures/CommandButtonsDisabled/DISBTN{stem}.blp'
                blp(normal,normal_path)
                disabled=ImageEnhance.Brightness(ImageOps.grayscale(normal).convert('RGBA')).enhance(.45)
                blp(disabled,disabled_path)
                assets.append({'species':species,'quality':quality,'ownedCount':count,'name':stem,'normal':str(normal_path.relative_to(ROOT)),'disabled':str(disabled_path.relative_to(ROOT)),'normalSha256':sha(normal_path),'disabledSha256':sha(disabled_path),'portraitSha256':sha(source)})
    manifest={'version':1,'basis':'Final MDX800 embedded Portrait-camera pose, true BLP texture; v5 original frame/quality/count outlines','gameTested':False,'species':15,'qualityPortraits':60,'ownedCountPortraits':240,'toolVersions':{'inkscape':subprocess.run([inkscape,'--version'],capture_output=True,text=True,check=True).stdout.strip(),'pillow':PILLOW_VERSION},'assets':assets}
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    verify()

def verify():
    manifest=json.loads(MANIFEST.read_text())
    assert len(manifest['assets'])==315
    seen=set()
    for a in manifest['assets']:
        key=(a['species'],a['quality'],a['ownedCount'])
        assert key not in seen;seen.add(key)
        for field,hashfield in [('normal','normalSha256'),('disabled','disabledSha256')]:
            path=ROOT/a[field];assert sha(path)==a[hashfield];decode_blp(path)
        assert sha(SOURCE/f"portraits/species-{a['species']:02d}.png")==a['portraitSha256']
    for species in range(1,16):
        assert {(s,q,n) for s,q,n in seen if s==species}=={(species,0,0),*((species,q,0) for q in range(1,5)),*((species,q,n) for q in range(1,5) for n in range(1,5))}
    print('PASS: 315 distinct BTN/DIS pairs; 15 portraits, 60 quality, 240 count variants; SHA/BLP1 alpha8/7mips checked')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify-only',action='store_true');p.add_argument('--inkscape',default=shutil.which('inkscape'));a=p.parse_args()
    verify() if a.verify_only else build(a.inkscape)
