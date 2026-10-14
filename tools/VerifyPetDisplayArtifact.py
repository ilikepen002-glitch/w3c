#!/usr/bin/env python3
"""Narrow overhead-display source, MDX800, and final MPQ closure verification.

    python3 tools/VerifyPetDisplayArtifact.py
    python3 tools/VerifyPetDisplayArtifact.py --resources-only
    python3 tools/VerifyPetDisplayArtifact.py changed.w3x baseline.w3x --output report.json

Uses only Python's standard library and existing MPQ/object readers. This is not
a native animation/rendering/FPS test. Executable lifecycle/combat replay remains
a separate gate. The baseline must be the published lifecycle/no-ETA map before
this display change; only pv01..pv0F movement fields and the approved Silver Mane
model/atlas pair may change in its objects/resources.
"""
import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
from pathlib import Path

from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects
from VerifyUnitParentsArtifact import unit_parents
from VerifySemanticIconArtifact import parse_objects

ROOT = Path(__file__).resolve().parents[1]
BASE = '5aa702d11e99502349898fde1f47d61d3ad516a9'
FORMAL = '4abc225181e134b8e8f9de3d2bb3b52a78fc0b6b'
CARTOON = 'fb47e96832e7b86c026960d471ee76c267ae7b34'
DISPLAY = 'b24e6c19b7203cd23dc6115f86575682ce5e387e'
MODEL_DIR = 'assets/source/elemental-spirits/models/SilverManeBeast'
MANIFEST = 'assets/source/elemental-spirits/import-manifest.json'
PROVENANCE = 'assets/source/elemental-spirits/LICENSE-PROVENANCE.txt'
MODEL = 'imports/war3mapImported/SilverManeBeast.mdx'
TEXTURE = 'imports/Textures/SilverManeAtlas.blp'
APPROVED = {
    MODEL: ('7967acb75baacba9f14f71264dc11256674840927dd93134dd1d56983b89dbe4', 421506),
    TEXTURE: ('af713ae301a3dd2b5c83e2b9a128101e901119901301978d8f10e8f04f4084b2', 88561),
}
BASIC_HIT_APPROVED = {'imports/war3mapImported/TDPetHitEarthFault.mdx': ('77507ea16c78bde342a7322721df4c91a821e2d9cc6cc00d6bce3248e384e137', 11148), 'imports/war3mapImported/TDPetHitFireCrown.mdx': ('092f54b9a9f12ed171c72929c0b2c02667f29c0a4fa857adad042bbb39f56592', 11988), 'imports/war3mapImported/TDPetHitGoldCrescent.mdx': ('75999e2266cb844257d04a3723539fc7c400d075bfaa9fc9209a313028c96747', 21228), 'imports/war3mapImported/TDPetHitWaterShards.mdx': ('7fd1570f470aee99d62793e2d0518168d4eb3e172284f98ea49203654337efd7', 11988), 'imports/war3mapImported/TDPetHitWoodThorns.mdx': ('ae308d307ef7bb00988e16e0e180a17146b6075c5d090779dbc79c0f746eebd2', 10308)}

SEQUENCES = [
    ('Stand', 0, 2000, True), ('Walk', 2100, 3100, True),
    ('Attack', 3200, 3900, False), ('Death', 4000, 5400, False),
    ('Portrait', 5500, 7500, True), ('Display Float', 8000, 10000, True),
    ('Display Jump', 10100, 10900, False), ('Display Spin', 11000, 12200, False),
    ('Display Sleep', 12300, 15300, True), ('Display Cast', 15400, 16600, False),
]
REDUCE_TOOLTIP_OLD = '每次普攻命中叠加6%移动减速，最多5层30%；不同精灵各自叠层，同类取最强，Boss减半。'
REDUCE_TOOLTIP_NEW = '每次普攻命中叠加移动减速，每层3%/4%/5%/6%（随品质），最多5层；不同精灵各自叠层，同类取最强，Boss减半。'
PV = {f'pv0{species:X}' for species in range(1, 16)}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prior(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)


def paths_at(ref, prefix):
    return subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', ref, prefix],
                                   cwd=ROOT).decode().rstrip('\0').split('\0')


def cstring(data):
    return data.split(b'\0', 1)[0].decode('ascii')


