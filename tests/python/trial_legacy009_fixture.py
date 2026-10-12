"""Immutable formal trial map and matching source oracle, distinct from current40."""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '009dae4dc2a27382477ff1ea624c6fd6a91b5a19'
TREE = '2960fc1a52b14fd671cd9dc4414f67a4e7e3494c'
MAP_SHA = '03921c61e64e5392f8f9100291ca62df539b3f0bb8c7c4af47e82fa2bba21dde'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def identity():
    if git('rev-parse', COMMIT + '^{tree}').decode().strip() != TREE:
        raise ValueError('Historical legacy009 fixed tree identity differs')

def map_bytes():
    identity()
    data = git('show', COMMIT + ':ExampleMap.w3x')
    if hashlib.sha256(data).hexdigest() != MAP_SHA:
        raise ValueError('Historical legacy009 fixed map SHA differs')
    return data

class Legacy009SourceFixture:
    def __init__(self):
        identity()
        self.temporary = tempfile.TemporaryDirectory(prefix='.legacy009-oracle-', dir=ROOT)
        self.root = Path(self.temporary.name)
        names = git('ls-tree', '-r', '--name-only', COMMIT, '--', 'wurst').decode().splitlines()
        for name in names:
            if not name.endswith('.wurst') or '/_tests/' in name:
                continue
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(git('show', COMMIT + ':' + name))
    def cleanup(self):
        self.temporary.cleanup()
