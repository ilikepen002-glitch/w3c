#!/usr/bin/env python3
"""Check native Ghost Visible on actual packaged wild spirits and bounded diff.

Usage: python3 tools/VerifyPetWildPathingArtifact.py map.w3x baseline.w3x
The baseline must be the same release before this change (and any coordinated
wild uico/ussi icon changes). This proves offline contracts, not live pathing.
"""
from pathlib import Path
import re
import sys

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects
from VerifyUnitParentsArtifact import unit_parents

WILD_IDS = {f'p{wave:02X}{species}'
            for wave in range(1, 33) for species in range(1, 4)}
REQUIRED_TARGETS = {'neutral', 'ground', 'air', 'organic', 'invulnerable'}
RUNTIME_SCOPE = re.compile(r'TDPetWild|tdPetWild|tdPetSpawnWild|tdPetSetupWild|'
                           r'tdPetHandleCapture|tdPetHandleMaster|tdLaneWaypoint|'
                           r'tdLaneSpawnPosition|tdLaneExitPosition')


def verify_wild_units(units, parents):
    wild = {uid for uid, fields in units.items()
            if re.fullmatch(r'p[0-9A-F]{2}[1-3]', uid)
            or fields.get('unam', '').startswith('[野生精灵]')}
    require(wild == WILD_IDS, 'Wild rawcodes must be exactly 96 p{wave:02X}{species} objects')
    for uid in sorted(WILD_IDS):
        fields = units[uid]
        require(parents[uid] == 'hpea', f'{uid}: wild parent must remain hpea')
        require(fields.get('uabi') == 'Aeth',
                f'{uid}: wild uabi must be exactly Aeth (no Aloc/Agho or extra ability)')
        require(fields.get('ucol') == 0.0, f'{uid}: existing zero collision changed')


def verify_capture_contract(abilities):
    require(not any(uid == 'Aeth' or parent == 'Aeth'
                    for uid, (parent, _) in abilities.items()),
            'Native Aeth must not be overridden or used as a custom ability parent')
    for uid, count in (('Pcap', 61),):
        require(uid in abilities, f'Missing capture ability {uid}')
        parent, fields = abilities[uid]
        require(parent == 'ANcl', f'{uid}: capture must retain Channel parent')
        require(fields.get(('alev', 0, 0)) == (0, count), f'{uid}: capture level count changed')
        targets = [(level, kind, value) for (key, level, _), (kind, value) in fields.items()
                   if key == 'atar']
        require(len(targets) == count and {level for level, _, _ in targets} == set(range(1, count + 1)),
                f'{uid}: target masks must cover exactly levels 1..{count}')
        for level, kind, value in targets:
            require(kind == 3 and REQUIRED_TARGETS.issubset(value.split(',')),
                    f'{uid} level {level}: neutral/ground/air/organic/invulnerable target mask changed')
            target_type = [value for (key, lvl, _), value in fields.items()
                           if key == 'Ncl2' and lvl == level]
            require(target_type == [(0, 1)], f'{uid} level {level}: capture must remain unit-targeted')


def jass_functions(script):
    return {match.group(1): match.group(0) for match in re.finditer(
        r'^function (\w+) takes[^\n]*\n.*?^endfunction', script, re.MULTILINE | re.DOTALL)}


