#!/usr/bin/env python3
"""Append-only 15-species display source/import/MPQ gate; no native rendering claim.

python3 tools/VerifyAllPetDisplayArtifact.py --output report.json
python3 tools/VerifyAllPetDisplayArtifact.py --map final.w3x --output packed.json
The independent packed lifecycle/combat replay remains VerifyPetDisplayReplay.py.
"""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

from VerifyPetDisplayArtifact import parse_mdx, SEQUENCES, require
from GenerateTowerTerrainMask import Mpq

ROOT = Path(__file__).resolve().parents[1]
BASE = '2847c3f742a69661972cabb7a616e08e81cbae9c'
MANIFEST = 'assets/source/elemental-spirits/import-manifest.json'


def prior(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def chunks(data):
    result, cursor = {}, 4
    while cursor < len(data):
        tag = data[cursor:cursor + 4].decode()
        size = struct.unpack_from('<I', data, cursor + 4)[0]
        result[tag] = data[cursor + 8:cursor + 8 + size]
        cursor += 8 + size
    return result


def verify_model(before_bytes, current_bytes, entry):
    before, now = parse_mdx(before_bytes), parse_mdx(current_bytes)
    require([(s['name'], s['start'], s['end'], s['loop']) for s in now['sequences']] == SEQUENCES,
            'Display index/name/interval/loop contract changed: ' + entry['name'])
    require(before['geometry'] == now['geometry'], 'Geometry/normal/UV/topology/binding changed')
    require(before['pivots'] == now['pivots'] and before['attachments'] == now['attachments'],
            'Skeleton pivots/attachments changed')
    require(before['texture'] == now['texture'] == entry['requiredTextureImportPath'], 'Texture reference changed')
    require(before['sequences'][:5] == now['sequences'][:5], 'Original 0–4 sequences/extents changed')
    require(before['geosetSequenceExtents'][:5] == now['geosetSequenceExtents'][:5], 'Original geoset extents changed')
    require(len(before['bones']) == len(now['bones']) == entry['bones'], 'Bone count changed')
    original_keys = 0
    animated = {s[0]: set() for s in SEQUENCES[5:]}
    for old, new in zip(before['bones'], now['bones']):
        require({k: v for k, v in old.items() if k != 'tracks'} ==
                {k: v for k, v in new.items() if k != 'tracks'}, 'Bone identity changed')
        require(old['tracks'].keys() == new['tracks'].keys(), 'Track set changed')
        for tag, track in old['tracks'].items():
            newer = new['tracks'][tag]
            require((track['interpolation'], track['globalId']) == (newer['interpolation'], newer['globalId']),
                    'Track interpolation/global id changed')
            records, newer_records = track['records'], newer['records']
            require(newer_records[:len(records)] == records, 'Original 0–4 raw binary key changed')
            if entry['suggestedSpeciesId'] == 1:
                require(newer_records == records, 'Approved Silver Mane track changed')
            else:
                require(len(newer_records) == len(records) + 85, 'Expected 17 keys for each new sequence')
                require([f for f, _ in newer_records if f <= 7500] == [f for f, _ in records], 'Added keys in original intervals')
                if tag != 'KGSC' and new['name'] != 'Root':
                    for name, start, end, _ in SEQUENCES[5:]:
                        values = {raw[4:] for frame, raw in newer_records if start <= frame <= end}
                        if len(values) > 1:
                            animated[name].add(new['name'])
            original_keys += len(records)
    if entry['suggestedSpeciesId'] != 1:
        require(all(animated.values()), 'Display sequence moves only root')
    a, b = chunks(before_bytes), chunks(current_bytes)
    allowed = {'MODL', 'SEQS', 'BONE', 'GEOS'}
    require(a.keys() == b.keys(), 'MDX chunk set changed')
    require(all(a[k] == b[k] for k in a if k not in allowed), 'Camera/material/other MDX chunk changed')
    if entry['suggestedSpeciesId'] == 1:
        require(before_bytes == current_bytes, 'Approved Silver Mane model changed')
    return {'species': entry['suggestedSpeciesId'], 'name': entry['name'], 'sha256': sha(current_bytes),
            'bytes': len(current_bytes), 'originalBinaryKeyRecordsPreserved': original_keys,
            'geometryUvNormalsTopologyBindingByteIdentical': True, 'originalSequencesAndExtentsPreserved': True,
            'cameraMaterialTextureAndRigPreserved': True, 'triangles': len(now['geometry']['PVTX']) // 6,
            'bones': len(now['bones']), 'displaySequenceIndices': list(range(5, 10)),
            'rawGrowthBytes': len(current_bytes) - len(before_bytes),
            'animatedNonRootBonesBySequence': {k: sorted(v) for k, v in animated.items()}}


def resource_check(root=ROOT, map_path=None):
    manifest = json.loads((root / MANIFEST).read_text())
    baseline = json.loads(prior(MANIFEST))
    require({k: v for k, v in manifest.items() if k != 'models'} ==
            {k: v for k, v in baseline.items() if k != 'models'}, 'Manifest top-level metadata changed')
    require(len(manifest['models']) == 15, 'Expected 15 species')
    reports, changed_imports = [], set()
    packed = Mpq(map_path.read_bytes()) if map_path else None
    for old, entry in zip(baseline['models'], manifest['models']):
        require({k: v for k, v in old.items() if k not in ('modelSha256', 'modelBytes')} ==
                {k: v for k, v in entry.items() if k not in ('modelSha256', 'modelBytes')},
                'Manifest changed geometry/texture/species identity')
        model_path = 'imports/' + entry['modelImportPath'].replace('\\', '/')
        texture_path = 'imports/' + entry['requiredTextureImportPath'].replace('\\', '/')
        model, texture = (root / model_path).read_bytes(), (root / texture_path).read_bytes()
        require((sha(model), len(model)) == (entry['modelSha256'], entry['modelBytes']), 'Model manifest hash mismatch')
        require((sha(texture), len(texture)) == (entry['textureSha256'], entry['textureBytes']), 'Texture manifest hash mismatch')
        require(texture == prior(texture_path), 'Approved atlas changed')
        reports.append(verify_model(prior(model_path), model, entry))
        if entry['suggestedSpeciesId'] != 1:
            changed_imports.add(model_path)
        if packed:
            require(packed.extract(entry['modelImportPath']) == model, 'Packed display MDX differs from current import')
            require(packed.extract(entry['requiredTextureImportPath']) == texture, 'Packed display texture differs from approved import')
    tracked = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', BASE, 'imports'], cwd=ROOT).decode().rstrip('\0').split('\0')
    for path in tracked:
        if path not in changed_imports:
            require((root / path).read_bytes() == prior(path), 'Unrelated import changed: ' + path)
    originals = subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', BASE, 'assets/source/elemental-spirits/models'], cwd=ROOT).decode().rstrip('\0').split('\0')
    for path in originals:
        if path.endswith('/export_validate.cjs') and '/SilverManeBeast/' not in path:
            continue
        require((root / path).read_bytes() == prior(path), 'Original geometry/rig/atlas source changed: ' + path)
    return {'models': reports, 'allFifteenAtlasBytesPreserved': True,
            'originalGeometryRigAndTextureSourcesPreserved': True, 'otherTrackedImportsPreserved': len(tracked) - 14,
            'totalRawMdxGrowthBytes': sum(r['rawGrowthBytes'] for r in reports),
            'packedModelAndTexturePairsVerified': 15 if packed else 0}


def source_check(root=ROOT):
    rules = (root / 'wurst/pets/TDPetDisplayRules.wurst').read_text()
    before = prior('wurst/pets/TDPetDisplayRules.wurst').decode()
    expected = before.replace('import TDConfig\n', 'import TDConfig\nimport TDPetData\n').replace(
        'return species == 1', 'return species >= 1 and species <= TD_PET_SPECIES_COUNT')
    require(rules == expected, 'Display rule changed beyond capability 1–15')
    for path in ('wurst/pets/TDPetDisplayRuntime.wurst', 'wurst/pets/TDPetRuntime.wurst',
                 'wurst/pets/TDPetCombat.wurst', 'wurst/pets/TDPetState.wurst', 'wurst/pets/TDPetObjectGen.wurst'):
        require((root / path).read_bytes() == prior(path), 'Display lifecycle/combat/object ownership changed: ' + path)
    return {'onlyCapabilityRangeChanged': True, 'displayRuntimeStateAndSchedulerUnchanged': True,
            'combatAndObjectValuesUnchanged': True, 'noNewTimerRngOrLifecycleProtocol': True}


def main():
    # Active refinements have a different honest contract: preserve gameplay and
    # original rigs, validate intentional art changes and the replacement phoenix.
    # Never relax or rewrite the historical immutable-geometry assertions above.
    if json.loads((ROOT / MANIFEST).read_text()).get('refinementRevision'):
        import sys
        import tempfile
        with tempfile.TemporaryDirectory(prefix='spirit-display-verify-') as tmp:
            inspection = Path(tmp) / 'inspection.json'
            subprocess.run(['node', str(ROOT / 'tools/InspectSpiritRefinementModels.cjs'),
                            '--output', str(inspection)], check=True)
            subprocess.run([sys.executable, str(ROOT / 'tools/VerifySpiritRefinementArtifact.py'),
                            '--inspection', str(inspection), *sys.argv[1:]], check=True)
        return
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    report = {'status': 'PASS', 'baseline': BASE, 'source': source_check(),
              'resources': resource_check(map_path=a.map),
              'boundary': 'MDX/source/MPQ structural preservation only; independent Node sampling and packed replay required. No Warcraft rendering/FPS claim.'}
    if a.map:
        report['mapSha256'] = sha(a.map.read_bytes())
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if a.output:
        a.output.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
