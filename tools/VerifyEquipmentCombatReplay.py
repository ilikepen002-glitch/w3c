#!/usr/bin/env python3
"""Execute actual packed equipment JASS rules with explicit native boundaries.
No Warcraft launch or claim that a dummy order really stuns/displays a Buff.
"""
from pathlib import Path
import argparse
import json
import math
import hashlib
import sys
from GenerateTowerTerrainMask import Mpq
from VerifyPureBossArtifact import PureBossJassRuntime
from VerifyTrialReplay import TrialJassRuntime
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerUpgradeArtifact import rawcode

class MathBoundary:
    def native(self, name, args):
        if name in ('RMaxBJ','IMaxBJ'): return True,max(args[:2])
        if name in ('RMinBJ','IMinBJ'): return True,min(args[:2])
        return super().native(name,args)

class EquipmentRulesRuntime(MathBoundary, PureBossJassRuntime): pass
class EquipmentTrialRuntime(MathBoundary, TrialJassRuntime):
    def native(self, name, args):
        if name in ('UnitAddAbility','unit_addAbility') and getattr(self,'reject_carrier',None)==args[1]:
            return True,False
        if name == 'group_enumUnitsInRange' and hasattr(self, 'visible_units'):
            self.groups[args[0]] = list(self.visible_units); return True,None
        return super().native(name,args)

def close(actual,expected,label):
    require(math.isclose(actual,expected,abs_tol=1e-6,rel_tol=1e-6),f'{label}: {actual}, expected {expected}')

def verify_rules(script):
    r=EquipmentRulesRuntime(script)
    aura=r.invoke('new_TDAuraAggregate')
    offer=lambda identity,rank,power,covered:r.invoke('TDAuraAggregate_offer',aura,identity,rank,power,covered)
    offer(10,2,.30,False);offer(10,1,.18,True)
    require(r.invoke('TDAuraAggregate_rank',aura,10)==1,'Out-of-range stronger rank swallowed wider weak source')
    offer(14 if 'TDAuraRules_TD_AURA_PET_REDUCE' in r.globals else 9,1,.12,True);offer(7,2,.10,True)
    close(r.invoke('TDAuraAggregate_enemySlowPower',aura),.40,'Additive identities')
    close(r.invoke('tdCombinedEnemySlowFactor',.40),.60,'40% combined factor')
    offer(10,2,.216,True);offer(10,1,.50,True)
    close(r.invoke('TDAuraAggregate_power',aura,10),.216,'Higher rank wins before power')
    r.invoke('TDAuraAggregate_clearIdentity',aura,10);offer(10,1,.18,True)
    close(r.invoke('TDAuraAggregate_power',aura,14 if 'TDAuraRules_TD_AURA_PET_REDUCE' in r.globals else 9),.12,'Other identity survived downgrade')
    close(r.invoke('tdCombinedEnemySlowFactor',.90),.25,'75% global cap')
    require(r.invoke('tdAuraCarrierRepairNeeded',4,4,False),'Missing same-rank carrier cannot repair')
    require(r.invoke('tdAuraConfirmedAppliedRank',4,False)==0,'Failed carrier was shown as applied')
    close(r.invoke('tdFinalCooldownReduction',.10,.12,.18),.40,'Shared CD cap')
    require(not r.invoke('tdAuraCooldownTargetSupported',False,False,False),'Unsupported target displayed CD')
    require(r.invoke('tdAuraCooldownTargetSupported',False,True,True),'Valid unlocked pet active did not qualify')
    require(r.invoke('tdAuraCooldownTargetSupported',True,False,False),'Native active did not qualify')
    require(not r.invoke('tdAuraCooldownTargetSupported',False,False,True),'Unbound pet active qualified')
    require(not r.invoke('tdAuraCooldownTargetSupported',False,True,False),'Locked pet active qualified')
    war=r.invoke('new_TDWarIntentState')
    for at in (0.,.1,.2): require(not r.invoke('TDWarIntentState_hit',war,100,at),'Premature war burst')
    require(r.invoke('TDWarIntentState_hit',war,100,.3),'Fourth hit did not burst')
    close(r.globals['TDWarIntentState_burstUntil'][war],3.3,'Fixed war end')
    r.invoke('TDWarIntentState_hit',war,100,1.0)
    close(r.globals['TDWarIntentState_burstUntil'][war],3.3,'War burst incorrectly refreshed')
    r.invoke('TDWarIntentState_hit',war,101,1.1)
    require(r.invoke('TDWarIntentState_stage',war,1.1)==1,'Target switch did not clear war burst')
    poison=r.invoke('new_TDPoisonBurstState')
    require(not r.invoke('TDPoisonBurstState_hit',poison,100,1.0),'Poison first')
    require(not r.invoke('TDPoisonBurstState_hit',poison,100,1.1),'Poison second')
    r.invoke('TDPoisonBurstState_tick',poison,4.1)
    require(r.globals['TDPoisonBurstState_stack'][poison]==0,'Exact deadline poison timeout failed')
    for at in (5.0,5.1): r.invoke('TDPoisonBurstState_hit',poison,100,at)
    require(r.invoke('TDPoisonBurstState_hit',poison,100,5.2),'Third poison did not trigger')
    require(r.globals['TDPoisonBurstState_stack'][poison]==0,'Poison layer not cleared before proc')
    corpse=r.invoke('new_TDCorpseBurstState')
    for _ in range(5): require(not r.invoke('TDCorpseBurstState_hit',corpse),'Premature corpse proc')
    require(r.invoke('TDCorpseBurstState_hit',corpse),'Sixth total attack did not proc')
    window=r.invoke('new_TDShieldWindow')
    previous=r.invoke('TDShieldWindow_reserve',window,0.,False,.4)
    close(r.globals['TDShieldWindow_readyAt'][window],1.52,'Shield .84 stun+.60 protection+.08 margin')
    require(r.invoke('TDShieldWindow_reserve',window,.5,False,.4)==-1.,'Shared shield window reentered')
    r.invoke('TDShieldWindow_rollback',window,previous)
    close(r.globals['TDShieldWindow_readyAt'][window],0.,'Cast failure did not roll back')
    r.invoke('TDShieldWindow_reserve',window,1.,True,.6)
    close(r.globals['TDShieldWindow_readyAt'][window],3.08,'Boss separate shield window')
    close(r.invoke('tdShieldStunDuration',False,.6),.90,'Normal stun cap')
    close(r.invoke('tdShieldStunDuration',True,.6),.25,'Boss fixed stun')
    return {'actual_packed_rules':True,'aura_identity_cases':12,'war_poison_corpse_cases':12,'shield_window_cases':6,
            'boundary':'Pure/compiled JASS state and kernel math; no native percentage/Buff/stun projection emulated'}

