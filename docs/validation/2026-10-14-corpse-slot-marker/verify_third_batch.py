import sys,json,hashlib,re,struct,subprocess,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyWildLifetimeArtifact import WildRuntime,verify_wild,verify_waves
from VerifyPetUIArtifact import jass_function
from VerifyEquipmentAbilityArtifact import require
from VerifyGlobalRankingsArtifact import members

class Runtime(WildRuntime):
 def __init__(self,script):
  self.viewer=0;self.visibility=[]
  super().__init__(script)
 def native(self,name,args):
  if name=='GetLocalPlayer':return True,self.viewer
  if name=='IsUnitHidden':return True,self.units.get(args[0],{}).get('hidden',False)
  if name=='IsUnitVisible':return True,self.units.get(args[0],{}).get('visible',True)
  if name=='SetTextTagVisibility':
   require(args[0] in self.tags,'Visibility of unowned tag');self.visibility.append(tuple(args));return True,None
  return super().native(name,args)

def marker_checks(s):
 reports=[]
 for state,expected in [('visible',True),('other_viewer',False),('hidden',False),('fog',False),('dead',False),('removed',False)]:
  r=Runtime(s);rec,u,tag=r.wild();r.viewer=1 if state=='other_viewer' else 0
  if state=='hidden':r.units[u]['hidden']=True
  if state=='fog':r.units[u]['visible']=False
  if state=='dead':r.units[u]['alive']=False
  if state=='removed':r.units[u]['type']=0
  before=(copy.deepcopy(r.units),copy.deepcopy(r.player_resources),copy.deepcopy(r.tables),copy.deepcopy(r.lists),len(r.random_trace))
  r.invoke('tdPetWildSyncMarkerVisibility',rec)
  after=(r.units,r.player_resources,r.tables,r.lists,len(r.random_trace))
  require(r.visibility[-1]==(tag,expected),'Marker visibility '+state)
  require(before==after,'Local marker changed gameplay '+state)
  r.invoke('TDPetWildRecord_clearMarker',rec)
  r.invoke('TDPetWildRecord_clearMarker',rec)
  require(r.tags_destroyed==[tag] and r.globals['TDPetWildRecord_marker'][rec] is None,'Marker clearing not idempotent')
  reports.append(state)
 r=Runtime(s);rec,u,tag=r.wild();r.units[u]['type']=0;r.cleanup()
 require(r.tags_destroyed==[tag] and rec not in r.lists[r.globals['TDPetWild_tdPetWildRecords']],'Removed unit retained marker/record')
 # Actual destroy dispatch must release a marker without prior terminal transition.
 r=Runtime(s);rec,u,tag=r.wild()
 destroy=next(n for n in r.functions if n.startswith('dispatch_') and n.endswith('destroyTDPetWildRecord'))
 r.invoke(destroy,rec)
 require(r.tags_destroyed==[tag],'Direct polymorphic destruction leaked marker')
 body=jass_function(s,'tdPetWildSyncMarkerVisibility').group(1)
 require('SetTextTagVisibility(' in body and not re.search(r'call (?!SetTextTagVisibility\b)\w+\(',body),'Unexpected local effect in marker helper')
 return {'visibility_cases':reports,'local_gameplay_unchanged':True,'idempotent_clear':True,'removed_unit_cleanup':True,'direct_destroy':True}

