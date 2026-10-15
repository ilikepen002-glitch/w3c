#!/usr/bin/env python3
"""Fail-closed tower-target source and actual-MPQ transaction replay.

--source-only executes bounded real Wurst scalar bodies and source contracts.
With a map, transaction, identity, commands, groups and recovery execute extracted
war3map.j through the existing PetAttackRuntime/BossJassRuntime interpreter.
Only native handles, visibility, order return/callback delivery and clock are
controlled boundaries. This does not compile, modify a map or launch Warcraft,
measure client DPS, or prove engine turning/attack-point/trigger timing.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import re
import sys

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyPetAttackArtifact import PetAttackRuntime, near
from VerifyDamageRankingJass import functions
from VerifyBuilderControlDelta import allocations
from VerifyPetManagerSource import compile_source_helper, function_body
from VerifyTowerUpgradeArtifact import rawcode

ROOT = Path(__file__).resolve().parents[1]
RULES = 'towers/TDTowerTargetPriorityRules.wurst'
STATE = 'towers/TDTowerTargetPriorityState.wurst'
RUNTIME = 'towers/TDTowerTargetPriorityRuntime.wurst'
TOWER = 'towers/TDTowerRuntime.wurst'
INVENTORY = 'items/TDInventoryRuntime.wurst'
FAMILIES = {'A': 1, 'O': 2, 'H': 3, 'D': 4, 'G': 5}
TOWERS = tuple('u' + family + suffix for family in FAMILIES
               for suffix in ('11', '12', '13', '14', '15', '6A', '6B'))
BASELINE_SHA256 = '59a519fbb47761840320241f08a3b95e8a717cd38fb603e5da0911abf9a3a8eb'
ARCHERS = tuple(t for t in TOWERS if t[1] == 'A')
SCRIPTED_TOWERS = tuple(t for t in TOWERS if t[1] != 'A')
BOUNDARY = ('Offline execution of actual source/packed JASS with controlled native '
            'order results, callback interleavings, visibility, handles/groups and clock. '
            'No Warcraft launch, native attack-point/turning timings, client DPS, FPS '
            'or multiplayer synchronization measurement.')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_files(path):
    root = Path(path).resolve()
    if (root / 'wurst').is_dir():
        root /= 'wurst'
    return {p.relative_to(root).as_posix(): p.read_text(encoding='utf-8')
            for p in sorted(root.rglob('*.wurst'))
            if not set(p.relative_to(root).parts) & {'_tests', '_build', 'dependencies'}}


def code(text):
    return '\n'.join(line.split('//', 1)[0].rstrip() for line in text.splitlines()
                     if line.split('//', 1)[0].strip())


def body(text, name):
    return function_body(text, name)[1]


def ordered(text, snippets, label):
    start = 0
    for snippet in snippets:
        found = text.find(snippet, start)
        require(found >= 0, label + ': missing/out-of-order ' + snippet)
        start = found + len(snippet)


def verify_source_contract(files):
    for name in (RULES, STATE, RUNTIME, TOWER, INVENTORY, 'TDGame.wurst', 'TDState.wurst'):
        require(name in files, 'Missing production target-priority owner: ' + name)
    rules, state, runtime, tower = [code(files[p]) for p in (RULES, STATE, RUNTIME, TOWER)]
    region = rules + '\n' + state + '\n' + runtime
    require(not re.search(r'GetRandom|GetLocalPlayer|DamageEvent|damageTarget\(|UnitDamageTarget|'
                          r'setLife\(|setHP\(|SetWidgetLife|SetUnitState|doAfter\(|CreateTimer\(', region),
            'Priority code contains RNG, local-player, damage, HP compensation or per-attack timer')
    require(runtime.count('doPeriodically(') == 1, 'Recovery must have one shared periodic owner')
    require(runtime.count('enumUnitsInRange(') == 1 and 'enumUnitsInRect(' not in runtime,
            'Priority must have one local selector, no full-map scan')
    require(not re.search(r'TD_TARGET_PRIORITY_(?:EMERGENCY|MAX_SPEED|MAX_COORDINATE|ROUTE_)|tdTargetPriority(?:EnemyEta|Emergency|Urgent|DistanceEta|PrepareGeometry|Geometry|Suffix|Waypoint)|tdEnemyHasActiveMovementControl', region), 'Retired route interception code remains')
    imports = re.findall(r'^import (\w+)', state, re.M)
    require(set(imports) <= {'Table', 'LinkedList'}, 'Low state layer introduced a high-level dependency')
    require('return hp < bestHp' in body(rules, 'tdTargetPriorityStrictlyBetter') and
            'rank > bestRank' in body(rules, 'tdTargetPriorityStrictlyBetter'),
            'Strict HP/rank comparator contract changed')
    require('key < bestKey' in body(rules, 'tdTargetPriorityReplace') and
            'not keepCurrent' in body(rules, 'tdTargetPriorityReplace'), 'Tie/current stability changed')
    for literal in ('TD_TARGET_PRIORITY_RECOVERY_TICK = 0.10',
                    'TD_TARGET_PRIORITY_RECOVERY_INTERVAL = 0.50',
                    'TD_TARGET_PRIORITY_RECOVERY_BUDGET = 4'):
        require(re.search(r'\b' + re.escape(literal) + r'\s*$', rules, re.M), 'Recovery budget constant changed: ' + literal)
    all_code = '\n'.join(code(v) for v in files.values())
    require(all_code.count('registerAnyUnitEvent(EVENT_PLAYER_UNIT_ATTACKED)') == 1,
            'Expected exactly one ATTACKED registration')
    require(all_code.count('GetAttacker()') == 1, 'Extra attacker/ATTACKED side-effect listener')
    wrapper = body(tower, 'tdHandleTowerAttackStarted')
    ordered(wrapper, ('let source = GetAttacker()', 'let target = GetTriggerUnit()',
                     'tdTowerChoiceForUnitTypeId(GetUnitTypeId(source)) == TD_TOWER_CHOICE_ARCHER',
                     'if tdArcherNativeAttackAllowed(source)',
                     'tdHandleArcherSplitArrowAttack(source, target)', 'return',
                     'if not tdTargetPriorityAcceptAttack(source, target)', 'return',
                     'tdHandleArcherSplitArrowAttack(source, target)'), 'ARCHER native ATTACKED wrapper')
    require(re.search(r"if tdTowerChoiceForUnitTypeId\(GetUnitTypeId\(source\)\) == TD_TOWER_CHOICE_ARCHER\s*$", wrapper, re.M),
            'ARCHER catalog branch has a rawcode omission or extra priority condition')
    archer_branch = wrapper[:wrapper.index('if not tdTargetPriorityAcceptAttack')]
    require(not re.search(r'tdTargetPriority(?:Accept|Best|Redirect|Park)|consumePending|Issue\w*Order', archer_branch),
            'ARCHER native start re-enters priority transaction')
    require('tdQueueArcherSplitArrowVolley' not in wrapper and
            wrapper.count('tdHandleArcherSplitArrowAttack(') == 2,
            'Wrapper must have exactly one split call per family branch')
    allowed = body(tower, 'tdArcherNativeAttackAllowed')
    for token in ('source.isAlive()', 'tdIsLaneActive(owner)', 'tdTrialLaneContinues(owner)',
                  'tdPetBusyTowers.hasBoolean(', 'tdTowerSaleStates.hasInt(', 'sale.canSell()',
                  'tdTargetPriorityStateFor(source)', 'lifecycle.owner == owner',
                  'lifecycle.epoch == tdFlowEpoch()', 'not lifecycle.working', 'not lifecycle.casting'):
        require(token in allowed, 'Native ARCHER safety missing: ' + token)
    require(not re.search(r'tdTargetPriorityGet|tdGetTowerSaleState|manualTarget|playerHold|pendingRevision|Issue|\.newIntent|\.consumePending', allowed),
            'Native ARCHER safety mutates or rebuilds a priority token')
    uses = body(rules, 'tdTargetPriorityUsesScriptedPriority')
    require('towerChoice != TD_TOWER_CHOICE_ARCHER' in uses and 'tdTargetPriorityPolicy(towerChoice) != 0' in uses,
            'Scripted priority must exclude exactly the ARCHER family')
    for fn in ('tdTargetPriorityRedirect', 'tdTargetPriorityPark', 'tdTargetPriorityHandleOrder'):
        guarded = body(runtime, fn)
        require('not tdTargetPriorityUsesScriptedPriority(' in guarded and
                guarded.index('not tdTargetPriorityUsesScriptedPriority(') <
                min((guarded.index(t) for t in ('record.beginRedirect(', 'record.newIntent()', 'record.parked = true') if t in guarded), default=len(guarded)),
                'ARCHER priority control guard missing/late: ' + fn)
    for lifecycle_fn in ('tdHandleTowerSellCast', 'tdHandleTowerDeath',
                         'tdHandleTowerConstructionCancelled', 'tdRejectTowerConstruction'):
        require('tdClearTowerSaleState(tower)' in body(tower, lifecycle_fn),
                'Supported tower removal left stale sale state: ' + lifecycle_fn)
    setup = body(tower, 'tdSetupDialogTrigger')
    require('tdSetupTargetPriorityOrders()' in setup, 'Global priority order setup removed')
    require('tdTowerAttackTrigger.addAction(function tdHandleTowerAttackStarted)' in tower,
            'Native ATTACKED trigger bypasses verdict wrapper')
    helper = body(tower, 'tdHandleArcherSplitArrowAttack')
    require('GetAttacker' not in helper and 'GetTriggerUnit' not in helper and
            helper.count('tdQueueArcherSplitArrowVolley(source, target)') == 1,
            'Split helper must use explicit captured source/target')
    validity = body(runtime, 'tdTargetPriorityTargetValid')
    for token in ('target.isAlive()', 'IsUnitEnemy(', 'tdEnemyLaneId(target) != lane',
                  'IsUnitHidden(', 'IsUnitVisible(', 'UNIT_TYPE_MECHANICAL', 'UNIT_TYPE_STRUCTURE',
                  'UNIT_TYPE_GROUND', 'UNIT_TYPE_FLYING', 'range + 0.405',
                  'tdTrialTargetValid(target, lane)', 'tdEnemyBelongsToCurrentMatch(target)',
                  'not tdEnemyWasLeaked(target)'):
        require(token in validity, 'Legal-target contract missing: ' + token)
    ordered(validity, ('if tdTrialIsTargetType(target)', 'return tdTrialTargetValid(target, lane)',
                      'return tdEnemyBelongsToCurrentMatch'), 'Trial versus ordinary identity')
    manual = body(runtime, 'tdTargetPriorityManualValid')
    for token in ('record.manualEpoch', 'record.manualGeneration', 'record.manualToken',
                  'record.manualTrial', 'record.manualRevision', 'tdTrialTargetContextValid('):
        require(token in manual, 'Manual target lost identity snapshot: ' + token)
    select = body(runtime, 'tdTargetPriorityBest')
    require(select.count('enumUnitsInRange(') == 1 and select.count('nearby.destr()') == 1,
            'Selector duplicated local scan or leaked group')
    require('tdTargetPriorityReplace(' in select and '.getLife()' in select and
            'getMaxHP' not in select and 'getMaxLife' not in select, 'Selection is not absolute live HP')
    accept = body(runtime, 'tdTargetPriorityAcceptAttack')
    ordered(accept, ('if record.consumePending()', 'if record.manualTarget != null',
                    'let best = tdTargetPriorityBest(record, target, range)'), 'Pending-first verdict')
    require(accept.count('tdTargetPriorityBest(') == 1, 'Normal selection repeats candidate scan')
    redirect = body(runtime, 'tdTargetPriorityRedirect')
    ordered(redirect, ('record.beginRedirect(candidate)', 'record.scriptOrderDepth += 1',
                       'IssueTargetOrderById(source, Orders.attack, candidate)',
                       'tdTargetPriorityStateFor(source)', 'current.serial != serial',
                       'current.scriptOrderDepth -= 1', 'current.intentRevision != intent',
                       'current.observedRedirectSerial == redirect'), 'Reentrant redirect transaction')
    require(redirect.count('IssueTargetOrderById(') == 1 and 'current.cancelPending()' in redirect,
            'Redirect repeats orders or cannot roll back native false')
    order = body(runtime, 'tdTargetPriorityHandleOrder')
    ordered(order, ('record.scriptOrderDepth > 0', 'Orders.bloodluston', 'record.newIntent()',
                    'tdTargetPriorityUnpark(record)', 'tdTowerEffectiveRangeForTower(source)',
                    'SetUnitAcquireRange(source, range)'), 'External command precedence')
    for token in ('Orders.stop', 'Orders.holdposition', 'Orders.attack', 'Orders.smart',
                  'context.epoch', 'context.generation', 'context.token', 'binding.revision'):
        require(token in order, 'Order/manual contract missing: ' + token)
    for event in ('ISSUED_ORDER', 'ISSUED_POINT_ORDER', 'ISSUED_TARGET_ORDER', 'CHANGE_OWNER'):
        require('EVENT_PLAYER_UNIT_' + event in runtime, 'Missing native command/owner event: ' + event)
    recovery = body(runtime, 'tdTargetPriorityRecoveryTick')
    ordered(recovery, ('IMinBJ(TD_TARGET_PRIORITY_RECOVERY_BUDGET, tdTargetPriorityParked.size())',
                       'for i = 1 to count', 'tdTargetPriorityParked.get(0)',
                       'tdTargetPriorityParked.remove(record)', 'tdTargetPriorityParked.add(record)',
                       'tdTargetPriorityRecoveryDue(now, record.lastRecoveryQuery)',
                       'record.lastRecoveryQuery = now', 'tdTowerEffectiveRangeForTower(record.source)',
                       'tdTargetPriorityBest(record, null, range)', 'tdTargetPriorityUnpark(record)',
                       'SetUnitAcquireRange(source, range)'), 'Sparse round-robin recovery')
    require('tdAuraTowers' not in recovery and 'tdTargetPriorityRecords' not in recovery,
            'Recovery visits normal/all towers')
    start = body(runtime, 'tdTargetPriorityStartRecovery')
    require('tdTargetPriorityParked.isEmpty()' in start and 'destroy cb' in start and
            'tdTargetPriorityRecoveryRunning = false' in start, 'Empty recovery cannot stop shared timer')
    inventory = code(files[INVENTORY])
    require('tdTargetPriorityUsesScriptedPriority(choice) ? tdTargetPriorityProjectedAcquireRange(tower, effectiveRange) : effectiveRange' in inventory,
            'ARCHER equipment range must bypass acquisition pause projection')
    require('if GetUnitAcquireRange(tower) != projectedRange' in inventory and
            'targetState != null and targetState.working' in inventory,
            'Inventory range write optimization or aura working lifecycle lost')
    native_recovery = recovery[recovery.index('if not tdTargetPriorityUsesScriptedPriority('):recovery.index('tdTargetPriorityParked.add(record)')]
    ordered(native_recovery, ('record.cancelPending()', 'tdTargetPriorityUnpark(record)',
                             'tdTowerEffectiveRangeForTower(record.source)',
                             'GetUnitAcquireRange(record.source) != nativeRange',
                             'SetUnitAcquireRange(record.source, nativeRange)', 'continue'),
            'ARCHER stale recovery escape')
    require(not re.search(r'tdTargetPriorityBest|tdTargetPriorityRedirect|Issue\w*Order|SetUnitAcquireRange\([^,]+, 0', native_recovery),
            'ARCHER recovery performs automatic control')
    create = body(tower, 'tdCreateArcherSplitArrowVolley')
    ordered(create, ('tdEquipmentArcherAdditionalArrows(source)', 'for shot in extraShots',
                     'tdLaunchArcherSplitArrowVisual(source, shot.target, shot.flightTime)',
                     'return new TDArcherSplitArrowVolley'), 'Immediate all-arrow launch')
    damage = body(tower, 'tdHandleArcherSplitArrowDamage')
    require('DamageEvent.getUnreducedOriginalAmount()' in damage and
            'DamageEvent.isSpell() or DamageEvent.isCode() or DamageEvent.getId() == TD_ARCHER_SPLIT_ARROW_DAMAGE_EVENT_ID' in damage,
            'Split immutable basis or spell/code/Tspl recursion guard lost')
    for token in ('let victim = shot.target', 'let context = shot.context', 'let revision = shot.targetRevision',
                  'tdDealArcherSplitArrowAttackDamage(source, victim, attackDamage, context, revision)'):
        require(token in damage, 'Deferred split lost copied data: ' + token)
    require(body(tower, 'tdLaunchArcherSplitArrowVisual').count('doPeriodically(0.03)') == 1 and
            'tdArcherVisualTimerRunning' in body(tower, 'tdLaunchArcherSplitArrowVisual') and
            not re.search(r'(?i)(budget|admission|visualcap|visualcount|tokens)', create + body(tower, 'tdLaunchArcherSplitArrowVisual')),
            'All-arrow shared renderer restored an admission budget')
    expiry_delay = body(tower, 'tdArcherSplitArrowVolleyExpireDelay')
    require(expiry_delay.count('0.35') == 4, 'Historical split TTL changed')
    for fn, token in (('tdHandleTowerUpgradeStarted', 'tdTargetPriorityWorkStarted(tower)'),
                      ('tdHandleTowerConstructionStarted', 'tdTargetPriorityWorkStarted(tower)'),
                      ('tdHandleTowerConstructionFinished', 'tdTargetPriorityWorkFinished(tower)'),
                      ('tdHandleTowerUpgradeCancelled', 'tdTargetPriorityWorkFinished(tower)'),
                      ('tdHandleTowerUpgradeFinished', 'tdTargetPriorityWorkFinished(tower)'),
                      ('tdHandleTowerDeath', 'tdTargetPriorityForget(tower)'),
                      ('tdHandleTowerSellCast', 'tdTargetPriorityForget(tower)')):
        require(token in body(tower, fn), 'Lifecycle cleanup missing: ' + fn)
    for fn in ('tdHandleTowerUpgradeStarted', 'tdHandleTowerConstructionStarted',
               'tdHandleTowerConstructionFinished', 'tdHandleTowerUpgradeCancelled',
               'tdHandleTowerUpgradeFinished', 'tdHandleOrcBladestormCast'):
        require('tdTargetPriorityTrackTower(tower)' in body(tower, fn),
                'First lifecycle event cannot publish exclusion: ' + fn)
    ordered(body(tower, 'tdHandleTowerSellCast'), ('state.beginSale()',
            'tdTargetPriorityTrackTower(tower)', 'tdTargetPriorityWorkStarted(tower)',
            'UnitRemoveItem(tower, equipment)', 'tdTargetPriorityForget(tower)', 'tower.remove()'),
            'Sale blocks nested inventory/drop attack callbacks')
    require('tdTargetPriorityGet(source)' in body(runtime, 'tdTargetPriorityTrackTower'),
            'TrackTower does not initialize first lifecycle record')
    require('auras/TDAuraRuntime.wurst' in files and
            'tdTargetPriorityForget(record.target)' in body(code(files['auras/TDAuraRuntime.wurst']), 'tdAuraForget'),
            'External native removal lacks bounded aura cleanup bridge')
    require('tdTargetPriorityClearAll()' in code(files['TDState.wurst']) and
            'tdTargetPriorityClearAll()' in code(files['TDGame.wurst']) and
            'tdTargetPriorityClearLane(playerId)' in code(files['TDGame.wurst']),
            'Match/lane lifecycle cleanup missing')
    require('tdTargetPriorityAcceptAttack' not in body(tower, 'tdHandleArcherSplitArrowDamage'),
            'In-flight damage re-enters target selection')
    require('volley.source == source and volley.primaryTarget == primaryTarget' in
            body(tower, 'tdConsumeArcherSplitArrowVolley'), 'In-flight queue lost source + primary identity')
    require('destroy volley' not in body(tower, 'tdConsumeArcherSplitArrowVolley') and
            'destroy volley' in body(tower, 'tdExpireArcherSplitArrowVolley'),
            'Consume/expiry destruction ownership changed')
    return {'unique_attacked_wrapper': True, 'local_selector_count': 1,
            'shared_recovery_timer_count': 1, 'damage_selection_bridge_count': 0,
            'route_progress_or_speed_priority': False,
            'native_archer_types': list(ARCHERS), 'scripted_priority_types': list(SCRIPTED_TOWERS),
            'historical_ttl_unchanged': True,
            'source_files_sha256': {p: sha(files[p].encode()) for p in (RULES, STATE, RUNTIME, TOWER, INVENTORY,'enemies/TDEnemyControlRuntime.wurst','TDConfig.wurst')}}


def source_scalar_namespace(files):
    namespace = {'RMaxBJ': max, 'SquareRoot': math.sqrt}
    # Read actual constants, then use the reviewed existing bounded source compiler.
    for path in ('TDConfig.wurst', 'TDWaves.wurst', RULES):
        for kind, name, literal in re.findall(r'^(?:public )?constant (int|real) (\w+) = ([^\n]+)',
                                            files[path], re.M):
            if re.fullmatch(r"'\w{4}'", literal):
                namespace[name] = rawcode(literal[1:-1])
            elif re.fullmatch(r'-?\d+(?:\.\d+)?', literal):
                namespace[name] = float(literal) if kind == 'real' else int(literal)
    for name in ('tdIsBossUnitTypeId', 'tdIsBossGuardUnitTypeId'):
        compile_source_helper(files['TDWaves.wurst'], name, namespace)
    for name in ('tdTargetPriorityPolicy', 'tdTargetPriorityRank', 'tdTargetPriorityStrictlyBetter',
                 'tdTargetPriorityEqual', 'tdTargetPriorityReplace', 'tdTargetPriorityRecoveryDue',
                 'tdTargetPriorityUsesScriptedPriority'):
        compile_source_helper(files[RULES], name, namespace)
    return namespace


def verify_rules(invoke):
    count = 0
    for policy, hp, best, rank, best_rank, keep, key, best_key in itertools.product(
            (1, 2), (0., 1., 10., 100.), (0., 1., 10., 100.), range(3), range(3),
            (False, True), (10, 20), (10, 20)):
        better = hp < best if policy == 1 else rank > best_rank
        equal = hp == best if policy == 1 else rank == best_rank
        expected = better or (not keep and equal and key < best_key)
        require(invoke('tdTargetPriorityReplace', policy, hp, rank, key, best, best_rank,
                       best_key, keep) == expected, 'Actual comparator violates strict/current/tie rule')
        count += 1
    require([invoke('tdTargetPriorityPolicy', i) for i in range(6)] == [0, 1, 2, 2, 1, 2],
            'Family policy mismatch')
    require([invoke('tdTargetPriorityUsesScriptedPriority', i) for i in range(7)] ==
            [False, False, True, True, True, True, False], 'Scripted/native family boundary changed')
    for wave in (8, 16, 24, 32):
        require(invoke('tdTargetPriorityRank', rawcode(f'uB{wave:02d}')) == 2, 'Boss priority mismatch')
        require(invoke('tdTargetPriorityRank', rawcode(f'uG{wave:02d}')) == 1, 'Guard priority mismatch')
    for code_ in ('uW01', 'uE04', 'uE12', 'uE20', 'uE28', 'uTr0'):
        require(invoke('tdTargetPriorityRank', rawcode(code_)) == 0, 'Elite/trial unexpectedly promoted')
    require(not invoke('tdTargetPriorityRecoveryDue', .4999, 0.) and
            invoke('tdTargetPriorityRecoveryDue', .50, 0.), 'Half-second query floor changed')
    return {'comparator_cases': count, 'family_policies': [1, 2, 2, 1, 2],
            'boss_guard_normal_ranks': [2, 1, 0], 'live_absolute_hp': True}


def verify_source_mutations(files):
    cases = [
        (RULES, 'package TDTowerTargetPriorityRules', 'package TDTowerTargetPriorityRules\npublic constant real TD_TARGET_PRIORITY_EMERGENCY_SECONDS = 3.0', 'retired threshold reintroduced'),
        (RUNTIME, 'tdTargetPriorityReplace(policy,', 'tdTargetPriorityEmergencyReplace(policy,', 'retired comparator reintroduced'),
        (RULES, 'return hp < bestHp', 'return hp <= bestHp', 'HP tie redirect'),
        (RULES, 'rank > bestRank', 'rank >= bestRank', 'rank tie redirect'),
        (RULES, 'not keepCurrent and', 'keepCurrent and', 'current tie lost'),
        (RULES, 'TD_TARGET_PRIORITY_RECOVERY_BUDGET = 4', 'TD_TARGET_PRIORITY_RECOVERY_BUDGET = 40', 'unbounded recovery'),
        (RUNTIME, 'range + 0.405', 'range + 500.405', 'wrong effective range'),
        (RUNTIME, 'record.beginRedirect(candidate)', 'record.cancelPending()', 'pending not published'),
        (RUNTIME, 'current.observedRedirectSerial == redirect', 'current.observedRedirectSerial == -1', 'sync native-false duplicate'),
        (RUNTIME, 'record.manualRevision', '0', 'trial revision lost'),
        (RUNTIME, 'nearby.destr()', '// leaked group', 'selector group leak'),
        (RUNTIME, 'record.lastRecoveryQuery = now', 'record.lastRecoveryQuery = -100.0', 'recovery floor lost'),
        (RUNTIME, 'let hp = candidate.getLife()', 'let hp = GetRandomReal(0.0, 100.0)', 'RNG comparison'),
        (TOWER, '\tif not tdTargetPriorityAcceptAttack(source, target)',
         '\ttdQueueArcherSplitArrowVolley(source, target)\n\tif not tdTargetPriorityAcceptAttack(source, target)', 'queue before verdict'),
        (TOWER, '\ttdTargetPriorityTrackTower(tower)\n\ttdTargetPriorityWorkStarted(tower)\n\tlet refund',
         '\ttdTargetPriorityWorkStarted(tower)\n\tlet refund', 'sale first-event exclusion'),
        (TOWER, 'function tdHandleArcherSplitArrowDamage()\n',
         'function tdHandleArcherSplitArrowDamage()\n\ttdTargetPriorityAcceptAttack(null, null)\n', 'damage selection bridge'),
    ]
    cases.extend([
        (RULES, 'towerChoice != TD_TOWER_CHOICE_ARCHER and', 'true and', 'archer priority restored'),
        (TOWER, 'if tdArcherNativeAttackAllowed(source)',
         'if tdArcherNativeAttackAllowed(source) and tdTargetPriorityAcceptAttack(source, target)', 'archer accept restored'),
        (TOWER, 'if tdTowerChoiceForUnitTypeId(GetUnitTypeId(source)) == TD_TOWER_CHOICE_ARCHER',
         "if tdTowerChoiceForUnitTypeId(GetUnitTypeId(source)) == TD_TOWER_CHOICE_ARCHER and GetUnitTypeId(source) != 'uA6B'", 'uA6B native branch omitted'),
        (RUNTIME, 'record.cancelPending()\n\t\t\ttdTargetPriorityUnpark(record)',
         'record.cancelPending()\n\t\t\ttdTargetPriorityRedirect(record, null)\n\t\t\ttdTargetPriorityUnpark(record)', 'archer recovery resend'),
        (INVENTORY, ': effectiveRange', ': 0.0', 'archer acquire zero'),
        (TOWER, '\ttdSetupTargetPriorityOrders()', '\t// removed priority setup', 'global priority setup removed'),
        (TOWER, 'function tdLaunchArcherSplitArrowVisual(unit source, unit target, real duration)',
         'function tdLaunchArcherSplitArrowVisual(unit source, unit target, real duration)\n\tlet visualBudget = 6\n\tif tdArcherArrowVisuals.size() >= visualBudget\n\t\treturn', 'visual budget restored'),
        (TOWER, '\t\t\treturn volley', '\t\t\tdestroy volley\n\t\t\treturn volley', 'consume destroys volley'),
        (TOWER, ' or DamageEvent.getId() == TD_ARCHER_SPLIT_ARROW_DAMAGE_EVENT_ID', '', 'Tspl recursion filter removed'),
        (TOWER, 'DamageEvent.getUnreducedOriginalAmount()', 'DamageEvent.getAmount()', 'mutable split damage basis'),
    ])
    rejected = []
    for path, old, new, label in cases:
        require(old in files[path], 'Mutation anchor missing: ' + label)
        changed = dict(files); changed[path] = changed[path].replace(old, new, 1)
        try:
            verify_source_contract(changed)
        except (ValueError, AssertionError):
            rejected.append(label)
        else:
            raise ValueError('Unsafe source mutation accepted: ' + label)
    return rejected


def jass_boolean_expression(expression):
    """Parenthesize JASS's OR-above-AND, retaining lazy evaluation and literals.

    Reuses the repository's documented JASS precedence contract. Parentheses
    and comma-separated call arguments form independent expression groups.
    This changes only the interpreter's read-only expression view, not script.
    """
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_]\w*|\s+|.', expression)
    position = 0
    def group(nested=False):
        nonlocal position
        parts, current = [], []
        while position < len(tokens):
            token = tokens[position]; position += 1
            if token == '(':
                current.append('(' + group(True) + ')')
            elif token == ')':
                require(nested, 'Unbalanced JASS expression close')
                break
            elif token == ',':
                parts.append(current); current = []
            else:
                current.append(token)
        else:
            require(not nested, 'Unclosed JASS expression group')
        parts.append(current)
        rendered = []
        for part in parts:
            ops = {token for token in part if token in ('and', 'or')}
            if len(ops) < 2:
                rendered.append(''.join(part)); continue
            clauses, clause = [], []
            for token in part:
                if token == 'and':
                    clauses.append(''.join(clause).strip()); clause = []
                else:
                    clause.append(token)
            clauses.append(''.join(clause).strip())
            require(all(clauses), 'Malformed JASS Boolean operand')
            rendered.append(' and '.join('(' + clause + ')' for clause in clauses))
        return ','.join(rendered)
    return group()


class TowerTargetRuntime(PetAttackRuntime):
    """Actual packed gameplay, extending only the existing native boundaries."""
    def __init__(self, script, tower_type='uD6B'):
        self.priority_ready = False
        self.priority_available = 'function tdTargetPriorityAcceptAttack takes ' in script
        self.priority_initialized = False
        self.order_result = True
        self.order_callback = None
        self.stop_callback = None
        self.script_orders = []
        self.stop_orders = []
        self.group_queries = []
        self.accepted = []
        self.attacks = []
        self.acquisition = []
        self.order_source = None
        self.order_target = None
        self.issued_order = 0
        self.priority_rng = []
        self.live_groups = set()
        super().__init__(script)
        self.globals.update(bj_MAX_PLAYER_SLOTS=16, UNIT_TYPE_MECHANICAL='mechanical', UNIT_TYPE_STRUCTURE='structure',
                            UNIT_TYPE_GROUND='ground', UNIT_TYPE_FLYING='flying',
                            UNIT_TYPE_STUNNED='stunned', UNIT_TYPE_SNARED='snared',
                            EVENT_PLAYER_UNIT_ISSUED_ORDER='issued', EVENT_PLAYER_UNIT_ISSUED_POINT_ORDER='point',
                            EVENT_PLAYER_UNIT_ISSUED_TARGET_ORDER='target', EVENT_PLAYER_UNIT_CHANGE_OWNER='owner')
        for name in ('init_Orders', 'init_TDTowerTargetPriorityRuntime', 'init_TDTowerRuntime'):
            if name in self.functions:
                self.invoke(name)
        self.priority_ready = True
        if self.priority_available:
            self.invoke('tdSetupTargetPriorityOrders')
        self.units[101].update(type=rawcode(tower_type), x=0., y=1000., order=0, owner=0,
                               abilities={self.globals['TDTowerCatalogData_TD_ARCHER_SPLIT_ARROW_ABILITY_ID']: 1},
                               inventory={})
        self.enemy(102, life=100.)
        self.enemy(103, life=10.)
        self.enemy(104, life=80.)
        self.visible_units = [102, 103, 104]
        # Rendering is an explicit boundary for this gameplay fixture. Record every
        # actual launch; the full-arrow artifact gate executes Fx/recycler separately.
        self.split_visual_launches = []
        self.clear_trace()

    def initialize_match(self):
        # Match reset owns ClearAll, so package-state initialization precedes it.
        if not self.priority_initialized and not self.globals.get('TDTowerTargetPriorityState_tdTargetPriorityRecords'):
            for name in ('init_TDTowerTargetPriorityRules', 'init_TDTowerTargetPriorityState'):
                if name in self.functions:
                    self.invoke(name)
            self.priority_initialized = True
        return super().initialize_match()

    def clear_trace(self):
        for trace in (self.script_orders, self.stop_orders, self.group_queries,
                      self.accepted, self.attacks, self.acquisition, self.priority_rng):
            trace.clear()

    def enemy(self, handle, life=100., lane=0, type_='uW01', x=0., y=1000.):
        self.units[handle] = dict(alive=True, owner=4, type=rawcode(type_), life=life,
                                 maxLife=max(100., life), userdata=lane * 10000 + 100,
                                 x=x, y=y, order=0, lane=lane, wave=1, leaked=False,
                                 abilities={}, inventory={}, speed=260., defaultSpeed=260.,
                                 hidden=False, visible=True, kinds={'ground'})
        self.tables[self.globals['TDSpawn_tdEnemyMatchEpochs']][handle] = self.invoke('tdFlowEpoch')
        return handle

    def tower(self, handle, type_='uD11', lane=0):
        self.units[handle] = dict(self.units[101], type=rawcode(type_), owner=lane,
                                 abilities={}, inventory={}, x=0., y=1000., order=0)
        return handle

    def record(self, source=101):
        return self.invoke('tdTargetPriorityStateFor', source)

    def field(self, name, source=101):
        return self.globals['TDTowerTargetPriorityState_' + name][self.record(source)]

    def attack(self, target=102, source=101):
        old = self.event_source, self.event_target
        self.event_source, self.event_target = source, target
        self.attacks.append((source, target))
        try:
            self.invoke('tdHandleTowerAttackStarted' if self.priority_available else
                        'tdHandleArcherSplitArrowAttack')
        finally:
            self.event_source, self.event_target = old

    def command(self, order, target=None, source=101):
        old = self.order_source, self.order_target, self.issued_order, self.event_target
        self.order_source, self.order_target, self.issued_order, self.event_target = source, target, order, source
        self.units[source]['order'] = order
        try:
            self.invoke('tdTargetPriorityHandleOrder')
        finally:
            self.order_source, self.order_target, self.issued_order, self.event_target = old

    def expression(self, text, scope):
        return super().expression(jass_boolean_expression(text), scope)

    def native(self, name, args):
        if name == 'tdLaunchArcherSplitArrowVisual':
            self.split_visual_launches.append(tuple(args))
            return True, None
        if name == 'GetUnitMoveSpeed':
            return True, self.units.get(args[0], {}).get('speed', 0.)
        if name == 'IsUnitPaused':
            return True, self.units.get(args[0], {}).get('paused', False)
        if name == 'ModuloReal':
            return True, args[0] % args[1]
        if name == 'KillUnit':
            self.units[args[0]].update(alive=False, life=0.)
            return True, None
        if name == 'GetKillingUnit':
            return True, self.event_source
        if name == 'GetAttacker':
            return True, self.event_source
        if name == 'GetIssuedOrderId':
            return True, self.issued_order
        if name == 'GetOrderTargetUnit':
            return True, self.order_target
        if name in ('IsUnitHidden', 'IsUnitVisible'):
            value = self.units.get(args[0], {})
            return True, value.get('hidden', False) if name == 'IsUnitHidden' else value.get('visible', True)
        if name == 'IsUnitEnemy':
            return True, self.units.get(args[0], {}).get('owner', -1) != args[1]
        if name == 'IsUnitType':
            value = self.units.get(args[0], {})
            return True, (not value.get('alive', False)) if args[1] == 'dead' else args[1] in value.get('kinds', {'ground'})
        if name in ('GetRandomReal', 'GetRandomInt') and self.priority_ready:
            self.priority_rng.append((name, tuple(args), self.roll if name == 'GetRandomReal' else None))
        if name == 'IssueTargetOrderById' and self.priority_ready:
            source, order, target = args[:3]
            self.script_orders.append((source, order, target))
            # Native issued-order event may occur before the ATTACKED callback.
            self.command(order, target, source)
            if self.order_callback is not None:
                self.order_callback(self, source, target)
            return True, self.order_result
        if name == 'IssueImmediateOrderById' and self.priority_ready:
            self.stop_orders.append(tuple(args[:2]))
            self.command(args[1], None, args[0])
            if self.stop_callback is not None:
                self.stop_callback(self, args[0])
            return True, True
        if name == 'GetUnitAcquireRange':
            return True, self.units.get(args[0], {}).get('acquireRange', 0.)
        if name == 'SetUnitAcquireRange':
            self.acquisition.append(tuple(args[:2]))
        if name == 'group_enumUnitsInRange' and self.priority_ready:
            self.group_queries.append((self.event_source, self.now, tuple(args)))
        # Execute packed group helpers for both copied for-in iteration and
        # direct consuming iteration. The older cursor fixture only supported
        # groups first passed through group_iterator; native members suffice
        # for both forms and also exercise real copying/destruction ownership.
        if name in ('group_iterator', 'group_next', 'group_hasNext', 'group_close', 'group_destr', 'group_clear'):
            return False, None
        if name == 'IsUnitInGroup': return True, args[0] in self.groups[args[1]]
        if name == 'GroupAddUnit':
            if args[1] not in self.groups[args[0]]: self.groups[args[0]].append(args[1])
            return True, True
        if name == 'FirstOfGroup': return True, self.groups[args[0]][0] if self.groups[args[0]] else None
        if name == 'GroupRemoveUnit':
            if args[1] in self.groups[args[0]]: self.groups[args[0]].remove(args[1])
            return True, None
        if name == 'GroupClear': self.groups[args[0]].clear(); return True, None
        if name == 'ForGroup':
            previous = getattr(self, 'enum_unit', None)
            for unit in self.groups[args[0]][:]:
                self.enum_unit = unit; self.invoke(args[1])
            self.enum_unit = previous
            return True, None
        if name == 'CreateGroup':
            handled, handle = super().native(name, args)
            self.live_groups.add(handle)
            return handled, handle
        if name == 'DestroyGroup':
            require(args[0] in self.live_groups, 'Unknown/double-destroyed selector group')
            self.live_groups.remove(args[0])
            return True, None
        # These must execute current packed production helpers, never older Boss
        # harness gameplay substitutes. Native catalog/identity uses real JASS.
        if name in ('tdTowerChoiceForUnitTypeId', 'tdTowerLevelForUnitTypeId',
                    'tdTowerBranchForUnitTypeId', 'tdTowerIsEvolved',
                    'tdEnemyLaneId', 'tdEnemyWasLeaked', 'tdEnemyWave'):
            return False, None
        if name.startswith('dispatch_LinkedList_LinkedList_'):
            operation = name.removeprefix('dispatch_LinkedList_LinkedList_')
            if operation == 'add_1':
                self.lists[args[0]].append(args[-1]); return True, None
        return super().native(name, args)

    def execute_call(self, name, args):
        if name == 'tdHandleArcherSplitArrowAttack' and self.priority_ready:
            self.accepted.append(tuple(args[:2]) if args else (self.event_source,self.event_target))
        return super().execute_call(name, args)

    def recovery_tick(self):
        owner = allocations(self.script).get('alloc_CallbackPeriodic_doPeriodically_TDTowerTargetPriorityRuntime')
        require(owner is not None and owner[0] == 'CallbackPeriodic_typeId', 'Recovery periodic allocator missing')
        active = [cb for interval, cb in self.periodics
                  if interval == .1 and self.globals[owner[0]][cb] == owner[1] and
                  not self.timers[self.globals['CallbackPeriodic_t'][cb]]['destroyed']]
        require(len(active) <= 1, 'More than one active recovery timer')
        if not active:
            require(not self.globals['TDTowerTargetPriorityRuntime_tdTargetPriorityRecoveryRunning'],
                    'Recovery says running without an owned native callback')
            return
        callback = active[0]
        self.invoke('call_doPeriodically_TDTowerTargetPriorityRuntime', callback, callback)



def verify_packed_structure(script):
    packed = functions(script)
    require(not re.search(r'tdTargetPriority(?:EnemyEta|Emergency|Urgent|DistanceEta|PrepareGeometry|Geometry|Suffix|Waypoint)|tdEnemyHasActiveMovementControl', script), 'Retired route interception packed symbols remain')
    function_code = '\n'.join(function[4] for function in packed.values())
    require(function_code.count('GetAttacker()') == 1 and function_code.count('EVENT_PLAYER_UNIT_ATTACKED') == 1,
            'Packed artifact introduced another attacker/ATTACKED registration')
    for name in ('tdHandleTowerAttackStarted', 'tdTargetPriorityAcceptAttack',
                 'tdTargetPriorityTargetValid', 'tdTargetPriorityBest',
                 'tdTargetPriorityHandleOrder', 'tdTargetPriorityRecoveryTick'):
        require(name in packed, 'Missing actual packed priority function: ' + name)
    wrapper = packed['tdHandleTowerAttackStarted'][4]
    ordered(wrapper, ('GetAttacker()', 'GetTriggerUnit()', 'tdTowerChoiceForUnitTypeId(',
                     'tdArcherNativeAttackAllowed(', 'tdHandleArcherSplitArrowAttack(', 'return',
                     'tdTargetPriorityAcceptAttack(', 'return', 'tdHandleArcherSplitArrowAttack('),
            'Packed ARCHER native ATTACKED wrapper')
    require(wrapper.count('tdHandleArcherSplitArrowAttack(') == 2 and
            'tdQueueArcherSplitArrowVolley(' not in wrapper, 'Packed wrapper duplicate/missing family registration')
    renderer = packed['tdLaunchArcherSplitArrowVisual'][4]
    require(len(re.findall(r'^\s*if ', renderer, re.M)) == 3 and renderer.count('doPeriodically(0.03,') == 1,
            'Packed all-arrow renderer restored admission control')
    setup = packed['tdSetupDialogTrigger'][4]
    require('tdSetupTargetPriorityOrders(' in setup, 'Packed global priority order setup removed')
    for name, function in packed.items():
        if name.startswith('tdTargetPriority') or name.startswith('TDTowerTargetPriorityState_'):
            require(not re.search(r'GetRandom|GetLocalPlayer|UnitDamageTarget|DamageEvent_|doAfter\(', function[4]),
                    'Packed priority introduces randomness, damage or attack timers: ' + name)
    require('tdTargetPriorityAcceptAttack(' not in packed['tdHandleArcherSplitArrowDamage'][4],
            'Packed in-flight damage triggers target priority')
    return {'actual_packed_wrapper': True, 'priority_functions': sum(n.startswith('tdTargetPriority') for n in packed)}


def verify_transaction_replay(script):
    cases = []
    for synchronous, result in ((False, True), (True, True), (False, False), (True, False)):
        r = TowerTargetRuntime(script)
        r.order_result = result
        if synchronous:
            r.order_callback = lambda runtime, source, target: runtime.attack(target, source)
        r.attack()
        require(len(r.script_orders) == 1, 'Selection transaction issued more/less than one order')
        if synchronous:
            require(r.accepted == [(101, 103)], 'Synchronous redirect registered old/double split start')
        elif result:
            require(not r.accepted, 'Cancelled old start registered ghost split volley')
            require(r.field('pendingRevision') == r.field('intentRevision'), 'Async pending revision not published')
            scans = r.calls['tdTargetPriorityBest']
            r.units[102]['life'] = .01  # A new lower HP during confirmation cannot starve pending B.
            r.attack(103)
            require(r.accepted == [(101, 103)] and r.calls['tdTargetPriorityBest'] == scans,
                    'Async pending confirmation rescanned/redirected instead of making progress')
        else:
            require(r.accepted == [(101, 102)] and r.field('pendingRevision') == -1,
                    'Native false did not roll back to one legal original start')
        require(not r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']], 'Non-ARCHER priority transaction registered split volley')
        require(r.field('scriptOrderDepth') == 0 and not r.priority_rng and not r.live_groups,
                'Order provenance/group cleanup/RNG contract failed')
        cases.append({'sync_attacked': synchronous, 'native_order_result': result,
                      'script_orders': 1, 'accepted_starts': len(r.accepted)})
    r = TowerTargetRuntime(script)
    r.visible_units = [102, 103]
    r.units[102]['life'] = r.units[103]['life'] = 10.
    for _ in range(50):
        r.attack(102)
    require(not r.script_orders and r.accepted == [(101, 102)] * 50,
            'Repeated equal HP cancelled attacks or repeated orders')
    require(r.calls['tdTargetPriorityBest'] == 50, 'Normal ATTACKED selector count changed')
    cases.append({'same_hp_attacks': 50, 'script_orders': 0})
    r = TowerTargetRuntime(script)
    r.attack()
    r.units[103]['alive'] = False
    r.visible_units = []
    r.attack(103)
    require(not r.accepted and r.field('parked') and len(r.stop_orders) == 1,
            'Dead pending target accepted or recursively retried')
    cases.append({'pending_target_dead': True, 'accepted_starts': 0, 'stop_orders': 1})
    before = r.calls['tdTargetPriorityBest']
    r.visible_units = [102]; r.now = 10.49; r.recovery_tick()
    require(r.calls['tdTargetPriorityBest'] == before and len(r.script_orders) == 1,
            'Invalid pending confirmation bypassed recovery half-second floor')
    r.now = 10.50; r.recovery_tick()
    require(len(r.script_orders) == 2 and not r.accepted and r.calls['tdTargetPriorityBest'] == before + 1,
            'Invalid pending target failed one bounded sparse recovery transaction')
    r.attack(102)
    require(r.accepted == [(101,102)], 'Recovered pending attack failed to progress')
    # Engine callback picks another legal target: pending consumes once without HP re-scan.
    r = TowerTargetRuntime(script)
    r.attack(); scans = r.calls['tdTargetPriorityBest']; r.attack(104)
    require(r.accepted == [(101, 104)] and r.calls['tdTargetPriorityBest'] == scans,
            'Different legal confirmation target did not guarantee progress')
    cases.append({'different_legal_confirmation_target': True})
    return cases


def verify_manual_and_identity(script):
    cases = []
    for order in (851983, 851971):  # Native Orders.attack and Orders.smart.
        r = TowerTargetRuntime(script); r.command(order, 102); r.attack(102)
        require(r.field('manualTarget') == 102 and not r.script_orders and r.accepted == [(101, 102)],
                'Player attack/smart lock lost to lower-HP candidate')
        r.command(852102)  # Bloodlust autocast toggle.
        require(r.field('manualTarget') == 102, 'Autocast toggle cleared manual lock')
        r.command(851972)  # Stop.
        require(r.field('manualTarget') is None and r.field('playerHold'), 'Stop failed to clear manual lock')
        cases.append({'manual_order': order, 'lock_and_stop': True})
    for order in (851972, 851993, 852600):
        r = TowerTargetRuntime(script); r.command(order); r.attack(102)
        require(not r.script_orders and not r.stop_orders, 'Stop/hold/spell overwritten by auto command')
        cases.append({'nonattack_order': order, 'automatic_orders': 0})
    for invalid in ('lane', 'epoch', 'hidden', 'visible', 'dead', 'leaked', 'range', 'mechanical', 'structure'):
        r = TowerTargetRuntime(script); range_ = r.invoke('tdTowerEffectiveRangeForTower', 101)
        if invalid == 'lane': r.units[103]['userdata'] = 10100
        elif invalid == 'epoch': r.tables[r.globals['TDSpawn_tdEnemyMatchEpochs']][103] -= 1
        elif invalid == 'hidden': r.units[103]['hidden'] = True
        elif invalid == 'visible': r.units[103]['visible'] = False
        elif invalid == 'dead': r.units[103]['alive'] = False
        elif invalid == 'leaked': r.units[103]['userdata'] = 199
        elif invalid == 'range': r.units[103]['x'] = range_ + .406
        else: r.units[103]['kinds'] = {invalid}
        r.visible_units = [102, 103]; r.attack(102)
        require(not r.script_orders and r.accepted == [(101, 102)], 'Invalid better candidate selected: ' + invalid)
        cases.append({'rejected_candidate': invalid})
    r = TowerTargetRuntime(script); range_ = r.invoke('tdTowerEffectiveRangeForTower', 101)
    r.units[103]['x'] = range_ + .405; r.attack()
    require(r.script_orders[-1][2] == 103, '0.405 valid range boundary rejected')
    for exclusion in ('working', 'casting', 'pet_busy'):
        r = TowerTargetRuntime(script); record = r.invoke('tdTargetPriorityGet', 101)
        if exclusion == 'working': r.invoke('tdTargetPriorityWorkStarted', 101)
        elif exclusion == 'casting': r.invoke('tdTargetPriorityCasting', 101, True)
        else: r.tables[r.globals['TDPetState_tdPetBusyTowers']][101] = True
        r.attack(102)
        require(not r.accepted and not r.script_orders and not r.stop_orders,
                'Explicit working/casting/pet-busy source registered an attack side effect')
        cases.append({'explicit_exclusion': exclusion, 'accepted_starts': 0})
    for change in ('work', 'intent', 'command', 'forget_recreate'):
        r = TowerTargetRuntime(script)
        def callback(runtime, source, target):
            if change == 'work': runtime.invoke('tdTargetPriorityWorkStarted', source)
            elif change == 'intent': runtime.invoke('TDTowerTargetPriorityState_newIntent', runtime.record(source))
            elif change == 'command': runtime.command(851972, source=source)
            else:
                runtime.invoke('tdTargetPriorityForget', source)
                runtime.invoke('tdTargetPriorityCreate', source, 0, runtime.invoke('tdFlowEpoch'))
        r.order_callback = callback; r.attack()
        require(not r.accepted and r.field('scriptOrderDepth') == 0,
                'Native callback changed record/intent but outer start was registered or depth leaked')
        cases.append({'synchronous_change': change, 'ghost_old_starts': 0})
    r = TowerTargetRuntime(script); r.attack(); serial = r.field('serial')
    r.units[101]['owner'] = 1; r.event_target = 101; r.invoke('tdTargetPriorityHandleOwnerChanged')
    require(r.record() == 0, 'Owner transfer retained old intent')
    r.units[101]['owner'] = 0; r.attack(); require(r.field('serial') > serial, 'Record/source ID reuse kept serial')
    r.invoke('tdTargetPriorityClearAll'); require(r.record() == 0, 'Reset retained tower intent')
    cases.append({'owner_reset_serial_reuse': True})
    return cases


def verify_recovery(script):
    r = TowerTargetRuntime(script)
    r.visible_units = []
    sources = list(range(1000, 1040))
    for source in sources:
        r.tower(source); r.attack(None, source)
    require(len(r.stop_orders) == 40, 'Empty candidates did not park each source once')
    require(len(r.lists[r.globals['TDTowerTargetPriorityState_tdTargetPriorityParked']]) == 40,
            'Sparse recovery queue cardinality incorrect')
    r.clear_trace(); queries = {source: [] for source in sources}
    for tick in range(1, 31):
        r.now = 10. + tick * .1
        before = r.calls['tdTargetPriorityBest']
        r.recovery_tick()
        count = r.calls['tdTargetPriorityBest'] - before
        require(count <= 4, 'Recovery exceeded four-query tick budget')
        for source in sources:
            at = r.globals['TDTowerTargetPriorityState_lastRecoveryQuery'][r.record(source)]
            if at > 10. and (not queries[source] or at != queries[source][-1]):
                queries[source].append(at)
    require(all(len(at) >= 2 for at in queries.values()), '40 parked sources starved in round-robin recovery')
    require(all(b - a >= .49999 for at in queries.values() for a, b in zip(at, at[1:])),
            'A parked source was rescanned before half-second floor')
    require(not r.script_orders and not r.stop_orders, 'Empty recovery emitted repeated attack/Stop')
    # A fresh order removes one parked source and projects CURRENT actual range.
    r.command(851993, source=sources[0])
    require(not r.field('parked', sources[0]) and r.units[sources[0]]['acquireRange'] ==
            r.invoke('tdTowerEffectiveRangeForTower', sources[0]), 'Manual hold failed to unpark/current-range restore')
    r.visible_units = [102]
    for tick in range(31, 46):
        r.now = 10. + tick * .1; r.recovery_tick()
    require(not r.lists[r.globals['TDTowerTargetPriorityState_tdTargetPriorityParked']],
            'Legal candidates failed to drain sparse recovery')
    require(len(r.script_orders) == 39 and not r.live_groups, 'Recovery duplicated orders or leaked groups')
    r.invoke('tdTargetPriorityClearAll')
    require(not r.lists[r.globals['TDTowerTargetPriorityState_tdTargetPriorityRecords']], 'ClearAll retained records')
    return {'parked_sources': 40, 'ticks_observed': 45, 'max_queries_per_tick': 4,
            'min_query_interval_seconds': .5, 'fair_no_starvation': True,
            'empty_candidate_repeated_stop_orders': 0, 'recovery_attack_orders': 39}


def verify_catalog_selection(script):
    r = TowerTargetRuntime(script)
    r.enemy(102, life=100., type_='uW01')
    r.enemy(103, life=20., type_='uG08')
    r.enemy(104, life=80., type_='uB08')
    r.units[102]['maxLife'] = 10000.  # lowest percentage, highest absolute HP.
    r.visible_units = [102, 103, 104]
    rows = []
    for index, type_ in enumerate(TOWERS):
        source = r.tower(2000 + index, type_)
        scripted = r.invoke('tdTargetPriorityUsesScriptedPriority', FAMILIES[type_[1]])
        require(scripted == (type_[1] != 'A'), 'Wrong native/scripted family for ' + type_)
        if not scripted:
            rows.append({'rawcode': type_, 'family': 1, 'native_archer': True})
            continue
        record = r.invoke('tdTargetPriorityGet', source)
        range_ = r.invoke('tdTowerEffectiveRangeForTower', source)
        best = r.invoke('tdTargetPriorityBest', record, 102, range_)
        expected = 103 if type_[1] in ('A', 'D') else 104
        require(best == expected, 'Wrong live HP/rank selection for tower rawcode ' + type_)
        # Same-rank melee never switches by HP; current ranged equal HP stays.
        r.visible_units = [102, 103]
        before_type = r.units[103]['type']; r.units[103]['type'] = rawcode('uW01')
        before_hp = r.units[103]['life']; r.units[103]['life'] = 100.
        require(r.invoke('tdTargetPriorityBest', record, 102, range_) == 102,
                'Equal HP/rank did not retain current for ' + type_)
        r.units[103]['type'], r.units[103]['life'] = before_type, before_hp
        r.visible_units = [102, 103, 104]
        rows.append({'rawcode': type_, 'family': FAMILIES[type_[1]], 'best_target': best})
    require(not r.priority_rng and not r.live_groups, 'Catalog selection used RNG or leaked groups')
    return {'35_rawcodes_routing_and_28_actual_selectors': rows, 'hp_percent_adversary': True,
            'same_rank_no_hp_tiebreak': True, 'evolution_policy': 'Evolution retains these native rawcodes; family policy is independent of evolution state.'}


def verify_trial_identity(script):
    r = TowerTargetRuntime(script); r.units[101]['y'] = 0.; r.enter(8)
    target = r.target(0); other = r.target(5)
    r.units[target].update(x=0., y=0., life=20.)
    r.units[other].update(x=0., y=0., life=1.)
    range_ = r.invoke('tdTowerEffectiveRangeForTower', 101)
    require(r.invoke('tdTargetPriorityTargetValid', 101, target, 0, range_), 'Valid trial target incorrectly required normal epoch registration')
    require(not r.invoke('tdTargetPriorityTargetValid', 101, other, 0, range_), 'Cross-lane trial target selected')
    r.command(851983, target)
    record = r.record()
    require(r.invoke('tdTargetPriorityManualValid', record, range_), 'Fresh manual trial identity rejected')
    old_revision = r.field('manualRevision')
    r.units[target]['alive'] = False; r.event_target = target; r.invoke('tdTrialOnTargetDeath')
    replacement = r.adversarial_rebind(0, True)
    require(replacement == target, 'Adversarial native handle reuse did not actually reuse target')
    r.units[replacement].update(x=0., y=0.)
    require(r.globals['TDTrialBinding_revision'][r.binding(0)] != old_revision,
            'Adversarial rebind did not advance trial revision')
    require(r.invoke('tdTargetPriorityTargetValid', 101, replacement, 0, range_), 'New current trial binding is not valid')
    require(not r.invoke('tdTargetPriorityManualValid', record, range_), 'Old manual snapshot admitted reused trial revision')
    # Restamp manual to current, then mutate captured token/generation/epoch only.
    for field in ('manualToken', 'manualGeneration', 'manualEpoch'):
        r.command(851983, replacement); record = r.record()
        r.globals['TDTowerTargetPriorityState_' + field][record] -= 1
        require(not r.invoke('tdTargetPriorityManualValid', record, range_), 'Stale trial ' + field + ' admitted')
    return {'same_lane_trial_without_normal_epoch': True, 'cross_lane_rejected': True,
            'reused_native_handle_revision_rejected': True, 'old_token_generation_epoch_rejected': True,
            'registry_reuse_fixture': 'Adversarial rebind after actual production trial death; no replenishment claim.'}


def register_actual_split_listener(runtime):
    setup = functions(runtime.script)['tdSetupDialogTrigger'][4]
    pairs = re.findall(r'set (\w+) = (alloc_DamageListener_addListener_TDTowerRuntime(?:_\d+)?)\([^\n]*\)'
                       r'(?:(?!set \1 =).)*?call (DamageEvent_addListener(?:_\d+)?)\(0, \1\)', setup, re.S)
    require(len(pairs) == 1, 'No unique actual packed split listener priority0 binding')
    _, allocator, registration = pairs[0]
    require(len(runtime.functions[registration][0]) == 2, 'Actual damage registration signature changed')
    listener = runtime.invoke(allocator)
    runtime.invoke('construct_DamageListener', listener)
    runtime.invoke(registration, 0, listener)


def verify_split_immutable_basis(script):
    r = TowerTargetRuntime(script)
    r.units[101]['type'] = rawcode('uA6A')
    r.enemy(106, life=10000.)
    pet = r.pet([(17, 4)]); r.globals['TDPet_resolveRotation'][pet] = 4
    shots = r.invoke('new_LinkedList')
    shot = r.invoke('new_TDArcherSplitArrowShot', 106, 0.)
    r.lists[shots].append(shot)
    volley = r.invoke('new_TDArcherSplitArrowVolley', 101, 102, 0., shots)
    r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']].append(volley)
    register_actual_split_listener(r)
    r.units[102].update(life=10000., maxLife=10000.)
    r.emit(100.)
    near(next(event['amount'] for _, target, event in r.emitted if target == 102 and event['id'] == 0),
         210., 'Packed split original-host resolve primary')
    require(len(r.native_damage) == 1, 'Packed split callback duplicated/lost its segment')
    near(r.native_damage[0][2], 100., 'Packed split uses immutable original100, not modified210')
    require(any(event['id'] == rawcode('Tspl') for _, _, event in r.emitted), 'Packed split lost recursion tag')
    require(r.globals['TDPet_resolveRotation'][pet] == 0, 'Derived split recursively advanced pet counter')
    r.invoke('tdExpireArcherSplitArrowVolley', volley)
    require(r.globals['TDArcherSplitArrowShot_typeId'][shot] == 0 and
            r.globals['TDArcherSplitArrowVolley_typeId'][volley] == 0 and shots not in r.lists,
            'Split expiry failed to destroy captured shot/volley/list')
    return {'primary_final': 210., 'split_immutable_original_basis': 100.,
            'tag': 'Tspl', 'derived_recursive_pet_advances': 0,
            'fixture_boundary': 'Native post-armor input, constructed shot/volley and production allocator/listener registration/dispatch. No rendering or native armor emulation.'}


def verify_split_inflight(script):
    r = TowerTargetRuntime(script, 'uA6B')
    register_actual_split_listener(r)
    for handle in (102, 103, 104):
        r.units[handle].update(life=10000., maxLife=10000.)
    callbacks, volleys = [], []
    for target in (102, 103, 102):
        r.command(851983, target)
        before = len(r.scheduled); r.attack(target)
        require(len(r.scheduled) == before + 1, 'Accepted split attack did not own one expiry timer')
        callbacks.append(r.scheduled[-1][1])
        volleys.append(r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']][-1])
    require(len(set(volleys)) == 3, 'A/B/A in-flight volley allocation identity reused early')
    selections = r.calls['tdTargetPriorityBest']
    queue = r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']]
    r.emit(40., target=102)
    require(queue == volleys[1:], 'Old A hit consumed wrong/new A or moved B volley')
    r.run_timer(callbacks[0])
    require(queue == volleys[1:] and r.globals['TDArcherSplitArrowVolley_typeId'][volleys[2]] != 0,
            'Old A expiry destroyed newer A identity')
    r.emit(40., target=103)
    require(queue == [volleys[2]], 'B hit consumed unrelated A volley')
    r.run_timer(callbacks[1]); r.emit(40., target=102); r.run_timer(callbacks[2])
    require(not queue and len(r.native_damage) == 6, 'A/B/A impacts duplicated/lost split hits')
    require(r.calls['tdTargetPriorityBest'] == selections and len(r.script_orders) == 0,
            'Original/derived in-flight damage triggered selection or attack orders')
    require(all(r.globals['TDArcherSplitArrowVolley_typeId'][volley] == 0 for volley in volleys),
            'Actual expiry callbacks leaked consumed volleys')
    return {'actual_native_primary_sequence': ['A', 'B', 'A'], 'original_hits': 3,
            'split_segments': 6, 'old_expiry_new_volley_preserved': True,
            'damage_side_target_queries': 0, 'automatic_orders': 0,
            'render_boundary': 'Every production launch is recorded immediately; full-arrow artifact gate separately executes renderer and dummy recycling.'}


def archer_runtime(script, type_='uA6B'):
    r = TowerTargetRuntime(script, type_)
    register_actual_split_listener(r)
    for handle in (102, 103, 104, *range(110, 126)):
        r.enemy(handle, life=1000000.)
    return r


def split_queue(r):
    return r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']]


def volley_targets(r, volley):
    shots = r.globals['TDArcherSplitArrowVolley_extraShots'][volley]
    return [r.globals['TDArcherSplitArrowShot_target'][shot] for shot in r.lists[shots]]


def assert_archer_uncontrolled(r, label):
    require(not r.script_orders and not r.stop_orders and
            r.calls['tdTargetPriorityBest'] == 0 and r.calls['tdTargetPriorityRedirect'] == 0 and
            r.calls['tdTargetPriorityAcceptAttack'] == 0,
            'ARCHER native attack was selected/redirected/stopped: ' + label)
    require(all(value != 0. for _, value in r.acquisition),
            'ARCHER native acquisition was projected to zero: ' + label)


def start_archer_volley(r, target=102, source=101):
    before = list(split_queue(r)); visual_before = len(r.split_visual_launches)
    scheduled_before = len(r.scheduled)
    absent_record = r.record(source) == 0
    r.attack(target, source)
    require(not absent_record or r.record(source) == 0, 'ARCHER legal native start created priority state')
    require(len(split_queue(r)) == len(before) + 1 and split_queue(r)[:-1] == before,
            'ARCHER native ATTACKED lost/duplicated one volley')
    volley = split_queue(r)[-1]
    targets = volley_targets(r, volley)
    launches = r.split_visual_launches[visual_before:]
    require(targets and [(launch[0], launch[1]) for launch in launches] == [(source, t) for t in targets],
            'ARCHER ATTACKED did not immediately launch every selected visible arrow')
    require(len(r.scheduled) == scheduled_before + 1,
            'ARCHER volley must own one expiry, no delayed launch timers')
    assert_archer_uncontrolled(r, 'start')
    return volley, targets, r.scheduled[-1][1]


def hit_archer_volley(r, volley, targets, amount, source=101, target=102):
    before = len(r.native_damage)
    r.emit(amount, source=source, target=target)
    hits = r.native_damage[before:]
    require([hit[1] for hit in hits] == targets and all(hit[0] == source for hit in hits),
            'ARCHER real primary consumed another volley target snapshot')
    multiplier = r.invoke('tdArcherSplitArrowDamageMultiplier',
                          r.invoke('tdTowerLevelForUnitTypeId', r.units[source]['type']),
                          r.invoke('tdTowerBranchForUnitTypeId', r.units[source]['type']),
                          r.invoke('tdTowerIsEvolved', source))
    for hit in hits:
        near(hit[2], amount * multiplier, 'ARCHER per-hit immutable split damage')
    require(volley not in split_queue(r), 'ARCHER primary failed to dequeue its volley')
    require(r.globals['TDArcherSplitArrowVolley_typeId'][volley] != 0,
            'ARCHER consume destroyed volley before its unique expiry')
    assert_archer_uncontrolled(r, 'impact')


def verify_archer_native_restoration(script):
    rows = []
    for type_ in ARCHERS:
        for changing, count in ((False, 6), (True, 30)):
            r = archer_runtime(script, type_)
            level = r.invoke('tdTowerLevelForUnitTypeId', rawcode(type_))
            for index in range(count):
                target = (102, 103, 102)[index % 3] if changing else 102
                extras = list(range(110 + (index % 3 if changing else 0), 120 + (index % 3 if changing else 0)))
                r.visible_units = [target, *extras]
                # Adversarial HP changes used to redirect or alternate swallowed starts.
                r.units[target]['life'] = 1000000. + index
                for victim in extras:
                    r.units[victim]['life'] = 1000000. - index * 13.
                volley, targets, expiry = start_archer_volley(r, target)
                require(len(targets) == level, 'ARCHER catalog split count lost: ' + type_)
                hit_archer_volley(r, volley, targets, (11., 23., 37.)[index % 3], target=target)
                r.run_timer(expiry)
                require(not split_queue(r) and sum(value != 0 for value in r.globals['TDArcherSplitArrowVolley_typeId'].values()) == 0,
                        'ARCHER repeated attack expiry leaked live/pending volley')
                r.now += .05
            require(len(r.accepted) == count and not r.live_groups,
                    'ARCHER repeated actual starts dropped/duplicated or leaked groups')
            rows.append({'rawcode': type_, 'changing_hp_and_primary': changing,
                         'native_starts': count, 'per_start_immediate_visible_arrows': level,
                         'per_hit_damage_and_target_snapshot_checked': True,
                         'best_redirect_stop_orders': 0})
    return {'seven_catalog_types': list(ARCHERS), 'cases': rows,
            'native_starts_executed': sum(row['native_starts'] for row in rows),
            'historical_ttl': 'Unchanged .35 + maximum captured flight; deliveries remain inside this historical window. No native attack-point claim.'}


def verify_archer_native_orders_and_recovery(script):
    rows = []
    for type_ in ARCHERS:
        for order in (851983, 851971, 851972, 851993, 852600):
            r = archer_runtime(script, type_); r.visible_units = [102, 103, 104]
            r.command(order, 102 if order in (851983, 851971) else None)
            require(r.record() == 0 and not r.acquisition,
                    'ARCHER native command created priority/manual state or changed acquisition')
            volley, targets, expiry = start_archer_volley(r)
            hit_archer_volley(r, volley, targets, 23.)
            r.run_timer(expiry)
        r = archer_runtime(script, type_); r.visible_units = []
        r.attack(None)
        require(not split_queue(r), 'ARCHER empty native callback queued ghost volley')
        assert_archer_uncontrolled(r, 'empty field')
        r.visible_units = [102, 103]
        volley, targets, expiry = start_archer_volley(r)
        # Cancellation has no real main hit and therefore no invented split damage.
        r.command(851972); r.run_timer(expiry)
        require(not r.native_damage and not split_queue(r), 'ARCHER cancelled attempt invented split damage')
        r.units[102]['alive'] = False; r.attack(102)
        require(not split_queue(r), 'ARCHER dead primary registered volley')
        r.units[102]['alive'] = True
        volley, targets, expiry = start_archer_volley(r, 103)
        hit_archer_volley(r, volley, targets, 37., target=103); r.run_timer(expiry)
        # Stale state injection models a record surviving an earlier implementation.
        record = r.invoke('tdTargetPriorityGet', 101)
        r.invoke('TDTowerTargetPriorityState_beginRedirect', record, 102)
        r.globals['TDTowerTargetPriorityState_parked'][record] = True
        parked = r.lists[r.globals['TDTowerTargetPriorityState_tdTargetPriorityParked']]
        parked.append(record); r.units[101]['acquireRange'] = 0.
        r.invoke('tdTargetPriorityStartRecovery'); r.clear_trace(); r.recovery_tick()
        require(record not in parked and not r.field('parked') and r.field('pendingRevision') == -1,
                'ARCHER stale recovery retained parked/pending state')
        near(r.units[101]['acquireRange'], r.invoke('tdTowerEffectiveRangeForTower', 101),
             'ARCHER stale recovery did not restore effective range')
        assert_archer_uncontrolled(r, 'stale recovery')
        volley, targets, expiry = start_archer_volley(r)
        hit_archer_volley(r, volley, targets, 11.); r.run_timer(expiry)
        # Defensive direct entry points must also be harmless for archers.
        previous = (len(r.script_orders), len(r.stop_orders), r.calls['tdTargetPriorityBest'], len(r.acquisition))
        r.invoke('tdTargetPriorityRedirect', record, 103); r.invoke('tdTargetPriorityPark', record)
        require(previous == (len(r.script_orders), len(r.stop_orders), r.calls['tdTargetPriorityBest'], len(r.acquisition)),
                'ARCHER direct guarded entry changed orders/range or queried Best')
        rows.append({'rawcode': type_, 'native_manual_orders': 5, 'empty_reacquisition': True,
                     'cancel_without_primary_damage': True, 'stale_parked_recovery': True})
    # A mixed queue retains the ordinary Dryad recovery next to an Archer escape.
    r = archer_runtime(script); record = r.invoke('tdTargetPriorityGet', 101)
    r.globals['TDTowerTargetPriorityState_parked'][record] = True
    parked = r.lists[r.globals['TDTowerTargetPriorityState_tdTargetPriorityParked']]; parked.append(record)
    r.units[101]['acquireRange'] = 0.; r.tower(202, 'uD6B'); r.visible_units = []
    r.attack(None, 202); r.clear_trace(); r.visible_units = [102]; r.now = 10.5; r.recovery_tick()
    require(record not in parked and all(order[0] != 101 for order in r.script_orders) and
            any(order[0] == 202 for order in r.script_orders), 'Mixed recovery changed non-ARCHER priority')
    return {'cases': rows, 'mixed_archer_dryad_recovery': True}


def verify_archer_inflight_reuse_and_filters(script):
    r = archer_runtime(script)
    shots = []
    for index, target in enumerate((102, 103, 102)):
        r.visible_units = [target, 110 + index, 114 + index]
        shots.append((target, *start_archer_volley(r, target)))
    first, second, third = shots
    hit_archer_volley(r, first[1], first[2], 11., target=first[0])
    # Allocate after consume, before the old timer: early destroy would reuse its ID.
    r.visible_units = [104, 120, 121]
    newer = start_archer_volley(r, 104)
    require(newer[0] not in [item[1] for item in shots], 'ARCHER consumed volley identity reused before old expiry')
    r.run_timer(first[3])
    require(split_queue(r) == [second[1], third[1], newer[0]] and
            r.globals['TDArcherSplitArrowVolley_typeId'][newer[0]] != 0,
            'ARCHER old expiry destroyed a newer in-flight volley')
    for item, amount in ((second, 23.), (third, 37.)):
        hit_archer_volley(r, item[1], item[2], amount, target=item[0]); r.run_timer(item[3])
    hit_archer_volley(r, newer[0], newer[1], 41., target=104); r.run_timer(newer[2])
    require(sum(value != 0 for value in r.globals['TDArcherSplitArrowVolley_typeId'].values()) == 0 and not split_queue(r),
            'ARCHER all expiries failed to return live/pending to baseline')
    # Two archers share a primary but must consume only their own queued snapshots.
    r = archer_runtime(script); r.tower(202, 'uA6A')
    r.units[202]['abilities'] = dict(r.units[101]['abilities']); r.visible_units = [102, 110, 111]
    one = start_archer_volley(r); two = start_archer_volley(r, source=202)
    hit_archer_volley(r, two[0], two[1], 23., source=202)
    hit_archer_volley(r, one[0], one[1], 11.)
    r.run_timer(one[2]); r.run_timer(two[2])
    # Code/spell/tagged native inputs cannot consume an otherwise pending volley.
    for kind in ('code', 'spell', 'Tspl'):
        r = archer_runtime(script); r.visible_units = [102, 110]
        volley, targets, expiry = start_archer_volley(r)
        if kind == 'code': r.invoke('DamageEvent_setNextDamageFromCode')
        elif kind == 'Tspl': r.invoke('DamageEvent_setNextDamageId', rawcode('Tspl'))
        r.emit(-11. if kind == 'spell' else 11.)
        require(split_queue(r) == [volley] and not r.native_damage,
                'ARCHER recursive code/spell/Tspl consumed a new volley')
        hit_archer_volley(r, volley, targets, 37.); r.run_timer(expiry)
    return {'different_primary_sequence': ['A', 'B', 'A'], 'different_native_damage': [11, 23, 37, 41],
            'consume_then_allocate_before_old_expiry': True, 'two_sources_same_primary': True,
            'code_spell_Tspl_not_consumed': True, 'live_pending_after_expiry': 0}


def verify_archer_safety_and_equipment(script):
    rows = []
    for exclusion in ('working', 'casting', 'pet_busy', 'sale_busy', 'selling', 'owner', 'epoch', 'removed', 'dead'):
        r = archer_runtime(script); r.visible_units = [102, 103]
        if exclusion in ('working', 'casting', 'owner', 'epoch'):
            record = r.invoke('tdTargetPriorityGet', 101)
            if exclusion in ('working', 'casting'):
                r.globals['TDTowerTargetPriorityState_' + exclusion][record] = True
            elif exclusion == 'owner': r.units[101]['owner'] = 1
            else: r.globals['TDTowerTargetPriorityState_epoch'][record] -= 1
        elif exclusion == 'pet_busy': r.tables[r.globals['TDPetState_tdPetBusyTowers']][101] = True
        elif exclusion in ('sale_busy', 'selling'):
            state = r.invoke('tdGetTowerSaleState', 101)
            r.invoke('TDTowerSaleState_startWork' if exclusion == 'sale_busy' else 'TDTowerSaleState_beginSale', state)
        elif exclusion == 'removed': r.units[101]['type'] = 0
        else: r.units[101]['alive'] = False
        r.attack()
        require(not split_queue(r) and not r.split_visual_launches,
                'ARCHER unsafe source registered ghost arrows: ' + exclusion)
        if exclusion != 'removed':
            assert_archer_uncontrolled(r, exclusion)
        else:
            require(not r.script_orders and not r.stop_orders and r.calls['tdTargetPriorityBest'] == 0,
                    'Removed source changed priority control')
        rows.append(exclusion)
    r = archer_runtime(script); r.visible_units = [102, *range(110, 126)]
    base = start_archer_volley(r); base_count = len(base[1]); r.run_timer(base[2])
    candidates = [r.invoke('tdConfiguredEquipment', i) for i in range(1, 41)]
    arrow_items = [item for item in candidates if r.invoke('tdItemSpecialization', item) == r.globals['TDItemCatalogSchema_TD_ITEM_SPECIAL_ARCHER_ARROW']]
    require(arrow_items, 'ARCHER equipment additional-arrow fixture has no catalog item')
    r.units[101]['inventory'] = {0: 4242}; r.inventory_items[4242] = arrow_items[-1]
    equipped = start_archer_volley(r)
    expected = base_count + r.invoke('tdEquipmentArcherAdditionalArrows', 101)
    require(len(equipped[1]) == expected > base_count, 'ARCHER equipment extra arrows disappeared')
    hit_archer_volley(r, equipped[0], equipped[1], 23.); r.run_timer(equipped[2])
    # All existing equipment update work executes, including the family range branch.
    record = r.invoke('tdTargetPriorityGet', 101); r.globals['TDTowerTargetPriorityState_parked'][record] = True
    r.units[101]['acquireRange'] = 0.; r.clear_trace()
    refresh = next(name for name, definition in r.functions.items()
                   if name.startswith('tdRefreshTowerEquipmentBonuses') and len(definition[0]) >= 2 and definition[0][1] == 'excludedItem')
    r.invoke(refresh, 101, None)
    near(r.units[101]['acquireRange'], r.invoke('tdTowerEffectiveRangeForTower', 101),
         'ARCHER inventory refresh projected parked range to zero')
    assert_archer_uncontrolled(r, 'inventory refresh')
    return {'unsafe_source_exclusions': rows, 'equipment_arrow_counts': [base_count, expected],
            'actual_inventory_refresh_native_range': True}


def verify_archer_deferred_context(script):
    cases = []
    for invalid in ('dead', 'removed', 'leaked', 'trial_generation', 'match_reset'):
        r = archer_runtime(script); r.units[110]['x'] = 220.; r.visible_units = [102, 110]
        volley, targets, expiry = start_archer_volley(r)
        r.emit(11.)
        require(not r.native_damage and volley not in split_queue(r),
                'ARCHER farther extra shot did not defer real damage')
        delayed = [(delay, cb) for delay, cb in r.scheduled if cb != expiry]
        require(len(delayed) == 1 and delayed[0][0] > .03,
                'ARCHER deferred impact did not capture its own callback')
        if invalid == 'dead': r.units[110]['alive'] = False
        elif invalid == 'removed': r.call('RemoveUnit', [110])
        elif invalid == 'leaked':
            r.invoke('tdHandleEnemyLeak', 110)
            require(not r.units[110]['alive'], 'ARCHER leak fixture did not actually kill the leaked target')
        elif invalid == 'trial_generation': r.state_call('reset')
        else: r.invoke('tdStartGame')
        r.run_timer(delayed[0][1]); r.run_timer(expiry)
        require(not r.native_damage and not split_queue(r),
                'ARCHER deferred callback damaged a dead/removed/new-context target: ' + invalid)
        cases.append(invalid)
    # Real trial targets: in-flight snapshot cannot hit an adversarial reused handle.
    r = archer_runtime(script); r.units[101].update(x=0., y=0.); r.enter(8)
    primary, victim = r.target(0), r.target(1)
    r.units[primary].update(x=0., y=0., life=1000000.)
    r.units[victim].update(x=220., y=0., life=1000000.)
    r.visible_units = [primary, victim]
    previous_callbacks = {cb for _, cb in r.scheduled}
    volley, targets, expiry = start_archer_volley(r, primary)
    r.emit(23., target=primary)
    delayed = [(delay, cb) for delay, cb in r.scheduled if cb != expiry and cb not in previous_callbacks and delay > .03]
    require(len(delayed) == 1 and not r.native_damage, 'ARCHER trial deferred callback fixture failed')
    r.units[victim]['alive'] = False; r.event_target = victim; r.invoke('tdTrialOnTargetDeath')
    replacement = r.adversarial_rebind(1, True)
    require(replacement == victim, 'ARCHER trial registry adversary failed actual handle reuse')
    r.run_timer(delayed[0][1]); r.run_timer(expiry)
    require(not r.native_damage and r.units[replacement]['life'] == 1000000.,
            'ARCHER old trial split damaged a rebound revision')
    # A lethal native primary still confirms its already-visible secondary arrows.
    r = archer_runtime(script); r.units[102]['life'] = 1.; r.visible_units = [102, 110, 111]
    volley, targets, expiry = start_archer_volley(r)
    hit_archer_volley(r, volley, targets, 37.); r.run_timer(expiry)
    require(not r.units[102]['alive'], 'ARCHER lethal-primary fixture was not lethal')
    # Lifetime adversary: release the consumed volley before its copied impact.
    # Native chronological deadlines are tested separately; this deliberately
    # reverses callback delivery to exercise capture ownership only.
    r = archer_runtime(script); r.units[110]['x'] = 220.; r.visible_units = [102, 110]
    volley, targets, expiry = start_archer_volley(r); r.emit(23.)
    impact = next(cb for delay, cb in r.scheduled if cb != expiry and delay > .03)
    r.run_timer(expiry)
    r.visible_units = [103, 111]; newer = start_archer_volley(r, 103)
    r.run_timer(impact)
    require(r.native_damage and r.native_damage[-1][1] == 110, 'ARCHER deferred capture retargeted after volley reuse')
    near(r.native_damage[-1][2], 23., 'ARCHER deferred capture changed amount after volley reuse')
    r.run_timer(newer[2])
    return {'deferred_invalidations': cases, 'trial_reused_handle_revision_rejected': True,
            'trial_registry_adversary': 'Synthetic rebind only after actual production trial death; no ACTIVE replenishment claim.',
            'lethal_native_primary_confirms_split': True, 'copied_deferred_values_survive_volley_expiry': True}


def verify_recovery_failures_and_range(script):
    r = TowerTargetRuntime(script); r.visible_units = []; r.attack(None)
    require(len(r.stop_orders) == 1 and r.field('parked'), 'Initial no-candidate parking failed')
    r.visible_units = [102]; r.order_result = False
    r.clear_trace()
    attempts = []
    for tick in range(1, 16):
        r.now = 10. + tick * .1; before = len(r.script_orders); r.recovery_tick()
        if len(r.script_orders) != before: attempts.append(r.now)
    require(len(attempts) == 3 and all(b-a >= .49999 for a,b in zip(attempts, attempts[1:])),
            'Native-false recovery retried without half-second budget')
    require(not r.stop_orders and r.field('parked'), 'Native-false recovery emitted extra Stop or lost parking')
    r.command(851993); r.recovery_tick()
    require(not r.globals['TDTowerTargetPriorityRuntime_tdTargetPriorityRecoveryRunning'],
            'Empty sparse queue failed to destroy real recovery callback')
    # Equipment query remains actual packed inventory/catalog math.
    r = TowerTargetRuntime(script)
    candidates = [r.invoke('tdConfiguredEquipment', i) for i in range(1, 41)]
    range_items = [item for item in candidates if r.invoke('tdEquipmentRangeBonusForItems', item, 0, 0) > 0]
    require(range_items, 'No actual catalog range item discovered')
    old_range = r.invoke('tdTowerEffectiveRangeForTower', 101)
    r.visible_units = []; r.attack(None)
    r.units[101]['inventory'] = {0: 4242}; r.inventory_items[4242] = range_items[-1]
    new_range = r.invoke('tdTowerEffectiveRangeForTower', 101)
    require(new_range > old_range, 'Equipped actual range item did not increase effective range')
    require(r.invoke('tdTargetPriorityProjectedAcquireRange', 101, new_range) == 0.,
            'Equipment refresh resumed parked native acquisition')
    r.units[102]['x'] = (old_range + new_range) * .5; r.visible_units = [102]
    r.now = 10.5; r.recovery_tick()
    require(r.script_orders and r.script_orders[-1][2] == 102 and r.units[101]['acquireRange'] == new_range,
            'Recovery used stale pre-equipment range')
    for order in (851983, 851971, 851972, 851993, 852600):
        r = TowerTargetRuntime(script); r.visible_units = []; r.attack(None)
        r.clear_trace(); r.command(order, 102 if order in (851983,851971) else None)
        r.visible_units = [103]; r.now = 10.5; r.recovery_tick()
        require(not r.script_orders and not r.stop_orders and not r.field('parked'),
                'Park recovery overwrote newer attack/smart/stop/hold/spell intent')
    return {'recovery_false_attempt_seconds': attempts, 'extra_stop_orders': 0,
            'real_periodic_empty_queue_destroyed': True, 'equipment_range_sequence': [old_range,new_range],
            'new_player_commands_cancel_recovery': 5}


PACKED_MUTATION_ASSERTIONS = {'missing verdict': 'Packed ARCHER native ATTACKED wrapper: missing/out-of-order tdTargetPriorityAcceptAttack(', 'HP tie change': 'Actual comparator violates strict/current/tie rule', 'rank tie change': 'Actual comparator violates strict/current/tie rule', 'range inflation': 'Invalid better candidate selected: range', 'synchronous native-false old duplicate': 'Cancelled old start registered ghost split volley', 'unbounded recovery': 'Recovery exceeded four-query tick budget', 'old trial snapshot revision': 'Fresh manual trial identity rejected', 'stale restoration range': 'Recovery used stale pre-equipment range', 'duplicate accepted registration': 'Packed wrapper duplicate/missing family registration'}


def verify_archer_routing_probe(script):
    for type_ in ARCHERS:
        r = archer_runtime(script, type_); r.visible_units = [102, 103, 104]
        start_archer_volley(r)


def verify_archer_consume_lifetime_probe(script):
    r = archer_runtime(script); r.visible_units = [102, 103]
    volley, _, _ = start_archer_volley(r)
    require(r.invoke('tdConsumeArcherSplitArrowVolley', 101, 102) == volley and
            r.globals['TDArcherSplitArrowVolley_typeId'][volley] != 0,
            'ARCHER consume destroyed volley before its unique expiry')


def verify_archer_recovery_probe(script):
    r = archer_runtime(script); record = r.invoke('tdTargetPriorityGet', 101)
    r.globals['TDTowerTargetPriorityState_parked'][record] = True
    r.lists[r.globals['TDTowerTargetPriorityState_tdTargetPriorityParked']].append(record)
    r.units[101]['acquireRange'] = 0.
    r.invoke('tdTargetPriorityStartRecovery'); r.recovery_tick()
    assert_archer_uncontrolled(r, 'mutation stale recovery')


def mutation_failure_evidence(label, error, expected_assertions):
    """Only a known oracle assertion proves rejection; interpreter faults never do."""
    reason = str(error)
    matched = next((message for message in expected_assertions if message in reason), None)
    require(type(error) is ValueError and matched is not None,
            'Unexpected mutation failure is not rejection evidence: ' + label +
            ' / ' + type(error).__name__ + ': ' + reason)
    return {'label':label,'exception_type':type(error).__name__,'reason':reason,
            'expected_oracle_assertion':matched}


def verify_packed_mutations(script):
    packed = functions(script)
    cases = [
        ('tdHandleTowerAttackStarted', 'tdTargetPriorityAcceptAttack(', 'tdTargetPriorityAcceptAttack_BROKEN(',
         'missing verdict', verify_packed_structure),
        ('tdTargetPriorityStrictlyBetter', ' < ', ' <= ', 'HP tie change',
         lambda changed: verify_rules(TowerTargetRuntime(changed).invoke)),
        ('tdTargetPriorityStrictlyBetter', ' > ', ' >= ', 'rank tie change',
         lambda changed: verify_rules(TowerTargetRuntime(changed).invoke)),
        ('tdTargetPriorityTargetValid', '0.405', '500.405', 'range inflation', verify_manual_and_identity),
        ('tdTargetPriorityRedirect', 'if issued or', 'if issued and',
         'synchronous native-false old duplicate', verify_transaction_replay),
        ('tdTargetPriorityRecoveryTick', 'IMinBJ(', 'IMaxBJ(', 'unbounded recovery', verify_recovery),
        ('tdTargetPriorityManualValid', 'TDTowerTargetPriorityState_manualRevision[',
         'TDTowerTargetPriorityState_manualToken[', 'old trial snapshot revision', verify_trial_identity),
        ('tdTargetPriorityRecoveryTick', next(line.strip() for line in packed['tdTargetPriorityRecoveryTick'][0].splitlines() if 'set range = tdTowerEffectiveRangeForTower(' in line),
         'set range = 100.0', 'stale restoration range', verify_recovery_failures_and_range),
    ]
    wrapper = packed['tdHandleTowerAttackStarted'][0]
    registration = next(line for line in wrapper.splitlines() if 'call tdHandleArcherSplitArrowAttack(' in line)
    cases.append(('tdHandleTowerAttackStarted', registration, registration + '\n' + registration,
                  'duplicate accepted registration', verify_packed_structure))
    source = re.search(r'set (\w+) = GetAttacker\(\)', wrapper)[1]
    target = re.search(r'set (\w+) = GetTriggerUnit\(\)', wrapper)[1]
    allowed_line = next(line for line in wrapper.splitlines() if 'if tdArcherNativeAttackAllowed(' in line)
    accept_call = next(line.strip()[len('if  not '):-len(' then')] for line in wrapper.splitlines()
                       if 'if  not tdTargetPriorityAcceptAttack(' in line)
    family_line = next(line for line in wrapper.splitlines() if 'if tdTowerChoiceForUnitTypeId(' in line)
    recovery = packed['tdTargetPriorityRecoveryTick'][0]
    unpark_line = next(line for line in recovery.splitlines() if 'call tdTargetPriorityUnpark(' in line)
    record = re.search(r'tdTargetPriorityUnpark\((\w+),', unpark_line)[1]
    consume = packed['tdConsumeArcherSplitArrowVolley'][0]
    returned = re.search(r'return (\w+)', consume)[1]
    return_line = next(line for line in consume.splitlines() if 'return ' + returned in line)
    inventory_name = next(name for name, definition in packed.items()
                          if name.startswith('tdRefreshTowerEquipmentBonuses') and 'set cond_result = effectiveRange' in definition[0])
    renderer = packed['tdLaunchArcherSplitArrowVisual'][0]
    renderer_guard = next(line for line in renderer.splitlines() if 'if ' in line)
    setup_line = next(line for line in packed['tdSetupDialogTrigger'][0].splitlines() if 'call tdSetupTargetPriorityOrders(' in line)
    cases.extend([
        ('tdHandleTowerAttackStarted', allowed_line, allowed_line[:-len(' then')] + ' and ' + accept_call + ' then',
         'archer accept restored', verify_archer_routing_probe),
        ('tdHandleTowerAttackStarted', family_line, family_line[:-len(' then')] +
         ' and GetUnitTypeId(' + source + ') != ' + str(rawcode('uA6B')) + ' then',
         'uA6B native branch omitted', verify_archer_routing_probe),
        ('tdTargetPriorityRecoveryTick', unpark_line,
         unpark_line + '\n\tcall IssueTargetOrderById(TDTowerTargetPriorityState_source[' + record + '], 851983, null)',
         'archer recovery resend', verify_archer_recovery_probe),
        (inventory_name, 'set cond_result = effectiveRange', 'set cond_result = 0.0',
         'archer acquire zero', verify_archer_safety_and_equipment),
        ('tdSetupDialogTrigger', setup_line, '', 'global priority setup removed', verify_packed_structure),
        ('tdLaunchArcherSplitArrowVisual', renderer_guard,
         '\tif true then\n\t\treturn\n\tendif\n' + renderer_guard,
         'visual budget restored', verify_packed_structure),
        ('tdConsumeArcherSplitArrowVolley', return_line,
         '\tcall dispatch_TDArcherSplitArrowVolley_destroyTDArcherSplitArrowVolley(' + returned + ', "mutation consume")\n' + return_line,
         'consume destroys volley', verify_archer_consume_lifetime_probe),
        ('tdHandleArcherSplitArrowDamage', ' or DamageEvent_getId() == TDTowerRuntime_TD_ARCHER_SPLIT_ARROW_DAMAGE_EVENT_ID', '',
         'Tspl recursion filter removed', verify_archer_inflight_reuse_and_filters),
        ('tdHandleArcherSplitArrowDamage', 'DamageEvent_getUnreducedOriginalAmount()', 'DamageEvent_getAmount()',
         'mutable split damage basis', verify_split_immutable_basis),
    ])
    PACKED_MUTATION_ASSERTIONS.update({
        'archer accept restored': 'ARCHER native attack was selected/redirected/stopped',
        'uA6B native branch omitted': 'ARCHER native attack was selected/redirected/stopped',
        'archer recovery resend': 'ARCHER native attack was selected/redirected/stopped',
        'archer acquire zero': 'ARCHER inventory refresh projected parked range to zero',
        'global priority setup removed': 'Packed global priority order setup removed',
        'visual budget restored': 'Packed all-arrow renderer restored admission control',
        'consume destroys volley': 'ARCHER consume destroyed volley before its unique expiry',
        'Tspl recursion filter removed': 'ARCHER recursive code/spell/Tspl consumed a new volley',
        'mutable split damage basis': 'Packed split uses immutable original100, not modified210',
    })
    rejected = []
    for name, old, new, label, oracle in cases:
        require(old in packed[name][0], 'Packed mutation anchor missing: ' + label)
        changed = script[:packed[name].start()] + packed[name][0].replace(old, new, 1) + script[packed[name].end():]
        try:
            verify_packed_structure(changed)
            oracle(changed)
        except Exception as error:
            rejected.append(mutation_failure_evidence(label,error,[PACKED_MUTATION_ASSERTIONS[label]]))
        else:
            raise ValueError('Unsafe packed mutation accepted: ' + label)
    return rejected


def register_actual_tower_post_listeners(runtime):
    setup = functions(runtime.script)['tdSetupDialogTrigger'][4]
    for suffix, priority in (('',0),('_1',1),('_2',2)):
        allocator = 'alloc_DamageListener_addListener_TDTowerRuntime' + suffix
        match = re.search(r'set (\w+) = ' + re.escape(allocator) + r'\([^\n]*\)' +
                          r'(?:(?!set \1 =).)*?call (DamageEvent_addListener(?:_\d+)?)\(([^,]+), \1\)', setup, re.S)
        require(match is not None, 'Missing actual tower post listener: ' + allocator)
        expression = match[3].strip()
        if not expression.isdigit():
            assignment = re.search(r'set ' + re.escape(expression) + r' = (\w+)', setup)
            require(assignment is not None and runtime.globals[assignment[1]] == priority,
                    'Post priority lacks actual constant binding')
        else:
            require(int(expression) == priority, 'Native post priority changed')
        listener = runtime.invoke(allocator)
        runtime.invoke('construct_DamageListener', listener)
        runtime.invoke(match[2], priority, listener)


def baseline_trace(script, type_='uA6B', scene='passive'):
    r = TowerTargetRuntime(script)
    r.units[101]['type'] = rawcode(type_)
    for target in (102,103,104):
        r.units[target].update(life=100000., maxLife=1000000.)
    r.units[103]['life'] = r.units[104]['life'] = 200000.
    register_actual_tower_post_listeners(r)
    r.invoke('tdSetupEquipmentCombat')
    pet = None
    if scene == 'passive':
        pet = r.pet([(7,4),(16,4)]); r.roll = 0.
    elif scene == 'control':
        pet = r.pet([(5,4),(17,4)])
        r.units[101]['inventory'] = {0:4242,1:4243}
        r.inventory_items.update({4242:rawcode('iW08'),4243:rawcode('iW06')})
    elif scene == 'active_cd':
        pet = r.pet([(20,2),(7,4)])
    elif scene != 'plain_death':
        raise ValueError('Unknown baseline scenario')
    r.clear_trace(); r.emitted.clear(); r.native_damage.clear(); r.moves.clear(); r.random_draws.clear()
    trace = []
    for index, damage in enumerate((40.,100.,160.,100.,40.,160.,100.,40.)):
        before = len(r.emitted)
        r.attack(102)
        r.emit(damage, target=102); r.flush()
        if scene == 'control':
            r.invoke('tdTickEquipmentDebuffs'); r.drain_zero()
        pet_state = {} if pet is None else {field:r.globals['TDPet_' + field][pet]
                     for field in ('rotation','resolveRotation','readyAt','buffUntil','buffSkill',
                                   'buffPower','pendingSkill','pendingSerial','generation')}
        trace.append({'native_input':damage,'accepted_starts':len(r.accepted),
                      'damage_events':r.emitted[before:], 'pet':pet_state,
                      'native_segments':list(r.native_damage), 'rng':list(r.priority_rng),
                      'movement_calls':list(r.moves),
                      'targets':{str(t):{k:r.units[t][k] for k in ('life','alive','speed','abilities')}
                                 for t in (102,103,104)},
                      'ledger_total':r.score(),
                      'gold':[r.globals['TDState_tdGold'][lane] for lane in range(4)],
                      'lane_score':[r.globals['TDState_tdLaneScore'][lane] for lane in range(4)],
                      'team_score':r.globals['TDState_tdTeamScore'],
                      'pending_effect_tasks':r.invoke('tdPetEffectTaskCount')})
        trace[-1] = json.loads(json.dumps(trace[-1], sort_keys=True))
        r.now += .25
    if scene == 'plain_death':
        r.units[102]['life'] = 25.
        r.attack(102); r.emit(100.,target=102); r.flush()
        r.event_source, r.event_target = 101,102
        r.invoke('tdHandleEnemyDeath')
        trace.append({'death_gold':[r.globals['TDState_tdGold'][lane] for lane in range(4)],
                      'death_score':[r.globals['TDState_tdLaneScore'][lane] for lane in range(4)],
                      'death_team_score':r.globals['TDState_tdTeamScore'],
                      'rng':list(r.priority_rng), 'ledger_total':r.score()})
        require(trace[-1]['death_gold'][0] > trace[0]['gold'][0], 'Death reward comparison did not actually award gold')
        require(trace[-1]['death_score'][0] > trace[0]['lane_score'][0], 'Death comparison did not actually award score')
    require(not r.script_orders and not r.stop_orders, 'Steady-state baseline fixture unexpectedly reselected or stopped')
    require(len(r.accepted) == 8 + (scene == 'plain_death'), 'Steady native starts were dropped/duplicated')
    return trace


def verify_baseline_no_selection(script, baseline_script, baseline_sha):
    require(baseline_sha == BASELINE_SHA256, 'Baseline is not the explicitly verified formal 4abc225 map')
    require('function tdTargetPriorityAcceptAttack takes ' not in baseline_script,
            'Baseline must be a formal release before this target-priority implementation')
    rows = []
    for type_,scene in [('uA6B','passive'),('uO6B','passive'),('uH6B','passive'),
                        ('uD6B','passive'),('uG6B','passive'),('uA6B','control'),
                        ('uA6B','active_cd'),('uA6B','plain_death')]:
        expected = baseline_trace(baseline_script,type_,scene)
        actual = baseline_trace(script,type_,scene)
        require(actual == expected, 'Formal-baseline no-selection trajectory differs: ' + type_ + '/' + scene)
        if scene == 'active_cd':
            require(any(step['pet']['readyAt'] > 10. for step in actual), 'Active cooldown scene did not start real cooldown')
        if scene == 'control':
            require(any(step['movement_calls'] and step['targets']['102']['abilities'] for step in actual),
                    'Control scene did not execute actual movement/carrier effect')
            require(any(step['pet']['resolveRotation'] != 0 for step in actual),
                    'Control/resolve scene did not advance actual six-hit counter')
        if scene == 'passive':
            require(any(step['pet']['rotation'] != 0 for step in actual) and
                    any(step['rng'] for step in actual), 'Pet counter/RNG scene did not exercise real contract')
        rows.append({'tower':type_,'scene':scene,'native_primary_hits':len(actual),
                     'actual_resolveRotation_max':max(step.get('pet',{}).get('resolveRotation',0) for step in actual),
                     'actual_active_readyAt_max':max(step.get('pet',{}).get('readyAt',0.) for step in actual),
                     'actual_movement_calls':max(len(step.get('movement_calls',[])) for step in actual),
                     'actual_RNG_draws':max(len(step.get('rng',[])) for step in actual),
                     'actual_damage_event_count':sum(len(step.get('damage_events',[])) for step in actual),
                     'death_gold':actual[-1].get('death_gold'),
                     'death_lane_score':actual[-1].get('death_score'),
                     'equal_trajectory_sha256':sha(json.dumps(actual,sort_keys=True).encode())})
    return {'baseline_map_sha256':baseline_sha,'cases':rows,
            'actual_packed_native_start_and_damage_chain':True,
            'compared':['original/derived damage events','pet hit counters','actual active cooldown',
                        'slow/armor carrier and speed writes','RNG sequence','damage ledger',
                        'gold and score after actual death settlement'],
            'boundary':'Finite deterministic scenarios and native post-armor input/clock/delivery stubs; no all-input claim, engine armor/stun/DPS simulation or unrelated mode coverage.'}


def verify_base_policy_independent_of_route(script):
    # Legal current/candidates stay inside real tower range. Position/velocity
    # are native fixture inputs; the selector must not read route or speed.
    rows=[]
    for type_,expected in (('uO6B',102),('uD6B',103)):
        r=TowerTargetRuntime(script)
        r.units[101].update(type=rawcode(type_),x=-500.,y=0.)
        r.units[102].update(type=rawcode('uB08'),life=1000.,x=-380.,y=0.,speed=10000.,order=851986,userdata=105)
        r.units[103].update(type=rawcode('uW01'),life=1.,x=-1000.,y=0.,speed=0.,order=851972,userdata=100)
        r.visible_units=[102,103]
        native_reads=('GetUnitMoveSpeed','GetRectMinX','GetRectMinY','GetRectMaxX','GetRectMaxY')
        before={name:r.calls[name] for name in native_reads}
        r.attack(102)
        if expected==102:
            require(r.accepted==[(101,102)] and not r.script_orders,'Base Boss priority lost to route position or HP')
        else:
            require(r.script_orders and r.script_orders[-1][2]==103 and not r.accepted,'Base minimum live HP lost to near-exit Boss')
            scans=r.calls['tdTargetPriorityBest']
            r.units[103]['life']=10000.;r.units[102]['life']=.41
            r.attack(103)
            require(r.accepted==[(101,103)] and r.calls['tdTargetPriorityBest']==scans,'Base pending confirmation rescanned after HP changed')
        require(all(r.calls[name]==before[name] for name in native_reads),'Base selector still reads movement speed or exit rectangle')
        r.command(851983,102);r.clear_trace();scans=r.calls['tdTargetPriorityBest'];r.attack(102)
        require(r.accepted==[(101,102)] and not r.script_orders and r.calls['tdTargetPriorityBest']==scans,'Base manual lock lost to lower HP or route position')
        rows.append({'tower':type_,'base_target':expected,'route_or_speed_reads':0,'manual_lock_preserved':True})
    return {'cases':rows,'pending_confirmation_without_rescan':True,'route_progress_or_speed_priority':False}


def verify_artifact(map_path, source=ROOT / 'wurst', source_only=False, mutations=True, compiled_script=None, baseline_map=None):
    files = source_files(source)
    report = {'source_contract': verify_source_contract(files), 'boundary': BOUNDARY,
              'mutation_coverage': 'SOURCE_AND_PACKED' if mutations and not source_only else
              'SOURCE_ONLY' if mutations else 'NOT_RUN_DIAGNOSTIC',
              'coverage_not_claimed': ['All-input formal-baseline trajectory equivalence',
                                     'Native client DPS/turning/attack-point timing',
                                     'Rendering, dummy recycling, multiplayer synchronization']}

    scalar = source_scalar_namespace(files)
    report['source_rules'] = verify_rules(lambda name, *args: scalar[name](*args))
    if mutations: report['source_mutations_rejected'] = verify_source_mutations(files)
    if source_only:
        require(map_path is None and compiled_script is None and baseline_map is None, '--source-only cannot also claim a map verification')
        report.update(status='PASS_SOURCE_ONLY', actual_mpq_executed=False)
        return report
    require((map_path is None) != (compiled_script is None), 'Supply exactly one map or --compiled-script')
    if compiled_script is not None:
        data = Path(compiled_script).read_bytes()
        script = data.decode('utf-8')
    else:
        data = Path(map_path).read_bytes()
        script = Mpq(data).extract('war3map.j').decode('utf-8')
    report['packed_structure'] = verify_packed_structure(script)
    r = TowerTargetRuntime(script)
    report['packed_rules'] = verify_rules(r.invoke)
    report['base_policy_without_route_override'] = verify_base_policy_independent_of_route(script)
    if baseline_map is not None:
        baseline_data = Path(baseline_map).read_bytes()
        baseline_script = Mpq(baseline_data).extract('war3map.j').decode('utf-8')
        report['baseline_no_selection'] = verify_baseline_no_selection(script,baseline_script,sha(baseline_data))
    for tower in TOWERS:
        require(r.invoke('tdTowerChoiceForUnitTypeId', rawcode(tower)) == FAMILIES[tower[1]],
                'Packed catalog misses one of 35 tower branches: ' + tower)
    report['packed_catalog_rawcodes'] = list(TOWERS)
    report['transactions'] = verify_transaction_replay(script)
    report['commands_and_identity'] = verify_manual_and_identity(script)
    report['catalog_selection'] = verify_catalog_selection(script)
    report['trial_identity'] = verify_trial_identity(script)
    report['split_inflight'] = verify_split_inflight(script)
    report['archer_native_restoration'] = verify_archer_native_restoration(script)
    report['archer_native_orders_recovery'] = verify_archer_native_orders_and_recovery(script)
    report['archer_inflight_reuse_filters'] = verify_archer_inflight_reuse_and_filters(script)
    report['archer_safety_equipment'] = verify_archer_safety_and_equipment(script)
    report['archer_deferred_context'] = verify_archer_deferred_context(script)
    report['sparse_recovery'] = verify_recovery(script)
    report['recovery_failures_range_commands'] = verify_recovery_failures_and_range(script)
    report['existing_split_original_basis'] = verify_split_immutable_basis(script)
    if mutations:
        report['packed_mutations_rejected'] = verify_packed_mutations(script)
    report.update(status='PASS_COMPILED_SCRIPT_ONLY' if compiled_script else 'PASS',
                  actual_mpq_executed=compiled_script is None, jass_sha256=sha(script.encode()),
                  native_event_observation='Controlled replay has no native projectile/order token; no client event timing was measured.')
    report['compiled_script_sha256' if compiled_script else 'map_sha256'] = sha(data)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', nargs='?', type=Path)
    p.add_argument('--baseline-map', type=Path)
    p.add_argument('--source', type=Path, default=ROOT / 'wurst')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--source-only', action='store_true')
    mode.add_argument('--compiled-script', type=Path, help='Diagnostic compiler-output replay; never claims actual MPQ verification')
    p.add_argument('--output', type=Path)
    p.add_argument('--skip-mutations', action='store_true', help='Diagnostic only; report does not include mutation acceptance evidence')
    args = p.parse_args(argv)
    report = verify_artifact(args.map, args.source, args.source_only, not args.skip_mutations, args.compiled_script, args.baseline_map)
    report.update(tool_sha256=sha(Path(__file__).read_bytes()), command=sys.argv if argv is None else argv)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    print(rendered, end='')
    return 0


if __name__ == '__main__':
    main()
