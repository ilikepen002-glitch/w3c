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
    emergency_contract = verify_emergency_source_contract(files)
    all_code = '\n'.join(code(v) for v in files.values())
    require(all_code.count('registerAnyUnitEvent(EVENT_PLAYER_UNIT_ATTACKED)') == 1,
            'Expected exactly one ATTACKED registration')
    require(all_code.count('GetAttacker()') == 1, 'Extra attacker/ATTACKED side-effect listener')
    wrapper = body(tower, 'tdHandleTowerAttackStarted')
    ordered(wrapper, ('let source = GetAttacker()', 'let target = GetTriggerUnit()',
                     'if not tdTargetPriorityAcceptAttack(source, target)', 'return',
                     'tdHandleArcherSplitArrowAttack(source, target)'), 'ATTACKED wrapper')
    require('tdQueueArcherSplitArrowVolley' not in wrapper and
            wrapper.count('tdHandleArcherSplitArrowAttack(') == 1, 'Wrapper queues before verdict or twice')
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
    require('tdTargetPriorityEmergencyReplace(' in select and '.getLife()' in select and
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
    require('tdTargetPriorityProjectedAcquireRange(tower, tdTowerEffectiveRangeForLoadout(' in
            code(files[INVENTORY]), 'Inventory bypasses acquisition pause projection')
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
            'emergency': emergency_contract,
            'source_files_sha256': {p: sha(files[p].encode()) for p in (RULES, STATE, RUNTIME, TOWER, INVENTORY,'enemies/TDEnemyControlRuntime.wurst','TDConfig.wurst')}}


def verify_emergency_source_contract(files):
    rules, runtime = code(files[RULES]), code(files[RUNTIME])
    for literal in ('TD_TARGET_PRIORITY_EMERGENCY_SECONDS = 3.0',
                    'TD_TARGET_PRIORITY_MAX_SPEED = 10000.0',
                    'TD_TARGET_PRIORITY_ROUTE_STAGE_CAPACITY = 6',
                    'TD_TARGET_PRIORITY_ROUTE_LANE_CAPACITY = 4'):
        require(re.search(r'\b' + re.escape(literal) + r'\s*$', rules, re.M), 'Emergency constant changed: ' + literal)
    prepare = body(runtime, 'tdTargetPriorityPrepareGeometry')
    for token in ('tdTargetPriorityGeometryEpoch == tdFlowEpoch()', 'tdLaneExitRect()',
                  'exitRect == null', 'GetRectMinX(exitRect)', 'GetRectMinY(exitRect)',
                  'GetRectMaxX(exitRect)', 'GetRectMaxY(exitRect)', 'tdLaneWaypointCount(lane)',
                  'count >= TD_TARGET_PRIORITY_ROUTE_STAGE_CAPACITY', 'tdLaneWaypointRect(lane, index)',
                  'waypointRect == null', 'tdLaneWaypointPosition(lane, index)',
                  'tdTargetPrioritySuffix[slot + 1]', 'tdTargetPriorityGeometryEpoch = tdFlowEpoch()'):
        require(token in prepare, 'Real fixed-path geometry cache missing: ' + token)
    require('Fallback' not in prepare and 'tdLaneExitPosition' not in prepare,
            'Emergency path cached no-handle fallback geometry')
    entry = body(rules, 'tdTargetPriorityExitEntryDistance')
    require('SquareRoot(dx * dx + dy * dy) * fraction' in entry, 'Emergency forgot exit first-entry boundary')
    emergency = body(rules, 'tdTargetPriorityEmergencyReplace')
    ordered(emergency, ('if urgent != bestUrgent', 'return urgent', 'if urgent', 'if eta != bestEta',
                         'return eta < bestEta', 'if keepCurrent', 'return false',
                         'return tdTargetPriorityReplace('), 'Urgent-only override comparator')
    eta = body(runtime, 'tdTargetPriorityEnemyEta')
    ordered(eta, ('tdTrialIsTargetType(enemy)', 'tdTargetPriorityInsideExit(', 'return 0.0',
                  'IsUnitPaused(enemy)', 'tdEnemyHasActiveMovementControl(enemy)',
                  'enemy.getCurrentOrder() != tdEnemyLaneOrderIdForTest()', 'GetUnitMoveSpeed(enemy)',
                  'tdTargetPrioritySpeedValid(speed)', 'tdEnemyWaypointIndex(enemy)',
                  'index < 0 or index > count', 'tdTargetPriorityExitEntryDistance(',
                  'tdTargetPrioritySuffix[slot]', 'position.distanceTo(next) + suffix'),
            'Inside-exit-before-freeze, real-speed and P1-polyline ETA')
    require('readyAt' not in eta and 'SetUnitMoveSpeed' not in runtime,
            'Emergency uses post-control protection or writes/recomposes speed')
    select = body(runtime, 'tdTargetPriorityBest')
    require(select.count('tdTargetPriorityPrepareGeometry()') == 1 and
            select.count('tdTargetPriorityEnemyEta(') == 2 and
            'candidate == currentTarget and keepCurrent ? currentEta :' in select,
            'ETA repeated geometry/current reads or failed to reuse immutable current ETA')
    require(select.count('enumUnitsInRange(') == 1 and select.count('tdTargetPriorityEmergencyReplace(') == 1,
            'Emergency policy adds an extra scan or sorting pass')
    control = code(files['enemies/TDEnemyControlRuntime.wurst'])
    query = body(control, 'tdEnemyHasActiveMovementControl')
    for token in ("enemy.getAbilityLevel('BPSE') > 0", 'record.enemy == enemy',
                  'record.buffId != 0', 'enemy.getAbilityLevel(record.buffId) > 0'):
        require(token in query, 'Movement-control read lost actual source/buff identity: ' + token)
    require(not re.search(r'readyAt|reserve|cancel|destroy|SetUnit|saveInt|saveBoolean', query),
            'Read-only movement query became a control tracker/protection check')
    return {'emergency_seconds': 3., 'real_rect_cached_per_epoch': True,
            'fixed_route_slots': [4,6], 'per_legal_candidate_eta_reads': 1,
            'inside_exit_precedes_control_speed': True, 'trial_urgent': False}


