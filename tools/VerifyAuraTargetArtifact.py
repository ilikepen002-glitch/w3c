#!/usr/bin/env python3
"""Replay actual packaged aura target routing with bounded engine fixtures.

This reads the supplied MPQ and executes its production JASS. Unit ownership,
position, inventory, native ability storage and collection natives are modeled;
native Buff projection/target masks and real attack timing are NOT emulated.
No compilation, map editing or Warcraft launch occurs.
"""
import argparse
import hashlib
import json
from pathlib import Path

from GenerateTowerTerrainMask import Mpq
from ReadEquipmentCatalog import catalog
from VerifyEquipmentAbilityArtifact import require
from VerifyEquipmentCombatReplay import EquipmentTrialRuntime, close
from VerifyEquipmentAuraSpecialArtifact import field, named
from VerifySemanticIconArtifact import parse_objects
from VerifyTowerUpgradeArtifact import rawcode

ROOT = Path(__file__).resolve().parents[1]
AURA_IDENTITIES = {'ATTACK': 3, 'ATTACK_SPEED': 4, 'COOLDOWN': 5,
                   'ARMOR_ON_HIT': 6, 'ENEMY_SLOW': 7}


class AuraRuntime(EquipmentTrialRuntime):
    def native(self, name, args):
        if name == 'SetUnitAcquireRange':
            self.units[args[0]]['acquireRange'] = args[1]
            return True, None
        return super().native(name, args)


def fixture(script):
    r = AuraRuntime(script)
    r.initialize_match()
    template = dict(r.units[101])
    for handle, owner, tower in ((101, 0, True), (103, 0, True),
                                  (104, 1, True), (105, 4, False),
                                  (106, 4, False)):
        r.units[handle] = {**template, 'owner': owner,
                           'type': rawcode('uA11' if tower else 'uW01'),
                           'x': 0.0, 'y': 0.0, 'abilities': {}, 'inventory': {},
                           'userdata': 10000 if handle == 106 else 0}
        r.invoke('tdAuraRegisterTarget', handle, tower)
    return r


def offer(r, target, *, distance=0.0, eligible=True):
    record = r.invoke('tdAuraTargetFor', target)
    aggregate = r.globals['TDAuraTarget_effective'][record]
    r.invoke('TDAuraAggregate_clear', aggregate)
    tower = r.globals['TDAuraTarget_tower'][record]
    lane = r.units[target]['owner'] if tower else r.units[target]['userdata'] // 10000
    r.invoke('tdAuraOfferSource', record, 101, aggregate, lane, distance, 0.0,
             False, eligible)
    return aggregate


def expect_only(r, aggregate, identity, rank, power, label):
    for current in range(1, 14):
        expected_rank = rank if current == identity else 0
        require(r.invoke('TDAuraAggregate_rank', aggregate, current) == expected_rank,
                f'{label}: wrong target/identity rank for {current}')
        close(r.invoke('TDAuraAggregate_power', aggregate, current),
              power if current == identity else 0.0, label + f' identity {current}')


def verify_equipment_targets(script):
    r = fixture(script)
    count = 0
    for equipment in catalog():
        if equipment.aura == 'NONE':
            continue
        identity = AURA_IDENTITIES[equipment.aura]
        r.units[101]['inventory'] = {0: 4242}
        r.inventory_items[4242] = rawcode(equipment.rawcode)
        enemy_effect = equipment.aura == 'ENEMY_SLOW'
        cases = (
            ('source tower', 101, 0.0, True, not enemy_effect),
            ('own tower boundary', 103, equipment.aura_radius, True, not enemy_effect),
            ('own tower outside', 103, equipment.aura_radius + 0.1, True, False),
            ('ally tower', 104, 0.0, True, False),
            ('lane enemy boundary', 105, equipment.aura_radius, True, enemy_effect),
            ('lane enemy outside', 105, equipment.aura_radius + 0.1, True, False),
            ('other lane enemy', 106, 0.0, True, False),
            ('own tower no cooldown skill', 103, 0.0, False,
             not enemy_effect and equipment.aura != 'COOLDOWN'),
        )
        for label, target, distance, eligible, accepted in cases:
            aggregate = offer(r, target, distance=distance, eligible=eligible)
            expect_only(r, aggregate, identity if accepted else 0,
                        equipment.quality if accepted else 0,
                        equipment.aura_value if accepted else 0.0,
                        equipment.name + ': ' + label)
            count += 1
    return count


def verify_wind_application(script):
    r = fixture(script)
    r.units[101]['inventory'] = {0: 4242}
    r.inventory_items[4242] = rawcode('iW07')
    carrier = r.invoke('tdAuraRankCarrier', 4, 1)
    require(carrier != 0, 'Wind status carrier is missing')
    for target, speed_level in ((101, 4), (103, 4), (104, 0), (105, 0)):
        offer(r, target, distance=100.0 if target != 101 else 0.0)
        record = r.invoke('tdAuraTargetFor', target)
        if target == 105:
            r.invoke('tdAuraSyncBuffs', record)
        else:
            r.invoke('tdAuraApply', record)
        abilities = r.units[target]['abilities']
        require(abilities.get(rawcode('A129'), 0) == speed_level,
                f'Wind numeric attack-speed carrier routed incorrectly to {target}')
        require((carrier in abilities) == (speed_level > 0),
                f'Wind status carrier routed incorrectly to {target}')
    # The real clear/sync path retires both markers and speed when coverage ends.
    offer(r, 103, distance=350.1)
    r.invoke('tdAuraApply', r.invoke('tdAuraTargetFor', 103))
    require(carrier not in r.units[103]['abilities'] and
            rawcode('A129') not in r.units[103]['abilities'],
            'Wind removal retained numeric or displayed carrier')
    return {'own_towers_A129_level': 4, 'ally_and_enemy_A129_level': 0,
            'status_carrier': carrier, 'out_of_range_removal': True}


