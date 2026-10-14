#!/usr/bin/env python3
"""Actual packed display transitions and binding guards; native art setters are recorded.
No Warcraft rendering/FPS claim. Existing transaction and combat suites remain independent.
"""
import argparse, hashlib, json
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyPetRebindingArtifact import RebindingRuntime, verify_rebinding
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerUpgradeArtifact import rawcode
from VerifyElementalVfxArtifact import battle
from VerifyElementalPetArtifact import EXPECTED
from VerifyPetAttackArtifact import PetAttackRuntime
from VerifyPetUIArtifact import jass_function
import re

class DisplayRuntime(RebindingRuntime):
    def __init__(self, script):
        self.display_writes = []
        super().__init__(script)
        self.display_writes.clear()
    def native(self, name, args):
        if name in ('SetUnitPosition', 'SetUnitFlyHeight', 'SetUnitAnimation', 'SetUnitAnimationByIndex'):
            if args and args[0] in self.units:
                visual_types = {self.invoke('tdPetVisualUnitId', species) for species in range(1, 16)}
                if self.units[args[0]]['type'] in visual_types:
                    self.display_writes.append((self.now, name, *args))
        return super().native(name, args)

def require_action(r, pet, action):
    require(r.field('visualAction', pet) == action, 'Unexpected packed display action')

