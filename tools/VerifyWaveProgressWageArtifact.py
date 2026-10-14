#!/usr/bin/env python3
"""Replay actual packed Game/Flow settlement and native resource sync for progress wages.

Uses the existing PetAttackRuntime JASS interpreter and its native engine boundary.
No wage/rule/claim/reward helper is stubbed, and this never starts Warcraft or Grill.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require, ability_objects
from VerifyTowerPlacementArtifact import unit_objects
from VerifyGlobalRankingsArtifact import members, normalize_info
from VerifyPetAttackArtifact import PetAttackRuntime

NODES = {1:60, 4:90, 7:120, 10:150, 13:180, 16:210, 19:240, 22:270, 25:300, 28:330, 31:360}
# Exact prefix from locked stdlib 90b45617; OrderStringFactory SHA256 676cb64baeb329dc3e806fb2f4e5665e8069899481b5361ea2dd384e49cbb87e.
CHANNEL_ORDERS = ['absorb', 'acidbomb', 'acolyteharvest', 'whirlwind', 'ambush', 'ancestralspirit', 'ancestralspirittarget', 'animatedead', 'antimagicshell', 'webon', 'weboff', 'web', 'attributemodskill', 'auraunholy', 'auravampiric', 'autodispel', 'autodispeloff', 'autodispelon', 'autoentangle', 'autoentangleinstant', 'wateryminion', 'waterelemental', 'avatar', 'avengerform', 'awaken', 'banish', 'barkskin', 'barkskinoff', 'barkskinon', 'battleroar', 'battlestations', 'bearform', 'berserk', 'blackarrow', 'blackarrowoff', 'blackarrowon', 'blight', 'blink', 'blizzard', 'bloodlust', 'bloodlustoff', 'bloodluston', 'board', 'breathoffire', 'breathoffrost', 'ward', 'burrow', 'cannibalize', 'carrionscarabs', 'carrionscarabsinstant', 'carrionscarabsoff', 'carrionscarabson', 'carrionswarm', 'chainlightning', 'channel', 'charm', 'chemicalrage', 'cloudoffog', 'clusterrockets', 'coldarrows', 'coldarrowstarg', 'controlmagic', 'corporealform', 'corrosivebreath', 'coupleinstant', 'coupletarget', 'creepanimatedead', 'creepdevour', 'creepheal', 'creephealoff', 'creephealon', 'creepthunderbolt', 'creepthunderclap', 'cripple', 'curse', 'curseoff', 'curseon', 'cyclone', 'darkconversion', 'darkportal', 'darkritual', 'darksummoning', 'deathanddecay', 'deathcoil', 'deathpact', 'windwalk', 'defend', 'detectaoe', 'detonate', 'devour', 'devourmagic', 'disassociate', 'disenchant', 'dismount', 'dispel', 'divineshield', 'doom', 'drain', 'dreadlordinferno', 'dropitem']
REWARDS = [100,100,120,180,140,150,160,340,180,240,280,240,280,340,360,580,500,700,900,920,750,350,750,1200,100,600,900,1200,200,350,700,1500]


class WageReplay(PetAttackRuntime):
    def native(self, name, args):
        # Defeat-dialog engine calls only; Game defeat/payment still executes.
        if name == 'DialogCreate': return True, 'wage-replay-dialog'
        if name in ('DialogSetMessage', 'DialogDisplay', 'TriggerRegisterDialogEvent'): return True, None
        if name in ('DialogAddQuitButton', 'DialogAddButton'): return True, 'wage-replay-quit'
        return super().native(name,args)


def fixture(script):
    r = WageReplay(script)
    r.globals['PLAYER_STATE_RESOURCE_FOOD_CAP'] = 'foodCap'
    r.invoke('tdSetGlobalWave', 32)  # Avoid unrelated next-wave scheduling.
    return r


def gold(r, lane):
    return r.invoke('tdGetGold', lane)


def start_boss(r, wave):
    r.invoke('tdFlowEnterNormal')
    require(r.invoke('tdFlowPrepareBoss', wave), 'Cannot prepare real Boss flow')
    require(r.invoke('tdFlowStartBoss', wave), 'Cannot start real Boss flow')
    for lane in range(4):
        require(r.invoke('tdFlowActivateBoss', lane, wave, r.now), 'Cannot activate real Boss flow')


def run_clear_callback(r, script, callback):
    from VerifyBuilderControlDelta import allocations
    owner=r.globals['CallbackPeriodic_typeId'][callback]
    names=[name.removeprefix('alloc_') for name,(array,identity) in allocations(script).items()
           if array=='CallbackPeriodic_typeId' and identity==owner]
    require(len(names)==1,'Clear callback allocator is not unique')
    r.invoke('call_'+names[0].removeprefix('CallbackPeriodic_'),callback,callback)


def verify(script):
    r = fixture(script)
    for wave in [-2147483648, *range(-3,70), 2147483647]:
        require(r.invoke('tdWaveProgressWage', wave) == NODES.get(wave,0), 'Exact wage table changed')
    before = [gold(r,lane) for lane in range(4)]
    totals = [0]*4
    checkpoints = []
    for wave in range(1,33):
        if wave % 8 == 0:
            start_boss(r,wave)
            for lane in range(4):
                require(r.invoke('tdFlowClaimBossResult',lane,wave,2), 'Real Boss claim missing')
        for lane in range(4):
            previous = gold(r,lane)
            r.invoke('tdHandleWaveFinished',lane,wave)
            expected = REWARDS[wave-1] + NODES.get(wave,0)
            require(gold(r,lane)-previous == expected, 'Actual settlement delta mismatch')
            require(r.invoke('tdIsWaveResolved',lane,wave), 'Wave claim missing before payment')
            r.invoke('tdHandleWaveFinished',lane,wave)
            require(gold(r,lane)-previous == expected, 'Duplicate settlement paid again')
            totals[lane] += gold(r,lane)-previous-REWARDS[wave-1]
        if wave % 8 == 0:
            checkpoints.append({'wave':wave,'wagesPerLane':totals.copy()})
    require(totals == [2310]*4, 'Four lanes share or duplicate wage entitlement')
    require([row['wagesPerLane'][0] for row in checkpoints] == [270,810,1320,2310], 'Chapter totals changed')
    require(all(gold(r,lane)-before[lane] == sum(REWARDS)+2310 for lane in range(4)), 'Original clear rewards changed')

    # Original event wave stays authoritative despite newer pending production.
    r = fixture(script)
    pending = r.invoke('tdFlowBeginSpawn',0)
    previous = gold(r,0)
    for wave in (31,7,1,4):
        r.invoke('tdHandleWaveFinished',0,wave)
        require(gold(r,0)-previous == REWARDS[wave-1]+NODES[wave], 'Delayed original wave mispriced/rejected')
        previous = gold(r,0)
    require(r.invoke('tdFlowLaneHasPendingSpawn',0), 'Old clear canceled newer production')
    r.invoke('tdFlowEndSpawn',0,pending)
    # Spending, pause/wall-clock and opening UI cannot provide a fresh claim.
    r.call('SetPlayerState',[0,'gold',gold(r,0)-100])  # Native construction spending boundary.
    previous = gold(r,0)
    for now in (180.,3600.,1000000.):
        r.now = now
        r.invoke('tdHandleWaveFinished',0,1)
        require(gold(r,0)==previous, 'Wall-clock or spent balance renewed wage')

    for mode in ('inactive','defeated','finished','left','gameover'):
        r = fixture(script)
        if mode == 'inactive': r.invoke('tdSetLaneActive',0,False)
        elif mode == 'defeated': r.invoke('tdSetLaneDefeated',0,True)
        elif mode == 'finished': r.invoke('tdSetLaneFinished',0,True)
        elif mode == 'left': r.invoke('tdPetMarkPlayerLeft',0)
        else: r.invoke('tdSetGameOver',True)
        previous = gold(r,0)
        r.invoke('tdHandleWaveFinished',0,4)
        require(gold(r,0)==previous and not r.invoke('tdIsWaveResolved',0,4), 'Closed lane received settlement: '+mode)
    r = fixture(script)
    before = [gold(r,lane) for lane in range(4)]
    for lane,wave in ((-1,4),(4,4),(0,-1),(0,0),(0,33)):
        r.invoke('tdHandleWaveFinished',lane,wave)
    require([gold(r,lane) for lane in range(4)]==before,'Invalid event received money')

    boss_cases=[]
    for wave,lives,result in ((16,20,3),(16,20,4),(16,3,3),(16,3,4),(32,20,4)):
        r=fixture(script);start_boss(r,wave)
        r.globals['TDState_tdLives'][0]=lives
        before=gold(r,0)
        # Actual abnormal-disappearance/native timeout path allows a null Boss.
        r.invoke('tdSettleBossFailure',None,0,wave,result)
        expected=REWARDS[wave-1]+NODES.get(wave,0) if lives>3 and wave<32 else 0
        require(gold(r,0)-before==expected,'Boss failure survival/defeat wage boundary changed')
        require(r.invoke('tdIsLaneDefeated',0)==(lives<=3 or wave==32),'Boss defeat boundary changed')
        r.invoke('tdSettleBossFailure',None,0,wave,result)
        require(gold(r,0)-before==expected,'Repeated Boss failure paid twice')
        boss_cases.append({'wave':wave,'initialLives':lives,'result':result,'settlement':expected})

    # Execute the actual old-epoch spawn completion closure, not a Python guard.
    r=fixture(script)
    epoch=r.invoke('tdFlowEpoch')
    r.invoke('tdWaitForLaneToClear',0,4,epoch)
    callback=r.periodics[-1][1]
    r.invoke('tdResetState');r.invoke('tdPetInitializeLane',0);r.invoke('tdSetLaneActive',0,True)
    previous=gold(r,0)
    run_clear_callback(r,script,callback)
    require(gold(r,0)==previous and not r.invoke('tdIsWaveResolved',0,4),'Old epoch completion paid in new match')
    r=fixture(script)
    r.invoke('tdWaitForLaneToClear',0,1,r.invoke('tdFlowEpoch'))
    callback=r.periodics[-1][1]
    previous=gold(r,0)
    run_clear_callback(r,script,callback)
    require(gold(r,0)-previous==160 and r.invoke('tdIsWaveResolved',0,1),'Real clear callback not wired to wage settlement')
    r=fixture(script)
    r.invoke('tdWaitForLaneToClear',0,4,r.invoke('tdFlowEpoch'))
    callback=r.periodics[-1][1]
    r.invoke('tdHandleLanePlayerLeft',0)
    previous=gold(r,0)
    run_clear_callback(r,script,callback)
    require(gold(r,0)==previous and not r.invoke('tdIsWaveResolved',0,4),'Left lane callback paid wages')
    return {'checkpoints':checkpoints,'all32WavesFourLanes':True,'duplicateAndDelayed':True,
            'closedStates':5,'invalidEvents':5,'bossFailures':boss_cases,'oldEpochCallback':True,'nativeClearCallback':True,'leftCallback':True,
            'nativeResourceSync':True,'wallClockHasNoClaim':True}


def verify_objects(candidate,baseline):
    current,prior=Mpq(candidate),Mpq(baseline)
    a,b=members(current),members(prior)
    require(a.keys()==b.keys(),'Unexpected archive membership change')
    require(normalize_info(current.extract('war3map.w3i'),'契灵守卫战')==normalize_info(prior.extract('war3map.w3i'),'契灵守卫战'),'Unrelated map settings changed')
    changed=[name for name in a if a[name][1]!=b[name][1]]
    require(set(changed)<={'war3map.j','war3map.w3i','war3map.w3a','war3map.w3u'},'Unexpected map resource changes: '+repr(changed))
    abilities,old_abilities=ability_objects(current.extract('war3map.w3a')),ability_objects(prior.extract('war3map.w3a'))
    units,old_units=unit_objects(current.extract('war3map.w3u')),unit_objects(prior.extract('war3map.w3u'))
    require('A109' in old_abilities and 'A109' not in abilities,'Old wage object was not removed')
    expected=dict(old_abilities);expected.pop('A109')
    require(abilities.keys()==expected.keys(),'Unrelated ability catalog changed')
    for code,(parent,fields) in abilities.items():
        old_parent,old_fields=expected[code]
        require(parent==old_parent and fields.keys()==old_fields.keys(),'Ability identity/schema changed: '+code)
        # Removing one Channel allocation can shift subsequent generated orders.
        # No cooldown, target, effect or presentation field is exempted.
        delta={key for key in fields if fields[key]!=old_fields[key]}
        require(all(key[0]=='Ncl6' and parent=='ANcl' for key in delta),'Unrelated ability field changed: '+code)
        for key,(kind,old_order) in old_fields.items():
            if key[0]!='Ncl6': continue
            require(old_order in CHANNEL_ORDERS[1:],'Unknown Channel order allocation: '+code)
            expected_order=CHANNEL_ORDERS[CHANNEL_ORDERS.index(old_order)-1]
            require(fields[key]==(kind,expected_order),'Channel order did not shift by exactly retired allocation: '+code)
    require(units.keys()==old_units.keys(),'Unit catalog changed')
    for code,fields in units.items():
        expected=dict(old_units[code])
        if 'A109' in expected.get('uabi','').split(','):
            expected['uabi']=','.join(x for x in expected['uabi'].split(',') if x!='A109')
        require(fields==expected,'Unrelated unit field changed: '+code)
    probe=(Path(__file__).resolve().parents[1]/'tests/wurst/runtime/TDNativeNormalPlayProbe.wurst').read_text()
    declared=re.findall(r'IssueTargetOrderById\(worker, OrderId\("([^"]+)"\), normalCaptureTarget\)',probe)
    capture_order=abilities['Pcap'][1]['Ncl6',1,6][1]
    require(declared==[capture_order],'Native normal-play probe capture order differs from packaged Pcap')
    return sorted(changed)


def mutate_settlement(script,old,new):
    match=re.search(r'(?ms)^function tdHandleWaveFinished takes .*?^endfunction',script)
    require(match is not None,'Packed settlement function missing')
    body,count=re.subn(old,new,match[0],count=1)
    require(count==1,'Packed mutation anchor missing: '+old)
    return script[:match.start()]+body+script[match.end():]


def verify_mutations(script):
    cases=[
        ('wrong-wave',r'tdWaveProgressWage\([^)]*\)','tdWaveProgressWage(31)','settlement delta'),
        ('duplicate-credit',r'(?m)^\s*if tdIsWaveResolved\([^\n]+ then\n(?:\s*set wurst_stack_depth = wurst_stack_depth - 1\n)?\s*return\n\s*endif\n','','Duplicate settlement'),
        ('left-credit',r' or tdPetPlayerHasLeft\([^)]*\)','','Closed lane')]
    report=[]
    for name,old,new,reason in cases:
        changed=mutate_settlement(script,old,new)
        try: verify(changed)
        except ValueError as error:
            require(reason in str(error),'Mutation failed for unrelated reason: '+name+': '+str(error))
            report.append({'name':name,'rejected':True,'reason':str(error)})
        else: raise ValueError('Packed mutation escaped: '+name)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('map',type=Path);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();data=a.map.read_bytes();script=Mpq(data).extract('war3map.j').decode()
    require(not re.search(r'function (?:td\w*FarmerWage\w*) takes',script),'Retired wage function remains executable')
    report={'status':'PASS','mapSHA256':hashlib.sha256(data).hexdigest(),'coverage':verify(script),
            'mutations':verify_mutations(script),
            'changedMembers':verify_objects(data,a.baseline.read_bytes()),
            'boundary':'Actual packed Game/Flow/gold JASS; controlled native engine handles/UI/clock. No real gameplay or renderer claim.'}
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
