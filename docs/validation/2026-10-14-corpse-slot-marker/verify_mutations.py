import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_third_batch import *
s=Mpq((ROOT/'ExampleMap.w3x').read_bytes()).extract('war3map.j').decode()
results=[]
for label,name,old,new,check,reason in [
 ('revival_guard','tdBossCorpseCanRemove','and ( not alive)','and true',boss_checks,'Corpse guard failed revived'),
 ('identity_guard','tdBossCorpseCanRemove','originalIdentity == currentIdentity','true',boss_checks,'Corpse guard failed identity_changed'),
 ('viewer_guard','tdPetWildMarkerShouldShow','lane_3 == viewer','true',marker_checks,'Marker visibility other_viewer')]:
 m=jass_function(s,name);body=m.group(1);require(old in body,'Mutation root missing '+label)
 mutated=s[:m.start(1)]+body.replace(old,new,1)+s[m.end(1):]
 try:check(mutated)
 except ValueError as e:
  require(str(e)==reason,'Mutation unrelated failure '+label+': '+str(e));results.append({'mutation':label,'rejected':reason})
 else:raise ValueError('Mutation survived '+label)
Path(__file__).with_name('mutation-report.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