def verify_tower_targets(script):
    r = fixture(script)
    count = 0
    for ability, identity, rank, power, enemy in (
            ('A101', 1, 1, .18, False), ('A111', 1, 2, .216, False),
            ('A105', 2, 1, .16, False), ('AeCM', 2, 2, .192, False),
            ('A110', 10, 1, .18, True), ('A140', 10, 1, .18, True),
            ('AeSL', 10, 2, .216, True)):
        r.units[101]['abilities'] = {rawcode(ability): 1}
        for target in (101, 103, 104, 105, 106):
            accepted = target == 105 if enemy else target in (101, 103)
            aggregate = offer(r, target, distance=0.0)
            expect_only(r, aggregate, identity if accepted else 0,
                        rank if accepted else 0, power if accepted else 0.0,
                        ability + ': target ' + str(target))
            count += 1
    return count


def verify_pet_targets(script):
    r = fixture(script)
    final_catalog = r.globals.get('TDPetData_TD_PET_SKILL_COUNT') == 49
    pet = r.invoke('new_TDPet', 0, 1 if final_catalog else 0, 1)
    require(r.invoke('tdPetStore', 0, pet), 'Fixture pet registration failed')
    r.globals['TDPet_host'][pet] = 101
    r.globals['TDPet_level'][pet] = 10
    r.invoke('TDPet_setSkill', pet, 0, 0 if 'tdPetSkillIsAttackPassive' in r.functions else 19 if final_catalog else 0, 1)
    if 'tdPetApplyAttackDebuffs' in r.functions:
        require(not r.invoke('tdPetSkillDefined', 4), 'Retired command-aura skill is selectable')
        r.invoke('TDPet_setSkill', pet, 1, 4, 2)
        require(r.invoke('TDPet_skillAt', pet, 1) != 4, 'Retired command-aura slot was accepted')
        r.invoke('TDPet_setSkill', pet, 1, 5, 2)
        require(r.invoke('TDPet_skillAt', pet, 1) == 5, 'Combined attack-speed fixture was rejected')
        # The replacement attack passive has no spatial emitter. Replay the
        # same former aura routes and require every aggregate identity zero.
        for target in (101, 103, 104, 105, 106):
            aggregate = offer(r, target, distance=0.0 if target == 101 else 600.0)
            expect_only(r, aggregate, 0, 0, 0.0, 'Retired pet aura target ' + str(target))
        aggregate = offer(r, 105, distance=600.1)
        expect_only(r, aggregate, 0, 0, 0.0, 'Retired pet aura outside boundary')
        require('tdPet' not in '\n'.join(r.functions['tdAuraOfferSource'][1]),
                'Spatial aura dispatcher still depends on pets')
        return 6
    r.invoke('TDPet_setSkill', pet, 1, 4, 2)
    r.invoke('TDPet_setSkill', pet, 2, 5, 2)
    require(r.invoke('tdPetBindingValid', pet, 101, 0), 'Fixture host is not valid')
    require(r.invoke('tdPetSkillRank', pet, 4) == 2 and
            r.invoke('tdPetSkillRank', pet, 5) == 2, 'Fixture aura slots are not unlocked')
    for target, identity, power in ((101, 8, .12), (103, 0, 0.0),
                                    (104, 0, 0.0), (105, 9, .16), (106, 0, 0.0)):
        aggregate = offer(r, target, distance=0.0 if target == 101 else 600.0)
        expect_only(r, aggregate, identity, 2 if identity else 0, power,
                    'Pet aura target ' + str(target))
    aggregate = offer(r, 105, distance=600.1)
    expect_only(r, aggregate, 0, 0, 0.0, 'Pet enemy aura outside boundary')
    return 6


def verify(script):
    return {'equipment_target_cases': verify_equipment_targets(script),
            'tower_target_cases': verify_tower_targets(script),
            'pet_target_cases': verify_pet_targets(script),
            'wind_application': verify_wind_application(script)}


def verify_hidden_carriers(objects):
    """Require explicit legacy button hiding, never infer hiding from aite=1."""
    carriers = []
    for label in ('白虎', '统帅'):
        for rank in (1, 2):
            code, obj = named(objects, label + '百分比载体 ' + str(rank))
            require(field(obj, 'abpx') == 0 and field(obj, 'abpy') == -11,
                    code + ': internal percentage carrier button is not hidden')
            require(field(obj, 'atar', 1) == 'self' and field(obj, 'abuf', 1),
                    code + ': hiding must preserve the self target and real Buff')
            carriers.append(code)
    for code in ('A101', 'A111', 'A105', 'AeCM'):
        obj = objects[code]
        require(field(obj, 'abpx') == 1 and field(obj, 'abpy') == 1 and
                field(obj, 'aart') and field(obj, 'atp1', 1),
                code + ': real aura source button must remain visible and named')
    return carriers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--require-hidden-carriers', action='store_true',
                        help='Gate a rebuilt candidate; an old published map must fail')
    args = parser.parse_args()
    data = args.map.read_bytes()
    artifact = Mpq(data)
    script = artifact.extract('war3map.j').decode('utf-8')
    result = verify(script)
    if args.require_hidden_carriers:
        result['hidden_percentage_carriers'] = verify_hidden_carriers(
            parse_objects(artifact.extract('war3map.w3a'), True))
    result['map_sha256'] = hashlib.sha256(data).hexdigest()
    print('PASS PACKAGED AURA TARGET ROUTING: ' + json.dumps(result, ensure_ascii=False))
    print('NOT TESTED: native status-bar Buff projection, native target masks, '
          'real attack timing or user gameplay reproduction.')


if __name__ == '__main__':
    main()
