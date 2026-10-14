#!/usr/bin/env python3
"""Verify full native upgrade refund configuration and replay script non-interference.

The native debit/refund is an explicit boundary fixture, not retail Warcraft
emulation. The real packed lifecycle handlers run before/after that boundary,
including duplicate events. Retail 1.27a resource timing/UI remains untested.
"""
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import zipfile

from GenerateTowerTerrainMask import Mpq
from VerifyCombatVisualArtifact import VisualRuntime
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerPlacementArtifact import unit_objects
from VerifyTowerUpgradeArtifact import rawcode

ROOT = Path(__file__).resolve().parents[1]
BASE_MISC = {'PickupItemRange': '1200.0', 'DropItemRange': '1200.0',
             'GiveItemRange': '1200.0', 'DisplayBuildingStatus': '1'}


def parse_misc(text):
    parser = configparser.ConfigParser(interpolation=None, comment_prefixes=('//', ';', '#'))
    parser.optionxform = str
    parser.read_string(text)
    require(parser.sections() == ['Misc'], 'Unexpected gameplay constant section')
    return dict(parser['Misc'])


def validate_misc(text):
    data = parse_misc(text)
    require(data.get('UpgradeRefundRate') == '1.0', 'UpgradeRefundRate must refund 100%')
    require({k: v for k, v in data.items() if k != 'UpgradeRefundRate'} == BASE_MISC,
            'Unrelated gameplay constants changed (construction refund must stay inherited)')


def validate_source(root=ROOT):
    validate_misc((root / 'imports/war3mapMisc.txt').read_text())
    runtime = (root / 'wurst/towers/TDTowerRuntime.wurst').read_text()
    for name in ('tdHandleTowerUpgradeStarted', 'tdHandleTowerUpgradeCancelled', 'tdHandleTowerUpgradeFinished'):
        body = re.search(r'^function ' + name + r'\(\).*?(?=^(?:public )?(?:function |class )|\Z)',
                         runtime, re.M | re.S)[0]
        body = re.sub(r'//[^\n]*', '', body)
        require(not re.search(r'\b(?:tdGainGold|tdSpendGold|SetPlayerState|AdjustPlayerStateBJ)\s*\(', body),
                name + ': script must not debit/refund native upgrade gold')
    common = (root / 'wurst/towers/TDTowerCommonData.wurst').read_text()
    require('function tdTowerSellRefundPercent() returns int\n\treturn 80' in common,
            'Tower-sale refund changed')


def verify_locked_definition(jar):
    lock = json.loads((ROOT / 'tools/compiler/compiler-lock.json').read_text())
    digest = hashlib.sha256(jar.read_bytes()).hexdigest()
    require(digest.lower() == lock['compilerSha256'].lower(), 'Compiler jar is not locked version')
    with zipfile.ZipFile(jar) as archive:
        data = archive.read('net/moonlightflower/wc3libs/txt/app/MiscTXT$State.class')
        for token in (b'TECH_UPGRADE_REFUND_RATE', b'UpgradeRefundRate', b'War3Real',
                      b'TECH_UPGRADE_REFUND_DAMAGE_PENALTY', b'UpgradeDamageRefundPenalty',
                      b'ConstructionRefundRate'):
            require(token in data, 'Locked native field definition missing ' + repr(token))
    return {'compiler_sha256': digest, 'definition': 'wc3libs MiscTXT.State.TECH_UPGRADE_REFUND_RATE'}


def replay(script, units):
    r = VisualRuntime(script)
    gold_key = (0, r.globals['PLAYER_STATE_RESOURCE_GOLD'])
    r.native_trigger = 101
    matrix = []
    for family in 'AOHDG':
        for suffix in ('12', '13', '14', '15', '6A', '6B'):
            uid = 'u' + family + suffix
            obj = units[uid]
            level = 6 if suffix[0] == '6' else int(suffix[1])
            branch = 2 if suffix == '6B' else 1
            choice = 'AOHDG'.index(family) + 1
            cost = r.invoke('tdTowerGoldCostForLevelBranch', choice, level, branch)
            require(obj['ugol'] == cost, uid + ': declared object upgrade cost differs from rules')
            require(obj.get('ulum', 0) == 0, uid + ': unexpected lumber cost')
            parent = 'u' + family + '1' + str(level - 1)
            matrix.append((parent, uid, cost))
    # Zero and non-round charges ensure there is no fixed 20% top-up/rounding.
    matrix.extend([('uA11', 'uA12', 0), ('uA11', 'uA12', 1), ('uA11', 'uA12', 137)])
    expected_edges = {(parent, target) for parent, target, _ in matrix[:30]}
    actual_edges = {(uid, target) for uid, obj in units.items()
                    for target in obj.get('uupt', '').split(',') if target}
    require(actual_edges == expected_edges, 'Upgrade constant affects unexpected custom upgrade chains')
    initial = 20000
    for parent, target, charged in matrix:
        for timing in ('before_event', 'after_event'):
            r.executed_steps = 0
            r.units[101]['type'] = rawcode(parent)
            r.player_resources[gold_key] = initial - charged  # Native debit boundary.
            r.invoke('tdHandleTowerUpgradeStarted')
            require(r.player_resources[gold_key] == initial - charged, 'Script charged upgrade twice')
            if timing == 'before_event':
                r.player_resources[gold_key] += charged  # Native 100% refund, exactly once.
            r.invoke('tdHandleTowerUpgradeCancelled')
            if timing == 'after_event':
                require(r.player_resources[gold_key] == initial - charged, 'Script refund before native refund')
                r.player_resources[gold_key] += charged
            r.invoke('tdHandleTowerUpgradeCancelled')  # Duplicate queued callback.
            r.flush()
            r.invoke('tdHandleTowerUpgradeCancelled')  # Duplicate after completion.
            r.flush()
            require(r.player_resources[gold_key] == initial, target + ': script changed full native refund')
        r.executed_steps = 0
        r.player_resources[gold_key] = initial - charged
        r.invoke('tdHandleTowerUpgradeStarted')
        r.units[101]['type'] = rawcode(target)
        r.invoke('tdHandleTowerUpgradeFinished')
        r.invoke('tdHandleTowerUpgradeFinished')
        r.invoke('tdHandleTowerUpgradeCancelled')  # Late event must never mint gold.
        r.flush()
        require(r.player_resources[gold_key] == initial - charged, target + ': finish/late cancel minted gold')
    return {'all_upgrade_edges': 30, 'additional_charges': [0, 1, 137],
            'native_refund_timings': 2, 'duplicate_cancel_and_finish': True,
            'late_cancel_after_finish': True, 'native_engine_modeled_not_playtested': True}


def validate_artifact(path):
    archive = Mpq(path.read_bytes())
    misc = archive.extract('war3mapMisc.txt')
    require(misc == (ROOT / 'imports/war3mapMisc.txt').read_bytes(), 'Packaged misc differs from source')
    validate_misc(misc.decode('utf-8'))
    return replay(archive.extract('war3map.j').decode('utf-8'), unit_objects(archive.extract('war3map.w3u')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', nargs='?', type=Path)
    parser.add_argument('--locked-compiler', type=Path)
    args = parser.parse_args()
    validate_source()
    result = {'source': 'PASS'}
    if args.locked_compiler:
        result['native_definition'] = verify_locked_definition(args.locked_compiler)
    if args.map:
        result['artifact'] = validate_artifact(args.map)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
