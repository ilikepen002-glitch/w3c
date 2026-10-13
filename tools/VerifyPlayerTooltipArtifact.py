#!/usr/bin/env python3
"""Check actual packed tooltip text against packed numeric fields and rule matrices.
Usage: python3 tools/VerifyPlayerTooltipArtifact.py ExampleMap.w3x
No game launch; this does not prove native rendering or live ability semantics.
"""
import argparse
import hashlib
import math
import re
import sys
from pathlib import Path
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyTowerPlacementArtifact import unit_objects

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ('原生强化', '受控技能', '动态收藏共用命令', '动态模型', '全局补充预算', 'compiletime', 'rawcode', 'getUnreducedAmount', '伤害骰', '静态基础', '原生百分比', '载体上限', '本击事件', '回灌', '圈内快照', '同身份', '合法塔', '标称')


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


PROFILES = ('legacy72', 'legacy009', 'current40')
LEGACY_ITEM_SOURCE_SHA = {
    'legacy72': '2c3d8a35182bf573acbbca6e5de86a776cb77302a5b7425a947b5a5f873e89e4',
    'legacy009': '7a2d45e5a650b8dfc798376e360f95a75f8727cc578e4b03afe6dce2646c3b51',
}


def scalar(root, owner, name):
    text = (root / 'wurst' / owner).read_text()
    match = re.search(r'public function ' + re.escape(name) + r'\(\) returns real\n(?:\t//[^\n]*\n)*\treturn ([\d.]+)\n', text)
    require(match is not None, 'Missing source scalar: ' + name)
    return float(match[1])


