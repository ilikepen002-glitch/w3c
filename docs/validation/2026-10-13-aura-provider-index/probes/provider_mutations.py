import sys,re,json
from pathlib import Path
sys.path.insert(0,'/tmp')
from provider_entry_checks import *
from VerifyDamageRankingJass import functions

def edit(s,fn,old,new):
 m=functions(s)[fn];b=m.group(0);require(b.count(old)==1,'Mutation selector not exact: '+fn);return s[:m.start()]+b.replace(old,new)+s[m.end():]
def source_case(s,kind):
 r=setup(s)
 if kind=='native':
  r.units[101]['type']=rawcode('uA15');r.invoke('tdRefreshTowerEquipmentBonuses',101,None);require(inside(r),'Native form missing')
 elif kind=='working':
  event(r,'tdHandleTowerUpgradeStarted');r.invoke('tdRefreshTowerEquipmentBonuses',101,None);require(inside(r),'Working source lost')
 elif kind=='exclude':
  add(r,8001,'iW10');event(r,'tdHandleTowerInventoryChanged',h=8001);event(r,'tdHandleTowerItemDropped',h=8001);require(not inside(r),'Occupied drop handle retained')
 elif kind=='slot':
  add(r,8001,'iW10',slot=2);r.invoke('tdRefreshTowerEquipmentBonuses',101,None);require(inside(r),'Third aura slot missing')
 elif kind=='detach':
  add(r,8001,'iW10');r.invoke('tdRefreshTowerEquipmentBonuses',101,None);rec=r.invoke('tdAuraTargetFor',101);r.invoke('tdAuraDetachRecord',rec);require(rec not in r.lists[r.globals['TDAuraState_tdAuraProviders']],'Detached source retained')
 elif kind=='last':
  add(r,8001,'iW10');r.invoke('tdRefreshTowerEquipmentBonuses',101,None);r.invoke('tdAuraRegisterTarget',1000,False);refresh(r,1000);require(r.units[1000]['speed']<260.,'Missing initial frost fixture')
  r.units[101]['inventory']={};r.invoke('tdRefreshTowerEquipmentBonuses',101,None);refresh(r,1000);require(r.units[1000]['speed']==260.,'Last source did not Apply')
 elif kind=='owner':
  add(r,8001,'iW10');r.invoke('tdRefreshTowerEquipmentBonuses',101,None);r.invoke('tdAuraRegisterTarget',1000,False);refresh(r,1000);r.units[101]['owner']=1;refresh(r,1000);require(r.units[1000]['speed']==260.,'Old owner aura remained')
 elif kind=='carrier':
  add(r,8001,'iW10');r.invoke('tdRefreshTowerEquipmentBonuses',101,None);r.invoke('tdAuraRegisterTarget',1000,False);refresh(r,1000)
  rec=r.invoke('tdAuraTargetFor',1000);carrier=r.invoke('tdAuraRankCarrier',7,1);require(carrier in r.units[1000]['abilities'],'Carrier fixture missing');del r.units[1000]['abilities'][carrier];refresh(r,1000);require(carrier in r.units[1000]['abilities'],'Receiver carrier not repaired')

class Interrupted(EntryAura):
 def __init__(self,s):self.fail_source=False;super().__init__(s)
 def native(self,n,a):
  if n=='tdAuraOfferSource' and self.fail_source and a[1]==102:raise ValueError('injected source interruption')
  if n=='ForForce':
   try:self.invoke(a[1])
   except ValueError as e:
    if str(e)!='injected source interruption':raise
   return True,None
  return super().native(n,a)
def partial(s,mutation=None):
 r=Interrupted(s);r.initialize_match();r.invoke('init_Execute');r.invoke('init_TDActiveCooldownRuntime')
 template=dict(r.units[101])
 for u in (101,102,1000):
  r.units[u]={**template,'type':rawcode('uA11' if u<1000 else 'uE19'),'owner':0 if u<1000 else 4,'userdata':0 if u<1000 else 2500,'x':0.,'y':0.,'abilities':{},'inventory':{},'alive':True,'speed':260.,'defaultSpeed':260.}
  r.invoke('tdAuraRegisterTarget',u,u<1000)
 for u,item in [(101,'iW10'),(102,'iP10')]:
  r.inventory_items[u+8000]=rawcode(item);r.units[u]['inventory']={0:u+8000};r.invoke('tdRefreshTowerEquipmentBonuses',u,None)
 refresh(r,1000);old=r.invoke('tdAuraTargetFor',1000);oldaggregate=r.globals['TDAuraTarget_effective'][old];before=r.invoke('tdAuraPower',1000,7)
 if mutation is not None:r.functions['run_try_TDAuraRuntime']=Interrupted(mutation).functions['run_try_TDAuraRuntime']
 r.fail_source=True;r.executed_steps=0;r.invoke('tdAuraRefresh',old)
 require(r.notices,'Interrupted scan did not report its retained state')
 require(r.globals['TDAuraTarget_effective'][old]==oldaggregate and r.invoke('tdAuraPower',1000,7)==before,'Partial aggregate published')

