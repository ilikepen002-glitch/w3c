#!/usr/bin/env python3
"""Read-only ordinary-capture removal gate against the exact formal predecessor.

python3 tools/VerifyCaptureRemovalArtifact.py ExampleMap.w3x --baseline-map before.w3x
This gate is separate from the strict legacy icon-only predecessor delta.
Actual packed objects/JASS/resources are checked; no Warcraft engine is run.
"""
import argparse
import json
from pathlib import Path
import re
import struct

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects
from VerifyGroundItemArtifact import verify_function_book, verify_no_hunt_objects
from VerifySemanticIconArtifact import (ROOT, MANIFEST, Reader, icon_path, load_objects,
                                       normalized_path, sha, verify_bindings, verify_paths,
                                       verify_resources)

REMOVED = ('Pmas', 'Pfor')
COLLECTION = tuple(f'Pc0{i}' for i in range(8))
REMOVED_IMPORTS = tuple(icon_path('TDAction' + name, disabled)
                       for name in ('MasterCapture', 'CaptureForge')
                       for disabled in (False, True))
BOOK_DESCRIPTION = ('打开背包合成、地面范围升级和伤害统计。|n'
                    '地面物品每30秒整理到所属路线的高台边缘：装备按品质分堆，捕获球单独一堆。')
BOOK_VALUES = {('spb1', 1, 1): 'A119,Gupg,Dsta', ('spb3', 1, 3): 3,
               ('spb4', 1, 4): 3, ('aub1', 1, 0): BOOK_DESCRIPTION}


def verify_removal_objects(objects, baseline):
    """Closed field delta: two deletions, four book fields and eight order shifts."""
    before_abilities = baseline['abilities']
    require(all(rawcode in before_abilities for rawcode in REMOVED),
            'Baseline must contain both removed capture commands')
    old_book = before_abilities['Geqb'].fields
    require(old_book[('spb1', 1, 1)].value == 'A119,Gupg,Dsta,Pmas,Pfor' and
            all(old_book[(field, 1, column)].value == 5
                for field, column in (('spb3', 3), ('spb4', 4))),
            'Baseline must be the exact five-command predecessor')
    allocation = REMOVED + COLLECTION
    prior_orders = [before_abilities[rawcode].fields[('Ncl6', 1, 6)].value
                    for rawcode in allocation]
    require(len(set(prior_orders)) == len(prior_orders), 'Baseline allocator orders collide')
    expected_orders = dict(zip(COLLECTION, prior_orders[:-2]))
    for kind, current in objects.items():
        before = baseline[kind]
        deleted = set(REMOVED) if kind == 'abilities' else set()
        require(list(current) == [rawcode for rawcode in before if rawcode not in deleted],
                f'{kind}: unexpected object set/order delta')
        for rawcode, obj in current.items():
            previous = before[rawcode]
            require((obj.table, obj.identity) == (previous.table, previous.identity),
                    f'{rawcode}: object identity/parent/table changed')
            allowed = (BOOK_VALUES if kind == 'abilities' and rawcode == 'Geqb' else
                       {('Ncl6', 1, 6): expected_orders[rawcode]}
                       if kind == 'abilities' and rawcode in COLLECTION else {})
            require(list(obj.fields) == list(previous.fields), f'{rawcode}: field set/order changed')
            if not allowed:
                require(obj.encoded() == previous.encoded(), f'{rawcode}: unrelated object changed')
            for key, field in obj.fields.items():
                old = previous.fields[key]
                if key not in allowed:
                    require(field == old, f'{rawcode}.{key}: forbidden removal field delta')
                else:
                    require(field.value == allowed[key], f'{rawcode}.{key}: wrong approved removal value')
                    require(field.kind == old.kind and field.raw[:16] == old.raw[:16] and
                            field.raw[-4:] == old.raw[-4:],
                            f'{rawcode}.{key}: approved field metadata changed')
    verify_bindings(objects)


