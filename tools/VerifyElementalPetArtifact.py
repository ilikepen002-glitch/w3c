#!/usr/bin/env python3
"""Replay final-map elemental spells with explicit clock/handle/region/native-order boundaries.
Packed original-hit fence, cast creation, CD write, scheduler, geometry, target identity,
damage, controls, slow ownership and destruction execute. Native Buff acceptance and
visual handles are recorded models. Trial handle/revision adversaries use explicit
low-level registry setup after actual no-refill death, never production ACTIVE refill.
This is not Warcraft timing or visual observation.
"""
from pathlib import Path
import argparse, hashlib, json, math
from GenerateTowerTerrainMask import Mpq
from VerifyPetAttackArtifact import PetAttackRuntime, near
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerUpgradeArtifact import rawcode
from VerifyBuilderControlDelta import allocations

class ElementRuntime(PetAttackRuntime):
    def __init__(self,script):
        self.visual_handles={};self.visual_history=[];self.visual_serial=100000
        self.control_orders=[];self.reject_visual=False;self.reject_control=False
        self.effect_dummies={};self.fx_history=[];self.damage_trace=[];self.random_trace=[];self.effect_regions={}
        super().__init__(script)
        self.visual_history.clear()
        self.callback_allocations=allocations(script)
        self.fx_pool_baseline=None
        if 'new_TDVisualMoving' in self.functions:
            # Run real locked-library initialization once. Engine world bounds,
            # unit setters and native handle reinterpreting remain boundaries.
            self.globals.update(PLAYER_NEUTRAL_PASSIVE=15,bj_MAX_PLAYER_SLOTS=16,
                                bj_mapInitialPlayableArea='visualPlayableBounds')
            self.rects['worldBounds']=(-4096.,-4096.,4096.,4096.)
            self.rects['visualPlayableBounds']=(-4096.,-4096.,4096.,4096.)
            for name in ('init_Player','init_Basics','init_Colors','init_TypeCasting','init_MapBounds','init_DummyRecycler'):
                require(name in self.functions,'Live Fx lacks its actual library initializer '+name)
                self.invoke(name)
            self.fx_pool_baseline=self.fx_pool_size()
            require(self.fx_pool_baseline==48,'Locked DummyRecycler pool is not 8x6')
        self.damage_trace.clear();self.random_trace.clear()
    def fx_pool_size(self):
        return sum(len(self.lists[self.globals['DummyRecycler_angleQueues'][angle]]) for angle in range(8))
    def native(self,name,args):
        if name=='GetRandomReal':self.random_trace.append((self.now,name,tuple(args),self.roll))
        if name=='GetRandomInt':self.random_trace.append((self.now,name,tuple(args)))
        if name=='UnitDamageTarget':self.damage_trace.append((self.now,*args))
        if name=='GetLocalPlayer':return True,0
        if name=='ModuloReal':return True,args[0]%args[1]
        if name=='vec3_getTerrainZ':
            require(name in self.functions and len(args) in (3,4),'Unknown Fx terrain tuple lowering')
            return True,0.0
        if name=='GetPlayableMapRect':return True,'visualPlayableBounds'
        if name=='CreateRegion':
            region=80000+len(self.effect_regions);self.effect_regions[region]=[];return True,region
        if name=='RegionAddRect':
            require(args[0] in self.effect_regions and args[1] in self.rects,'Unknown Fx map-bounds native region')
            self.effect_regions[args[0]].append(args[1]);return True,None
        if name=='StringHash':
            # Only the real Colors named-color registry uses this engine boundary.
            # Stable distinct fixture keys preserve its table, not WC3 hash values.
            return True,int.from_bytes(hashlib.sha256(args[0].encode()).digest()[:4],'little') & 0x7fffffff
        if name=='ConvertFogState':return True,args[0]  # Native handle-type reinterpretation.
        if name=='dispatch_LinkedList_LinkedList_enqueue':
            self.lists[args[0]].append(args[1]);return True,None
        if name=='dispatch_LinkedList_LinkedList_dequeue':
            require(self.lists[args[0]],'Actual dummy queue underflow');return True,self.lists[args[0]].pop(0)
        if name in ('SetUnitX','SetUnitY','SetUnitFlyHeight','SetUnitFacing','SetUnitScale','SetUnitVertexColor','PauseUnit','SetUnitOwner'):
            unit=self.units[args[0]]
            require(unit['type']==self.globals['DummyRecycler_DUMMY_UNIT_ID'],'Cosmetic setter touched a non-Fx unit')
            if name=='SetUnitX':unit['x']=args[1]
            elif name=='SetUnitY':unit['y']=args[1]
            elif name=='SetUnitFlyHeight':unit['z']=args[1]
            elif name=='SetUnitFacing':unit['facing']=args[1]
            elif name=='SetUnitScale':unit['scale']=args[1]
            elif name=='SetUnitVertexColor':unit['rgba']=tuple(args[1:5])
            elif name=='PauseUnit':unit['paused']=args[1]
            else:unit['owner']=args[1]
            if args[0] in self.effect_dummies:
                self.fx_history.append((self.now,name,args[0],unit['x'],unit['y'],unit.get('z',0.),unit.get('facing',0.),unit.get('scale',1.)))
            return True,None
        if name=='GetUnitFlyHeight':return True,self.units[args[0]].get('z',0.)
        if name=='doAfter':
            allocation=getattr(self,'callback_allocations',{}).get('alloc_CallbackSingle_doAfter_DummyRecycler')
            if allocation and self.globals[allocation[0]][args[1]]==allocation[1]:
                require(args[0]==1.0,'Actual Fx recycle delay is not exactly one second')
            handled,value=super().native(name,args)
            self.timers[self.globals['CallbackSingle_t'][args[1]]]['created']=self.now
            return handled,value
        if name=='UnitDamageTarget' and getattr(self,'terminal_in_hit',False):
            self.terminal_in_hit=False
            handled,value=super().native(name,args)
            self.invoke('tdSetGameOver',True)
            self.invoke('call_doPeriodically_TDPetRuntime',self.cleanup_cb,self.cleanup_cb)
            self.terminal_on_stack={
                'busy':self.invoke('tdPetAttackQueueBusy'),
                'destroy_allowed':self.invoke('tdPetCanDestroyMatchRecords'),
                'pet_type':self.globals['TDPet_typeId'][self.cleanup_pet],
                'callback_type':self.globals['CallbackPeriodic_typeId'][self.cleanup_cb],
                'records':self.globals['TDPetState_tdPetMatchRecords']}
            return handled,value
        if name=='doPeriodically':
            self.timer_serial+=1;self.timers[self.timer_serial]={'destroyed':False,'closure':args[1],'periodic':True}
            self.globals['CallbackPeriodic_t'][args[1]]=self.timer_serial
            self.periodics.append(tuple(args[:2]));return True,args[1]
        if name=='timer_release' and self.timers.get(args[0],{}).get('periodic'):
            require(not self.timers[args[0]]['destroyed'],'Periodic native timer released twice')
            self.timers[args[0]]['destroyed']=True;return True,None
        if name=='registerSpellEffectEvent':return True,None
        if name=='dispatch_LinkedList_LinkedList_add_1':
            # Final catalog DCE eliminates the old packed-generic dummy parameter.
            signature=self.functions[name][0]
            require(len(args)==len(signature) and len(args) in (2,3),'Final list-add signature changed')
            require(len(args)==2 or signature[1] in ('w__wurst_stackPos','stackPos'),'Unrecognized generic add argument')
            self.lists[args[0]].append(args[-1]);return True,None
        if name in ('tdTowerChoiceForUnitTypeId','tdTowerLevelForUnitTypeId','tdTowerBranchForUnitTypeId',
                                                        'tdEnemyLaneId','tdEnemyWave','tdEnemyWasLeaked','tdEnemyDeathWasSettled'):
            return False,None
        if name=='RAbsBJ':return True,abs(args[0])
        if name=='group_enumUnitsInRange':
            self.groups[args[0]]=[target for target in self.visible_units if
                            math.hypot(self.units[target]['x']-args[1],self.units[target]['y']-args[2])<=args[3]]
            return True,None
        if name=='AddSpecialEffectTarget':
            unit=self.units[args[1]]
            self.visual_history.append((self.now,args[0],unit['x'],unit['y']))
            if self.reject_visual:return True,None
            handled,value=super().native(name,args)
            self.effect_dummies[args[1]]=value
            self.fx_history.append((self.now,name,args[1],unit['x'],unit['y'],unit.get('z',0.),unit.get('facing',0.),unit.get('scale',1.)))
            return handled,value
        if name=='AddLightningEx' and self.reject_visual:return True,None
        if name=='AddSpecialEffect':
            self.visual_history.append((self.now,*args[:3]))
            if self.reject_visual:return True,None
            self.visual_serial+=1;self.visual_handles[self.visual_serial]=tuple(args[:3]);return True,self.visual_serial
        if name=='DestroyEffect':
            require(args[0] in self.visual_handles,'Visual destroyed twice or without ownership')
            del self.visual_handles[args[0]]
            self.effect_dummies={unit:effect for unit,effect in self.effect_dummies.items() if effect!=args[0]}
            return True,None
        if name=='dispatch_DummyCaster_DummyCaster_castTarget':
            if self.reject_control:return True,None
            self.control_orders.append(tuple(args[1:5]))
            record=self.tables[self.globals['TDEnemyControlRuntime_byHandle']][args[4]]
            buff=self.globals['TDEnemyControlWindow_buffId'][record]
            self.units[args[4]].setdefault('abilities',{})[buff]=1
            return True,99999
        return super().native(name,args)
    def pet(self,skill):
        species=(skill-19)//4*3+1;quality=(skill-19)%4+1
        if self.four_slot_contract:
            # Complete legal loadout: Resolve stays quiescent before the fifth
            # primary; this suite emits at most one primary per fixture host.
            # Hero39 is incompatible with the ordinary fixture tower. Avoid
            # skill5's real slow, which contaminates Boss/control negatives.
            pet=super().pet([(0,1),(17,1),(39,1),(skill,quality)])
            require(self.invoke('TDPet_skillAt',pet,3)==skill,'Actual slot3 fixed-quality/element admission failed')
            return pet
        pet=self.invoke('new_TDPet',0,species,1)
        require(self.invoke('tdPetStore',0,pet),'Actual collection rejected elemental fixture')
        self.invoke('TDPet_setSkill',pet,0,skill,quality)
        require(self.invoke('TDPet_skillAt',pet,0)==skill,'Actual fixed-quality/element admission failed')
        self.globals['TDPet_level'][pet]=3;self.globals['TDPet_host'][pet]=101;self.globals['TDPet_generation'][pet]=1
        return pet
    def enemy(self,target,x=100.,y=0.,lane=0,life=100000.):
        self.units[target]={**self.units[102],'alive':True,'life':life,'maxLife':life,'abilities':{},
                                                                                        'x':x,'y':y,'userdata':lane*10000+100,'lane':lane}
    def periodic_callbacks(self,package):
        allocation=self.callback_allocations.get('alloc_CallbackPeriodic_doPeriodically_'+package)
        if allocation is None:return []  # Optional visual closure can be DCE in a baseline.
        array,type_id=allocation
        require(array=='CallbackPeriodic_typeId','Unrecognized actual periodic allocator')
        return sorted({cb for interval,cb in self.periodics if interval==.05 and
                       self.globals[array][cb]==type_id and
                       not self.timers[self.globals['CallbackPeriodic_t'][cb]]['destroyed']})
    def tick(self,elapsed=.05):
        self.now+=elapsed
        # Visual expiry and battle scheduling are separate actual closures, not
        # an interval-based guess. Deliver each as its own controlled native turn.
        for package in ('TDCombatVisualRuntime','TDPetEffectScheduler'):
            callbacks=self.periodic_callbacks(package)
            if package=='TDPetEffectScheduler':require(len(callbacks)==1,'One shared battle scheduler required')
            else:require(len(callbacks)<=1,'Multiple shared visual recyclers')
            for cb in callbacks:
                self.executed_steps=0
                self.invoke('call_doPeriodically_'+package,cb,cb)
        self.drain_zero()
    def finish(self,seconds=5.25):
        for _ in range(round(seconds/.05)):self.tick()
        self.flush_fx_recycle()
    def fx_recycle_pending(self):
        allocation=self.callback_allocations.get('alloc_CallbackSingle_doAfter_DummyRecycler')
        if allocation is None:return []
        array,type_id=allocation
        require(array=='CallbackSingle_typeId','Unknown actual dummy recycle allocator')
        pending=[]
        for delay,cb in self.scheduled:
            if self.globals[array][cb]==type_id:
                require(delay==1.,'Actual dummy recycle native delay changed')
                timer=self.timers[self.globals['CallbackSingle_t'][cb]]
                require(not timer['destroyed'],'Queued recycle has retired native timer')
                pending.append((timer['created']+1.,cb))
        return sorted(pending)
    def deliver_due_fx_recycle(self):
        due=[cb for deadline,cb in self.fx_recycle_pending() if deadline<=self.now+1e-8]
        for cb in due:self.executed_steps=0;self.run_timer(cb)
        return len(due)
    def flush_fx_recycle(self):
        if self.fx_pool_baseline is None:return
        # Deliver ONLY actual locked DummyRecycler single callbacks at created+1.
        # Unrelated game/trial timers retain their separate controlled deliveries.
        for deadline,cb in self.fx_recycle_pending():
            self.now=max(self.now,deadline);self.executed_steps=0;self.run_timer(cb)
        require(self.fx_pool_size()==self.fx_pool_baseline,'Actual delayed Fx recycle did not restore pool baseline')

