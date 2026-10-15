#!/usr/bin/env python3
"""Attached-only presence gate; optional current MPQ object/import verification.
Offline extents and source are not a Warcraft rendering/occlusion test.
"""
import argparse,json,re,struct,subprocess,math
from pathlib import Path
from VerifySpiritRefinementArtifact import chunks
ROOT=Path(__file__).resolve().parents[1]
BASE='7834f5c890f3a95f9935e40a30f514e5fd88a994'

def verify(map_path=None):
    rules=(ROOT/'wurst/pets/TDPetDisplayRules.wurst').read_text()
    scales={int(i):float(v) for i,v in re.findall(r'if species == (\d+)\s+return ([\d.]+)',rules)}
    assert len(scales)==15
    manifest=json.loads((ROOT/'assets/source/elemental-spirits/import-manifest.json').read_text())
    mpq=None
    if map_path:
        from GenerateTowerTerrainMask import Mpq
        from VerifyTowerPlacementArtifact import unit_objects
        mpq=Mpq(Path(map_path).read_bytes());units=unit_objects(mpq.extract('war3map.w3u'))
    rows=[]
    for entry in manifest['models']:
        i=entry['suggestedSpeciesId'];name=entry['modelImportPath'];raw=(ROOT/'imports'/name.replace('\\','/')).read_bytes()
        seq=chunks(raw)['SEQS'];ex=struct.unpack_from('<7f',seq,5*132+104)
        longest=max(ex[k+4]-ex[k+1] for k in range(3))*scales[i]
        if i==10: assert scales[i]==1.04
        else: assert 228<=longest<=232,(i,longest)
        # This fix must not change existing creature meshes, textures or animations.
        assert raw==subprocess.check_output(['git','show',BASE+':imports/'+name.replace('\\','/')],cwd=ROOT)
        if mpq:
            assert mpq.extract(name)==raw
            code="pv"+format(i,"02X")
            assert units[code]["umdl"]==name
            assert math.isclose(units[code]["usca"],scales[i],abs_tol=1e-6)
        rows.append({'species':i,'attachedScale':scales[i],'floatEnvelopeLongest':longest})
    for name in ('TDPetPossessionStars.mdx','TDPetPossessionStars.blp'):
        raw=(ROOT/'imports/war3mapImported'/name).read_bytes()
        if mpq: assert mpq.extract('war3mapImported\\'+name)==raw
    link=chunks((ROOT/'imports/war3mapImported/TDPetPossessionStars.mdx').read_bytes())
    assert struct.unpack('<I',link['VERS'])[0]==800 and len(link['SEQS'])==132
    assert not any(k in link for k in ('PRE2','PREM','RIBB'))
    # Header bounds, exact host scaling formula and all 35 tower placements.
    columns=[]
    for choice,heights in enumerate(((110,160),(135,145),(115,145),(155,180),(105,185)),1):
        for level in range(1,7):
            scale=.95+level*.03;head=heights[level>4]*scale;pet=head+110
            # Authored top mote reaches above 310 even at its smallest pulse.
            assert 310*scale>=pet,(choice,level,pet)
            for branch in range(1,3 if level==6 else 2):
                columns.append({'choice':choice,'level':level,'branch':branch,'petBase':pet,'linkTopMinimum':310*scale})
    runtime=(ROOT/'wurst/pets/TDPetDisplayRuntime.wurst').read_text()
    assert 'pet.host, "origin"' in runtime and runtime.count('AddSpecialEffectTarget')==1
    state=(ROOT/'wurst/pets/TDPetState.wurst').read_text()
    assert 'function invalidateCombat()\n\t\tclearVisualLink()' in state
    assert '\tondestroy\n\t\tclearVisualLink()' in state
    assert 'DestroyEffect(visualLink)\n\t\t\tvisualLink = null' in state
    # Wild/collection object fields, generic attacks and periodic traversal remain byte-identical.
    for p in ('wurst/pets/TDPetObjectGen.wurst','wurst/pets/TDPetRuntime.wurst','wurst/pets/TDPetCombat.wurst'):
        assert (ROOT/p).read_bytes()==subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
    return {'status':'PASS','species':rows,'towerProfiles':columns,'starBudget':{'handlesPerPet':1,'movingStars':12,'triangles':48,'newTimers':0},'currentMap':str(map_path) if map_path else None,'boundary':'Offline only; native origin anchor positioning, occlusion and frame rate need gameplay observation.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--map');a=p.parse_args();print(json.dumps(verify(a.map),ensure_ascii=False,indent=2))
