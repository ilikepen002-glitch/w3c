#!/usr/bin/env python3
"""Execute actual production trial JASS against bounded native engine stubs.

Game/Flow registration, interface dispatch, concrete trial callbacks, state,
unit identity, movement, damage listeners, ledger and native cleanup calls run
from the supplied map. Warcraft clock, collections, unit creation/removal,
movement, rendering and trigger scheduling are explicit recorded boundaries.
This never accepts the older dummy-hook fixture or an empty DCE dispatcher.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from VerifyPureBossArtifact import PureBossJassRuntime
from VerifyBuilderControlDelta import allocations
from VerifyDamageRankingJass import functions
from VerifyEquipmentAbilityArtifact import require
from GenerateTowerTerrainMask import Mpq
from VerifyTowerUpgradeArtifact import rawcode

class TrialJassRuntime(PureBossJassRuntime):
    def __init__(self, script):
        super().__init__(script)
        self.timer_serial, self.table_serial, self.list_serial, self.unit_serial = 20000, 30000, 40000, 50000
        self.timers, self.iterators, self.rects, self.inventory_items = {}, {}, {}, {}
        self.expired_timer = None
        self.fail_creation_at = None
        self.creations, self.removals, self.orders, self.teleports, self.native_events = [], [], [], [], []
        self.timer_starts, self.timer_destroys, self.trigger_events = [], [], []
        self.periodics = []
        self.hud_refreshes = 0
        self.player_resources = {(lane, "gold"):1000 for lane in range(4)}
        self.execute_lane_state, self.capture_wave_production = True, True
        self.tables[610].clear()
        self.table.clear(); self.lists[700].clear()
        self.globals.update(EVENT_PLAYER_UNIT_DEATH='unitDeath', UNIT_TYPE_DEAD='dead',
                            UNIT_STATE_LIFE='life', UNIT_STATE_MAX_LIFE='maxLife', PLAYER_STATE_RESOURCE_GOLD='gold', PLAYER_STATE_RESOURCE_LUMBER='lumber')
        for field, code in re.findall(r'^\s*set (ref_function_\w+) = function (\w+)\s*$', script, re.M):
            self.globals[field] = code
        self.invoke('CreateRegions')
        # Only relevant production package initialization, not main/UI/game boot.
        # The packaged min/max helpers use Real_REAL_MAX/MIN initialized here.
        # Replaying match startup alone omits the engine's earlier package init.
        for name in ('init_Real', 'init_TDTowerTargetPriorityRules', 'init_TDTowerTargetPriorityState',
                     'init_TDPetRules', 'init_TDCombatVisualRuntime', 'init_TDPetEffectScheduler', 'init_TDPetHeroState', 'init_TDPetHeroEffects',
                     'init_TDPetCastContext', 'init_TDPetEffectTargetState', 'init_TDPetActiveVisualData', 'init_TDPetActiveVisuals',
                     'init_TDEnemyControlRuntime', 'init_TDPetRuntime',
                     'init_TDBossDarkTideRuntime', 'init_TDTowerEvolutionRuntime', 'init_TDPetWild', 'init_TDDamageState', 'init_TDDamageRuntime', 'init_TDItemData', 'init_TDEquipmentCombat',
                     'init_TDPetAttackQueue', 'init_TDPetState', 'init_TDPetAttackState', 'init_TDPetCombat', 'init_TDTrialIdentity',
                     'init_TDTrialRuntime', 'init_TDTrialHook', 'init_TDTrialHud',
                     'init_TDAuraObjectIds', 'init_TDEquipmentSpecialObjectIds',
                     'init_TDAuraState', 'init_TDShieldRuntime', 'init_TDEquipmentSpecialState'):
            if name in self.functions: self.invoke(name)
        require('TDTrialIdentity_tdTrialState' in self.globals and self.globals['TDTrialIdentity_tdTrialState'] != 0,
                'Actual production trial state initialization missing')

    def invoke(self, name, *arguments):
        signature = self.functions[name][0]
        if len(signature) == len(arguments) + 1 and signature[-1] in ('w__wurst_stackPos', 'stackPos'):
            arguments += ('offline production trial replay',)
        return self.call(name, list(arguments))

    @property
    def state(self): return self.globals['TDTrialIdentity_tdTrialState']
    @property
    def slots(self): return self.globals['TDTrialIdentity_tdTrialNativeSlots']
    def state_call(self, method, *args):
        if method == 'targetCount' and 'TDTrialState_targetCount' not in self.functions:
            return self.invoke('TDTrialTargets_count', self.globals['TDTrialState_targets'][self.state])
        return self.invoke('TDTrialState_' + method, self.state, *args)
    def binding(self, index): return self.slots[index]
    def target(self, index): return self.globals['TDTrialBinding_target'][self.binding(index)]

    def adversarial_rebind(self, index, reused=False):
        """Synthetic registry adversary, NEVER production ACTIVE replenishment.

        The real death/exit must already have vacated this slot. Native allocation
        and the pure identity registry model an adversary bypassing both reviewed
        admission APIs, so actual snapshot guards retain new/reused-handle negatives.
        """
        lane, slot = divmod(index, 5)
        require(0 <= index < 20 and self.slots[index] == 0 and self.state_call('getPhase') == 2,
                'Registry adversary needs one already-vacant ACTIVE slot')
        token, generation = self.state_call('getToken'), self.state_call('getGeneration')
        before = len(self.creations)
        require(not self.invoke('tdTrialCreateTarget', lane, slot, token, generation, self.now) and
                not self.state_call('bindTarget', lane, slot, 999999, token, generation, self.now) and
                len(self.creations) == before, 'ACTIVE admission allowed a real replacement')
        if reused:
            require(bool(self.removals), 'Reused-handle adversary lacks native retired handle')
            self.unit_serial = self.removals[-1] - 1
        target = self.call('CreateUnit', [4, rawcode('uTrG'), 0., 0., 0.])
        self.units[target].update(userdata=lane * 10000, life=1000000., maxLife=1000000., alive=True)
        identity = self.globals['TDTrialState_targets'][self.state]
        require(self.invoke('TDTrialTargets_bind', identity, lane, slot, target), 'Pure adversarial identity bind failed')
        binding = self.invoke('new_TDTrialBinding', target, lane, slot, 0., 0.)
        require(self.invoke('tdTrialRegisterBinding', binding), 'Adversarial native binding registration failed')
        require(self.state_call('getToken') == token and self.state_call('getGeneration') == generation,
                'Registry adversary changed the actual session')
        return target

    def expression(self, text, scope):
        # JASS code values are opaque native callback names, not Python code.
        text = re.sub(r'\bfunction (\w+)', lambda m: repr(m[1]), text)
        reserved = {'except', 'from', 'lambda'}
        text = re.sub(r'\"(?:\\.|[^\"\\])*\"|[A-Za-z_]\w*', lambda m: 'jass_' + m[0] if m[0] in reserved else m[0], text)
        scope = {**scope, **{'jass_' + key:value for key,value in scope.items() if key in reserved}}
        return super().expression(text, scope)

    def native(self, name, args):
        # Do not inherit Boss harness gameplay stubs for current production.
        if name in {'tdDamageTrackTower', 'dispatch_TDDamageRecord_TDDamageRecord_getLane',
                    'dispatch_TDDamageLedger_TDDamageLedger_credit', 'tdEquipmentSourceValid',
                    'tdEquipmentEnemyValid', 'tdPetBindingValid', 'tdPetEnemyIsValid', 'tdSyncPlayerResources'}:
            return False, None
        if name == 'tdRevealWholeMap': return True, None
        if name == 'GetPlayerState': return True, self.player_resources.get(tuple(args[:2]), 0)
        if name == 'SetPlayerState':
            self.player_resources[tuple(args[:2])] = args[2]; self.native_events.append(('resource', *args[:3])); return True,None
        if name.startswith('preloadAbility'): return True, True
        if name == 'tdRefreshHud': self.hud_refreshes += 1; return True, None
        if name == 'new_Table':
            self.table_serial += 1; self.tables[self.table_serial] = {}; return True, self.table_serial
        if name in ('new_LinkedList', 'new_LinkedList_1'):
            self.list_serial += 1; self.lists[self.list_serial] = []; return True, self.list_serial
        if name.startswith('dispatch_Table_Table_'):
            require(args[0] in self.tables, 'Unknown actual collection table boundary ' + str(args[0]))
            table = self.tables[args[0]]; op = name.removeprefix('dispatch_Table_Table_')
            if op.startswith('has'): return True, args[1] in table
            if op.startswith('load'): return True, table.get(args[1], False if op.endswith('Boolean') else 0.0 if op.endswith('Real') else 0)
            if op.startswith('save'): table[args[1]] = args[2]; return True, None
            if op.startswith('remove'): table.pop(args[1], None); return True, None
            if op == 'flush': table.clear(); return True, None
            raise ValueError('Unmodeled table operation ' + name)
        if name == 'LinkedList_iterator' or name == 'dispatch_LinkedList_LinkedList_iterator':
            require(args[0] in self.lists, 'Uninitialized actual collection list')
            ident = max(self.iterators, default=60000) + 1; self.iterators[ident] = [args[0], 0, None]; return True, ident
        if name.startswith('LLIterator_') or name.startswith('dispatch_LLIterator_LLIterator_'):
            op = name.split('LLIterator_')[-1]; require(args[0] in self.iterators, 'Uninitialized native list iterator')
            ident, index, last = self.iterators[args[0]]; values = self.lists[ident]
            if op == 'hasNext': return True, index < len(values)
            if op == 'next':
                require(index < len(values), 'Iterator overrun'); self.iterators[args[0]][1:]=[index+1,index]; return True,values[index]
            if op == 'remove':
                require(last is not None, 'Iterator remove before next'); values.pop(last); self.iterators[args[0]][1:]=[index-1,None]; return True,None
            if op == 'close': del self.iterators[args[0]]; return True,None
        if name == 'dispatch_LLIterator_destroyLLIterator': self.iterators.pop(args[0],None); return True,None
        if name == 'dispatch_LinkedList_destroyLinkedList':
            require(args[0] in self.lists and not self.lists[args[0]], 'Destroying unknown/nonempty modeled list')
            del self.lists[args[0]]; return True,None
        if name.startswith('dispatch_LinkedList_LinkedList_'):
            require(args[0] in self.lists, 'Unknown native list boundary')
            op = name.removeprefix('dispatch_LinkedList_LinkedList_'); values = self.lists[args[0]]
            if op == 'clear': values.clear(); return True,None
            if op == 'getDummy': require(not values, 'Nonempty list getDummy not modeled'); return True,0
            if op == 'size': return True,len(values)
            return super().native(name,args)
        if name == 'Rect':
            ident = 70000 + len(self.rects); self.rects[ident] = tuple(args[:4]); return True,ident
        if name == 'AddWeatherEffect': return True,1
        if name == 'EnableWeatherEffect': return True,None
        if name.startswith('GetRect'):
            require(args[0] in self.rects, 'Unknown actual map rectangle')
            x1,y1,x2,y2 = self.rects[args[0]]
            values = {'GetRectMinX':x1, 'GetRectMinY':y1, 'GetRectMaxX':x2, 'GetRectMaxY':y2, 'GetRectCenterX':(x1+x2)/2, 'GetRectCenterY':(y1+y2)/2}
            require(name in values, 'Unknown rect native'); return True,values[name]
        if name == 'doPeriodically': self.periodics.append(tuple(args[:2])); return True,args[1]
        if name == 'IMinBJ': return True,min(args[:2])
        if name == 'RMinBJ': return True,min(args[:2])
        if name == 'RMaxBJ': return True,max(args[:2])
        if name == 'Pow': return True,args[0]**args[1]
        if name == 'CreateTimer':
            self.timer_serial += 1; self.timers[self.timer_serial] = {'destroyed':False}; return True,self.timer_serial
        if name == 'TimerStart':
            require(args[0] in self.timers and not self.timers[args[0]]['destroyed'], 'TimerStart used a retired timer')
            self.timers[args[0]].update(delay=args[1], periodic=args[2], callback=args[3]); self.timer_starts.append(tuple(args[:4])); return True,None
        if name == 'DestroyTimer':
            require(args[0] in self.timers, 'DestroyTimer unknown handle'); self.timers[args[0]]['destroyed']=True; self.timer_destroys.append(args[0]); return True,None
        if name == 'GetExpiredTimer': return True,self.expired_timer
        if name in ('TriggerRegisterPlayerUnitEvent', 'TriggerAddAction'):
            self.trigger_events.append((name,*args)); return True,None
        if name == 'CreateUnit':
            attempt=len(self.creations)+1
            if self.fail_creation_at == attempt: self.creations.append(None); return True,None
            self.unit_serial+=1; handle=self.unit_serial
            self.units[handle]={'alive':True,'owner':args[0],'type':args[1],'life':5000000.0,'maxLife':5000000.0,
                                'userdata':0,'speed':260.0,'defaultSpeed':260.0,'x':args[2],'y':args[3],'order':0,
                                'lane':0,'wave':0,'leaked':False,'abilities':{}}
            self.creations.append(handle); self.native_events.append(('create',handle)); return True,handle
        if name in ('RemoveUnit','unit_remove'):
            require(args[0] in self.units, 'Removing unknown unit'); self.units[args[0]].update(alive=False,type=0)
            self.removals.append(args[0]); self.native_events.append(('remove',args[0])); return True,None
        if name in ('SetUnitCreepGuard','RemoveGuardPosition','SetUnitPathing'): return True,None
        if name == 'GetUnitDefaultMoveSpeed': return True,self.units.get(args[0],{}).get('defaultSpeed',0.0)
        if name == 'GetUnitX': return True,self.units.get(args[0],{}).get('x',0.0)
        if name == 'GetUnitY': return True,self.units.get(args[0],{}).get('y',0.0)
        if name == 'GetUnitCurrentOrder': return True,self.units.get(args[0],{}).get('order',0)
        if name == 'SetUnitPosition':
            self.units[args[0]].update(x=args[1],y=args[2]); self.teleports.append(tuple(args[:3])); return True,None
        if name in ('IssuePointOrderById','IssuePointOrder'):
            self.units[args[0]]['order']=args[1]; self.orders.append(tuple(args[:4])); return True,True
        if name == 'SetUnitMoveSpeed':
            self.units[args[0]]['speed']=args[1]; self.moves.append(tuple(args[:2])); return True,None
        if name == 'UnitItemInSlot': return True,self.units.get(args[0],{}).get('inventory',{}).get(args[1])
        if name == 'GetItemTypeId': return True,self.inventory_items.get(args[0],0)
        if name == 'GetUnitName': return True,'Tower '+str(args[0])
        if name == 'GetUnitState':
            require(args[1] in ('life','maxLife'), 'Unmodeled unit state'); return True,self.units[args[0]][args[1]]
        if name in ('unit_getAbilityLevel','GetUnitAbilityLevel'): return True,self.units.get(args[0],{}).get('abilities',{}).get(args[1],0)
        if name in ('unit_addAbility','UnitAddAbility'):
            self.units.get(args[0],{}).setdefault('abilities',{})[args[1]]=1; self.ability_events.append((name,*args[:2])); return True,True
        if name == 'UnitMakeAbilityPermanent':
            return True, args[0] in self.units and args[2] in self.units[args[0]].get('abilities', {})
        if name == 'SetUnitAbilityLevel':
            self.units.get(args[0],{}).setdefault('abilities',{})[args[1]]=args[2]; return True,args[2]
        if name in ('unit_removeAbility','UnitRemoveAbility'):
            self.units.get(args[0],{}).setdefault('abilities',{}).pop(args[1],None); self.ability_events.append((name,*args[:2])); return True,True
        if name == 'SubString': return True,args[0][args[1]:args[2]]
        if name in ('R2SW','R2S'):
            return True,format(args[0],'.'+str(args[2] if len(args)>2 else 1)+'f')
        if name == 'SquareRoot': return True,args[0]**0.5
        if name == 'Sin': return True,__import__('math').sin(args[0])
        if name == 'Cos': return True,__import__('math').cos(args[0])
        if name == 'Atan2': return True,__import__('math').atan2(args[0],args[1])
        if name == 'tdTowerChoiceForUnitTypeId': return False,None
        if name == 'GetUnitTypeId': return True,self.units.get(args[0],{}).get('type',0)
        if name == 'unit_getPos':
            self.globals['unit_getPos_return_y']=self.units.get(args[0],{}).get('y',0.0); return True,self.units.get(args[0],{}).get('x',0.0)
        return super().native(name,args)

    def fire_native_timer(self,timer):
        require(timer in self.timers and 'callback' in self.timers[timer], 'No native callback binding')
        self.expired_timer=timer
        try: return self.invoke(self.timers[timer]['callback'])
        finally: self.expired_timer=None

    def initialize_match(self):
        # Execute the real production initialization spine including hook register.
        self.invoke('tdStartGame')
        self.scheduled.clear() # Bootstrap scheduling is outside this offline match fixture.
        for lane in range(4): self.invoke('tdSetLaneActive',lane,True)
        self.now=10.0

    def enter(self,wave=8):
        self.invoke('tdSetGlobalWave',wave)
        for lane in range(4): self.invoke('tdSetResolvedWave',lane,wave)
        self.globals['TDWaveFlowState_tdFlowPhase']=2
        self.globals['TDWaveFlowState_tdFlowBossWave']=wave
        self.invoke('tdBeginBossIntermission',wave)


def production_contract(script):
    names=set(functions(script)); required={'tdRegisterBossTransitionHook','tdFlowRegisterTransitionHook',
        'tdResetAndRegisterTrialHook','TDTrialHook_onReady','tdTrialStartTargets','tdTrialRemoveTarget',
        'tdTrialRefillBeforeDamage','tdDamageCaptureHit','tdTrialContextValid'}
    require(required<=names, 'Production Trial APIs missing/DCE: '+repr(sorted(required-names)))
    require('new_TDTransitionRuntimeHarness' not in names, 'Dummy-hook test harness must not be released')
    require('alloc_TDTrialHook' in allocations(script), 'Production hook allocator missing')
    array,ident=allocations(script)['alloc_TDTrialHook']
    require(array=='TDBossTransitionHook_typeId' and ident>0, 'Production hook has wrong interface identity')
    ready=functions(script)['dispatch_TDBossTransitionHook_TDBossTransitionHook_onReady'][0]
    require('TDTrialHook_onReady(' in ready, 'Production ready dispatch is empty or not bound to real Trial')
    release=functions(script).get('dispatch_TDBossTransitionHook_TDBossTransitionHook_onRelease')
    require((release is not None and 'TDTrialHook_onRelease(' in release[0]) or 'cyc_tdResumeBossTransition' in names,
            'Production release dispatch missing')
    return {'allocator':{'array':array,'type_id':ident},'registration':'production compiled hook; no dummy callback interception'}


def verify_damage_chain(script):
    r = TrialJassRuntime(script); r.initialize_match(); r.enter(8)
    r.invoke('tdSetupDamageStatistics')
    require(r.globals['DamageEvent_firstUnreducedListeners'][0] != 0 and
            r.globals['DamageEvent_firstUnreducedListeners'][4] != 0,
            'Actual priority0 refill / priority4 credit registrations missing')
    target = r.target(0)
    r.units[103] = {**r.units[101], 'owner': 1, 'abilities': {}}
    r.units[104] = {**r.units[101], 'type': rawcode('uF01'), 'abilities': {}}
    ledger = r.globals['TDDamageState_tdDamageLedger']
    before = [r.invoke('TDDamageLedger_playerTotal', ledger, lane) for lane in range(4)]
    for amount in (0.25, 0.25, 0.25, 123.0):
        r.units[target]['life'] = 15.0
        event = r.emit(amount, source=101, target=target)
        require(event['life'] == 5000000.0 - amount and ('engineLife', target, 5000000.0) in r.events[-2:], 'Priority0 did not refill fixed 5m before native hit')
    require(r.state_call('totalText', 0) == '124', 'Every real positive segment must aggregate before final rounding')
    total = r.state_call('total', 0)
    for source in (103, 104): r.emit(99.0, source=source, target=target)
    r.emit(0.0, source=101, target=target)
    require(r.state_call('total', 0) == total, 'Cross-lane / fake tower / nonpositive damage counted')
    require([r.invoke('TDDamageLedger_playerTotal', ledger, lane) for lane in range(4)] == before,
            'Trial contaminated actual ordinary global damage ledger')
    r.emit(3.0, source=101, target=102)
    require(r.invoke('TDDamageLedger_playerTotal', ledger, 0) == before[0] + 3.0,
            'Ordinary damage stopped crediting its original actual ledger')
    # A rawcode-only unit and an expired registered trial may never fall back.
    r.units[105] = {**r.units[target], 'abilities': {}, 'userdata': 3200}
    r.emit(17.0, source=101, target=105)
    r.now = r.state_call('getDeadline')
    r.emit(17.0, source=101, target=target)
    require(r.state_call('total', 0) == total and r.invoke('TDDamageLedger_playerTotal', ledger, 0) == before[0] + 3.0,
            'Unregistered / expired trial fell back into ordinary scoring')
    return {'cases': 11, 'listeners': {'refill': 0, 'final_credit': 4},
            'ordinary_ledger': 'actual production register/credit/playerTotal executed, unaffected by trial hits',
            'score': '123.75 effective actual segments, rendered 124 after aggregate rounding'}


def credit_lane(r, lane, amount):
    target = r.target(lane * 5)
    token, generation = r.state_call('getToken'), r.state_call('getGeneration')
    ticket = r.state_call('hitTicket',lane,0,target,token,generation,r.now,1000000.0)
    require(ticket != 0 and r.state_call('credit',ticket,lane,amount,r.now) == amount, 'Real lane ticket failed')
    r.invoke('dispatch_TDTrialHitTicket_destroyTDTrialHitTicket',ticket)


def verify_lifecycle(script):
    records = []
    for fail_at in (1,7,20):
        r = TrialJassRuntime(script); r.initialize_match(); r.fail_creation_at = fail_at; r.enter(8)
        created = [unit for unit in r.creations if unit is not None]
        require(len(created) == fail_at - 1 and set(r.removals) == set(created), 'Partial prepare failure leaked native target')
        require(all(r.slots[i] == 0 for i in range(20)) and r.state_call('getPhase') == 0, 'Failed prepare became ACTIVE or retained slots')
        require(all(r.invoke('tdGetGold',lane) == 1000 for lane in range(4)), 'False onReady Game COMPLETED release awarded gold')
        require(len(r.scheduled) == 1 and r.scheduled[0][0] == 30.0, 'False onReady lost ordinary 30 second fallback')
        r.run_timer(r.scheduled[0][1]); require(r.globals['TDState_tdGlobalWave'] == 9, 'False prepare fallback could not advance')
        records.append({'prepare_failure_at':fail_at,'created_removed':len(created),'reward':0})
    r = TrialJassRuntime(script); r.initialize_match(); r.enter(8)
    old_deadline_timer = r.globals['TDTrialHook_tdTrialResumeTimer']
    old_route_timer = r.globals['TDTrialRuntime_tdTrialRouteTimer']
    old_watchdog = r.scheduled[-1][1]
    token, generation = r.state_call('getToken'), r.state_call('getGeneration')
    old_target = r.target(0); r.units[old_target]['alive'] = False; r.event_target = old_target
    r.invoke('tdTrialOnTargetDeath')
    require(r.slots[0] == 0 and len(r.removals) == 1, 'Death did not invalidate/remove old target before scheduling')
    r.initialize_match()
    require(r.state_call('getGeneration') > generation and r.calls['tdResetAndRegisterTrialHook'] == 2, 'Second real TDInit did not reset generation and re-register')
    require(len(r.removals) == 20 and all(r.invoke('tdGetGold',lane)==1000 for lane in range(4)), 'ABORTED reset did not clear all old units zero reward')
    r.enter(8); fresh_slots=[r.slots[i] for i in range(20)]; fresh_count=len(r.creations)
    r.now=r.state_call('getDeadline')
    r.fire_native_timer(old_deadline_timer); r.fire_native_timer(old_route_timer)
    r.run_timer(old_watchdog);r.event_target=old_target;r.invoke('tdTrialOnTargetDeath')
    require(r.state_call('getPhase') == 2 and [r.slots[i] for i in range(20)] == fresh_slots and len(r.creations)==fresh_count and not r.spawn_requests,
            'Old native timer/watchdog/death callback affected the second real match')
    r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer'])
    require(r.state_call('getPhase') == 3 and len(r.removals) == 40, 'Second registered match did not complete native cleanup')
    records.append({'two_real_TDInit_matches':True,'old_callbacks_rejected':['deadline','route','watchdog','death'],'aborted_prize':0})
    # Last route tick is deliberately omitted after leave/defeat.
    for release in ('trialTimerFirst','gameWatchdogFirst'):
        r=TrialJassRuntime(script); r.initialize_match(); r.enter(8)
        credit_lane(r,0,200.0); credit_lane(r,1,100.0)
        r.invoke('tdSetLaneDefeated',0,True)
        r.now=r.state_call('getDeadline')
        if release=='trialTimerFirst':r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer'])
        else:r.run_timer(r.scheduled[-1][1])
        require(r.state_call('isWithdrawn',0) and r.invoke('tdGetGold',0)==1000 and r.invoke('tdGetGold',1)==1240,
                'Final-tick departed leader gained gold or redistributed its frozen ranking place')
        require(r.state_call('rank',0)==0 and r.state_call('rank',1)==1, 'Withdrawn score did not keep ranking occupancy')
        records.append({'release_order':release,'last_tick_departed_leader_gold':0,'remaining_second_place_gold':240})
    return {'cases':records}


def single_batch_retire(r,indices,method):
 before=len(r.scheduled)
 if method=='exit':
  for i in indices:
   binding=r.binding(i);lane=i//5;target=r.target(i)
   r.globals['TDTrialBinding_waypoint'][binding]=r.invoke('tdLaneWaypointCount',lane)
   x=r.invoke('tdLaneExitPosition',lane);y=r.globals['tdLaneExitPosition_return_y']
   r.units[target].update(x=x,y=y)
  r.invoke('tdTrialTickTargets')
 else:
  for i in indices:
   target=r.target(i);r.units[target]['alive']=False;r.event_target=target
   r.invoke('tdTrialOnTargetDeath')
 require(all(r.slots[i]==0 for i in indices),'Retired target remained registered')
 require(len(r.scheduled)==before,'Single-batch retirement scheduled replacement callback')
 require(len(r.creations)==20 and not r.teleports,'Retirement created or looped targets')

def single_batch_empty_admission(r):
 token,generation=r.state_call('getToken'),r.state_call('getGeneration')
 before=(len(r.creations),r.state_call('targetCount'),r.state_call('targetRevision',0,0),r.invoke('TDTrialTargets_identity',r.globals['TDTrialState_targets'][r.state],0,0))
 require(not r.invoke('tdTrialCreateTarget',0,0,token,generation,r.now),'Empty-slot create accepted ACTIVE')
 require((len(r.creations),r.state_call('targetCount'),r.state_call('targetRevision',0,0),r.invoke('TDTrialTargets_identity',r.globals['TDTrialState_targets'][r.state],0,0))==before,'Empty-slot create allocated or changed registry')
 require(not r.state_call('bindTarget',0,0,999999,token,generation,r.now),'Empty-slot state bind accepted ACTIVE')
 require((len(r.creations),r.state_call('targetCount'),r.state_call('targetRevision',0,0),r.invoke('TDTrialTargets_identity',r.globals['TDTrialState_targets'][r.state],0,0))==before,'Empty-slot bind changed registry')

def verify_single_batch(script):
 report={'production':production_contract(script),'cases':[]}
 for wave in (8,24):
  for method in ('exit','death'):
   for order in ('early','periodicFirstAtDeadline','watchdogFirstAtDeadline'):
    r=TrialJassRuntime(script);r.initialize_match();r.enter(wave)
    require(r.state_call('targetCount')==20 and len(r.creations)==20,'Not exactly five per participant')
    token,generation=r.state_call('getToken'),r.state_call('getGeneration')
    timer=r.globals['TDTrialHook_tdTrialResumeTimer'];route=r.globals['TDTrialRuntime_tdTrialRouteTimer'];watchdog=r.scheduled[-1][1]
    require(r.timers[timer]['periodic'] and r.timers[timer]['delay']==.20,'Resume does not use existing periodic timer')
    require(not r.invoke('tdTrialCreateTarget',0,0,token,generation,r.now) and not r.state_call('bindTarget',0,0,900001,token,generation,r.now),'ACTIVE admission accepted')
    ready=r.calls['TDTrialHook_onReady'];r.invoke('tdBeginBossIntermission',wave)
    require(not r.invoke('tdFlowCallTransitionReady',wave,token) and r.calls['TDTrialHook_onReady']==ready,'Session reentered')
    for lane in range(4):credit_lane(r,lane,(4-lane)*100.)
    r.now=20.;single_batch_retire(r,range(5),method);single_batch_empty_admission(r);r.fire_native_timer(timer)
    require(r.state_call('getPhase')==2 and r.state_call('laneCompleted',0) and r.state_call('targetCount')==15,'One completed lane ended other lanes')
    r.invoke('tdTrialPrepareHud',r.state,r.now)
    require(r.invoke('tdTrialHudCell',1,3)=='已完成 · 等待其他路','Completed lane HUD changed')
    r.now=30.;single_batch_retire(r,range(5,20),method)
    require(r.state_call('getPhase')==2 and r.state_call('targetCount')==0,'Last retirement settled synchronously')
    if order=='early':r.fire_native_timer(timer)
    else:
     r.now=r.state_call('getDeadline')
     if order=='periodicFirstAtDeadline':r.fire_native_timer(timer);r.run_timer(watchdog)
     else:r.run_timer(watchdog);r.fire_native_timer(timer)
    require(r.state_call('getPhase')==3 and len(r.removals)==20 and len(set(r.removals))==20,'Settlement cleanup/reentry changed')
    require(r.globals['TDState_tdGlobalWave']==wave+1 and r.spawn_requests==[(lane,wave+1) for lane in range(4)],'Next wave not once')
    prizes=[r.invoke('tdGetGold',lane)-1000 for lane in range(4)]
    require(prizes==[x*(1 if wave==8 else 2) for x in (300,240,180,120)],'Current ranking prizes changed')
    require(r.state_call('averageDps',0,999.)==400./(20. if order=='early' else 120.),'Sealed elapsed is not actual/capped')
    starts=len(r.timer_starts);r.now=r.state_call('getDeadline')
    r.fire_native_timer(timer);r.fire_native_timer(route);r.run_timer(watchdog)
    require(len(r.creations)==20 and len(r.removals)==20 and len(r.spawn_requests)==4 and len(r.timer_starts)==starts,'Old callback created/paid/restarted')
    require(all(r.invoke('tdGetLives',lane)==20 for lane in range(4)),'Retirement leaked normal lives')
    report['cases'].append({'wave':wave,'retire':method,'order':order,'created':20,'removed_once':20,'prizes':prizes,'next_wave_once':wave+1})
  # No exhaustion at the deadline still clears the remaining original batch.
  for order in ('periodicFirst','watchdogFirst'):
   r=TrialJassRuntime(script);r.initialize_match();r.enter(wave);credit_lane(r,0,10.)
   timer=r.globals['TDTrialHook_tdTrialResumeTimer'];watchdog=r.scheduled[-1][1]
   r.now=r.state_call('getDeadline')
   if order=='periodicFirst':r.fire_native_timer(timer);r.run_timer(watchdog)
   else:r.run_timer(watchdog);r.fire_native_timer(timer)
   require(r.state_call('targetCount')==0 and len(r.removals)==20 and len(r.creations)==20 and len(r.spawn_requests)==4,'120-second cap failed')
   report['cases'].append({'wave':wave,'unexhausted_cap_order':order,'remaining_cleared':20})
  # Actual player-leave public path, rather than manually withdrawing state.
  r=TrialJassRuntime(script);r.initialize_match();r.enter(wave)
  for lane in range(4):credit_lane(r,lane,10.)
  for lane in range(4):r.invoke('tdHandleLanePlayerLeft',lane)
  require(r.invoke('tdIsGameOver') and r.state_call('getPhase')==3 and r.state_call('targetCount')==0 and len(r.removals)==20,'All-leave abort failed')
  require(all(r.invoke('tdGetGold',lane)==1000 for lane in range(4)) and not r.spawn_requests,'All-leave awarded or advanced')
  report['cases'].append({'wave':wave,'all_players_left_abort':True,'prizes':0,'next_wave':0})
 # Two independent compiled-phase-guard mutations must expose the empty-slot check.
 mutations=[]
 for name,pattern in [('TDTrialState_bindTarget',r'TDTrialState_phase\[[^\]]+\] != TDTrialRules_TD_TRIAL_PREPARING'),('tdTrialCreateTarget',r'dispatch_TDTrialState_TDTrialState_getPhase\([^\n]+?\) != TDTrialRules_TD_TRIAL_PREPARING')]:
  body=functions(script)[name][4];changed,n=re.subn(pattern,'false',body);require(n==1,'Unique phase mutation missing')
  r=TrialJassRuntime(script.replace(body,changed,1));r.initialize_match();r.enter(8);single_batch_retire(r,range(5),'death')
  try:single_batch_empty_admission(r)
  except ValueError as e:require('Empty-slot' in str(e),'Unrelated phase-guard negative failure')
  else:raise ValueError('Compiled ACTIVE phase guard mutation survived')
  mutations.append(name)
 report['empty_slot_phase_guard_mutations_rejected']=mutations
 for wave in (8,24):
  r=TrialJassRuntime(script);r.initialize_match();r.enter(wave)
  for lane in range(4):credit_lane(r,lane,(4-lane)*100.)
  r.now=30.;single_batch_retire(r,range(15),'death')
  r.invoke('tdHandleLanePlayerLeft',3);r.invoke('tdTrialTickTargets')
  require(r.state_call('targetCount')==0 and r.state_call('getPhase')==2,'Last leave did not vacate exactly its five slots')
  r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer'])
  require(r.state_call('getPhase')==3 and r.invoke('tdGetGold',3)==1000 and r.globals['TDState_tdGlobalWave']==wave+1 and len(r.spawn_requests)==3,'Early last-leave release/reward failed')
  report['cases'].append({'wave':wave,'last_unexhausted_lane_left':True,'withdrawn_gold':0,'next_wave_once':wave+1})
  r=TrialJassRuntime(script);r.initialize_match();r.enter(wave)
  handles=[r.target(i) for i in range(20)]
  # Missing native death delivery: native RemoveUnit leaves the stale binding.
  for target in handles:r.call('RemoveUnit',[target])
  r.invoke('tdTrialTickTargets')
  require(r.state_call('targetCount')==0 and all(r.slots[i]==0 for i in range(20)) and len(r.creations)==20,'Missing-death stale native handles remained or refilled')
  r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer'])
  require(r.state_call('getPhase')==3 and len(r.spawn_requests)==4,'Missing-death empty pool did not release')
  report['cases'].append({'wave':wave,'missing_death_native_removals_cleaned':20,'replacement_creates':0})
 report['boundary']='Exact packed trial/Game/Flow/HUD/cleanup execution; native clocks/timers/movement/units/collections are controlled. No Warcraft launch.'
 return report


def verify_routes(script):
    if 'TDTrialState_laneCompleted' in functions(script):
        return verify_single_batch(script)
    r=TrialJassRuntime(script); r.initialize_match(); r.enter(8)
    start_orders=len(r.orders); r.invoke('tdTrialTickTargets')
    require(len(r.orders)==start_orders,'Uninterrupted targets were forcibly reordered every tick')
    for index in range(20):
        binding=r.binding(index); lane=index//5; target=r.target(index)
        waypoint=r.globals['TDTrialBinding_waypoint'][binding]
        x=r.invoke('tdLaneWaypointPosition',lane,waypoint); y=r.globals['tdLaneWaypointPosition_return_y']
        r.units[target].update(x=x,y=y)
    r.invoke('tdTrialTickTargets')
    require(all(r.globals['TDTrialBinding_waypoint'][r.binding(i)]==1 for i in range(5)) and all(r.globals['TDTrialBinding_waypoint'][r.binding(i)]==0 for i in range(5,20)), 'Actual five-waypoint lane / three direct lanes did not follow formal route shape')
    r.teleports.clear()
    for index in range(20):
        binding=r.binding(index); lane=index//5; target=r.target(index)
        r.globals['TDTrialBinding_waypoint'][binding]=r.invoke('tdLaneWaypointCount',lane)
        x=r.invoke('tdLaneExitPosition',lane); y=r.globals['tdLaneExitPosition_return_y']
        r.units[target].update(x=x,y=y)
    r.invoke('tdTrialTickTargets')
    require(len(r.teleports)==20 and not r.removals and all(r.globals['TDTrialBinding_waypoint'][r.binding(i)]==0 for i in range(20)), 'Exit loop killed/leaked/replaced units instead of native same-slot reset')
    require(all(r.invoke('tdGetLives',lane)==20 for lane in range(4)), 'Loop consumed normal lane lives')
    old=r.target(0); old_binding=r.binding(0); old_revision=r.globals['TDTrialBinding_revision'][old_binding]
    r.units[old]['alive']=False;r.event_target=old;r.invoke('tdTrialOnTargetDeath');callback=r.scheduled[-1][1]
    r.run_timer(callback)
    require(r.target(0)!=old and r.globals['TDTrialBinding_revision'][r.binding(0)]>old_revision and r.state_call('targetCount')==20,'Abnormal death did not refill exactly its invalidated slot')
    count=len(r.creations);r.run_timer(callback);require(len(r.creations)==count,'Repeated death callback grew beyond 5 targets/lane')
    r.invoke('tdSetLaneDefeated',2,True);r.invoke('tdTrialTickTargets')
    require(r.state_call('isWithdrawn',2) and all(r.slots[i]==0 for i in range(10,15)) and r.state_call('targetCount')==15,'Departed lane did not clear exactly its five native slots')
    return {'slots':20,'waypoint_advances':5,'native_exit_loops':20,'life_loss':0,'death_replacement_slots':1,'repeat_death_spawn':0,'lane_leave_removed':5}


def verify_debuff_and_late_proc(script):
    if 'TDPetData_TD_PET_SKILL_COUNT = 49' in script:
        return verify_final_debuff_and_late_proc(script)
    r=TrialJassRuntime(script);r.initialize_match();r.enter(8);target=r.target(0)
    r.invoke('tdPetSetupCombat')
    current40 = 'tdEnemySlowOfferTimed' in r.functions
    phase_one = 'tdPetApplyAttackDebuffs' in r.functions
    pet_debuff_key = 'TDPetAttackState_targets' if phase_one else 'TDPetCombat_debuffs'
    if phase_one:
        pet=r.invoke('new_TDPet',0,1,8)
        r.globals['TDPet_host'][pet]=101;r.globals['TDPet_generation'][pet]=1
        r.globals['TDPetState_tdPets'][0]=pet
    if current40:
        r.invoke('tdEnemySlowOfferTimed', target, 101, 12, 1, .5, 3.0)
        if phase_one: r.invoke('tdPetApplyAttackDebuffs',pet,101,target,2.0,0)
        else: r.invoke('applyArmor', target, 2.0)
        record = r.invoke('tdAuraTargetFor', target)
        require(r.units[target]['speed']==130.0 and record != 0, 'Unified actual slow did not compose base260 slow0.5')
    else:
        r.invoke('applySlow',target,0.5,3.0,0)
        periodic=r.periodics[-1][1];r.invoke('call_doPeriodically_TDPetCombat',periodic,periodic)
        require(r.units[target]['speed']==130.0 and r.tables[r.globals['TDPetState_tdPetEnemySlowFactors']][target]==0.5,'Real pet debuff tick did not compose base260 slow0.5')
    r.invoke('tdEquipmentDebuffFor',target,0)
    require(len(r.lists[r.globals[pet_debuff_key]])==1 and len(r.lists[r.globals['TDEquipmentCombat_tdEquipmentDebuffs']])==1,'Real debuff record creation missing')
    if current40:
        r.invoke('tdForgetAuraTarget', target)
    r.invoke('tdPetForgetEnemy',target)
    require(r.units[target]['speed']==260.0 and not r.lists[r.globals[pet_debuff_key]], 'Explicit single-target cleanup did not restore260 and remove pet state')
    if current40:
        require(r.invoke('tdAuraTargetFor', target)==0, 'Explicit cleanup retained unified slow record')
    else:
        require(target not in r.tables[r.globals['TDPetState_tdPetEnemySlowFactors']], 'Legacy slow state survived cleanup')
    # Keep another real debuff on target through normal release to prove adapter cleanup.
    if current40:
        r.invoke('tdEnemySlowOfferTimed', target, 101, 13, 1, .25, 3.0)
        if phase_one: r.invoke('tdPetApplyAttackDebuffs',pet,101,target,2.0,0)
        else: r.invoke('applyArmor', target, 2.0)
    else:
        r.invoke('applySlow',target,0.25,3.0,1)
    if not phase_one: pet=r.invoke('new_TDPet',0,1,8)
    r.globals['TDPet_host'][pet]=101;r.globals['TDPet_generation'][pet]=1
    r.globals['TDPetState_tdPets'][0]=pet
    r.globals['TDPet_level'][pet]=3
    r.invoke('TDPet_setSkill',pet,0,0,1)
    r.invoke('TDPet_setSkill',pet,1,6,1)
    r.invoke('TDPet_setSkill',pet,2,13,1)
    require(r.globals['TDPet_skillCount'][pet]==3 and r.invoke('TDPet_skillAt',pet,2)==13,'Real active AoE pet skill fixture invalid')
    # The real early/final listener (according to the artifact) creates all captures.
    r.emit(100.0,source=101,target=target)
    callback=r.scheduled[-1][1]
    require(r.globals['TDPet_pendingSkill'][pet] and r.calls['onAttack']==1,'Real attack did not schedule pending production AoE')
    r.now=r.state_call('getDeadline');r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer'])
    require(not r.lists[r.globals[pet_debuff_key]] and not r.lists[r.globals['TDEquipmentCombat_tdEquipmentDebuffs']], 'Real release left native debuff records populated')
    if current40:
        require(r.invoke('tdAuraTargetFor', target)==0, 'Real release left unified timed-slow target')
    else:
        require(not r.tables[r.globals['TDPetState_tdPetEnemySlowFactors']], 'Real release left legacy slow table')
    # New ordinary-wave units are placed at the old stored AoE center.
    r.units[106]={**r.units[102],'type':rawcode('uW09'),'life':500.0,'alive':True,'abilities':{},'userdata':900}
    before_hits=len(r.native_damage);before_groups=r.calls['group_enumUnitsInRange'];ready=r.globals['TDPet_readyAt'][pet]
    r.run_timer(callback)
    require(len(r.native_damage)==before_hits and r.calls['group_enumUnitsInRange']==before_groups and r.globals['TDPet_readyAt'][pet]==ready and not r.globals['TDPet_pendingSkill'][pet], 'Old trial AoE proc enumerated/damaged new wave or spent cooldown')
    r.globals['TDPet_pendingSkill'][pet]=True;r.globals['TDPet_pendingSerial'][pet]+=1
    r.run_timer(callback)
    require(r.globals['TDPet_pendingSkill'][pet], 'Old invalid proc cleared a new serial pending proc')
    return {'slow':{'base':260,'active':130,'explicit_cleanup_restored':260},'release_debuff_records':0,
            'old_trial_aoe_new_wave_damage':0,'old_proc_new_pending_serial_preserved':True,
            'capture':'Actual onAttack + listener captured epoch/generation/token/revision and center; no fabricated closure'}


def verify_final_debuff_and_late_proc(script):
    # Use the existing exact original-post timer/fence runtime for current casts,
    # not the older retired slot0=0/slot2=13 fixture or direct post simulation.
    from VerifyPetAttackArtifact import PetAttackRuntime
    for new_serial in (False, True):
        r=PetAttackRuntime(script);r.auto_post=False;r.enter(8)
        target=r.target(0);pet=r.pet([(38,4)])
        r.invoke('tdEnemySlowOfferTimed',target,101,12,1,.5,3.)
        r.invoke('tdPetApplyAttackDebuffs',pet,101,target,2.,0)
        r.invoke('tdEquipmentDebuffFor',target,0)
        require(r.units[target]['speed']==130. and r.invoke('tdAuraTargetFor',target)!=0,'Real current slow did not compose base260')
        r.emit(100.,target=target)
        require(r.globals['TDPet_pendingSkill'][pet] and r.calls['onAttack']==1,'Legal current AoE did not capture a pending packet')
        r.now=r.state_call('getDeadline');r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer'])
        require(not r.lists[r.globals['TDPetAttackState_targets']] and
                not r.lists[r.globals['TDEquipmentCombat_tdEquipmentDebuffs']] and
                r.invoke('tdAuraTargetFor',target)==0,'Release retained a real target debuff record')
        r.units[106]={**r.units[102],'type':rawcode('uW09'),'life':500.,'alive':True,'abilities':{},'userdata':900}
        if new_serial:r.globals['TDPet_pendingSerial'][pet]+=1
        before=len(r.native_damage);groups=r.calls['group_enumUnitsInRange'];ready=r.globals['TDPet_readyAt'][pet]
        r.flush()
        require(len(r.native_damage)==before and r.calls['group_enumUnitsInRange']==groups and
                r.globals['TDPet_readyAt'][pet]==ready,'Old trial cast hit/enumerated a new wave or spent CD')
        require(r.globals['TDPet_pendingSkill'][pet] is new_serial,'Old packet cleared a different pending serial or leaked its own')
    return {'slow':{'base':260,'active':130},'release_debuff_records':0,
            'old_trial_aoe_new_wave_damage':0,'old_proc_new_pending_serial_preserved':True,
            'fixture':'Legal earth38Q4; actual original post/queue captured before real trial release; no retired skills'}


def verify_exact_hud(script):
    r=TrialJassRuntime(script);r.initialize_match();r.enter(24)
    for lane in (0,1):
        score=r.invoke('TDTrialState_scores_get',r.state,lane)
        for _ in range(2148):require(r.invoke('TDTrialScore_add',score,1000000.0),'Actual score addition failed below bound')
    score=r.invoke('TDTrialState_scores_get',r.state,0);r.invoke('TDTrialScore_add',score,1.0)
    require(r.state_call('totalText',0)=='2148000001' and r.state_call('totalText',1)=='2148000000','Actual exact decimal text lost >2^31 one-point difference')
    require(r.state_call('rank',0)==0 and r.state_call('rank',1)==1,'Actual rank tied scores one point apart above2^31')
    r.invoke('tdTrialPrepareHud',r.state,r.now)
    require(r.invoke('tdTrialHudCell',1,1)=='2148000001' and r.invoke('tdTrialHudCell',2,1)=='2148000000','HUD and actual ranking keys differ')
    r.now=r.state_call('getDeadline');r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer'])
    require(r.invoke('tdGetGold',0)==1600 and r.invoke('tdGetGold',1)==1480,'Above2^31 distinct ranks failed fixed round2 prizes')
    return {'actual_score_additions':4297,'exact_totals':['2148000001','2148000000'],'hud_rank_reward_consistent':True,
            'native_precision_boundary':'Accumulation operands stay below2^21; arbitrary fractional float32 behavior is not emulated by this scalar interpreter'}


def verify_equipment_segments(script):
    r=TrialJassRuntime(script);r.initialize_match();r.enter(8)
    r.invoke('tdEnsureItemCatalog');current40='tdEnemySlowOfferTimed' in r.functions
    r.inventory_items[90001]=rawcode('iP02' if current40 else 'iB02');r.units[101]['inventory']={0:90001}
    r.invoke('tdSetupEquipmentCombat');r.invoke('tdSetupDamageStatistics')
    target=r.target(0)
    require(not r.invoke('tdIsBossUnitTypeId',rawcode('uTrG')), 'Trial contaminated normal Boss whitelist')
    r.emit(100.0,source=101,target=target);callback=r.scheduled[-1][1]
    require(r.scheduled[-1][0]==0.01 and r.state_call('total',0)==100.0,'Actual Boss-only equipment did not schedule trial additional segment')
    r.run_timer(callback)
    require(r.state_call('total',0)==125.0 and len(r.native_damage)==1,'Real in-round trial equipment additional segment did not execute/credit25%')
    r.emit(100.0,source=101,target=target);late=r.scheduled[-1][1]
    r.units[target]['alive']=False;r.event_target=target;r.invoke('tdTrialOnTargetDeath')
    require(r.slots[0]==0 and r.state_call('targetCount')==19 and len(r.creations)==20,'Single-batch equipment target replenished')
    replacement=r.adversarial_rebind(0);before=len(r.native_damage);score=r.state_call('total',0);r.run_timer(late)
    require(replacement!=target and len(r.native_damage)==before and r.state_call('total',0)==score,'Old equipment segment retargeted into replacement slot')
    r.emit(100.0,source=101,target=replacement);sealed_late=r.scheduled[-1][1]
    r.now=r.state_call('getDeadline');r.fire_native_timer(r.globals['TDTrialHook_tdTrialResumeTimer']);before=len(r.native_damage);r.run_timer(sealed_late)
    require(len(r.native_damage)==before,'Sealed trial equipment segment hit new ordinary wave')
    return {'normal_boss_whitelist_excludes_trial':True,'actual_equipment_id':'iP02' if current40 else 'iB02','actual_trial_bonus':25,'actual_delayed_segment_credited':25,
            'registry_adversary_old_handle_damage':0,'post_release_segment_damage':0}


def verify_current_capture(script):
    """Current real capture helper with one proved local-identifier view.

    The historical oracle binds a fixed lane variable. The current lane comes
    from its actual typed local declaration and exact GetPlayerId/owner site;
    only that identifier in this one function is changed for the old parser.
    Constants, predicates, call targets, values and every other function stay
    untouched. This is a read-only check view, never a JASS/MPQ rewrite.
    """
    from VerifyCaptureRemovalArtifact import verify_spend_and_attempt
    body = functions(script)['tdPetHandleCapture'][0]
    lane_sites = re.findall(r'^\s*set (\w+) = GetPlayerId\(GetOwningPlayer\((\w+)\)\)\s*$', body, re.M)
    require(len(lane_sites) == 1, 'Capture has no unique actual lane-owner site')
    lane, farmer = lane_sites[0]
    require(re.search(r'^\s*local integer ' + re.escape(lane) + r'\b', body, re.M) is not None and
            re.search(r'^\s*local unit ' + re.escape(farmer) + r'\b', body, re.M) is not None,
            'Capture lane/farmer owner lacks typed local provenance')
    require('tdPetSpendCaptureBall(' + lane + ',' in body and 'tdPetStore(' + lane + ',' in body, 'Capture uses different spend/store lane')
    require(lane == 'lane_2' or not re.search(r'\blane_2\b', body), 'Capture alias view would collide')
    view = re.sub(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*', lambda m: 'lane_2' if m[0] == lane else m[0], body)
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        verify_spend_and_attempt(script.replace(body, view, 1), capacity=20, capture_percent=65)
    return {'status': 'PASS', 'actual_lane_identifier': lane, 'typed_lane_view': 'lane_2',
            'actual_compiled_cases': '120 spend eligibility/charge cases; tutorial guarantee/used flags; 200 ordinary65% roll cases; explicit one refund + sync after failed store',
            'scope': 'Actual current capture bodies, no gameplay values/control-flow normalization'}


def verify_replay(script):
    binding=production_contract(script)
    records=[]
    for wave in (8,24):
        for order in ('trialTimerFirst','gameWatchdogFirst'):
            r=TrialJassRuntime(script); r.initialize_match(); r.enter(wave)
            require(r.state_call('getPhase')==2 and len([r.slots[i] for i in range(20) if r.slots[i]])==20,'Real production ready did not activate 20 native slots')
            require(len(r.creations)==20 and len(set(r.creations))==20,'Real independent target creation count differs')
            targets=[r.target(i) for i in range(20)]
            require(all(not r.invoke('tdEnemyBelongsToCurrentMatch',target) for target in targets),'Trial polluted ordinary match registration')
            require(r.calls['TDTrialHook_onReady']==1,'Real concrete onReady not executed exactly once')
            token=r.state_call('getToken'); generation=r.state_call('getGeneration')
            # Real per-event ticket and public accounting function, then engine listeners below.
            ticket=r.state_call('hitTicket',0,0,targets[0],token,generation,r.now,1000000.0)
            require(ticket!=0 and r.state_call('credit',ticket,0,123.0,r.now)==123.0,'Real trial score could not credit')
            r.invoke('dispatch_TDTrialHitTicket_destroyTDTrialHitTicket',ticket)
            deadline=r.state_call('getDeadline'); r.now=deadline
            native_timer=r.globals['TDTrialHook_tdTrialResumeTimer']
            watchdog=r.scheduled[-1][1]
            if order=='trialTimerFirst': r.fire_native_timer(native_timer); r.run_timer(watchdog)
            else: r.run_timer(watchdog); r.fire_native_timer(native_timer)
            require(r.state_call('getPhase')==3 and r.state_call('targetCount')==0 and all(r.slots[i]==0 for i in range(20)),'Release failed state/native cleanup')
            require(len(r.removals)==20 and len(set(r.removals))==20,'Release did not remove every target exactly once')
            require(r.invoke('tdGetGold',0)==(r.globals['TDConfig_TD_STARTING_GOLD'] if 'TDConfig_TD_STARTING_GOLD' in r.globals else 1000)+300*(1 if wave==8 else 2),'Release prize not applied exactly once')
            require(r.globals['TDState_tdGlobalWave']==wave+1 and r.spawn_requests==[(lane,wave+1) for lane in range(4)],'Real synchronous resume/release did not open 9/25 once')
            r.fire_native_timer(native_timer); r.run_timer(watchdog)
            require(len(r.removals)==20 and len(r.spawn_requests)==4,'Repeated native/watchdog callback affected sealed trial')
            records.append({'wave':wave,'order':order,'targets_created':20,'targets_removed':20,'next_wave':wave+1,'resume_synchronous':True})
    damage = verify_damage_chain(script)
    lifecycle = verify_lifecycle(script)
    routes = verify_routes(script)
    debuff_proc = verify_debuff_and_late_proc(script)
    exact_hud = verify_exact_hud(script)
    equipment = verify_equipment_segments(script)
    capture = verify_current_capture(script)
    return {'status':'PASS','production':binding,'cases':records, 'damage_chain':damage, 'lifecycle':lifecycle, 'routes':routes, 'debuff_late_proc':debuff_proc, 'exact_hud':exact_hud, 'equipment_segments':equipment, 'current_capture':capture,
            'boundaries':['Warcraft native unit/timer/rendering boundary modeled; no game launched',
                          'Collections modeled, all gameplay guards, hook dispatch, score, ledger and cleanup ownership execute packaged JASS']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('map');p.add_argument('--output');a=p.parse_args()
    data=Path(a.map).read_bytes();script=Mpq(data).extract('war3map.j').decode();result=verify_replay(script)
    result.update(command=__import__('sys').argv,map_sha256=hashlib.sha256(data).hexdigest(),jass_sha256=hashlib.sha256(script.encode()).hexdigest(),tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if a.output:Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
