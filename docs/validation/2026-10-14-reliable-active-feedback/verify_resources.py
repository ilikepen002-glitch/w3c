"""Verify exact persistent-buff resources and bounded final MPQ delta."""
import argparse, hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyGlobalRankingsArtifact import members
p = argparse.ArgumentParser()
p.add_argument('--map', required=True, type=Path)
p.add_argument('--baseline-map', required=True, type=Path)
a = p.parse_args()
cur, old = members(Mpq(a.map.read_bytes())), members(Mpq(a.baseline_map.read_bytes()))
manifest = json.loads((ROOT / 'assets/source/persistent-buff-vfx/manifest.json').read_text())
expected = {m['resourcePath'].casefold() for m in manifest['models']}
added, removed = sorted(cur.keys() - old.keys()), sorted(old.keys() - cur.keys())
changed = sorted(k for k in cur.keys() & old.keys() if cur[k][1] != old[k][1])
assert set(added) == expected, added
assert not removed, removed
assert set(changed) <= {'(listfile)', 'war3map.imp', 'war3map.j', 'war3map.w3i'}, changed
script = cur['war3map.j'][1].decode('utf-8')
for m in manifest['models']:
    raw = cur[m['resourcePath'].casefold()][1]
    assert raw == (ROOT / m['importFile']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == m['sha256']
    assert m['resourcePath'].replace('\\', '\\\\') in script
    tex = m['texture'].casefold()
    assert cur[tex][1] == old[tex][1]
    assert hashlib.sha256(cur[tex][1]).hexdigest() == m['textureSha256']
print(json.dumps(dict(status='PASS', mapSHA256=hashlib.sha256(a.map.read_bytes()).hexdigest(), baselineSHA256=hashlib.sha256(a.baseline_map.read_bytes()).hexdigest(), added=added, removed=removed, changed=changed, unchanged=len(cur.keys() & old.keys())-len(changed), models=[{k:m[k] for k in ('name','resourcePath','sha256','bytes','triangles','durationMs')} for m in manifest['models']], atlasUnchanged=True), indent=2))