def verify_current_items(items, root=ROOT, *, shared_active_cooldown=False):
    """Every packed item numeric/aura line consumes the single current catalog."""
    from ReadEquipmentCatalog import catalog
    entries = catalog(root)
    expected = {entry.rawcode for entry in entries}
    actual = {uid for uid in items if re.fullmatch(r'i[WGBP]\d\d', uid)}
    require(actual == expected, 'current40 equipment identity set mismatch')
    patterns = {
        'ATTACK': (r'攻击 \+([\d.]+)', 1),
        'RANGE': (r'射程 \+([\d.]+)', 1),
        'ATTACK_SPEED': (r'攻速 \+([\d.]+)%', 100),
        'COOLDOWN': (r'冷却时间缩短([\d.]+)%', 100),
        'KILL_GOLD': (r'精英(?:击杀金币)? \+([\d.]+)', 1),
        'ARMOR_SHRED': (r'(?:护甲降低|普攻破甲)([\d.]+)', 1),
        'EXECUTE': (r'主目标生命不高于50%时，普攻追加([\d.]+)%', 100),
        'POISON': (r'每秒([\d.]+)伤害', 1),
        'CONTROL_POWER': (r'眩晕时间提高([\d.]+)%', 100),
        'DROP_BONUS': (r'额外抽取([\d.]+)次', 1),
        'BOSS_DAMAGE': (r'首领或金币试炼主目标(?:追加|普攻 \+)([\d.]+)%', 100),
    }
    aura_patterns = {
        'ATTACK': (r'(?:增加基础攻击的|基础攻击 \+)([\d.]+)%', 100),
        'ATTACK_SPEED': (r'攻速光环：攻击速度 \+([\d.]+)%', 100),
        'COOLDOWN': (r'冷却光环：嗜血、剑刃风暴及精灵主动冷却缩短([\d.]+)%', 100),
        'ARMOR_ON_HIT': (r'普攻主目标破甲([\d.]+)', 1),
        'ENEMY_SLOW': (r'本路敌人移动速度降低([\d.]+)%', 100),
    }
    if shared_active_cooldown:
        aura_patterns['COOLDOWN'] = (r'冷却光环：主动技能冷却缩短([\d.]+)%（(?:包括附身精灵的主动技能|含附身精灵)）', 100)
    for entry in entries:
        fields = items[entry.rawcode]
        text = fields.get('utub', '')
        label = entry.rawcode
        name = re.sub(r'\|c[0-9a-fA-F]{8}|\|r', '', fields.get('unam', ''))
        require(name == entry.name, label + ': config name mismatch')
        text_check(text, label, max_chars=320)
        require(fields.get('ides') == text, label + ': ground selection description must match equipment tooltip')
        for phrase in ('塔可装备', '同塔同名限1件'):
            require(phrase in text, label + ': current crafting/admission rule missing: ' + phrase)
        require('同塔第3件同名装备' not in text and '65%' not in text,
                label + ': retired equipment rule')
        for kind, amount in ((entry.primary, entry.primary_value), (entry.secondary, entry.secondary_value)):
            if kind == 'NONE':
                continue
            pattern, multiplier = patterns[kind]
            number(text, pattern, int(amount * multiplier + .5), label)
            if kind == 'KILL_GOLD':
                number(text, r'普通 \+([\d.]+)', int(amount / 2), label)
                require('首领无效' in text, label + ': Boss excluded from bonus gold')
            if kind == 'RANGE':
                require('上限500' in text, label + ': range cap')
                require('仅远程塔生效' in text, label + ': ranged tower eligibility')
            elif kind == 'CONTROL_POWER':
                require('上限60%' in text, label + ': control cap')
            elif kind in ('EXECUTE', 'BOSS_DAMAGE'):
                require((((('仅主目标普攻' in text and '半血与首领追加比例相加' in text) or
                           ('主目标生命不高于50%时，普攻追加' in text and '与首领追加相加' in text)) and
                          '法术、副箭、精灵伤害不触发；普攻击杀不追加' in text) or
                         (kind == 'BOSS_DAMAGE' and '同类最高，半血追加相加' in text and
                          '法术、副箭、精灵及击杀不触发' in text)),
                        label + ': additional damage eligibility')
        if entry.aura != 'NONE':
            pattern, multiplier = aura_patterns[entry.aura]
            number(text, pattern, int(entry.aura_value * multiplier + .5), label)
            number(text, r'光环范围([\d.]+)', entry.aura_radius, label)
            require(any(p in text for p in ('同名取最高等级，异名可叠加', '同名取最高等级，异名叠加', '同名取最高，异名叠加')), label + ': aura stacking rule')
            require('不受装备射程影响' in text or re.search(r'光环范围[\d.]+（固定）', text), label + ': aura radius ownership')
            if entry.aura == 'ENEMY_SLOW':
                require('合计上限75%' in text, label + ': slow cap')
            else:
                require('本路己方塔，含自身' in text, label + ': aura owner/lane')
            if entry.aura == 'COOLDOWN':
                require('合计上限40%' in text and any(p in text for p in ('不重置进行中的冷却', '不重置当前冷却', '不重置冷却')), label + ': cooldown cap/lifecycle')
            if entry.aura == 'ATTACK_SPEED':
                require('与装备攻速合计上限120%' in text, label + ': attack-speed cap')
        if entry.specialization != 'NONE':
            config = 'items/TDItemCatalogConfig.wurst'
            if entry.specialization == 'WAR_INTENT':
                number(text, r'攻速 \+([\d.]+)%', 100 * scalar(root, config, 'tdConfiguredWarAttackSpeed'), label)
                number(text, r'持续([\d.]+)秒', scalar(root, config, 'tdConfiguredWarDuration'), label)
                require(('同目标4次普攻命中' in text and '期间不叠层、不续时' in text) or
                        ('剑圣同目标4次普攻' in text and '不叠层不续时' in text), label + ': war-intent lifecycle')
                number(text, r'停攻([\d.]+)秒', scalar(root, config, 'tdConfiguredWarInactivity'), label)
            elif entry.specialization == 'ARCHER_ARROW':
                require('增加1支副箭' in text, label + ': arrow count')
            elif entry.specialization in ('CORPSE_BURST', 'POISON_BURST'):
                count, radius = (6, 180) if entry.specialization == 'CORPSE_BURST' else (3, 220)
                number(text, r'每([\d.]+)次普攻命中', count, label)
                number(text, r'本次普攻伤害的([\d.]+)%', 50, label)
                number(text, r'目标周围([\d.]+)范围', radius, label)
                require('最多4名敌人' in text and '副箭、毒伤不计' in text,
                        label + ': burst eligibility/cap')
                if entry.specialization == 'POISON_BURST':
                    require(('须同一目标' in text or '同目标；换目标' in text) and '换目标' in text, label + ': poison target reset')
                    number(text, r'停攻([\d.]+)秒', scalar(root, config, 'tdConfiguredPoisonBurstInactivity'), label)
            elif entry.specialization == 'SHIELD_SPREAD':
                require('目标周围200范围' in text and '最多2名非首领' in text and '不受额外眩晕' in text,
                        label + ': shield spread/real Boss rule')
                number(text, r'首领只受破甲([\d.]+)', scalar(root, config, 'tdConfiguredShieldBossArmor'), label)
                # This duration belongs to the specialization, not the personal control line.
                number(text, r'首领只受破甲[\d.]+，持续([\d.]+)秒', scalar(root, config, 'tdConfiguredShieldBossArmorDuration'), label)
    return len(entries)


