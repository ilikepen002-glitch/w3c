"""Bounded execution of current actual Wurst craft bodies, not type/JASS proof.

Class allocation and planner/catalog are explicit fixtures; real capture,
backend.available, prepare/deliver/consume/publish/discard, watch and recovery
bodies execute. Warcraft items/units/callback order and placement API are models.
Unknown source syntax stays fail-closed through the existing source transpiler.
"""
from pathlib import Path
import re
import sys
from types import SimpleNamespace as NS

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests/python'))
from test_elemental_pet_runtime_source import compile_body
from ReadEquipmentCatalog import catalog
from VerifyTowerUpgradeArtifact import rawcode

class Map(dict):
    def has(self,key):return key in self
    def put(self,key,value):self[key]=value
    def remove(self,key):del self[key]
class List(list):
    def add(self,value):self.append(value)
    def size(self):return len(self)

BACKEND_FIELDS=('inputs','records','handles','farmer','caster','lane','origin','inventory',
                'output','outputId','outputKey','phase','staging','pileCounts','lastFailure','taskToken')
METHODS=('capture','available','clearOutput','releaseCommitOwner','prepareResult','sourceValid','sourcesValid',
         'inventoryOutputAccepted','cancelInventoryDelivery','deliverInventory','consumeThree',
         'publishResult','discardResult','onDestroy')

def destructor(text,classname,name):
    block=text.split('class '+classname,1)[1]
    lines=block.splitlines();start=next(i for i,l in enumerate(lines) if l=='\tondestroy')
    body=[]
    for line in lines[start+1:]:
        if line.strip() and not line.startswith('\t\t'):break
        body.append(line[1:])
    return 'function '+name+'()\n'+'\n'.join(body)+'\n'

class Backend:
    def __init__(self,fixture,farmer,inventory,lane):
        self.f=fixture
        self.values=dict(inputs=List(),records=Map(),handles=Map(),farmer=farmer,caster=farmer.owner,
            lane=lane,origin=NS(x=farmer.x,y=farmer.y),inventory=inventory,output=None,
            outputId=0,outputKey=0,phase=0,staging=None,pileCounts=[0]*5,lastFailure=0,taskToken=id(self))
        self.destroyed=False
    def __getattr__(self,name):
        if name in METHODS:return lambda *args:self.call(name,*args)
        if name in self.values:
            return self.f.n[name] if self.f.active_backend is self else self.values[name]
        raise AttributeError(name)
    def call(self,name,*args):
        n=self.f.n
        if self.f.active_backend is self:
            # Same-object reentry observes the real live fields, never the stale
            # saved snapshot from before the outer native-boundary call.
            return self.f.compiled[name](*args)
        old={k:n.get(k) for k in BACKEND_FIELDS};previous=self.f.active_backend
        n.update(self.values);self.f.active_backend=self
        try:return self.f.compiled[name](*args)
        finally:
            self.values.update({k:n[k] for k in BACKEND_FIELDS})
            n.update(old);self.f.active_backend=previous

