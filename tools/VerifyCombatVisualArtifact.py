#!/usr/bin/env python3
"""Replay actual packed visual ownership; rendering/terrain/time are native boundaries."""
from pathlib import Path
import argparse, hashlib, json, math, re, sys, time
from GenerateTowerTerrainMask import Mpq
from VerifyPetAttackArtifact import PetAttackRuntime
from VerifyElementalPetArtifact import ElementRuntime
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerUpgradeArtifact import rawcode
from VerifyBuilderControlDelta import allocations
from VerifyTowerPlacementArtifact import unit_objects

class VisualRuntime(ElementRuntime):
    def __init__(self,script):
        self.visual_history=[];self.reject_visual=False;self.native_trigger=None;self.native_killer=None
        self.random_real_draws=[];self.control_orders=[];self.damage_timeline=[];self.native_hashtables={}
        super().__init__(script)
        self.invoke('init_TDTowerRuntime')
        self.invoke('init_TDActiveCooldownRuntime')
        self.invoke('init_TDTowerBloodlustAutocast')
        self.globals.update(bj_MAX_PLAYER_SLOTS=16,PLAYER_STATE_RESOURCE_FOOD_CAP='foodCap',PLAYER_STATE_RESOURCE_FOOD_USED='foodUsed')
        for player in range(16):self.globals['Player_players'][player]=player
    def native(self,name,args):
        if name in ('GetConstructingStructure','GetConstructedStructure','GetCancelledStructure') and self.native_trigger is not None:return True,self.native_trigger
        if name=='SetUnitInvulnerable':
            self.units[args[0]]['invulnerable']=args[1];return True,None
        if name=='destroyLLIterator':
            require(args[0] in self.iterators,'Retiring unknown native collection iterator')
            del self.iterators[args[0]];return True,None
        if name=='UnitDamageTarget':
            self.damage_timeline.append((self.now,tuple(args)))
        if name=='InitHashtable':
            self.table_serial+=1;self.native_hashtables[self.table_serial]={};return True,self.table_serial
        if name in ('SaveInteger','LoadInteger','HaveSavedInteger','RemoveSavedInteger','FlushChildHashtable'):
            require(args[0] in self.native_hashtables,'Unknown native autocast hashtable')
            table=self.native_hashtables[args[0]]
            if name=='FlushChildHashtable':
                for key in list(table):
                    if key[0]==args[1]:del table[key]
                return True,None
            key=tuple(args[1:3])
            if name=='SaveInteger':table[key]=args[3];return True,True
            if name=='LoadInteger':return True,table.get(key,0)
            if name=='HaveSavedInteger':return True,key in table
            table.pop(key,None);return True,None
        if name=='GetRandomReal':
            self.random_real_draws.append((*args,self.roll));return True,self.roll
        if name=='dispatch_DummyCaster_DummyCaster_castTarget':
            self.control_orders.append(tuple(args[1:5]))
            record=self.tables[self.globals['TDEnemyControlRuntime_byHandle']][args[4]]
            buff=self.globals['TDEnemyControlWindow_buffId'][record]
            self.units[args[4]].setdefault('abilities',{})[buff]=1
            return True,99999
        if name in ('AddSpecialEffect','AddSpecialEffectTarget','AddLightningEx'):
            self.visual_history.append((self.now,name,tuple(args)))
            if self.reject_visual:return True,None
            # Keep this gate's event-shaped visual trace while reusing the
            # elemental gate's real Fx initialization/setter/recycler boundary.
            handled,value=PetAttackRuntime.native(self,name,args)
            if name=='AddSpecialEffectTarget':
                self.effect_dummies[args[1]]=value
            return handled,value
        if name=='GetTriggerUnit' and self.native_trigger is not None:return True,self.native_trigger
        if name=='GetKillingUnit' and self.native_killer is not None:return True,self.native_killer
        if name in ('LinkedList_iterator','dispatch_LinkedList_LinkedList_iterator') and args[0] not in self.lists:
            raise ValueError('Uninitialized actual visual replay dependency list '+repr(args))
        return super().native(name,args)
    def pet(self,skills,host=101,slot=0,level=3):
        return PetAttackRuntime.pet(self,skills,host,slot,level)
    def tick_visuals(self,elapsed=.05):
        self.now+=elapsed;self.executed_steps=0
        callback=self.globals.get('TDCombatVisualRuntime_cleanup',0)
        if callback:
            expected=allocations(self.script)['alloc_CallbackPeriodic_doPeriodically_TDCombatVisualRuntime'][1]
            require(self.globals['CallbackPeriodic_typeId'][callback]==expected,'Visual callback actual owner changed')
            self.invoke('call_doPeriodically_TDCombatVisualRuntime',callback,callback)
    def clear(self):
        self.invoke('tdCombatVisualShutdown')
        require(not self.visual_handles and not self.lightning_handles,'Shutdown leaked owned visual handles')
    def count(self):
        return self.globals.get('TDCombatVisualRuntime_hitVisualCount',0),self.globals.get('TDCombatVisualRuntime_castVisualCount',0)

