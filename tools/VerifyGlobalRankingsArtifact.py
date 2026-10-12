#!/usr/bin/env python3
"""Closed Dsta-only artifact delta against the formal ordinary-capture map.

python tools/VerifyGlobalRankingsArtifact.py map.w3x --baseline-map A.w3x
The packaged real helpers and participant selection execute against an oracle.
Native multiboard rendering and engine timer scheduling remain unobserved.
"""
import argparse
import importlib
from pathlib import Path
import re
from GenerateTowerTerrainMask import Mpq, mpq_hash
from VerifyEquipmentAbilityArtifact import ability_objects, require
from VerifyGroundItemArtifact import verify_global_channel_orders
from VerifySemanticIconArtifact import parse_objects, Reader
from VerifyDamageRankingJass import functions, verify_comparators, verify_player_selection
from VerifyInheritedJassAliases import inherited_script_view

ROOT = Path(__file__).resolve().parents[1]
OBJECTS = {'war3map.w3u': False, 'war3map.w3a': True, 'war3map.w3t': False,
           'war3map.w3b': False, 'war3map.w3d': True, 'war3map.w3h': False, 'war3map.w3q': True}
BOOK_TEXT = ('打开背包合成与地面范围升级功能。|n地面物品每30秒整理到所属路线的高台边缘：'
             '装备按品质分堆，捕获球单独一堆。')
# Locked factory slots, not per-ability order assignments. Removing Dsta must
# compact exactly one slot, preserving the relative allocation of every survivor.
ORDER_FACTORY = ('absorb', 'acidbomb', 'acolyteharvest', 'whirlwind', 'ambush',
                 'ancestralspirit', 'ancestralspirittarget', 'animatedead',
                 'antimagicshell', 'webon', 'weboff', 'web', 'attributemodskill',
                 'auraunholy', 'auravampiric', 'autodispel', 'autodispeloff',
                 'autodispelon', 'autoentangle', 'autoentangleinstant',
                 'wateryminion', 'waterelemental', 'avatar', 'avengerform',
                 'awaken', 'banish', 'barkskin', 'barkskinoff', 'barkskinon',
                 'battleroar', 'battlestations', 'bearform')


def no_removed_objects(objects):
    removed = ('Dsta', 'Pmas', 'Pfor')
    token = re.compile(r'(?<![A-Za-z0-9_])(?:Dsta|Pmas|Pfor)(?![A-Za-z0-9_])')
    for filename, entries in objects.items():
        for rawcode, obj in entries.items():
            require(rawcode not in removed and obj.identity[:4].decode('ascii') not in removed,
                    filename + ': removed ability ghost/parent')
            for item in obj.fields.values():
                require(not isinstance(item.value, str) or not token.search(item.value),
                        rawcode + ': removed ability reference')


def allocation(abilities):
    result = {}
    for rawcode, obj in abilities.items():
        if obj.identity[:4] != b'ANcl':
            continue
        orders = {f.value for key, f in obj.fields.items() if key[0] == 'Ncl6'}
        require(len(orders) == 1, rawcode + ': inconsistent Channel order across levels')
        order = orders.pop()
        require(order in ORDER_FACTORY, rawcode + ': unknown locked factory order')
        result[rawcode] = ORDER_FACTORY.index(order)
    require(len(set(result.values())) == len(result) and set(result.values()) == set(range(len(result))),
            'Channel allocation must be unique and dense')
    return result


def verify_object_delta(current, baseline):
    no_removed_objects(current)
    old_abilities, abilities = baseline['war3map.w3a'], current['war3map.w3a']
    require('Dsta' in old_abilities and 'Pmas' not in old_abilities and 'Pfor' not in old_abilities,
            'Baseline must be the formal ordinary-capture map, before Dsta removal')
    before, after = allocation(old_abilities), allocation(abilities)
    require('Dsta' in before, 'Baseline Dsta must use Channel')
    removed_slot = before['Dsta']
    for filename, previous in baseline.items():
        entries = current[filename]
        require(list(entries) == [k for k in previous if filename != 'war3map.w3a' or k != 'Dsta'],
                filename + ': forbidden object set/order delta')
        for rawcode, obj in entries.items():
            old = previous[rawcode]
            require((obj.table, obj.identity, list(obj.fields)) == (old.table, old.identity, list(old.fields)),
                    rawcode + ': forbidden object identity/field order delta')
            for key, item in obj.fields.items():
                prior = old.fields[key]
                book = filename == 'war3map.w3a' and rawcode == 'Geqb' and key in {
                    ('spb1', 1, 1), ('spb3', 1, 3), ('spb4', 1, 4), ('aub1', 1, 0)}
                channel = filename == 'war3map.w3a' and rawcode in before and key[0] == 'Ncl6'
                if not book and not channel:
                    require(item == prior, rawcode + ': unrelated object field changed: ' + repr(key))
                    continue
                require(item.kind == prior.kind and item.raw[:16] == prior.raw[:16] and item.raw[-4:] == prior.raw[-4:],
                        rawcode + ': permitted field encoding changed')
                if channel:
                    expected = before[rawcode] - (before[rawcode] > removed_slot)
                    require(after[rawcode] == expected and item.value == ORDER_FACTORY[expected],
                            rawcode + ': unjustified Channel allocation shift')
    old, new = old_abilities['Geqb'].fields, abilities['Geqb'].fields
    for key, first, last in [(('spb1', 1, 1), 'A119,Gupg,Dsta', 'A119,Gupg'),
                             (('spb3', 1, 3), 3, 2), (('spb4', 1, 4), 3, 2)]:
        require(old[key].value == first and new[key].value == last, 'Function book exact three-to-two delta')
    require(new[('aub1', 1, 0)].value == BOOK_TEXT, 'Function book exact description')