def extent(data, offset):
    values = struct.unpack_from('<7f', data, offset)
    require(all(math.isfinite(v) for v in values), 'Non-finite MDX extent')
    radius, low, high = values[0], values[1:4], values[4:7]
    require(radius > 0 and all(a < b for a, b in zip(low, high)), 'Invalid MDX extent')
    return {'radius': radius, 'min': list(low), 'max': list(high)}


def generic_node(data, offset):
    size = struct.unpack_from('<I', data, offset)[0]
    end = offset + size
    require(size >= 96 and end <= len(data), 'Malformed MDX generic node')
    oid, parent, flags = struct.unpack_from('<iiI', data, offset + 84)
    node = {'name': cstring(data[offset + 4:offset + 84]),
            'objectId': oid, 'parentId': parent, 'flags': flags, 'tracks': {}}
    cursor = offset + 96
    while cursor < end:
        tag = data[cursor:cursor + 4].decode('ascii')
        require(tag in ('KGTR', 'KGRT', 'KGSC'), f'Unknown generic animation track: {tag}')
        require(tag not in node['tracks'], f'Duplicate animation track: {tag}')
        count, interpolation, global_id = struct.unpack_from('<IIi', data, cursor + 4)
        require(interpolation in (0, 1, 2, 3) and global_id == -1,
                'Unexpected interpolation/global-sequence contract')
        width = 4 if tag == 'KGRT' else 3
        record_size = 4 + width * 4 * (3 if interpolation > 1 else 1)
        cursor += 16
        records = []
        for _ in range(count):
            raw = data[cursor:cursor + record_size]
            require(len(raw) == record_size, 'Truncated key record')
            frame = struct.unpack_from('<I', raw)[0]
            values = struct.unpack_from('<' + 'f' * ((record_size - 4) // 4), raw, 4)
            require(all(math.isfinite(v) for v in values), 'Non-finite animation key')
            records.append((frame, raw))
            cursor += record_size
        require([f for f, _ in records] == sorted({f for f, _ in records}),
                f'Unordered/duplicate key frames in {node["name"]}/{tag}')
        node['tracks'][tag] = {'interpolation': interpolation, 'globalId': global_id,
                               'records': records}
    require(cursor == end, 'Generic node track size mismatch')
    return node, end


def parse_mdx(data):
    """Strict parser for the approved classic MDX800 subset, with raw key bytes."""
    require(data[:4] == b'MDLX', 'Not MDX')
    chunks, cursor = {}, 4
    while cursor < len(data):
        tag = data[cursor:cursor + 4].decode('ascii')
        size = struct.unpack_from('<I', data, cursor + 4)[0]
        require(tag not in chunks and cursor + 8 + size <= len(data), 'Invalid MDX chunk')
        chunks[tag] = data[cursor + 8:cursor + 8 + size]
        cursor += 8 + size
    require(cursor == len(data), 'MDX trailing data')
    require(struct.unpack('<I', chunks['VERS']) == (800,), 'MDX is not classic version800')
    require(all(not chunks.get(tag) for tag in ('PREM', 'PRE2', 'RIBB', 'EVTS', 'GLBS')),
            'Unexpected emitter/event/global sequence')
    sequences, seq_data = [], chunks['SEQS']
    require(len(seq_data) % 132 == 0, 'Malformed SEQS')
    for i in range(0, len(seq_data), 132):
        start, end, speed, flags, rarity, sync = struct.unpack_from('<IIfIfI', seq_data, i + 80)
        require(flags in (0, 1) and end > start and math.isfinite(speed) and math.isfinite(rarity),
                'Invalid sequence identity')
        sequences.append({'name': cstring(seq_data[i:i + 80]), 'start': start, 'end': end,
                          'loop': flags == 0, 'moveSpeed': speed, 'rarity': rarity,
                          'syncPoint': sync, 'identity': seq_data[i:i + 104],
                          'extent': extent(seq_data, i + 104)})
    tex = chunks['TEXS']
    require(len(tex) == 268, 'Expected one texture')
    replaceable, flags = struct.unpack_from('<I', tex)[0], struct.unpack_from('<I', tex, 264)[0]
    require(replaceable == 0 and flags == 0, 'Unexpected texture flags')
    texture_path = cstring(tex[4:264])
    mat = chunks['MTLS']
    require(len(mat) == 48 and struct.unpack_from('<I', mat)[0] == 48
            and mat[12:16] == b'LAYS' and struct.unpack_from('<I', mat, 16)[0] == 1,
            'Expected one single-layer material')
    layer = struct.unpack_from('<IIIiiIf', mat, 20)
    require(layer == (28, 0, 0, 0, -1, 0, 1.0), 'Material must remain opaque, unanimated texture0')
    bones, bone_data, cursor = [], chunks['BONE'], 0
    while cursor < len(bone_data):
        node, cursor = generic_node(bone_data, cursor)
        node['geosetIds'] = struct.unpack_from('<ii', bone_data, cursor)
        cursor += 8
        bones.append(node)
    require(cursor == len(bone_data), 'Malformed BONE')
    pivots_data = chunks['PIVT']
    require(len(pivots_data) % 12 == 0, 'Malformed PIVT')
    pivots = list(struct.iter_unpack('<3f', pivots_data))
    require(all(math.isfinite(v) for p in pivots for v in p), 'Non-finite pivot')
    attachments, att_data, cursor = [], chunks.get('ATCH', b''), 0
    while cursor < len(att_data):
        size = struct.unpack_from('<I', att_data, cursor)[0]
        end = cursor + size
        node, body_end = generic_node(att_data, cursor + 4)
        node['path'] = cstring(att_data[body_end:body_end + 260])
        node['attachmentId'] = struct.unpack_from('<i', att_data, body_end + 260)[0]
        require(end == body_end + 264 and not node['tracks'], 'Unexpected attachment animation')
        attachments.append(node)
        cursor = end
    require(cursor == len(att_data), 'Malformed ATCH')
    geo = chunks['GEOS']
    require(struct.unpack_from('<I', geo)[0] == len(geo), 'Expected one geoset')
    cursor, arrays = 4, {}
    for tag, item_size in [('VRTX', 12), ('NRMS', 12), ('PTYP', 4), ('PCNT', 4),
                           ('PVTX', 2), ('GNDX', 1), ('MTGC', 4), ('MATS', 4)]:
        require(geo[cursor:cursor + 4] == tag.encode(), f'Missing geoset {tag}')
        count = struct.unpack_from('<I', geo, cursor + 4)[0]
        arrays[tag] = geo[cursor + 8:cursor + 8 + count * item_size]
        require(len(arrays[tag]) == count * item_size, f'Truncated geoset {tag}')
        cursor += 8 + count * item_size
    require(struct.unpack_from('<III', geo, cursor) == (0, 0, 0), 'Geoset material/selection changed')
    cursor += 12
    geo_extent = extent(geo, cursor)
    cursor += 28
    count = struct.unpack_from('<I', geo, cursor)[0]
    cursor += 4
    require(count == len(sequences), 'Geoset sequence extent count mismatch')
    geo_extents = [extent(geo, cursor + 28 * i) for i in range(count)]
    cursor += 28 * count
    require(geo[cursor:cursor + 4] == b'UVAS' and struct.unpack_from('<I', geo, cursor + 4)[0] == 1,
            'Expected one UV set')
    cursor += 8
    require(geo[cursor:cursor + 4] == b'UVBS', 'Missing UVBS')
    count = struct.unpack_from('<I', geo, cursor + 4)[0]
    arrays['UVBS'] = geo[cursor + 8:cursor + 8 + count * 8]
    cursor += 8 + count * 8
    require(cursor == len(geo), 'Geoset trailing data')
    require(len(arrays['VRTX']) == len(arrays['NRMS']) == len(arrays['GNDX']) * 12,
            'Vertex/normals/binding count mismatch')
    require(len(arrays['UVBS']) == len(arrays['GNDX']) * 8, 'UV count mismatch')
    for tag in ('VRTX', 'NRMS', 'UVBS'):
        require(all(math.isfinite(v[0]) for v in struct.iter_unpack('<f', arrays[tag])),
                f'Non-finite {tag}')
    require(all(v[0] < len(arrays['GNDX']) for v in struct.iter_unpack('<H', arrays['PVTX'])),
            'Out-of-range face index')
    return {'sequences': sequences, 'bones': bones, 'pivots': pivots, 'attachments': attachments,
            'texture': texture_path, 'geometry': arrays, 'geosetExtent': geo_extent,
            'geosetSequenceExtents': geo_extents, 'modelExtent': extent(chunks['MODL'], 340)}


def original_keys_equal(before, after):
    require(len(before['bones']) == len(after['bones']) == 11, 'Bone count changed')
    keys = 0
    for i, (a, b) in enumerate(zip(before['bones'], after['bones'])):
        require({k: v for k, v in a.items() if k != 'tracks'} ==
                {k: v for k, v in b.items() if k != 'tracks'}, f'Bone identity changed: {i}')
        require(before['pivots'][i] == after['pivots'][i], f'Bone pivot changed: {i}')
        require(a['tracks'].keys() == b['tracks'].keys(), f'Original track set changed: {i}')
        for tag, track in a['tracks'].items():
            newer = b['tracks'][tag]
            require((track['interpolation'], track['globalId']) ==
                    (newer['interpolation'], newer['globalId']), f'Track metadata changed: {i}/{tag}')
            old_records = [(frame, raw) for frame, raw in track['records'] if frame <= 7500]
            new_records = [(frame, raw) for frame, raw in newer['records'] if frame <= 7500]
            require(old_records == new_records, f'Original 0–4 binary key records changed: {i}/{tag}')
            keys += len(old_records)
    require([s['identity'] for s in before['sequences'][:5]] ==
            [s['identity'] for s in after['sequences'][:5]], 'Original sequence identity changed')
    return keys


def verify_model(data):
    formal = parse_mdx(prior(FORMAL, MODEL))
    cartoon = parse_mdx(prior(CARTOON, MODEL))
    current = parse_mdx(data)
    keys = original_keys_equal(formal, cartoon)
    require(original_keys_equal(cartoon, current) == keys, 'Original key-count chain mismatch')
    require([(s['name'], s['start'], s['end'], s['loop']) for s in current['sequences']] == SEQUENCES,
            'Ten sequence names/indices/intervals/loops differ from approved display contract')
    require(cartoon['geometry'] == current['geometry'], 'Cartoon → display geometry/UV/binding changed')
    for tag in ('PVTX', 'GNDX', 'MTGC', 'MATS'):
        require(formal['geometry'][tag] == cartoon['geometry'][tag], 'Formal → cartoon topology/binding changed')
    require(len(current['geometry']['PVTX']) // 6 == 3038, 'Expected 3038 triangles')
    require(current['texture'] == 'Textures\\SilverManeAtlas.blp', 'Incorrect exact MDX texture path')
    require([(a['name'], a['parentId'], a['objectId'], a['attachmentId'], a['path'])
             for a in current['attachments']] ==
            [('Origin Ref', 0, 11, 0, ''), ('Head Ref', 2, 12, 1, '')], 'Reference attachments changed')
    require(current['pivots'][11:] == [(0.0, 0.0, 0.0), (43.0, 0.0, 49.0)], 'Attachment pivots changed')
    return {'originalBinaryKeyRecordsPreservedPerChainLink': keys,
            'originalSequenceIdentityPreserved': True, 'cartoonToDisplayGeometryByteIdentical': True,
            'formalToCartoonGeometryByteIdentical': formal['geometry'] == cartoon['geometry'],
            'formalToCartoonTopologyBindingPreserved': True, 'triangles': 3038, 'bones': 11,
            'singleOpaqueMaterialAndTexture': True, 'emitters': 0, 'unusedReferenceAttachments': 2,
            'texturePath': current['texture'], 'rawModelGrowthBytes': len(data) - len(prior(CARTOON, MODEL)),
            'modelExtent': current['modelExtent'], 'sequences': [
                {'index': i, 'name': s['name'], 'interval': [s['start'], s['end']],
                 'durationMs': s['end'] - s['start'], 'loop': s['loop'],
                 'extent': s['extent'], 'geosetExtent': current['geosetSequenceExtents'][i]}
                for i, s in enumerate(current['sequences'])]}


def resource_source_check(base_ref=BASE, companion=False):
    for path, (digest, size) in APPROVED.items():
        data = (ROOT / path).read_bytes()
        require((sha(data), len(data)) == (digest, size), f'Approved pair mismatch: {path}')
    model_paths = paths_at(DISPLAY, MODEL_DIR)
    require({str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / MODEL_DIR).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts} == set(model_paths), 'Species-1 source file set changed')
    for path in model_paths:
        require((ROOT / path).read_bytes() == prior(DISPLAY, path), f'Approved model source mismatch: {path}')
    original = json.loads(prior(FORMAL, MODEL_DIR + '/original/silvermane-source.json'))
    source = json.loads((ROOT / MODEL_DIR / 'original/silvermane-source.json').read_text())
    require(original['sequences'] == source['sequences'][:5], 'Original source sequences changed')
    for a, b in zip(original['bones'], source['bones']):
        require({k: v for k, v in a.items() if k != 'tracks'} ==
                {k: v for k, v in b.items() if k != 'tracks'}, 'Original source bone changed')
        for tag, records in a['tracks'].items():
            require(b['tracks'][tag][:len(records)] == records, 'Original source key records changed')
    manifest = json.loads((ROOT / MANIFEST).read_text())
    previous = json.loads(prior(base_ref, MANIFEST))
    approved = json.loads(prior(DISPLAY, MANIFEST))
    require(len(manifest['models']) == 15 and manifest['models'][0] == approved['models'][0], 'Species1 manifest mismatch')
    require(manifest['models'][1:] == previous['models'][1:], 'Other14 model manifest entries changed')
    require({k: v for k, v in manifest.items() if k != 'models'} ==
            {k: v for k, v in previous.items() if k != 'models'}, 'Manifest top-level metadata changed')
    for entry in manifest['models']:
        for path_key, hash_key, bytes_key in [('modelImportPath', 'modelSha256', 'modelBytes'),
                                               ('requiredTextureImportPath', 'textureSha256', 'textureBytes')]:
            data = (ROOT / 'imports' / entry[path_key].replace('\\', '/')).read_bytes()
            require((sha(data), len(data)) == (entry[hash_key], entry[bytes_key]), entry[path_key])
    imports = paths_at(base_ref, 'imports')
    # Licensed King Leoric originals are intentionally ignored in Git and are
    # restored by the existing preparation tool. They already ship in the base
    # map; permitting exactly these four files is not retired-asset revival.
    restored = json.loads(prior(base_ref, 'assets/source/king-leoric.json'))['assets']
    restored_paths = {entry['import_path'] for entry in restored}
    current_paths = {str(p.relative_to(ROOT)).replace('\\', '/') for p in (ROOT / 'imports').rglob('*') if p.is_file()}
    companion_paths = set(BASIC_HIT_APPROVED) if companion else set()
    for path in companion_paths:
        data = (ROOT / path).read_bytes()
        require((sha(data),len(data)) == BASIC_HIT_APPROVED[path], 'Approved companion mesh differs: '+path)
    require(current_paths == set(imports) | restored_paths | companion_paths,
            'Imported asset set changed; no additions/deleted-asset resurrection allowed')
    published = Mpq(prior(base_ref, 'ExampleMap.w3x'))
    for entry in restored:
        path = entry['import_path']
        data = (ROOT / path).read_bytes()
        require((sha(data), len(data)) == (entry['sha256'], entry['size_bytes']),
                f'Restored licensed original differs: {path}')
        require(data == published.extract(path.removeprefix('imports/').replace('/', '\\')),
                f'Restored asset differs from published map: {path}')
    preserved_imports = 0
    for path in imports:
        if path not in APPROVED:
            require((ROOT / path).read_bytes() == prior(base_ref, path), f'Unrelated import changed: {path}')
            preserved_imports += 1
    preserved_sources = 0
    for path in paths_at(base_ref, 'assets/source'):
        if path.startswith(MODEL_DIR + '/') or path in (MANIFEST, PROVENANCE):
            continue
        require((ROOT / path).read_bytes() == prior(base_ref, path), f'Unrelated asset source/manifest changed: {path}')
        preserved_sources += 1
    provenance = (ROOT / PROVENANCE).read_text()
    require(provenance.startswith(prior(base_ref, PROVENANCE).decode().rstrip()), 'Existing provenance lost')
    require('cartoon-texture-provenance.json' in provenance and 'b24e6c19' in provenance and 'fb47e968' in provenance,
            'Missing cartoon/display provenance')
    return {'approvedPair': {path: {'sha256': digest, 'bytes': size} for path, (digest, size) in APPROVED.items()},
            'otherModelPairsPreserved': 14, 'unchangedOtherImports': preserved_imports,
            'unchangedOtherAssetSourcesAndManifests': preserved_sources,
            'unchangedRestoredLicensedOriginals': len(restored),
            'noImportedAssetAddedOrResurrected': True,
            'model': verify_model((ROOT / MODEL).read_bytes())}


def source_check(base_ref=BASE):
    files = {p.stem: p.read_text() for p in (ROOT / 'wurst').rglob('*.wurst')}
    rules, runtime = files['TDPetDisplayRules'], files['TDPetDisplayRuntime']
    forbidden = r'\b(?:Random\w*|GetRandom\w*|GetLocalPlayer|Create\w*|Destroy\w*|RemoveUnit|Issue\w*|doAfter|doPeriodically)\s*\('
    require(not re.search(forbidden, rules + runtime), 'Display introduced RNG/local state/handles/orders/timer')
    require(not re.search(r'\b(?:Blz\w*|Arav)\b', runtime), 'Nonclassic fly-height workaround/native introduced')
    require('return species == 1' in rules and '((lane * 20 + slot + species * 3) mod 17)' in rules,
            'Capability or deterministic idle gap changed')
    require('pet.generation == generation' in runtime and 'pet.host == host' in runtime,
            'Captured ownership generation fence missing')
    require('distanceTo(desired) > 1.0' in runtime and 'GetUnitFlyHeight(pet.visual) - height) > 1.0' in runtime,
            'Steady-state setter thresholds missing')
    require('if pet.visualAction != action' in runtime, 'Repeated animation setter guard missing')
    require('pet.paused or not tdPetDisplaySupported(pet.species)' in runtime, 'Cast pause/capability guard missing')
    graph = {name: re.findall(r'^import\s+(?:public\s+)?(\w+)', text, re.M) for name, text in files.items()}
    require('TDPetDisplayRuntime' in graph['TDPetRuntime'] and 'TDPetDisplayRuntime' in graph['TDPetCombat'],
            'Runtime/Combat display dependency missing')
    visiting, seen = set(), set()
    def visit(name):
        require(name not in visiting, f'Display import cycle: {name}')
        if name in seen or name not in graph:
            return
        visiting.add(name)
        for child in graph[name]:
            require(child not in ('TDPetCombatSource', 'TDPetRuntime'), f'Reverse display dependency: {name} → {child}')
            visit(child)
        visiting.remove(name)
        seen.add(name)
    visit('TDPetDisplayRuntime')
    obj = files['TDPetObjectGen']
    old_obj = prior(base_ref, 'wurst/pets/TDPetObjectGen.wurst').decode()
    new_block = next(line for line in obj.splitlines() if 'new UnitDefinition(tdPetVisualUnitId' in line)
    old_block = next(line for line in old_obj.splitlines() if 'new UnitDefinition(tdPetVisualUnitId' in line)
    expected = old_block.replace('MovementType.None', 'MovementType.Fly').replace(
        '..setScalingValue(0.45)', '..setScalingValue(0.45)..setMovementHeight(160.0)..setMovementHeightMinimum(0.0)')
    require(new_block == expected and obj.replace(new_block, old_block) == old_obj,
            'Object source changed beyond pv-only flight/fallback/minimum height')
    state = files['TDPetState']
    for default in ('visualAction = -1', 'visualNextAt = 0.0', 'visualCycle = 0'):
        require(state.count(default) == 2, f'Cosmetic construction/invalidation default missing: {default}')
    combat = files['TDPetCombat']
    require(combat.count('tdPetDisplayCast(') == 1 and re.search(
        r'if started and tdTrialContextValid\(context\) and tdPetBindingValid\(pet, host, generation\)\s+'
        r'pet\.readyAt = [^\n]+\s+if activeSkill == 11 or activeSkill == 12\s+'
        r'tdCombatVisualStartPetBuff\([^\n]+\)\s+tdPetDisplayCast\(pet, host, generation, getElapsedGameTime\(\)\)', combat),
        'Cast hook is not the last successful-activation statement')
    return {'importGraphAcyclic': True, 'noReverseRuntimeCombatDependency': True,
            'noDisplayRngTimerHandleOrderGrowth': True, 'pvOnlyObjectSourceDelta': True,
            'singlePostSuccessCastHook': True}


def jass_body(script, name):
    match = re.search(r'^function ' + re.escape(name) + r' takes [^\n]+\n(.*?)^endfunction\b', script, re.M | re.S)
    require(match is not None, f'Missing actual JASS function: {name}')
    return match.group(1)



def verify_reduce_buff_tooltip(current, baseline):
    now=parse_objects(current,False);old=parse_objects(baseline,False)
    require(now.keys()==old.keys(),'Buff object set changed')
    changed=[]
    for uid,a in now.items():
        b=old[uid]
        require(a.table==b.table and a.identity==b.identity and a.fields.keys()==b.fields.keys(),'Buff identity/fields changed: '+uid)
        for key,field in a.fields.items():
            prior_field=b.fields[key]
            if field==prior_field:continue
            require(key==('fube',0,0) and a.fields[('fnam',0,0)].value=='精灵减击 1','Unexpected Buff field delta: '+uid+': '+str(key))
            require(field.kind==prior_field.kind==3 and field.value==prior_field.value.replace(REDUCE_TOOLTIP_OLD,REDUCE_TOOLTIP_NEW) and REDUCE_TOOLTIP_NEW in field.value,'Incorrect quality-dependent reduce tooltip')
            changed.append(uid+'.fube')
    require(len(changed)==1,'Exactly one reduce Buff tooltip delta required')
    return changed

def artifact_check(current_path, baseline_path, resource_result, companion=False):
    data, before_data = current_path.read_bytes(), baseline_path.read_bytes()
    current, baseline = Mpq(data), Mpq(before_data)
    new_w3u, old_w3u = current.extract('war3map.w3u'), baseline.extract('war3map.w3u')
    now, old = unit_objects(new_w3u), unit_objects(old_w3u)
    require(now.keys() == old.keys() and unit_parents(new_w3u) == unit_parents(old_w3u), 'Unit set/parents changed')
    manifest = json.loads((ROOT / MANIFEST).read_text())
    for uid in now:
        if uid == 'wurs':
            continue  # Fresh compiler metadata only.
        a, b = now[uid].copy(), old[uid].copy()
        if uid in PV:
            require(a.get('umvt') == 'fly' and a.get('umvh') == 160.0 and a.get('umvf') == 0.0,
                    f'{uid}: incorrect packed fly/fallback/minimum height')
            require(math.isclose(a.get('usca', 0), .45, abs_tol=1e-6) and a.get('ucol') == 0.0
                    and a.get('umvs') == 0 and a.get('uaen') == 0 and a.get('uacq') == 0.0
                    and a.get('ufoo') == 0 and a.get('ubui') == '', f'{uid}: visual gameplay/footprint changed')
            require(set(a.get('uabi', '').split(',')) == {'Aloc', 'Avul'}, f'{uid}: missing Aloc/Avul')
            species = int(uid[-1], 16)
            require(a.get('umdl') == manifest['models'][species - 1]['modelImportPath'], f'{uid}: model linkage changed')
            for field in ('umvt', 'umvh', 'umvf'):
                a.pop(field, None)
                b.pop(field, None)
        require(a == b, f'Unexpected packed unit-field difference: {uid}')
    for name in ('war3map.w3a', 'war3map.w3t', 'war3map.w3b', 'war3map.w3d', 'war3map.w3h',
                 'war3map.w3q', 'war3map.w3e', 'war3map.wpm'):
        require(current.has(name) == baseline.has(name), f'Member presence changed: {name}')
        if current.has(name):
            if name=='war3map.w3h':
                verify_reduce_buff_tooltip(current.extract(name),baseline.extract(name))
                continue
            require(current.extract(name) == baseline.extract(name), f'Unrelated gameplay/terrain member changed: {name}')
    members, previous_members = current.members(), baseline.members()
    imports = {str(p.relative_to(ROOT / 'imports')).replace('/', '\\'): p for p in (ROOT / 'imports').rglob('*') if p.is_file()}
    companion_members = {p.removeprefix('imports/').replace('/', '\\') for p in BASIC_HIT_APPROVED} if companion else set()
    require(set(members) == set(previous_members) | companion_members, 'Packed member set changed; retired/new asset introduced')
    allowed = {p.removeprefix('imports/').replace('/', '\\') for p in APPROVED} | companion_members
    checked, icons = 0, 0
    for name, path in imports.items():
        packed = current.extract(name)
        require(packed == path.read_bytes(), f'Packed import differs from source: {name}')
        if name not in allowed:
            require(packed == baseline.extract(name), f'Unrelated packed import changed: {name}')
            checked += 1
            icons += int('BTN' in name and name.endswith('.blp'))
    for name in members:
        if name not in allowed and (name.lower().endswith(('.blp', '.mdx', '.mdl', '.tga', '.png', '.mp3', '.wav'))):
            require(members[name] == previous_members[name], f'Other packed media changed: {name}')
    packed_model = verify_model(current.extract('war3mapImported\\SilverManeBeast.mdx'))
    require(packed_model == resource_result['model'], 'Packed model parse differs from source parse')
    script, old_script = current.extract('war3map.j').decode(), baseline.extract('war3map.j').decode()
    for name in ('tdPetDisplayOwnerValid', 'tdPetDisplayInitialize', 'tdPetDisplayTick', 'tdPetDisplayCast'):
        body = jass_body(script, name)
        require(not re.search(r'\b(?:GetRandom\w*|GetLocalPlayer|CreateTimer|CreateUnit|DestroyTimer|RemoveUnit|Issue\w*)\s*\(', body),
                f'Forbidden display gameplay/handle/RNG native: {name}')
    require('TDPet_generation' in jass_body(script, 'tdPetDisplayOwnerValid'), 'Packed captured-generation fence absent')
    require(len(re.findall(r'\bcall TimerStart\(', script)) == len(re.findall(r'\bcall TimerStart\(', old_script)),
            'Packed TimerStart site count grew')
    require(len(re.findall(r'\bcall SetUnitAnimationByIndex\(', jass_body(script, 'tdPetDisplayCast'))) == 1,
            'Packed Cast does not have exactly one index setter')
    return {'status': 'PASS', 'mapSHA256': sha(data), 'baselineSHA256': sha(before_data),
            'boundVisualObjects': 15, 'allowedBoundVisualFields': ['umvt', 'umvh', 'umvf'],
            'allOtherUnitFieldsAndParentsPreserved': True, 'otherObjectFilesAndTerrainPreserved': True,
            'packedImportsEqualCurrentSource': len(imports), 'unchangedOtherPackedImports': checked,
            'unchangedPackedIcons': icons, 'unchangedPackedMemberSet': True,
            'packedDisplayFunctionClosure': True, 'noNewPackedTimerStartSites': True,
            'model': packed_model,
            'boundary': 'Actual MPQ/object/resource/JASS structural closure only; lifecycle/combat replay is separate. '
                        'Native head overlap, animation reset/culling, and FPS remain unobserved.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path, nargs='?')
    parser.add_argument('baseline', type=Path, nargs='?')
    parser.add_argument('--baseline-ref', default=BASE)
    parser.add_argument('--allow-basic-hit-vfx', action='store_true', help='Permit only five exact meshes from approved independent 37191dfa companion change')
    parser.add_argument('--resources-only', action='store_true', help='Skip runtime source and final artifact structural checks')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    require(bool(args.map) == bool(args.baseline), 'Provide both current and matching baseline maps')
    require(not (args.resources_only and args.map), '--resources-only accepts no final map')
    resources = resource_source_check(args.baseline_ref, args.allow_basic_hit_vfx)
    result = {'status': 'PASS', 'sourceResources': resources}
    if not args.resources_only:
        result['sourceStructure'] = source_check(args.baseline_ref)
    if args.map:
        result['artifact'] = artifact_check(args.map, args.baseline, resources, args.allow_basic_hit_vfx)
    else:
        result['artifactStatus'] = 'NOT RUN: requires final map and matching published baseline'
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
