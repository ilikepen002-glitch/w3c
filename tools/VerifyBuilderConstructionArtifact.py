#!/usr/bin/env python3
"""Native builder source/packaged-object contract; no claim of live 1.27a play.

Usage: python tools/VerifyBuilderConstructionArtifact.py map.w3x
       python tools/VerifyBuilderConstructionArtifact.py --source-only
"""
from pathlib import Path
import re
import struct
import sys
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerPlacementArtifact import unit_objects
from VerifyUnitParentsArtifact import unit_parents

ROOT = Path(__file__).resolve().parents[1]
TOWER_IDS = tuple(f'u{family}{suffix}' for family in 'AOHDG'
                  for suffix in ('11', '12', '13', '14', '15', '6A', '6B'))
A_WORKER_ABILITIES = 'AUbu,A108,A109,A117,Geqb,Pcap,Pcol,Pdep'


def validate_builder_source(catalog, common, objects, runtime):
    require("TD_FARMER_BUILD_ABILITY_ID = 'AUbu'" in catalog, 'Source builder must use AUbu')
    require(re.search(r'function tdFarmerRaceForObjectGen\(\) returns Race\n(?:\t//[^\n]*\n)*\treturn Race.Undead', common),
            'Source builder race must be Undead')
    require('function tdTowerRaceForObjectGen() returns Race\n\treturn Race.Human' in common,
            'Source tower race must remain Human')
    match = re.search(r'@compiletime function tdGenerateBuilderObjects\(\)\n(.*?)(?=^function |\Z)', objects, re.M | re.S)
    require(match is not None, 'Missing builder object generator')
    worker = match[1]
    for token in ("new UnitDefinition(TD_FARMER_UNIT_ID, 'hpea')", 'setRace(tdFarmerRaceForObjectGen())',
                  'setDefaultActiveAbility("")', 'setNormalAbilities(TD_FARMER_BUILD_ABILITY_ID.toRawCode()',
                  'setStructuresBuilt(tdFarmerBuildMenuRawcodes())', 'setMovementType(MovementType.Fly)',
                  'setFoodCost(tdFarmerFoodCostForObjectGen())'):
        require(token in worker, 'Source builder missing ' + token)
    require('TD_FARMER_MENU_REPAIR_ABILITY_ID' not in worker and '"AHbu' not in worker,
            'Source builder must not attach Human build or repair')
    require('setModelFile' not in worker, 'Source builder must retain inherited hpea model')
    require('..setBuildTime(2 + level)' in objects, 'Source native build time must remain 2+level')
    validate_construction_jass(runtime)


def validate_builder_objects(units, parents):
    require('uF01' in units, 'Missing native builder uF01')
    worker = units['uF01']
    require(parents.get('uF01') == 'hpea', 'Builder must retain hpea parent/model')
    require('umdl' not in worker, 'Builder must retain inherited peasant model')
    require(worker.get('urac') == 'undead', 'Builder race must be undead')
    attached = worker.get('uabi', '').split(',')
    require(attached.count('AUbu') == 1, 'Builder must attach exactly one AUbu')
    require(not {'AHbu', 'Ahrp', 'Prpr'}.intersection(attached), 'Builder must not attach Human build or repair')
    require(worker.get('udaa') == '', 'Builder must explicitly clear default repair')
    require(worker.get('ubui') == 'uA11,uO11,uH11,uD11,uG11', 'Builder must retain five-tower build menu')
    for field, expected in [('umvt', 'fly'), ('umvh', 275.0), ('umvf', 275.0),
                            ('umvs', 522), ('umis', 522), ('umas', 522), ('ufoo', 0), ('ufma', 0)]:
        require(worker.get(field) == expected, f'Builder {field} must remain {expected}')
    for uid in TOWER_IDS:
        require(uid in units, f'Missing tower {uid}')
        tower = units[uid]
        level = int(uid[-1]) if uid[-2] == '1' else 6
        for field, expected, label in [('ubld', 2 + level, 'native build time'), ('urac', 'human', 'tower race'),
                                       ('ufoo', 1, 'population'), ('ubdg', 1, 'building flag'),
                                       ('upat', 'war3mapImported\\TDTower192.tga', 'pathing'),
                                       ('upar', '', 'required terrain'), ('upap', 'unbuildable,unwalkable,water', 'prevented terrain')]:
            require(tower.get(field) == expected, f'{uid}: {label} must remain {expected}')
        family = uid[1]
        upgrade = f'u{family}1{level + 1}' if level < 5 else f'u{family}6A,u{family}6B' if level == 5 else ''
        require(tower.get('uupt') == upgrade, f'{uid}: upgrade chain must remain unchanged')


