#!/usr/bin/env python3
"""Check packaged pet UI registration and rawcode cost, without engine op claims."""
import argparse
import json
import re
from pathlib import Path

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyTrialReplay import TrialJassRuntime


class PetStartupRuntime(TrialJassRuntime):
    def __init__(self, script):
        self.trigger_serial = 80000
        self.conditions = {}
        self.actions = {}
        self.integer_saves = {}
        super().__init__(script)
        self.registered = []
        self.globals.update(EVENT_PLAYER_UNIT_SELECTED=18, EVENT_PLAYER_UNIT_DESELECTED=19,
                            EVENT_PLAYER_UNIT_SPELL_EFFECT=274, bj_MAX_PLAYER_SLOTS=16)
        self.invoke('init_ObjectIds')
        self.globals['RegisterEvents_onCastMap'] = self.invoke('new_HashMap')
        self.globals['TypeCasting_typecastdata'] = self.call('new_Table', [])
        self.invoke('init_TDPetUI')
        for player in range(16):
            self.globals['Player_players'][player] = player

    def native(self, name, args):
        if name == 'StringLength':
            return True, len(args[0])
        if name == 'registerSpellEffectEvent':
            self.registered.append(args[0])
            # Execute the packaged registration and HashMap implementation.
            return False, None
        if name == 'trigger_addAction':
            return False, None  # Execute the packaged wrapper into TriggerAddAction.
        if name == 'CreateTrigger':
            self.trigger_serial += 1
            self.conditions[self.trigger_serial] = []
            self.actions[self.trigger_serial] = []
            return True, self.trigger_serial
        if name in ('GetHandleId', 'ConvertFogState', 'Filter'):
            return True, args[0]
        if name == 'HaveSavedInteger':
            return True, tuple(args[:3]) in self.integer_saves
        if name == 'LoadInteger':
            return True, self.integer_saves.get(tuple(args[:3]), 0)
        if name == 'SaveInteger':
            self.integer_saves[tuple(args[:3])] = args[3]
            return True, True
        if name == 'TriggerAddCondition':
            self.conditions[args[0]].append(args[1])
            return True, None
        if name == 'TriggerAddAction':
            self.actions[args[0]].append(args[1])
            self.trigger_events.append((name, *args))
            return True, None
        return super().native(name, args)


class ManagerRoutingRuntime(PetStartupRuntime):
    """Run the actual event bridge up to admission (covered by Wurst tests)."""
    def __init__(self, script):
        super().__init__(script)
        self.admitted = []
        self.spell = 0

    def native(self, name, args):
        if name == 'GetSpellAbilityId':
            return True, self.spell
        if name == 'dispatch_TDPetUISession_TDPetUISession_admitCommand':
            self.admitted.append(tuple(args[:5]))
            return True, -1
        return super().native(name, args)


def manager_listener(runtime):
    """Both frozen spell bridges invoke the same exact admission owner once."""
    names = [name for name in ('TDPetUI_commandTrigger', 'TDPetUI_managerCommandTrigger')
             if name in runtime.globals]
    require(len(names) == 1, 'Missing/duplicate manager trigger identity')
    command = runtime.globals[names[0]]
    handlers = runtime.conditions[command] + runtime.actions[command]
    require(len(handlers) == 1, 'Missing/duplicate shared manager callback')
    callback = handlers[0]
    if names[0] == 'TDPetUI_commandTrigger':
        require(runtime.conditions[command] == ['bridge_onCommand'] and not runtime.actions[command],
                'User manager bridge must bind the exact onCommand condition')
    else:
        require(runtime.actions[command] == ['bridge_onManagerSpell'] and not runtime.conditions[command],
                'Phase-one manager bridge must bind the exact forwarding action')
        wrapper = runtime.functions['onManagerSpell'][1]
        require(len(wrapper) == 4 and
                wrapper[:2] == ['set wurst_stack[wurst_stack_depth] = w__wurst_stackPos',
                                'set wurst_stack_depth = wurst_stack_depth + 1'] and
                re.fullmatch(r'call onCommand\("when calling onCommand in TDPetUI, line \d+"\)', wrapper[2]) and
                wrapper[3] == 'set wurst_stack_depth = wurst_stack_depth - 1',
                'Manager action wrapper must only call onCommand once')
    return command, callback