def verify_display(script, full_profiles=True):
    r = DisplayRuntime(script)
    profiles = 0
    for family in (('A', 'O', 'H', 'D', 'G') if full_profiles else ('A',)):
        for suffix in (('11','12','13','14','15','6A','6B') if full_profiles else ('11',)):
            for species in (range(1, 16) if full_profiles else (1,)):
                # Bound each independent profile instead of charging all 525 cases
                # against one transaction budget. The per-case 2M guard remains.
                r.executed_steps = 0
                host = r.tower(5000, type_id='u'+family+suffix)
                pet = r.invoke('new_TDPet', 0, species, 1)
                require(r.invoke('tdPetStore', 0, pet), 'Profile collection fixture rejected')
                require(r.invoke('tdPetDeploy', pet, host), 'Profile real deployment rejected')
                visual = r.field('visual', pet)
                require(r.units[visual]['x'] == r.units[host]['x'] and r.units[visual]['y'] == r.units[host]['y'], 'Visual not host-centered')
                require(r.units[visual]['z'] == r.invoke('tdPetDisplayHeight', rawcode('u'+family+suffix)), 'Profile native height mismatch')
                require_action(r, pet, 5)
                before = len(r.display_writes)
                r.invoke('tdPetDisplayTick', pet, 0, r.now + .5)
                require(len(r.display_writes) == before, 'Stationary early tick spammed setters')
                display_state = tuple(r.field(k,pet) for k in ('visualAction','visualNextAt','visualCycle'))
                r.now += .1
                require(r.invoke('tdPetDeploy', pet, host), 'Same-host legal no-op rejected')
                require(display_state == tuple(r.field(k,pet) for k in ('visualAction','visualNextAt','visualCycle')), 'Same-host reinitialized cosmetic state')
                require(len(r.display_writes) == before, 'Same-host reinitialized display')
                r.invoke('TDPet_recall', pet)
                require(r.invoke('tdPetDiscardOwned', 0, 0), 'Profile cleanup rejected')
                profiles += 1
    # Every species must transition through all appended indices using the real
    # packed runtime, not just share the initial Float capability check.
    for species in range(1, 16):
        each = DisplayRuntime(script)
        host = each.tower(5200 + species)
        pet = each.invoke('new_TDPet', 0, species, 1)
        require(each.invoke('tdPetStore', 0, pet), 'Species-action collection fixture rejected')
        require(each.invoke('tdPetDeploy', pet, host), 'Species-action deployment rejected')
        for action in (6, 7, 8):
            each.now = each.field('visualNextAt', pet)
            each.invoke('tdPetDisplayTick', pet, 0, each.now)
            require_action(each, pet, action)
            each.now = each.field('visualNextAt', pet)
            each.invoke('tdPetDisplayTick', pet, 0, each.now)
            require_action(each, pet, 5)
        each.invoke('tdPetDisplayCast', pet, host, each.field('generation', pet), each.now)
        require_action(each, pet, 9)
        each.now = each.field('visualNextAt', pet)
        each.invoke('tdPetDisplayTick', pet, 0, each.now)
        require_action(each, pet, 5)
    r = DisplayRuntime(script)
    pet = r.record(host=r.tower(201))
    host = r.field('host', pet); generation = r.field('generation', pet)
    r.units[host].update(x=25.,y=40.)
    r.invoke('tdPetDisplayTick',pet,0,r.now+.5)
    require(r.units[r.field('visual',pet)]['x']==25. and r.units[r.field('visual',pet)]['y']==40.,'Moved host XY not corrected')
    for action in (6,7,8):
        deadline = r.field('visualNextAt', pet)
        r.now = deadline
        r.invoke('tdPetDisplayTick', pet, 0, r.now)
        require_action(r, pet, action)
        duration = r.invoke('tdPetDisplayDuration', action)
        require(r.field('visualNextAt', pet) == r.now + duration, 'Action duration mismatch')
        r.now += duration
        r.invoke('tdPetDisplayTick', pet, 0, r.now)
        require_action(r, pet, 5)
    r.now = r.field('visualNextAt', pet)
    r.invoke('tdPetDisplayTick', pet, 0, r.now)
    require_action(r, pet, 6)
    r.invoke('tdPetDisplayCast', pet, host, generation, r.now)
    require_action(r, pet, 9)
    require(r.field('visualNextAt', pet) == r.now + 1.2, 'Cast duration mismatch')
    before = len(r.display_writes)
    r.invoke('tdPetDisplayCast', pet, host, generation - 1, r.now)
    require(len(r.display_writes) == before, 'Stale generation wrote display')
    r.invoke('tdPetTowerWorkStarted', host)
    r.invoke('tdPetDisplayTick', pet, 0, r.now)
    require_action(r, pet, 5)
    before = len(r.display_writes)
    r.invoke('tdPetDisplayTick', pet, 0, r.now + .5)
    r.invoke('tdPetDisplayCast', pet, host, r.field('generation',pet), r.now)
    require(len(r.display_writes) == before, 'Paused display spammed or cast')
    r.units[host]['type'] = rawcode('uA15')
    r.invoke('tdPetTowerWorkFinished', host)
    r.invoke('tdPetDisplayTick', pet, 0, r.now + 1.)
    require(r.units[r.field('visual',pet)]['z'] == r.invoke('tdPetDisplayHeight',rawcode('uA15')), 'Upgrade profile not refreshed')
    visual = r.field('visual',pet)
    for damage in ('dead','wrong-owner','wrong-type','missing'):
        saved = dict(r.units[visual]); r.globals['TDPet_visual'][pet] = visual
        if damage == 'dead': r.units[visual]['alive'] = False
        if damage == 'wrong-owner': r.units[visual]['owner'] = 1
        if damage == 'wrong-type': r.units[visual]['type'] = rawcode('hpea')
        if damage == 'missing': r.globals['TDPet_visual'][pet] = None
        before = len(r.display_writes)
        r.invoke('tdPetDisplayTick', pet, 0, r.now + 100.)
        r.invoke('tdPetDisplayCast', pet, host, r.field('generation',pet), r.now + 100.)
        require(len(r.display_writes) == before, 'Invalid visual accepted writes: '+damage)
        r.units[visual] = saved
    r.globals['TDPet_visual'][pet] = visual
    r.invoke('TDPet_recall',pet)
    require_action(r,pet,-1)
    before = len(r.display_writes)
    r.invoke('tdPetDisplayCast',pet,host,generation,r.now)
    require(len(r.display_writes) == before,'Recalled stale cast wrote')
    stress = DisplayRuntime(script); pets=[]
    for lane in range(4):
        for slot in range(20):
            host=stress.tower(6000+lane*20+slot,lane=lane)
            pet=stress.record(lane=lane,host=host);pets.append((pet,slot))
    before=len(stress.display_writes); handles=len(stress.units); timers=len(stress.timers); rng=len(stress.random_trace)
    for step in range(1,15):
        for pet,slot in pets:stress.invoke('tdPetDisplayTick',pet,slot,stress.now+step*.5)
    require(len(stress.display_writes)==before,'80-bound early idle setter spam')
    require(len(stress.units)==handles and len(stress.timers)==timers and len(stress.random_trace)==rng,'Display grew handles/timers/RNG')
    negative = DisplayRuntime(script); record=negative.pet(20)
    negative.invoke('TDPet_recall',record)
    require(negative.invoke('tdPetDeploy',record,101),'Failed-start fixture deployment rejected')
    negative.globals['TDPet_readyAt'][record]=0.
    negative.auto_post=False
    negative.emit(100.)
    negative.units[102]['alive']=False
    negative.units[102]['life']=0.
    negative.drain_zero()
    require_action(negative,record,5)
    require(negative.field('readyAt',record)==0.,'Failed start changed cooldown')
    require(not any(write[1]=='SetUnitAnimationByIndex' and write[3]==9 for write in negative.display_writes),'Failed start animated Cast')
    invalidated=DisplayRuntime(script)
    record=PetAttackRuntime.pet(invalidated,[(0,1),(16,4),(39,1),(19,1)])
    invalidated.invoke('TDPet_recall',record)
    require(invalidated.invoke('tdPetDeploy',record,101),'Post-hit fixture deployment rejected')
    invalidated.globals['TDPet_readyAt'][record]=0.;invalidated.roll=0.
    invalidated.swap_on_damage=lambda runtime:runtime.invoke('TDPet_recall',record)
    invalidated.emit(100.)
    require_action(invalidated,record,-1)
    require(not any(write[1]=='SetUnitAnimationByIndex' and write[3]==9 for write in invalidated.display_writes),'Post-hit invalidation animated Cast')
    active_reports = []
    for skill in list(EXPECTED) + [11,12]:
        traces=[]
        for missing in (False,True):
            active=DisplayRuntime(script); record=active.pet(skill)
            active.invoke('TDPet_recall',record)
            require(active.invoke('tdPetDeploy',record,101),'Legal active display deployment failed')
            active.globals['TDPet_readyAt'][record]=0.
            if missing:
                visual=active.field('visual',record)
                active.native('RemoveUnit',[visual])
                active.globals['TDPet_visual'][record]=None
            # Match battle()'s explicit 15-enemy fixture, rather than reading
            # nonexistent enemy handles after a one-enemy pet() setup.
            for target in range(103,116): active.enemy(target)
            active.enemy(116,lane=1)
            active.visible_units=list(range(102,117))
            active.now += 1.
            active.emit(100.)
            if not missing:
                expected=9
                require_action(active,record,expected)
            active.finish(9.)
            traces.append(battle(active,record))
        require(traces[0]==traces[1],'Display affected actual active battle trace: '+str(skill))
        active_reports.append(skill)
    return {'failed_start_no_cast':True,'post_hit_invalidation_no_cast':True,'active_success_trace_equivalence':active_reports,'profile_species_scenarios':profiles,'all_species_action_scenarios':15,'idle_sequence':[6,7,8],'cast_preemption':True,'pause_upgrade':True,'invalid_visual_cases':4,'stress_bound':80,'steady_state_writes':0,'rebinding':verify_rebinding(script)}

