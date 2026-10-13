#!/usr/bin/env python3
"""Execute the real packaged deployment gate with bounded, controlled inputs.

Usage: python3 tools/VerifyPetDeploymentArtifact.py ExampleMap.w3x \
    --previous /path/to/previous.w3x --baseline HEAD
Use --expect-capped or --historical-differential for preserved old-map checks.
The default current-manager mode admits twenty-slot fixture boundaries without
requiring the previous single-tail source differential to remain unchanged.
This is a gate test, not a Warcraft runtime or combat/performance simulation.
"""
import argparse
from pathlib import Path
import re
import subprocess

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyPetUIArtifact import (_run_scalar_helper, field_value, jass_function)

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_HINT = '每座塔可上阵1只精灵'
OLD_HINT = re.compile(r'上阵\s*(?:最多\s*)?3\s*(?:只)?|每路\s*3\s*只')
PROTECTED_SOURCE = (
    'wurst/pets/TDPetState.wurst', 'wurst/pets/TDPetCombat.wurst',
    'wurst/pets/TDPetRules.wurst', 'wurst/pets/TDPetEffectState.wurst',
    'wurst/TDState.wurst', 'wurst/towers/TDTowerRuntime.wurst',
    'wurst/towers/TDTowerCommonData.wurst',
    'tests/wurst/TDPetsTests.wurst', 'tests/wurst/TDPetReleaseTests.wurst',
    'tests/wurst/TDPetReleaseRewardTests.wurst', 'tests/wurst/TDStateTests.wurst',
    'tests/wurst/TDTowersTests.wurst',
)
PROTECTED_JASS = (
    'tdPetDeploy', 'TDPet_recall', 'tdPetAt', 'tdPetForHost',
    'tdPetStore', 'tdPetDiscardOwned',
    'tdPetInitializeLane', 'tdPetLaneDefeated', 'tdPetTowerRemoved',
    'tdPetTowerWorkStarted', 'tdPetTowerWorkFinished',
    'tdPetCooldownReduction', 'tdPetGlobalAura',
    'call_doPeriodically_TDPetRuntime', 'call_doAfter_doPeriodically_TDPetRuntime',
    'tdPopulationLimitForStage', 'tdGetTowerPopulationLimit',
)


def packaged_script(path):
    return Mpq(path.read_bytes()).extract('war3map.j').decode('utf-8')


