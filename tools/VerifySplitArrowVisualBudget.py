#!/usr/bin/env python3
"""Full-arrow source and packed JASS gate. Native rendering/clock are modeled, not FPS."""
from pathlib import Path
import argparse, json, subprocess
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyCombatVisualArtifact import VisualRuntime
from VerifyLocalCombatHotpathArtifact import split_traces, archive_delta, CountedRuntime, shot_trace
from VerifyTowerTargetPriorityArtifact import register_actual_split_listener
from VerifyBuilderControlDelta import allocations

ROOT = Path(__file__).resolve().parents[1]
PATH = 'wurst/towers/TDTowerRuntime.wurst'

def source_gate():
    source = (ROOT / PATH).read_text()
    prior = subprocess.check_output(['git','show','d08fb2db50c2325722de41efa7500fe6272f7902:'+PATH],cwd=ROOT,text=True)
    require(source.split('// Every selected extra shot')[0] == prior.split('// The shared recycler')[0].replace('import GameTimer\n',''), 'Unrelated leading gameplay changed')
    require(source.split('function tdFindFarthestArcherSplitArrowShot')[1] == prior.split('function tdFindFarthestArcherSplitArrowShot')[1], 'Target/damage/flight gameplay changed')
    launch = source.split('function tdLaunchArcherSplitArrowVisual',1)[1].split('function tdFindFarthest',1)[0]
    before_alloc = launch.split('tdArcherArrowVisuals.add(new TDArcherArrowVisual')[0]
    require(before_alloc.count('if ') == 1 and 'source == null or target == null' in before_alloc, 'Launch admission must only reject null handles')
    require('tdArcherVisualBudget' not in source and 'tdArcherVisualCreation' not in source and 'TD_ARCHER_VISUAL_' not in source, 'Old admission counters remain')
    require(launch.count('doPeriodically(')==1, 'Multiple timer owners')
    require('arrow.epoch != tdFlowEpoch()' in launch and 'destroy arrow' in launch and 'destroy cb' in launch, 'Cleanup contract missing')

def full_visuals(script, cancel=False, reject=False):
    r = VisualRuntime(script)
    # Bounded interpreter guard, not a Warcraft operation/FPS claim.
    r.per_call_step_limit = 100000
    r.reject_visual = reject
    r.units[101].update(x=0.,y=0.)
    r.units[102].update(x=500.,y=0.)
    array, owner = allocations(script)['alloc_CallbackPeriodic_doPeriodically_TDTowerRuntime']
    def count(): return len(r.lists[r.globals['TDTowerRuntime_tdArcherArrowVisuals']])
    def tick():
        r.now += .03
        active = [cb for interval,cb in r.periodics if interval==.03 and r.globals[array][cb]==owner]
        require(len(active)<=1,'Duplicate shared arrow timers')
        for cb in active:
            r.executed_steps=0
            r.invoke('call_doPeriodically_TDTowerRuntime', cb, cb)
        r.deliver_due_fx_recycle()
    # Forty towers, seven equipment-enhanced side arrows, roughly 11 attacks/sec.
    # All waves overlap a 0.6s flight, far above both former limits and warm pool.
    attempts = 0
    peak = 0
    waves, towers = (1, 1) if cancel or reject else (4, 40)
    for wave in range(waves):
        for tower in range(towers):
            handle=101 if tower==0 else 2000+tower
            if handle not in r.units:r.units[handle]=dict(r.units[101])
            for arrow in range(7):
                r.executed_steps=0
                r.invoke('tdLaunchArcherSplitArrowVisual',handle,102,.6)
                attempts+=1
        require(count()==attempts,'A selected arrow was hidden')
        peak=max(peak,count())
        for _ in range(3):tick()
    require(attempts==waves*towers*7 and peak==attempts,'Pressure fixture incomplete')
    require(len(r.visual_history)==attempts,'Arrow/effect attempt not one to one')
    require(len(r.visual_handles)==(0 if reject else attempts),'Live effects missing')
    if cancel:
        r.invoke('tdResetWaveFlowState')
        tick()
        require(count()==0,'Epoch cancellation did not clean on first tick')
    for _ in range(25):tick()
    require(count()==0 and not r.visual_handles,'Arrow/effect leak')
    require(not r.globals['TDTowerRuntime_tdArcherVisualTimerRunning'],'Shared timer retained')
    r.flush_fx_recycle()
    require(r.fx_pool_size()==48,'Recycler did not return to warm pool')
    result = dict(attempts=attempts,peak=peak,cancel=cancel,native_effect_failure=reject,cleanup=True)
    print(json.dumps(result), flush=True)
    return result

def combat(script):
    r=CountedRuntime(script)
    for i in range(1000,1010):r.enemy(i,life=10000.,x=400.)
    r.visible_units=list(range(1000,1010))
    volley=r.invoke('tdCreateArcherSplitArrowVolley',101,1000)
    trace=shot_trace(r,volley)
    require(len(r.split_visual_launches)==len(trace['shots'])==6,'Selected shot/launch count mismatch')
    for launch,shot in zip(r.split_visual_launches,trace['shots']):
        require(launch[:3]==(101,shot['TDArcherSplitArrowShot_target'],shot['TDArcherSplitArrowShot_flightTime']),'Launch target/flight differs from damage shot')
    r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']].append(volley)
    register_actual_split_listener(r);r.emit(100.,target=1000);r.flush()
    require(len(r.native_damage)==6,'Shot damage count mismatch')
    return dict(shots=6,launches=6,damage_events=6)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('map',nargs='?',type=Path);p.add_argument('--baseline',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    source_gate();report=dict(source='PASS')
    if a.map:
        script=Mpq(a.map.read_bytes()).extract('war3map.j').decode('utf8')
        report['visuals']=[full_visuals(script,cancel,reject) for cancel,reject in ((False,False),(True,False),(False,True))]
        report['combat']=combat(script)
        if a.baseline:
            prior=Mpq(a.baseline.read_bytes()).extract('war3map.j').decode('utf8')
            require(split_traces(prior)==split_traces(script),'Damage/selection/flight traces changed')
            report['damage_trace']='IDENTICAL';report['strict_mpq']=archive_delta(a.baseline,a.map)
    report['status']='PASS'
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
