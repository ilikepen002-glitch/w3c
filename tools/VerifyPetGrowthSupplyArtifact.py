"""Replay actual packed milestone credits; native game timing/UI are not simulated."""
import argparse, hashlib, json, re
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyPetAttackArtifact import PetAttackRuntime
from VerifyEquipmentAbilityArtifact import require
from VerifyGlobalRankingsArtifact import members

PREFIX = 'TDPetState_'
LIMIT = 2147483647

def fixture(script):
    r = PetAttackRuntime(script)
    r.invoke('tdPetInitializeLane', 0)
    r.invoke('tdSetLaneActive', 0, True)
    return r

def counts(r, lane):
    return [r.globals[PREFIX+n][lane] for n in ('tdPetSlotStones', 'tdPetRerollStones', 'tdPetBalls')]

def credit(r, lane, wave):
    r.invoke('tdMarkWaveResolved', lane, wave)
    r.invoke('tdPetCreditWave', lane, wave)

def verify(script):
    r = fixture(script)
    rows = []
    for lane in range(4):
        r.invoke('tdPetInitializeLane', lane); r.invoke('tdSetLaneActive', lane, True)
    r.invoke('tdSetGlobalWave', 32)
    for wave in range(1, 33):
        for lane in range(4):
            credit(r, lane, wave); r.invoke('tdPetCreditWave', lane, wave)
            expected = [sum(w <= wave for w in (4,12)), 2*sum(w <= wave for w in (4,12,20,28)), 3+6*sum(w <= wave for w in (4,8,13,19))]
            require(counts(r,lane) == expected, 'Milestone schedule or duplicate credit mismatch')
        if wave in (4,12,20,28): rows.append({'wave':wave,'perLane':counts(r,0)})
    for lane in range(4):
        r.globals[PREFIX+'tdPetSlotStones'][lane] = 0
        r.globals[PREFIX+'tdPetRerollStones'][lane] = 0
        r.invoke('tdPetCreditWave',lane,4)
        require(counts(r,lane)[:2] == [0,0], 'Spent supplies credited twice')
    for mode in ('unresolved','inactive','defeated','finished','left','gameover'):
        r = fixture(script)
        if mode != 'unresolved': r.invoke('tdMarkWaveResolved',0,4)
        if mode == 'inactive': r.invoke('tdSetLaneActive',0,False)
        elif mode == 'defeated': r.invoke('tdSetLaneDefeated',0,True)
        elif mode == 'finished': r.invoke('tdSetLaneFinished',0,True)
        elif mode == 'left': r.invoke('tdPetMarkPlayerLeft',0)
        elif mode == 'gameover': r.invoke('tdSetGameOver',True)
        before=counts(r,0);r.invoke('tdPetCreditWave',0,4)
        require(counts(r,0)==before, 'Closed/unresolved lane received supplies: '+mode)
    r=fixture(script);r.invoke('tdSetGlobalWave',30)
    credit(r,0,12);credit(r,0,4)
    require(counts(r,0)==[2,4,9], 'Late resolved wave reward lost')
    r=fixture(script)
    r.globals[PREFIX+'tdPetSlotStones'][0]=LIMIT
    r.globals[PREFIX+'tdPetRerollStones'][0]=LIMIT-1
    credit(r,0,4)
    require(counts(r,0)==[LIMIT,LIMIT,9], 'Material saturation or ball independence failed')
    r=fixture(script);r.globals[PREFIX+'tdPetBalls'][0]=60
    r.globals[PREFIX+'tdPetSlotStones'][0]=-1
    credit(r,0,4)
    require(counts(r,0)==[-1,2,60], 'Invalid/full material damaged other reward')
    before=counts(r,0)
    for lane,wave in [(-1,4),(4,4),(0,-1),(0,0),(0,33)]: r.invoke('tdPetCreditWave',lane,wave)
    require(counts(r,0)==before,'Invalid event changed inventories')
    return {'milestones':rows,'lanes':4,'all32Waves':True,'idempotent':True,'delayedResolution':True,
            'closedStates':6,'saturation':True,'independentResources':True,'invalidEvents':5}

def change_body(script,name,old,new):
    pattern=r'(?ms)^function '+re.escape(name)+r' takes .*?\n(.*?)^endfunction'
    m=re.search(pattern,script);require(m is not None,'Missing mutation function')
    body=m.group(1);require(body.count(old)==1,'Mutation anchor not exact '+name)
    return script[:m.start(1)]+body.replace(old,new,1)+script[m.end(1):]

def main():
    p=argparse.ArgumentParser();p.add_argument('map',type=Path);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=a.map.read_bytes();script=Mpq(data).extract('war3map.j').decode();report={'status':'PASS','mapSHA256':hashlib.sha256(data).hexdigest(),'coverage':verify(script)}
    mutations=[('wrong-reroll-count',change_body(script,'tdPetStageRerollStoneReward','set cond_result = 2','set cond_result = 3'),'schedule'),
      ('duplicate-award',change_body(script,'tdPetCreditWave','set TDPetState_tdPetWaveCredited[key_1] = true','set TDPetState_tdPetWaveCredited[key_1] = false'),'duplicate'),
      ('unresolved-award',change_body(script,'tdPetCreditWave',' or ( not tdIsWaveResolved(lane_3, wave_9))',''),'unresolved')]
    report['mutations']=[]
    for name,mutated,reason in mutations:
        try: verify(mutated)
        except ValueError as e:
            require(reason in str(e),'Mutation failed for unrelated reason '+str(e));report['mutations'].append({'name':name,'rejected':True,'reason':str(e)})
        else: raise ValueError('Mutation escaped '+name)
    current,baseline=members(Mpq(data)),members(Mpq(a.baseline.read_bytes()))
    require(current.keys()==baseline.keys(),'Growth supplies changed archive membership')
    changed=[k for k in current if current[k][1]!=baseline[k][1]]
    require(set(changed)<={'war3map.j','war3map.w3i'},'Unexpected resource/object mutation '+str(changed))
    report['changedMembers']=sorted(changed);report['boundary']='Actual packed JASS, controlled native handles/UI. Native play timing, renderer and FPS untested.'
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
