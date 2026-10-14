#!/usr/bin/env python3
"""Attached-only scale and model-envelope gate. No native rendering claim."""
import json
import re
import subprocess
from pathlib import Path
from VerifyPetDisplayArtifact import parse_mdx
ROOT = Path(__file__).resolve().parents[1]
BASE = '779151ec'

def verify(root=ROOT):
    def prior(path):
        return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT).decode()
    rules_path = 'wurst/pets/TDPetDisplayRules.wurst'
    rules = (root / rules_path).read_text()
    prefix, scales = rules.split('// Attached-only art scale.', 1)
    assert prefix.rstrip() == prior(rules_path).rstrip(), 'Height/animation rules changed'
    pairs = re.findall(r'if species == (\d+)\s+return ([\d.]+)', scales)
    values = {int(i):float(v) for i,v in pairs}
    assert sorted(values) == list(range(1,16)) and len(pairs)==15, 'Missing/duplicate species'
    assert all(.75 <= v <= 1.5 for v in values.values()), 'Unsafe attached scale'
    obj_path = 'wurst/pets/TDPetObjectGen.wurst'
    obj = (root / obj_path).read_text()
    expected = prior(obj_path).replace('import TDPetData\n', 'import TDPetData\nimport TDPetDisplayRules\n').replace('..setScalingValue(0.45)..setMovementHeight', '..setScalingValue(tdPetDisplayScale(species))..setMovementHeight')
    assert obj == expected, 'Changed non-attached object field'
    assert obj.count('setScalingValue(tdPetDisplayScale(species))') == 1
    rows = []
    for entry in json.loads((root / 'assets/source/elemental-spirits/import-manifest.json').read_text())['models']:
        model = parse_mdx((root / 'imports' / entry['modelImportPath'].replace('\\','/')).read_bytes())
        scale = values[entry['suggestedSpeciesId']]
        extent = model['sequences'][5]['extent']
        axes = [b-a for a,b in zip(extent['min'],extent['max'])]
        assert 127 <= max(axes)*scale <= 133, 'Float silhouette outside 130 ± 3 world units'
        peak = max(max(b-a for a,b in zip(seq['extent']['min'], seq['extent']['max'])) for seq in model['sequences'][5:]) * scale
        assert peak <= 165, 'Display gesture grows beyond 165 world units'
        low = min(seq['extent']['min'][2] for seq in model['sequences'][5:])*scale
        assert low >= -8, 'Pose crosses tower clearance'
        rows.append(dict(species=entry['suggestedSpeciesId'],name=entry['name'],oldScale=.45,newScale=scale,floatAxes=axes,oldLongest=max(axes)*.45,newLongest=max(axes)*scale,maxGestureLongest=peak,minimumPoseZ=low))
    return dict(status='PASS',baseline=BASE,models=rows,wildScaleUnchanged=2.55,collectionScaleUnchanged=.65,heightFormulaUnchanged=True,boundary='Offline MDX extents and source only. Not native rendering, health-bar occlusion or FPS verification.')

if __name__ == '__main__':
    print(json.dumps(verify(),ensure_ascii=False,indent=2))
