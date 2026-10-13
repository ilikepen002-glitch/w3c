#!/usr/bin/env python3
"""Focused 40-equipment aura/specialization gate on actual W3A/W3H/JASS.
Reuse project MPQ/object readers. No map writing or in-game claim.
"""
from pathlib import Path
import argparse
import math
from GenerateTowerTerrainMask import Mpq
from VerifySemanticIconArtifact import parse_objects
from VerifyEquipmentAbilityArtifact import ability_objects, require, verify_current_equipment_abilities


def field(obj, name, level=0, column=0):
    entry = obj.fields.get((name, level, column))
    return None if entry is None else entry.value


def near(actual, expected, label):
    require(isinstance(actual, (int, float)) and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6),
            f'{label}: {actual!r}, expected {expected}')


def named(objects, name):
    matches = [(rawcode, obj) for rawcode, obj in objects.items() if field(obj, 'anam') == name]
    require(len(matches) == 1, f'{name}: expected exactly one object, found {len(matches)}')
    return matches[0]


def verify(objects, buffs):
    # The finite real-source identity/rank set, never hundreds of total-percent Buffs.
    identities = {
        '白虎战吼': (1, 2), '统帅光环': (1, 2), '统御攻击光环': (1, 2, 3, 4),
        '疾风攻速光环': (1, 2, 3, 4), '灵感冷却光环': (4,), '裂甲普攻光环': (4,),
        '寒霜领域': (1, 2, 3, 4),
        '缓速藤蔓': (1, 2), '毒镖移动缓速': (1, 2), '精灵霜箭': (1, 2, 3, 4), '精灵风缚': (1, 2, 3, 4),
    }
    if any(field(obj, 'fnam') == '精灵减击 1' for obj in buffs.values()):
        identities['精灵减击'] = (1,)
        require(not any(field(obj, 'fnam') in {f'{name} {rank}' for name in ('精灵统御', '精灵迟滞') for rank in range(1, 5)} for obj in buffs.values()), 'Retired spirit aura Buffs remain')
    else:
        identities.update({'精灵统御': (1, 2, 3, 4), '精灵迟滞': (1, 2, 3, 4)})
    expected = {f'{name} {rank}' for name, ranks in identities.items() for rank in ranks}
    expected |= {'剑圣战意 1/4', '剑圣战意 2/4', '剑圣战意 3/4', '剑圣战意 爆发', '森蚀 1/3', '森蚀 2/3'}
    known_names = set()
    for rawcode, obj in buffs.items():
        name = field(obj, 'fnam')
        if name not in expected:
            continue
        require(name not in known_names, f'Duplicate real source Buff: {name}')
        known_names.add(name)
        require(obj.identity[:4] == b'Basl', f'{rawcode}: real state Buff must inherit Basl')
        require(bool(field(obj, 'fart')), f'{rawcode}: missing real native status icon')
        tooltip = field(obj, 'fube')
        require(isinstance(tooltip, str) and tooltip, f'{rawcode}: missing status tooltip')
        from VerifyPlayerTooltipArtifact import text_check
        text_check(tooltip, f'{rawcode}: status tooltip', max_chars=220)
        dummy_id, dummy = named(objects, 'Aura Dummy: ' + name)
        require(dummy.identity[:4] == b'Aasl', f'{dummy_id}: dummy aura parent')
        require(field(dummy, 'atar', 1) == 'self', f'{dummy_id}: status dummy must be self-only')
        near(field(dummy, 'Slo1', 1, 1), 0.0, dummy_id + '.movement')
        require(field(dummy, 'abuf', 1) == rawcode, f'{dummy_id}: mismatched real Buff ID')
    require(known_names == expected, f'Real Buff set mismatch: missing {expected-known_names}')

    for name, parent, bonus_field, powers, source_ids in (
        ('白虎', b'AEar', 'Ear1', (0.18, 0.216), ('A101','A111')),
        ('统帅', b'AIcd', 'Cac1', (0.16, 0.192), ('A105','AeCM')),
    ):
        for rank, power in enumerate(powers, 1):
            rawcode, obj = named(objects, name + '百分比载体 ' + str(rank))
            require(obj.identity[:4] == parent, f'{rawcode}: wrong native percentage parent')
            require(field(obj, 'atar', 1) == 'self', f'{rawcode}: must not range-double-apply')
            near(field(obj, bonus_field, 1, 1), power, rawcode + '.percent')
            near(field(obj, 'Ear4', 1, 4), 0, rawcode + '.flat-flag')
            near(field(obj, 'aare', 1), 0, rawcode + '.radius')
            state_name = ('白虎战吼' if name == '白虎' else '统帅光环') + ' ' + str(rank)
            real_id = [key for key, value in buffs.items() if field(value, 'fnam') == state_name]
            require(field(obj, 'abuf', 1) == real_id[0], f'{rawcode}: wrong highest-rank Buff')
        for source_id in source_ids:
            obj = objects[source_id]
            near(field(obj, bonus_field, 1, 1), 0.0, source_id + '.source-bonus')
            require(field(obj, 'atar', 1) == 'self' and field(obj, 'abuf', 1) == '',
                    source_id + ': old independent range/Buff source survived')

    for rawcode in ('A104','A113'):
        obj = objects[rawcode]
        require(obj.identity[:4] == b'AHbh', rawcode + ': bash parent changed')
        for level in range(1, 62):
            near(field(obj, 'Hbh1', level, 1), 0.0, rawcode+'.chance')
            near(field(obj, 'Hbh2', level, 2), 1.0, rawcode+'.multiplier')
            near(field(obj, 'Hbh3', level, 3), 0.0, rawcode+'.bonus')
    for name, levels, duration in (
        ('盾击短晕', 61, lambda level: min(0.90, 0.60*(1+(level-1)/100))),
        ('首领盾击短晕', 1, lambda level: 0.25),
    ):
        rawcode, obj = named(objects, name)
        require(obj.identity[:4] == b'AHtb', rawcode + ': zero-damage caster parent')
        require(field(obj, 'alev') == levels, rawcode + ': stun level count')
        for level in range(1, levels+1):
            near(field(obj, 'Htb1', level, 1), 0.0, rawcode+'.damage')
            near(field(obj, 'adur', level), duration(level), rawcode+'.normal-duration')
            near(field(obj, 'ahdu', level), duration(level), rawcode+'.hero-duration')
    rawcode, obj = named(objects, '剑圣战意攻速载体')
    require(obj.identity[:4] == b'AIsx', rawcode + ': must inherit safe object alias, never AIas')
    near(field(obj, 'Isx1', 1, 1), 0.20, rawcode+'.attack-speed')

    # Movement-only extraction: preserve native poison damage/attack slow/durations.
    for rawcode, dps in (('A106', 12.0), ('A114', 14.4)):
        obj = objects[rawcode]
        require(obj.identity[:4] == b'Aspo', rawcode + ': poison parent')
        for level in range(1,62):
            near(field(obj, 'Spo1', level, 1), dps, rawcode+'.native-poison')
            near(field(obj, 'Spo2', level, 2), 0.0, rawcode+'.native-move')
            near(field(obj, 'Spo3', level, 3), 0.16, rawcode+'.native-attack-slow')
            near(field(obj, 'adur', level), 5.0, rawcode+'.normal-duration')
            near(field(obj, 'ahdu', level), 1.0, rawcode+'.hero-duration')
            require(field(obj, 'abuf', level) == 'Bspo,Bssd', rawcode + ': poison buffs')
    for rawcode in ('A110','A140','AeSL'):
        for level in range(1,62):
            near(field(objects[rawcode], 'Slo1', level, 1), 0.0, rawcode+'.native-move')
    return {'real_buff_count': len(expected), 'native_percent_carriers':4, 'shield_levels':62,
            'native_bash_disabled_levels':122, 'safe_war_speed_parent':'AIsx'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map',type=Path)
    args=parser.parse_args()
    artifact=Mpq(args.map.read_bytes())
    data=artifact.extract('war3map.w3a')
    verify_current_equipment_abilities(ability_objects(data))
    report=verify(parse_objects(data,True),parse_objects(artifact.extract('war3map.w3h'),False))
    script=artifact.extract('war3map.j').decode('utf-8')
    for symbol in ('tdRefreshEnemyMoveSpeed','tdStartInventoryCraft','tdStartGroundCraft','tdSetupAuraRuntime','tdSetupEquipmentSpecialRuntime','tdTryEquipmentShieldProc','tdResolveSpecialExplosion','tdEquipmentArcherAdditionalArrows'):
        require(symbol in script, 'Packed script missing live entry: '+symbol)
    print('PASS PACKED EQUIPMENT AURA/SPECIAL:',report)
    print('NOT TESTED: native Buff projection, percentage stacking, accepted order actually stunning, gameplay/performance')
if __name__=='__main__': main()
