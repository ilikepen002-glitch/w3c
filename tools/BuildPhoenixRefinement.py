#!/usr/bin/env python3
"""Rebuild the compact credited phoenix from its pinned editable source."""
from pathlib import Path
import os
import shutil
import subprocess
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets/source/elemental-spirits/refinement-20261015/phoenix'
env=dict(os.environ,PHOENIX_SOURCE_STAGE=str(SOURCE),PHOENIX_STAGE=str(SOURCE))
textures=SOURCE/'texture-source'
subprocess.run(['python3',str(textures/'scripts/rebuild_textures.py')],check=True)
for name in ('PhoenixBody.blp','PhoenixHead.blp'):
    shutil.copy2(textures/'rebuilt'/name,SOURCE/'source'/name)
for command,name in [('node','build_compact.cjs'),('python3','audit_phoenix.py'),('node','apply_extents.cjs'),('node','verify_compact.cjs'),('python3','audit_effects.py')]:
    subprocess.run([command,str(SOURCE/'scripts'/name)],env=env,check=True)
for source,destination in [('QiLingPhoenix-Display.mdx','war3mapImported/EmberBird.mdx'),('QiLingPhoenix/PhoenixBody.blp','QiLingPhoenix/PhoenixBody.blp'),('QiLingPhoenix/PhoenixHead.blp','QiLingPhoenix/PhoenixHead.blp')]:
    dest=ROOT/'imports'/destination
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE/'output'/source,dest)
