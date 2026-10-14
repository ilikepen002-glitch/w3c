#!/usr/bin/env python3
"""Compare real baseline/candidate packed HUDs at unchanged refresh boundaries.

The production HUD preparation, ranking, local text selection and projection run.
Only native multiboard handles/rendering, the clock and inherited engine fixtures
are modeled. No patched old-map candidate, Warcraft synchronization or FPS claim.
"""
import argparse
import collections
import copy
import hashlib
from functools import cmp_to_key
import json
from pathlib import Path
import re
import subprocess

from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerEvolutionReplay import EvolutionRuntime


class HudRuntime(EvolutionRuntime):
    def __init__(self, script, local=0):
        self.local = local
        self.ui, self.items, self.boards = [], {}, {}
        self.preparation_trace = []
        self.drawing = False
        self.expression_count = 0
        self.item_serial = 200000
        super().__init__(script)
        # TrialHud already initializes through the production replay's dependency
        # spine. Initialize only the remaining HUD package-owned presentation data.
        for name in ('init_TDHudProjection', 'init_TDHud', 'init_TDDamageHud', 'init_TDPetUIState'):
            if name in self.functions:
                self.invoke(name)
        self.bind_board(999)

    def expression(self, text, scope):
        if self.drawing:
            self.expression_count += 1
        return super().expression(text, scope)

    def execute_call(self, name, args):
        if self.drawing and name in ('tdPetDetailHudTextForLane', 'tdDamageRefreshCatalog',
                                    'tdDamagePrepareHud', 'TDDamageLedger_refreshOrder',
                                    'dispatch_LinkedList_LinkedList_sortWith', 'tdTrialPrepareHud'):
            self.preparation_trace.append(name)
        return super().execute_call(name, args)

    def bind_board(self, board):
        self.globals['TDHud_tdStatusBoard'] = board
        self.boards[board] = {'title': '', 'cells': {
            (row, col): {'value': '', 'icon': '', 'style': (True, False)}
            for row in range(31) for col in range(4)}}

    def native(self, name, args):
        if name in ('tdRefreshStatusBoard', 'tdDamageRefreshCatalog',
                    'tdDamageRefreshHud', 'tdTrialRefreshHud'):
            return False, None
        if name == 'dispatch_LinkedList_LinkedList_sortWith':
            values, comparator = self.lists[args[0]], args[1]
            values.sort(key=cmp_to_key(lambda left, right: self.invoke('dispatch_Comparator_Comparator_compare', comparator, left, right)))
            return True, None
        if name == 'GetLocalPlayer':
            return True, self.local
        if name.startswith('Multiboard'):
            if name == 'MultiboardGetItem':
                board, row, col = args
                require((row, col) in self.boards[board]['cells'], 'Out-of-range HUD item')
                self.item_serial += 1
                self.items[self.item_serial] = (board, row, col)
                self.ui.append((name, (board, row, col)))
                return True, self.item_serial
            if name == 'MultiboardSetTitleText':
                self.boards[args[0]]['title'] = args[1]
                self.ui.append((name, tuple(args)))
                return True, None
            require(args[0] in self.items, 'Unknown or released multiboard item: ' + name)
            board, row, col = self.items[args[0]]
            cell = self.boards[board]['cells'][(row, col)]
            self.ui.append((name, (board, row, col, *args[1:])))
            if name == 'MultiboardSetItemValue': cell['value'] = args[1]
            elif name == 'MultiboardSetItemIcon': cell['icon'] = args[1]
            elif name == 'MultiboardSetItemStyle': cell['style'] = tuple(args[1:])
            elif name == 'MultiboardReleaseItem': del self.items[args[0]]
            else: raise ValueError('Unmodeled multiboard native: ' + name)
            return True, None
        return super().native(name, args)

    def draw(self):
        self.ui.clear()
        self.executed_steps = 0
        self.preparation_trace.clear()
        self.expression_count = 0
        self.drawing = True
        self.invoke('tdRefreshStatusBoard')
        self.drawing = False
        require(not self.items, 'Refresh leaked a multiboard item handle')
        return {'view': copy.deepcopy(self.boards), 'calls': copy.deepcopy(self.ui),
                'interpreter_steps': self.executed_steps, 'evaluated_expressions': self.expression_count, 'preparation_trace': list(self.preparation_trace)}

    def set_active_lanes(self, lanes):
        for lane in range(4): self.invoke('tdSetLaneActive', lane, lane in lanes)

    def add_rankings(self):
        records = []
        for index in range(14):
            record = self.invoke('TDDamageLedger_register', self.ledger, index % 4, '测试塔' + str(index))
            self.invoke('TDDamageLedger_credit', self.ledger, record, float(index // 2 + 1), 100.)
            records.append(record)
        self.globals['TDDamageRecord_retired'][records[-1]] = True
        self.globals['TDDamageRecord_label'][records[-2]] = '升级后的塔'

    def trial(self):
        generation = self.state_call('getGeneration')
        require(self.state_call('prepare', 8, 5, generation, 0.), 'Trial prepare fixture')
        for lane in range(4):
            self.state_call('snapshotLane', lane, True)
            for slot in range(5):
                self.state_call('bindTarget', lane, slot, lane * 5 + slot + 1, 5, generation, 0.)
        require(self.state_call('activate', 5, generation, 0.), 'Trial activate fixture')
        for lane, amount in enumerate((20.25, 10., 0.125, 20.)):
            ticket = self.state_call('hitTicket', lane, 0, lane * 5 + 1, 5, generation, 1., 1000000.)
            require(ticket, 'Trial score fixture')
            self.state_call('credit', ticket, lane, amount, 1.)
            self.invoke('dispatch_TDTrialHitTicket_destroyTDTrialHitTicket', ticket)
        self.now = 20.

    def detail(self):
        for lane in range(4):
            pet = self.record(lane=lane)
            session = self.invoke('new_TDPetUISession', lane)
            self.globals['TDPetUIState_tdPetUISessions'][lane] = session
            require(self.invoke('TDPetUISession_open', session, 1, 0, 0, pet, 0, 700000 + lane), 'Pet detail fixture')
            self.globals['TDPetUISession_detailHudText'][session] = '详情 P' + str(lane + 1)


def snapshots(script, local):
    r = HudRuntime(script, local)
    out = {}
    def draw(label): out[label] = r.draw()
    r.set_active_lanes([0]); draw('one_first'); draw('one_unchanged')
    r.invoke('tdLoseLife', 0, 1); draw('one_life_changed')
    r.globals['TDState_tdDifficulty'] = 2; draw('title_changed')
    r.invoke('tdSetGlobalWave', 7); draw('boss_preview')
    r.invoke('tdSetGlobalWave', 8); draw('boss_current')
    r.set_active_lanes(range(4)); draw('four_layout'); draw('four_unchanged')
    r.add_rankings(); draw('rankings_ties_retired_top10'); draw('rankings_unchanged')
    r.invoke('TDDamageLedger_reset', r.ledger)
    r.invoke('TDDamageLedger_register', r.ledger, 2, '唯一新塔')
    draw('rankings_tail_clear')
    r.detail(); draw('pet_details'); draw('pet_details_unchanged')
    session = r.globals['TDPetUIState_tdPetUISessions'][0]
    r.globals['TDPetUISession_detailHudText'][session] = '详情 P1 已更新'
    draw('only_local_zero_detail_changed')
    r.globals['TDPetUISession_dirty'][session] = True; draw('pet_stale_detail')
    r.trial(); draw('trial_active_ties'); draw('trial_unchanged')
    r.now = 21.; draw('trial_next_second')
    r.state_call('withdraw', 1); draw('trial_withdrawn')
    r.state_call('seal', 5, r.state_call('getGeneration'), 2, 120.)
    r.now = 120.; draw('trial_settled')
    r.state_call('reset'); draw('trial_reset')
    r.set_active_lanes([2]); draw('four_to_one_layout'); draw('one_after_layout_unchanged')
    r.set_active_lanes(range(4)); draw('one_to_four_layout')
    r.bind_board(1000); draw('board_identity_changed'); draw('new_board_unchanged')
    r.invoke('tdSetLaneDefeated', 0, True); draw('lane_defeated')
    r.invoke('tdSetGameOver', True); draw('defeat_final'); draw('defeat_final_unchanged')
    r.invoke('tdSetLaneFinished', 2, True); draw('victory_final'); draw('victory_final_unchanged')
    return out


def skeleton(calls):
    # Item identities above are normalized to their board/row/column. Only text
    # values may differ across clients; icon/style/title and call order may not.
    return [(name, args[:3] if name == 'MultiboardSetItemValue' else args) for name, args in calls]


def summary(snapshot):
    serial = [(board, data['title'], sorted(data['cells'].items())) for board, data in sorted(snapshot['view'].items())]
    return {'native_calls': dict(collections.Counter(name for name, _ in snapshot['calls'])),
            'total_native_calls': len(snapshot['calls']),
            'interpreter_steps': snapshot['interpreter_steps'],
            'evaluated_expressions': snapshot['evaluated_expressions'],
            'preparation_trace': snapshot['preparation_trace'],
            'final_board_sha256': hashlib.sha256(json.dumps(serial, ensure_ascii=False).encode()).hexdigest()}


def verify_clients(replays):
    reference = replays[0]
    for local, cases in replays.items():
        for label, case in cases.items():
            require(skeleton(case['calls']) == skeleton(reference[label]['calls']),
                    f'Client-dependent handle/native skeleton: local={local}, {label}')


def verify_mutation(script):
    # Convert only the local baby cell to the synchronized dirty cache. Correct
    # pixels still result, but the P1-only update must break the client skeleton.
    pattern = r'call multiboard_setItemValue\(TDHud_tdStatusBoard, (\w+), 2, (TDHud_tdPetHudSummaries\[[^\]]+\]|"旁观")\)'
    runtime = HudRuntime(script)
    setter = 'tdHudProjectionSetValue'
    require(setter in runtime.functions, 'Projection mutation setter missing')
    stack = ', "negative local-cache mutation"' if len(runtime.functions[setter][0]) == 5 else ''
    changed, count = re.subn(pattern, lambda match: f'call {setter}(0, {match[1]}, 2, {match[2]}{stack})', script)
    require(count == 2, 'Local-cell dirty mutation target missing')
    caught = False
    try:
        verify_clients({local: snapshots(changed, local) for local in (0, 1)})
    except ValueError as error:
        require('Client-dependent handle/native skeleton' in str(error), 'Mutation failed for unrelated reason: ' + str(error))
        caught = True
    require(caught, 'Client-local dirty mutation was not detected')
    return {'local_cell_dirty_handle_divergence_detected': True}


def verify_projection_properties(script):
    r = HudRuntime(script)
    def call(method, *args): return r.invoke('tdHudProjection' + method[0].upper() + method[1:], 0, *args)
    call('bind', 999, 0, 9, 4)
    for method, args, expected in (
        ('setValue', (1, 0, ''), 3), ('setValue', (1, 0, ''), 0),
        ('setValue', (1, 0, 'text'), 3), ('setIcon', (1, 0, ''), 3),
        ('setIcon', (1, 0, ''), 0), ('setIcon', (1, 0, 'icon.blp'), 3),
        ('setStyle', (1, 0, False, False), 3), ('setStyle', (1, 0, False, False), 0),
        ('setStyle', (1, 0, True, False), 3), ('setTitle', ('',), 1),
        ('setTitle', ('',), 0), ('setTitle', ('new',), 1)):
        r.ui.clear(); call(method, *args)
        require(len(r.ui) == expected and not r.items, 'Independent property cache failed: ' + method)
    for first, rows, cols in ((1, 9, 4), (1, 8, 4), (1, 8, 3)):
        call('bind', 999, first, rows, cols)
        r.ui.clear(); call('setValue', 1, 0, 'text')
        require(len(r.ui) == 3, 'Layout/dimension cache was not invalidated')
    return {'independent_value_icon_style_title': True, 'move_resize_invalidation': True}


def read_map(path):
    data = path.read_bytes()
    script = Mpq(data).extract('war3map.j').decode('utf-8')
    return script, {'path': str(path.resolve()), 'map_sha256': hashlib.sha256(data).hexdigest(),
                    'jass_sha256': hashlib.sha256(script.encode()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-map', type=Path, required=True)
    parser.add_argument('--candidate-map', type=Path)
    parser.add_argument('--source-commit')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    baseline, baseline_meta = read_map(args.baseline_map)
    baseline_runs = {local: snapshots(baseline, local) for local in (0, 1, 2, 3, 15)}
    verify_clients(baseline_runs)
    require(len(baseline_runs[0]['one_first']['calls']) == 328, 'Baseline one-lane count differs')
    require(len(baseline_runs[0]['four_unchanged']['calls']) == 355, 'Baseline four-lane count differs')
    result = {'baseline': baseline_meta, 'clients': [0, 1, 2, 3, 15],
              'baseline_cases': {key: summary(value) for key, value in baseline_runs[0].items()}}
    if args.candidate_map:
        candidate, candidate_meta = read_map(args.candidate_map)
        require(candidate_meta['jass_sha256'] != baseline_meta['jass_sha256'], 'Candidate must be a newly packed script')
        candidate_runs = {local: snapshots(candidate, local) for local in (0, 1, 2, 3, 15)}
        verify_clients(candidate_runs)
        for local, cases in candidate_runs.items():
            for label, case in cases.items():
                require(case['view'] == baseline_runs[local][label]['view'],
                        f'Final board differs from complete baseline refresh: local={local}, {label}')
                require(case['preparation_trace'] == baseline_runs[local][label]['preparation_trace'],
                        f'Preparation/catalog/sort invocation order changed: local={local}, {label}')
                if label.endswith('unchanged'):
                    require(len(case['calls']) == 3, 'Unchanged refresh wrote beyond the local baby cell: ' + label)
                    require(case['evaluated_expressions'] < baseline_runs[local][label]['evaluated_expressions'],
                            'Unchanged projection did not reduce evaluated expression work: ' + label)
        require(len(candidate_runs[0]['one_first']['calls']) == 328, 'First draw is incomplete')
        require(len(candidate_runs[0]['one_life_changed']['calls']) == 6, 'One changed cell must write exactly itself plus baby text')
        require(len(candidate_runs[0]['board_identity_changed']['calls']) == 355, 'New board missed full projection')
        result.update(candidate=candidate_meta, equivalent_final_boards=len(candidate_runs) * len(candidate_runs[0]),
                      candidate_cases={key: summary(value) for key, value in candidate_runs[0].items()},
                      properties=verify_projection_properties(candidate), mutation=verify_mutation(candidate))
    root = Path(__file__).resolve().parents[1]
    result['source_commit'] = args.source_commit or subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    result['source_tree_dirty'] = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip())
    result['boundary'] = ('Actual supplied MPQ JASS. Native board cells/handles and engine clock modeled, not rendered. '
                          'All three production preparation and refresh functions execute, including catalog and sort timing; '
                          'the inherited collection boundary uses a modeled list sort with the actual packed comparator. '
                          'Interpreter steps include inactive-branch scans; evaluated expressions count only evaluated expression entries. '
                          'Neither count is JASS VM operations, milliseconds, FPS or engine synchronization proof.')
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
