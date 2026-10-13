#!/usr/bin/env python3
"""Replay packaged startup/HUD scheduling; unrelated systems are explicit stubs.

Checks thread separation, not Warcraft engine operation budgets or live rendering.
"""
import argparse
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyPetStartupArtifact import PetStartupRuntime
from VerifyEquipmentAbilityArtifact import require
from VerifyDamageRankingJass import functions


class StartupRuntime(PetStartupRuntime):
    def __init__(self, script):
        self.events = []
        self.dialogs = {}
        self.dialog_events = {}
        self.dialog_actions = {}
        self.clicked_dialog = self.clicked_button = None
        self.click_player = 0
        super().__init__(script)
        self.invoke('init_TDDifficultyDialog')
        # Run packaged asset initialization rather than inventing music paths.
        if 'init_Sounds' in self.functions:
            self.invoke('init_Sounds')
        self.globals['ALLIANCE_PASSIVE'] = 'passive'

    def native(self, name, args):
        if name in {'SetMusicVolume', 'SetMapMusic', 'PlayMusic'}:
            # Engine audio is a recording boundary; execute the real map setup.
            self.events.append((name, *args))
            return True, None
        if name in {'DialogCreate', 'DialogAddButton'}:
            self.trigger_serial += 1
            handle = self.trigger_serial
            if name == 'DialogCreate':
                self.dialogs[handle] = {'buttons': {}, 'visible': set(), 'destroyed': False}
            else:
                self.dialogs[args[0]]['buttons'][handle] = args[1]
            return True, handle
        if name == 'DialogSetMessage':
            self.dialogs[args[0]]['message'] = args[1]
            return True, None
        if name == 'DialogDisplay':
            visible = self.dialogs[args[1]]['visible']
            (visible.add if args[2] else visible.discard)(args[0])
            return True, None
        if name == 'DialogClear':
            self.dialogs[args[0]]['buttons'].clear()
            return True, None
        if name == 'DialogDestroy':
            self.dialogs[args[0]]['destroyed'] = True
            return True, None
        if name == 'TriggerRegisterDialogEvent':
            self.dialog_events[args[1]] = args[0]
            return True, None
        if name == 'TriggerAddAction' and args[0] in self.dialog_events.values():
            self.dialog_actions[args[0]] = args[1]
            return True, None
        if name == 'DestroyTrigger':
            self.dialog_actions.pop(args[0], None)
            return True, None
        if name in {'GetClickedDialog', 'GetClickedButton', 'GetTriggerPlayer'}:
            return True, {'GetClickedDialog': self.clicked_dialog, 'GetClickedButton': self.clicked_button,
                          'GetTriggerPlayer': self.click_player}[name]
        if name == 'DisplayTimedTextToPlayer':
            self.events.append(('text', args[4]))
            return True, None
        if name == 'tdSetupPets':
            # Keep the previously missed, expensive UI initialization real.
            # Combat/wild runtime hooks remain unrelated native fixture boundaries.
            self.invoke('tdPetSetupUI')
            return True, None
        if name == 'tdRefreshHud':
            return False, None
        if name == 'tdRefreshStatusBoard':
            require(not self.globals.get('TDHud_tdHudRefreshPending', True), 'Pending must clear before rendering')
            self.events.append(('render', self.globals['TDState_tdGlobalWave']))
            return True, None
        if name == 'tdSetupHud':
            self.events.append(('setup',))
            self.globals['TDHud_tdStatusBoard'] = 99
            self.invoke('tdRequestHudRefresh')
            return True, None
        if name in {'tdApplyStartingCamera', 'tdStartCameraDistanceClamp', 'tdLiftStartingCameraAgain',
                    'tdFocusStartingCameraOnFarmers'}:
            self.events.append((name,))
            return True, None
        if name in {'RemoveAllGuardPositions', 'SetPlayerAlliance', 'tdCreatePads', 'tdPetInitializeFarmer',
                    'tdSetupLanePlayerLeaveWatcher', 'tdSetupDamageStatistics',
                    'tdSetupEnemyMechanics', 'tdSetupBuildDialog', 'tdSetupPadSelection',
                    'tdSetupDialogTrigger', 'tdSetupInventoryRuntime', 'tdSetupAuraRuntime', 'tdSetupGroundItemRuntime',
                    'tdSetupLaneRects', 'tdStartLaneWaypointWatcher', 'tdStartEnemyDeathWatcher',
                    'tdStartLeakWatcher', 'tdSetupChatCommands'}:
            return True, None
        return super().native(name, args)