def verify_emergency_rules(invoke):
    checked = 0
    for policy, eta, best_eta, hp, best_hp, rank, best_rank, keep in itertools.product(
            (1,2), (-1.,0.,2.999,3.,3.001,10.), (-1.,0.,3.,3.001),
            (1.,100.), (1.,100.), (0,2), (0,2), (False,True)):
        urgent, best_urgent = 0. <= eta <= 3., 0. <= best_eta <= 3.
        base = hp < best_hp if policy == 1 else rank > best_rank
        equal = hp == best_hp if policy == 1 else rank == best_rank
        expected = urgent if urgent != best_urgent else eta < best_eta if urgent and eta != best_eta else                   False if urgent and keep else base or (not keep and equal)
        actual = invoke('tdTargetPriorityEmergencyReplace', policy,hp,rank,10,eta,
                        best_hp,best_rank,20,best_eta,keep)
        require(actual == expected, 'Emergency/base/current-tie precedence mismatch')
        checked += 1
    for eta, urgent in ((2.999,True),(3.,True),(3.001,False),(-1.,False),(math.nan,False)):
        require(invoke('tdTargetPriorityUrgent', eta) == urgent, 'Emergency 3s threshold/NaN mismatch')
    for speed in (0., -1., math.nan, math.inf,10000.001):
        require(not invoke('tdTargetPrioritySpeedValid', speed), 'Invalid actual speed accepted')
        require(invoke('tdTargetPriorityDistanceEta',900.,speed) == -1., 'Invalid speed divided/clamped')
    near(invoke('tdTargetPriorityDistanceEta',900.,300.),3., 'Current speed ETA')
    near(invoke('tdTargetPriorityDistanceEta',900.,150.),6., 'Current slowed speed ETA')
    bounds = (-10.,-20.,10.,20.)
    points = [(0.,0.,0.),(10.,20.,0.),(50.,0.,40.),(0.,60.,40.),
              (30.,60.,math.sqrt(2000.)),(20.,40.,math.sqrt(500.))]
    for x,y,expected in points:
        near(invoke('tdTargetPriorityExitEntryDistance', x,y,*bounds),expected,'Rect first-entry geometry')
    require(invoke('tdTargetPriorityExitEntryDistance',0.,0.,0.,0.,0.,20.) == -1., 'Invalid exit rect admitted')
    require(invoke('tdTargetPriorityExitEntryDistance',math.nan,0.,*bounds) == -1., 'NaN position admitted')
    return {'emergency_comparator_cases': checked, 'threshold_cases': [2.999,3.,3.001],
            'rect_first_entry_cases': len(points), 'invalid_speed_fail_closed': True,
            'nonurgent_base_policy_unchanged': True}


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
                 'tdTargetPrioritySpeedValid', 'tdTargetPriorityCoordinateValid',
                 'tdTargetPriorityExitBoundsValid', 'tdTargetPriorityInsideExit',
                 'tdTargetPriorityExitEntryDistance', 'tdTargetPriorityDistanceEta',
                 'tdTargetPriorityUrgent', 'tdTargetPriorityEmergencyReplace'):
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
        (RULES, 'TD_TARGET_PRIORITY_EMERGENCY_SECONDS = 3.0', 'TD_TARGET_PRIORITY_EMERGENCY_SECONDS = 30.0', 'emergency threshold expanded'),
        (RULES, 'SquareRoot(dx * dx + dy * dy) * fraction', 'SquareRoot(dx * dx + dy * dy)', 'exit center replaces boundary'),
        (RULES, '\tif urgent\n', '\tif true\n', 'permanent ETA sorting'),
        (RUNTIME, 'tdTrialIsTargetType(enemy) or', 'false or', 'trial becomes urgent'),
        (RUNTIME, 'let suffix = tdTargetPrioritySuffix[slot]', 'let suffix = 0.0', 'P1 polyline removed'),
        (RUNTIME, '? currentEta :', '? bestEta :', 'immutable current ETA lost'),
        (RUNTIME, 'enemy.getCurrentOrder() != tdEnemyLaneOrderIdForTest()', 'false', 'stopped enemy marked moving'),
        ('enemies/TDEnemyControlRuntime.wurst', 'enemy.getAbilityLevel(record.buffId) > 0', 'record.window.readyAt > 0.0', 'protection deadline treated as freeze'),
        (TOWER, 'function tdHandleArcherSplitArrowDamage()\n',
         'function tdHandleArcherSplitArrowDamage()\n\ttdTargetPriorityAcceptAttack(null, null)\n', 'damage selection bridge'),
    ]
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
    def __init__(self, script):
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
        self.units[101].update(type=rawcode('uA6B'), x=0., y=1000., order=0, owner=0,
                               abilities={self.globals['TDTowerCatalogData_TD_ARCHER_SPLIT_ARROW_ABILITY_ID']: 1},
                               inventory={})
        self.enemy(102, life=100.)
        self.enemy(103, life=10.)
        self.enemy(104, life=80.)
        self.visible_units = [102, 103, 104]
        # Admission is intentionally saturated using the real VFX budget; split
        # shots/queues still execute, while dummy recycler rendering is outside
        # this transaction fixture. No gameplay target/queue helper is stubbed.
        self.globals['TDTowerRuntime_tdArcherVisualCreationWindow'] = int(self.now)
        self.globals['TDTowerRuntime_tdArcherVisualCreationCount'] = 6
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

    def tower(self, handle, type_='uA11', lane=0):
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
        if name == 'GetUnitMoveSpeed':
            return True, self.units.get(args[0], {}).get('speed', 0.)
        if name == 'IsUnitPaused':
            return True, self.units.get(args[0], {}).get('paused', False)
        if name == 'ModuloReal':
            return True, args[0] % args[1]
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
        if name == 'SetUnitAcquireRange':
            self.acquisition.append(tuple(args[:2]))
        if name == 'group_enumUnitsInRange' and self.priority_ready:
            self.group_queries.append((self.event_source, self.now, tuple(args)))
        if name == 'CreateGroup':
            handled, handle = super().native(name, args)
            self.live_groups.add(handle)
            return handled, handle
        if name in ('group_destr', 'DestroyGroup'):
            require(args[0] in self.live_groups, 'Unknown/double-destroyed selector group')
            self.live_groups.remove(args[0])
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
    function_code = '\n'.join(function[4] for function in packed.values())
    require(function_code.count('GetAttacker()') == 1 and function_code.count('EVENT_PLAYER_UNIT_ATTACKED') == 1,
            'Packed artifact introduced another attacker/ATTACKED registration')
    for name in ('tdHandleTowerAttackStarted', 'tdTargetPriorityAcceptAttack',
                 'tdTargetPriorityTargetValid', 'tdTargetPriorityBest',
                 'tdTargetPriorityHandleOrder', 'tdTargetPriorityRecoveryTick',
                 'tdTargetPriorityPrepareGeometry','tdTargetPriorityEnemyEta','tdTargetPriorityEmergencyReplace',
                 'tdTargetPriorityExitEntryDistance','tdEnemyHasActiveMovementControl'):
        require(name in packed, 'Missing actual packed priority function: ' + name)
    wrapper = packed['tdHandleTowerAttackStarted'][4]
    ordered(wrapper, ('GetAttacker()', 'GetTriggerUnit()', 'tdTargetPriorityAcceptAttack(',
                     'return', 'tdHandleArcherSplitArrowAttack('), 'Packed ATTACKED wrapper')
    require(wrapper.count('tdHandleArcherSplitArrowAttack(') == 1 and
            'tdQueueArcherSplitArrowVolley(' not in wrapper, 'Packed wrapper queues before verdict/twice')
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
        require(len(r.lists[r.globals['TDTowerRuntime_tdArcherSplitArrowVolleys']]) == 1, 'Accepted transaction must own exactly one actual split volley')
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
    return {'35_rawcodes_actual_selectors': rows, 'hp_percent_adversary': True,
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
    r = TowerTargetRuntime(script)
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
            'render_boundary': 'Real visual admission budget saturated (6 new/sec) in the controlled fixture; renderer and dummy recycling are not measured.'}


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