EXPECTED={19:(6,480.),20:(1,130.),21:(4,240.),22:(48,2160.),23:(1,65.),
                                        24:(9,195.),25:(12,1200.),26:(24,1680.),27:(1,95.),28:(16,1120.),
                                        29:(12,1680.),30:(96,1920.),31:(4,140.),32:(12,1680.),33:(48,2460.),
                                        34:(28,1080.),35:(1,110.),36:(8,1040.),37:(0,0.),38:(24,2040.)}

def verify_twenty(script):
    records=[]
    for skill,(expected_count,expected_total) in EXPECTED.items():
        r=ElementRuntime(script);pet=r.pet(skill)
        for target in range(102,116):r.enemy(target)
        r.enemy(116,lane=1);r.visible_units=list(range(102,117))
        r.auto_post=False;r.emit(100.)
        require(not r.native_damage and r.invoke('tdPetEffectTaskCount')==0,'Element starts inside original phase')
        r.drain_zero();require(r.invoke('tdPetEffectTaskCount')==1,'One active context was not created')
        expected_cd=r.invoke('tdActiveSkillDefinitionForPetSkill',skill)
        r.invoke('tdActiveSkillDefinitionForKey',expected_cd)
        cd=r.globals['tdActiveSkillDefinitionForKey_return_baseCooldown']
        near(r.globals['TDPet_readyAt'][pet],r.now+cd,'One shared metadata CD timestamp')
        r.auto_post=True;r.finish()
        require(len(r.native_damage)==expected_count,f'Skill{skill} count: {len(r.native_damage)}, expected{expected_count}')
        near(sum(hit[2] for hit in r.native_damage),expected_total,f'Skill{skill} actual damage sequence')
        require(all(hit[0]==101 and hit[1]!=116 for hit in r.native_damage),'Source ownership/cross-lane exclusion changed')
        require(r.invoke('tdPetEffectTaskCount')==0 and not r.visual_handles,'Context completion leaked effect/visual ownership')
        require(r.visual_history,'Element omitted its actual stage/geometry visuals')
        require(r.globals['TDPetCastContext_visualCount']==0,'Global visual counter leaked')
        print('verified skill',skill,flush=True)
        records.append({'skill':skill,'hits':expected_count,'total':expected_total,
                                                                        'visual_emissions':len(r.visual_history),'control_orders':len(r.control_orders)})
    return records

