#!/usr/bin/env python3
"""Verify an isolated Leoric visual release against its same-toolchain baseline.

    python3 tools/VerifyKingLeoricArtifact.py new.w3x baseline.w3x

This is deliberately strict: only uB16 umdl/usca and the listed imports may
change. Use a baseline from before this isolated change, not a historical map
that also lacks unrelated UI/features or uses a different compiler.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
from GenerateTowerTerrainMask import Mpq, ROOT
from VerifyTowerPlacementArtifact import unit_objects
from VerifySemanticIconArtifact import parse_objects
from VerifyGlobalRankingsArtifact import members, normalize_info


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def import_records(data):
    version, count = struct.unpack_from('<II', data)
    require(version == 1, 'Unsupported import table')
    offset, records = 8, []
    for _ in range(count):
        flag = data[offset]
        end = data.index(0, offset + 1)
        path = data[offset + 1:end].decode('utf-8')
        require(flag in (5, 8, 10, 13), 'Unsupported import flag')
        records.append((flag, path if flag in (10, 13) else 'war3mapImported\\' + path))
        offset = end + 1
    require(offset == len(data), 'Trailing import bytes')
    require(len({p.casefold() for _, p in records}) == len(records), 'Duplicate import paths')
    return records


def validate(current, baseline, manifest, *, combined_release=False):
    require(manifest['unit_id'] == 'uB16' and manifest['object_model_path'] == 'war3mapImported\\Leoric.mdx'
            and manifest['object_scale'] == 1.3, 'Unexpected visual-change scope')
    units = unit_objects(current.extract('war3map.w3u'))
    before = unit_objects(baseline.extract('war3map.w3u'))
    full_units = parse_objects(current.extract('war3map.w3u'), False)
    full_before = parse_objects(baseline.extract('war3map.w3u'), False)
    uid = manifest['unit_id']
    require(units[uid].get('umdl') == manifest['object_model_path'], 'Wrong Boss model path')
    require(math.isclose(units[uid].get('usca', 0), manifest['object_scale'], abs_tol=1e-6), 'Wrong visual scale')
    require(units[uid].get('ucol') == before[uid].get('ucol') == 0.0, 'Collision changed')
    strip_visual = lambda fields: {k: v for k, v in fields.items() if k not in ('umdl', 'usca')}
    require(strip_visual(units[uid]) == strip_visual(before[uid]), 'Boss nonvisual fields changed')
    nonvisual = lambda obj: {k: f for k, f in obj.fields.items() if k[0] not in ('umdl', 'usca')}
    require(nonvisual(full_units[uid]) == nonvisual(full_before[uid]), 'Boss nonvisual field encoding changed')
    require(list(full_units) == list(full_before), 'Unit table order changed')
    for key in set(units) | set(before):
        require(key in full_units and key in full_before, 'Unit set changed')
        require(full_units[key].identity == full_before[key].identity
                and full_units[key].table == full_before[key].table, 'Unit parent/identity changed: ' + key)
        if key != uid and not combined_release:
            require(full_units[key].encoded() == full_before[key].encoded(), 'Unrelated unit changed: ' + key)
    immutable = ('war3map.w3e', 'war3map.wpm', 'war3mapMap.blp') if combined_release else ('war3map.j', 'war3map.w3a', 'war3map.w3t', 'war3map.w3e', 'war3map.wpm', 'war3mapMap.blp')
    for member in immutable:
        require(current.extract(member) == baseline.extract(member), 'Unrelated gameplay/assets changed: ' + member)
    imported = import_records(current.extract('war3map.imp'))
    old_imported = import_records(baseline.extract('war3map.imp'))
    expected = {a['mpq_path'] for a in manifest['assets']} | {manifest['credits_mpq_path']}
    now_members, old_members = members(current), members(baseline)
    additions = {p.casefold(): p for p in expected}
    require(set(now_members) == set(old_members) | set(additions), 'Unexpected MPQ addition/removal')
    mutable = {'war3map.w3u', 'war3map.imp', '(listfile)', '(attributes)'}
    if combined_release:
        from VerifyCombinedVisualTextArtifact import verify_tables, verify_ground_runtime
        delta = verify_tables(current, baseline, ROOT)
        verify_ground_runtime(current.extract('war3map.j').decode('utf-8'))
        mutable |= {'war3map.j', 'war3map.w3a', 'war3map.w3t', 'war3map.w3h'}
        print('PASS COMBINED: finite source-derived visual/text/button fields:', len(delta))
    for folded, (path, data) in old_members.items():
        new_path, new_data = now_members[folded]
        require(new_path == path, 'Existing MPQ path spelling changed')
        if path == 'war3map.w3i':
            require(normalize_info(data, '契灵守卫战') == normalize_info(new_data, '契灵守卫战'),
                    'Metadata changed beyond build timestamps')
        elif path not in mutable:
            require(data == new_data, 'Unrelated MPQ member changed: ' + path)
    for folded, path in additions.items():
        require(now_members[folded][0] == path, 'New MPQ resource spelling changed')
    require([r for r in imported if r[1] not in expected] == old_imported, 'Unrelated import table changed')
    for spec in manifest['assets']:
        packed = current.extract(spec['mpq_path'])
        require(len(packed) == spec['size_bytes'] and hashlib.sha256(packed).hexdigest() == spec['sha256'],
                'Original asset not packed exactly: ' + spec['mpq_path'])
        require(imported.count((13, spec['mpq_path'])) == 1, 'Missing exact custom import: ' + spec['mpq_path'])
    credits = current.extract(manifest['credits_mpq_path'])
    require(credits == (ROOT / 'imports/Credits-KingLeoric.txt').read_bytes(), 'Missing source credits')
    require(imported.count((13, manifest['credits_mpq_path'])) == 1, 'Missing credits import')
    print('PASS: uB16 only model/1.30 visual scale changed; its combat fields identical' if combined_release else 'PASS: only uB16 model/1.30 visual scale changed; all other unit fields and gameplay members identical')
    print('PASS: exact original MDX/portrait/BLP/readme and creator credits packed under exact flag13 paths')
    print('NOT VERIFIED: actual 1.27a native textures/TeamGlow/events; game rendering, timing, occlusion, performance')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('--combined-release', action='store_true', help='Explicit current source-derived text/carrier/ground-sort batch; isolated default retained')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'assets/source/king-leoric.json').read_text(encoding='utf-8'))
    validate(Mpq(args.map.read_bytes()), Mpq(args.baseline.read_bytes()), manifest, combined_release=args.combined_release)
