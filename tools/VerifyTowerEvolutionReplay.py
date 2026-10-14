#!/usr/bin/env python3
"""Replay actual packed lane-evolution settlement, native event bridges and claim.
Only engine unit/dialog/effect/collection boundaries are modeled. Production
eligibility, snapshot checks, spending, branch application and equipment run.
No Warcraft dialog rendering, visual/FPS or balance claim.
"""
import argparse, hashlib, json, re
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyPetRebindingArtifact import RebindingRuntime
from VerifyTowerUpgradeArtifact import EXPECTED_TOWERS, EVOLUTION_REPLACEMENTS, rawcode, function_body
from VerifyEquipmentAbilityArtifact import require

PREFIX = 'TDTowerEvolutionRuntime_'

class EvolutionRuntime(RebindingRuntime):
    def __init__(self, script):
        self.dialog_serial = 120000
        self.trigger_serial = 130000
        self.dialogs, self.live_triggers = {}, set()
        self.hashtable_serial, self.hash_integers = 140000, {}
        self.actor, self.clicked_dialog, self.clicked_button = 0, None, None
        self.spell = 0
        self.equipment_refreshes = []
        super().__init__(script)
        for lane in range(4): self.invoke('tdPetInitializeLane', lane)
        self.equipment_refreshes.clear()
        for name in ('init_Orders', 'init_TDTowerRuntime', 'init_TDActiveCooldownRuntime', 'init_TDTowerBloodlustAutocast', 'init_TDInventoryRuntime'):
            if name in self.functions: self.invoke(name)
        self.globals.update(PLAYER_STATE_RESOURCE_FOOD_CAP='foodCap', PLAYER_STATE_RESOURCE_FOOD_USED='foodUsed')

    def native(self, name, args):
        # The inherited combat harness has a historical unevolved-tower oracle.
        # Execute this map's actual authority, never stub its evolved/claim state.
        if name == 'tdTowerIsEvolved': return False, None
        if name == 'StringLength': return True, len(args[0])
        if name in ('tdShowTowerRangeIndicatorForPlayer', 'tdClearTowerRangeIndicator'):
            return True, None  # Independent range-image rendering boundary only.
        if name == 'InitHashtable':
            self.hashtable_serial += 1; return True, self.hashtable_serial
        if name in ('LoadInteger', 'HaveSavedInteger'):
            key = tuple(args[:3])
            return True, key in self.hash_integers if name == 'HaveSavedInteger' else self.hash_integers.get(key, 0)
        if name == 'SaveInteger': self.hash_integers[tuple(args[:3])] = args[3]; return True, True
        if name == 'FlushChildHashtable':
            self.hash_integers = {key: value for key, value in self.hash_integers.items() if key[:2] != tuple(args[:2])}
            return True, None
        if name == 'UnitRemoveItem':
            self.units[args[0]]['inventory'] = {slot: item for slot, item in self.units[args[0]]['inventory'].items() if item != args[1]}
            return True, None
        if name == 'SetUnitInvulnerable': self.units[args[0]]['invulnerable'] = args[1]; return True, None
        if name == 'CreateTrigger':
            self.trigger_serial += 1
            self.live_triggers.add(self.trigger_serial)
            return True, self.trigger_serial
        if name == 'DestroyTrigger':
            require(args[0] in self.live_triggers, 'Unknown/double-destroyed evolution dialog trigger')
            self.live_triggers.remove(args[0]); return True, None
        if name == 'DialogCreate':
            self.dialog_serial += 1
            self.dialogs[self.dialog_serial] = {'buttons': [], 'visible': {}, 'live': True, 'message': ''}
            return True, self.dialog_serial
        if name in ('DialogAddButton', 'DialogAddQuitButton'):
            require(self.dialogs[args[0]]['live'], 'Adding button to retired dialog')
            self.dialog_serial += 1
            self.dialogs[args[0]]['buttons'].append(self.dialog_serial)
            return True, self.dialog_serial
        if name == 'DialogSetMessage':
            self.dialogs[args[0]]['message'] = args[1]; return True, None
        if name == 'DialogDisplay':
            require(self.dialogs[args[1]]['live'], 'Displaying retired dialog')
            self.dialogs[args[1]]['visible'][args[0]] = args[2]; return True, None
        if name == 'DialogClear':
            require(self.dialogs[args[0]]['live'], 'Clearing retired dialog'); return True, None
        if name == 'DialogDestroy':
            require(self.dialogs[args[0]]['live'], 'Double dialog destruction')
            self.dialogs[args[0]]['live'] = False; return True, None
        if name == 'TriggerRegisterDialogEvent': return True, None
        if name == 'GetTriggerPlayer': return True, self.actor
        if name == 'GetSpellAbilityId': return True, self.spell
        if name == 'GetClickedDialog': return True, self.clicked_dialog
        if name == 'GetClickedButton': return True, self.clicked_button
        if name in ('KillUnit', 'unit_kill'):
            self.units[args[0]]['alive'] = False; return True, None
        return super().native(name, args)

    def execute_call(self, name, args):
        if name == 'tdRefreshTowerEquipmentBonuses': self.equipment_refreshes.append(args[0])
        return super().execute_call(name, args)

    def make_tower(self, handle, lane=0, type_id='uA6A'):
        self.tower(handle, lane, type_id)
        self.units[handle]['abilities'] = {rawcode(code): 1 for code in EXPECTED_TOWERS[type_id]}
        self.invoke('tdEvolutionRefresh', handle)
        return handle

    def start_boss(self, lane):
        if not self.invoke('tdFlowIsBossActive'):
            require(self.invoke('tdFlowPrepareBoss', 24), 'Boss preparation fixture failed')
            require(self.invoke('tdFlowStartBoss', 24), 'Boss start fixture failed')
        require(self.invoke('tdFlowActivateBoss', lane, 24, self.now), 'Boss lane fixture failed')

    def settle(self, lane=0, result=2):
        self.start_boss(lane)
        require(self.invoke('tdFlowClaimBossResult', lane, 24, result), 'Boss result fixture failed')
        self.invoke('tdHandleWaveFinished', lane, 24)

    def fail_boss(self, result, survive=True):
        self.start_boss(0)
        enemy = self.call('CreateUnit', [4, rawcode('uB24'), 0., 0., 0.])
        self.globals['TDGame_tdBossUnits'][0] = enemy
        if not survive: self.invoke('tdLoseLife', 0, self.invoke('tdGetLives', 0) - 3)
        self.invoke('tdSettleBossFailure', enemy, 0, 24, result)

    def ticket(self, lane=0): return self.globals[PREFIX + 'tdEvolutionTickets'][lane]
    def ticket_field(self, field, ticket): return self.globals['TDEvolutionTicket_' + field][ticket]
    def request(self, tower, lane=0):
        self.actor, self.event_target = lane, tower
        self.invoke('tdHandleTowerEvolutionCast')
        return self.ticket(lane)
    def click(self, ticket, confirm=True, actor=0):
        self.actor = actor
        self.clicked_dialog = self.ticket_field('preview', ticket)
        self.clicked_button = self.ticket_field('confirm' if confirm else 'cancel', ticket)
        self.invoke('tdEvolutionHandleButton')
    def old_click(self, dialog, button, actor=0):
        self.actor, self.clicked_dialog, self.clicked_button = actor, dialog, button
        self.invoke('tdEvolutionHandleButton')
    def snapshot_ticket(self, ticket):
        return tuple(self.ticket_field(field, ticket) for field in ('nonce', 'preview', 'confirm', 'cancel'))
    def is_spent(self, lane=0):
        return self.invoke('dispatch_TDTowerEvolutionLane_TDTowerEvolutionLane_isSpent', self.invoke('tdEvolutionLane', lane))
    def qualified(self, lane=0):
        return self.invoke('dispatch_TDTowerEvolutionLane_TDTowerEvolutionLane_isQualified', self.invoke('tdEvolutionLane', lane))