def filtered_import_manifest(data):
    """Keep retained flags, paths and record ordering byte-for-byte."""
    reader = Reader(data)
    require(reader.integer() == 1, 'Unsupported import version')
    records, removed = [], set()
    forbidden = {normalized_path(path) for path in REMOVED_IMPORTS}
    for _ in range(reader.integer()):
        start = reader.offset
        flag, name = reader.take(1)[0], reader.string()
        require(flag in (5, 8, 10, 13), 'Unsupported import flag')
        path = name if flag in (10, 13) else 'war3mapImported\\' + name
        folded = normalized_path(path)
        if folded in forbidden:
            require(folded not in removed, 'Duplicate retired import')
            removed.add(folded)
        else:
            records.append(data[start:reader.offset])
    require(reader.offset == len(data) and removed == forbidden,
            'Baseline must contain exactly four retired imports')
    return struct.pack('<II', 1, len(records)) + b''.join(records)


def normalize_display_timestamp(data):
    pattern = re.compile(rb'\d{8}-\d{4}-UTC\+8')
    require(len(pattern.findall(data)) == 2, 'Expected only map/loading display timestamps')
    return pattern.sub(b'BUILD-DISPLAY-TIMESTAMP', data)


def verify_removal_members(artifact, baseline):
    current, before = artifact.members(), baseline.members()
    require(set(current) == set(before) - set(REMOVED_IMPORTS),
            'Unexpected packaged member delta')
    for archive, members in ((artifact, current), (baseline, before)):
        active = sum(1 for _a, _b, _locale, _platform, block in archive.hashes
                     if block < len(archive.blocks) and archive.blocks[block][3] & 0x80000000)
        require(active == len(members), 'Hidden/unlisted packaged resource remains')
    require(current['war3map.imp'] == filtered_import_manifest(before['war3map.imp']),
            'Import manifest changed outside four retired paths')
    require(normalize_display_timestamp(current['war3map.w3i']) ==
            normalize_display_timestamp(before['war3map.w3i']),
            'Map metadata changed outside display timestamps')
    mutable = {'war3map.w3a', 'war3map.j', 'war3map.imp', 'war3map.w3i', '(listfile)'}
    for path, data in current.items():
        if path not in mutable:
            require(data == before[path], f'{path}: unrelated packaged resource changed')
    script = current['war3map.j'].decode('utf-8')
    for obsolete in ('大师球', '五合一', 'tdPetMasterBalls', 'tdPetForgeMasterBall',
                     'tdPetHandleMaster', 'tdPetHandleForge', 'tdPetHandleCaptureWithBall'):
        require(obsolete not in script, f'Obsolete capture gameplay remains: {obsolete}')
    for rawcode in REMOVED:
        literal = str(int.from_bytes(rawcode.encode('ascii'), 'big'))
        require(not re.search(r'(?<!\d)' + literal + r'(?!\d)', script),
                f'Removed {rawcode} remains in packaged script')


def canonical_packaged_function(body):
    """Normalize debug source lines and declared compiler-temp alpha-renaming only."""
    body = re.sub(r'(when calling [^"\n]+, line )\d+', r'\1#', body)
    names = re.findall(r'^\s*local (?:integer|real|string|player|unit|boolean) (temp\d+)\b',
                       body, re.MULTILINE)
    mapping = {name: f'compilerTemp{index}' for index, name in enumerate(names)}
    return re.sub(r'\btemp\d+\b', lambda match: mapping.get(match[0], match[0]), body)