def verify_current_pet_descriptions(abilities, root):
    """Four fixed role slots use quality levels, not the retired 16×4 ID layout."""
    from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
    from VerifyPetUIArtifact import verify_phase_one_slots
    verify_phase_one_slots(abilities)
    class Descriptions(SourceScalarEvaluator):
        def call(self, name, args, fields=None):
            if name == 'tdTooltipNumber':
                # Positive Wurst R2S display precision, followed by its zero trim.
                return format(args[0], '.3f').rstrip('0').rstrip('.')
            return super().call(name, args, fields)
    evaluator = Descriptions(read_sources(root))
    count = evaluator.constant('TD_PET_SKILL_COUNT')
    require(count == 49, 'Unreviewed current skill catalogue')
    checked = 0
    for code, (_, fields) in abilities.items():
        if not re.fullmatch(r's[0-3][0-9A-F]{2}', code):
            continue
        slot, variant = int(code[1]), int(code[2:], 16)
        empty = variant == count * 2
        skill, locked = variant % count, variant >= count and not empty
        for quality in range(1, 2 if empty else 5):
            text = value(fields, 'aub1', quality)
            text_check(text, code + '/' + str(quality))
            if not empty:
                expected = evaluator.call('tdPetSkillDescriptionById', [skill, quality])
                if locked:
                    expected = f'技能已获得；共鸣锁定，完成本路第{4 if slot == 2 else 8}波解锁。|n' + expected
                if slot == 3:
                    expected += '|n冷却就绪后，下一次有效普攻自动释放。当前状态见精灵信息行。'
                require(text == expected, code + '/' + str(quality) + ': current skill description/numeric mismatch')
            checked += 1
    return checked