def verify_settlement(script):
    r = EvolutionRuntime(script)
    for lane in range(4):
        tower = r.make_tower(7000 + lane, lane)
        r.invoke('tdSetGlobalWave', 24)
        require(not r.request(tower, lane) and not r.qualified(lane), 'Global wave incorrectly unlocks lane')
        r.settle(lane, (2, 3, 4, 2)[lane])
        require(r.qualified(lane), 'Real surviving Boss24 result failed to qualify lane')
        ticket = r.request(tower, lane)
        require(ticket, 'Qualified own finished tier6 tower cannot request')
        r.click(ticket, actor=lane)
        require(r.is_spent(lane) and r.invoke('tdTowerIsEvolved', tower), 'Confirmed lane evolution failed')
        r.invoke('tdHandleWaveFinished', lane, 24)
        require(r.is_spent(lane), 'Duplicate wave24 reset spent')
    for mode in ('inactive', 'defeated', 'finished', 'left', 'gameover'):
        r = EvolutionRuntime(script)
        if mode == 'left': r.invoke('tdPetMarkPlayerLeft', 0)
        elif mode == 'gameover': r.invoke('tdSetGameOver', True)
        else: r.invoke({'inactive':'tdSetLaneActive','defeated':'tdSetLaneDefeated','finished':'tdSetLaneFinished'}[mode], 0, mode != 'inactive')
        r.settle(0)
        require(not r.qualified(), 'Closed lane qualified: ' + mode)
    for result in (3, 4):
        for survive in (False, True):
            r = EvolutionRuntime(script); r.fail_boss(result, survive)
            require(r.qualified() == survive, 'Actual Boss failure path qualified eliminated lane or denied survivor')
    return {'four_independent_lanes': True, 'real_boss_results': ['kill', 'surviving_leak', 'surviving_timeout'],
            'actual_boss_failure_routes': 4, 'closed_lanes': 5}


