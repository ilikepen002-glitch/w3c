#!/usr/bin/env python3
"""Strict uB08/uB32 visual-only MPQ delta; no Warcraft engine claims."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from GenerateTowerTerrainMask import Mpq, ROOT
from VerifyGlobalRankingsArtifact import members, normalize_info
from VerifyKingLeoricArtifact import import_records
from VerifySemanticIconArtifact import parse_objects

TARGETS = {
    'uB08': ('Ocbh', 'RiftwindHunter', 7.75, 22, 'Spell', 'riftwind-hunter'),
    'uB32': ('Ulic', 'UncrownedAbyssKing', 7.00, 27, 'Attack', 'uncrowned-abyss-king'),
}


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def load_manifests():
    return {code: json.loads((ROOT / 'assets/source' / row[5] / 'production-manifest.json')
                            .read_text(encoding='utf-8')) for code, row in TARGETS.items()}


def check_formats(mdx, blp, stem, bones, action):
    require(mdx[:4] == b'MDLX', 'Invalid model magic')
    offset, chunks = 4, {}
    while offset < len(mdx):
        require(offset + 8 <= len(mdx), 'Truncated MDX header')
        tag, size = struct.unpack_from('<4sI', mdx, offset)
        require(tag not in chunks and offset + 8 + size <= len(mdx), 'Duplicate/truncated MDX chunk')
        chunks[tag] = mdx[offset + 8:offset + 8 + size]
        offset += 8 + size
    require(chunks.get(b'VERS') == struct.pack('<I', 800), 'Expected classic MDX800')
    seqs = chunks.get(b'SEQS', b'')
    expected = [('Stand', 0, 2400, 0), ('Walk', 2500, 3700, 0), (action, 3800, 5300, 1),
                ('Stand Hit', 5400, 6000, 1), ('Death', 6100, 8100, 1), ('Portrait', 8200, 10600, 0)]
    require(len(seqs) == 6 * 132, 'Expected six animations')
    for i, (name, start, end, flags) in enumerate(expected):
        row = seqs[i * 132:(i + 1) * 132]
        require(row[:80].split(b'\0')[0] == name.encode('ascii') and
                struct.unpack_from('<II', row, 80) == (start, end) and
                struct.unpack_from('<I', row, 92)[0] == flags, 'Wrong animation interval/loop: ' + name)
    tex = chunks.get(b'TEXS', b'')
    texture = ('Textures\\' + stem + 'Atlas.blp').encode('ascii')
    require(len(tex) == 268 and struct.unpack_from('<I', tex)[0] == 0 and
            tex[4:264].split(b'\0')[0] == texture, 'Unexpected texture/native dependency')
    require(len(chunks.get(b'PIVT', b'')) == bones * 12, 'Wrong bone pivot count')
    cameras = chunks.get(b'CAMS', b'')
    require(len(cameras) == 120 and cameras[4:84].split(b'\0')[0] == b'Portrait', 'Missing Portrait camera')
    require(blp[:4] == b'BLP1' and struct.unpack_from('<IIII', blp, 4) == (1, 0, 512, 512),
            'Expected opaque palette BLP1 512x512')
    offsets, sizes = struct.unpack_from('<16I', blp, 28), struct.unpack_from('<16I', blp, 92)
    end = 1180
    for level in range(10):
        size = max(1, 512 >> level) ** 2
        require(offsets[level] == end and sizes[level] == size, 'Wrong BLP mip chain')
        end += size
    require(end == len(blp) and not any(offsets[10:] + sizes[10:]), 'Trailing/missing BLP mip data')
    return {'MDX': 800, 'sequences': [r[0] for r in expected], 'bonePivots': bones,
            'BLP': '512x512/10mips/alpha0', 'portrait': 'embedded sequence/camera; client fallback untested'}


def validate(current, baseline, manifests, *, verify_formats=True):
    require(set(manifests) == set(TARGETS), 'Unexpected target allowlist')
    now, old = (parse_objects(m.extract('war3map.w3u'), False) for m in (current, baseline))
    require(list(now) == list(old), 'Unit identity/order changed')
    allowed = {('umdl', 0, 0), ('usca', 0, 0)}
    specs = {}
    for code, (parent, stem, scale, bones, action, folder) in TARGETS.items():
        obj, manifest = now[code], manifests[code]
        path = 'war3mapImported\\' + stem + '.mdx'
        require(manifest['unitRawcode'] == code and manifest['baseUnitRawcode'] == parent and
                manifest['integration']['modelPath'] == path and manifest['integration']['scale'] == scale,
                'Unexpected manifest visual scope: ' + code)
        require(obj.identity == parent.encode() + code.encode(), 'Wrong target parent: ' + code)
        model, size = obj.fields['umdl', 0, 0], obj.fields['usca', 0, 0]
        require(model.kind == 3 and model.value == path and size.kind in (1, 2) and size.value == scale,
                'Wrong model/visual scale: ' + code)
        assets = manifest['assets']
        expected = {path, 'Textures\\' + stem + 'Atlas.blp'}
        require(len(assets) == 2 and {a['role'] for a in assets} == {'model', 'texture'} and
                {a['importPath'] for a in assets} == expected, 'Unexpected asset allowlist: ' + code)
        specs[code] = assets
    for code in now:
        a, b = now[code], old[code]
        require(a.identity == b.identity and a.table == b.table, 'Unit parent/table changed: ' + code)
        retained_a = [k for k in a.fields if code not in TARGETS or k not in allowed]
        retained_b = [k for k in b.fields if code not in TARGETS or k not in allowed]
        require(retained_a == retained_b, 'Nonvisual field order/set changed: ' + code)
        for key in retained_a:
            require(a.fields[key] == b.fields[key], 'Nonvisual unit field changed: ' + code + str(key))
    new_paths = {a['importPath'] for assets in specs.values() for a in assets}
    before, after = members(baseline), members(current)
    require(not ({p.casefold() for p in new_paths} & set(before)), 'New asset already in baseline')
    require(set(after) == set(before) | {p.casefold() for p in new_paths}, 'Unexpected MPQ addition/removal')
    mutable = {'war3map.w3u', 'war3map.imp', '(listfile)', '(attributes)'}
    for key, (name, data) in before.items():
        path, packed = after[key]
        require(path == name, 'Inherited resource path spelling changed')
        if name == 'war3map.w3i':
            require(normalize_info(data, '契灵守卫战') == normalize_info(packed, '契灵守卫战'),
                    'Metadata changed beyond two display dates')
        elif name not in mutable:
            require(packed == data, 'Inherited MPQ bytes changed: ' + name)
    records = import_records(current.extract('war3map.imp'))
    require([r for r in records if r[1] not in new_paths] == import_records(baseline.extract('war3map.imp')),
            'Inherited import table changed')
    formats = {}
    for code, assets in specs.items():
        packed = {}
        for a in assets:
            path = a['importPath']; data = current.extract(path)
            require(after[path.casefold()][0] == path and records.count((13, path)) == 1,
                    'Wrong import spelling/flag: ' + path)
            require(len(data) == a['bytes'] and hashlib.sha256(data).hexdigest() == a['sha256'],
                    'Frozen asset hash mismatch: ' + path)
            packed[a['role']] = data
        row = TARGETS[code]
        formats[code] = (check_formats(packed['model'], packed['texture'], row[1], row[3], row[4])
                         if verify_formats else 'Synthetic API fixtures only')
    return {'status': 'PASS', 'scope': 'Only uB08/uB32 model/visualScale and four original resources; '
            'all JASS, other object fields and inherited resources byte-identical',
            'scales': {code: row[2] for code, row in TARGETS.items()}, 'formats': formats,
            'notTested': 'Warcraft 1.27a rendering, occlusion, Portrait fallback and performance'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path); p.add_argument('baseline', type=Path)
    args = p.parse_args(); data = args.map.read_bytes()
    result = validate(Mpq(data), Mpq(args.baseline.read_bytes()), load_manifests())
    result.update(mapSha256=hashlib.sha256(data).hexdigest(), compressedMapBytes=len(data),
                  bytesBelow8MiB=8 * 1024 * 1024 - len(data))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
