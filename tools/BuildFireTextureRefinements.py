#!/usr/bin/env python3
"""Rebuild only the two approved fire atlas/TEXS updates from pinned inputs."""
from pathlib import Path
import subprocess
import shutil
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/elemental-spirits/refinement-20261015/batch-c-fire'
for folder in ('fox','salamander'):
    for output in ('output','audit'):
        (SOURCE/folder/output).mkdir(parents=True,exist_ok=True)
subprocess.run(['python3',str(SOURCE/'tools/rebuild_fire_textures.py')],check=True)
for folder,model,texture in [('fox','CinderTailFox','CinderFoxAtlasRefined'),('salamander','MoltenHornSalamander','MoltenHornAtlasRefined')]:
    for sub,name in [('war3mapImported',model+'.mdx'),('Textures',texture+'.blp')]:
        dest=ROOT/'imports'/sub/name
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(SOURCE/folder/'output'/name,dest)
