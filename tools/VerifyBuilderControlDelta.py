#!/usr/bin/env python3
"""Historical B-only closed delta, never a wider rule for subsequent features."""
import re
import struct
from VerifyEquipmentAbilityArtifact import require
from VerifyDamageRankingJass import functions
from VerifyGlobalRankingsArtifact import members, normalize_info
from VerifySemanticIconArtifact import load_objects

OLD_GUIDE = '守住起点到终点的路线，在高台建塔。B 建造 / F 闪烁 / C 功能 / G 工资；Q 捕获 / W 收藏 / E 上阵。滚轮调整镜头；精灵与装备都可强化塔。|n每漏过1名敌人扣除生命：普通1、精英和近卫队长2、首领3。'
NEW_GUIDE = '守住起点到终点的路线，在高台建塔。B 建造 / U 范围升级 / C 背包合成 / G 工资；Q 捕获 / W 收藏 / E 上阵。发起建造后建筑自行施工。滚轮调整镜头；精灵与装备都可强化塔。|n每漏过1名敌人扣除生命：普通1、精英和近卫队长2、首领3。'
OLD_WORKER_TEXT = '空中建造工人，可穿越障碍并用闪烁快速移动到建造位。'
NEW_WORKER_TEXT = '空中建造工人，可穿越障碍。发起建造后建筑自行施工；U 范围升级地面装备，C 打开背包合成。'
OLD_BOOK_TEXT = '打开背包合成与地面范围升级功能。|n地面物品每30秒整理到所属路线的高台边缘：装备按品质分堆，捕获球单独一堆。'
NEW_BOOK_TEXT = '打开背包合成。|n范围升级已移到工人主栏，按U选择地面装备区域。地面物品每30秒整理到本路高台边缘：装备按品质分堆，捕获球单独一堆。'
OBJECT_VALUES = {('units', 'uF01', ('utub', 0, 0)): (OLD_WORKER_TEXT, NEW_WORKER_TEXT),
                 ('units', 'uF01', ('uabi', 0, 0)): ('AUbu,A108,A109,A117,Geqb,Pcap,Pcol,Pdep', 'AUbu,A109,A117,Geqb,Gupg,Pcap,Pcol,Pdep'),
                 ('abilities', 'Geqb', ('aub1', 1, 0)): (OLD_BOOK_TEXT, NEW_BOOK_TEXT),
                 ('abilities', 'Geqb', ('spb1', 1, 1)): ('A119,Gupg', 'A119'),
                 ('abilities', 'Geqb', ('spb3', 1, 3)): (2, 1),
                 ('abilities', 'Geqb', ('spb4', 1, 4)): (2, 1),
                 ('abilities', 'Gupg', ('abpy', 0, 0)): (0, 1)}
# Exact observed compiletime-class removal reindexes these named allocators only.
REINDEXED = {'TDEnemyGuardLink': 819, 'TDEnemyMechanicRecord': 818, 'TDEnemyMechanicState': 820,
             'TDPetDebuff': 823, 'TDPetSlowState': 824, 'TDEquipmentCooldown': 821,
             'TDEquipmentDebuff': 822, 'TDDamageRecord': 817, 'TDDamageTowerBinding': 815,
             'TDPetWildRecord': 828, 'TDPetDialogSession': 826, 'TDEvolutionTower': 829,
             'Table': 835, 'HashMap': 836, 'TDDamageLedger': 816, 'TDTowerEvolutionMatch': 830,
             'TDArcherSplitArrowVolley': 833, 'TDArcherArrowVisual': 831, 'TDArcherSplitArrowShot': 832,
             'TDTowerSaleState': 834, 'TDPet': 825}
ASSIGN = re.compile(r'^(\s*set (\w+_typeId)\[[^\]\n]+\] = )(\d+)(\s*)$', re.M)
TYPE_TEST = re.compile(r'((?:\w+_typeId\[[^\]\n]+\]|\btypeId)\s*(?:==|!=|<=|>=|<|>)\s*)(\d+)')
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*')
TEMP = re.compile(r'^\s*local (\w+) (temp\d+(?:_\w+)?)\b', re.M)


# Explicit unallocated ancestor/range boundaries in immutable formal A.
UNCHANGED_TYPE_BOUNDARIES = {0, 633, 638, 659, 660, 661, 662, 665}