def verify_confirmations(script):
    r = EvolutionRuntime(script); r.settle()
    a, b = r.make_tower(7100), r.make_tower(7101)
    require(r.qualified() and not r.is_spent(), 'Qualification without a tower was not retained')
    first = r.request(a); old_nonce, old_dialog, old_confirm, old_cancel = r.snapshot_ticket(first)
    second = r.request(b); second_nonce = r.ticket_field('nonce', second)
    r.old_click(old_dialog, old_cancel)
    r.old_click(old_dialog, old_confirm)
    require(r.ticket() == second and not r.is_spent(), 'Old A dialog altered B or spent qualification')
    require(not r.invoke('tdEvolutionConfirm', 0, 0, old_nonce), 'Old nonce confirmed newer tower preview')
    require(not r.invoke('tdEvolutionCancel', 0, old_nonce), 'Old nonce cancelled new preview')
    require(not r.invoke('tdEvolutionConfirm', 0, 1, second_nonce), 'Teammate confirmed owner preview')
    r.actor, r.event_target = 0, a
    r.invoke('tdHandleTowerDeselected')
    require(r.ticket() == second, 'Old A deselection cancelled new B')
    r.event_target = b; r.invoke('tdHandleTowerDeselected')
    require(not r.ticket() and not r.is_spent(), 'Standalone B deselection retained its preview')
    current = r.request(a); nonce, dialog, confirm, cancel = r.snapshot_ticket(current)
    r.click(current, confirm=False)
    require(not r.ticket() and not r.is_spent(), 'Cancel spent qualification')
    require(not r.invoke('tdEvolutionConfirm', 0, 0, nonce), 'Cancelled nonce confirmed')
    current = r.request(b); nonce, dialog, confirm, cancel = r.snapshot_ticket(current)
    r.click(current)
    require(r.is_spent() and not r.invoke('tdEvolutionConfirm', 0, 0, nonce), 'Duplicate confirmation succeeded')
    r.old_click(dialog, confirm)
    require(not r.invoke('tdTowerIsEvolved', a), 'Second tower evolved in same lane')
    r.invoke('tdEvolutionForgetTower', b)
    require(r.is_spent() and not r.request(a), 'Tower death/sale refunded lane qualification')
    return {'old_dialogs': 2, 'actor_nonce_checks': 3, 'cancel_duplicate_no_refund': True, 'native_deselection_bridges': 2}