def verify_spend_and_attempt(script, capacity=12, capture_percent=60):
    """Execute real scalar helper/conditions with explicit controlled dependencies.

    Default 60 preserves the immutable historical removal oracle. Current-map
    callers explicitly select the approved 65-percent profile.
    """
    from VerifyPetUIArtifact import _integer_expression, _run_scalar_helper, jass_function
    spend = jass_function(script, 'tdPetSpendCaptureBall')
    for lane in (-1, 0, 1, 3, 4):
        for valid in (False, True):
            for count in (0, capacity - 1, capacity, capacity + 1):
                for balls in (0, 1, 60):
                    calls = []
                    def take(requested_lane):
                        calls.append(requested_lane)
                        return balls > 0
                    actual = _run_scalar_helper(spend, (lane, valid),
                        {'TDPetData_TD_PET_COLLECTION_LIMIT': capacity},
                        {'tdIsLanePlayer': lambda value: 0 <= value < 4,
                         'tdPetCollectionCount': lambda _lane: count, 'tdPetTakeBall': take})
                    eligible = 0 <= lane < 4 and valid and count < capacity
                    require(actual is (eligible and balls > 0) and
                            calls == ([lane] if eligible else []),
                            f'Ordinary spend precondition/charge changed: {lane, valid, count, balls}')
    capture = jass_function(script, 'tdPetHandleCapture').group(1)
    guarantee = re.search(r'^\s*set guaranteed = (.+)$', capture, re.MULTILINE)
    require(guarantee is not None, 'Missing ordinary tutorial guarantee')
    for tutorial in (False, True):
        for used in (False, True):
            actual = _integer_expression(guarantee[1], {
                'TDPetWildRecord_tutorial': {1: tutorial},
                'TDPetState_tdPetTutorialUsed': {0: used}, 'wild': 1, 'lane_2': 0})
            require(actual is (tutorial and not used), 'Tutorial first-attempt guarantee changed')
    roll = re.search(r'^\s*if (.+GetRandomInt\(1, 100\).+) then$', capture, re.MULTILINE)
    require(roll is not None, 'Missing ordinary capture roll')
    for guaranteed in (False, True):
        for value in range(1, 101):
            actual = _integer_expression(roll[1].strip(), {'guaranteed': guaranteed},
                                        {'GetRandomInt': lambda _low, _high: value})
            require(actual is (not guaranteed and value > capture_percent), 'Ordinary sixty-percent roll changed' if capture_percent == 60 else f'Ordinary {capture_percent}-percent roll changed')
    # Current four-slot capture refunds either failed generation or failed storage.
    # Keep the historical direct-store branch and accept only this exact new shape.
    refund = re.search(r'if\s+(?:not tdPetStore\(|\( not generated\) or \( not tdPetStore\().*?^\s*endif',
                       capture, re.MULTILINE | re.DOTALL)
    require(refund is not None and refund[0].count('call tdPetAddBall(lane_2)') == 1 and
            refund[0].count('call tdPetSyncBallAbility(lane_2)') == 1,
            'Ordinary storage failure must refund and synchronize exactly once')
    require(capture.index('tdPetSpendCaptureBall(') < capture.index('set guaranteed =') and
            'set TDPetState_tdPetTutorialUsed[lane_2] = true' in capture,
            'Tutorial attempt must be marked only after ordinary ball spending')
    print('PASS SUPPLIED JASS CAPTURE RULES: 120 spend states, 4 tutorial states, 200 rolls; refund/sync.')


def verify_capture_runtime(script, baseline_script):
    from VerifyPetUIArtifact import jass_function
    from VerifyPetDeploymentArtifact import verify_gate
    from VerifyPetWildPathingArtifact import jass_functions, verify_runtime
    protected = ('tdPetTakeBall', 'tdPetAddBall', 'tdPetSyncBallAbility',
                 'tdPetHandleBallPickup', 'tdPetHandleEnemyBallDrop', 'tdPetStore',
                 'tdPetDeploy', 'TDPet_recall', 'tdPetForHost', 'tdPetAt',
                 'tdPetTowerRemoved', 'tdPetTowerWorkStarted', 'tdPetTowerWorkFinished',
                 'tdPetCooldownReduction', 'tdPetGlobalAura',
                 'call_doPeriodically_TDPetRuntime', 'call_doAfter_doPeriodically_TDPetRuntime',
                 'tdPopulationLimitForStage', 'tdGetTowerPopulationLimit')
    for name in protected:
        require(canonical_packaged_function(jass_function(script, name).group(0)) ==
                canonical_packaged_function(jass_function(baseline_script, name).group(0)),
                f'Unrelated ordinary/deployment/lifecycle function changed: {name}')
    current, before = jass_functions(script), jass_functions(baseline_script)
    wild_scope = re.compile(r'TDPetWild|tdPetWild|tdPetSpawnWild|tdPetSetupWild|'
                            r'tdLaneWaypoint|tdLaneSpawnPosition|tdLaneExitPosition')
    protected_wild = {name for name in before if wild_scope.search(name)}
    require(protected_wild == {name for name in current if wild_scope.search(name)},
            'Wild lifecycle function set changed')
    for name in protected_wild:
        expected = before[name].replace('Q普通球捕获；功能菜单可投大师球。', 'Q普通球捕获。')
        require(canonical_packaged_function(current[name]) == canonical_packaged_function(expected),
                f'Wild lifecycle changed outside removed master hint: {name}')
    verify_runtime(script, script)  # Current invariant checks; the differential is above.
    verify_gate(script)  # Actual packaged uncapped admission, including fourth..twelfth.
    verify_spend_and_attempt(script)


