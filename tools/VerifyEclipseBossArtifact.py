#!/usr/bin/env python3
"""Strict isolated uB24 visual delta, actual MPQ bytes; no engine claims."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from GenerateTowerTerrainMask import Mpq, ROOT
from VerifyGlobalRankingsArtifact import members, normalize_info
from VerifyKingLeoricArtifact import import_records
from VerifySemanticIconArtifact import parse_objects

MANIFEST = ROOT / 'assets/source/eclipse-spellweaver-v3/production-manifest.json'

def require(ok, message):
    if not ok:
        raise AssertionError(message)


def check_model(mdx, blp):
    require(mdx[:4] == b'MDLX', 'Invalid model magic')
    offset, chunks = 4, {}
    while offset < len(mdx):
        require(offset + 8 <= len(mdx), 'Truncated MDX chunk')
        tag, size = struct.unpack_from('<4sI', mdx, offset)
        require(tag not in chunks and offset + 8 + size <= len(mdx), 'Duplicate/truncated MDX chunk')
        chunks[tag] = mdx[offset + 8:offset + 8 + size]
        offset += 8 + size
    require(chunks.get(b'VERS') == struct.pack('<I', 800), 'Expected classic MDX800')
    sequences = chunks.get(b'SEQS', b'')
    require(len(sequences) == 6 * 132, 'Expected exact six animations')
    expected = [('Stand', 0, 2400, 0), ('Walk', 2500, 3700, 0), ('Spell', 3800, 5300, 1),
                ('Stand Hit', 5400, 6000, 1), ('Death', 6100, 8100, 1), ('Portrait', 8200, 10600, 0)]
    for i, (name, start, end, flags) in enumerate(expected):
        row = sequences[i * 132:(i + 1) * 132]
        require(row[:80].split(b'\0')[0].decode('ascii') == name and
                struct.unpack_from('<II', row, 80) == (start, end) and
                struct.unpack_from('<I', row, 92)[0] == flags, 'Animation interval/loop mismatch: ' + name)
    texture = chunks.get(b'TEXS', b'')
    require(len(texture) == 268 and struct.unpack_from('<I', texture)[0] == 0 and
            texture[4:264].split(b'\0')[0] == b'Textures\\EclipseSpellweaverAtlas.blp',
            'Unexpected texture reference or native dependency')
    require(len(chunks.get(b'PIVT', b'')) == 25 * 12, 'Expected 25 bone pivots')
    cameras = chunks.get(b'CAMS', b'')
    require(len(cameras) == 120 and cameras[4:84].split(b'\0')[0] == b'Portrait', 'Portrait camera missing')
    require(blp[:4] == b'BLP1' and struct.unpack_from('<IIII', blp, 4) == (1, 0, 512, 512),
            'Expected opaque palette BLP1 512x512')
    offsets, sizes = struct.unpack_from('<16I', blp, 28), struct.unpack_from('<16I', blp, 92)
    previous = 1180
    for level in range(10):
        size = max(1, 512 >> level) ** 2
        require(offsets[level] == previous and sizes[level] == size, 'BLP mip chain mismatch')
        previous += size
    require(previous == len(blp) and not any(offsets[10:] + sizes[10:]), 'Trailing/missing BLP mip data')
    return {'version': 800, 'sequences': [r[0] for r in expected], 'bonePivots': 25,
            'texture': 'BLP1 512x512/10mips/alpha0', 'portrait': 'embedded sequence and camera; no separate Portrait MDX'}


def validate(current, baseline, manifest, *, check_formats=True, scale_only=False):
    require(manifest['unitRawcode'] == 'uB24' and manifest['baseUnitRawcode'] == 'Udre' and
            manifest['integration']['modelPath'] == 'war3mapImported\\EclipseSpellweaver.mdx' and
            manifest['integration']['scale'] == 8.0, 'Unexpected visual scope')
    now = parse_objects(current.extract('war3map.w3u'), False)
    old = parse_objects(baseline.extract('war3map.w3u'), False)
    require(list(now) == list(old), 'Unit identity/order changed')
    target = now['uB24']
    require(target.fields['umdl', 0, 0].value == manifest['integration']['modelPath'] and
            target.fields['usca', 0, 0].value == 8.0, 'Wrong model or visual scale')
    if scale_only:
        require(old['uB24'].fields['umdl', 0, 0] == target.fields['umdl', 0, 0] and
                old['uB24'].fields['usca', 0, 0].value == 1.5, 'Unexpected scale-only baseline')
        a, b = target.fields['usca', 0, 0], old['uB24'].fields['usca', 0, 0]
        require(a.kind == b.kind and b.kind in (1, 2) and
                a.raw == b.raw[:8] + struct.pack('<f', 8.0) + b.raw[12:], 'Scale encoding changed beyond value')
    allowed = {('usca', 0, 0)} if scale_only else {('umdl', 0, 0), ('usca', 0, 0)}
    for code in now:
        a, b = now[code], old[code]
        require(a.identity == b.identity and a.table == b.table, 'Unit parent changed: ' + code)
        if scale_only:
            require(list(a.fields) == list(b.fields), 'Unit field order changed: ' + code)
        for key in set(a.fields) | set(b.fields):
            if code == 'uB24' and key in allowed:
                continue
            require(a.fields.get(key) == b.fields.get(key), 'Nonvisual unit field changed: ' + code + str(key))
    specs = manifest['assets']
    expected = {'war3mapImported\\EclipseSpellweaver.mdx', 'Textures\\EclipseSpellweaverAtlas.blp'}
    require(len(specs) == 2 and {s['importPath'] for s in specs} == expected, 'Unexpected import allowlist')
    before, after = members(baseline), members(current)
    require(set(after) == (set(before) if scale_only else set(before) | {s.casefold() for s in expected}), 'Unexpected MPQ member addition/removal')
    mutable = {'war3map.w3u', '(listfile)', '(attributes)'}
    if not scale_only:
        mutable.add('war3map.imp')
    for key, (path, data) in before.items():
        name, packed = after[key]
        require(name == path, 'Resource path spelling changed')
        if path == 'war3map.w3i':
            require(normalize_info(data, '契灵守卫战') == normalize_info(packed, '契灵守卫战'),
                    'Metadata changed beyond build display strings')
        elif path not in mutable:
            require(packed == data, 'Inherited MPQ bytes changed: ' + path)
    records = import_records(current.extract('war3map.imp'))
    inherited_records = records if scale_only else [r for r in records if r[1] not in expected]
    require(inherited_records == import_records(baseline.extract('war3map.imp')),
            'Existing import table changed')
    packed_assets = {}
    for spec in specs:
        path = spec['importPath']; data = current.extract(path)
        require(after[path.casefold()][0] == path, 'New asset path case mismatch')
        require(records.count((13, path)) == 1, 'Wrong import flag/path: ' + path)
        require(len(data) == spec['bytes'] and hashlib.sha256(data).hexdigest() == spec['sha256'],
                'Frozen original asset hash mismatch: ' + path)
        packed_assets[spec['role']] = data
    formats = check_model(packed_assets['model'], packed_assets['texture']) if check_formats else 'synthetic tests only'
    return {'status': 'PASS', 'scope': ('Only uB24 usca 1.50 to 8.00; models/assets and all other fields/resources and JASS byte-identical'
                                        if scale_only else 'Only uB24 umdl/usca and two new original assets; all other fields/resources and JASS byte-identical'),
            'unit': 'uB24', 'visualScale': 8.0, 'formats': formats,
            'notTested': 'Warcraft 1.27a rendering, embedded Portrait fallback, occlusion, animation feel and performance'}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('map', type=Path); p.add_argument('baseline', type=Path)
    p.add_argument('--scale-only', action='store_true', help='Require existing 1.50 model/assets; allow only usca to 8.00')
    args = p.parse_args(); result = validate(Mpq(args.map.read_bytes()), Mpq(args.baseline.read_bytes()),
                                            json.loads(MANIFEST.read_text(encoding='utf-8')), scale_only=args.scale_only)
    result['mapSha256'] = hashlib.sha256(args.map.read_bytes()).hexdigest()
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