PACKED_MUTATION_ASSERTIONS = {'missing verdict': 'Packed ATTACKED wrapper: missing/out-of-order tdTargetPriorityAcceptAttack(',
 'HP tie change': 'Actual comparator violates strict/current/tie rule',
 'rank tie change': 'Actual comparator violates strict/current/tie rule',
 'range inflation': 'Invalid better candidate selected: range',
 'synchronous native-false old duplicate': 'Cancelled old start registered ghost split volley',
 'unbounded recovery': 'Recovery exceeded four-query tick budget',
 'old trial snapshot revision': 'Fresh manual trial identity rejected',
 'stale restoration range': 'Recovery used stale pre-equipment range',
 'duplicate accepted registration': 'Packed wrapper queues before verdict/twice',
 'exit center instead of first entry': 'P1 remaining polyline/entry mismatch at next index 0',
 'P1 remaining polyline omitted': 'P1 remaining polyline/entry mismatch at next index 0',
 'trial urgency admitted': 'Trial inside exit became urgent',
 'stationary current speed predicted moving': 'Outside-exit movement exclusion failed: stopped',
 'nonurgent permanent ETA sorting': 'No-urgent selection did not restore complete base family policy',
 'late current reused mutable best ETA': 'Late current incorrectly reused changed best ETA',
 'repeated geometry prepare per selector': 'Selection rebuilt/prepared geometry more than once per '
                                           'local scan',
 'protection deadline mistaken for current freeze': 'Post-control protection was mistaken for current '
                                                    'frozen state',
 '3s boundary excluded': 'Emergency/base/current-tie precedence mismatch',
 'zero speed admitted': 'Invalid actual speed accepted',
 'freeze tested before actual exit inclusion': 'Inside-exit exclusion hid a pending leak: paused',
 'duplicate local enumeration': 'Dense steady 40-source ATTACKED changed selector/order budget'}


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


