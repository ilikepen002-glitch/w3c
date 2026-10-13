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
        super().__init__(script)
        self.globals['ALLIANCE_PASSIVE'] = 'passive'

    def native(self, name, args):
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
    refresh_callback = runtime.scheduled[-1][1]
    scheduled = len(runtime.scheduled)
    for _ in range(5):
        runtime.invoke('tdRefreshHud')
    require(len(runtime.scheduled) == scheduled, 'Repeated requests must coalesce')
    runtime.run_timer(wave_callback)
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
    return 'PASS: real pet UI setup, startup/camera separation, first-wave epoch, HUD coalescing, latest-state refresh and watchdog lifecycle'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('map')
    parser.add_argument('--current-pet-ui', action='store_true',
                        help='Compatibility flag; current shared-listener contract is always required')
    args = parser.parse_args()
    print(verify(Mpq(Path(args.map).read_bytes()).extract('war3map.j').decode(),
                 expected_pet_registrations=2))
