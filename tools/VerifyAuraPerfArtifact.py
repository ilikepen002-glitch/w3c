#!/usr/bin/env python3
"""Actual packed aura allocation/routing and deterministic interpreter-work counts.

No Warcraft opcode/FPS claim. Native units, inventory, buffs, timers and ForForce
delivery are controlled; the production Execute/try/Aura functions still run.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from GenerateTowerTerrainMask import Mpq
from VerifyAuraTargetArtifact import AuraRuntime, verify as verify_routing
from VerifyEquipmentCombatReplay import EquipmentRulesRuntime, close
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerUpgradeArtifact import rawcode
from ReadEquipmentCatalog import catalog


class CountedAuraRuntime(AuraRuntime):
    def __init__(self, script):
        self.expressions = 0
        self.force_threads = []
        self.notices = []
        super().__init__(script)
        self.functions['jass_try'] = self.functions['try']
        self.globals['UNIT_TYPE_MECHANICAL'] = 'mechanical'

    def expression(self, text, scope):
        self.expressions += 1
        return super().expression(re.sub(r'\btry\(', 'jass_try(', text), scope)

    def native(self, name, args):
        if name == 'IsUnitType' and args[1] == 'mechanical':
            return True, self.units[args[0]].get('mechanical', False)
        if name == 'CreateForce': return True, 90001
        if name == 'ForceAddPlayer': return True, None
        if name == 'ForForce':
            before = self.expressions, sum(self.calls.values())
            self.invoke(args[1])
            self.force_threads.append((self.expressions-before[0], sum(self.calls.values())-before[1]))
            return True, None
        if name == 'GetUnitDefaultMoveSpeed': return True, self.units[args[0]].get('defaultSpeed', 260.)
        if name == 'DisplayTimedTextToPlayer': self.notices.append(args); return True, None
        return super().native(name, args)


def fixture(script):
    r = CountedAuraRuntime(script)
    r.initialize_match(); r.invoke('init_Execute')
    template = dict(r.units[101])
    for lane in range(4):
        for index in range(10):
            unit = 101+lane*10+index
            r.units[unit] = {**template, 'type': rawcode('uA11'), 'owner': lane,
                'userdata': lane*10000, 'x': lane*2000., 'y': 0., 'abilities': {},
                'inventory': {}, 'alive': True, 'speed': 260., 'defaultSpeed': 260.}
            r.invoke('tdAuraRegisterTarget', unit, True)
        for index in range(52):
            unit = 1000+lane*52+index
            r.units[unit] = {**template, 'type': rawcode('uE19'), 'owner': 4,
                'userdata': lane*10000+2500, 'x': lane*2000.+10, 'y': 0.,
                'abilities': {}, 'inventory': {}, 'alive': True, 'speed': 260., 'defaultSpeed': 260.}
            r.invoke('tdAuraRegisterTarget', unit, False)
    return r


def refresh(r, target):
    r.executed_steps = 0
    r.invoke('tdAuraRefresh', r.invoke('tdAuraTargetFor', target))
    require(not r.notices, 'Production Execute/try reported a failed aura refresh')


def state(r, target):
    record = r.invoke('tdAuraTargetFor', target)
    aggregate = r.globals['TDAuraTarget_effective'][record]
    return {'auras': [(r.invoke('TDAuraAggregate_rank', aggregate, i),
                       r.invoke('TDAuraAggregate_power', aggregate, i)) for i in range(1,18)],
            'abilities': dict(r.units[target]['abilities']), 'speed': r.units[target]['speed']}


def benchmark(script):
    r = fixture(script); refresh(r,101)
    report = []
    for label, function, args in (
        ('warm_empty_tower_40_sources', 'tdAuraRefresh', [r.invoke('tdAuraTargetFor',101)]),
        ('empty_enemy_40_sources', 'tdAuraRefresh', [r.invoke('tdAuraTargetFor',1000)]),
        ('16_target_periodic', 'call_doPeriodically_TDAuraRuntime', [0,0])):
        r.executed_steps = 0; r.force_threads = []
        before = r.expressions; calls = Counter(r.calls)
        r.invoke(function, *args)
        delta = Counter(r.calls)-calls
        require(not r.notices, 'Benchmark skipped production application after try failure')
        report.append({'label': label, 'expressions': r.expressions-before, 'calls': sum(delta.values()),
            'source_visits': delta['tdAuraOfferSource'], 'apply_calls': delta['tdAuraApply'],
            'force_threads': r.force_threads[:], 'state': [state(r,t) for t in (101,1000,1052)]})
    return report


def verify_reuse(script):
    r = EquipmentRulesRuntime(script)
    first = r.invoke('new_TDAuraAggregate')
    for identity in range(1,18): r.invoke('TDAuraAggregate_offer',first,identity,4,.2,True)
    r.invoke('destroyTDAuraAggregate',first)
    again = r.invoke('new_TDAuraAggregate')
    require(first == again, 'Allocation fixture did not actually reuse the freed class ID')
    for identity in range(1,18):
        require(r.invoke('TDAuraAggregate_rank',again,identity)==0, 'Recycled aggregate retained rank')
        close(r.invoke('TDAuraAggregate_power',again,identity),0.,'Recycled aggregate retained power')
    r.invoke('TDAuraAggregate_offer',again,7,1,.06,True)
    close(r.invoke('TDAuraAggregate_power',again,7),.06,'Weak offer after strong recycled owner')
    return {'same_id_reused':True,'all_17_identities_empty':True,'weak_power':.06}


def verify_metadata(script):
    r = EquipmentRulesRuntime(script)
    aura_kinds={'NONE':0,'ATTACK':1,'ATTACK_SPEED':2,'COOLDOWN':3,'ARMOR_ON_HIT':4,'ENEMY_SLOW':5}
    count=0
    for item in catalog():
        kind=r.invoke('tdItemAuraDefinition',rawcode(item.rawcode))
        require(kind==aura_kinds[item.aura],'Packed catalog aura kind changed: '+item.rawcode)
        require(r.globals['tdItemAuraDefinition_return_quality']==item.quality,'Packed catalog quality changed: '+item.rawcode)
        close(r.globals['tdItemAuraDefinition_return_power'],item.aura_value,'Packed catalog aura power '+item.rawcode)
        close(r.globals['tdItemAuraDefinition_return_radius'],item.aura_radius,'Packed catalog aura radius '+item.rawcode)
        count+=1
    for item in (0,-1,rawcode('Ibal'),rawcode('uA11'),rawcode('iZ01')):
        require(r.invoke('tdItemAuraDefinition',item)==0,'Unknown/absent item emitted an aura')
        require(all(r.globals['tdItemAuraDefinition_return_'+field]==0 for field in ('quality','power','radius')),'Unknown item retained aura metadata')
    return {'all_catalog_items':count,'absent_or_non_equipment':5}


def verify_constructor_negative(script):
    match=re.search(r'function construct_TDAuraAggregate takes[^\n]*\n(.*?)endfunction',script,re.S)
    require(match is not None,'Actual aggregate constructor is missing')
    clears=re.findall(r'^[ \t]*call dispatch_TDAuraAggregate_TDAuraAggregate_clear\([^\n]*\)\n',match[1],re.M)
    require(len(clears)==1,'Actual constructor must clear its arrays exactly once')
    broken=script[:match.start(1)]+match[1].replace(clears[0],'',1)+script[match.end(1):]
    for check,expected in ((verify_reuse,'Recycled aggregate retained rank'),
                           (verify_transitions,'Strong removed must fall back to weak')):
        try:check(broken)
        except ValueError as error:require(expected in str(error),'Unrelated constructor-removal failure: '+str(error))
        else:raise ValueError('Removing the actual constructor clear survived the aura gate')
    return {'clear_removal_reproduces_reuse_and_weak_fallback':True}


def verify_transitions(script):
    r = fixture(script)
    def equip(source,item):
        handle = 4000+source
        r.inventory_items[handle] = rawcode(item)
        r.units[source]['inventory'] = {0:handle}
    equip(101,'iW10'); equip(102,'iP10')
    for _ in range(3): refresh(r,1000)
    close(state(r,1000)['auras'][6][1],.20,'Strong frost')
    r.units[102]['inventory'] = {}
    for _ in range(3): refresh(r,1000)
    close(state(r,1000)['auras'][6][1],.06,'Strong removed must fall back to weak')
    close(r.units[1000]['speed'],244.4,'Weak frost move speed')
    r.units[101]['inventory'] = {}
    for _ in range(3): refresh(r,1000); refresh(r,1052); refresh(r,101)
    require(all(rank==0 and power==0. for rank,power in state(r,1000)['auras']), 'Removed aura survived class-ID rotation')
    require(all(rank==0 and power==0. for rank,power in state(r,1052)['auras']), 'Other-lane target inherited recycled source power')
    close(r.units[1000]['speed'],260.,'All frost removed')
    equip(101,'iW10'); equip(102,'iP10'); r.units[102]['alive']=False
    for _ in range(3): refresh(r,1000)
    close(state(r,1000)['auras'][6][1],.06,'Dead strong source must fall back')
    r.units[101]['x']=10000.
    for _ in range(3): refresh(r,1000)
    close(state(r,1000)['auras'][6][1],0.,'Out-of-range weak source must expire')
    return {'strong_to_weak':True,'all_removed':True,'tower_enemy_cross_lane_rotation':True,
            'dead_strong_source':True,'out_of_range':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map',type=Path); parser.add_argument('--baseline',type=Path,required=True)
    args=parser.parse_args()
    scripts=[Mpq(path.read_bytes()).extract('war3map.j').decode('utf-8') for path in (args.baseline,args.map)]
    before,after=[benchmark(script) for script in scripts]
    for old,new in zip(before,after):
        require(old['state']==new['state'], 'Clean-state benchmark changed aura outputs')
        require(old['source_visits']==new['source_visits'] and old['apply_calls']==new['apply_calls'], 'Optimization changed source/target scheduling')
        require(new['expressions']<old['expressions'] and new['calls']<old['calls'], 'No interpreter-work reduction')
    report={'status':'PASS','map_sha256':hashlib.sha256(args.map.read_bytes()).hexdigest(),
        'baseline_sha256':hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
        'metadata':verify_metadata(scripts[1]),'routing':verify_routing(scripts[1]),'aggregate_reuse':verify_reuse(scripts[1]),
        'transitions':verify_transitions(scripts[1]),'constructor_mutation':verify_constructor_negative(scripts[1]),'before':before,'after':after,
        'boundary':'Actual packed functions. Expression/call counts are interpreter work, not WC3 opcodes/FPS. Native engine buffs/rendering, unit/clock/ForForce boundaries controlled.'}
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