def verify_display_mutations(script):
    def mutate(name, transform):
        m=jass_function(script,name);body=transform(m.group(1))
        require(body!=m.group(1),'Missing display mutation root: '+name)
        return script[:m.start(1)]+body+script[m.end(1):]
    def prepend(body,statement):
        lines=body.splitlines(True)
        i=next(i for i,line in enumerate(lines) if line.strip() and not line.lstrip().startswith('local '))
        lines.insert(i,statement+'\n');return ''.join(lines)
    owner=jass_function(script,'tdPetDisplayOwnerValid')
    tick=jass_function(script,'tdPetDisplayTick')
    pet=re.search(r'takes integer (\w+)',tick.group(0))[1]
    deploy=jass_function(script,'tdPetDeploy');deployed=re.search(r'takes integer (\w+)',deploy.group(0))[1]
    cast_function=re.search(r'^function (\w+) takes[^\n]*\n(?:(?!^endfunction).)*?call tdPetDisplayCast\(',script,re.M|re.S)[1]
    tests=[
        ('failed_start_cast','Unexpected packed display action',mutate(cast_function,lambda b:re.sub(r'if started\w* and ', 'if true and ',b,count=1))),
        ('generation_guard_removed','Stale generation wrote display',mutate('tdPetDisplayOwnerValid',lambda b:re.sub(r'TDPet_generation\[[^]]+\] == \w+','true',b,count=1))),
        ('same_host_reinitialize','Same-host reinitialized cosmetic state',mutate('tdPetDeploy',lambda b:b.replace('return true','call tdPetDisplayInitialize('+deployed+', 0, getElapsedGameTime())\nreturn true',1))),
        ('tick_animation_reset','Stationary early tick spammed setters',mutate('tdPetDisplayTick',lambda b:prepend(b,'call SetUnitAnimationByIndex(TDPet_visual['+pet+'], 5)'))),
        ('rng_introduced','Display grew handles/timers/RNG',mutate('tdPetDisplayTick',lambda b:prepend(b,'call GetRandomInt(1, 100)'))),
    ]
    reports=[]
    for label,reason,changed in tests:
        try:verify_display(changed, full_profiles=False)
        except ValueError as error:
            require(str(error)==reason,'Mutation hit unrelated failure: '+label+': '+str(error))
            reports.append({'mutation':label,'reason':reason})
        else:raise ValueError('Display mutation survived: '+label)
    return reports

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('map',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    data=a.map.read_bytes();script=Mpq(data).extract('war3map.j').decode()
    report=verify_display(script);report['mutations']=verify_display_mutations(script);report.update(status='PASS',map_sha256=hashlib.sha256(data).hexdigest(),boundary='Actual packed JASS; engine setters recorded; no Warcraft observation')
    if a.output:a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