def normalize_type_tests(text, previous, old_to_new):
    actual, before = list(TYPE_TEST.finditer(text)), list(TYPE_TEST.finditer(previous))
    require(len(actual) == len(before), 'Type comparison count changed')
    replacements = []
    for now, old in zip(actual, before):
        require(now[1] == old[1], 'Type comparison array/operator/reference changed')
        threshold = int(old[2])
        if threshold in old_to_new:
            expected = old_to_new[threshold]
        else:
            require(threshold in UNCHANGED_TYPE_BOUNDARIES, 'Unknown baseline type threshold')
            expected = threshold
        require(int(now[2]) == expected, 'Type comparison threshold changed')
        replacements.append((now.start(2), now.end(2), str(threshold)))
    for start, end, value in reversed(replacements):
        text = text[:start] + value + text[end:]
    return text


def allocations(script):
    result = {}
    for name, fn in functions(script).items():
        hits = [(m[2], int(m[3])) for m in ASSIGN.finditer(fn[0]) if int(m[3])]
        if hits:
            require(name.startswith('alloc_') and len(set(hits)) == 1,
                    'Type allocation must be one consistent named allocator: ' + name)
            result[name] = hits[0]
    require(len({value[1] for value in result.values()}) == len(result), 'Type IDs must have unique allocator owners')
    return result


def proved_type_reindex_view(script, baseline):
    """Read-only inherited-check view: named allocators plus every type threshold.

    This does not ignore other function differences or validate their gameplay.
    Current behavior gates execute the actual script separately.
    """
    current, before = functions(script), functions(baseline)
    new_ids, old_ids = allocations(script), allocations(baseline)
    require(set(new_ids) == set(old_ids), 'B type allocator set changed')
    require(all('alloc_' + name in old_ids for name in REINDEXED), 'Not the exact formal A allocator baseline')
    mapping, evidence = {}, {}
    for name, (array, old_id) in old_ids.items():
        new_array, new_id = new_ids[name]
        require(old_id == REINDEXED.get(name[6:], old_id) and array == new_array, 'B type allocator identity changed: ' + name)
        require(new_id == old_id - (5 if name[6:] in REINDEXED else 0), 'B type allocator reindex changed: ' + name)
        mapping[new_id] = old_id
        if new_id != old_id: evidence[name] = {'array': array, 'before': old_id, 'after': new_id}
    require(len(mapping) == len(old_ids), 'Type mapping is not a bijection')
    pieces, offset = [], 0
    for name, fn in current.items():
        text = fn[0]
        if name in new_ids:
            text = ASSIGN.sub(lambda m: m[1] + str(mapping[int(m[3])]) + m[4] if int(m[3]) else m[0], text)
            require(text == before[name][0], 'Type allocator differs beyond the proved ID: ' + name)
        text = normalize_type_tests(text, before[name][0] if name in before else '', {old: new for new, old in mapping.items()})
        pieces.extend([script[offset:fn.start()], text]); offset = fn.end()
    pieces.append(script[offset:])
    return ''.join(pieces), {'allocators': len(mapping), 'type_reindex': evidence,
                            'type_comparisons': len(TYPE_TEST.findall(script))}