def entry_distance_oracle(x, y, bounds):
    """Independent rectangle segment-intersection expected value, never gameplay."""
    minx,miny,maxx,maxy = bounds
    cx,cy = (minx+maxx)/2.,(miny+maxy)/2.
    delta = (cx-x,cy-y)
    lower,upper = 0.,1.
    for start,direction,lo,hi in ((x,delta[0],minx,maxx),(y,delta[1],miny,maxy)):
        if direction == 0.:
            require(lo <= start <= hi, 'Oracle parallel segment cannot enter exit')
        else:
            a,b=(lo-start)/direction,(hi-start)/direction
            lower=max(lower,min(a,b));upper=min(upper,max(a,b))
    require(lower <= upper, 'Oracle segment-to-center misses exit')
    return math.hypot(*delta)*lower


def actual_geometry(runtime):
    exit_rect = runtime.invoke('tdLaneExitRect')
    bounds = tuple(runtime.rects[exit_rect])
    points = []
    for index in range(runtime.invoke('tdLaneWaypointCount',0)):
        rect = runtime.rects[runtime.invoke('tdLaneWaypointRect',0,index)]
        points.append(((rect[0]+rect[2])/2.,(rect[1]+rect[3])/2.))
    return bounds,points


def moving_enemy(runtime, target=102, lane=0, index=5, x=-1136., y=304., speed=300.):
    runtime.enemy(target,lane=lane,x=x,y=y)
    runtime.units[target].update(userdata=lane*10000+100+index,
                                order=runtime.invoke('tdEnemyLaneOrderIdForTest'),speed=speed)
    return target