def verify_routing(script):
    runtime = ManagerRoutingRuntime(script)
    runtime.invoke('tdResetState')
    runtime.invoke('tdSetLaneActive', 0, True)
    runtime.invoke('tdPetSetupUI')
    command, callback = manager_listener(runtime)
    display = 90001
    runtime.units[display] = {'owner': 0, 'abilities': {}}
    runtime.globals['TDPetUIView_tdPetDisplays'][0] = display
    owners = runtime.call('new_Table', [])
    runtime.globals['TDPetUIView_tdPetDisplayOwners'] = owners
    runtime.tables[owners][display] = 0
    runtime.event_target = display
    codes = [f'Pc{a:02X}' if a < 8 else f'Pm{a-8:02X}' for a in range(23)]
    codes += [f'L{index:03X}' for index in range(490)]
    for code in codes:
        runtime.spell = int.from_bytes(code.encode('ascii'), 'big')
        runtime.units[display]['abilities'][runtime.spell] = 1
        runtime.invoke(callback)
        require(runtime.admitted[-1] == (runtime.globals['TDPetUIView_tdPetUISessions'][0],
                                        0, display, runtime.spell, 1), 'Shared callback lost the exact command identity')
    require(len(runtime.admitted) == 513, 'Shared callback must reach admission exactly once per command')
    for caster, owner in ((90002, 0), (90003, 1), (90004, 4)):
        runtime.units[caster] = {'owner': owner}
        runtime.event_target = caster
        runtime.invoke(callback)
    runtime.event_target = None
    runtime.invoke(callback)
    runtime.event_target = display
    runtime.tables[owners].clear()
    runtime.invoke(callback)
    require(len(runtime.admitted) == 513, 'Foreign/null/revoked caster reached manager admission')
    return '513 button IDs reach exact session admission; foreign/null/revoked casters are ignored'


def measure(script, legacy=False):
    runtime = PetStartupRuntime(script)
    runtime.calls.clear()
    runtime.executed_steps = 0
    runtime.invoke('tdPetSetupUI')
    expected = ['Pcol', 'Pdep']
    if legacy:
        expected += [f'Pc{a:02X}' if a < 8 else f'Pm{a-8:02X}' for a in range(23)]
        expected += [f'L{index:03X}' for index in range(490)]
    require(runtime.registered == [int.from_bytes(value.encode('ascii'), 'big') for value in expected],
            f'Actual UI setup changed or missed its {len(expected)} spell registrations')
    require(runtime.globals['TDPetUI_ready'], 'UI setup did not set its guard')
    require(len(runtime.periodics) == 1, 'UI setup did not finish registering its watcher')
    steps = runtime.executed_steps
    conditions = {key: list(value) for key, value in runtime.conditions.items()}
    actions = {key: list(value) for key, value in runtime.actions.items()}
    events = list(runtime.trigger_events)
    if not legacy:
        command, _ = manager_listener(runtime)
        registrations = [event for event in events if event[0] == 'TriggerRegisterPlayerUnitEvent' and event[1] == command]
        require(len(registrations) == 16 and {event[2] for event in registrations} == set(range(16))
                and all(event[3] == 274 for event in registrations), 'Shared listener must cover each player once')
        require(steps < 2000, 'Pet UI startup work grew beyond the bounded shared-listener fixture')
    runtime.invoke('tdPetSetupUI')
    require(len(runtime.registered) == len(expected) and len(runtime.periodics) == 1, 'Repeated setup duplicated registrations')
    require(runtime.conditions == conditions and runtime.actions == actions and runtime.trigger_events == events,
            'Repeated setup duplicated shared handlers')
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
    result = {'current': current, 'boundary': 'Packaged UI setup, spell registration, HashMap and player registration loops execute. Engine natives, typecast handle table and timers are modeled. Statement counts are not engine operations.'}
    result['routing'] = verify_routing(script_from_map(args.map))
    if args.baseline:
        result['baseline'] = measure(script_from_map(args.baseline), legacy=True)
        candidate = Mpq(Path(args.map).read_bytes())
        baseline = Mpq(Path(args.baseline).read_bytes())
        for member in ('war3map.w3a', 'war3map.w3u'):
            require(candidate.extract(member) == baseline.extract(member), member + ' object bytes changed')
        result['object_bytes'] = 'W3A and W3U unchanged'
    print(json.dumps(result, ensure_ascii=False, indent=2))
