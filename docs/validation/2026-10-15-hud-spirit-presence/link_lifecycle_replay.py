import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'tools')
from VerifyPetDisplayReplay import DisplayRuntime
from GenerateTowerTerrainMask import Mpq
raw=Path('ExampleMap.w3x').read_bytes();r=DisplayRuntime(Mpq(raw).extract('war3map.j').decode())
host=r.tower(7000);pet=r.record(host=host)
link=r.field('visualLink',pet)
assert link in r.visual_handles and r.visual_handles[link][1:]==(host,'origin')
r.invoke('tdPetDisplayInitialize',pet,0,r.now)
assert r.field('visualLink',pet)==link
r.invoke('TDPet_invalidateCombat',pet)
assert r.field('visualLink',pet) is None and link not in r.visual_handles
r.invoke('tdPetDisplayTick',pet,0,r.now)
second=r.field('visualLink',pet);assert second in r.visual_handles and second!=link
other=r.tower(7001);assert r.invoke('tdPetDeploy',pet,other)
third=r.field('visualLink',pet);assert second not in r.visual_handles and third in r.visual_handles
assert r.visual_handles[third][1:]==(other,'origin')
r.invoke('TDPet_recall',pet);assert third not in r.visual_handles and r.field('visualLink',pet) is None
r.invoke('TDPet_recall',pet)
assert r.invoke('tdPetDeploy',pet,host)
final=r.field('visualLink',pet);assert final in r.visual_handles
r.invoke('destroyTDPet',pet)
assert final not in r.visual_handles
print(json.dumps({'status':'PASS','map_sha256':hashlib.sha256(raw).hexdigest(),'cases':['deploy_host_origin','initialize_idempotent','invalidate_releases','tick_recreates','rebind_releases_old_and_attaches_new','recall_releases','repeated_recall_safe','destructor_releases'],'boundary':'Actual packed JASS; native effects modeled with strict unknown/double destroy rejection. No Warcraft render test.'},indent=2))