def verify_emergency_geometry(script):
    r=TowerTargetRuntime(script)
    bounds,points=actual_geometry(r)
    require(bounds == (-384.,-448.,352.,64.) and points ==
            [(-1152.,2640.),(-1184.,1424.),(-2800.,1376.),(-2800.,400.),(-1136.,304.)],
            'Actual packed leak/waypoint geometry drifted; explicitly review route oracle')
    require(r.invoke('tdTargetPriorityPrepareGeometry'), 'Actual geometry cache did not initialize')
    read_names=('GetRectMinX','GetRectMinY','GetRectMaxX','GetRectMaxY')
    reads=sum(r.calls[n] for n in read_names)
    require(r.invoke('tdTargetPriorityPrepareGeometry') and sum(r.calls[n] for n in read_names)==reads,
            'Same-epoch geometry cache reread native rectangles')
    actual=[]
    suffix=[0.]*6
    suffix[4]=entry_distance_oracle(*points[4],bounds)
    for index in range(3,-1,-1):
        suffix[index]=math.dist(points[index],points[index+1])+suffix[index+1]
    for index in range(6):
        moving_enemy(r,index=index,x=-16.,y=100.)
        expected=(entry_distance_oracle(-16.,100.,bounds) if index==5 else
                  math.dist((-16.,100.),points[index])+suffix[index])/10000.
        r.units[102]['speed']=10000.
        value=r.invoke('tdTargetPriorityEnemyEta',102,0,True)
        require(math.isclose(value,expected,rel_tol=1e-6,abs_tol=1e-5),
                'P1 remaining polyline/entry mismatch at next index '+str(index))
        actual.append(value)
    moving_enemy(r,index=4)
    entry=r.invoke('tdTargetPriorityEnemyEta',102,0,True)
    center=math.dist(points[4],((bounds[0]+bounds[2])/2.,(bounds[1]+bounds[3])/2.))/300.
    require(0 < entry <= 3. < center, 'Packed P1 final segment must cross 3s only after exit-boundary deduction')
    for lane in range(1,4):
        moving_enemy(r,lane=lane,index=0,x=1000.,y=-192.)
        require(math.isclose(r.invoke('tdTargetPriorityEnemyEta',102,lane,True),648./300.),
                'Zero-waypoint lane failed direct real-rectangle entry')
    for position in ((-1000.,-192.),(-16.,1000.),(352.,100.),(-384.,64.),(-16.,-192.)):
        moving_enemy(r,index=5,x=position[0],y=position[1])
        require(math.isclose(r.invoke('tdTargetPriorityEnemyEta',102,0,True),
                             entry_distance_oracle(*position,bounds)/300.), 'Packed rect edge/parallel/diagonal failed')
    invalid_indices=[]
    for index in (-1,6,99):
        moving_enemy(r,index=index)
        require(r.invoke('tdTargetPriorityEnemyEta',102,0,True)==-1.,'Illegal waypoint index became urgent')
        invalid_indices.append(index)
    moving_enemy(r,index=0,x=-16.,y=100.)
    require(r.invoke('tdTargetPriorityEnemyEta',102,0,True)==-1.,
            'P1 early remaining route was replaced with near-exit Euclidean distance')
    # Missing regions are retried, never replaced by TDConfig's fallback positions.
    r=TowerTargetRuntime(script);original=r.globals['gg_rct_td_exit_center']
    r.globals['gg_rct_td_exit_center']=None
    require(not r.invoke('tdTargetPriorityPrepareGeometry'),'Missing actual exit cached a fallback')
    r.globals['gg_rct_td_exit_center']=original
    require(r.invoke('tdTargetPriorityPrepareGeometry'),'Actual exit appearing later could not initialize')
    epoch_global=next(line.split('return ',1)[1].strip() for line in functions(script)['tdFlowEpoch'][4].splitlines() if 'return ' in line)
    reads=sum(r.calls[n] for n in read_names)
    r.globals[epoch_global]+=1
    require(r.invoke('tdTargetPriorityPrepareGeometry') and sum(r.calls[n] for n in read_names)>reads,
            'New flow epoch did not rebuild actual geometry')
    r.globals['TDTowerTargetPriorityRuntime_tdTargetPriorityGeometryEpoch']=-1
    r.globals['TDConfig_TD_PLAYER_ONE_WAYPOINT_COUNT']=6
    require(not r.invoke('tdTargetPriorityPrepareGeometry'),'Over-capacity route stages did not fail closed')
    r.globals['TDConfig_TD_PLAYER_ONE_WAYPOINT_COUNT']=5
    waypoint_handle=r.globals['gg_rct_td_spawn_p1_3'];r.globals['gg_rct_td_spawn_p1_3']=None
    require(not r.invoke('tdTargetPriorityPrepareGeometry'),'Missing waypoint used fallback geometry')
    r.globals['gg_rct_td_spawn_p1_3']=waypoint_handle
    require(r.invoke('tdTargetPriorityPrepareGeometry'),'Missing waypoint could not retry real handle')
    r.globals['TDTowerTargetPriorityRuntime_tdTargetPriorityGeometryEpoch']=-1
    r.globals['TDConfig_TD_ACTIVE_PLAYER_COUNT']=5
    require(not r.invoke('tdTargetPriorityPrepareGeometry'),'Over-capacity lane cache did not fail closed')
    return {'actual_exit_bounds':bounds,'actual_p1_waypoint_centers':points,
            'p1_next_indices_0_to_5_eta_at_10000':actual,
            'tail_at_speed300_entry_eta':entry,'tail_center_eta':center,
            'invalid_next_indices':invalid_indices,'direct_other_lanes':3,
            'same_epoch_zero_rect_reads':True,'missing_rect_retry':True,'epoch_rebuild':True,
            'over_capacity_lane_fail_closed':True,'over_capacity_route_fail_closed':True,'missing_waypoint_retry':True}


