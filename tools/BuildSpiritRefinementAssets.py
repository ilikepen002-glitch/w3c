#!/usr/bin/env python3
"""Reproduce the approved refined imports in an isolated temporary directory.

No network, image generation or historical display append is performed. Inputs,
commands and expected output hashes come from the checked-in refinement plan.
By default compare to production imports; --write restores only verified bytes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'assets/source/elemental-spirits/refinement-20261015/rebuild-plan.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def relative(name):
    p = Path(name)
    if p.is_absolute() or '..' in p.parts or not p.parts or '.git' in p.parts:
        raise ValueError('Invalid relative source/output path: ' + name)
    return p

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write', action='store_true', help='Restore verified imports; never update manifest hashes')
    p.add_argument('--output', type=Path, help='Optional verification report')
    a = p.parse_args()
    plan = json.loads((ROOT/PLAN).read_text())
    if plan['version'] != 1 or len(plan['species']) != 15 or sorted(plan['species']) != list(range(1,16)):
        raise ValueError('Refinement plan must cover exactly all 15 species')
    report = {'status': 'RUNNING', 'planSha256': sha(ROOT/PLAN), 'verifiedInputs': [], 'outputs': [],
              'isolatedRebuild': True, 'updatedManifestHashes': False, 'wroteImports': a.write}
    with tempfile.TemporaryDirectory(prefix='spirit-refinement-rebuild-') as tmp:
        stage = Path(tmp)
        for spec in plan['inputs']:
            rel = relative(spec['path'])
            src = ROOT/rel
            if not src.is_file() or src.is_symlink() or sha(src) != spec['sha256']:
                raise ValueError('Missing or changed approved input: ' + str(rel))
            dest = stage/rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src,dest)
            report['verifiedInputs'].append(spec['path'])
        for command in plan['commands']:
            if not isinstance(command,list) or not command or command[0] not in ('python3','node'):
                raise ValueError('Only explicit Python/Node rebuild commands are supported')
            relative(command[1])
            for item in command[1:]:
                if item.startswith('/') or '\x00' in item:
                    raise ValueError('Nonportable rebuild argument: ' + item)
            subprocess.run(command, cwd=stage, check=True)
        for spec in plan['outputs']:
            rel = relative(spec['path'])
            if rel.parts[0] != 'imports':
                raise ValueError('Rebuild may restore only imports')
            made = stage/rel
            if not made.is_file() or sha(made) != spec['sha256'] or made.stat().st_size != spec['bytes']:
                raise ValueError('Rebuild does not match approved bytes: ' + str(rel))
            dest = ROOT/rel
            if a.write:
                dest.parent.mkdir(parents=True, exist_ok=True)
                fd, name = tempfile.mkstemp(prefix='.'+dest.name+'.',dir=dest.parent)
                try:
                    with os.fdopen(fd,'wb') as f:
                        f.write(made.read_bytes())
                    os.replace(name,dest)
                finally:
                    Path(name).unlink(missing_ok=True)
            elif not dest.is_file() or made.read_bytes() != dest.read_bytes():
                raise ValueError('Current import differs from deterministic rebuild: '+str(rel))
            report['outputs'].append(spec)
    report['status'] = 'PASS'
    text = json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if a.output:
        a.output.write_text(text)
    print(text)

if __name__ == '__main__':
    main()
