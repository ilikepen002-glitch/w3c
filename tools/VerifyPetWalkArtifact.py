#!/usr/bin/env python3
"""Check wild-spirit animation calibration source, optionally final map + baseline.

python3 tools/VerifyPetWalkArtifact.py
python3 tools/VerifyPetWalkArtifact.py changed.w3x baseline.w3x
The baseline must have identical objects/imports except the three calibrated wild
fields. --combined-runtime explicitly permits independently verified VFX JASS changes.
No live-game claims.
"""
import argparse
import math
import hashlib
import json
import re
import sys
from pathlib import Path

from GenerateTowerTerrainMask import Mpq
from VerifyTowerPlacementArtifact import unit_objects
from VerifyUnitParentsArtifact import unit_parents

ROOT = Path(__file__).resolve().parents[1]
WILD = {f'p{wave:02X}{species:X}' for wave in range(1, 33) for species in range(1, 16)}


def source_check():
    source = (ROOT / 'wurst/pets/TDPetObjectGen.wurst').read_text()
    block = source.split('new UnitDefinition(tdPetWildUnitId(wave, species),')[1].split('new ItemDefinition')[0]
    assert 'for species = 1 to TD_PET_SPECIES_COUNT' in source
    assert 'for wave = 1 to tdWaveCount()' in source
    assert re.search(r'function tdWaveCount\(\) returns int\s+return 32\b', (ROOT / 'wurst/TDWaves.wurst').read_text())
    assert 'TD_PET_SPECIES_COUNT = 15' in (ROOT / 'wurst/pets/TDPetData.wurst').read_text()
    for setter in ('setAnimationWalkSpeed(50.0)', 'setAnimationRunSpeed(50.0)',
                   'setScalingValue(2.55)', 'setSpeedBase(120)', 'setSpeedMaximum(150)',
                   'setCollisionSize(0.0)', 'setNormalAbilities("Aeth")'):
        assert block.count('..' + setter) == 1, setter
    assert len(WILD) == 480
    # Neither wild movement nor deployment introduces an animation override.
    for file in ('TDPetWild.wurst', 'TDPetRuntime.wurst'):
        runtime = (ROOT / 'wurst/pets' / file).read_text()
        assert not re.search(r'SetUnit(?:TimeScale|Animation)|\.set(?:TimeScale|Animation)\(', runtime)
    print('PASS source: shared wild definition covers 480 rawcodes (32 waves × 15 species); scale2.55 and animation reference speeds50/50; gameplay settings unchanged.')


def artifact_check(current_path, baseline_path, combined_runtime=False):
    current, baseline = (Mpq(Path(p).read_bytes()) for p in (current_path, baseline_path))
    new_data, old_data = (mpq.extract('war3map.w3u') for mpq in (current, baseline))
    new, old = unit_objects(new_data), unit_objects(old_data)
    assert new.keys() == old.keys(), 'Unit set changed'
    assert unit_parents(new_data) == unit_parents(old_data), 'Unit parents changed'
    actual = {uid for uid, fields in new.items() if fields.get('unam', '').startswith('[野生精灵]')}
    assert actual == WILD, 'Wild object coverage mismatch'
    for uid in new:
        if uid == 'wurs':  # Compiler-generated metadata may change with a fresh compile.
            continue
        a, b = new[uid].copy(), old[uid].copy()
        if uid in WILD:
            assert a.get('uwal') == 50.0 and a.get('urun') == 50.0, uid
            assert math.isclose(a.get('usca',0),2.55,abs_tol=1e-6) and a.get('umvs') == 120 and a.get('ucol') == 0.0, uid
            for field in ('usca', 'uwal', 'urun'):
                a.pop(field, None)
                b.pop(field, None)
        assert a == b, f'Unexpected unit field difference: {uid}'
    manifest = json.loads((ROOT / 'assets/source/elemental-spirits/import-manifest.json').read_text())
    assert len(manifest['models']) == 15, 'Spirit model count changed'
    for entry in manifest['models']:
        for key, digest in (('modelImportPath', 'modelSha256'), ('requiredTextureImportPath', 'textureSha256')):
            data = current.extract(entry[key])
            assert data == baseline.extract(entry[key]), entry[key]
            assert hashlib.sha256(data).hexdigest() == entry[digest], entry[key]
    runtime_equal = current.extract('war3map.j') == baseline.extract('war3map.j')
    if not combined_runtime:
        assert runtime_equal, 'Runtime changed; use explicit --combined-runtime for separately verified combined work'
    result = {'status':'PASS', 'wildObjects':480, 'allowedWildFields':['usca','uwal','urun'],
              'scale':2.55,'walkReference':50.0,'runReference':50.0,'scaleReferenceProduct':127.5,
              'otherObjectsAndFieldsIdentical':True, 'bossObjectsIdentical':True,
              'modelTexturePairsIdentical':15, 'runtimeByteIdentical':runtime_equal,
              'combinedRuntimeExplicitlyPermitted':combined_runtime,
              'mapSHA256':hashlib.sha256(Path(current_path).read_bytes()).hexdigest(),
              'baselineSHA256':hashlib.sha256(Path(baseline_path).read_bytes()).hexdigest(),
              'boundary':'Packed objects/import bytes only; VFX runtime difference needs its separate source/22-active gates. No native Walk cadence/rendering assertion.'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map',type=Path,nargs='?')
    parser.add_argument('baseline',type=Path,nargs='?')
    parser.add_argument('--combined-runtime',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    assert bool(args.map)==bool(args.baseline), 'Provide both current and baseline maps'
    source_check()
    if args.map:
        result=artifact_check(args.map,args.baseline,args.combined_runtime)
        if args.output: args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    else:
        print('NOT RUN: final-map verification (requires new build and matching baseline).')