def prove_jass_delta(script, baseline):
    current, before = functions(script), functions(baseline)
    require(set(current) == set(before), 'B JASS function set changed')
    new_ids, old_ids = allocations(script), allocations(baseline)
    require(set(new_ids) == set(old_ids), 'B type allocator set changed')
    require(all('alloc_' + name in old_ids for name in REINDEXED), 'Not the exact formal A allocator baseline')
    mapping, evidence = {}, {}
    for name, (array, old_id) in old_ids.items():
        new_array, new_id = new_ids[name]
        expected = REINDEXED.get(name[6:], old_id)
        require(old_id == expected and array == new_array, 'B type allocator identity changed: ' + name)
        require(new_id == old_id - (5 if name[6:] in REINDEXED else 0), 'B type allocator reindex changed: ' + name)
        mapping[new_id] = old_id
        if new_id != old_id: evidence[name] = {'array': array, 'before': old_id, 'after': new_id}
    require(len(mapping) == len(old_ids), 'Type mapping is not a bijection')
    pieces, offset, temps = [], 0, {}
    for name, fn in current.items():
        old = before[name]
        require((fn[2], fn[3]) == (old[2], old[3]), 'B JASS signature changed: ' + name)
        text = fn[0]
        declarations, previous = TEMP.findall(text), TEMP.findall(old[0])
        require([t for t, _ in declarations] == [t for t, _ in previous], 'Local compiler temp declaration/type changed: ' + name)
        rename = {new: prior for (_, new), (_, prior) in zip(declarations, previous)}
        require(len(rename) == len(declarations) and len(set(rename.values())) == len(previous), 'Local temp map not bijective')
        text = TOKEN.sub(lambda m: m[0] if m[0].startswith('"') else rename.get(m[0], m[0]), text)
        if any(k != v for k, v in rename.items()): temps[name] = rename
        if name in new_ids:
            text = ASSIGN.sub(lambda m: m[1] + str(mapping[int(m[3])]) + m[4] if int(m[3]) else m[0], text)
        # Comparison operands are mapped by the same proved allocator identity,
        # including zero and unchanged thresholds; full text equality follows.
        text = normalize_type_tests(text, old[0], {old_id: new_id for new_id, old_id in mapping.items()})
        pieces.extend([script[offset:fn.start()], text]); offset = fn.end()
    pieces.append(script[offset:]); view = ''.join(pieces)
    for new_line, old_line in [(14, 15), (63, 64)]:
        new = f'when calling fromRawCode in TDPetData, line {new_line}'
        old = f'when calling fromRawCode in TDPetData, line {old_line}'
        require(view.count(new) == 1 and baseline.count(old) == 1, 'Only two exact shifted TDPetData diagnostic strings are permitted')
        view = view.replace(new, old)
    require(view.count('"' + NEW_GUIDE + '"') == 1 and baseline.count('"' + OLD_GUIDE + '"') == 1, 'Only exact B startup text is permitted')
    view = view.replace('"' + NEW_GUIDE + '"', '"' + OLD_GUIDE + '"')
    require(view == baseline, 'B JASS changed outside proved type/local-temp reindex, two diagnostic lines and exact startup text')
    return {'allocators': len(mapping), 'type_reindex': evidence, 'type_comparisons': len(TYPE_TEST.findall(script)), 'local_temp_alpha': temps}


def verify_object_delta(current, baseline):
    require(set(current) == set(baseline), 'B object table set changed')
    for kind, before in baseline.items():
        after = current[kind]
        removed = {'A108', 'Prpr'} if kind == 'abilities' else set()
        require(removed.issubset(before), 'B requires formal A blink/repair definitions')
        require(list(after) == [k for k in before if k not in removed], 'B unrelated object set/order changed: ' + kind)
        for code, obj in after.items():
            old = before[code]
            require((obj.table, obj.identity, list(obj.fields)) == (old.table, old.identity, list(old.fields)), 'B object identity/field order changed: ' + code)
            for key, item in obj.fields.items():
                prior = old.fields[key]; values = OBJECT_VALUES.get((kind, code, key))
                if values is None:
                    require(item == prior, 'B unrelated object field changed: ' + code + '/' + key[0]); continue
                require((prior.value, item.value) == values and item.kind == prior.kind, 'B exact field value/type changed: ' + code + '/' + key[0])
                header = 16 if kind == 'abilities' else 8
                payload = item.value.encode() + b'\0' if item.kind == 3 else struct.pack('<i', item.value)
                require(item.raw == prior.raw[:header] + payload + prior.raw[-4:], 'B field encoding changed: ' + code + '/' + key[0])


def validate_closed_control_delta(current, baseline):
    after, before = members(current), members(baseline)
    require(set(after) == set(before), 'B MPQ resource set changed')
    for key, (old_name, old) in before.items():
        name, data = after[key]; require(name == old_name, 'B MPQ resource spelling changed')
        if name in ('war3map.w3a', 'war3map.w3u', 'war3map.j'): continue
        if name == 'war3map.w3i': require(normalize_info(data) == normalize_info(old), 'B metadata changed beyond two display timestamps')
        else: require(data == old, 'B unrelated resource changed: ' + name)
    verify_object_delta(load_objects(current), load_objects(baseline))
    proof = prove_jass_delta(current.extract('war3map.j').decode(), baseline.extract('war3map.j').decode())
    proof['resources'] = len(after)
    return proof