def verify_inherited_boss(script, baseline_script):
    """Re-use Boss behavior gates; retain its strict Boss-only object delta separately."""
    import VerifyBossSpellResistanceArtifact as boss
    from VerifyTowerUpgradeArtifact import JassScalarEvaluator
    current = JassScalarEvaluator(script).functions
    before = JassScalarEvaluator(baseline_script).functions
    names = {name for name in before if re.match(
        r'(?:tdWaveBoss|tdEnemyMechanicScale|tdEnemyMechanicNativeSpellEligible|'
        r'TDEnemyMechanicState_scaledSpellAmount|tdSetupEnemyMechanics|'
        r'tdEnemyMechanicsShutdown|DamageEvent_setAmount|DamageEvent_onDamage|'
        r'dispatch_DamageListener_DamageListener_onEvent|spellDamage$)', name)}
    require(len(names) >= 10, 'Formal baseline lacks expected Boss resistance/engine functions')
    for name in sorted(names):
        require(name in current and boss.canonical_function(script, name) ==
                boss.canonical_function(baseline_script, name),
                'Inherited Boss resistance/engine function changed: ' + name)
    result = dict(state_cases=boss.verify_pure_and_runtime(script),
                  engine_accounting_cases=boss.verify_engine_and_accounting(script),
                  zero_event_cases=boss.verify_zero_engine_event(script),
                  damage_sites=boss.verify_compiled_structure(script),
                  scripted_paths=boss.verify_scripted_damage(script),
                  inherited_functions=len(names))
    boss.verify_setup_lifecycle(script)
    print('PASS INHERITED BOSS JASS:', json.dumps(result, sort_keys=True))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--baseline-map', type=Path, required=True)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    data, old_data = args.map.read_bytes(), args.baseline_map.read_bytes()
    artifact, baseline = Mpq(data), Mpq(old_data)
    verify_removal_objects(load_objects(artifact), load_objects(baseline))
    verify_removal_members(artifact, baseline)
    verify_capture_runtime(artifact.extract('war3map.j').decode('utf-8'),
                           baseline.extract('war3map.j').decode('utf-8'))
    verify_inherited_boss(artifact.extract('war3map.j').decode('utf-8'),
                          baseline.extract('war3map.j').decode('utf-8'))
    abilities = ability_objects(artifact.extract('war3map.w3a'))
    units = unit_objects(artifact.extract('war3map.w3u'))
    items = unit_objects(artifact.extract('war3map.w3t'))
    verify_no_hunt_objects(abilities, units, items)
    verify_function_book(abilities, units)
    paths = verify_paths(artifact, args.root)
    for retired in REMOVED_IMPORTS:
        require(not artifact.has(retired) and normalized_path(retired) not in paths[0] and
                normalized_path(retired) not in paths[1], f'Retired import remains: {retired}')
    manifest = json.loads((args.root / MANIFEST).read_text(encoding='utf-8'))
    decoded = verify_resources(artifact, baseline, args.root, manifest, paths,
                               preserved_current_paths=True)
    print('PASS: only Pmas/Pfor removed; exact three-command book; eight predecessor-derived order shifts.')
    print(f'PASS: four retired imports absent; {len(decoded)} retained icons verified; unrelated objects/resources identical.')
    print('FINAL MAP SHA256:', sha(data))
    print('BASELINE MAP SHA256:', sha(old_data))
    print('NOT TESTED: native 1.27a UI/gameplay/pathing or platform extensions.')


if __name__ == '__main__':
    main()
