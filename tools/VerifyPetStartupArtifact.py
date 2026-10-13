#!/usr/bin/env python3
"""Check packaged pet UI registration and rawcode cost, without engine op claims."""
import argparse
import json
from pathlib import Path

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyTrialReplay import TrialJassRuntime


class PetStartupRuntime(TrialJassRuntime):
    def __init__(self, script):
        super().__init__(script)
        self.registered = []
        self.globals.update(EVENT_PLAYER_UNIT_SELECTED='selected', EVENT_PLAYER_UNIT_DESELECTED='deselected')
        self.invoke('init_ObjectIds')

    def native(self, name, args):
        if name == 'StringLength':
            return True, len(args[0])
        if name == 'registerSpellEffectEvent':
            self.registered.append(args[0])
            return True, None
        if name == 'trigger_registerAnyUnitEvent':
            return True, None
        return super().native(name, args)


def measure(script, current_ui=True):
    runtime = PetStartupRuntime(script)
    runtime.calls.clear()
    runtime.executed_steps = 0
    runtime.invoke('tdPetSetupUI')
    expected = ['Pcol', 'Pdep']
    expected += [f'Pc{a:02X}' if a < 8 else f'Pm{a-8:02X}' for a in range(23 if current_ui else 21)]
    expected += ([f'L{index:03X}' for index in range(490)] if current_ui else [f'Pl{index:02X}' for index in range(130)])
    require(runtime.registered == [int.from_bytes(value.encode('ascii'), 'big') for value in expected],
            f'Actual UI setup changed or missed its {len(expected)} spell registrations')
    require(runtime.globals['TDPetUI_ready'], 'UI setup did not set its guard')
    require(len(runtime.periodics) == 1, 'UI setup did not finish registering its watcher')
    steps = runtime.executed_steps
    runtime.invoke('tdPetSetupUI')
    require(len(runtime.registered) == len(expected) and len(runtime.periodics) == 1, 'Repeated setup duplicated registrations')
    return {'registrations': len(expected), 'interpreted_statements': steps,
            'string_search_calls': runtime.calls['string_indexOf'], 'substring_calls': runtime.calls['SubString']}


def script_from_map(path):
    return Mpq(Path(path).read_bytes()).extract('war3map.j').decode()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('map')
    parser.add_argument('--baseline')
    args = parser.parse_args()
    current = measure(script_from_map(args.map))
    require(current['string_search_calls'] == 0 and current['substring_calls'] == 0,
            'UI startup still performs runtime string searches for rawcodes')
    result = {'current': current, 'boundary': 'Actual packaged UI setup; spell registration, event natives and timers are stubs. Statements are not engine operations.'}
    if args.baseline:
        result['baseline'] = measure(script_from_map(args.baseline), current_ui=False)
        candidate = Mpq(Path(args.map).read_bytes())
        baseline = Mpq(Path(args.baseline).read_bytes())
        for member in ('war3map.w3a', 'war3map.w3u'):
            require(candidate.extract(member) == baseline.extract(member), member + ' object bytes changed')
        result['object_bytes'] = 'W3A and W3U unchanged; legacy rawcode-only comparison'
    print(json.dumps(result, ensure_ascii=False, indent=2))
