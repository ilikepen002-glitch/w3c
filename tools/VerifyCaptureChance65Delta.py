"""Read-only actual-map delta gate. Usage: ROOT BASE_COMMIT_OR_MAP_PATH."""
from pathlib import Path
import sys, subprocess, hashlib, json, re
root=Path(sys.argv[1]); base=sys.argv[2]
sys.path.insert(0,str(root/'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifyTrialReplay import verify_current_capture
from VerifyDamageRankingJass import functions
from VerifyCaptureRemovalArtifact import canonical_packaged_function
from VerifyPetUIArtifact import _integer_expression
oldbytes=Path(base).read_bytes() if Path(base).is_file() else subprocess.check_output(['git','show',base+':ExampleMap.w3x'],cwd=root)
newbytes=(root/'ExampleMap.w3x').read_bytes()
a,b=Mpq(oldbytes),Mpq(newbytes)
# All imported geometry/textures/sounds and unit/item gameplay fields must remain exact.
assert a.extract('war3map.imp')==b.extract('war3map.imp')
for name in ('war3map.w3u','war3map.w3t','war3map.w3b','war3map.w3d','war3map.w3q'):
 if a.has(name) or b.has(name): assert a.extract(name)==b.extract(name), name
imports=a.extract('(listfile)').decode(errors='replace').splitlines()
compared=0
for name in imports:
 if name.lower().endswith(('.mdx','.blp','.wav','.mp3','.tga')):
  assert a.extract(name)==b.extract(name),name
  compared+=1
x,y=[ability_objects(m.extract('war3map.w3a')) for m in (a,b)]
assert set(x)==set(y)
changed=[]
for code in x:
 assert x[code][0]==y[code][0]
 old,new=x[code][1],y[code][1]
 assert set(old)==set(new)
 for key in old:
  if old[key]!=new[key]:
   assert code=='Pcap' and key[0]=='aub1',(code,key)
   ov,nv=old[key],new[key]
   assert ov[0]==nv[0]==3
   assert '成功率60%' in ov[1] and nv[1]==ov[1].replace('成功率60%','成功率65%')
   changed.append([code,list(key)])
assert len(changed)==61, changed
oldscript,newscript=[m.extract('war3map.j').decode() for m in(a,b)]
oldbody=functions(oldscript)['tdPetHandleCapture'][0]
newbody=functions(newscript)['tdPetHandleCapture'][0]
assert oldbody.count('GetRandomInt(1, 100) > 60')==1
assert canonical_packaged_function(oldbody.replace('GetRandomInt(1, 100) > 60','GetRandomInt(1, 100) > 65'))==canonical_packaged_function(newbody),'Capture flow changed beyond threshold/debug source line'
capture=verify_current_capture(newscript)
condition=re.search(r'^\s*if (.+GetRandomInt\(1, 100\).+) then$',newbody,re.M)[1]
for guaranteed in (False,True):
 for roll in range(1,101):
  calls=[]
  def rng(low,high):calls.append((low,high));return roll
  fail=_integer_expression(condition,{'guaranteed':guaranteed},{'GetRandomInt':rng})
  assert fail==(not guaranteed and roll>65)
  assert calls==([] if guaranteed else [(1,100)])
print(json.dumps({'base':base,'map_sha256':hashlib.sha256(newbytes).hexdigest(),'map_bytes':len(newbytes),'capture':capture,'actual_rng_cases':200,'boundaries':{'1':'success','65':'success','66':'failure','100':'failure'},'changed_capture_tooltip_levels':len(changed),'all_unit_item_other_ability_numeric_fields_identical':True,'preserved_asset_members':compared,'compiled_capture_only_threshold_changed':True},ensure_ascii=False,indent=2))
