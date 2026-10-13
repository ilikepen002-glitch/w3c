from pathlib import Path
import sys,hashlib,json,subprocess
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyPureBossArtifact import PureBossJassRuntime
from VerifyDamageRankingJass import functions
from VerifyCaptureRemovalArtifact import canonical_packaged_function
from VerifyTowerPlacementArtifact import unit_objects
class TerrainRuntime(PureBossJassRuntime):
 def native(self,name,args):
  if name=='SubString':return True,args[0][args[1]:args[2]]
  if name=='tdIsLanePlayer':return False,None
  return super().native(name,args)
new=(root/'ExampleMap.w3x').read_bytes(); old=subprocess.check_output(['git','show','e1c6d06ee9dbd054d65c5a055e63f767a0ed9bfe:ExampleMap.w3x'],cwd=root)
a,b=Mpq(old),Mpq(new);script=b.extract('war3map.j').decode();r=TerrainRuntime(script)
for name in ('init_TDTowerPlacementRules','init_TDTowerTerrainMask','init_TDConfig'):
 if name in r.functions:r.invoke(name)
assert r.globals['TDTowerTerrainMask_TD_TERRAIN_MAX_HEIGHT_DELTA']==64
assert r.globals['TDTowerPlacementRules_TD_TOWER_FOOTPRINT_SIZE']==192
assert r.globals['TDTowerPlacementRules_TD_TOWER_CLIFF_MARGIN']==32
for x in (-2432,-2240,-2048,-1856,-1664):
 for y in (1792,2304):
  assert r.invoke('tdBuildPlotHasValidTerrain',x,y) and r.invoke('tdBuildPlotIsFlat',x,y)
assert r.invoke('tdBuildPlotHasValidTerrain',-2048,896) and r.invoke('tdBuildPlotIsFlat',-2048,896)
assert r.invoke('tdBuildPlotHasValidTerrain',-2244,768) and not r.invoke('tdBuildPlotIsFlat',-2244,768)
for x,y in [(-2048,640),(-2560,896),(-2000,2672),(-1168,2048),(-3840,3840),(0,-192),(-5000,2048)]:
 assert not r.invoke('tdBuildPlotHasValidTerrain',x,y),(x,y)
assert r.invoke('tdIsInLaneBuildZone',0,-2048,896)
for lane in (1,2,3):assert not r.invoke('tdIsInLaneBuildZone',lane,-2048,896)
assert r.invoke('tdBuildAreaOwner',-16,-192)==-1
assert r.invoke('tdTowerFootprintsOverlap',-2048,896,-2048+191,896)
assert not r.invoke('tdTowerFootprintsOverlap',-2048,896,-2048+192,896)
for name in ('war3map.w3u','war3map.w3t','war3map.w3a','war3map.w3b','war3map.w3d','war3map.w3q','war3map.imp','war3map.w3e'):
 if a.has(name) or b.has(name):assert a.extract(name)==b.extract(name),name
assets=0
for name in a.extract('(listfile)').decode().splitlines():
 if name.lower().endswith(('.mdx','.blp','.wav','.mp3','.tga')):assert a.extract(name)==b.extract(name),name;assets+=1
x,y=functions(a.extract('war3map.j').decode()),functions(script)
assert canonical_packaged_function(x['tdPetHandleCapture'][0])==canonical_packaged_function(y['tdPetHandleCapture'][0])
objects=unit_objects(b.extract('war3map.w3u'))
for code in ('uA11','uO11','uH11','uD11','uG11'):assert objects[code]['ugol']==500
for choice in range(1,6):assert r.invoke('tdTowerCost',choice)==500
oldp,newp=a.extract('war3map.wpm'),b.extract('war3map.wpm');changed=0
for before,after in zip(oldp[16:],newp[16:]):
 assert before&~8==after&~8
 if before!=after:assert before==after|8;changed+=1
assert changed==2340
print(json.dumps({'map_sha256':hashlib.sha256(new).hexdigest(),'base_tower_prices_actual_object_and_jass':500,'actual_jass_terrain64_boundaries':'PASS','approved_ten_centers':'PASS','natural_relief_54_75':'PASS','excessive_relief_70_75_rejected':'PASS','road_cliff_exit_other_quadrants_overlap_rejected':'PASS','cleared_only_derived_unbuildable_cells':changed,'vs_65_baseline_objects_identical':True,'capture_body_identical_to_65':True,'preserved_vfx_model_texture_audio_members':assets},indent=2))
