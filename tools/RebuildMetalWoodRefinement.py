"""Convert only built-in imagegen source atlases to legacy opaque BLP1 mip chains.
No procedural painting or color edits. Preserves the approved SilverMane BLP byte-for-byte.
Run from any directory: python3 tools/RebuildMetalWoodRefinement.py [repo_root]
Then: MDX_PARSER_MODULES=... node tools/RebuildMetalWoodRefinement.cjs [repo_root]
"""
import sys,json,struct,shutil
from pathlib import Path
from PIL import Image
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent.parent
SRC=ROOT/'assets/source/elemental-spirits/refinement-20261015/batch-a'
def blp(image,path):
 image=image.convert('RGB').resize((256,256),Image.Resampling.LANCZOS)
 palette=image.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
 colors=palette.getpalette();colors += [0]*(768-len(colors))
 bgra=bytes(v for i in range(256) for v in (colors[i*3+2],colors[i*3+1],colors[i*3],0))
 payload=[];sizes=[];offsets=[];cursor=1180
 for level in range(9):
  dim=max(1,256>>level);mip=image.resize((dim,dim),Image.Resampling.LANCZOS).quantize(palette=palette,dither=Image.Dither.NONE)
  data=mip.tobytes();offsets.append(cursor);sizes.append(len(data));payload.append(data);cursor+=len(data)
 header=b'BLP1'+struct.pack('<6I',1,0,256,256,5,1)+struct.pack('<16I',*(offsets+[0]*7))+struct.pack('<16I',*(sizes+[0]*7))
 path.write_bytes(header+bgra+b''.join(payload))
for e in json.loads((SRC/'config.json').read_text()):
 name=e['model'];src=SRC/name;out=ROOT/'imports'/e['requiredTextureImportPath'].replace('\\','/');out.parent.mkdir(parents=True,exist_ok=True)
 if name=='SilverManeBeast':shutil.copy2(src/'input.blp',out)
 elif (src/'atlas-imagegen.png').exists():blp(Image.open(src/'atlas-imagegen.png'),out)
 else:print('Awaiting imagegen:',name);continue
 print(name,out.stat().st_size)