def verify_hits(script):
    records=[]
    for element in range(1,6):
        r=VisualRuntime(script);pet=r.pet([])
        r.globals['TDPet_species'][pet]=(element-1)*3+1
        result=r.emit(100.)
        require(r.visual_history and r.count()[0] in (1,2),'Bound true primary did not draw element '+str(element))
        require(result['amount']==100. and r.score()==100.,'Visual changed physical event or score')
        models=[args[0] for _,name,args in r.visual_history if name=='AddSpecialEffect']
        r.tick_visuals(.30)
        require(r.count()==(0,0) and not r.visual_handles and not r.lightning_handles,'Expired hit visual leaked')
        require(r.globals['TDCombatVisualRuntime_cleanup']==0,'Idle visual timer did not stop')
        records.append({'element':element,'models':models,'pieces':len(r.visual_history)})
    require(len({x['models'][0] for x in records})==5,'Five elements reuse one core model')
    r=VisualRuntime(script);r.emit(100.);require(not r.visual_history,'Unbound ordinary attack got a new visual')
    r=VisualRuntime(script);r.pet([]);r.emit(0.);require(not r.visual_history,'Zero original attack got visual')
    r=VisualRuntime(script);p=r.pet([]);r.invoke('TDPet_recall',p);r.emit(100.);require(not r.visual_history,'Recalled pet got visual')
    return records

def verify_gear(script,units):
    r=VisualRuntime(script);matrix=0;hosts=[]
    required={1:'iP01',2:'iP02',3:'iP03',4:'iP05',5:'iP04'}
    for identity in units:
        identity=rawcode(identity)
        choice=r.invoke('tdTowerChoiceForUnitTypeId',identity)
        if choice:hosts.append((identity,choice))
    require(len(hosts)==35,'Current 35 tower visual matrix changed')
    items=[rawcode('i'+q+f'{i:02d}') for q in ('W','G','B','P') for i in range(1,11)]
    for typeid,choice in hosts:
        for item in items:
            for slot in range(3):
                loadout=[0]*3;loadout[slot]=item
                profile=r.invoke('tdCombatVisualGearProfile',choice,*loadout)
                require(profile==(choice if item==rawcode(required[choice]) else 0),'Wrong profession/quality became worn visual')
                matrix+=1
    for choice in range(1,6):
        typeid=next(typeid for typeid,c in hosts if c==choice)
        r.units[101]['type']=typeid
        r.invoke('tdCombatVisualRefreshGear',101,choice,rawcode(required[choice]),0,0)
        require(len(r.visual_handles)==1,'Profession special did not produce exactly one attachment')
        before=len(r.visual_history);r.invoke('tdCombatVisualRefreshGear',101,choice,rawcode(required[choice]),0,0)
        require(len(r.visual_history)==before,'Unchanged loadout rebuilt attachment')
        r.invoke('tdCombatVisualClearPet',101);require(len(r.visual_handles)==1,'Recall clear deleted gear layer')
        r.invoke('tdCombatVisualClearGear',101);require(not r.visual_handles,'Unloading gear leaked effect')
    # Native DROP_ITEM still occupies the original slot; execute real excluded snapshot.
    r.units[101]['type']=next(typeid for typeid,c in hosts if c==1)
    r.inventory_items[88001]=rawcode('iP01');r.units[101]['inventory']={0:88001}
    r.invoke('tdRefreshTowerEquipmentBonuses',101,0)
    require(len(r.visual_handles)==1,'Inventory refresh did not notify attached appearance')
    r.native_trigger=101
    r.invoke('tdRefreshTowerEquipmentBonuses',101,88001)
    require(not r.visual_handles,'DROP excluded-item snapshot retained worn weapon')
    r.clear()
    return {'actual_35x40x3_matrix':matrix,'five_profession_attachment_cases':5,'repeat_refresh_no_rebuild':True,'drop_excluded_snapshot':True}

