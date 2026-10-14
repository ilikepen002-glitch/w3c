#!/usr/bin/env python3
"""Fail-closed source contract for per-lane wave24 chosen tower evolution.
This checks ownership/wiring and negative mutations, not Wurst or Warcraft.
"""
from pathlib import Path
import argparse, re
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources, calls
from VerifyEquipmentAbilityArtifact import require

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = 'towers/TDTowerEvolutionRuntime.wurst'
STATE = 'towers/TDTowerEvolutionState.wurst'

def verify_source(root=ROOT, sources=None):
    sources = read_sources(root) if sources is None else sources
    evaluator = SourceScalarEvaluator(sources)
    state = sources[STATE]
    runtime = sources[RUNTIME]
    require('TDTowerEvolutionLane array tdEvolutionLanes' in runtime and 'TDTowerEvolutionMatch' not in runtime,
            'Evolution authority must be lane-owned')
    require(evaluator.constant('TD_EVOLUTION_QUALIFY_WAVE') == 24, 'Qualification wave must be24')
    require('private boolean qualified = false' in state and 'private boolean spent = false' in state,
            'Qualified and spent need separate private state')
    require('not eligible or not resolved or wave != TD_EVOLUTION_QUALIFY_WAVE' in state,
            'Qualification bypasses real eligible wave24 settlement')
    require('not qualified or spent or working or evolved or not eligible or level != 6' in state,
            'Claim admission changed')
    require(runtime.count('.tryClaim(') == 1, 'Only the confirmation transaction may claim')
    for name in ('tdEvolutionRefresh', 'tdEvolutionRecordKill'):
        body = evaluator.body(name)
        require('tryClaim' not in body and 'tdEvolutionApplyChosenBranch' not in body,
                'Refresh/kills cannot automatically evolve')
    credit = evaluator.body('tdEvolutionCreditWave')
    require('tdIsWaveResolved(lane, wave)' in credit and 'tdEvolutionLaneCanChoose(lane)' in credit and
            'tdGetGlobalWave' not in credit and 'tdGetResolvedWave' not in credit,
            'Credit must use its original formally settled lane/wave')
    eligibility = evaluator.body('tdEvolutionLaneCanChoose')
    require('tdPetLaneCanManage(lane)' in eligibility and 'not tdIsLaneFinished(lane)' in eligibility,
            'Closed/left lane may choose')
    completion = evaluator.body('tdHandleWaveFinished')
    require(completion.index('tdMarkWaveResolved(playerId, wave)') < completion.index('tdEvolutionCreditWave(playerId, wave)'),
            'Evolution credited before formal settlement')
    require(calls(completion, 'tdEvolutionCreditWave') == [['playerId', 'wave']], 'Settlement evolution wiring changed')
    cancel = evaluator.body('tdEvolutionCancel')
    require('ticket.nonce != nonce' in cancel, 'Cancellation lost nonce guard')
    request = evaluator.body('tdEvolutionRequest')
    for fragment in ('tdEvolutionTowerCanChoose(tower, lane)', 'ticket.tower = tower', 'ticket.record = record',
                     'ticket.identity = record.identity', 'ticket.rawcode = GetUnitTypeId(tower)',
                     'ticket.branch = tdTowerBranchForUnitTypeId(ticket.rawcode)',
                     'ticket.workGeneration = record.workGeneration', 'ticket.epoch = tdFlowEpoch()',
                     'ticket.nonce = tdEvolutionNonce'):
        require(fragment in request, 'Ticket missing snapshot: ' + fragment)
    confirm = evaluator.body('tdEvolutionConfirm')
    for fragment in ('GetPlayerId(actor) != lane', 'ticket.nonce != nonce', 'ticket.epoch != tdFlowEpoch()',
                     'not tdEvolutionTowerCanChoose(tower, lane)', 'castTo TDEvolutionTower) != record',
                     'record.tower != tower', 'record.identity != ticket.identity',
                     'record.workGeneration != ticket.workGeneration', 'GetUnitTypeId(tower) != ticket.rawcode',
                     'tdTowerBranchForUnitTypeId(GetUnitTypeId(tower)) != ticket.branch'):
        require(fragment in confirm, 'Confirmation lost guard: ' + fragment)
    ordered = ('tdEvolutionTickets[lane] = null', '.tryClaim(', 'record.evolved = true',
               'destroy ticket', 'tdEvolutionApplyChosenBranch(record)')
    # The first destroy is the rejected claim's cleanup; successful writes still
    # precede both the successful UI destruction and ability/equipment application.
    require(confirm.index(ordered[0]) < confirm.index(ordered[1]) < confirm.index(ordered[2]) <
            confirm.rindex(ordered[3]) < confirm.index(ordered[4]), 'Claim/evolved writes must precede native effects')
    require(not any(x in confirm for x in ('doAfter(', 'doPeriodically(', 'sleep(', 'GetLocalPlayer(')),
            'Confirmation transaction must stay synchronous')
    refresh = evaluator.body('tdEvolutionRefresh')
    for fragment in ('removeAbility(TD_TOWER_EVOLUTION_STATUS_ABILITY_ID)',
                     'addPermanentAbility(TD_TOWER_EVOLUTION_CHOOSE_ABILITY_ID, 1)',
                     'removeAbility(TD_TOWER_EVOLUTION_CHOOSE_ABILITY_ID)',
                     'addPermanentAbility(TD_TOWER_EVOLUTION_STATUS_ABILITY_ID, 1)'):
        require(fragment in refresh, 'Chooser/status card exclusivity lost')
    require('for other' not in refresh and 'tdEvolutionRefreshLane' not in refresh,
            'Refresh cannot recursively scan other towers')
    require(not any(x in runtime for x in ('enumUnitsInRect', 'GetWorldBounds', 'GroupEnumUnits', 'GetLocalPlayer')),
            'Evolution cannot add a world scan or local state mutation')
    for name, fragment in [('tdEvolutionWorkStarted', 'tdEvolutionCancelTower(tower)'),
                           ('tdEvolutionOwnershipChanged', 'tdEvolutionCancelTower(tower)'),
                           ('tdEvolutionForgetTower', 'tdEvolutionCancelTower(tower)'),
                           ('tdEvolutionClearLaneEffects', 'tdEvolutionCancelLane(lane)'),
                           ('tdEvolutionShutdown', 'tdEvolutionCancelLane(lane)')]:
        require(fragment in evaluator.body(name), 'Lifecycle does not invalidate preview: ' + name)
    reset = evaluator.body('tdStartGame')
    require(reset.index('tdEvolutionShutdown()') < reset.index('tdResetState()') <
            reset.index('tdEvolutionResetForNewMatch()'), 'New match reset order changed')
    for owner, source in sources.items():
        for name in ('tdEvolutionIdentity', 'tdEvolutionWorkGeneration', 'tdEvolutionNonce'):
            zero_writes = re.findall(r'\b' + name + r'\s*=\s*0', source)
            require(len(zero_writes) == (1 if owner == RUNTIME else 0),
                    'Evolution identities/nonces may initialize once but cannot reset')
    # A109 remains reserved even after the wage batch deletes its declaration.
    require(evaluator.constant('TD_TOWER_EVOLUTION_CHOOSE_ABILITY_ID') != int.from_bytes(b'A109', 'big'),
            'Evolution cannot reuse retired wage rawcode')
    objects = evaluator.body('tdGenerateTowerAbilities')
    chooser = objects.split('new ChannelAbilityPreset(TD_TOWER_EVOLUTION_CHOOSE_ABILITY_ID', 1)[1].split('new ChannelAbilityPreset', 1)[0]
    require('..presetHotkey("R")' in chooser and '..presetButtonPosNormal(3, 2)' in chooser,
            'Evolution chooser command must preserve combat hotkeys/card')
    setup = evaluator.body('tdSetupDialogTrigger')
    require(['TD_TOWER_EVOLUTION_CHOOSE_ABILITY_ID', 'function tdHandleTowerEvolutionCast'] in calls(setup, 'registerSpellEffectEvent'),
            'Actual tower chooser spell is not wired')
    require('EVENT_PLAYER_UNIT_CHANGE_OWNER' in setup and 'function tdHandleTowerOwnershipChanged' in setup,
            'Ownership change is not wired')
    require('tdEvolutionSelectionChanged(GetTriggerPlayer(), tower)' in evaluator.body('tdHandleTowerSelected'),
            'New tower selection does not invalidate old preview')
    require('tdEvolutionDeselected(GetTriggerPlayer(), tower)' in evaluator.body('tdHandleTowerDeselected') and
            'tdEvolutionTickets[lane].tower == deselected' in evaluator.body('tdEvolutionDeselected'),
            'Deselection must cancel only its exact tower preview')
    return {'qualified_wave': 24, 'authority': 'four independent lane states',
            'ticket_guards': 10, 'world_scans': 0, 'automatic_claims': 0}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, default=ROOT)
    args = p.parse_args()
    print('PASS SOURCE:', verify_source(args.source_root))
    print('NOT EXECUTED: Wurst compilation, packed JASS or Warcraft engine.')

if __name__ == '__main__': main()