def verify_emergency_control(script):
    r=TowerTargetRuntime(script);require(r.invoke('tdTargetPriorityPrepareGeometry'),'No actual geometry')
    def eta(): return r.invoke('tdTargetPriorityEnemyEta',102,0,True)
    exclusions=[]
    for label,changes in [('paused',{'paused':True}),('stunned',{'kinds':{'ground','stunned'}}),
                          ('snared',{'kinds':{'ground','snared'}}),('stopped',{'order':851972}),
                          ('hold',{'order':851993}),('BPSE',{'abilities':{rawcode('BPSE'):1}})]:
        moving_enemy(r);r.units[102].update(changes)
        require(eta()==-1.,'Outside-exit movement exclusion failed: '+label)
        r.units[102].update(x=-16.,y=-192.,speed=0.)
        require(eta()==0.,'Inside-exit exclusion hid a pending leak: '+label)
        exclusions.append(label)
    # All actual control identities share the existing recorded buff, no fabricated deadline tracker.
    moving_enemy(r)
    record=r.invoke('windowFor',102)
    window=r.globals['TDEnemyControlWindow_window'][record]
    r.globals['TDShieldWindow_readyAt'][window]=1000.
    buffs=[r.globals['TDPetCastContext_TD_PET_' + kind + '_BUFF_ID'] for kind in ('ROOT','FREEZE','STAGGER','BOSS')]
    for buff in buffs:
        r.globals['TDEnemyControlWindow_buffId'][record]=buff
        r.units[102]['abilities']={buff:1}
        require(r.invoke('tdEnemyHasActiveMovementControl',102) and eta()==-1.,
                'Actual recorded movement buff did not exclude urgency')
        r.units[102].update(x=-16.,y=-192.,speed=0.)
        require(eta()==0.,'Actual freeze/root inside exit hid pending leak')
        r.units[102].update(x=-1136.,y=304.,speed=300.)
        r.units[102]['abilities']={}
        require(not r.invoke('tdEnemyHasActiveMovementControl',102) and eta()>0.,
                'Post-control protection was mistaken for current frozen state')
    r.globals['TDEnemyControlWindow_enemy'][record]=103
    r.units[102]['abilities']={buffs[0]:1}
    require(not r.invoke('tdEnemyHasActiveMovementControl',102),'Reused handle control record ignored enemy identity')
    r.globals['TDEnemyControlWindow_enemy'][record]=102;r.units[102]['abilities']={}
    values=[]
    for speed in (150.,300.,600.):
        moving_enemy(r,speed=speed);values.append(eta())
    require(math.isclose(values[0],values[1]*2.) and math.isclose(values[2],values[1]/2.),
            'Effective sprint/slow speed was multiplied twice')
    for speed in (0.,-1.,float('nan'),float('inf'),10000.001):
        moving_enemy(r,speed=speed);require(eta()==-1.,'Invalid configured speed became urgent')
    moving_enemy(r);r.units[102]['order']=851972;require(eta()==-1.,'Stopped was predicted moving')
    r.units[102]['order']=r.invoke('tdEnemyLaneOrderIdForTest');require(eta()>0.,'Move resumption not reevaluated')
    r.units[102]['type']=rawcode('uTrG');r.units[102].update(x=-16.,y=-192.)
    require(eta()==-1.,'Trial inside exit became urgent')
    return {'outside_and_inside_exclusions':exclusions,'actual_recorded_buff_identity_cases':len(buffs),
            'protection_without_buff_moves':True,'current_speed_150_300_600_eta':values,
            'invalid_speed_cases':5,'trial_never_urgent':True,'stop_then_move_reevaluated':True}


def urgent_fixture(script,type_='uO6B'):
    r=TowerTargetRuntime(script);r.units[101].update(type=rawcode(type_),x=-1136.,y=304.)
    moving_enemy(r,102,index=4);r.units[102].update(type=rawcode('uB08'),life=100.)
    moving_enemy(r,103,index=4);r.units[103]['life']=200.
    r.units[102]['order']=851972
    r.visible_units=[102,103]
    return r