def verify_work(script):
    r=VisualRuntime(script);r.units[101]['type']=rawcode('uA11')
    r.inventory_items[88001]=rawcode('iP01');r.units[101]['inventory']={0:88001}
    refresh=lambda:r.invoke('tdRefreshTowerEquipmentBonuses',101,0)
    refresh();require(len(r.visual_handles)==1,'Work fixture lacks original gear')
    r.native_trigger=101;r.invoke('tdHandleTowerUpgradeStarted')
    require(not r.visual_handles,'Upgrade start retained appearance')
    refresh();r.invoke('tdPetRefreshHost',101,0.)
    require(not r.visual_handles,'Refresh during upgrade reattached appearance')
    r.tick_visuals(.30);refresh()
    require(not r.visual_handles,'Cleanup erased work suspension')
    r.invoke('tdHandleTowerUpgradeCancelled')
    r.invoke('tdHandleTowerUpgradeStarted');r.flush()
    require(not r.visual_handles,'Stale cancellation resumed a newer upgrade')
    r.invoke('tdHandleTowerUpgradeCancelled');r.flush()
    require(len(r.visual_handles)==1,'Current cancellation did not restore one appearance')
    r.invoke('tdHandleTowerUpgradeStarted');r.units[101]['type']=rawcode('uA12')
    r.invoke('tdHandleTowerUpgradeFinished')
    require(len(r.visual_handles)==1,'Upgrade finish did not restore one current-model appearance')
    r.invoke('tdHandleTowerDeath');require(not r.visual_handles,'Tower death leaked gear')
    r.tick_visuals(.30);require(r.count()==(0,0),'Tower removal left short visuals')
    r.clear()
    return {'start_refresh_hidden':True,'cleanup_preserves_pause':True,'stale_cancel_rejected':True,'cancel_restore':1,'finish_restore':1,'death_clean':True}

def verify_rejection(script):
    results=[]
    for code in ('Tspl','Pdam','Eadd'):
        r=VisualRuntime(script);r.pet([]);r.invoke('DamageEvent_setNextDamageId',rawcode(code))
        if code=='Eadd':r.invoke('DamageEvent_setNextDamageFromCode')
        r.emit(100.)
        require(not r.visual_history,code+' added an ordinary hit layer');results.append(code)
    r=VisualRuntime(script);r.pet([]);r.invoke('DamageEvent_setNextDamageFromCode');r.emit(100.)
    require(not r.visual_history,'Code segment added ordinary hit layer');results.append('code')
    r=VisualRuntime(script);r.pet([]);r.emit(-100.)
    require(not r.visual_history,'Spell added ordinary hit layer');results.append('spell')
    r=VisualRuntime(script);p=r.pet([]);r.invoke('tdPetTowerWorkStarted',101);r.emit(100.)
    require(not r.visual_history,'Paused pet added ordinary hit layer');results.append('paused')
    r=VisualRuntime(script);r.units[101]['type']=rawcode('uA11')
    r.invoke('tdCombatVisualRefreshGear',101,1,rawcode('iP01'),0,0);count=len(r.visual_history)
    r.emit(100.);require(len(r.visual_history)==count and len(r.visual_handles)==1,'Purple gear without pet changed ordinary hit')
    results.append('purple_without_pet')
    r.clear()
    return results