def normalize_info(data):
    r = Reader(data)
    require(r.integer() == 25, 'Unexpected W3I version')
    r.take(8)
    spans = []
    start = r.offset; name = r.string(); spans.append((start, r.offset, name))
    for _ in range(3): r.string()
    r.take(65)
    r.string(); r.string()
    start = r.offset; title = r.string(); spans.append((start, r.offset, title))
    stamp = re.fullmatch(r'深渊守望 (\d{8})-([0-2]\d[0-5]\d)-UTC\+8', name)
    require(name == title and stamp and int(stamp[2][:2]) < 24,
            'Unexpected map/loading title timestamp')
    result, offset = bytearray(), 0
    for start, end, text in spans:
        result.extend(data[offset:start]); result.extend(b'\xe6\xb7\xb1\xe6\xb8\x8a\xe5\xae\x88\xe6\x9c\x9b BUILD-TIMESTAMP\0'); offset = end
    result.extend(data[offset:])
    return bytes(result)


def members(mpq):
    names = mpq.extract('(listfile)').decode('utf-8-sig').splitlines()
    names += ['(listfile)', '(attributes)', '(signature)']
    known, result = {}, {}
    for name in names:
        if not name or not mpq.has(name): continue
        folded = name.casefold()
        require(folded not in result or result[folded][0] == name, 'Resource case alias')
        result[folded] = (name, mpq.extract(name))
        key = mpq_hash(name, 1), mpq_hash(name, 2)
        require(key not in known or known[key] == folded, 'Resource hash alias')
        known[key] = folded
    active = set()
    for a, b, locale, platform, block in mpq.hashes:
        if block >= len(mpq.blocks) or not mpq.blocks[block][3] & 0x80000000: continue
        require((a, b) not in active and locale == platform == 0, 'Duplicate/localized MPQ entry')
        require((a, b) in known, 'Unlisted active MPQ resource')
        active.add((a, b))
    require(active == set(known), 'MPQ member/hash coverage')
    for name in result:
        require(not re.search('tdaction(?:mastercapture|captureforge)', name), 'Removed capture icon remains')
    return result


def verify_archive_delta(current, baseline):
    after, before = members(current), members(baseline)
    require(set(after) == set(before), 'Forbidden packaged resource set delta')
    objects, previous = {}, {}
    for name in before:
        path, data = after[name]; old_path, old = before[name]
        require(path == old_path, 'Resource spelling changed')
        if path in OBJECTS:
            objects[path] = parse_objects(data, OBJECTS[path]); previous[path] = parse_objects(old, OBJECTS[path])
        elif path == 'war3map.w3i':
            require(normalize_info(data) == normalize_info(old), 'Forbidden W3I delta beyond display timestamps')
        elif path not in ('war3map.j', '(attributes)', '(listfile)'):
            require(data == old, 'Unrelated resource changed: ' + path)
    require('war3map.w3a' in objects, 'Missing ability member')
    verify_object_delta(objects, previous)
    verify_global_channel_orders(ability_objects(current.extract('war3map.w3a')))
    return len(before)


