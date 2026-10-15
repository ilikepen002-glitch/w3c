"""Rebuild six refined original models and exact imagegen atlas pixels; no git BASE."""
from pathlib import Path
import subprocess,shutil,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
ENTRIES={'TideWyrm': ('build_tidewyrm.py', 'TideWyrmAtlas', 'tidewyrm-source.json'), 'FrostFinManta': ('build_frostmanta.py', 'FrostMantaAtlas', 'frostmanta-source.json'), 'SnowManeOtter': ('build_snowotter.py', 'SnowOtterAtlas', 'snowotter-source.json'), 'RockShellTurtle': ('build_rockturtle.py', 'RockTurtlePalette', 'rockturtle-source.json'), 'BoulderArmGibbon': ('build_earth_gibbon.py', 'BoulderArmAtlas', 'earth_gibbon-source.json'), 'SandSpiralSnail': ('build_earth_snail.py', 'SandSpiralAtlas', 'earth_snail-source.json')}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
report=[]
for name,(script,atlas,source) in ENTRIES.items():
 d=ROOT/'assets/source/elemental-spirits/models'/name
 subprocess.run(['python3',str(d/script)],check=True)
 subprocess.run(['node',str(d/'export_validate.cjs')],check=True,stdout=subprocess.DEVNULL)
 for rel,src in [('war3mapImported/'+name+'.mdx',name+'.mdx'),('Textures/'+atlas+'.blp',atlas+'.blp')]:
  dst=ROOT/'imports'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(d/'original'/src,dst)
 report.append({'model':name,'modelImportPath':'war3mapImported\\'+name+'.mdx','requiredTextureImportPath':'Textures\\'+atlas+'.blp','modelSha256':sha(d/'original'/f'{name}.mdx'),'textureSha256':sha(d/'original'/f'{atlas}.blp'),'source':str((d/'original'/source).relative_to(ROOT)),'game127aTested':False})
(ROOT/'evidence').mkdir(exist_ok=True)
(ROOT/'evidence/water-earth-hashes.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