def verify_stale_lifecycle(script):
    cases = ('dead', 'sold', 'removed', 'owner', 'owner-back', 'work', 'cancel-work', 'rawcode', 'branch',
             'record-reused', 'selection', 'left', 'finished', 'defeated', 'gameover', 'epoch', 'new-match')
    for mode in cases:
        r = EvolutionRuntime(script); r.settle(); tower = r.make_tower(7200)
        ticket = r.request(tower); nonce, dialog, button, cancel = r.snapshot_ticket(ticket)
        if mode == 'dead':
            r.units[tower]['alive'] = False; r.event_target = tower; r.invoke('tdHandleTowerDeath')
        elif mode == 'sold':
            r.event_target = tower; r.invoke('tdHandleTowerSellCast')
        elif mode == 'removed':
            r.invoke('tdEvolutionForgetTower', tower)
            r.units[tower].update(type=0, alive=False)
        elif mode in ('owner', 'owner-back'):
            r.units[tower]['owner'] = 1; r.event_target = tower; r.invoke('tdHandleTowerOwnershipChanged')
            if mode == 'owner-back':
                r.units[tower]['owner'] = 0; r.invoke('tdHandleTowerOwnershipChanged')
        elif mode in ('work', 'cancel-work'):
            r.event_target = tower; r.invoke('tdHandleTowerUpgradeStarted')
            if mode == 'cancel-work':
                r.invoke('tdHandleTowerUpgradeCancelled')
                r.invoke('tdHandleTowerUpgradeStarted')
                r.drain_zero()
                require(not r.request(tower), 'Old zero-delay upgrade cancel completed newer construction')
                r.invoke('tdHandleTowerUpgradeCancelled'); r.drain_zero()
                require(r.request(tower), 'Matching zero-delay cancel did not restore finished terminal tower')
        elif mode in ('rawcode', 'branch'): r.units[tower]['type'] = rawcode('uA15' if mode == 'rawcode' else 'uA6B')
        elif mode == 'record-reused':
            r.invoke('tdEvolutionForgetTower', tower); r.invoke('tdEvolutionRefresh', tower)
        elif mode == 'selection':
            r.actor, r.event_target = 0, r.make_tower(7201); r.invoke('tdHandleTowerSelected')
        elif mode == 'left': r.invoke('tdHandleLanePlayerLeft', 0)
        elif mode in ('finished', 'defeated'): r.invoke('tdSetLaneFinished' if mode == 'finished' else 'tdSetLaneDefeated', 0, True)
        elif mode == 'gameover': r.invoke('tdSetGameOver', True)
        elif mode == 'epoch': r.invoke('tdResetWaveFlowState')
        elif mode == 'new-match':
            r.initialize_match()
            for lane in range(4): r.invoke('tdPetInitializeLane', lane)
            r.settle()
            fresh = r.request(tower)
            require(fresh and r.ticket_field('nonce', fresh) != nonce, 'New match reused prior confirmation nonce')
        require(not r.invoke('tdEvolutionConfirm', 0, 0, nonce), 'Stale preview confirmed: ' + mode)
        r.old_click(dialog, button)
        require(not r.is_spent(), 'Stale click spent new/closed lane: ' + mode)
        if mode == 'new-match':
            require(r.ticket() == fresh, 'Old match click cancelled new match preview')
            r.click(fresh)
            require(r.is_spent(), 'Fresh match preview could not confirm after old callback rejection')
    # No state mutation is allowed from any count, including the old threshold.
    r = EvolutionRuntime(script); tower = r.make_tower(7250)
    for kills in range(935): r.invoke('tdEvolutionRecordKill', tower, 0)
    require(not r.invoke('tdTowerIsEvolved', tower) and not r.is_spent(), 'Kills automatically evolved')
    r.settle(); ticket = r.request(tower); r.click(ticket)
    require(r.invoke('tdTowerIsEvolved', tower), 'Kills prevented explicit qualified evolution')
    return {'stale_lifecycle_cases': len(cases), 'kill_only_cases': 935}


