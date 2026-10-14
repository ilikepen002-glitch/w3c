#!/usr/bin/env python3
"""Packed elemental VFX calls, battle-trace equivalence and real Fx recycler execution.
Clock, engine unit setters, collection primitives, flat terrain/world bounds and native
art/lightning handles are recorded boundaries. No Warcraft picture, blending or FPS claim.
"""
from pathlib import Path
import argparse,hashlib,json
from GenerateTowerTerrainMask import Mpq
from VerifyElementalPetArtifact import ElementRuntime,EXPECTED
from VerifyEquipmentAbilityArtifact import require
from SpiritVisualBudgetFixture import saturate, release

class VfxRuntime(ElementRuntime):
    def __init__(self,script):
        self.phase_stack=[];self.visual_events=[];self.visual_calls=[]
        super().__init__(script)
        self.visual_events.clear();self.visual_calls.clear()
    def execute_call(self,name,args):
        phase=name.startswith('TDPetCastContext_visual')
        if phase:
            self.phase_stack.append(name)
            self.visual_calls.append({'time':round(self.now,6),'method':name,'args':list(args)})
        try:return super().execute_call(name,args)
        finally:
            if phase:self.phase_stack.pop()
    def native(self,name,args):
        if name in ('AddSpecialEffect','AddSpecialEffectTarget','AddLightningEx','MoveLightningEx','DestroyEffect','DestroyLightning') or name.startswith('SetUnit') and args and args[0] in getattr(self,'effect_dummies',{}):
            self.visual_events.append({'time':round(self.now,6),'phase':self.phase_stack[-1] if self.phase_stack else 'shared','phases':list(self.phase_stack),
                                      'native':name,'args':list(args)})
        return super().native(name,args)

def moving(r):return len(r.lists[r.globals['TDCombatVisualRuntime_moving']])
def battle(r,pet):
    return {'damage':r.damage_trace,'control':r.control_orders,'cd':r.globals['TDPet_readyAt'][pet],
            'score':r.score(),'gold':dict(r.player_resources),'random':r.random_trace,
            'life':[(t,r.units[t]['life']) for t in range(102,117)]}

def run(script,skill,mode='normal'):
    r=VfxRuntime(script);pet=r.pet(skill);start=r.now
    for target in range(102,116):r.enemy(target)
    r.enemy(116,lane=1);r.visible_units=list(range(102,117))
    if mode=='null':r.reject_visual=True
    if mode=='full':
        # Preserve the true128 shared ceiling while filling the reserved
        # core40/decoration88 composition through matching production APIs.
        held=saturate(r,128)
        require(r.invoke('tdCombatVisualShortCount')==128,'Shared visual saturation setup did not reach128')
        r.now=start+1.
    else:
        # Keep styled, null/full and official baseline on the same clock.
        r.now=start+1.
    r.emit(100.);r.finish()
    require(r.invoke('tdPetEffectTaskCount')==0 and not r.visual_handles and not r.lightning_handles,
            'VFX completion leaked an active effect/line/context')
    if mode=='full':
        release(r,held)
    if 'tdCombatVisualShortCount' in r.functions:
        require(r.invoke('tdCombatVisualShortCount')==0 and moving(r)==0,'Shared VFX budget did not return to zero')
    return r,battle(r,pet)