def verify_runtime(script, baseline_script):
    functions, baseline = jass_functions(script), jass_functions(baseline_script)
    protected = {name for name, body in baseline.items() if RUNTIME_SCOPE.search(name + body)}
    actual = {name for name, body in functions.items() if RUNTIME_SCOPE.search(name + body)}
    require(protected == actual, 'Packaged wild/capture/route function set changed')
    for name in sorted(protected):
        require(functions[name] == baseline[name], f'Packaged wild/capture/route function changed: {name}')
    spawn = functions.get('tdPetSpawnWild', '')
    for statement in ('Player(PLAYER_NEUTRAL_PASSIVE)', 'unit_setPathing(creature, false)',
                      'SetUnitInvulnerable(creature, true)',
                      'SetUnitMoveSpeed(creature, tdPetWildTravelSpeed('):
        require(statement in spawn, f'Packaged wild spawn lost {statement}')
    require('distance / 80.0' in functions.get('tdPetWildTravelSpeed', ''),
            'Wild route-speed budget must remain 80 seconds')
    require('appearedAt + 60.0' in functions.get('construct_TDPetWildState', ''),
            'Wild capture deadline must remain 60 seconds')
    wild_bodies = '\n'.join(functions[name] for name in protected)
    require(not re.search(r'\b(?:PauseUnit|unit_pause|unit_unpause|UnitRemoveAbility|'
                          r'unit_removeAbility|UnitAddAbility|unit_addAbility)\(', wild_bodies),
            'Wild lifecycle must not pause or add/remove abilities at runtime')
    require(not re.search(r'(?:SetUnitPathing|unit_setPathing)\([^\n]*,\s*true\)', wild_bodies),
            'Wild lifecycle must not re-enable pathing')
    require(not re.search(r'\b(?:ReplaceUnit|ReplaceUnitBJ|unit_morph|unit_transform)\(', wild_bodies),
            'Wild lifecycle must not replace or transform its units')
    # Ghost Visible may stop excluding paused units. Audit call sites, rather
    # than rejecting harmless PauseUnit wrappers used for recycled FX dummies.
    calls = {
        'PauseUnit': {'unit_pause', 'unit_unpause'},
        'unit_pause': {'DummyRecycler_recycle'},
        'unit_unpause': {'DummyRecycler_get'},
        'DummyRecycler_recycle': {'call_doAfter_DummyRecycler'},
        'DummyRecycler_recycle_1': {'Fx_onDestroy'},
        'DummyRecycler_get': {'construct_Fx2'},
    }
    for callee, allowed in calls.items():
        callers = {name for name, body in functions.items()
                   if re.search(r'\b' + re.escape(callee) + r'\(', body.split('\n', 1)[1])}
        require(callers == allowed, f'Unexpected pause/dummy call sites for {callee}: {sorted(callers)}')
    require(re.search(r'DummyRecycler_recycle_1\(Fx_dummy\[', functions.get('Fx_onDestroy', '')),
            'FX recycler must only receive its own dummy')
    require(not re.search(r'\bset Fx_dummy\[[^\]]+\] = (?!null\b|DummyRecycler_get\()', script),
            'FX dummy assignment changed; cannot prove wild units stay out of recycler')
    require("'Aeth'" not in script and str(int.from_bytes(b'Aeth', 'big')) not in script,
            'Aeth must be attached by object generation only, not runtime code')
    return len(protected)


def verify_unit_diff(units, parents, baseline_units, baseline_parents):
    require(set(units) == set(baseline_units), 'Packaged unit object set changed')
    require(parents == baseline_parents, 'Packaged unit parents changed')
    ability_changes, icon_changes = set(), 0
    for uid in sorted(units):
        before, after = baseline_units[uid], units[uid]
        for key in set(before) | set(after):
            if key == 'wurs' or before.get(key) == after.get(key):
                continue
            require(uid in WILD_IDS and key in ('uabi', 'uico', 'ussi'),
                    f'Unapproved packaged unit change: {uid}.{key}')
            if key == 'uabi':
                require(before.get(key) == '' and after.get(key) == 'Aeth',
                        f'{uid}: baseline-to-built uabi must be empty -> Aeth')
                ability_changes.add(uid)
            else:
                icon_changes += 1
    require(ability_changes == WILD_IDS, 'Diff must contain exactly 96 wild uabi changes')
    return icon_changes


def verify_archive(artifact, baseline):
    units = unit_objects(artifact.extract('war3map.w3u'))
    parents = unit_parents(artifact.extract('war3map.w3u'))
    verify_wild_units(units, parents)
    verify_capture_contract(ability_objects(artifact.extract('war3map.w3a')))
    icons = verify_unit_diff(units, parents, unit_objects(baseline.extract('war3map.w3u')),
                             unit_parents(baseline.extract('war3map.w3u')))
    for member in ('war3map.w3a', 'war3map.w3e', 'war3map.wpm'):
        require(artifact.extract(member) == baseline.extract(member), f'Packaged {member} changed')
    count = verify_runtime(artifact.extract('war3map.j').decode('utf-8'),
                           baseline.extract('war3map.j').decode('utf-8'))
    return icons, count


def main():
    require(len(sys.argv) == 3, __doc__)
    artifact, baseline = (Mpq(Path(path).read_bytes()) for path in sys.argv[1:])
    icons, functions = verify_archive(artifact, baseline)
    print(f'PASS: exactly 96 hpea wild objects use native Aeth only; '
          f'96 uabi changes, {icons} coordinated wild icon field changes; no other W3U changes except wurs.')
    print(f'PASS: Pcap 61 ordinary unit-target masks; unchanged W3A/W3E/WPM; '
          f'{functions} unchanged wild/capture/route functions; pause calls confined to FX dummy recycler.')
    print('NOT TESTED: live blocking, selection, Channel click targeting and native Aeth side effects.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, AssertionError, OSError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        sys.exit(1)