def verify_negatives(script):
    result={}
    # Native main hit kills the seed before its queued context starts.
    r=ElementRuntime(script);pet=r.pet(24)
    r.enemy(102,life=50.)
    for target in range(103,107):r.enemy(target)
    r.visible_units=list(range(102,107));r.emit(100.)
    require(not r.units[102]['alive'],'Lethal seed fixture did not kill original')
    r.finish()
    require(len(r.native_damage)==6 and {hit[1] for hit in r.native_damage}=={103,104,105},
                                    'Dead seed lost one-generation propagation or changed its cap')
    require(all(hit[2]==15. for hit in r.native_damage),'Dead seed changed weak ticks')
    result['seed_main_lethal']={'original_ticks':0,'neighbour_ticks':6,'generations':1}
    # A cast with a full identity table cannot acquire an unowned thirteenth control.
    r=ElementRuntime(script);pet=r.pet(29)
    r.units[201]={**r.units[101],'abilities':{},'inventory':{}}
    for target in range(102,115):r.enemy(target)
    r.visible_units=list(range(102,115))
    for target in range(102,114):
        require(r.invoke('tdTryEnemyControlToken',201,target,0,.6,rawcode('Pfr0'),60,852095,999,rawcode('Bpfr')),
                                        'Protected-window fixture was not accepted')
    before=len(r.control_orders);r.emit(100.);r.tick(.6)
    require(len(r.control_orders)==before,'Thirteenth victim escaped full identity table')
    r.invoke('TDPet_invalidateCombat',pet)
    require(114 not in r.tables[r.globals['TDEnemyControlRuntime_byHandle']],
                                    'Thirteenth target retained an orphan window/control')
    require(all(rawcode('Bpfr') in r.units[t]['abilities'] for t in range(102,114)),
                                    'Source cancellation removed another source control')
    result['full_control_identity_table']={'protected':12,'orphan_controls':0,'other_source_preserved':12}
    # Native order rejection rolls back only its reserved window.
    r=ElementRuntime(script);pet=r.pet(23);r.reject_control=True;r.visible_units=[102]
    r.emit(100.);r.tick()
    record=r.tables[r.globals['TDEnemyControlRuntime_byHandle']][102]
    window=r.globals['TDEnemyControlWindow_window'][record]
    near(r.globals['TDShieldWindow_readyAt'][window],0.,'Rejected native order rollback')
    require(r.globals['TDEnemyControlWindow_sourceToken'][record]==0,'Rejected cast retained source token')
    r.reject_control=False
    require(r.invoke('tdTryEnemyControlToken',101,102,0,.75,rawcode('Prt0'),75,852171,111,rawcode('Bprt')),
                                    'Rejected control incorrectly retained its protection deadline')
    r.invoke('tdCancelEnemyControl',102,101,111)
    result['native_control_rejection']={'rolled_back':True,'next_control_accepted':True}
    # Death leaves its slot empty. An explicit low-level identity-registry adversary
    # then changes a handle/revision without granting production ACTIVE refill.
    for reused in (False,True):
        r=ElementRuntime(script);r.auto_post=False;r.enter(8);pet=r.pet(33)
        original=[r.target(index) for index in range(5)]
        for target in original:r.units[target].update(x=100.,y=0.)
        r.visible_units=original[:];r.emit(100.,target=original[0]);r.drain_zero()
        old=original[0];old_revision=r.globals['TDTrialBinding_revision'][r.binding(0)]
        before_creations=len(r.creations);before_scheduled=list(r.scheduled)
        before_count=r.state_call('targetCount')
        r.units[old]['alive']=False;r.event_target=old;r.invoke('tdTrialOnTargetDeath')
        require(r.slots[0]==0 and r.state_call('targetCount')==before_count-1
                and len(r.creations)==before_creations and r.scheduled==before_scheduled,
                'Actual death refilled/scheduled replenishment instead of leaving one vacant slot')
        replacement=r.adversarial_rebind(0,reused=reused)
        r.units[replacement].update(x=100.,y=0.)
        require((replacement==old)==reused and r.globals['TDTrialBinding_revision'][r.binding(0)]!=old_revision,
                                        'Controlled registry fixture did not change the captured identity')
        r.visible_units=[replacement,*original[1:]];r.auto_post=True;r.finish(4.)
        require(len(r.native_damage)==16 and all(hit[1]!=replacement for hit in r.native_damage),
                                        'Delayed meteor admitted a trial replacement or lost old neighbours')
        result['trial_registry_reused_handle' if reused else 'trial_registry_new_handle']={'old_hits':16,'adversary_hits':0,'production_death_refilled':False,'setup':'controlled low-level registry adversary'}
    for reset in (False,True):
        r=ElementRuntime(script);r.enter(8);pet=r.pet(33)
        original=[r.target(index) for index in range(5)]
        for target in original:r.units[target].update(x=100.,y=0.)
        r.visible_units=original[:];r.emit(100.,target=original[0])
        generation=r.state_call('getGeneration')
        if reset:
            r.invoke('tdStartGame')
            for lane in range(4):r.invoke('tdSetLaneActive',lane,True)
            r.enter(24)
            require(r.state_call('getGeneration')>generation and r.state_call('getRound')==2,
                    'Actual reset did not create a new trial generation/round')
            r.visible_units=[r.target(index) for index in range(5)]
            for target in r.visible_units:r.units[target].update(x=100.,y=0.)
        else:
            r.invoke('tdTrialClearTargets')
            require(r.state_call('targetCount')==0,'Actual clear retained trial identities')
        r.finish(4.)
        require(not r.native_damage and r.invoke('tdPetEffectTaskCount')==0 and not r.visual_handles,
                'Cleared/reset trial warning damaged a new identity or retained its context/visuals')
        result['trial_real_reset_new_round' if reset else 'trial_real_clear']={
            'damage':0,'owned_tasks':0,'visuals':0,'package_globals_reinitialized':False}
    # Optional visuals cannot authorize or suppress an actual effect.
    r=ElementRuntime(script);r.reject_visual=True;pet=r.pet(32);r.visible_units=[102]
    r.emit(100.);r.finish(.4)
    require(len(r.native_damage)==1 and r.native_damage[0][2]==140. and not r.visual_handles,
                                    'Rejected visuals changed spell damage or leaked a handle')
    result['visual_native_rejection']={'damage':140.,'visual_handles':0}
    # Generation changes and terminal cancellation reclaim the same owned context.
    for terminal in (False,True):
        r=ElementRuntime(script);pet=r.pet(34)
        for target in range(102,106):r.enemy(target)
        r.visible_units=list(range(102,106));r.emit(100.)
        require(r.visual_handles,'Context did not own the initial mark visuals')
        if terminal:r.invoke('tdSetGameOver',True);r.tick()
        else:r.invoke('TDPet_invalidateCombat',pet)
        require(r.invoke('tdPetEffectTaskCount')==0 and not r.visual_handles
                                        and not r.tables[r.globals['TDPetCastContext_tdPetActiveCastIndex']],
                                        'Source/terminal cancellation retained a context or its owned visuals')
        require(not r.native_damage,'Cancelled warning emitted later damage')
        result['gameover_cancellation' if terminal else 'source_invalidation']={'tasks':0,'visuals':0,'damage':0}
    # Two seals weaken by max and cancel independently; tagged spell consumes Boss factor once.
    r=ElementRuntime(script);first=r.pet(37)
    r.units[106]={**r.units[101],'abilities':{},'inventory':{}}
    second=r.pet(37);r.globals['TDPet_host'][second]=106
    r.enemy(102);r.units[102].update(type=rawcode('uB32'),userdata=3200,wave=32)
    r.invoke('tdSetupEnemyMechanics');r.invoke('tdEnemyMechanicRegister',102,0,32,3)
    require(r.invoke('tdEnemyMechanicIsRegistered',102),'Real Boss state was not registered')
    r.visible_units=[102];r.emit(1.);r.emit(1.,source=106);r.tick()
    near(r.invoke('tdEnemyMechanicScaleSpellDamage',102,100.),66.4,'Two stage seals do not stack')
    r.invoke('TDPet_invalidateCombat',first)
    near(r.invoke('tdEnemyMechanicScaleSpellDamage',102,100.),66.4,'Cancelling one source preserves another')
    near(r.invoke('tdAuraEnemySpeedFactor',102),.925,'Remaining Boss slow is exactly half15%')
    r.invoke('tdPetSpellDamage',second,106,1,102,100.);r.drain_zero()
    require(len(r.native_damage)==1,'Tagged Boss spell count changed')
    near(r.native_damage[0][2],66.4,'Boss factor must be consumed exactly once')
    r.invoke('TDPet_invalidateCombat',second)
    near(r.invoke('tdEnemyMechanicScaleSpellDamage',102,100.),58.,'All stage seal sources removed')
    near(r.invoke('tdAuraEnemySpeedFactor',102),1.,'All owned slows removed')
    result['two_stage_seal_sources_boss_once']={'with_two':66.4,'with_one':66.4,'with_none':58.,'tagged_hit':66.4}
    # Execute the existing half-second lifecycle callback inside an actual popped
    # damage packet, then retry it after that packet returns. No predicate stub.
    r=ElementRuntime(script)
    r.globals.update(EVENT_PLAYER_UNIT_PICKUP_ITEM=18,bj_MAX_PLAYER_SLOTS=16)
    r.invoke('tdPetSetupRuntime')
    r.cleanup_cb=next(cb for interval,cb in r.periodics if interval==.5)
    r.cleanup_pet=r.pet(19)
    r.invoke('TDPet_setSkill',r.cleanup_pet,3 if r.four_slot_contract else 0,11,1)
    r.invoke('TDPet_setSkill',r.cleanup_pet,1,16,1)
    require(r.invoke('TDPet_skillAt',r.cleanup_pet,3 if r.four_slot_contract else 0)==11 and r.invoke('TDPet_skillAt',r.cleanup_pet,1)==16,
                                    'Terminal fixture did not have a legal active-plus-passive layout')
    r.globals['TDPet_readyAt'][r.cleanup_pet]=1000.;r.roll=0.;r.terminal_in_hit=True
    r.emit(100.)
    require(r.terminal_on_stack['busy'] and not r.terminal_on_stack['destroy_allowed']
                                    and all(r.terminal_on_stack[k]!=0 for k in ('pet_type','callback_type','records')),
                                    'Half-second terminal callback destroyed records/current callback on the packet stack')
    near(r.globals['TDPet_readyAt'][r.cleanup_pet],1000.,'Terminal retry must not reset CD')
    require(not r.invoke('tdPetAttackQueueBusy') and r.invoke('tdPetCanDestroyMatchRecords'),
                                    'Packet return failed to release the terminal busy fence')
    r.invoke('call_doPeriodically_TDPetRuntime',r.cleanup_cb,r.cleanup_cb)
    require(r.globals['TDPet_typeId'][r.cleanup_pet]==0 and r.globals['TDPetState_tdPetMatchRecords']==0
                                    and r.globals['CallbackPeriodic_typeId'][r.cleanup_cb]==0,
                                    'Existing half-second callback did not retry and destroy after ownership completion')
    cleanup_timer=r.globals['CallbackPeriodic_t'][r.cleanup_cb]
    require(r.timers[cleanup_timer]['destroyed'],'Terminal watcher native timer was not released')
    scheduler=r.periodic_callbacks('TDPetEffectScheduler')[0]
    scheduler_timer=r.globals['CallbackPeriodic_t'][scheduler]
    r.tick()
    require(r.globals['CallbackPeriodic_typeId'][scheduler]==0 and r.timers[scheduler_timer]['destroyed'],
                                    'Shared scheduler did not release its terminal periodic callback/timer exactly once')
    result['existing_terminal_retry']={'in_packet_busy':True,'records_preserved_on_stack':True,
                    'after_return_destroy_allowed':True,'retry_records_destroyed':True,'watcher_timer_released':True,
                    'scheduler_timer_released':True,'cooldown_unchanged_before_record_destruction':1000.}

    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('map',type=Path);p.add_argument('--negative-only',action='store_true');p.add_argument('--report',type=Path);args=p.parse_args()
    script=Mpq(args.map.read_bytes()).extract('war3map.j').decode('utf-8')
    report={'sha256':hashlib.sha256(args.map.read_bytes()).hexdigest(),'twenty':[] if args.negative_only else verify_twenty(script),'negative':verify_negatives(script),
                                    'boundary':__doc__}
    output=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.report:args.report.write_text(output,encoding='utf-8')
    print(output,end='')
if __name__=='__main__':main()