def verify_aura_apply(script):
    r=EquipmentTrialRuntime(script);r.initialize_match();r.enter(8);target=r.target(0)
    carrier=r.invoke('tdAuraRankCarrier',12,1)
    require(carrier != 0,'Actual source Buff carrier metadata uninitialized')
    r.reject_carrier=carrier
    r.invoke('tdEnemySlowOfferTimed',target,101,12,1,.08,3.)
    record=r.invoke('tdAuraTargetFor',target)
    rank=lambda:r.invoke('TDAuraAggregate_rank',r.globals['TDAuraTarget_effective'][record],12)
    require(rank()==0,'Failed native add still published effect')
    require(r.invoke('TDAuraTarget_shownRanks_get',record,12)==0,'Failed native add was shown')
    require(r.invoke('TDAuraTarget_pendingApplications_get',record,12),'Failed native add lost retry state')
    r.reject_carrier=None;r.invoke('tdEnemySlowRefreshTimed',target)
    require(rank()==1 and carrier in r.units[target]['abilities'],'Next round did not repair missing carrier')
    close(r.units[target]['speed'],239.2,'Source Buff effect shared slow state')
    r.units[target]['abilities'].pop(carrier);r.invoke('tdEnemySlowRefreshTimed',target)
    require(carrier in r.units[target]['abilities'],'Same shown rank could not repair missing real carrier')
    r.invoke('tdEnemySlowOfferTimed',target,101,13,1,.16,1.)
    close(r.units[target]['speed'],197.6,'Different timed identities added')
    r.now+=1.;r.invoke('tdEnemySlowRefreshTimed',target)
    close(r.units[target]['speed'],239.2,'Independent short expiry removed another valid identity')
    r.now+=2.;r.invoke('tdEnemySlowRefreshTimed',target)
    close(r.units[target]['speed'],260.,'Final slow expiry did not restore trial base')
    r.invoke('tdForgetAuraTarget',target)
    require(r.invoke('tdAuraTargetFor',target)==0,'Actual explicit cleanup retained registry record')
    return {'actual_carrier_failure_retry_same_rank_repair':True,'identity_expiries_independent':True,
            'speed_sequence':[260.,239.2,197.6,239.2,260.],
            'boundary':'UnitAddAbility and native handle storage modeled; does not prove status bar projection or native aura percentage engine semantics'}

