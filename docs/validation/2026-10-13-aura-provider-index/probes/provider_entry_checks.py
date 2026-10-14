import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,'/workspace/scratch/2106c0ab1fac/aura-provider-independent-evidence')
from provider_compare import *
from VerifyTowerTargetPriorityArtifact import jass_boolean_expression
class EntryAura(ActualAura):
 def __init__(self,s):
  self.manip_unit=101;self.manip_item=None;self.item_positions={};self.force_gear_failure=False
  super().__init__(s)
  self.globals.update(PATHING_TYPE_WALKABILITY='walk',bj_MAX_PLAYER_SLOTS=16,PLAYER_STATE_RESOURCE_FOOD_CAP='foodCap',PLAYER_STATE_RESOURCE_FOOD_USED='foodUsed')
  for player in range(16):self.globals['Player_players'][player]=player
 def expression(self,text,scope):
  return super().expression(jass_boolean_expression(text),scope)
 def native(self,n,a):
  if n=='SetUnitInvulnerable':self.units[a[0]]['invulnerable']=a[1];return True,None
  if n=='GroupEnumUnitsOfPlayer':self.groups[a[0]]=[u for u,d in self.units.items() if d['owner']==a[1]];return True,None
  if n=='ForGroup':
   for u in self.groups[a[0]]:self.enum_unit=u;self.invoke(a[1])
   return True,None
  if n=='GetEnumUnit':return True,self.enum_unit
  if n=='IsTerrainPathable':return True,False
  if n=='IsItemOwned':return True,any(a[0] in d.get('inventory',{}).values() for d in self.units.values())
  if n=='StringLength':return True,len(a[0])
  if n=='SubString':return True,a[0][a[1]:a[2]]
  if n=='GetManipulatingUnit':return True,self.manip_unit
  if n=='GetManipulatedItem':return True,self.manip_item
  if n in ('GetConstructingStructure','GetConstructedStructure','GetCancelledStructure'):return True,self.event_target
  if n in ('GetItemX','GetItemY'):return True,self.item_positions.get(a[0],(0.,0.))[n=='GetItemY']
  if n=='SetItemPosition':self.item_positions[a[0]]=tuple(a[1:]);return True,None
  if n=='UnitRemoveItem':
   u,h=a[:2]
   old=self.manip_unit,self.manip_item;self.manip_unit=u;self.manip_item=h
   self.invoke('tdHandleTowerItemDropped')
   self.manip_unit,self.manip_item=old
   for slot,x in list(self.units[u]['inventory'].items()):
    if x==h:del self.units[u]['inventory'][slot]
   return True,None
  if n=='UnitAddItem':
   u,h=a[:2]
   if all(slot in self.units[u]['inventory'] for slot in range(3)):return True,False
   for v,d in list(self.units.items()):
    if h in d.get('inventory',{}).values():self.native('UnitRemoveItem',[v,h])
   for slot in range(3):
    if slot not in self.units[u]['inventory']:
     self.units[u]['inventory'][slot]=h
     old=self.manip_unit,self.manip_item;self.manip_unit=u;self.manip_item=h
     self.invoke('tdHandleTowerInventoryChanged');self.manip_unit,self.manip_item=old
     return True,True
   return True,False
  if n=='tdCombatVisualRefreshGear' and self.force_gear_failure:raise ValueError('injected gear failure')
  return super().native(n,a)
def setup(s):
 base=make(s);r=EntryAura(s);r.initialize_match();r.invoke('init_Execute');r.invoke('init_TDActiveCooldownRuntime');r.invoke('init_TDTowerRuntime')
 for t,d in base.units.items():r.units[t]=dict(d,abilities=dict(d.get('abilities',{})),inventory=dict(d.get('inventory',{})))
 for t in (101,102,103):r.invoke('tdRefreshTowerEquipmentBonuses',t,None)
 return r
def inside(r,u=101):return r.invoke('tdAuraTargetFor',u) in r.lists[r.globals['TDAuraState_tdAuraProviders']]
def event(r,fn,u=101,h=None):
 r.manip_unit=u;r.manip_item=h;r.event_target=u;r.executed_steps=0;r.invoke(fn)
