#!/usr/bin/env python3
"""Self-authored low-cost origin-mounted link, MDL source and BLP. No external artwork.
Convert with BuildPetPossessionStars.cjs using the project's pinned MDX parser.
"""
from pathlib import Path
from PIL import Image
from BuildEvolutionAssets import blp
ROOT = Path(__file__).resolve().parents[1]

def main():
    source = ROOT/'assets/source/pet-possession'
    source.mkdir(parents=True, exist_ok=True)
    out = ROOT/'imports/war3mapImported'
    blp(Image.new('RGBA', (8,8), (215,233,255,255)), out/'TDPetPossessionStars.blp')
    vertices, groups, faces, bones, pivots = [], [], [], [], []
    # Two crossed four-point diamond faces per mote, readable from either camera side.
    for i in range(12):
        x = (-1 if i%2 else 1)*(7 + (i%3)*4)
        y = ((i%3)-1)*9
        z = 95+i*20
        radius = 3.0 + (i%3)*0.8
        first = len(vertices)
        vertices += [(x-radius,y,z),(x,y,z+radius*2),(x+radius,y,z),(x,y,z-radius*2),
                     (x,y-radius,z),(x,y,z+radius*2),(x,y+radius,z),(x,y,z-radius*2)]
        groups += [i]*8
        faces += [first+j for j in (0,1,2,0,2,3,4,5,6,4,6,7)]
        shift = 7 if i%2 else -7
        bones.append(f'''Bone "Star{i}" {{ ObjectId {i}, GeosetId 0, GeosetAnimId None,
Translation 3 {{ Linear, 0: {{ 0,0,{shift} }}, 1500: {{ 0,0,{-shift} }}, 3000: {{ 0,0,{shift} }}, }}
Scaling 3 {{ Linear, 0: {{ 0.55,0.55,0.55 }}, 1500: {{ 1,1,1 }}, 3000: {{ 0.55,0.55,0.55 }}, }}
}}''')
        pivots.append((x,y,z))
    def rows(vs): return ' '.join('{ '+','.join(str(n) for n in v)+' },' for v in vs)
    extent = 'MinimumExtent { -30,-30,75 }, MaximumExtent { 30,30,340 }, BoundsRadius 350,'
    text = f'''Version {{ FormatVersion 800, }}
Model "TDPetPossessionStars" {{ NumGeosets 1, NumBones 12, BlendTime 150, {extent} }}
Sequences 1 {{ Anim "Stand" {{ Interval {{ 0,3000 }}, {extent} }} }}
Textures 1 {{ Bitmap {{ Image "war3mapImported\\TDPetPossessionStars.blp", }} }}
Materials 1 {{ Material {{ Layer {{ FilterMode Additive, TwoSided, Unshaded, Unfogged, static TextureID 0, static Alpha 0.72, }} }} }}
Geoset {{
Vertices {len(vertices)} {{ {rows(vertices)} }}
Normals {len(vertices)} {{ {rows([(0,0,1)]*len(vertices))} }}
TVertices {len(vertices)} {{ {rows([(0.5,0.5)]*len(vertices))} }}
VertexGroup {{ {','.join(map(str,groups))}, }}
Faces 1 {len(faces)} {{ Triangles {{ {{ {','.join(map(str,faces))} }}, }} }}
Groups 12 12 {{ {''.join('Matrices { '+str(i)+' }, ' for i in range(12))} }}
{extent}
Anim {{ {extent} }}
MaterialID 0, SelectionGroup 0, Unselectable,
}}
{chr(10).join(bones)}
PivotPoints 12 {{ {rows(pivots)} }}
'''
    (source/'TDPetPossessionStars.mdl').write_text(text)

if __name__ == '__main__': main()