def verify_difficulty_dialog(script):
    r = StartupRuntime(script)
    r.invoke('tdResetState')
    for lane in (1, 3):
        r.invoke('tdSetLaneActive', lane, True)
    r.invoke('tdRefreshDifficultyDialog')
    dialog = r.globals['TDDifficultyDialog_tdDifficultyDialog']
    view = r.dialogs[dialog]
    buttons = list(view['buttons'])
    require(len(buttons) == 4 and view['visible'] == {1}, 'Only the current selector should see four buttons')
    require(list(view['buttons'].values()) == ['普通 · 生命×1', '困难 · 生命×1.3', '噩梦 · 生命×1.7', '传奇 · 生命×2.2'],
            'Buttons must explain the actual health multipliers')
    callback = r.dialog_actions[r.dialog_events[dialog]]
    def click(player, button, source=dialog):
        r.click_player, r.clicked_button, r.clicked_dialog = player, button, source
        r.invoke(callback)
    click(3, buttons[3])
    click(1, -1)
    click(1, buttons[3], -1)
    require(r.invoke('tdGetDifficulty') == 1, 'Unauthorized/unknown/stale dialog clicks changed difficulty')
    for index, button in enumerate(buttons, 1):
        click(1, button)
        require(r.invoke('tdGetDifficulty') == index and not view['visible'], 'Button did not select and dismiss')
    r.invoke('tdRefreshDifficultyDialog')
    require(not view['visible'], 'Unchanged selector should not be prompted again after selection')
    r.invoke('tdSetLaneActive', 1, False)
    r.invoke('tdRefreshDifficultyDialog')
    require(view['visible'] == {3}, 'Departed selector did not transfer the dialog')
    click(1, buttons[0])
    require(r.invoke('tdGetDifficulty') == 4, 'Departed selector changed difficulty')
    click(3, buttons[1])
    require(r.invoke('tdGetDifficulty') == 2, 'Replacement selector could not choose')
    r.invoke('tdStartGlobalWave', 1)
    require(r.invoke('tdIsDifficultyLocked') and view['destroyed'] and not view['visible'], 'First wave left dialog open')
    require(not r.dialog_actions, 'First wave leaked the dialog trigger')
    click(3, buttons[0])
    require(r.invoke('tdGetDifficulty') == 2, 'Late click changed locked difficulty')
    r.invoke('tdResetState')
    r.invoke('tdSetLaneActive', 0, True)
    r.invoke('tdRefreshDifficultyDialog')
    new_dialog = r.globals['TDDifficultyDialog_tdDifficultyDialog']
    require(new_dialog != dialog and r.dialogs[new_dialog]['visible'] == {0}, 'Reset did not show a fresh dialog')
    r.invoke('tdShutdownGameFlow')
    require(r.dialogs[new_dialog]['destroyed'] and not r.dialog_actions, 'Shutdown leaked dialog/trigger')


