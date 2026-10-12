"""Recover the immutable historical oracle input from a fixed git tree.

This never copies current production sources. formal72 is a reachable ancestor
of the trial integration branch. Missing git history fails clearly rather than
silently treating the working tree as a historical fixture.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '72b2c9c3406868d33969c087dd5e6015abc3ac7b'
TREE = 'd1b1567bd10b47e974ddbe8cfd44fcb91c2e5edc'
MAP_SHA = 'be13ef7b9f7c2144a7feedbef88c79802b4c3e034e8336933e8f808735937d80'

def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT)

def source_bytes():
    actual = git('rev-parse', COMMIT + '^{tree}').decode().strip()
    if actual != TREE: raise ValueError('Historical formal72 fixed tree identity differs')
    names = git('ls-tree', '-r', '--name-only', COMMIT, '--', 'wurst').decode().splitlines()
    return {name: git('show', COMMIT + ':' + name) for name in names if name.endswith('.wurst') and '/_tests/' not in name}

def sources(): return {name.removeprefix('wurst/'): data.decode() for name, data in source_bytes().items()}

def map_bytes():
    data = git('show', COMMIT + ':ExampleMap.w3x')
    if hashlib.sha256(data).hexdigest() != MAP_SHA: raise ValueError('Historical formal72 fixed map SHA differs')
    return data

class Formal72SourceFixture:
    def __init__(self):
        # Located beneath repo so unmodified historical checkers' git commands
        # can find the same object database without an absolute scratch path.
        self.temporary = tempfile.TemporaryDirectory(prefix='.formal72-oracle-', dir=ROOT)
        self.root = Path(self.temporary.name)
        self.file_sha256 = {}
        for name, data in source_bytes().items():
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            self.file_sha256[name] = hashlib.sha256(data).hexdigest()
        # Native asset gates can use the real checked-in assets, whose hashes
        # have their own independent frozen contract. No mutable sources link.
    def cleanup(self): self.temporary.cleanup()