def verify_source(root=ROOT):
    root = Path(root); damage = root / 'wurst/damage'
    for name in ('TDDamageData.wurst', 'TDDamageObjectGen.wurst', 'TDDamageUI.wurst'):
        require(not (damage / name).exists(), 'Obsolete damage package remains')
    clean = lambda text: re.sub(r'//[^\n]*', '', text)
    hud = clean((damage / 'TDDamageHud.wurst').read_text())
    state = clean((damage / 'TDDamageState.wurst').read_text())
    runtime = clean((damage / 'TDDamageRuntime.wurst').read_text())
    board = clean((root / 'wurst/TDHud.wurst').read_text())
    init = clean((root / 'wurst/TDInit.wurst').read_text())
    require('TD_DAMAGE_HUD_ROWS = 16' in hud and 'TD_DAMAGE_HUD_COLUMNS = 4' in hud and
            'TD_DAMAGE_TOWER_TOP_COUNT = 10' in hud and 'string array tdDamageHudCells' in hud, 'Fixed damage layout changed')
    require(hud.count('string array tdDamageHudCells') == 1 and 'class ' not in hud and 'GetLocalPlayer' not in hud,
            'Rankings must use one synchronized snapshot')
    require('tdDamageHudCells[index] = ""' in hud and hud.index('tdDamageHudCells[index] = ""') < hud.index('tdDamageSetHudCell(0,'), 'Snapshot clearing missing')
    for lane in range(4):
        require(re.search(r'if p' + str(lane) + r'\s+tdDamageSetPlayerHud\(ledger, ' + str(lane) + r', p0, p1, p2, p3\)', hud),
                'Player must be selected exactly once by startup membership')
        require(hud.count(f'tdDamageSetPlayerHud(ledger, {lane}, p0, p1, p2, p3)') == 1, 'Duplicate player selection')
    player = hud.split('function tdDamageSetPlayerHud', 1)[1].split('public function tdDamagePrepareHud', 1)[0]
    require(re.findall(r'tdDamageSetHudCell\(1 \+ rank, (\d),', player) == ['0', '1'], 'Player row must contain only ID/total')
    require('getSerial()' not in hud and 'getHandleId()' not in hud and ' [退场]' in hud, 'Tower display exposes identity or loses retirement')
    require('tdDamagePrepareHud(tdDamageLedger, tdIsLaneActive(0), tdIsLaneActive(1), tdIsLaneActive(2), tdIsLaneActive(3))' in hud,
            'Startup participation flags changed')
    for source in (hud, state, runtime, init):
        require(not re.search(r'TDDamageUI|tdSetupDamageUI|tdDamageViewer|tdDamagePage|tdDamageSetView|tdResetDamageViews', source), 'Removed UI/page hook')
    setup = board.split('public function tdSetupHud()', 1)[1]
    require('if compiletime or tdStatusBoard != null' in setup and 'setColumnCount(TD_DAMAGE_HUD_COLUMNS)' in setup and
            'setRowCount(tdCountActiveLanes() + 5 + TD_DAMAGE_HUD_ROWS)' in setup, 'Board setup guard/layout')
    require('setItemWidth(row, 2, 0.25)' in setup and 'setItemWidth(row, 3, 0.005)' in setup, 'Upper status text width lost')
    require(re.search(r'doPeriodically\(1\.0\) cb ->\s+tdRefreshStatusBoard\(\)\s+if tdIsGameOver\(\)\s+destroy cb', setup),
            'Timer must final-refresh before destruction')
    refresh = board.split('public function tdRefreshStatusBoard()', 1)[1].split('public function tdSetupHud()', 1)[0]
    require('.show()' not in refresh and '.maximize()' not in refresh and setup.count('.show()') == setup.count('.maximize()') == 1,
            'Refresh must preserve native collapse state')
    require(re.search(r'if tdDamageReady or compiletime\s+return\s+tdDamageReady = true', runtime) and runtime.count('DamageEvent.addUnreducedListener(4)') == 1 and
            'tdEffectiveDamage(DamageEvent.getAmount(), target.getLife())' in runtime and
            runtime.count('tdDamageLedger.credit(record, amount, amount)') == 1, 'Damage accounting/listener changed')
    require('tdResetDamageStatistics' not in refresh + setup, 'Game-over HUD must retain ledger')
    require(re.search(r'function tdDamageCaptureHit\(\)\s+if tdIsGameOver\(\)\s+return', runtime),
            'Damage accounting must freeze at game over')
    for row, column, label in ((0, 0, '玩家ID'), (0, 1, '累计伤害'), (5, 0, '排名'),
                               (5, 1, '玩家ID'), (5, 2, '防御塔 Top10'), (5, 3, '累计伤害')):
        require(f'tdDamageSetHudCell({row}, {column}, "{label}")' in hud, 'Ranking header field changed')
    return True