def actual_stages(r,skill):
    events=r.visual_events
    marked=lambda event,key:any(key in phase for phase in event['phases'])
    finish=[e for e in r.visual_calls if 'visualFinish' in e['method']]
    require(not any('visualFinish' in e['phase'] and e['native'].startswith('Add') for e in events),
            'Completion still created immediately-destroyed replacement art')
    require(finish,'Skill lacks actual normal finish invocation '+str(skill))
    tick_adds=[e for e in events if marked(e,'visualTick') and e['native'].startswith('Add')]
    if skill==37:
        ticks=sorted({e['time'] for e in tick_adds})
        require(all(b-a>=.95 for a,b in zip(ticks,ticks[1:])),'Seal lost low-frequency breathing')
    else:require(not tick_adds,'Motion allocated native art every .05 tick')
    hit_times={round(e[0],6) for e in r.damage_trace}
    immediate={19:'visualInstantLine',20:'visualStrike',21:'visualSwordCut',23:'visualStrike',27:'visualStrike',
               28:'visualInstantLine',32:'visualLotus',35:'visualStrike',36:'visualRockFan'}
    if skill in immediate:
        impact=[e for e in events if marked(e,immediate[skill]) and e['native'].startswith('Add')]
        require(impact and all(e['time'] in hit_times for e in impact),'Immediate trace is not on existing damage frame '+str(skill))
    if skill==21:
        starts=[tuple(e['args'][2:4]) for e in events if marked(e,'visualSwordCut') and e['native'] in ('AddLightningEx','MoveLightningEx')]
        require(len(starts)==4 and len(set(starts))==4,'Four sword traces did not have distinct cardinal starts')
    if skill in (22,33):
        z=[item[5] for item in r.fx_history if item[1]=='SetUnitFlyHeight']
        require(z and max(z)>100 and min(z)<=0.001,'Existing warning lacks real descending Fx motion')
    if skill==24:
        edges=[e for e in events if marked(e,'visualTrace') and e['native']=='AddLightningEx']
        require(len(edges)==3,'Seed did not emit exactly3 selected weak edges')
    if skill==34:
        edges=[e for e in events if marked(e,'visualTrace') and e['native']=='AddLightningEx']
        require(len(edges)==3,'Four existing marks did not emit3 successor edges')
    # Full exact native model/position/timestamp records are retained, not merely counts.
    return {'skill':skill,'events':events,'fx_updates':r.fx_history,'hit_times':sorted(hit_times),
            'normal_finish':bool(finish),'pool_baseline':r.fx_pool_baseline,'pool_after':r.fx_pool_size()}

def compare_twenty(styled,baseline):
    records=[]
    for skill in EXPECTED:
        base,expected=run(baseline,skill)
        normal,trace=run(styled,skill)
        require(trace==expected,'Styled combat trace differs from official baseline '+str(skill))
        stages=actual_stages(normal,skill)
        for mode in ('null','full'):
            failed,actual=run(styled,skill,mode)
            require(actual==expected,'Visual '+mode+' changed combat trace '+str(skill))
        records.append(stages);print('vfx trace/fail/budget verified',skill,flush=True)
    return records

def fx_budget(script):
    r=VfxRuntime(script);start=r.now
    require(r.fx_pool_baseline==48,'Actual Fx/DummyRecycler constructors were not initialized')
    model='war3mapImported\\TDPetVfxSwordArray.mdx'
    serials=[r.invoke('tdCombatVisualNewSerial') for _ in range(5)]
    create=lambda serial,slot:r.invoke('tdCombatVisualCreateMoving',serial,slot,101,0,model,100.,0.,100.,0.,.75)
    for serial in serials[:4]:
        require(create(serial,0) and create(serial,1),'Two-slot cast could not allocate bounded Fx')
        require(not create(serial,0) and not create(serial,2),'Same/third slot rebuilt a moving Fx')
    require(moving(r)==8 and not create(serials[4],0),'Eight-global moving cap failed')
    art_count=len(r.visual_handles);creations=len(r.creations)
    for frame in range(100):
        r.invoke('tdCombatVisualMoveMoving',serials[0],0,100.,0.,float(frame),0.,.75)
    require(len(r.visual_handles)==art_count and len(r.creations)==creations,'Move rebuilt Fx/dummy instead of reusing it')
    r.invoke('tdCombatVisualClearMoving',serials[0])
    require(moving(r)==6 and not create(serials[4],0),'Eight-new-per-second ceiling ignored segment destruction')
    before=r.fx_pool_size()
    require(len(r.fx_recycle_pending())==2,'First segment did not schedule two owned recycle tails')
    r.now=start+.99
    require(r.deliver_due_fx_recycle()==0 and r.fx_pool_size()==before,'Fx returned before native one-second tail')
    for serial in serials[1:4]:r.invoke('tdCombatVisualClearMoving',serial)
    r.now=start+1.00
    require(r.deliver_due_fx_recycle()==2 and r.fx_pool_size()==before+2,'First group did not return at created+1')
    r.now=start+1.98
    require(r.deliver_due_fx_recycle()==0,'Second group returned before its own one-second tail')
    r.now=start+1.99
    require(r.deliver_due_fx_recycle()==6,'Second group did not return at its own created+1')
    r.flush_fx_recycle()
    require(moving(r)==0 and not r.visual_handles and r.fx_pool_size()==48,'Actual 1s callbacks failed to restore48 pool')
    require(not r.orders,'Cosmetic Fx issued a unit order')
    require(r.units[101]['x']==0. and r.units[102]['x']==0.,'Cosmetic Fx moved host/enemy')
    return {'globalFxMax':8,'perCastFxMax':2,'newFxPerSecondMax':8,'movesWithoutRebuild':100,
            'actualPoolBaseline':48,'actualPoolAfter':r.fx_pool_size(),'nativeRecycleDelay':1.,
            'physicalDummyCreations':len(r.creations),'engineBoundary':'unit setters, flat bounds and native handles'}