class CraftSourceFixture:
    def __init__(self,count=3,lane=0,quality=1,inventory=True,*,mixed=False,roll=1,source_mutation=None):
        self.entries=catalog();self.by_raw={rawcode(e.rawcode):e for e in self.entries}
        self.pools={q:[rawcode(e.rawcode) for e in self.entries if e.quality==q] for q in (1,2,3,4)}
        self.items=[];self.products=[];self.removed=[];self.moves=[];self.adds=[];self.detaches=[]
        self.messages=[];self.over=False;self.create_mode='normal';self.output_mode=(True,True)
        self.return_mode=(True,True);self.pile_available=False;self.pile_reject=False
        self.on_create=self.on_add=self.on_drop=None;self.drop_mode='after';self.current_item=None
        self.current_unit=None;self.units=[];self.source_mutation=source_mutation
        self.owner=lane;self.inventory=inventory;self.quality=quality
        self.farmer=self.unit(lane);self.other=self.unit((lane+1)%4)
        self.n=dict(TD_FARMER_UNIT_ID=rawcode('uF01'),TD_ACTIVE_PLAYER_COUNT=4,
            tdCraftPickupRecords=Map(),tdCraftPickupWatchReady=False,
            tdCraftRecoveryRecords=[None]*4,tdCraftRecoveryCount=0,tdCraftRecoveryClock=0.,
            tdCraftBackendCommitOwner=0,TD_CRAFT_PHASE_IDLE=0,TD_CRAFT_PHASE_PREPARING=1,
            TD_CRAFT_PHASE_PREPARED=2,TD_CRAFT_PHASE_DELIVERING=3,TD_CRAFT_PHASE_CONSUMED=4,
            TD_CRAFT_FAILURE_NONE=0,TD_CRAFT_FAILURE_MATERIAL=1,TD_CRAFT_FAILURE_DELIVERY=2,
            TD_CRAFT_RECOVERY_STAGING=1,TD_CRAFT_RECOVERY_PENDING=2,
            TD_CRAFT_RECOVERY_RETURNING=3,TD_CRAFT_RECOVERY_EXTERNAL=4,
            TD_CRAFT_COMMIT_CANCELLED=0,TD_CRAFT_COMMIT_SUCCESS=1,TD_CRAFT_COMMIT_RESULT_FAILED=2,
            TD_CRAFT_COMMIT_ALREADY_ATTEMPTED=3,tdIsGameOver=lambda:self.over,
            GetUnitTypeId=lambda u:u.raw if u else 0,GetOwningPlayer=lambda u:u.owner,
            GetPlayerId=lambda p:p,GetHandleId=lambda i:i.key if i else 0,
            GetItemTypeId=lambda i:i.raw if i else 0,IsItemOwned=lambda i:i.holder is not None,
            IsItemVisible=lambda i:i.visible,GetItemX=lambda i:i.x,GetItemY=lambda i:i.y,
            SetItemVisible=lambda i,v:setattr(i,'visible',v),UnitItemInSlot=lambda u,s:u.slots[s],
            GetManipulatedItem=lambda:self.current_item,GetTriggerUnit=lambda:self.current_unit,
            CreateItem=self.create,RemoveItem=self.remove,UnitAddItem=self.add,UnitRemoveItem=self.drop,
            tdItemIsEquipment=lambda raw:raw in self.by_raw,tdItemQuality=lambda raw:self.by_raw[raw].quality if raw in self.by_raw else 0,
            tdItemQualityName=lambda q:('白装','绿装','蓝装','紫装')[q-1],
            tdItemActualPosition=lambda i:NS(x=i.x,y=i.y),tdGroundItemLane=lambda x,y:int(x/1000)-1 if x in (1000.,2000.,3000.,4000.) else -1,
            tdGroundPointInUpgradeCircle=lambda x,y,ox,oy:(x-ox)**2+(y-oy)**2<=144**2,
            tdGroundItemHandleValid=lambda i:i is not None and bool(i.raw) and i.holder is None,
            tdItemGroundPointSafe=lambda lane,p:self.pile_available and self.n['tdGroundItemLane'](p.x,p.y)==lane,
            tdTryPlaceItemInPile=self.place_pile,tdTryPlaceItemNear=self.forbidden_near,
            tdItemActualInPile=lambda i,l,q:i.raw and i.holder is None and i.pile==(l,q) and not self.pile_reject,
            DisplayTimedTextToPlayer=lambda owner,x,y,t,msg:self.messages.append((owner,msg)),
            destroy=self.destroy,TDCraftPickupRecord=self.watch_record,TDCraftRecoveryRecord=self.recovery_record,
            TDCraftNativeIngredient=self.ingredient)
        self.active_backend=None;self.compiled={}
        for package in ('TDCraftingItemWatch','TDCraftingRecovery','TDCraftingNativeBackend'):
            text=(ROOT/'wurst/items'/f'{package}.wurst').read_text().replace('override function ','function ').replace('private function ','function ')
            if source_mutation:text=source_mutation(package,text)
            if package=='TDCraftingNativeBackend':
                text+=destructor(text,'TDCraftNativeBackend','onDestroy')
                for name in METHODS:self.compiled[name]=compile_body(text,name,self.n,BACKEND_FIELDS+('tdCraftBackendCommitOwner',),'_body_'+name)
                self.n.update({name:self.compiled[name] for name in METHODS})
            else:
                names=re.findall(r'^(?:public )?function (\w+)\(',text,re.M)
                for name in names:
                    if name=='tdSetupCraftPickupWatch':continue
                    compile_body(text,name,self.n,('tdCraftRecoveryCount','tdCraftRecoveryClock'))
        self.backend=Backend(self,self.farmer,inventory,lane)
        self.originals=[]
        for index in range(count):
            item=self.item(self.pools[quality][index if mixed else 0] if index<3 else self.pools[4][-1])
            self.originals.append(item)
            if inventory:self.place(self.farmer,item,index)
            if index<3:
                plan=NS(capture=lambda key,raw:True)
                assert self.backend.capture(plan,item,index if inventory else -1)
        self.attempted=False;self.expected=(self.by_raw[self.pools[quality+1][roll-1]].rawcode if mixed else self.by_raw[self.originals[0].raw].next_id)
        ingredients=[NS(getKey=lambda k=k:k,getRawcode=lambda raw=self.originals[k-1].raw:raw) for k in (1,2,3)]
        # Catalog/planner allocation is a fixture, not map acceptance.
        batch=NS(beginAttempt=self.begin_attempt,result=lambda c,roll:rawcode(self.expected),
            sourceQuality=lambda:quality,ingredient=lambda slot:ingredients[slot])
        self.catalog=NS(quality=lambda raw:self.n['tdItemQuality'](raw))
        self.plan=NS(isFrozen=lambda:True,usesCatalog=lambda c:c is self.catalog,
            batch=lambda index:batch if index==0 else None)
        text=(ROOT/'wurst/items/TDCraftingTransaction.wurst').read_text()
        compile_body(text,'tdCraftBatchAvailable',self.n)
        self.commit_body=compile_body(text,'tdCommitCraftBatch',self.n)
    def unit(self,owner):
        u=NS(owner=owner,raw=rawcode('uF01'),alive=True,slots=[None]*6,x=1000.+owner*1000,y=100.)
        u.isAlive=lambda:u.alive;self.units.append(u);return u
    def item(self,raw):
        i=NS(key=len(self.items)+1,raw=raw,x=self.farmer.x,y=self.farmer.y,
             visible=True,holder=None,pile=None);self.items.append(i);return i
    def watch_record(self,item):return NS(kind='watch',material=item,handleKey=item.key,pickupSerial=0,refs=1,lastHolder=None)
    def recovery_record(self,u,i,raw,q,slot):
        watch=self.n['tdCraftWatchAcquire'](i)
        return NS(kind='recovery',owner=u.owner,playerId=u.owner,farmer=u,material=i,handleKey=i.key,
                  rawcode=raw,quality=q,originalSlot=slot,originalVisible=i.visible,watch=watch,
                  pickupSerial=watch.pickupSerial,custodyX=0.,custodyY=0.,custodyReady=False,
                  phase=1,notified=False,nextAt=0.)
    def ingredient(self,i,slot):
        watch=self.n['tdCraftWatchAcquire'](i)
        return NS(kind='ingredient',itemHandle=i,handleKey=i.key,rawcode=i.raw,slot=slot,
                  watch=watch,pickupSerial=watch.pickupSerial)
    def destroy(self,value):
        if isinstance(value,Backend):value.onDestroy();value.destroyed=True
        elif getattr(value,'kind',None) in ('ingredient','recovery'):
            self.n['tdCraftWatchRelease'](value.watch)
        elif getattr(value,'kind',None)=='watch':assert value.refs==0
    def begin_attempt(self):
        old=self.attempted;self.attempted=True;return not old
    def commit(self):return self.commit_body(self.plan,0,self.catalog,self.backend,1)
    def create(self,raw,x,y):
        if self.create_mode=='null':return None
        if self.create_mode=='alias':return self.originals[0]
        i=self.item(raw);i.x,i.y=x,y;self.products.append(i)
        if self.create_mode=='wrong':i.raw=self.pools[4][-1]
        if self.on_create:self.on_create(i)
        return i
    def unlink(self,item):
        if item.holder:
            u=item.holder
            for slot in range(6):
                if u.slots[slot] is item:u.slots[slot]=None
        item.holder=None
    def place(self,u,i,slot):
        self.unlink(i);assert u.slots[slot] is None
        u.slots[slot]=i;i.holder=u;i.pile=None
    def pickup(self,u,i,slot=None):
        if slot is None:slot=next((s for s in range(6) if u.slots[s] is None),None)
        if slot is not None:self.place(u,i,slot)
        self.current_item,self.current_unit=i,u;self.n['tdCraftTrackPickup']()
    def add(self,u,i):
        self.adds.append((u,i));result,insert=self.output_mode if i in self.products else self.return_mode
        slot=next((s for s in range(6) if u.slots[s] is None),None)
        if insert and slot is not None:self.pickup(u,i,slot)
        if self.on_add:self.on_add(u,i)
        return result
    def drop(self,u,i):
        self.detaches.append(i)
        if self.drop_mode=='before':
            if self.on_drop:self.on_drop(u,i)
            if i.holder is u:self.unlink(i)
        elif self.drop_mode=='none':
            if self.on_drop:self.on_drop(u,i)
        else:
            self.unlink(i)
            if self.on_drop:self.on_drop(u,i)
    def remove(self,i):
        assert i.raw,'double remove'
        self.unlink(i);i.raw=0;self.removed.append(i)
    def place_pile(self,i,lane,q,index):
        self.moves.append((i,lane,q))
        if not self.pile_available:return -1
        self.unlink(i);i.x=1000.+lane*1000
        i.y=q*256.;i.pile=(lane,q);return index
    def forbidden_near(self,*args):raise AssertionError('inventory nearby-terrain dependency')
    def pending(self):return self.n['tdCraftRecoveryRecords'][self.owner]
    def pump(self):self.n['tdCraftPumpRecovery'](.5)
    def conserved(self):
        assert not any(i in self.removed for i in self.originals[:3]),'failure consumed original'
        for i in self.items:
            holders=[u for u in self.units if i in u.slots]
            assert len(holders)<=1 and (holders[0] if holders else None) is i.holder
