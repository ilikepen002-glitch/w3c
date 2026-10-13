import sys,json,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path('/workspace/scratch/2106c0ab1fac/aura-provider-index-20261013');sys.path.insert(0,str(ROOT/'tools'))
from VerifyAuraPerfArtifact import CountedAuraRuntime,refresh,state
from VerifyTowerUpgradeArtifact import expected_towers,EVOLUTION_REPLACEMENTS,rawcode
from VerifyTowerPlacementArtifact import unit_objects
from VerifyEquipmentAbilityArtifact import require
from ReadEquipmentCatalog import catalog
from GenerateTowerTerrainMask import Mpq
from VerifyTowerTargetPriorityArtifact import jass_boolean_expression
class ActualAura(CountedAuraRuntime):
 def __init__(self,script):
  self.native_hashtables={}
  super().__init__(script)
 def expression(self,text,scope):
  return super().expression(jass_boolean_expression(text),scope)
 def native(self,name,args):
  if name=='InitHashtable':
   self.table_serial+=1;self.native_hashtables[self.table_serial]={};return True,self.table_serial
  if name in ('LoadInteger','SaveInteger','HaveSavedInteger','FlushChildHashtable'):
   require(args[0] in self.native_hashtables,'Unknown actual native hashtable')
   table=self.native_hashtables[args[0]];key=tuple(args[1:3])
   if name=='LoadInteger':return True,table.get(key,0)
   if name=='SaveInteger':table[key]=args[3];return True,True
   if name=='HaveSavedInteger':return True,key in table
   for k in list(table):
    if k[0]==args[1]:del table[k]
   return True,None
  if name in ('tdTowerChoiceForUnitTypeId','tdTowerLevelForUnitTypeId','tdTowerBranchForUnitTypeId','tdTowerIsEvolved'):return False,None
  return super().native(name,args)

def make(script,large=False):
 r=ActualAura(script);r.initialize_match();r.invoke('init_Execute');r.invoke('init_TDActiveCooldownRuntime');r.invoke('init_TDTowerBloodlustAutocast')
 template=dict(r.units[101])
 towers=list(range(101,141)) if large else [101,102,103]
 for idx,t in enumerate(towers):
  lane=idx//10 if large else (1 if t==103 else 0)
  r.units[t]={**template,'type':rawcode('uA11'),'owner':lane,'userdata':lane*10000,'x':lane*2000.,'y':0.,'abilities':{},'inventory':{},'alive':True,'speed':260.,'defaultSpeed':260.}
  r.invoke('tdAuraRegisterTarget',t,True)
  r.invoke('tdRefreshTowerEquipmentBonuses',t,None)
 enemies=[1000+i for i in range(8)] if large else [1000,1001]
 for i,t in enumerate(enemies):
  lane=i//2 if large else i
  r.units[t]={**template,'type':rawcode('uE19'),'owner':4,'userdata':lane*10000+2500,'x':lane*2000.+10.,'y':0.,'abilities':{},'inventory':{},'alive':True,'speed':260.,'defaultSpeed':260.}
  r.invoke('tdAuraRegisterTarget',t,False)
 return r

def members(r):
 key='TDAuraState_tdAuraProviders'
 return None if key not in r.globals else len(r.lists[r.globals[key]])

def set_source(r,unit,code,abilities,items=()):
 r.units[unit]['type']=rawcode(code);r.units[unit]['abilities']={rawcode(a):1 for a in abilities}
 r.units[unit]['inventory']={}
 for slot,item in items:
  h=90000+unit*10+slot;r.inventory_items[h]=rawcode(item);r.units[unit]['inventory'][slot]=h
 r.executed_steps=0;r.invoke('tdRefreshTowerEquipmentBonuses',unit,None)

def result(r):
 return {str(t):{**state(r,t),'range':r.units[t].get('acquireRange')} for t in [102,103,1000,1001]}

def project(r):
 for t in [102,103,1000,1001]:refresh(r,t)
 require(not r.notices,'Production aura refresh failed')
 return result(r)

def cost(s,objects,n,item_sources=False):
 r=make(s,True)
 for i in range(n):
  if item_sources:set_source(r,101+i,'uA11',objects['uA11']['uabi'].split(','),[(0,'iW01'),(1,'iW02'),(2,'iW10')])
  else:set_source(r,101+i,'uA15',objects['uA15']['uabi'].split(','))
 for t in list(range(101,141))+list(range(1000,1008)):refresh(r,t)
 require(members(r) in (None,n),'Provider count incorrect after actual Inventory warmup')
 before=Counter(r.calls);expr=r.expressions;r.executed_steps=0
 r.invoke('call_doPeriodically_TDAuraRuntime',0,0)
 delta=Counter(r.calls)-before
 keys=['tdAuraOfferSource','tdRefreshTowerEquipmentBonuses','tdAuraSetProviderCandidate','tdAuraSetProviderRecord','UnitItemInSlot','unit_getAbilityLevel','GetUnitTypeId','GetOwningPlayer','tdItemAuraKind','SetUnitMoveSpeed','SetUnitAcquireRange','SetUnitAbilityLevel','CreateGroup','CreateUnit','IssueTargetOrderById','GetRandomInt','GetRandomReal','doPeriodically','doAfter']
 return {'sources':n,'source_kind':'item' if item_sources else 'native','actual_members':members(r),'calls':sum(delta.values()),'expressions':r.expressions-expr,'counts':{k:delta[k] for k in keys},'state':[state(r,t) for t in [101,105,111,116,1000,1002]]}

