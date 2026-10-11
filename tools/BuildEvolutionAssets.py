"""Deterministic PNG -> BLP1 alpha8/mipmaps and low-poly wing MDL sources.
Run from repo root; requires Pillow. Then run node tools/asset-converter/convert.cjs.
"""
from pathlib import Path
import struct
from PIL import Image, ImageOps, ImageEnhance
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/source'
OUT = ROOT / 'imports/war3mapImported'
TOWER_ICON_NAMES = frozenset([
    'SplitShot', 'TrueshotAura', 'SwordDance', 'Bloodlust', 'Bladestorm',
    'ShieldBash', 'CommandAura', 'PoisonDart', 'VinesAura', 'Frenzy', 'CorpseExplosion',
])

def tower_icon_stem(name):
    if name not in TOWER_ICON_NAMES:
        raise ValueError(f'Unknown tower icon source: {name}')
    return 'TDTower' + name

def remove_legacy_tower_icon(name):
    tower_icon_stem(name)  # Restrict cleanup to the eleven approved tower names.
    # MPQ path lookup is case-insensitive. A legacy DISBTNBloodlust import also
    # replaces native DISBTNBloodLust, so future rebuilds must not resurrect it.
    for folder, prefix in [(OUT, 'BTN'), (ROOT / 'imports/ReplaceableTextures/CommandButtonsDisabled', 'DISBTN')]:
        legacy = (prefix + name + '.blp').casefold()
        for path in folder.glob('*.blp'):
            if path.name.casefold() == legacy:
                path.unlink()

def blp(image, path):
    image = image.convert('RGBA')
    width, height = image.size
    palette = image.convert('RGB').quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    colors = palette.getpalette()
    colors += [0] * (768 - len(colors))
    bgra = bytes(v for i in range(256) for v in (colors[i*3+2], colors[i*3+1], colors[i*3], 0))
    payload, sizes, offsets = [], [], []
    cursor = 156 + 1024
    for level in range(16):
        w, h = max(1, width >> level), max(1, height >> level)
        mip = image.resize((w, h), Image.Resampling.LANCZOS)
        indexed = mip.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE)
        data = indexed.tobytes() + mip.getchannel('A').tobytes()
        offsets.append(cursor)
        sizes.append(len(data))
        payload.append(data)
        cursor += len(data)
        if w == h == 1:
            break
    offsets += [0] * (16 - len(offsets))
    sizes += [0] * (16 - len(sizes))
    header = b'BLP1' + struct.pack('<6I', 1, 8, width, height, 5, 1)
    header += struct.pack('<16I', *offsets) + struct.pack('<16I', *sizes)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + bgra + b''.join(payload))

def wing_mdl(choice, width, base, height):
    geosets = []
    for side in range(2):
        y0, y1 = (-width, 0) if side == 0 else (0, width)
        u0, u1 = (0, 0.5) if side == 0 else (0.5, 1)
        vertices = [(-20,y0,base), (-20,y1,base), (-20,y1,base+height), (-20,y0,base+height)]
        vs = '\n'.join('{ '+', '.join(map(str,v))+' },' for v in vertices)
        geosets.append(f'''Geoset {{
Vertices 4 {{ {vs} }}
Normals 4 {{ {{ -1,0,0 }}, {{ -1,0,0 }}, {{ -1,0,0 }}, {{ -1,0,0 }}, }}
TVertices 4 {{ {{ {u0},1 }}, {{ {u1},1 }}, {{ {u1},0 }}, {{ {u0},0 }}, }}
VertexGroup {{ 0,0,0,0, }}
Faces 1 6 {{ Triangles {{ {{ 0,1,2,0,2,3 }}, }} }}
Groups 1 1 {{ Matrices {{ {side} }}, }}
MinimumExtent {{ -40, {-width}, {base} }},
MaximumExtent {{ 40, {width}, {base+height} }},
BoundsRadius {width+height},
Anim {{ MinimumExtent {{ -40, {-width}, {base} }}, MaximumExtent {{ 40, {width}, {base+height} }}, BoundsRadius {width+height}, }}
MaterialID 0,
SelectionGroup 0,
Unselectable,
}}''')
    bones = []
    for side in range(2):
        q = 0.04 if side == 0 else -0.04
        bones.append(f'''Bone "Wing{side}" {{ ObjectId {side}, GeosetId {side}, GeosetAnimId None,
Rotation 3 {{ Linear, 0: {{ 0,0,{-q},0.99919968 }}, 1500: {{ 0,0,{q},0.99919968 }}, 3000: {{ 0,0,{-q},0.99919968 }}, }}
}}''')
    return f'''Version {{ FormatVersion 800, }}
Model "TDEvolutionWings{choice}" {{ NumGeosets 2, NumBones 2, BlendTime 150, MinimumExtent {{ -40,{-width},{base} }}, MaximumExtent {{ 40,{width},{base+height} }}, BoundsRadius {width+height}, }}
Sequences 1 {{ Anim "Stand" {{ Interval {{ 0,3000 }}, MinimumExtent {{ -40,{-width},{base} }}, MaximumExtent {{ 40,{width},{base+height} }}, BoundsRadius {width+height}, }} }}
Textures 1 {{ Bitmap {{ Image "war3mapImported\\TDEvolutionWings.blp", }} }}
Materials 1 {{ Material {{ Layer {{ FilterMode Blend, TwoSided, Unshaded, static TextureID 0, static Alpha 1, }} }} }}
{''.join(geosets)}
{''.join(bones)}
PivotPoints 2 {{ {{ -20,0,{base+height*0.35} }}, {{ -20,0,{base+height*0.35} }}, }}
'''

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wing = Image.open(SOURCE/'evolution-wings.png').convert('RGBA').resize((512,512), Image.Resampling.LANCZOS)
    blp(wing, OUT/'TDEvolutionWings.blp')
    wing.save(SOURCE/'evolution-wings-texture-preview.png')
    for choice, (width,base,height) in enumerate([(110,45,155),(95,40,140),(90,45,135),(115,55,165),(115,35,155)], 1):
        (SOURCE/f'TDEvolutionWings{choice}.mdl').write_text(wing_mdl(choice,width,base,height), encoding='utf-8')
    for png in sorted(SOURCE.glob('icon-*.png')):
        name = png.stem[5:]
        stem = tower_icon_stem(name)
        remove_legacy_tower_icon(name)
        image = Image.open(png).convert('RGBA').resize((64,64), Image.Resampling.LANCZOS)
        blp(image, OUT/f'BTN{stem}.blp')
        disabled = ImageOps.grayscale(image).convert('RGBA')
        disabled.putalpha(image.getchannel('A'))
        disabled = ImageEnhance.Brightness(disabled).enhance(0.45)
        blp(disabled, ROOT/f'imports/ReplaceableTextures/CommandButtonsDisabled/DISBTN{stem}.blp')

if __name__ == '__main__':
    main()