def boss_checks(s):
 reports=[]
 for wave in (8,16,24,32):
  for state in ('dead','revived','removed','identity_changed','type_changed'):
   r=Runtime(s);u=102;kind=r.invoke('tdWaveSpecialUnitId',wave)
   r.units[u].update(type=kind,alive=False,userdata=wave*100,owner=4)
   r.tables[r.globals['TDSpawn_tdEnemyMatchEpochs']][u]=r.invoke('tdFlowEpoch')
   old=list(r.scheduled);r.invoke('tdScheduleBossCorpseCleanup',u)
   added=[item for item in r.scheduled if item not in old]
   require(len(added)==1 and added[0][0]==3.,'Missing exact 3s callback')
   cb=added[0][1]
   require(u not in r.removals,'Premature removal')
   if state=='revived':r.units[u]['alive']=True
   if state=='removed':r.units[u]['type']=0
   if state=='identity_changed':r.units[u]['userdata']+=100
   if state=='type_changed':r.units[u]['type']=r.invoke('tdWaveUnitId',1)
   before=(dict(r.player_resources),r.score(),list(r.credit_grants))
   r.now+=3.;r.run_timer(cb)
   require((u in r.removals)==(state=='dead'),'Corpse guard failed '+state)
   require(before==(r.player_resources,r.score(),r.credit_grants),'Cleanup awarded settlement')
   require(r.globals['CallbackSingle_typeId'][cb]==0,'Cleanup closure leaked')
   reports.append({'wave':wave,'state':state,'removed':u in r.removals})
 # Execute real Boss death/reward path, then repeat event: no duplicate result or reward.
 r=Runtime(s)
 for lane in range(4):r.invoke('tdSetResolvedWave',lane,7)
 r.invoke('tdSetGlobalWave',7);r.invoke('tdStartGlobalWave',8)
 method=next(n for n in r.functions if n.startswith('call_doPeriodically_TDGame') and 'tdBossPreparationReady(' in jass_function(s,n).group(1))
 owner=r.callback_allocations[method.replace('call_','alloc_CallbackPeriodic_',1)][1]
 cb=next(cb for delay,cb in r.periodics if delay==.20 and r.globals['CallbackPeriodic_typeId'][cb]==owner)
 r.invoke(method,cb,cb);boss=r.globals['TDGame_tdBossUnits'][0];r.units[boss]['alive']=False;r.event_target=boss
 r.invoke('tdHandleEnemyDeath');before=(dict(r.player_resources),r.score(),list(r.credit_grants),list(r.scheduled))
 r.invoke('tdHandleEnemyDeath');require(before==(r.player_resources,r.score(),r.credit_grants,r.scheduled),'Duplicate death duplicate reward/timer')
 cbs=[cb for delay,cb in r.scheduled if delay==3.]
 require(len(cbs)==1,'Real death did not create exactly one cleanup')
 r.run_timer(cbs[0]);require(r.removals.count(boss)==1,'Real death cleanup mismatch')
 require(before[:3]==(r.player_resources,r.score(),r.credit_grants),'Delayed cleanup duplicated reward')
 return {'guard_cases':reports,'real_death_duplicate_and_cleanup_no_rewards':True,'closure_released':True}

def main():
 data=(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'ExampleMap.w3x').read_bytes();a=Mpq(data);s=a.extract('war3map.j').decode('utf8')
 base=Mpq(subprocess.check_output(['git','-C',str(ROOT),'show','e599851c1e05cb062f8e9026d87da35de6f6aad5:ExampleMap.w3x']))
 before={x.casefold():x for x in members(base)};after={x.casefold():x for x in members(a)}
 require(set(before)==set(after),'Map member set changed')
 changed=[p for p in before if base.extract(before[p])!=a.extract(after[p])]
 require(set(changed)<= {'war3map.j','war3map.w3i','war3map.wts','(attributes)'},'Unexpected resource/object delta '+str(changed))
 report={'map_sha256':hashlib.sha256(data).hexdigest(),'jass_sha256':hashlib.sha256(s.encode()).hexdigest(),'changed_members':changed,'unchanged_members':len(before)-len(changed)}
 old=base.extract('war3map.w3i');new=a.extract('war3map.w3i');needle='黑潮怪物'.encode()
 require(needle in new and b'Enemy Slot' not in new,'Final w3i enemy slot mismatch')
 require('Enemy Slot' not in s and not re.search(r'call SetPlayerName\(Player\(4\), (?!"黑潮怪物")',s),'Final JASS overrides enemy slot name')
 from VerifyMapBrandingArtifact import normalized_info
 require(normalized_info(new)==normalized_info(old).replace(b'Enemy Slot',needle),'W3I changed beyond build stamp and exact enemy slot name')
 report['slot_name_exact']='黑潮怪物';report['marker']=marker_checks(s);report['boss']=boss_checks(s);report['legacy_wild']=verify_wild(s);report['legacy_waves']=verify_waves(s);report['status']='PASS'
 Path(__file__).with_name('third-batch-artifact-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