def prepare_proc(script, item='iP04', ordinary=False):
    r=EquipmentTrialRuntime(script);r.initialize_match();r.enter(8)
    tower = 'uG6B' if item=='iP04' else 'uD6B'
    r.units[101].update(type=rawcode(tower),owner=0,lane=0,inventory={0:4242},abilities={})
    r.inventory_items[4242]=rawcode(item)
    targets=[r.target(i) for i in range(5)]
    for target in targets:r.units[target].update(x=0.,y=0.)
    target = 102 if ordinary else targets[0]
    r.units[target].update(x=0.,y=0.,userdata=0)
    r.invoke('tdSetupEquipmentSpecialRuntime')
    initial=len(r.scheduled)
    for _ in range(6 if item=='iP04' else 3): r.emit(100.0,source=101,target=target)
    require(r.calls['tdCaptureEquipmentSpecialMainAttack']>=3,'Actual special listener not reached')
    require(len(r.scheduled)>initial,'Actual main attacks did not queue proc')
    return r,target,targets,r.scheduled[-1][1]

def verify_new_aoe(script):
    cases=[]
    for item in ('iP04','iP05'):
        r,primary,original,callback=prepare_proc(script,item)
        r.run_timer(callback)
        require(len(r.native_damage)==4,'Actual proc did not enforce four-victim cap')
        require(r.native_damage[0][1]==primary,'Live primary was not first')
        for hit in r.native_damage:close(hit[2],50.,'One 50% event segment, no trial Boss scaling')
        require(len(r.scheduled)==2,'Code damage recursively queued another special proc')
        cases.append({'item':item,'native_main_hits':6 if item=='iP04' else 3,'live_victims':4,'primary_first':True})
        # Kill the primary through the actual trial lifecycle, refill its slot,
        # then run the ORIGINAL timer. Old neighbours remain valid, new slot does not.
        r,primary,original,callback=prepare_proc(script,item)
        r.units[primary]['alive']=False;r.event_target=primary;r.invoke('tdTrialOnTargetDeath')
        death=r.scheduled[-1][1];r.run_timer(death)
        replacement=r.target(0);r.units[replacement].update(x=0.,y=0.)
        require(replacement not in original,'Death fixture did not replace the handle')
        r.run_timer(callback)
        victims=[hit[1] for hit in r.native_damage]
        require(len(victims)==4 and set(victims)==set(original[1:]),'Lethal primary swallowed old neighbours or damaged replacement')
        cases.append({'item':item,'dead_primary_neighbours':4,'new_same_slot_damage':0})
        r,primary,original,callback=prepare_proc(script,item)
        old_neighbour=original[1]
        r.units[old_neighbour]['alive']=False;r.event_target=old_neighbour;r.invoke('tdTrialOnTargetDeath')
        # The native allocator may reuse a retired handle. Production revision
        # guards must reject it even when pointer equality alone would match.
        r.unit_serial=old_neighbour-1;r.run_timer(r.scheduled[-1][1])
        require(r.target(1)==old_neighbour,'Native handle-reuse fixture did not reuse the exact value')
        r.units[old_neighbour].update(x=0.,y=0.);r.run_timer(callback)
        victims=[hit[1] for hit in r.native_damage]
        require(old_neighbour not in victims and len(victims)==4,'Captured old revision damaged reused native handle')
        cases.append({'item':item,'reused_handle_new_revision_damage':0,'original_other_victims':4})
        r,primary,original,callback=prepare_proc(script,item)
        r.now=r.state_call('getDeadline');r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer'])
        r.enter(24);r.run_timer(callback)
        require(not r.native_damage,'Old trial proc damaged subsequent epoch/round')
        cases.append({'item':item,'old_epoch_new_round_damage':0})
    r,primary,original,callback=prepare_proc(script,ordinary=True)
    r.visible_units=[primary,*original]
    r.run_timer(callback)
    require(len(r.native_damage)==1 and r.native_damage[0][1]==primary,'Ordinary-origin AoE leaked into trial targets')
    cases.append({'ordinary_origin_trial_damage':0,'ordinary_primary_damage':50})
    return {'actual_main_attack_listener_and_captured_timers':True,'cases':cases,
            'boundary':'Native unit/clock/damage callbacks and enumerated handles are bounded recorded stubs; guards/capture/victim revisions execute actual packed JASS; native armor/visuals not emulated'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('map',type=Path);p.add_argument('--output',type=Path);args=p.parse_args()
    data=args.map.read_bytes();script=Mpq(data).extract('war3map.j').decode('utf-8')
    report={'rules':verify_rules(script),'aura_application':verify_aura_apply(script),'new_aoe':verify_new_aoe(script)}
    report.update(status='PASS',map_sha256=hashlib.sha256(data).hexdigest(),jass_sha256=hashlib.sha256(script.encode()).hexdigest(),tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),command=sys.argv)
    if args.output:args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
