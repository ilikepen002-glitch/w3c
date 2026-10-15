#!/usr/bin/env python3
"""Read-only 15-species resource/source/actual-MPQ closure gate.

Pairs with InspectSpiritRefinementModels.cjs for MDX800/BLP/pose inspection.
Historical display-extension validators remain historical, not applicable evidence
for retextured assets or the replacement phoenix. This does not launch Warcraft.
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

ROOT = Path(__file__).resolve().parents[1]
BASE = '163b613d5d52a7190c9db3bf0b61b62658feaca7'
MANIFEST = 'assets/source/elemental-spirits/import-manifest.json'

def require(ok, text):
    if not ok:
        raise AssertionError(text)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def prior(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)

def paths_at(prefix):
    return subprocess.check_output(['git', 'ls-tree', '-rz', '--name-only', BASE, prefix], cwd=ROOT).decode().rstrip('\0').split('\0')

def chunks(data):
    require(data[:4] == b'MDLX', 'Missing MDX magic')
    out, pos = {}, 4
    while pos < len(data):
        tag = data[pos:pos+4].decode('ascii')
        size = struct.unpack_from('<I', data, pos+4)[0]
        require(tag not in out and pos+8+size <= len(data), 'Malformed or duplicate MDX chunk')
        out[tag] = data[pos+8:pos+8+size]
        pos += 8+size
    require(pos == len(data), 'Trailing MDX data')
    return out

def verify_source():
    paths = paths_at('wurst') + paths_at('tests/wurst')
    phoenix = json.loads((ROOT/MANIFEST).read_text())['models'][9]
    for path in paths:
        expected = prior(path)
        if path == 'wurst/pets/TDPetObjectGen.wurst' and phoenix.get('wildModelImportPath'):
            old = '..setModelFile(tdPetModel(species))\n\t\t\t..setScalingValue(2.55)'
            new = '..setModelFile(species == 10 ? "' + phoenix['wildModelImportPath'].replace('\\','\\\\') + '" : tdPetModel(species))\n\t\t\t..setScalingValue(species == 10 ? ' + str(phoenix['wildScale']) + ' : 2.55)'
            require(expected.decode().count(old) == 1, 'Ambiguous wild-only model/scale insertion')
            expected = expected.decode().replace(old,new).encode()
        require((ROOT/path).read_bytes() == expected, 'Unexpected gameplay/test source change: ' + path)
    for path in ('wurst.build', 'maps/ExampleMap.source.w3x', 'tools/Run-WurstLinux.py',
                 'tools/compiler/compiler-lock.json'):
        require((ROOT/path).read_bytes() == prior(path), 'Build/template contract changed: ' + path)
    now = set(subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', 'wurst', 'tests/wurst'], cwd=ROOT).decode().rstrip('\0').split('\0'))
    require(now == set(paths), 'Runtime/test file added or removed')
    return {'baseline': BASE, 'byteIdenticalGameplayAndTestSources': len(paths) - bool(phoenix.get('wildModelImportPath')),
            'onlyAllowedObjectSourceChange': 'Species 10 wild model path and scale' if phoenix.get('wildModelImportPath') else None,
            'newRuntimeTimersOrPerFrameCode': False, 'nativeArcherAttackAndCancelledPossessionAttackLooksPreserved': True}

def verify(inspection, map_path=None):
    require(inspection['status'] == 'PASS' and len(inspection['models']) == 15, 'Missing final inspector PASS')
    manifest = json.loads((ROOT/MANIFEST).read_text())
    require(len(manifest['models']) == 15, 'Not exactly 15 species')
    rows = []
    allowed = set()
    mpq = Mpq(map_path.read_bytes()) if map_path else None
    units = unit_objects(mpq.extract('war3map.w3u')) if mpq else None
    reference_count = 0
    for index, (entry, inspected) in enumerate(zip(manifest['models'], inspection['models']), 1):
        require(entry['suggestedSpeciesId'] == inspected['species'] == index, 'Species order changed')
        model_path = 'imports/' + entry['modelImportPath'].replace('\\', '/')
        current = (ROOT/model_path).read_bytes()
        require(sha(current) == entry['modelSha256'] == inspected['sha256'], 'Stale model inspection/manifest')
        require(len(current) == entry['modelBytes'] == inspected['bytes'], 'Model length mismatch')
        allowed.add(model_path)
        textures = []
        for texture in inspected['textures']:
            if texture['kind'] != 'packaged-custom':
                require(texture['kind'] == 'native-replaceable' or texture['path'] in entry.get('nativeTexturePaths', []), 'Missing custom texture')
                continue
            name = texture['path']
            path = 'imports/' + name.replace('\\', '/')
            raw = (ROOT/path).read_bytes()
            require(sha(raw) == texture['sha256'] and len(raw) == texture['bytes'], 'Stale texture inspection ' + name)
            allowed.add(path)
            if mpq:
                require(mpq.extract(name) == raw, 'Packed texture differs: ' + name)
            textures.append({'path': name, 'sha256': sha(raw), 'bytes': len(raw)})
        before = chunks(prior(model_path))
        after = chunks(current)
        preserved = []
        if index != 10:
            # Refinement may alter eyes/UVs, materials and derived culling bounds;
            # original rig and every animation track must remain exactly intact.
            for tag in ('BONE', 'HELP', 'PIVT', 'ATCH', 'CAMS', 'GLBS', 'PREM', 'PRE2', 'RIBB', 'EVTS'):
                require(before.get(tag) == after.get(tag), f'{entry["name"]}: original rig/animation/emitter chunk changed: {tag}')
                if tag in before:
                    preserved.append(tag)
            require(len(before['SEQS']) == len(after['SEQS']) == 1320, 'Original ten sequences changed')
            for si in range(10):
                require(before['SEQS'][si*132:si*132+104] == after['SEQS'][si*132:si*132+104], 'Original sequence identity changed')
        wild_refs = []
        if entry.get('wildModelImportPath'):
            wild_path = 'imports/' + entry['wildModelImportPath'].replace('\\','/')
            wild = (ROOT/wild_path).read_bytes()
            require(sha(wild) == entry['wildModelSha256'] and len(wild) == entry['wildModelBytes'], 'Wild phoenix manifest mismatch')
            allowed.add(wild_path)
            if mpq:
                require(mpq.extract(entry['wildModelImportPath']) == wild, 'Packed wild phoenix differs')
                wild_refs = [code for code, fields in units.items() if fields.get('umdl') == entry['wildModelImportPath']]
                require(set(wild_refs) == {f'p{wave:02X}A' for wave in range(1,33)}, 'Wild model assigned outside exact species10 waves')
                require(all(math.isclose(units[code]['usca'], entry['wildScale'], abs_tol=1e-6) for code in wild_refs), 'Wild scale output mismatch')
        if mpq:
            require(mpq.extract(entry['modelImportPath']) == current, 'Packed MDX differs: ' + entry['name'])
            refs = [code for code, fields in units.items() if fields.get('umdl') == entry['modelImportPath']]
            # 32 wild waves, four collection qualities and one overhead visual.
            expected_references = 38 if index == 3 else 37  # Species 3 also fronts collection UI.
            require(len(refs) + len(wild_refs) == expected_references, f'{entry["name"]}: unexpected actual unit model references: {len(refs)}')
            require(f'pv0{index:X}' in refs, 'Missing actual overhead visual reference')
            reference_count += len(refs) + len(wild_refs)
        rows.append({'species': index, 'name': entry['name'], 'modelSha256': sha(current),
                     'textures': textures, 'preservedRigAnimationChunks': preserved,
                     'replacementPhoenix': index == 10, 'packedUnitModelReferences': len(refs) + len(wild_refs) if mpq else 0})
    for path in paths_at('imports'):
        if path not in allowed:
            require((ROOT/path).read_bytes() == prior(path), 'Unrelated imported resource changed: ' + path)
    report = {'status': 'PASS', 'source': verify_source(), 'models': rows,
              'packedModelPairsVerified': 15 if mpq else 0, 'packedUnitModelReferences': reference_count,
              'modelBytes': inspection['totalModelBytes'], 'triangles': inspection['totalTriangles'],
              'uniqueCustomTextureBytes': inspection['uniqueCustomTextureBytes'],
              'nativeTextureBoundary': [dict(species=m['species'], texture=t) for m in inspection['models'] for t in m['textures'] if t['kind'] != 'packaged-custom'],
              'boundary': 'Source, final asset bytes, sampled poses and actual MPQ references only. Native Warcraft III 1.27a rendering, native dependencies, camera billboard behavior and FPS are not tested.'}
    if mpq:
        require(mpq.extract('Credits-Phoenix.txt') == (ROOT/'imports/Credits-Phoenix.txt').read_bytes(), 'Missing final phoenix source credit')
        report['embeddedJohnwarCreditVerified'] = True
        report['mapSha256'] = sha(map_path.read_bytes())
        report['mapBytes'] = map_path.stat().st_size
        # Art-only update must not silently change combat/object/scheduling output.
        baseline_mpq = Mpq(prior('ExampleMap.w3x'))
        unchanged = []
        for name in ('war3map.w3u', 'war3map.w3a', 'war3map.w3t', 'war3map.w3b', 'war3map.w3d', 'war3map.w3h', 'war3map.w3q'):
            if mpq.has(name) or baseline_mpq.has(name):
                if name == 'war3map.w3u' and manifest['models'][9].get('wildModelImportPath'):
                    prior_units = unit_objects(baseline_mpq.extract(name))
                    require(prior_units.keys() == units.keys(), 'Unit identities changed')
                    wild_codes = {f'p{wave:02X}A' for wave in range(1,33)}
                    for code, fields in units.items():
                        expected = dict(prior_units[code])
                        if code in wild_codes:
                            expected['umdl'] = manifest['models'][9]['wildModelImportPath']
                            expected['usca'] = fields['usca']  # precise target separately checked above
                        require(fields == expected, 'Unexpected unit field changed: ' + code)
                    report['onlyAllowedObjectDifferences'] = {'units': sorted(wild_codes), 'fields': ['umdl','usca']}
                else:
                    require(mpq.extract(name) == baseline_mpq.extract(name), 'Object output changed in art-only build: ' + name)
                    unchanged.append(name)
        report['byteIdenticalObjectFiles'] = unchanged
    return report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inspection', required=True, type=Path)
    p.add_argument('--map', type=Path)
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    report = verify(json.loads(a.inspection.read_text()), a.map)
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if a.output:
        a.output.write_text(text)
    print(text)

if __name__ == '__main__':
    main()
