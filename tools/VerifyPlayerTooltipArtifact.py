#!/usr/bin/env python3
"""Check actual packed tooltip text against packed numeric fields and rule matrices.
Usage: python3 tools/VerifyPlayerTooltipArtifact.py ExampleMap.w3x
No game launch; this does not prove native rendering or live ability semantics.
"""
import math
import re
import sys
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ('原生强化', '受控技能', '动态收藏共用命令', '动态模型', '全局补充预算', 'compiletime', 'rawcode', 'getUnreducedAmount', '伤害骰')


def value(fields, name, level=0, column=0):
    return fields[(name, level, column)][1]


def number(text, pattern, expected, label):
    match = re.search(pattern, text)
    require(match is not None, f'{label}: missing {pattern}: {text}')
    require(math.isclose(float(match[1]), expected, abs_tol=.001),
            f'{label}: {match[1]} != {expected}')


def text_check(text, label, max_chars=260):
    plain = re.sub(r'\|c[0-9a-fA-F]{8}|\|r', '', text).replace('|n', '\n')
    require(0 < len(plain) <= max_chars, f'{label}: visible length {len(plain)} > {max_chars}')
    require(not any(word in plain for word in FORBIDDEN), f'{label}: developer wording')


def validate(abilities, units, items):
    checked = 0
    for rawcode in ('A106', 'A114'):
        fields = abilities[rawcode][1]
        for level in range(1, 62):
            text = value(fields, 'aub1', level)
            label = f'{rawcode}/{level}'
            text_check(text, label)
            number(text, r'每秒([\d.]+)伤害', value(fields, 'Spo1', level, 1), label)
            number(text, r'移动速度降低([\d.]+)%', 100 * value(fields, 'Spo2', level, 2), label)
            number(text, r'攻击速度降低([\d.]+)%', 100 * value(fields, 'Spo3', level, 3), label)
            number(text, r'持续([\d.]+)秒', value(fields, 'adur', level), label)
            number(text, r'英雄([\d.]+)秒', value(fields, 'ahdu', level), label)
            checked += 1
    for rawcode in ('A104', 'A113'):
        fields = abilities[rawcode][1]
        for level in range(1, 62):
            text = value(fields, 'aub1', level)
            label = f'{rawcode}/{level}'
            text_check(text, label)
            number(text, r'有([\d.]+)%概率', value(fields, 'Hbh1', level, 1), label)
            number(text, r'追加([\d.]+)伤害', value(fields, 'Hbh3', level, 3), label)
            number(text, r'眩晕([\d.]+)秒', value(fields, 'adur', level), label)
            number(text, r'英雄([\d.]+)秒', value(fields, 'ahdu', level), label)
            require('1.45倍' not in text, f'{label}: unproven native multiplier claim')
            checked += 1
    for rawcode in ('A131', 'A132'):
        fields = abilities[rawcode][1]
        for level in range(1, 42):
            text = value(fields, 'aub1', level)
            label = f'{rawcode}/{level}'
            text_check(text, label)
            number(text, r'冷却([\d.]+)秒', value(fields, 'acdn', level), label)
            require('可自动施放' in text, label)
            if rawcode == 'A132':
                require(all(x in text for x in ('780范围', '每秒造成70伤害', '不受装备射程影响')), label)
            checked += 1
    # 16 skills x 4 qualities; also check all four display slots and locked copies.
    pet_tokens = ('攻击力', '基础攻击', '攻击速度', '冷却缩短', '全队所有塔', '600范围', '护甲降低',
                  '第4次普攻', '不高于30%', '分裂箭', '180范围毒域', '持续6秒', '基础攻击', '450范围', '220范围', '220范围')
    for skill in range(16):
        for quality in range(1, 5):
            variant = skill * 4 + quality - 1
            power = (8 * quality if skill == 0 else .06 * quality if skill in (1, 2, 3, 4)
                     else .08 + .04 * quality if skill in (5, 9) else 2 * quality if skill == 6 else .25 + .15 * quality)
            for slot in range(4):
                for locked in (0, 64):
                    rawcode = f's{slot}{variant + locked:02X}'
                    text = value(abilities[rawcode][1], 'aub1', 1)
                    text_check(text, rawcode)
                    require(pet_tokens[skill] in text, f'{rawcode}: wrong skill text')
                    if skill == 10:
                        number(text, r'造成([\d.]+)伤害', 36 * power, rawcode)
                        require('最多12名' in text and '持续3秒' in text and '不随尸爆进化增伤' in text, rawcode)
                    elif skill == 0:
                        number(text, r'攻击力\+([\d.]+)', power, rawcode)
                    elif skill == 6:
                        number(text, r'护甲降低([\d.]+)', power, rawcode)
                    elif skill == 8:
                        number(text, r'普攻伤害的([\d.]+)%', power * 100, rawcode)
                    elif skill == 15:
                        number(text, r'移动速度降低([\d.]+)%', min(.75, power) * 100, rawcode)
                    else:
                        number(text, r'([\d.]+)%', power * 100, rawcode)
                    checked += 1
    catalog = (ROOT / 'wurst/towers/TDTowerCatalogData.wurst').read_text()
    tower_ids = re.findall(r"public constant int TD_(?:ARCHER|ORC|FOOT|DRYAD|GHOUL)_LEVEL_[A-Z0-9_]+_ID = '(.{4})'", catalog)
    require(len(tower_ids) == 35, 'tower coverage')
    for uid in tower_ids:
        fields = units[uid]
        text = fields['utub']
        text_check(text, uid)
        require(f"攻击：{fields['ua1b'] + fields['ua1d']}至{fields['ua1b'] + fields['ua1d'] * fields['ua1s']}（基础{fields['ua1b']}）" in text, f'{uid}: base/die mismatch')
        require(fields['ua1d'] == 1, f'{uid}: dice contract changed')
        number(text, r'射程：([\d.]+)', fields['ua1r'] - 500, uid)
        require('建在草地' in text if uid[-1] == '1' else '建在草地' not in text, f'{uid}: repeated building instruction')
        checked += 1
    equipment = [fields for uid, fields in items.items() if uid != 'Ibal' and '同塔第3件同名装备' in fields.get('utub', '')]
    require(len(equipment) == 28, f'expected 28 gear texts, got {len(equipment)}')
    for fields in equipment:
        text = fields['utub']
        text_check(text, fields['unam'])
        require('50%' in text and '前3格' in text, fields['unam'])
        checked += 1
    source = (ROOT / 'wurst/items/TDItemData.wurst').read_text()
    ids = dict(re.findall(r"public constant int (TD_ITEM_\w+_ID) = '(.{4})'", source))
    entries = re.findall(r'tdRegisterItem\((TD_ITEM_\w+_ID), TD_ITEM_QUALITY_\w+, "[^"]+", TD_ITEM_EFFECT_(\w+), ([\d.]+), TD_ITEM_EFFECT_(\w+), ([\d.]+)\)', source)
    require(len(entries) == 28, 'item numeric matrix coverage')
    patterns = {
        'ATTACK': (r'攻击 \+([\d.]+)', 1),
        'RANGE': (r'射程 \+([\d.]+)', 1),
        'ATTACK_SPEED': (r'攻速 \+([\d.]+)%', 100),
        'COOLDOWN': (r'冷却时间缩短([\d.]+)%', 100),
        'KILL_GOLD': (r'击杀金币 \+([\d.]+)', 1),
        'ARMOR_SHRED': (r'护甲降低([\d.]+)', 1),
        'EXECUTE': (r'不高于50%的主目标时，追加本次普攻伤害的([\d.]+)%', 100),
        'POISON': (r'每秒([\d.]+)伤害', 1),
        'CONTROL_POWER': (r'眩晕时间提高([\d.]+)%', 100),
        'DROP_BONUS': (r'额外抽取([\d.]+)次', 1),
        'BOSS_DAMAGE': (r'首领主目标时，追加本次普攻伤害的([\d.]+)%', 100),
    }
    for name, primary, first, secondary, second in entries:
        uid = ids[name]
        text = items[uid]['utub']
        for kind, amount in ((primary, first), (secondary, second)):
            if kind == 'NONE':
                continue
            pattern, multiplier = patterns[kind]
            number(text, pattern, round(float(amount) * multiplier), uid)
            if kind == 'RANGE':
                require('上限500' in text, uid)
            elif kind == 'COOLDOWN':
                require('合计上限40%' in text, uid)
            elif kind == 'CONTROL_POWER':
                require('上限60%' in text, uid)
    actions = ('A119', 'A133', 'A109', 'AeEV', 'A130', 'Pcap', 'Pcol', 'Pdep', 'Geqb', 'Gupg') + tuple(f'Pc0{i}' for i in range(8))
    for retired in ('Dsta', 'Pmas', 'Pfor'):
        require(retired not in abilities, f'Removed action {retired} remains')
    for uid in actions:
        require(uid in abilities, f'Missing required action {uid}')
        if uid in abilities:
            for (field, level, _), (_, text) in abilities[uid][1].items():
                if field == 'aub1':
                    text_check(text, f'{uid}/{level}')
                    checked += 1
    for function_id, display_id in (('A103', 'A139'), ('A107', 'A137'), ('A115', 'A138'), ('A110', 'A135'), ('A140', 'A141'), ('AeSL', 'A136')):
        require(function_id in abilities and display_id in abilities, 'missing passive function/display')
        for (field, level, _), (_, text) in abilities[display_id][1].items():
            if field == 'aub1':
                text_check(text, f'{display_id}/{level}')
                require(text == value(abilities[function_id][1], 'aub1', level), f'{display_id}/{level}: hidden function description mismatch')
    for rawcode in ('A101', 'A102', 'A105', 'A111', 'A112', 'AeCM', 'A100', 'A116'):
        require(rawcode in abilities, f'Missing tower skill {rawcode}')
        for (field, level, _), (_, text) in abilities[rawcode][1].items():
            if field == 'aub1':
                text_check(text, f'{rawcode}/{level}')
    for rawcode, chance, multiplier, bonus in (('A102', 25, 2.2, 18), ('A112', 25, 2.64, 21.6)):
        text = value(abilities[rawcode][1], 'aub1', 1)
        number(text, r'(?:有)?([\d.]+)%概率', chance, rawcode)
        number(text, r'造成([\d.]+)倍伤害', multiplier, rawcode)
        number(text, r'(?:追加|附加)([\d.]+)(?:点)?伤害', bonus, rawcode)
    cultivation = value(abilities['Pc06'][1], 'aub1', 1)
    require(all(x in cultivation for x in ('不退石', '共鸣锁定', '永久删除', '不退球和已用材料', '1洗练石', '2%', '1开栏石', '先召回')), 'cultivation risk/cost missing')
    descriptions = [value(abilities[f'Pc0{i}'][1], 'aub1', 1) for i in range(8)]
    require(len(set(descriptions)) == 8, 'collection commands reuse generic description')
    ground = value(abilities['Gupg'][1], 'aub1', 1)
    require(all(x in ground for x in ('本路', '144范围', '每3件必得1件', '高一品质', '可不同名', '每次只升一级', '对应品质堆', '本次不再参与升级', '余1至2件原地保留')), 'ground craft rule missing')
    require(not any(x in ground for x in ('65%', '失败', '继续合成至紫')), 'ground craft old rule remains')
    craft = value(abilities['A119'][1], 'aub1', 1)
    require(all(x in craft for x in ('3件必成', '65%', '失败时材料全部消失', '最高紫装')), 'backpack craft risks missing')
    require('不返还' in value(abilities['A133'][1], 'aub1', 1), 'sale evolution limit missing')
    for uid in ('A116',):
        for level in (1, 2):
            text = value(abilities[uid][1], 'aub1', level)
            require('不高于25%' in text and '180范围' in text, 'corpse explosion trigger mismatch')
    return checked


def main():
    require(len(sys.argv) == 2, __doc__)
    mpq = Mpq(Path(sys.argv[1]).read_bytes())
    count = validate(ability_objects(mpq.extract('war3map.w3a')), unit_objects(mpq.extract('war3map.w3u')), unit_objects(mpq.extract('war3map.w3t')))
    print(f'PASS: {count} packaged player tooltip instances checked against numeric fields/rules; length and developer-language checks passed.')


if __name__ == '__main__':
    main()
