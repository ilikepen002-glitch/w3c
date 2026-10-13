#!/usr/bin/env python3
"""Prepare unchanged author assets from a locally downloaded original Hive ZIP.

    python3 tools/RestoreKingLeoricAssets.py /absolute/path/to/author-download.zip
    python3 tools/RestoreKingLeoricAssets.py /absolute/path/to/author-download.zip --check

No network access, installer, MDX conversion or standalone redistribution.
Read docs/credits/king-leoric.md for the original download and permission scope.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'assets/source/king-leoric.json'


def verify_bytes(data, spec):
    if len(data) != spec['size_bytes'] or hashlib.sha256(data).hexdigest() != spec['sha256']:
        raise ValueError(f"Unexpected original bytes: {spec['name']}; do not substitute another version")


def read_originals(archive, manifest):
    if archive.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Unexpectedly large original archive')
    originals = {}
    with zipfile.ZipFile(archive) as z:
        for spec in manifest['assets']:
            matches = [i for i in z.infolist() if not i.is_dir()
                       and i.filename.replace('\\', '/').rsplit('/', 1)[-1] == spec['name']]
            if not matches or any(i.file_size != spec['size_bytes'] for i in matches):
                raise ValueError(f"Missing or wrong-sized original asset: {spec['name']}")
            # The author's bundle contains the same BLP twice. Validate both.
            for item in matches:
                data = z.read(item)
                verify_bytes(data, spec)
                originals[spec['name']] = data
    return originals


def prepare(archive, check=False):
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    originals = read_originals(archive, manifest)
    # Check all destinations before writing any. Never replace a collaborator's bytes.
    for spec in manifest['assets']:
        target = ROOT / spec['import_path']
        if target.exists():
            verify_bytes(target.read_bytes(), spec)
        elif check:
            raise ValueError(f"Asset has not been restored: {spec['import_path']}")
    if not check:
        for spec in manifest['assets']:
            target = ROOT / spec['import_path']
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix='.' + target.name + '.', dir=target.parent)
            try:
                with os.fdopen(fd, 'wb') as f:
                    f.write(originals[spec['name']])
                os.replace(temporary, target)
            finally:
                Path(temporary).unlink(missing_ok=True)
    print('PASS: three original model/texture files and original readme; exact hashes and import paths')
    print('NOT VERIFIED: target native textures/events, map compilation, actual MPQ, game rendering')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    prepare(args.archive.resolve(), args.check)