def add(r,h,code,u=101,slot=0):r.inventory_items[h]=rawcode(code);r.units[u]['inventory'][slot]=h

def entries(s):
 r=setup(s);out=[]
 require(not inside(r),'Empty source unexpectedly retained')
 add(r,8001,'iW10');event(r,'tdHandleTowerInventoryChanged',h=8001);require(inside(r),'Native pickup did not register aura provider');out.append('pickup_0_to_1')
 event(r,'tdHandleTowerItemDropped',h=8001);require(not inside(r),'Drop occupied native slot did not exclude source');del r.units[101]['inventory'][0];out.append('drop_1_to_0_before_native_slot_clear')
 add(r,8002,'iW10');event(r,'tdHandleTowerInventoryChanged',h=8002)
 add(r,8003,'iW10',slot=1);event(r,'tdHandleTowerInventoryChanged',h=8003);require(inside(r) and 8003 not in r.units[101]['inventory'].values(),'Duplicate rejection lost valid source or kept duplicate');out.append('duplicate_rejection')
 r.inventory_items[8004]=rawcode('iP10');require(r.native('UnitAddItem',[102,8004])[1],'Script give failed');require(inside(r,102),'Script give did not add provider');out.append('script_give')
 require(r.native('UnitAddItem',[103,8004])[1],'Script transfer failed');require(inside(r,103) and not inside(r,102),'Transfer did not update old and new provider');out.append('script_transfer_drop_callback')
 # Native failure emits no successful pickup and preserves the existing holder.
 r.units[102]['inventory']={0:8006,1:8007,2:8008}
 for h in (8006,8007,8008):r.inventory_items[h]=rawcode('iW01')
 before=Counter(r.calls);require(not r.native('UnitAddItem',[102,8004])[1],'Full inventory accepted failed add')
 require((Counter(r.calls)-before)['tdHandleTowerInventoryChanged']==0 and 8004 in r.units[103]['inventory'].values(),'Failed add emitted pickup or stole source item');out.append('failed_native_add_no_pickup')
 # A non-aura tower is protected immediately on a real work-start, before type restoration.
 r.units[101]['inventory']={};r.units[101]['type']=rawcode('uA14');r.invoke('tdRefreshTowerEquipmentBonuses',101,None)
 require(not inside(r),'Nonprovider level4 was classified incorrectly')
 event(r,'tdHandleTowerUpgradeStarted');require(inside(r),'Upgrade work-start source not protected');out.append('upgrade_start_conservative')
 event(r,'tdHandleTowerUpgradeCancelled');stale=r.scheduled[-1][1]
 event(r,'tdHandleTowerUpgradeStarted');r.now+=.001;r.run_timer(stale);require(inside(r),'Stale cancel cleared current working source');out.append('stale_cancel_generation_ignored')
 event(r,'tdHandleTowerUpgradeCancelled');r.now+=.001;r.run_timer(r.scheduled[-1][1]);require(not inside(r),'Legal cancel did not narrow restored level4');out.append('cancel_narrows')
 event(r,'tdHandleTowerUpgradeStarted');r.units[101]['type']=rawcode('uA15');event(r,'tdHandleTowerUpgradeFinished');require(inside(r),'Upgrade level5 native form missing');out.append('upgrade4_to5_finish')
 # Failure after snapshot membership leaves a conservative complete source; no numeric aggregate is published.
 r.units[102]['inventory']={};r.invoke('tdRefreshTowerEquipmentBonuses',102,None);add(r,8005,'iW10',u=102)
 r.force_gear_failure=True
 try:r.invoke('tdRefreshTowerEquipmentBonuses',102,None)
 except ValueError as e:require(str(e)=='injected gear failure','Unrelated registration failure')
 else:raise ValueError('Failure injector missed actual gear call')
 require(inside(r,102),'Early membership publication lost provider after gear failure');r.force_gear_failure=False;r.invoke('tdRefreshTowerEquipmentBonuses',102,None);out.append('registration_before_failure')
 return out
if __name__=='__main__':
 p=ROOT/'ExampleMap.w3x';s=Mpq(p.read_bytes()).extract('war3map.j').decode();print(json.dumps({'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'entries':entries(s)},indent=2))