def verify_emergency_selection(script):
    r=urgent_fixture(script);r.attack(102)
    require(not r.accepted and r.script_orders[-1][2]==103,'Urgent ordinary failed to override nonurgent Boss')
    r.attack(103);require(r.accepted==[(101,103)] and len(r.group_queries)==1,'Pending urgency confirmation reselected')
    # Strict smaller ETA dominates HP/rank; exactly equal urgent current is kept.
    for current in (102,103):
        r=urgent_fixture(script);r.units[102].update(order=r.invoke('tdEnemyLaneOrderIdForTest'),speed=300.)
        r.attack(current)
        require(r.accepted==[(101,current)] and not r.script_orders,'Equal urgent ETA failed to retain legal current')
    r=urgent_fixture(script);r.units[102].update(order=r.invoke('tdEnemyLaneOrderIdForTest'),speed=300.)
    r.units[103]['speed']=600.;r.attack(102)
    require(r.script_orders and r.script_orders[-1][2]==103,'Smaller urgent ETA did not outrank Boss')
    for type_,expected in (('uA6B',103),('uO6B',102)):
        r=urgent_fixture(script,type_);r.units[102].update(life=200.,order=851972)
        r.units[103].update(life=10.,order=851972)
        r.attack(102)
        require((r.script_orders[-1][2] if r.script_orders else r.accepted[-1][1])==expected,
                'No-urgent selection did not restore complete base family policy')
    r=urgent_fixture(script);r.command(851983,102);r.clear_trace();r.attack(102)
    require(r.accepted==[(101,102)] and not r.script_orders and not r.group_queries,'Emergency overrode valid manual lock')
    for synchronous in (False,True):
        for success in (False,True):
            r=urgent_fixture(script);r.order_result=success
            if synchronous:r.order_callback=lambda rt,source,target:rt.attack(target,source)
            r.attack(102)
            if synchronous or success:
                if not synchronous:
                    r.units[102].update(x=-16.,y=-192.,order=r.invoke('tdEnemyLaneOrderIdForTest'))
                    r.attack(103)
                require(r.accepted==[(101,103)] and len(r.group_queries)==1,
                        'Urgent pending was rescanned or registered twice across native delivery')
            else:
                require(r.accepted==[(101,102)],'Urgent native-false did not preserve legal old attack once')
    # Current is enumerated AFTER best changed: mutable bestEta must never replace frozen currentEta.
    r=urgent_fixture(script,'uA6B');r.units[102].update(type=rawcode('uW01'),life=1.,order=r.invoke('tdEnemyLaneOrderIdForTest'))
    r.units[103]['speed']=600.;r.visible_units=[103,102];r.attack(102)
    require(r.script_orders and r.script_orders[-1][2]==103,'Late current incorrectly reused changed best ETA')
    # Actual trial target remains normal legal identity but never urgent inside the exit.
    r=TowerTargetRuntime(script);r.enter();target=r.target(0)
    r.units[101].update(x=-16.,y=-192.);r.units[target].update(x=-16.,y=-192.,life=1.)
    r.enemy(102,life=20.,x=-16.,y=-192.);r.visible_units=[target,102]
    r.attack(target)
    require(r.script_orders and r.script_orders[-1][2]==102,'Inside-exit trial competed as urgent')
    return {'urgent_ordinary_over_boss':True,'strict_eta_before_rank_hp':True,
            'exact_eta_keeps_current':2,'nonurgent_base_policies':2,'manual_lock_wins':True,
            'urgent_sync_async_native_result_cases':4,'pending_eta_change_zero_reselection':True,
            'trial_legal_but_nonurgent':True,'late_current_immutable_eta':True}


def verify_emergency_dense_cost(script):
    r=TowerTargetRuntime(script);r.units[101].update(x=-1136.,y=304.)
    for target in range(102,142):
        moving_enemy(r,target,index=4);r.units[target]['life']=100.
    r.visible_units=list(range(102,142))
    for source in range(200,240):
        r.tower(source,type_='uA11');r.units[source].update(x=-1136.,y=304.)
    reads=sum(r.calls[n] for n in ('GetRectMinX','GetRectMinY','GetRectMaxX','GetRectMaxY'))
    eta_count=r.calls['tdTargetPriorityEnemyEta'];prepare_count=r.calls['tdTargetPriorityPrepareGeometry']
    timer_count=len(r.periodics)
    for source in range(200,240):r.attack(102,source)
    require(len(r.group_queries)==40 and not r.script_orders and len(r.accepted)==40,
            'Dense steady 40-source ATTACKED changed selector/order budget')
    require(r.calls['tdTargetPriorityEnemyEta']-eta_count==40*40,
            'ETA current/candidates were reread or skipped; current ETA must remain immutable')
    require(r.calls['tdTargetPriorityPrepareGeometry']-prepare_count==40,
            'Selection rebuilt/prepared geometry more than once per local scan')
    geometry_reads=sum(r.calls[n] for n in ('GetRectMinX','GetRectMinY','GetRectMaxX','GetRectMaxY'))-reads
    require(0 < geometry_reads <= 44 and len(r.periodics)==timer_count and not r.live_groups and not r.priority_rng,
            'Dense ETA created timers/RNG/group leak or repeated native geometry reads')
    return {'sources':40,'local_candidates_per_source':40,'actual_eta_calls':1600,
            'local_group_enumerations':40,'geometry_native_reads_first_epoch_only':geometry_reads,
            'new_periodic_timers':0,'script_orders':0,'RNG_calls':0}