def verify_packaged_structure(script):
    f = functions(script)
    for name in ('tdDamagePrepareHud', 'tdDamageSetPlayerHud', 'tdDamageRefreshHud', 'tdSetupHud', 'tdSetupDamageStatistics'):
        require(name in f, 'Missing packaged function: ' + name)
    snapshot = '\n'.join(m[0] for name, m in f.items() if name in ('tdDamagePrepareHud', 'tdDamageSetPlayerHud', 'tdDamageSetHudCell', 'tdDamageHudCell', 'tdDamageRefreshHud'))
    require('GetLocalPlayer' not in snapshot and not re.search(r'viewer|laneFilter|tdDamagePage', snapshot), 'Local/filtered packaged ranking')
    require(not re.search(r'tdSetupDamageUI|tdDamageViewer|tdDamagePage|tdResetDamageViews|TDDamageUI', script), 'Obsolete packaged hook')
    refresh = f['tdDamagePrepareHud'][4]
    require(re.search(r'set TDDamageHud_tdDamageHudCells\[[^\n]+\] = ""', refresh) and ' [退场]' in refresh and 'getSerial' not in refresh,
            'Packaged tail clearing/retirement contract')
    require(refresh.index('] = ""') < refresh.index('tdDamageSetHudCell('), 'Packaged clear must precede populate')
    for lane in range(4):
        require(len(re.findall(r'tdDamageSetPlayerHud\([^\n]*, ' + str(lane) + r',', refresh)) == 1,
                'Packaged duplicate/missing player selection')
    player = f['tdDamageSetPlayerHud'][4]
    require('tdDamagePlayerRank(' in player and len(re.findall(r'tdDamageSetHudCell\(', player)) == 2,
            'Packaged player row must use scalar rank and two cells')
    bridge = f['tdDamageRefreshHud'][4]
    require(bridge.count('tdDamagePrepareHud(') == 1 and all('tdIsLaneActive(' + str(i) + ')' in bridge for i in range(4)),
            'Packaged membership bridge must refresh once')
    require(len(re.findall(r'^string array TDDamageHud_tdDamageHudCells$', script, re.M)) == 1, 'Packaged scalar snapshot storage count')
    require(re.search(r'addUnreducedListener\(4,', f['tdSetupDamageStatistics'][4]), 'Packaged priority4 listener')
    require('call_doPeriodically_TDHud' in f, 'Missing packaged HUD periodic callback')
    timer = f['call_doPeriodically_TDHud'][4]
    require(re.search(r'call tdRefreshStatusBoard\([^\n]*\)\s+if tdIsGameOver\(\) then\s+call dispatch_CallbackPeriodic_destroyCallbackPeriodic\(', timer),
            'Packaged final refresh/timer stop')
    require('TDDamageLedger_reset' not in timer and 'tdResetDamageStatistics' not in timer, 'Packaged final timer resets ledger')
    for symbol, count in (('TD_DAMAGE_HUD_ROWS', 16), ('TD_DAMAGE_HUD_COLUMNS', 4), ('TD_DAMAGE_TOWER_TOP_COUNT', 10)):
        require(re.search(r'\bset \w*' + symbol + r' = ' + str(count) + r'\b', script), 'Packaged ranking constant changed: ' + symbol)
    periodic_setup = f['tdSetupHud'][4]
    require(len(re.findall(r'call doPeriodically\(1\.0,', periodic_setup)) == 1 and
            periodic_setup.count('multiboard_show(') == periodic_setup.count('multiboard_maximize(') == 1,
            'Packaged initial show/maximize/one-second timer contract')
    require('multiboard_maximize(' not in f['tdRefreshStatusBoard'][4] and
            'multiboard_show(' not in f['tdRefreshStatusBoard'][4], 'Packaged refresh forces native expansion')
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path); p.add_argument('--baseline-map', type=Path, required=True)
    p.add_argument('--root', type=Path, default=ROOT); a = p.parse_args()
    artifact, baseline = Mpq(a.map.read_bytes()), Mpq(a.baseline_map.read_bytes())
    count = verify_archive_delta(artifact, baseline)
    script = artifact.extract('war3map.j').decode('utf-8')
    comparisons, selections = verify_comparators(script), verify_player_selection(script)
    verify_packaged_structure(script); verify_source(a.root)
    # Final A's unchanged capture runtime guard must exist; no uncommitted A
    # source or permissive substitute is loaded during static preparation.
    capture = importlib.import_module('VerifyCaptureRemovalArtifact')
    before_script = baseline.extract('war3map.j').decode('utf-8')
    inherited_view, aliases = inherited_script_view(script, before_script)
    capture.verify_capture_runtime(inherited_view, before_script)
    boss = importlib.import_module('VerifyBossSpellResistanceArtifact')
    capture.verify_inherited_boss(inherited_view, before_script)
    # Actual behavior still executes the untouched final MPQ script.
    for name in ('verify_pure_and_runtime', 'verify_engine_and_accounting', 'verify_zero_engine_event',
                 'verify_setup_lifecycle', 'verify_scripted_damage', 'verify_compiled_structure'):
        getattr(boss, name)(script)
    print('PROVED MATH IDENTIFIER ALIASES:', aliases)
    boss.verify_source_contract(a.root / 'wurst')
    print(f'PASS: {comparisons} real comparator cases; {selections} participant selections; {count} predecessor members; Dsta-only delta.')
    print('NOT TESTED: native multiboard rendering, actual gameplay or engine timer scheduling.')


if __name__ == '__main__': main()