def run(s):
 cases=[]
 def addcase(name,fn,old,new,gate,expected):
  gate(s)
  broken=edit(s,fn,old,new)
  try:gate(broken)
  except ValueError as e:require(str(e)==expected,'Unrelated mutation failure '+name+': '+str(e));cases.append({'mutation':name,'rejected_by':str(e)})
  else:raise ValueError('Mutation survived '+name)
 addcase('native_candidate','tdTowerAuraProviderInput','if level >= 5 then','if false then',lambda x:source_case(x,'native'),'Native form missing')
 addcase('working_guard','tdTowerAuraProviderInput','if working then','if false then',lambda x:source_case(x,'working'),'Working source lost')
 addcase('drop_excluded_handle','tdTowerEquipmentItemId','itm == excludedItem or ','',lambda x:source_case(x,'exclude'),'Occupied drop handle retained')
 body=functions(s)['tdRefreshTowerEquipmentBonuses'].group(0)
 target=re.search(r'tdTowerEquipmentItemId\([^\n]+?, 2, excludedItem, [^\n]+?\)',body)[0]
 addcase('third_item_slot','tdRefreshTowerEquipmentBonuses',target,target.replace(', 2, excludedItem,',', 5, excludedItem,'),lambda x:source_case(x,'slot'),'Third aura slot missing')
 body=functions(s)['tdAuraDetachRecord'].group(0);line=next(l for l in body.splitlines(True) if 'call tdAuraSetProviderRecord' in l)
 addcase('detach_cleanup','tdAuraDetachRecord',line,'',lambda x:source_case(x,'detach'),'Detached source retained')
 body=functions(s)['run_try_TDAuraRuntime'].group(0);line=next(l for l in body.splitlines(True) if 'call tdAuraApply' in l)
 addcase('last_source_apply','run_try_TDAuraRuntime',line,'\tif not dispatch_LinkedList_LinkedList_isEmpty(TDAuraState_tdAuraProviders) then\n'+line+'\tendif\n',lambda x:source_case(x,'last'),'Last source did not Apply')
 body=functions(s)['tdAuraOfferSource'].group(0);owner=re.search(r'GetPlayerId\(GetOwningPlayer\([^\)]+\)\)',body)[0]
 addcase('live_owner_filter','tdAuraOfferSource',owner,'0',lambda x:source_case(x,'owner'),'Old owner aura remained')
 body=functions(s)['tdAuraSyncDisplayedRank'].group(0);needle=re.search(r'\( not tdAuraCarrierRepairNeeded\([^\n]+?\)\)',body)[0]
 addcase('carrier_repair','tdAuraSyncDisplayedRank',needle,'rank == oldRank',lambda x:source_case(x,'carrier'),'Receiver carrier not repaired')
 partial(s)
 m=functions(s)['run_try_TDAuraRuntime'];b=m.group(0);oldset=next(l for l in b.splitlines(True) if 'set TDAuraTarget_effective' in l);b=b.replace(oldset,'');at=next(l for l in b.splitlines(True) if 'set iterator = LinkedList_iterator' in l);b=b.replace(at,oldset+at);broken=s[:m.start()]+b+s[m.end():]
 try:partial(s,broken)
 except ValueError as e:require(str(e)=='Partial aggregate published','Unrelated partial-publish failure: '+str(e));cases.append({'mutation':'partial_aggregate_publication','rejected_by':str(e)})
 else:raise ValueError('Partial publication mutation survived')
 return cases
if __name__=='__main__':
 p=ROOT/'ExampleMap.w3x';s=Mpq(p.read_bytes()).extract('war3map.j').decode();print(json.dumps({'map_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'semantic_mutations':run(s)},indent=2))