def run_gate(script, existing, *, lane=0, other_existing=0, capacity=20,
             pet_present=True, released=False, tower_present=True,
             alive=True, lane_allowed=True, owner=None, tower_choice=1, busy=False,
             occupied=False, rebind=False, repeated=False):
    """A bounded twenty-slot fixture (capacity=12 for historical checks); all gate dependencies/natives below are controlled stubs.

    Deployed count and occupied-host stubs read concrete fixture hosts, rather
    than returning an asserted expected answer. No deploy/recall is simulated.
    """
    require(lane in (0, 1) and capacity in (12, 20) and 0 <= existing < capacity and 0 <= other_existing < capacity,
            'Gate fixture must fit two independent bounded lane collections')
    other_lane = 1 - lane
    base = lane * 100
    hosts = {base + index + 1: 1000 + base + index for index in range(existing)}
    pet = base + existing + 1
    slots = {lane: list(range(base + 1, base + existing + 2)) + [0] * (capacity - 1 - existing),
             other_lane: [other_lane * 100 + index + 1 for index in range(other_existing)]
                         + [0] * (capacity - other_existing)}
    hosts.update({record: 1000 + record - 1 for record in slots[other_lane] if record})
    hosts[pet] = None
    if rebind or repeated:
        require(existing > 0, 'Rebind/repeat fixture needs an already deployed record')
        pet = base + 1
    tower = 1000 + base if occupied or repeated else 2000 + lane
    all_units = set(host for host in hosts.values() if host is not None) | {tower}
    # Only the selected tower differs from the otherwise valid fixture units.
    owners = {host: record // 100 for record, host in hosts.items() if host is not None}
    owners[tower] = lane if owner is None else owner
    constants = {'TDPet_lane': {record: record // 100 for record in hosts},
                 'TDPet_released': {record: released if record == pet else False for record in hosts},
                 'TDPet_host': hosts, 'TDPetState_tdPetBusyTowers': 317}
    limit = re.search(r'\bset TDPetData_TD_PET_DEPLOY_LIMIT\s*=\s*(\d+)\b', script)
    if limit:
        constants['TDPetData_TD_PET_DEPLOY_LIMIT'] = int(limit.group(1))
    calls = []

    def known_unit(unit):
        require(unit in all_units, f'Unknown controlled native unit input: {unit}')
        return unit

    def deployed_count(requested_lane):
        require(requested_lane in slots, 'Unknown controlled deployed-count lane')
        count = sum(record != 0 and hosts[record] is not None for record in slots[requested_lane])
        require(count == (existing if requested_lane == lane else other_existing),
                'Concrete fixture deployed count does not match lane setup')
        calls.append(('tdPetDeployedCount', (requested_lane, count)))
        return count

    def for_host(unit):
        known_unit(unit)
        calls.append(('tdPetForHost', unit))
        require(owners[unit] in slots, 'Unknown controlled host-lookup lane')
        return next((record for record in slots[owners[unit]]
                     if record != 0 and hosts[record] == unit), 0)

    def table_busy(table, handle, stack_position):
        require(table == 317 and known_unit(handle) == tower
                and re.fullmatch(r'when calling hasBoolean in TDPetRuntime, line \d+',
                                 stack_position) is not None,
                'Unexpected controlled busy-tower dependency arguments')
        calls.append(('busy', handle))
        return busy

    # These names are the complete, explicit whitelist. Unknown calls fail closed.
    functions = {
        'unit_isAlive': lambda unit: alive if known_unit(unit) == tower else True,
        'tdPetLaneCanAct': lambda requested_lane: lane_allowed if requested_lane == lane else False,
        'GetOwningPlayer': lambda unit: owners[known_unit(unit)],
        'GetPlayerId': lambda player: player,
        'GetUnitTypeId': lambda unit: tower_choice if known_unit(unit) == tower else 1,
        'tdTowerChoiceForUnitTypeId': lambda type_id: type_id,
        'handle_getHandleId': known_unit,
        'dispatch_Table_Table_hasBoolean': table_busy,
        'tdPetForHost': for_host,
        'tdPetDeployedCount': deployed_count,
    }
    actual = _run_scalar_helper(jass_function(script, 'tdPetCanDeploy'),
                                (pet if pet_present else 0,
                                 tower if tower_present else None,
                                 'controlled packaged deployment gate test'),
                                constants, functions, debug_stack=True)
    require(type(actual) is bool, 'Packaged deployment gate did not return boolean')
    return actual, calls


def verify_gate(script, capped=False, capacity=20):
    for lane in (0, 1):
        for existing in sorted({0, 1, 2, 3, 4, 9, capacity - 1}):
            actual, calls = run_gate(script, existing, lane=lane, other_existing=capacity - 1 - existing, capacity=capacity)
            expected = existing < 3 if capped else True
            require(actual is expected,
                    f'Real packaged gate: lane={lane} existing={existing}, new candidate got {actual}, '
                    f'expected {expected}')
            if capped:
                require(('tdPetDeployedCount', (lane, existing)) in calls,
                        'Old-map reproduction did not execute the lane-specific count dependency')
            else:
                require(not any(name == 'tdPetDeployedCount' for name, _ in calls),
                        'Uncapped gate still consults a lane-wide count dependency')
    guards = (
        ('null pet', {'pet_present': False}), ('released pet', {'released': True}),
        ('null tower', {'tower_present': False}), ('dead tower', {'alive': False}),
        ('stopped lane', {'lane_allowed': False}), ('foreign owner', {'owner': 1}),
        ('non-tower', {'tower_choice': 0}), ('busy tower', {'busy': True}),
        ('occupied tower', {'occupied': True}), ('same-host repeat', {'repeated': True}),
    )
    for lane in (0, 1):
        for name, options in guards:
            if name == 'foreign owner':
                options = {'owner': 1 - lane}
            actual, _ = run_gate(script, 3, lane=lane, other_existing=9, capacity=capacity, **options)
            require(actual is False, f'Real packaged gate failed to reject {name} in lane={lane}')
        for existing in sorted({3, 4, 9, capacity - 1}):
            actual, _ = run_gate(script, existing, lane=lane, other_existing=2, rebind=True, capacity=capacity)
            require(actual is True, f'Legal empty-tower rebind failed at lane={lane} existing={existing}')
    if capped:
        print('PASS OLD RED: three concrete fixture records already hosted; the real '
              'packaged tdPetCanDeploy rejects a fourth unbound record. '
              'Parsing, all earlier legal guards and legal rebind execute successfully.')
    else:
        print(f'PASS NEW GATE: two independent {capacity}-slot lanes through existing {capacity - 1} admit another record; '
              'ten rejection guards per lane '
              'and legal empty-tower rebind pass. Upper boundary is synthetic gate coverage; '
              'normal tower population remains at most 10.')
    print('CONTROLLED STUBS: lane eligibility, tower/native properties, busy table, '
          f'{capacity}-slot deployed count and host lookup. Only the real packaged admission '
          'function is executed; no deploy/recall/combat/native engine is modeled.')


def canonical_jass(body):
    return re.sub(r'(when calling [^"\n]+, line )\d+', r'\1#', body)


def verify_unchanged_packaged(previous, current):
    for name in PROTECTED_JASS:
        require(canonical_jass(jass_function(previous, name).group(0)) ==
                canonical_jass(jass_function(current, name).group(0)),
                f'Protected packaged function changed: {name}')
    for name in ('call_doPeriodically_TDPetRuntime',
                 'call_doAfter_doPeriodically_TDPetRuntime', 'tdPetForHost', 'tdPetAt'):
        require('TDPetData_TD_PET_COLLECTION_LIMIT' in jass_function(current, name).group(1),
                f'Packaged 12-slot lifecycle/host path lost its collection bound: {name}')
    require(re.search(r'\bset TDPetData_TD_PET_COLLECTION_LIMIT\s*=\s*12\b', current),
            'Packaged collection limit is not 12')
    require('TDPetData_TD_PET_DEPLOY_LIMIT' not in current,
            'Removed deploy-limit constant remains in packaged JASS')
    print('PASS PACKAGED STRUCTURE: deploy, recall, host lookup, 12-slot lifecycle, '
          'cooldown and tower-population functions unchanged against predecessor.')


def verify_source(baseline):
    def before(name):
        result = subprocess.run(['git', 'show', f'{baseline}:{name}'], cwd=ROOT,
                                check=True, capture_output=True)
        return result.stdout
    for name in PROTECTED_SOURCE:
        path = ROOT / name
        require(path.read_bytes() == before(name), f'Protected source/test changed: {name}')
    runtime = 'wurst/pets/TDPetRuntime.wurst'
    old = before(runtime).decode('utf-8')
    tail = 'return pet.host != null or tdPetDeployedCount(pet.lane) < TD_PET_DEPLOY_LIMIT'
    require(old.count(tail) == 1, 'Predecessor deploy gate no longer has the known cap tail')
    require((ROOT / runtime).read_text() == old.replace(tail, 'return true'),
            'Runtime changed beyond the approved gate tail; first three guards must stay byte-identical')
    data = (ROOT / 'wurst/pets/TDPetData.wurst').read_text()
    require('TD_PET_DEPLOY_LIMIT' not in data and
            'public constant int TD_PET_COLLECTION_LIMIT = 12' in data,
            'Source deploy cap/collection capacity contract failed')
    for name in ('TDPetData', 'TDPetUI', 'TDPetObjectGen'):
        source = (ROOT / f'wurst/pets/{name}.wurst').read_text()
        require(not OLD_HINT.search(source) and
                (name == 'TDPetData' or DEPLOY_HINT in source),
                f'Player source still advertises old three-pet deployment cap: {name}')
    print('PASS SOURCE DIFFERENTIAL: only the deployment-gate tail changed in runtime; '
          'state/combat/rules, collection/release/cooldown tests and population tests unchanged.')


def verify_tooltips(path, script, current_manager=True):
    abilities = ability_objects(Mpq(path.read_bytes()).extract('war3map.w3a'))
    for rawcode, expected_levels in (('Pdep', 1), ('Pcap', 61)):
        fields = abilities[rawcode][1]
        require(field_value(fields, 'alev') == expected_levels,
                f'{rawcode}: tooltip level count changed')
        for level in range(1, expected_levels + 1):
            tooltip = field_value(fields, 'aub1', level)
            require(not OLD_HINT.search(tooltip) and
                    (rawcode == 'Pcap' or (current_manager and '本塔' in tooltip and '没有精灵' in tooltip) or (not current_manager and DEPLOY_HINT in tooltip)),
                    f'{rawcode} level {level}: missing navigation/deployment hint or obsolete total cap')
    fields = abilities['Pc04'][1]
    require(DEPLOY_HINT in field_value(fields, 'aub1', 1),
            'Pc04 deployment tooltip lacks the one-pet-per-tower hint')
    require(not any(OLD_HINT.search(value) for (_, _, _), (_, value) in fields.items()
                    if isinstance(value, str)), 'Pc04 still advertises an old three-pet cap')
    require(not OLD_HINT.search(script), 'Packaged UI/JASS still advertises an old three-pet cap')
    if not current_manager:
        require(DEPLOY_HINT in jass_function(script, 'onCommand').group(1),
                'Packaged deployment UI lacks the one-pet-per-tower hint')
    print('PASS PLAYER HINTS: Pdep, all 61 Pcap levels, Pc04 and packaged UI have no old '
          'three-pet total cap; tower details and manager deployment hints are current.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--previous', type=Path)
    parser.add_argument('--baseline', default='HEAD')
    parser.add_argument('--expect-capped', action='store_true')
    parser.add_argument('--historical-differential', action='store_true', help='Reproduce the older twelve-slot single-tail cap-removal contract only')
    args = parser.parse_args()
    script = packaged_script(args.map)
    if args.expect_capped:
        verify_gate(script, capped=True, capacity=12)
        return
    if args.historical_differential:
        require(args.previous is not None, 'Historical differential requires the predecessor map')
        previous = packaged_script(args.previous)
        verify_gate(previous, capped=True, capacity=12)
        verify_gate(script, capacity=12)
        verify_source(args.baseline)
        verify_unchanged_packaged(previous, script)
        verify_tooltips(args.map, script, current_manager=False)
    else:
        verify_gate(script, capacity=20)
        require(re.search(r'\bset TDPetData_TD_PET_COLLECTION_LIMIT\s*=\s*20\b', script),
                'Current manager packaged capacity must be twenty')
        require('TDPetData_TD_PET_DEPLOY_LIMIT' not in script, 'Removed deployment cap remains')
        require('tdPetDeploy(' not in jass_function(script, 'onDeploy').group(1),
                'Tower Pdep bypasses the authorized manager session')
        verify_tooltips(args.map, script)
    print('NOT TESTED: live Warcraft deployment/effects, native engine lifecycle, '
          'rendering or higher active-combat load/performance.')


if __name__ == '__main__':
    main()