def verify_emergency_packed_mutations(script):
    packed=functions(script)
    geometry=lambda changed:verify_emergency_geometry(changed)
    selection=lambda changed:verify_emergency_selection(changed)
    control=lambda changed:verify_emergency_control(changed)
    rules=lambda changed:verify_emergency_rules(TowerTargetRuntime(changed).invoke)
    cases=[
        ('tdTargetPriorityExitEntryDistance',' * fraction','', 'exit center instead of first entry',geometry),
        ('tdTargetPriorityEnemyEta',' + suffix, speed)',', speed)','P1 remaining polyline omitted',geometry),
        ('tdTargetPriorityEnemyEta','tdTrialIsTargetType(enemy_1)','false','trial urgency admitted',control),
        ('tdTargetPriorityEnemyEta','unit_getCurrentOrder(enemy_1) != tdEnemyLaneOrderIdForTest()',
         'false','stationary current speed predicted moving',control),
        ('tdTargetPriorityEmergencyReplace',
         'return tdTargetPriorityReplace(policy, hp, rank, key_1, bestHp, bestRank, bestKey, keepCurrent)',
         'return eta < bestEta','nonurgent permanent ETA sorting',selection),
        ('tdTargetPriorityBest','set cond_result_4 = currentEta','set cond_result_4 = bestEta',
         'late current reused mutable best ETA',selection),
        ('tdTargetPriorityBest','set geometryReady = tdTargetPriorityPrepareGeometry()',
         'set geometryReady = tdTargetPriorityPrepareGeometry()\n\tcall tdTargetPriorityPrepareGeometry()',
         'repeated geometry prepare per selector',verify_emergency_dense_cost),
        ('tdEnemyHasActiveMovementControl',
         'unit_getAbilityLevel(enemy_1, TDEnemyControlWindow_buffId[record_1]) > 0',
         'TDShieldWindow_readyAt[TDEnemyControlWindow_window[record_1]] > getElapsedGameTime()',
         'protection deadline mistaken for current freeze',control),
        ('tdTargetPriorityUrgent','eta <= TDTowerTargetPriorityRules_TD_TARGET_PRIORITY_EMERGENCY_SECONDS',
         'eta < TDTowerTargetPriorityRules_TD_TARGET_PRIORITY_EMERGENCY_SECONDS','3s boundary excluded',rules),
        ('tdTargetPrioritySpeedValid','speed > 0.0','speed >= 0.0','zero speed admitted',rules),
    ]
    eta=packed['tdTargetPriorityEnemyEta'][0]
    inside=re.search(r'\tif tdTargetPriorityInsideExit\([^\n]*\n(?:\t\t[^\n]*\n)*?\t\treturn 0\.0\n\tendif\n',eta)
    frozen=re.search(r'\tif IsUnitPaused\([^\n]*\n(?:\t\t[^\n]*\n)*?\t\treturn  - 1\.0\n\tendif\n',eta)
    require(inside is not None and frozen is not None and inside.end()==frozen.start(),
            'Cannot locate actual inside-exit then freeze branches for mutation')
    cases.append(('tdTargetPriorityEnemyEta',inside[0]+frozen[0],frozen[0]+inside[0],
                  'freeze tested before actual exit inclusion',control))
    # O(N) real iterator remains one local enumeration, with no replacement selector stub.
    best=packed['tdTargetPriorityBest'][0]
    enumeration=next(line for line in best.splitlines() if 'call group_enumUnitsInRange(' in line)
    cases.append(('tdTargetPriorityBest',enumeration,enumeration+'\n'+enumeration,
                  'duplicate local enumeration',verify_emergency_dense_cost))
    rejected=[]
    for name,old,new,label,oracle in cases:
        require(old in packed[name][0],'Emergency packed mutation anchor missing: '+label)
        changed=script[:packed[name].start()]+packed[name][0].replace(old,new,1)+script[packed[name].end():]
        try:oracle(changed)
        except Exception as error:
            rejected.append(mutation_failure_evidence(label,error,[PACKED_MUTATION_ASSERTIONS[label]]))
        else:raise ValueError('Unsafe emergency packed mutation accepted: '+label)
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
        r.globals['TDTowerRuntime_tdArcherVisualCreationWindow'] = int(r.now)
        r.globals['TDTowerRuntime_tdArcherVisualCreationCount'] = 6
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
        r.globals['TDTowerRuntime_tdArcherVisualCreationWindow'] = int(r.now)
        r.globals['TDTowerRuntime_tdArcherVisualCreationCount'] = 6
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
    report['source_emergency_rules'] = verify_emergency_rules(lambda name,*args: scalar[name](*args))
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
    report['packed_emergency_rules'] = verify_emergency_rules(r.invoke)
    report['emergency_geometry'] = verify_emergency_geometry(script)
    report['emergency_control'] = verify_emergency_control(script)
    report['emergency_selection'] = verify_emergency_selection(script)
    report['emergency_dense_cost'] = verify_emergency_dense_cost(script)
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
    report['sparse_recovery'] = verify_recovery(script)
    report['recovery_failures_range_commands'] = verify_recovery_failures_and_range(script)
    report['existing_split_original_basis'] = verify_split_immutable_basis(script)
    if mutations:
        report['packed_mutations_rejected'] = verify_packed_mutations(script)
        report['emergency_packed_mutations_rejected'] = verify_emergency_packed_mutations(script)
    report.update(status='PASS_COMPILED_SCRIPT_ONLY' if compiled_script else 'PASS',
                  actual_mpq_executed=compiled_script is None, jass_sha256=sha(script.encode()),
                  native_event_observation='A legal native ATTACKED delivered under stop/hold/nonattack order may still register its original contract. Warcraft 1.28 supplies no per-event order token. The gate proves no automatic order override and no old outer registration after observable synchronous intent changes.')
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