def verify(script, expected_pet_registrations=2):
    packaged = functions(script)
    setup = packaged['tdSetupHud'][4]
    require('call tdRequestHudRefresh(' in setup and 'call tdRefreshStatusBoard(' not in setup,
            'Actual packaged setup must request, rather than perform, initial rendering')
    periodic = [body[4] for name, body in packaged.items() if name.startswith('call_doPeriodically_TDHud')]
    require(len(periodic) == 1 and 'call tdRequestHudRefresh(' in periodic[0]
            and 'call tdRefreshStatusBoard(' not in periodic[0], 'Actual HUD periodic must request rendering')
    runtime = StartupRuntime(script)
    runtime.invoke('tdResetState')
    runtime.invoke('tdSetLaneActive', 0, True)
    runtime.invoke('tdRefreshHud')
    require(not runtime.scheduled, 'Refresh before board creation should be ignored')
    runtime.invoke('tdFinalizeGameplayBootstrap')
    require(len(runtime.registered) == expected_pet_registrations and runtime.calls['string_indexOf'] == 0,
            'Pet UI startup missed handlers or performed expensive string scans')
    require(len(runtime.scheduled) == 2, 'Startup must register first wave and one deferred HUD setup')
    require(runtime.scheduled[0][0] > 0 and runtime.scheduled[1][0] == 0, 'First wave must register before HUD setup')
    require(('tdFocusStartingCameraOnFarmers',) in runtime.events and ('tdLiftStartingCameraAgain',) in runtime.events,
            'Camera continuation must complete before any HUD work')
    require(not any(event[0] in {'setup', 'render'} for event in runtime.events), 'Startup synchronously performs HUD work')
    wave_callback, setup_callback = runtime.scheduled[0][1], runtime.scheduled[1][1]
    runtime.run_timer(setup_callback)
    opening_dialog = runtime.globals['TDDifficultyDialog_tdDifficultyDialog']
    require(runtime.dialogs[opening_dialog]['visible'] == {0}, 'Deferred startup did not show the selector dialog')
    refresh_callback = runtime.scheduled[-1][1]
    scheduled = len(runtime.scheduled)
    for _ in range(5):
        runtime.invoke('tdRefreshHud')
    require(len(runtime.scheduled) == scheduled, 'Repeated requests must coalesce')
    runtime.run_timer(wave_callback)
    require(runtime.invoke('tdGetDifficulty') == 1 and runtime.dialogs[opening_dialog]['destroyed'],
            'Unanswered dialog must close with default difficulty on first wave')
    require(runtime.globals['TDState_tdGlobalWave'] == 1 and runtime.spawn_requests == [(0, 1)], 'First wave did not advance/spawn')
    require(not any(event[0] == 'render' for event in runtime.events), 'Wave callback synchronously rendered HUD')
    runtime.run_timer(refresh_callback)
    require(runtime.events[-1] == ('render', 1), 'Refresh must read latest state')
    runtime.invoke('tdRefreshHud')
    require(len(runtime.scheduled) == scheduled + 1, 'Completed refresh must allow another request')
    runtime.invoke('tdResetState')
    runtime.run_timer(wave_callback)
    require(runtime.globals['TDState_tdGlobalWave'] == 0, 'Stale first-wave epoch callback advanced new match')
    diagnostics = StartupRuntime(script)
    diagnostics.invoke('tdStartGame')
    old_timer = diagnostics.globals['TDInit_tdStartupWatchdog']
    diagnostics.fire_native_timer(old_timer)
    require(any(event[0] == 'text' and '等待玩家槽位' in event[1] for event in diagnostics.events),
            'Independent watchdog did not report the unfinished stage')
    diagnostics.invoke('tdStartGame')
    current_timer = diagnostics.globals['TDInit_tdStartupWatchdog']
    diagnostics.fire_native_timer(old_timer)
    require(diagnostics.globals['TDInit_tdStartupWatchdog'] == current_timer,
            'Old watchdog affected the new startup')
    diagnostics.invoke('tdSetLaneActive', 0, True)
    diagnostics.invoke('tdFinalizeGameplayBootstrap')
    require(diagnostics.globals['TDInit_tdStartupWatchdog'] is None and diagnostics.timers[current_timer]['destroyed'],
            'Successful startup did not cancel its watchdog')
    verify_difficulty_dialog(script)
    return 'PASS: pet UI/startup/camera, first-wave epoch, HUD/watchdog lifecycle; difficulty buttons, authority, transfer, lock and dialog cleanup (engine natives modeled)'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('map')
    parser.add_argument('--current-pet-ui', action='store_true',
                        help='Compatibility flag; current shared-listener contract is always required')
    args = parser.parse_args()
    print(verify(Mpq(Path(args.map).read_bytes()).extract('war3map.j').decode(),
                 expected_pet_registrations=2))