def verify_branches(script):
    for uid in EVOLUTION_REPLACEMENTS:
        r = EvolutionRuntime(script); tower = r.make_tower(7300, type_id=uid)
        for slot, code in enumerate(('iW09', 'iW01', 'iW03')):
            item = 150000 + slot
            r.inventory_items[item] = rawcode(code)
            r.units[tower]['inventory'][slot] = item
        r.invoke('tdRefreshTowerEquipmentBonuses_1', tower)
        pet = r.record(host=tower, ready=123.)
        generation = r.field('generation', pet)
        before = dict(r.units[tower]['abilities'])
        if uid in ('uO6A', 'uO6B'):
            r.event_target = tower
            r.spell = rawcode('A131' if uid == 'uO6A' else 'A132')
            r.invoke('tdNativeActiveSpellCast')
            require(any(deadline > r.now for deadline in r.globals['TDActiveNativeCooldownState_readyAt'].values()),
                    uid + ': actual native cast did not establish an unexpired cooldown')
        native_deadlines = dict(r.globals['TDActiveNativeCooldownState_readyAt'])
        r.settle(); ticket = r.request(tower); r.click(ticket)
        require(r.invoke('tdTowerIsEvolved', tower), uid + ': actual evolved state not set')
        after = r.units[tower]['abilities']
        for old, new in EVOLUTION_REPLACEMENTS[uid].items():
            require(rawcode(old) not in after and after.get(rawcode(new)) == before[rawcode(old)], uid + ': selected replacement wrong')
        for code in EXPECTED_TOWERS[uid]:
            if code not in EVOLUTION_REPLACEMENTS[uid]: require(rawcode(code) in after, uid + ': nonselected skill lost')
        require(dict(r.globals['TDActiveNativeCooldownState_readyAt']) == native_deadlines, uid + ': existing native active cooldown deadline changed')
        require(r.units[tower]['inventory'] == {slot: 150000 + slot for slot in range(3)}, uid + ': gear ownership changed')
        for code in ('A128', 'A129'):
            require(after.get(rawcode(code)) == before.get(rawcode(code)), uid + ': equipment scalar reapplied or lost')
        require(r.field('host', pet) == tower and r.field('generation', pet) == generation and r.field('readyAt', pet) == 123.,
                uid + ': evolution changed pet binding/generation/cooldown')
        wings = [event for event in r.visual_events if event['native'] == 'AddSpecialEffectTarget' and 'TDEvolutionWings' in event['args'][0]]
        require(len(wings) == 1 and tower in r.equipment_refreshes, uid + ': wings/equipment application missing')
        frozen = dict(after)
        for _ in range(3): r.invoke('tdEvolutionRefresh', tower)
        require(after == frozen, uid + ': refresh repeated effect/changed abilities')
        r.invoke('tdEvolutionForgetTower', tower)
        r.invoke('tdEvolutionForgetTower', tower)
        require(r.is_spent(), uid + ': cleanup refunded spent')
    return {'ten_terminal_branches': 10, 'pet_binding_readyAt_preserved': True, 'single_wings_and_no_repeat': True}


def verify_mutation(script):
    body = function_body(script, 'tdEvolutionConfirm')
    # Mutate the actual packed nonce guard, retaining all native production paths.
    changed, count = re.subn(r'TDEvolutionTicket_nonce\[\w+\] != nonce(?:_\d+)?', 'false', body)
    require(count == 1, 'Packed nonce mutation target missing')
    mutant = script.replace(body, changed, 1)
    r = EvolutionRuntime(mutant); r.settle(); a, b = r.make_tower(7400), r.make_tower(7401)
    first = r.request(a); old_nonce = r.ticket_field('nonce', first)
    r.request(b)
    require(r.invoke('tdEvolutionConfirm', 0, 0, old_nonce) and r.is_spent(), 'Nonce bypass mutant was not exposed')
    # The positive stale-confirmation oracle must reject this exact mutant.
    caught = False
    try: verify_confirmations(mutant)
    except ValueError: caught = True
    require(caught, 'Lifecycle replay did not catch packed confirmation bypass')
    return {'packed_nonce_bypass_detected': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args(); data = args.map.read_bytes()
    script = Mpq(data).extract('war3map.j').decode('utf-8')
    result = {'sha256': hashlib.sha256(data).hexdigest(), 'settlement': verify_settlement(script),
              'confirmations': verify_confirmations(script), 'lifecycle': verify_stale_lifecycle(script),
              'branches': verify_branches(script), 'mutation': verify_mutation(script),
              'not_tested': 'Warcraft rendering, Dialog input, native aura projection, FPS or balance'}
    if args.output: args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == '__main__': main()