def validate_construction_jass(script):
    for event in ('CONSTRUCT_START', 'CONSTRUCT_FINISH', 'CONSTRUCT_CANCEL', 'UPGRADE_START', 'UPGRADE_FINISH', 'UPGRADE_CANCEL'):
        require('EVENT_PLAYER_UNIT_' + event in script, f'Missing native construction event {event}')
    for native in ('GetConstructingStructure', 'GetConstructedStructure', 'GetCancelledStructure'):
        require(native + '()' in script, f'Missing native lifecycle structure {native}')


def validate_worker_only_delta(current, baseline):
    """A-only historical contract: two fields added and one attachment changed."""
    require(set(current) == set(baseline), 'A delta changed object tables')
    for kind, before in baseline.items():
        after = current[kind]
        require(list(after) == list(before), 'A delta changed object set/order: ' + kind)
        for code, old in before.items():
            new = after[code]
            require(new.table == old.table and new.identity == old.identity, f'A delta changed parent/table: {kind}/{code}')
            if (kind, code) != ('units', 'uF01'):
                require(new.encoded() == old.encoded(), f'A delta changed unrelated object: {kind}/{code}')
                continue
            added = [('urac', 0, 0), ('udaa', 0, 0)]
            require(not set(added).intersection(old.fields), 'A baseline already contains explicit worker race/default')
            expected_keys = []
            for key in old.fields:
                if key == ('uabi', 0, 0):
                    expected_keys.extend(added)
                expected_keys.append(key)
            require(list(new.fields) == expected_keys, 'A worker field set/order changed')
            old_abilities = old.fields[('uabi', 0, 0)]
            require(old_abilities.value == 'AHbu,Prpr,A108,A109,A117,Geqb,Pcap,Pcol,Pdep', 'A baseline worker attachments changed')
            expected = {'urac': 'undead', 'udaa': '', 'uabi': A_WORKER_ABILITIES}
            for key, field in new.fields.items():
                if key[0] not in expected:
                    require(field == old.fields[key], 'A worker unrelated field changed: ' + key[0])
                    continue
                raw = key[0].encode() + struct.pack('<I', 3) + expected[key[0]].encode() + b'\0' + old_abilities.raw[-4:]
                require(field.kind == 3 and field.value == expected[key[0]] and field.raw == raw,
                        'A worker field value/encoding changed: ' + key[0])


def validate_closed_builder_delta(current, baseline):
    from VerifyGlobalRankingsArtifact import members, normalize_info
    from VerifySemanticIconArtifact import load_objects
    after, before = members(current), members(baseline)
    require(set(after) == set(before), 'A delta changed MPQ resource set')
    for key, (old_name, old) in before.items():
        name, data = after[key]
        require(name == old_name, 'A delta changed resource spelling')
        if name == 'war3map.w3u':
            continue
        if name == 'war3map.w3i':
            require(normalize_info(data) == normalize_info(old), 'A delta changed metadata beyond display timestamps')
        else:
            require(data == old, 'A delta changed unrelated resource or JASS: ' + name)
    validate_worker_only_delta(load_objects(current), load_objects(baseline))
    return len(after)


def main():
    require(len(sys.argv) in (2, 4), __doc__)
    if sys.argv[1] == '--source-only':
        validate_builder_source(*[(ROOT / path).read_text() for path in
                                ('wurst/towers/TDTowerCatalogData.wurst', 'wurst/towers/TDTowerCommonData.wurst',
                                 'wurst/towers/TDTowerObjectGen.wurst', 'wurst/towers/TDTowerRuntime.wurst')])
        print('PASS STATIC SOURCE: native Undead/AUbu worker with no repair; Human towers/native lifecycle preserved.')
        return
    artifact = Mpq(Path(sys.argv[1]).read_bytes())
    data = artifact.extract('war3map.w3u')
    validate_builder_objects(unit_objects(data), unit_parents(data))
    validate_construction_jass(artifact.extract('war3map.j').decode('utf-8'))
    print('PASS ARTIFACT: hpea-model flying Undead/AUbu worker without repair; 35 Human towers retain native 3..8s build time, food/path/upgrades.')
    if len(sys.argv) == 4:
        require(sys.argv[2] == '--baseline-map', 'Expected --baseline-map')
        count = validate_closed_builder_delta(artifact, Mpq(Path(sys.argv[3]).read_bytes()))
        print(f'PASS A-ONLY DELTA: {count} resources; only uF01 urac/udaa/uabi and two display timestamps differ; JASS and all other objects/resources identical.')
    print('NOT TESTED: 1.27a autonomous construction, refund/population timing or native command rendering.')


if __name__ == '__main__':
    main()