def verify_finisher(script):
    r=VisualRuntime(script);r.pet([]);r.units[102].update(life=200.,maxLife=200.)
    r.emit(100.)
    epoch=r.invoke('tdFlowEpoch');r.tables[r.globals['TDSpawn_tdEnemyMatchEpochs']][102]=epoch
    r.units[102].update(life=0.,alive=False);r.native_trigger=102;r.native_killer=101
    before=len(r.visual_history);r.invoke('tdHandleEnemyDeath')
    added=r.visual_history[before:]
    require(len(added)==1 and added[0][2][0].endswith('RifleImpact.mdx'),'Confirmed Game kill did not add one finisher core')
    before=len(r.visual_history);r.invoke('tdHandleEnemyDeath')
    require(len(r.visual_history)==before,'Repeated death replay added a second finisher')
    r.tick_visuals(.35);require(not r.visual_handles and not r.lightning_handles,'Finisher failed .30 lifetime cleanup')
    r.clear()
    r=VisualRuntime(script);r.pet([]);r.units[102].update(life=200.,maxLife=200.)
    r.emit(100.);r.invoke('tdMarkEnemyLeaked',102);r.native_trigger=102;r.native_killer=101
    before=len(r.visual_history);r.invoke('tdHandleEnemyDeath');require(len(r.visual_history)==before,'Leak settlement added a finisher')
    r.clear()
    r=VisualRuntime(script);r.pet([]);r.enter(8);target=r.target(0)
    r.emit(100.,target=target);r.native_trigger=target;r.native_killer=101
    before=len(r.visual_history);r.invoke('tdHandleEnemyDeath');require(len(r.visual_history)==before,'Trial target added a Game finisher')
    r.clear()
    return {'actual_game_claim':True,'duplicate_death':0,'leak':0,'trial':0,'lifetime':.30}

def verify_budget_cleanup(script):
    r=VisualRuntime(script)
    # Direct admitted rendering input stresses all 40 legal lane tower sources.
    for lane in range(4):
        for index in range(10):
            host=1000+lane*10+index
            r.units[host]={**r.units[101],'owner':lane,'alive':True,'life':10000.,'type':r.units[101]['type']}
            r.invoke('tdCombatVisualHit',host,0.,0.,100.,0.,2,lane,False)
            require(r.count()[0]<=32,'Ordinary hit global32 cap breached')
    require(r.count()[0]==32,'40-source burst did not saturate bounded ordinary layer')
    require(len(r.lists[r.globals['TDCombatVisualRuntime_sources']])==40,'Stress lost source admission records')
    require(len([cb for _,cb in r.periodics if r.globals['CallbackPeriodic_typeId'][cb]==allocations(r.script)['alloc_CallbackPeriodic_doPeriodically_TDCombatVisualRuntime'][1]])==1,'Ordinary hits created per-hit visual timers')
    count=len(r.visual_history)
    r.invoke('tdCombatVisualHit',1000,0.,0.,100.,0.,2,0,False)
    require(len(r.visual_history)==count,'Single source .20 limit did not reject repeat')
    r.invoke('tdCombatVisualClearLane',0)
    require(all(not (name=='AddSpecialEffectTarget' and args[1]==1000) for _,name,args in r.visual_history),'Unexpected gear in hit stress')
    r.tick_visuals(.30);require(r.count()==(0,0) and not r.visual_handles,'Burst expiration left handles')
    require(not r.lists[r.globals['TDCombatVisualRuntime_sources']],'Budget-rejected empty owners leaked after expiry')
    # Source forget invalidates owner serial before a reused native handle gets fresh records.
    r.invoke('tdCombatVisualHit',1000,0.,0.,100.,0.,2,0,False)
    r.invoke('tdCombatVisualForgetSource',1000);require(r.count()[0]==0,'Source forget failed hit cleanup')
    r.now+=1.;r.invoke('tdCombatVisualHit',1000,0.,0.,100.,0.,3,0,False)
    require(r.count()[0]==1,'Reused source handle cannot admit a fresh owner')
    r.tick_visuals(.30);require(r.count()[0]==0,'Old/new owner cleanup leaked')
    r.clear()
    r=VisualRuntime(script);r.invoke('tdCombatVisualHit',101,0.,0.,100.,0.,2,0,False)
    r.invoke('tdResetWaveFlowState');r.tick_visuals(.05)
    require(not r.visual_handles and not r.lightning_handles and r.count()==(0,0),'Epoch advance retained prior visual')
    require(not r.lists[r.globals['TDCombatVisualRuntime_sources']],'Epoch advance retained prior source owner')
    r=VisualRuntime(script);r.reject_visual=True
    r.invoke('tdCombatVisualHit',101,0.,0.,100.,0.,2,0,False)
    require(not r.visual_handles and len(r.lists[r.globals['TDCombatVisualRuntime_sources']])==1,'Null-native fixture did not retain exactly one pending source')
    r.tick_visuals(.30)
    require(not r.lists[r.globals['TDCombatVisualRuntime_sources']] and r.globals['TDCombatVisualRuntime_cleanup']==0,'Null-native empty owner never reclaimed')
    return {'forty_sources_peak':32,'single_source_gate':True,'expiry':True,'lane_clear':True,'handle_reuse':True}

