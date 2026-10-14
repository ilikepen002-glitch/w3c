#!/usr/bin/env python3
"""Closed wave-wages -> lane-evolution packed delta; no resource/numeric exemptions.

Checks the exact fourth-batch object changes against the frozen third-batch map.
The separate evolution artifact and replay gates validate behavior and resources.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyGlobalRankingsArtifact import members, normalize_info
from VerifyTowerPlacementArtifact import unit_objects

ROOT = Path(__file__).resolve().parents[1]
# Locked stdlib OrderStringFactory prefix: inserting one allocation before A133
# shifts every existing Channel field by precisely one, including shared choices.
CHANNEL_ORDERS = ('absorb acidbomb acolyteharvest whirlwind ambush ancestralspirit '
                  'ancestralspirittarget animatedead antimagicshell webon weboff web '
                  'attributemodskill auraunholy auravampiric autodispel autodispeloff '
                  'autodispelon autoentangle autoentangleinstant wateryminion waterelemental '
                  'avatar avengerform awaken banish barkskin barkskinoff barkskinon battleroar '
                  'battlestations bearform berserk blackarrow blackarrowoff blackarrowon '
                  'blight blink blizzard bloodlust bloodlustoff bloodluston board breathoffire '
                  'breathoffrost ward burrow cannibalize carrionscarabs carrionscarabsinstant '
                  'carrionscarabsoff carrionscarabson carrionswarm chainlightning channel charm '
                  'chemicalrage cloudoffog clusterrockets coldarrows').split()

STATUS_TITLES = ('第24波后进化', '等待完成6阶', '已进化', '本路名额已用')
STATUS_DETAILS = (
    '本路第24波完成后获得一次资格。主动选择一座已完工6阶终阶塔进化，沿用该分支20%强化。',
    '本路已有一次进化资格。完成6阶升级后点击进化并确认；尚无终阶塔可保留资格。',
    '此塔已进化，当前分支技能已强化。|n出售或死亡不返还本路进化名额。',
    '本路进化名额已使用，此塔无法进化。出售或死亡不返还名额。')


def expected_abilities(previous):
    require('A109' not in previous and 'AeEC' not in previous,
            'Baseline must be the frozen wage map before chosen evolution')
    require(previous['A133'][0] == 'ANcl' and previous['A133'][1]['Ncl6', 1, 6] == (3, 'absorb'),
            'Baseline first Channel allocation must be tower sale')
    expected = deepcopy(previous)
    # The new chooser uses the same locked single-level zero-effect Channel
    # constructor as sale. Every unchanged flag/target/mana/CD is compared too.
    parent, chooser = deepcopy(previous['A133'])
    values = {'anam': '选择进化', 'atp1': '进化 (R)',
              'aub1': '预览并确认此塔的当前分支20%强化。|n本路第24波完成后仅一次；出售或死亡不返还。取消不消耗资格。',
              'aart': 'ReplaceableTextures\\CommandButtons\\BTNMetamorphosis.blp',
              'arar': 'ReplaceableTextures\\CommandButtons\\BTNMetamorphosis.blp',
              'ahky': 'R', 'arhk': 'R', 'auhk': 'R', 'abpy': 2}
    for field, value in values.items():
        key = field, (1 if field in ('atp1', 'aub1') else 0), 0
        chooser[key] = (chooser[key][0], value)
    for code, (parent_id, fields) in expected.items():
        if parent_id != 'ANcl':
            continue
        for key, (kind, order) in list(fields.items()):
            if key[0] == 'Ncl6':
                require(order in CHANNEL_ORDERS[:-1], 'Unknown locked Channel allocation: ' + code)
                fields[key] = kind, CHANNEL_ORDERS[CHANNEL_ORDERS.index(order) + 1]
    expected['AeEC'] = parent, chooser
    progress = expected['A130'][1]
    require(progress['alev', 0, 0] == (0, 935), 'Baseline statistics level count changed')
    for level in range(1, 936):
        progress['aub1', level, 0] = (3, f'本塔累计击杀：{level - 1}。升级继承统计；进化后继续累计。击杀仅作统计，不决定进化资格。')
    status = expected['AeEV'][1]
    require(status['alev', 0, 0] == (0, 3), 'Baseline global status is not three levels')
    for (field, level, column), value in list(status.items()):
        if level == 3:
            status[field, 4, column] = value
    status['anam', 0, 0] = (3, '路线进化')
    status['alev', 0, 0] = (0, 4)
    for level, (title, detail) in enumerate(zip(STATUS_TITLES, STATUS_DETAILS), 1):
        status['atp1', level, 0] = 3, title
        status['aub1', level, 0] = 3, detail
    sale = expected['A133'][1]
    sale['aub1', 1, 0] = (3, '出售此塔，返还已完成建造与升级花费的80%，不足1金币部分舍去；装备留在原地。|n建造或升级中不可出售。已使用的本路进化名额不返还。')
    return expected


def validate_ability_delta(current, previous):
    expected = expected_abilities(previous)
    require(current.keys() == expected.keys(), 'Unexpected evolution ability catalog delta')
    for code, (parent, fields) in current.items():
        old_parent, old_fields = expected[code]
        require(parent == old_parent and fields.keys() == old_fields.keys(),
                'Unexpected evolution ability identity/schema: ' + code)
        for key, value in fields.items():
            require(value == old_fields[key], 'Unrelated/incorrect evolution field: ' + code + '/' + repr(key))


def verify(candidate, baseline, source_root=ROOT):
    current, prior = Mpq(candidate), Mpq(baseline)
    a, b = members(current), members(prior)
    require(a.keys() == b.keys(), 'Unexpected evolution archive membership/resource change')
    require(normalize_info(current.extract('war3map.w3i'), '契灵守卫战') ==
            normalize_info(prior.extract('war3map.w3i'), '契灵守卫战'), 'Unrelated evolution map setting changed')
    changed = sorted(name for name in a if a[name][1] != b[name][1])
    require(set(changed) <= {'war3map.j', 'war3map.w3i', 'war3map.w3a'},
            'Unexpected evolution resource/object delta: ' + repr(changed))
    abilities = ability_objects(current.extract('war3map.w3a'))
    validate_ability_delta(abilities, ability_objects(prior.extract('war3map.w3a')))
    require(unit_objects(current.extract('war3map.w3u')) == unit_objects(prior.extract('war3map.w3u')),
            'Evolution changed a unit, upgrade path, route or base balance field')
    probe = (source_root / 'tests/wurst/runtime/TDNativeNormalPlayProbe.wurst').read_text()
    declared = re.findall(r'IssueTargetOrderById\(worker, OrderId\("([^"]+)"\), normalCaptureTarget\)', probe)
    require(declared == [abilities['Pcap'][1]['Ncl6', 1, 6][1]],
            'Native normal-play capture probe does not match packaged Channel order')
    return {'changedMembers': changed, 'newAbility': 'AeEC', 'unchangedUnits': True,
            'resourceDeltas': 0, 'balanceDeltas': 0, 'nativeProbeOrderMatched': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    data = args.map.read_bytes()
    result = {'status': 'PASS', 'mapSHA256': hashlib.sha256(data).hexdigest(),
              'baselineSHA256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
              'delta': verify(data, args.baseline.read_bytes()),
              'boundary': 'Exact packed archive/object delta only; no Warcraft rendering or input claim.'}
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