def independent_global_cap(script):
    r=VfxRuntime(script);start=r.now
    model='war3mapImported\\TDPetVfxSwordArray.mdx'
    serials=[r.invoke('tdCombatVisualNewSerial') for _ in range(5)]
    for serial in serials[:4]:
        for slot in (0,1):
            require(r.invoke('tdCombatVisualCreateMoving',serial,slot,101,0,model,100.,0.,100.,0.,.75),
                    'Independent global cap fixture could not fill8')
    r.now=start+1.01
    require(not r.invoke('tdCombatVisualCreateMoving',serials[4],0,101,0,model,100.,0.,100.,0.,.75),
            'Global eight-Fx cap failed after creation-rate window reset')
    for serial in serials[:4]:r.invoke('tdCombatVisualClearMoving',serial)
    r.flush_fx_recycle()
    require(r.fx_pool_size()==48,'Independent global-cap fixture leaked dummy pool')
    return {'active':8,'rateBucketReset':True,'ninthRejected':True,'poolAfter':48}

def reject_recycler_mutations(script):
    anchor='call DummyRecycler_recycle_1(Fx_dummy[this_2], 1., "when calling recycle in Fx, line 184")'
    require(script.count(anchor)==1,'Actual locked Fx destructor mutation root changed')
    results=[]
    for delay in ('0.','0.01'):
        changed=script.replace(anchor,anchor.replace(', 1.,',', '+delay+','),1)
        try:fx_budget(changed)
        except ValueError as error:
            require(str(error)=='Actual Fx recycle delay is not exactly one second',
                    'Wrong failure reason for actual recycle mutation: '+str(error))
            results.append({'delay':delay,'rejected':True,'reason':str(error)})
            continue
        raise ValueError('Early Fx recycle compiled mutation escaped '+delay)
    anchor='set TDCombatVisualData_TD_VISUAL_MOVING_LIMIT = 8'
    require(script.count(anchor)==1,'Actual global Fx limit mutation root changed')
    try:independent_global_cap(script.replace(anchor,anchor.replace('= 8','= 9'),1))
    except ValueError as error:
        require(str(error)=='Global eight-Fx cap failed after creation-rate window reset',
                'Wrong failure reason for global Fx mutation: '+str(error))
        results.append({'globalLimit':9,'rejected':True,'reason':str(error)})
    else:raise ValueError('Global Fx cap compiled mutation escaped')
    return results

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('map',type=Path);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--budget-only',action='store_true');args=p.parse_args()
    script=Mpq(args.map.read_bytes()).extract('war3map.j').decode();base=Mpq(args.baseline.read_bytes()).extract('war3map.j').decode()
    report={'status':'PASS','mapSHA256':hashlib.sha256(args.map.read_bytes()).hexdigest(),
            'baselineSHA256':hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
            'twenty':[] if args.budget_only else compare_twenty(script,base),'fxBudget':fx_budget(script),
            'globalCapIndependent':independent_global_cap(script),'compiledMutations':reject_recycler_mutations(script),'boundary':__doc__}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='twenty'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