def matrix(s,objects):
 r=make(s);out=[]
 # All 35 actual object ability sets, then their actual evolved replacements.
 for code in expected_towers():
  modes=[('normal',objects[code]['uabi'].split(','))]
  if code in EVOLUTION_REPLACEMENTS:
   rep=EVOLUTION_REPLACEMENTS[code];modes.append(('evolved',[rep.get(a,a) for a in modes[0][1]]))
  for mode,abilities in modes:
   set_source(r,101,code,abilities)
   choice=r.invoke('tdTowerChoiceForUnitTypeId',rawcode(code));level=r.invoke('tdTowerLevelForUnitTypeId',rawcode(code))
   expected=level>=5 and choice in (1,3,4)
   require(members(r) in (None,int(expected)),'Actual form membership incorrect '+code+'/'+mode)
   out.append({'label':code+'/'+mode,'state':project(r)})
 # Cooldown recipient is a legal native-active Orc form, not a forged low archer.
 set_source(r,102,'uO6A',objects['uO6A']['uabi'].split(','))
 require(r.invoke('tdHasNativeActiveCooldown',102),'Actual cooldown recipient lacks native active')
 for item in catalog(ROOT):
  if item.aura=='NONE':continue
  for slot in range(3):
   set_source(r,101,'uA11',objects['uA11']['uabi'].split(','),[(slot,item.rawcode)])
   require(members(r) in (None,1),'Aura item missing provider')
   projected=project(r)
   if item.aura=='COOLDOWN':
    require(projected['102']['auras'][4][0]==item.quality and projected['102']['auras'][4][1]>0,'Cooldown aura matrix was vacuous')
   out.append({'label':item.rawcode+'/slot'+str(slot),'state':projected})
 return out

def transitions(s,objects):
 r=make(s);out=[]
 def record(label):out.append({'label':label,'state':project(r)})
 record('source_zero')
 set_source(r,101,'uA11',objects['uA11']['uabi'].split(','),[(0,'iW10')]);record('frost_source_added')
 r.units[101]['x']=10000.;record('source_outside');r.units[101]['x']=0.;record('source_back')
 r.units[101]['owner']=1;r.units[101]['x']=2000.;record('owner_moved_live')
 r.units[101]['owner']=0;r.units[101]['x']=0.;record('owner_back')
 r.units[1000]['mechanical']=True;record('mechanical_enemy');r.units[1000]['mechanical']=False
 set_source(r,101,'uA11',objects['uA11']['uabi'].split(','));record('last_source_removed')
 require(members(r) in (None,0),'Source 1-to-0 membership retained')
 set_source(r,101,'uA15',objects['uA15']['uabi'].split(','));record('native_provider')
 r.units[101]['abilities'].pop(rawcode('A101'),None);record('native_ability_removed')
 require(members(r) in (None,1),'Conservative provider incorrectly removed')
 r.units[101]['abilities'][rawcode('A101')]=1;record('native_ability_readded')
 carrier=r.invoke('tdAuraRankCarrier',1,1);r.units[102]['abilities'].pop(carrier,None);record('receiver_carrier_repaired')
 require(carrier in r.units[102]['abilities'],'Missing receiver carrier unrepaired')
 # Remove and failed-add retry while source remains unchanged.
 r.units[102]['abilities'].pop(carrier,None);r.reject_carrier=carrier;record('receiver_add_failed')
 r.reject_carrier=None;record('receiver_add_retry');require(carrier in r.units[102]['abilities'],'Carrier add retry failed')
 r.units[101]['alive']=False;record('source_dead_live_reject')
 r.event_target=101;r.invoke('tdAuraOnDeath');require(members(r) in (None,0),'Death cleanup retained candidate')
 r.units[101]['alive']=True;r.units[101]['type']=rawcode('uA11');r.units[101]['abilities']={};r.invoke('tdRefreshTowerEquipmentBonuses',101,None)
 record('recycled_empty_source');require(members(r) in (None,0),'Recycled record inherited candidate')
 # Equal-rank/power source permutation and strong-to-weak fallback.
 for t,item in ((101,'iP10'),(102,'iW10')):set_source(r,t,'uA11',[],[(0,item)])
 record('strong_and_weak')
 r.invoke('tdAuraSetProviderCandidate',101,False) if 'tdAuraSetProviderCandidate' in r.functions else None
 r.invoke('tdRefreshTowerEquipmentBonuses',101,None);record('strong_reappend_same_outputs')
 set_source(r,101,'uA11',[],[]);record('weak_fallback')
 set_source(r,102,'uA11',[],[]);record('all_removed')
 return out

def main():
 paths=list(map(Path,sys.argv[1:3]));maps=[Mpq(p.read_bytes()) for p in paths];scripts=[m.extract('war3map.j').decode() for m in maps];objects=[unit_objects(m.extract('war3map.w3u')) for m in maps]
 report={'hashes':[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]}
 matrices=[matrix(s,o) for s,o in zip(scripts,objects)];require(matrices[0]==matrices[1],'35-form/item matrix numeric mismatch');report['matrix_cases']=len(matrices[0]);report['matrix']=matrices[1]
 flows=[transitions(s,o) for s,o in zip(scripts,objects)];require(flows[0]==flows[1],'Transition numeric mismatch');report['transitions']=flows[1]
 costs=[[cost(s,o,n) for n in [0,4,10,40]] for s,o in zip(scripts,objects)]
 for a,b in zip(*costs):
  require(a['state']==b['state'],'Cost scenario numeric mismatch')
  require(a['counts']['tdAuraOfferSource']==640,'Baseline did not traverse 40 sources')
  require(b['counts']['tdAuraOfferSource']==16*b['sources'],'Candidate did not traverse real providers')
 report['costs']=costs;report['status']='PASS';report['boundary']='Packed JASS, true catalog helpers, controlled natives. No FPS/CPU claim. Inventory creates membership; no fixture source-list filtering.'
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