def verify_gameplay(script,baseline):
    traces=[]
    # Explicit complete loadouts own identical IDs/qualities in both maps.
    # Only their approved physical order differs. Three attack passives no
    # longer coexist, so preserve their damage/FX comparisons in legal pairs.
    for skills in ([(0,1),(7,1),(8,1),(11,1)],[(0,1),(16,1),(7,1),(11,1)],
                   [(0,1),(16,1),(17,2),(11,1)],[(0,1),(5,1),(6,2),(11,1)],
                   [(0,1),(5,1),(8,2),(11,1)],[(0,1),(5,1),(6,1),(38,4)]):
        for mode in ('normal','null','exhausted'):
            runs=[]
            for source in (baseline,script):
                r=VisualRuntime(source);r.reject_visual=mode=='null';p=r.pet(skills)
                if mode=='exhausted' and 'TDCombatVisualRuntime_castVisualCount' in r.globals:
                    r.globals['TDCombatVisualRuntime_castVisualCount']=128
                amounts=[]
                if (38,4) in skills:
                    r.visible_units=[102,103]
                    r.units[103]={**r.units[102],'x':100.,'abilities':{}}
                    r.units[102].update(life=100000.,maxLife=100000.)
                    amounts.append(r.emit(100.)['amount'])
                    for _ in range(95):
                        r.executed_steps=0;r.tick_effects(.05);r.tick_visuals(0.)
                else:
                    for i in range(8):
                        r.now=10.+i*.25;r.units[102].update(life=10000.,alive=True)
                        amounts.append(r.emit(100.)['amount']);r.flush();r.tick_visuals(0.)
                runs.append({'amounts':amounts,'damage':r.native_damage,'damage_time':r.damage_timeline,'score':r.score(),'gold':r.player_resources,
                             'draws':r.random_draws,'real_draws':r.random_real_draws,'controls':r.control_orders,
                             'pet_rotation':r.globals['TDPet_resolveRotation'][p],'cd':r.globals['TDPet_readyAt'][p],
                             'host_bonus':{key:r.units[101]['abilities'].get(key,0) for key in (rawcode('Pbat'),rawcode('Pbsp'))},
                             'target_speed':r.units[102]['speed']})
            require(runs[0]==runs[1],'Visual success/failure changed actual combat trajectory '+repr(skills)+' '+mode)
            traces.append({'skills':skills,'visual_mode':mode,'identical':True,'native_segments':len(runs[1]['damage'])})
    return traces

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('map',type=Path);p.add_argument('--baseline',type=Path,required=True);a=p.parse_args()
    mpq=Mpq(a.map.read_bytes());script=mpq.extract('war3map.j').decode('utf-8');prior=Mpq(a.baseline.read_bytes()).extract('war3map.j').decode('utf-8')
    require('function init_TDCombatVisualRuntime takes' in script,'Missing actual visual initialization')
    report={'sha256':hashlib.sha256(a.map.read_bytes()).hexdigest()}
    for key,run in (('hits',lambda:verify_hits(script)),
                    ('gear',lambda:verify_gear(script,unit_objects(mpq.extract('war3map.w3u')))),
                    ('budgets_cleanup',lambda:verify_budget_cleanup(script)),
                    ('tower_work',lambda:verify_work(script)),('rejection',lambda:verify_rejection(script)),
                    ('finisher',lambda:verify_finisher(script)),('gameplay_trajectory',lambda:verify_gameplay(script,prior))):
        print('RUN '+key, file=sys.stderr,flush=True);start=time.monotonic()
        report[key]=run()
        print('PASS '+key+' %.3fs'%(time.monotonic()-start),file=sys.stderr,flush=True)
    report['boundary']='Actual packed JASS. Effects/lightning/rendering, native terrain, engine timers/armor are explicit boundaries; no game/FPS claim. Moving API is DCE only in the A baseline; when live, this gate uses the reviewed elemental Fx native boundary. Global8/per-cast2/dummy1s stress belongs to the elemental VFX gate.'
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