def validate(abilities, units, items, *, profile='current40', source_root=None, shared_active_cooldown=False, current_pet_ui=False):
    require(profile in PROFILES, 'Unknown player tooltip profile')
    require(profile == 'current40' or source_root is not None,
            'Historical tooltip profile requires matching frozen source_root')
    root = ROOT if source_root is None else Path(source_root)
    current = profile == 'current40'
    source = (root / 'wurst/items/TDItemData.wurst').read_text()
    if not current:
        require(hashlib.sha256(source.encode()).hexdigest() == LEGACY_ITEM_SOURCE_SHA[profile],
                profile + ': frozen item source identity mismatch')
        gear = [uid for uid, fields in items.items() if uid != 'Ibal' and '同塔第3件同名装备' in fields.get('utub', '')]
        require(len(gear) == 28, f'expected 28 gear texts, got {len(gear)}')
    require(not shared_active_cooldown or current, 'Shared active cooldown requires current40 profile')
    require(not current_pet_ui or current, 'Current pet UI requires current40 profile')
    checked = verify_current_items(items, root, shared_active_cooldown=shared_active_cooldown) if current else 0
    for rawcode in ('A106', 'A114'):
        fields = abilities[rawcode][1]
        for level in range(1, 62):
            text = value(fields, 'aub1', level)
            label = f'{rawcode}/{level}'
            text_check(text, label)
            number(text, r'每秒([\d.]+)伤害', value(fields, 'Spo1', level, 1), label)
            if current:
                require(value(fields, 'Spo2', level, 2) == 0.0, label + ': native poison move double application')
                base = 1 - scalar(root, 'towers/TDTowerCommonData.wurst', 'tdDryadSlowFactor')
                number(text, r'移动速度降低([\d.]+)%', 100 * min(.70, base * (1 + (level - 1) / 100)), label)
            else:
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
            if current:
                for field, column, expected in (('Hbh1', 1, 0.0), ('Hbh2', 2, 1.0), ('Hbh3', 3, 0.0), ('adur', 0, 0.0), ('ahdu', 0, 0.0)):
                    require(value(fields, field, level, column) == expected, label + ': disabled native bash ' + field)
                common = 'towers/TDTowerCommonData.wurst'
                config = 'items/TDItemCatalogConfig.wurst'
                chance = 100 * scalar(root, common, 'tdFootmanBashChance') * (1.2 if rawcode == 'A113' else 1)
                number(text, r'有([\d.]+)%概率', chance, label)
                duration = min(scalar(root, config, 'tdConfiguredShieldNormalStunCap'),
                               scalar(root, config, 'tdConfiguredShieldNormalStunDuration') * (1 + (level - 1) / 100))
                number(text, r'普通敌人眩晕([\d.]+)秒', duration, label)
                number(text, r'首领眩晕([\d.]+)秒', scalar(root, config, 'tdConfiguredShieldBossStunDuration'), label)
                require('保护期间不受任何塔的盾击' in text and '不造成额外伤害' in text,
                        label + ': shared shield window/failed cast')
            else:
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
                require(all(x in text for x in ('780范围', '每秒造成350伤害', '不受装备射程影响')), label)
            checked += 1
    from VerifyPetUIArtifact import is_phase_one_ui
    if current and is_phase_one_ui(abilities):
        checked += verify_current_pet_descriptions(abilities, root)
    else:
        # 16 skills x 4 qualities; also check all four display slots and locked copies.
        pet_tokens = ('攻击力', '基础攻击', '攻击速度', '冷却缩短', '全队所有塔', '600范围', '护甲降低',
                      '第4次普攻', '不高于30%', '分裂箭', '180范围毒域', '持续6秒', '基础攻击', '450范围', '220范围', '220范围')
        if current:
            pet_tokens = pet_tokens[:4] + ('仅附身塔',) + pet_tokens[5:]
        for skill in range(16):
            for quality in range(1, 5):
                variant = skill * 4 + quality - 1
                power = (40 * quality if skill == 0 else .06 * quality if skill in (1, 2, 3, 4)
                         else .08 + .04 * quality if skill in (5, 9) else 2 * quality if skill == 6 else .25 + .15 * quality)
                for slot in range(4):
                    for locked in (0, 64):
                        rawcode = f's{slot}{variant + locked:02X}'
                        text = value(abilities[rawcode][1], 'aub1', 1)
                        text_check(text, rawcode)
                        require(pet_tokens[skill] in text, f'{rawcode}: wrong skill text')
                        if skill == 10:
                            number(text, r'造成([\d.]+)伤害', 180 * power, rawcode)
                            require('最多12名' in text and '持续3秒' in text and '不随尸爆进化增伤' in text, rawcode)
                        elif skill == 0:
                            number(text, r'攻击力\+([\d.]+)', power, rawcode)
                        elif skill == 6:
                            number(text, r'护甲降低([\d.]+)', power, rawcode)
                        elif skill == 8:
                            number(text, r'普攻伤害的([\d.]+)%', power * 100, rawcode)
                        elif skill == 15:
                            number(text, r'移动速度降低([\d.]+)%', (power if current else min(.75, power)) * 100, rawcode)
                        else:
                            number(text, r'([\d.]+)%', power * 100, rawcode)
                        if current and skill in (5, 9, 15):
                            require('总上限75%' in text, rawcode + ': pet slow total cap')
                        if current and skill == 4:
                            require('全队' not in text, rawcode + ': pet command must affect only host')
                        checked += 1
    catalog = (root / 'wurst/towers/TDTowerCatalogData.wurst').read_text()
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
    if not current:
        equipment = [fields for uid, fields in items.items() if uid != 'Ibal' and '同塔第3件同名装备' in fields.get('utub', '')]
        require(len(equipment) == 28, f'expected 28 gear texts, got {len(equipment)}')
        for fields in equipment:
            text = fields['utub']
            text_check(text, fields['unam'])
            require('50%' in text and '前3格' in text, fields['unam'])
            checked += 1
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
            'BOSS_DAMAGE': (r'首领' + ('或金币试炼' if profile == 'legacy009' else '') + r'主目标时，追加本次普攻伤害的([\d.]+)%', 100),
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
    for rawcode, chance, multiplier, bonus in (('A102', 25, 2.2, 90), ('A112', 25, 2.64, 108)):
        text = value(abilities[rawcode][1], 'aub1', 1)
        number(text, r'(?:有)?([\d.]+)%概率', chance, rawcode)
        number(text, r'造成([\d.]+)倍伤害', multiplier, rawcode)
        number(text, r'(?:追加|附加)([\d.]+)(?:点)?伤害', bonus, rawcode)
    if current_pet_ui:
        # Current UI puts irreversible release and material costs on their own
        # commands. Keep the historical combined Pc06 assertion below intact.
        from VerifyPetUIArtifact import verify_cultivation_command, verify_manager_commands
        verify_cultivation_command(abilities, current_manager=True)
        verify_manager_commands(abilities)
        for uid in ('Pm02', 'Pm03', 'Pm04', 'Pm05'):
            text = value(abilities[uid][1], 'aub1', 1)
            require(all(x in text for x in ('1洗练石', '保留旧技能也会消耗洗练石', '未解锁的技能也可洗练', '空栏须先开栏')), uid + ': current cultivation risk/cost missing')
        slot_rule = '按属性、攻击被动、强化、自动主动的顺序' if is_phase_one_ui(abilities) else '不重复技能'
        require(all(x in value(abilities['Pm06'][1], 'aub1', 1) for x in ('1开栏石', slot_rule, '最多4栏', '先完成当前洗练选择')), 'Pm06: current slot cost/order missing')
        for uid in ('Pm07', 'Pm0B'):
            text = value(abilities[uid][1], 'aub1', 1)
            require(all(x in text for x in ('永久失去', '1洗练石', '紫色精灵必得1开栏石', '非紫色3技能精灵有5%概率', '其他非紫色精灵有2%概率获得1开栏石', '捕获球和已用材料不返还')), uid + ': current release risk/reward missing')
        require('先解绑' in value(abilities['Pm07'][1], 'aub1', 1) and '再次确认' in value(abilities['Pm07'][1], 'aub1', 1), 'Pm07: current release prerequisites missing')
        require('无法撤销' in value(abilities['Pm0B'][1], 'aub1', 1), 'Pm0B: current release irreversibility missing')
        require('洗练石不返还' in value(abilities['Pm09'][1], 'aub1', 1), 'Pm09: current reroll refund risk missing')
        for uid in ('Pm02', 'Pm03', 'Pm04', 'Pm05', 'Pm06', 'Pm07', 'Pm09', 'Pm0A', 'Pm0B', 'Pm0D', 'Pm0E'):
            text_check(value(abilities[uid][1], 'aub1', 1), uid)
        require('冷却结束' in value(abilities['Pm0A'][1], 'aub1', 1), 'adopt cooldown restriction missing')
        continuation = value(abilities['Pm0D'][1], 'aub1', 1)
        require(all(x in continuation for x in ('消耗1洗练石', '新技能会被替换', '原技能保持不变')), 'continue reroll cost/preservation missing')
        require('保留本次洗练结果' in value(abilities['Pm0E'][1], 'aub1', 1), 'preview return preservation missing')
    else:
        cultivation = value(abilities['Pc06'][1], 'aub1', 1)
        require(all(x in cultivation for x in ('不退石', '共鸣锁定', '永久删除', '不退球和已用材料', '1洗练石', '2%', '1开栏石', '先召回')), 'cultivation risk/cost missing')
    descriptions = [value(abilities[f'Pc0{i}'][1], 'aub1', 1) for i in range(8)]
    require(len(set(descriptions)) == 8, 'collection commands reuse generic description')
    ground = value(abilities['Gupg'][1], 'aub1', 1)
    craft = value(abilities['A119'][1], 'aub1', 1)
    if current:
        require(all(x in ground for x in ('本路地面装备', '144范围', '每3件同品质升一级', '优先同名，升为对应下一阶', '混名随机', '紫装不能合成', '不足3件保留', '本次不再参与合成', '材料被移走或收纳点不可用时，该组不消耗')), 'current ground craft rule missing')
        require(all(x in craft for x in ('前3格', '三件同品质', '三件同名升为对应下一阶', '混名随机获得下一品质', '均必成', '紫装不能合成', '未成功不耗材料')), 'current backpack craft risks missing')
        require(not any(x in craft + ground for x in ('65%', '失败时材料全部消失', '两件必成')), 'current retired craft rule remains')
    else:
        require(all(x in ground for x in ('本路', '144范围', '每3件必得1件', '高一品质', '可不同名', '每次只升一级', '对应品质堆', '本次不再参与升级', '余1至2件原地保留')), 'ground craft rule missing')
        require(not any(x in ground for x in ('65%', '失败', '继续合成至紫')), 'ground craft old rule remains')
        require(all(x in craft for x in ('3件必成', '65%', '失败时材料全部消失', '最高紫装')), 'backpack craft risks missing')
    require('不返还' in value(abilities['A133'][1], 'aub1', 1), 'sale evolution limit missing')
    for uid in ('A116',):
        for level in (1, 2):
            text = value(abilities[uid][1], 'aub1', level)
            require('不高于25%' in text and ('220范围' if current else '180范围') in text, 'corpse explosion trigger mismatch')
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--profile', choices=PROFILES, default='current40')
    parser.add_argument('--source-root', type=Path)
    parser.add_argument('--shared-active-cooldown', action='store_true', help='Require the current generic active-CD wording; historical default retained')
    parser.add_argument('--current-pet-ui', action='store_true', help='Require the current split cultivation/release UI; historical default retained')
    args = parser.parse_args()
    mpq = Mpq(args.map.read_bytes())
    count = validate(ability_objects(mpq.extract('war3map.w3a')), unit_objects(mpq.extract('war3map.w3u')), unit_objects(mpq.extract('war3map.w3t')), profile=args.profile, source_root=args.source_root, shared_active_cooldown=args.shared_active_cooldown, current_pet_ui=args.current_pet_ui)
    print(f'PASS {args.profile}: {count} packaged player tooltip instances checked against numeric fields/rules; length and developer-language checks passed.')


if __name__ == '__main__':
    main()
