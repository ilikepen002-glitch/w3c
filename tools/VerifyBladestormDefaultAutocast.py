#!/usr/bin/env python3
"""Replay packed upgrade/autocast/CDR code with explicit engine/side-system boundaries.
Native order execution records the order and synchronously dispatches the real
choice listener; it does not prove Warcraft UI or engine timing.
"""
import sys
from pathlib import Path
from VerifyLocalCombatHotpathArtifact import CountedRuntime
from VerifyBloodlustAutocastArtifact import validate_compiled_lifecycle
from VerifyEquipmentAbilityArtifact import require
from GenerateTowerTerrainMask import Mpq
from VerifyTowerUpgradeArtifact import rawcode

class Runtime(CountedRuntime):
    def native(self, name, args):
        if name == 'IssueImmediateOrderById':
            self.stop_orders.append(tuple(args))
            old = self.event_target, self.issued_order
            self.event_target, self.issued_order = args
            self.invoke('tdHandleBloodlustAutocastOrder')
            self.event_target, self.issued_order = old
            return True, True
        # Independent upgrade presentation/equipment boundaries. The actual
        # lifecycle entry, busy state, initialization and CDR restore run below.
        if name in ('tdTargetPriorityTrackTower', 'tdTargetPriorityWorkFinished',
                    'tdDarkTideForgetTower', 'tdTargetPriorityWorkStarted',
                    'tdAuraSetProviderCandidate', 'tdCombatVisualSuspendGear',
                    'tdEvolutionWorkStarted', 'tdPetHeroTowerInvalidated',
                    'tdCombatVisualResumeGear', 'tdEvolutionWorkFinished',
                    'tdDamageTrackTower', 'tdApplyTowerPersistentState',
                    'tdEvolutionRefresh', 'tdRefreshTowerEquipmentBonuses',
                    'tdRefreshTowerEquipmentBonuses_1', 'tdRefreshTowerRangeIndicatorsForTower',
                    'tdAlignPlayerTowerPopulation', 'tdForgetEquipmentSpecial'):
            return True, None
        return super().native(name, args)

def run(script):
    validate_compiled_lifecycle(script)
    r = Runtime(script)
    r.invoke('init_TDActiveCooldownRuntime')
    r.invoke('init_TDTowerBloodlustAutocast')
    r.units[101]['type'] = rawcode('uO15')
    ability = rawcode('A132')
    r.units[101]['abilities'] = {}
    r.event_target = 101
    r.stop_orders.clear()
    r.invoke('tdHandleTowerUpgradeStarted')
    r.invoke('tdInitializeBloodlustAutocast', 101)
    require(not r.stop_orders, 'Missing/busy ability initialized early')
    r.units[101]['type'] = rawcode('uO6B')
    r.units[101]['abilities'] = {ability: 1}
    r.invoke('tdHandleTowerUpgradeFinished')
    require((101, 852076) in r.stop_orders, 'Upgrade must default A132 ON')
    r.issued_order = 852077
    r.invoke('tdHandleBloodlustAutocastOrder')
    r.stop_orders.clear()
    for reduction in (.18, .40, 0., .18):
        r.invoke('tdRefreshNativeActiveCooldowns', 101, reduction)
    require(r.stop_orders and all(order == 852077 for _, order in r.stop_orders), 'CDR refresh must preserve manual OFF')
    r.spell_ability = ability
    r.invoke('tdNativeActiveSpellCast')
    r.stop_orders.clear()
    r.invoke('tdRefreshNativeActiveCooldowns', 101, .40)
    require(not r.stop_orders, 'Active cooldown must defer refresh')
    r.now += 20.
    r.invoke('tdRefreshNativeActiveCooldowns', 101, .40)
    require(r.stop_orders == [(101, 852077)], 'Delayed refresh must restore latest manual OFF')
    r.stop_orders.clear()
    r.invoke('tdHandleTowerUpgradeFinished')
    require(r.stop_orders == [(101, 852077)], 'Repeated upgrade completion reset manual OFF')
    r.stop_orders.clear()
    r.invoke('tdHandleTowerUpgradeStarted')
    r.invoke('tdHandleTowerUpgradeCancelled')
    r.invoke('tdHandleTowerUpgradeStarted')
    r.drain_zero()
    require(not r.stop_orders, 'Stale cancellation must not initialize while new upgrade is busy')
    r.invoke('tdHandleTowerUpgradeCancelled')
    r.drain_zero()
    require(r.stop_orders == [(101, 852077)], 'Matching cancellation must restore manual OFF')
    r.invoke('tdForgetBloodlustAutocast', 101)
    r.stop_orders.clear()
    r.invoke('tdHandleTowerUpgradeFinished')
    require(r.stop_orders == [(101, 852076)], 'Retired/reused handle must get default ON')
    print('PASS packed upgrade/default ON, manual OFF, CDR restore, repeated completion, stale/matching cancellation, retirement')

if __name__ == '__main__':
    run(Mpq(Path(sys.argv[1]).read_bytes()).extract('war3map.j').decode())
