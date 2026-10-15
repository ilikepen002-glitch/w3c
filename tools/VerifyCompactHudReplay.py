#!/usr/bin/env python3
"""Replay the packed compact/detail HUD; engine multiboard rendering is modeled.
No Warcraft launch, pixel-layout, multiplayer networking, timing or FPS claim.
"""
import argparse
import collections
import copy
import json
import re
from pathlib import Path

from VerifyHudProjectionReplay import HudRuntime, read_map, skeleton, summary
from VerifyEquipmentAbilityArtifact import require


class CompactRuntime(HudRuntime):
    def __init__(self, script, local=0):
        self.chat_text = ''
        self.board_serial = 2000
        self.chat_events = []
        super().__init__(script, local)
        if 'TDHud_tdCompactBoard' in self.globals:
            self.globals['TDHud_tdCompactBoard'] = 998
            self.make_board(998, 0)
        self.boards[999].update(rows=31, columns=4, visible=False, minimized=False)

    def make_board(self, ident, rows=0):
        self.boards[ident] = {'title': '', 'rows': rows, 'columns': 4,
                             'visible': False, 'minimized': False,
                             'cells': {(r, c): self.empty_cell() for r in range(rows) for c in range(4)}}

    @staticmethod
    def empty_cell():
        return {'value': '', 'icon': '', 'style': (True, False), 'width': 0.0}

    def native(self, name, args):
        if name == 'CreateMultiboard':
            self.board_serial += 1
            self.make_board(self.board_serial)
            self.ui.append((name, (self.board_serial,)))
            return True, self.board_serial
        if name == 'IsMultiboardDisplayed':
            # A local read, not a handle acquisition or a native UI write.
            return True, self.boards[args[0]]['visible']
        if name == 'GetEventPlayerChatString': return True, self.chat_text
        if name == 'TriggerRegisterPlayerChatEvent':
            self.chat_events.append(tuple(args)); return True, None
        if name in ('MultiboardSetRowCount', 'MultiboardSetColumnCount',
                    'MultiboardSetItemsStyle', 'MultiboardSetItemsValue', 'MultiboardSetItemsIcon',
                    'MultiboardDisplay', 'MultiboardMinimize'):
            board = self.boards[args[0]]
            self.ui.append((name, tuple(args)))
            if name == 'MultiboardSetRowCount':
                board['rows'] = args[1]
                board['cells'] = {(r, c): board['cells'].get((r, c), self.empty_cell())
                                  for r in range(args[1]) for c in range(board['columns'])}
            elif name == 'MultiboardSetColumnCount': board['columns'] = args[1]
            elif name == 'MultiboardDisplay':
                if args[1]:
                    for other in self.boards.values(): other['visible'] = False
                board['visible'] = args[1]
            elif name == 'MultiboardMinimize': board['minimized'] = args[1]
            else:
                field = {'MultiboardSetItemsStyle': 'style', 'MultiboardSetItemsValue': 'value',
                         'MultiboardSetItemsIcon': 'icon'}[name]
                for cell in board['cells'].values():
                    cell[field] = tuple(args[1:]) if field == 'style' else args[1]
            return True, None
        if name == 'MultiboardSetItemWidth':
            require(args[0] in self.items, 'Width applied to unknown/released item')
            board, row, col = self.items[args[0]]
            self.boards[board]['cells'][(row, col)]['width'] = args[1]
            self.ui.append((name, (board, row, col, args[1])))
            return True, None
        return super().native(name, args)

    def chat(self, viewer, text):
        self.actor, self.chat_text = viewer, text
        self.invoke('tdHudHandleChat')
        # The production command queues a zero-delay render. The test explicitly
        # executes that render boundary, never stubs the production HUD itself.
        self.globals['TDHud_tdHudRefreshPending'] = False

    def startup(self):
        self.globals['TDHud_tdStatusBoard'] = None
        self.globals['TDHud_tdCompactBoard'] = None
        self.boards.clear(); self.ui.clear()
        self.invoke('tdSetupHud')
        require(len(self.boards) == 2, 'Setup must create exactly two synchronized boards')
        require(len(self.chat_events) == 16, 'Chat command missing player/observer registration')
        full = self.globals['TDHud_tdStatusBoard']
        compact = self.globals['TDHud_tdCompactBoard']
        self.invoke('tdSetupHud')
        require(len(self.boards) == 2, 'Repeated setup allocated extra boards')
        return full, compact


def handle_skeleton(calls):
    return skeleton([(name, args) for name, args in calls
                     if name not in ('MultiboardDisplay', 'MultiboardMinimize')])


def row_text(board):
    return [' | '.join(board['cells'][(r, c)]['value'] for c in range(4)) for r in range(board['rows'])]


def scenarios(script, local):
    r = CompactRuntime(script, local)
    full, compact = r.startup()
    out = {}
    def draw(label):
        snapshot = r.draw()
        snapshot['rows'] = {key: row_text(value) for key, value in snapshot['view'].items()}
        for board_id, board in snapshot['view'].items():
            if not board['cells'] or board['rows'] == 1: continue
            limit = 0.25 if board_id == compact else 0.355
            for row in range(board['rows']):
                width = sum(board['cells'][(row, col)]['width'] for col in range(4))
                require(abs(width - limit) < 0.00001, 'Board row exceeds its compact width budget')
        out[label] = snapshot
        return snapshot
    r.set_active_lanes([0]); draw('one_first'); draw('one_unchanged')
    require(r.boards[compact]['rows'] == 3 and r.boards[compact]['visible'], 'Default must be three visible compact rows')
    require(not r.boards[full]['visible'] and r.boards[full]['rows'] == 1, 'Default must not prepare the full board')
    r.chat(0, '-hud full'); draw('one_full_first'); draw('one_full_unchanged')
    require(r.boards[full]['rows'] == 8, 'One-player empty full board must use eight actual rows')
    require(r.boards[full]['visible'] == (local == 0), 'Full command leaked visibility to other clients')
    r.chat(0, '-hud compact'); draw('all_compact_again')
    r.set_active_lanes(range(4)); draw('four_compact'); draw('four_compact_unchanged')
    require(r.boards[compact]['rows'] == 6, 'Four-player compact board must use six rows')
    r.add_rankings(); draw('compact_rankings'); draw('compact_rankings_unchanged')
    require('tdDamagePrepareHud' not in out['compact_rankings']['preparation_trace'], 'Compact view prepared hidden tower rankings')
    r.chat(1, '-hud'); draw('mixed_full_first'); draw('mixed_full_unchanged')
    require(r.boards[full]['rows'] == 25, 'Populated full board must show 9 status + 16 ranking rows')
    for snap in out.values():
        require(snap['preparation_trace'].count('tdDamagePrepareHud') <= 1, 'Duplicated ranking snapshot preparation')
        require(snap['preparation_trace'].count('tdTrialPrepareHud') == 1, 'Duplicated trial snapshot preparation')
    r.invoke('tdSetGlobalWave', 24)
    r.start_boss(0); r.now += 5.; draw('boss_countdown')
    require('85s' in r.boards[compact]['title'], 'Compact title lost the actual boss deadline')
    require(r.boards[compact]['cells'][(5, 2)]['value'] == '暗潮减攻速 · 预告1秒', 'Compact threat retained the long detail paragraph')
    r.invoke('tdResetWaveFlowState'); r.now = 0.; r.invoke('tdSetGlobalWave', 1)
    r.detail(); draw('pet_detail')
    session = r.globals['TDPetUIState_tdPetUISessions'][0]
    r.globals['TDPetUISession_detailHudText'][session] = '仅P1变化'
    draw('pet_only_one_local_changed'); draw('pet_unchanged')
    r.trial(); draw('trial_active'); draw('trial_unchanged')
    require(r.boards[compact]['rows'] == 7 and r.boards[full]['rows'] == 31, 'Trial must add one compact row or six detailed rows')
    r.now = 21.; draw('trial_second')
    r.state_call('withdraw', 1); draw('trial_withdrawn')
    r.state_call('seal', 5, r.state_call('getGeneration'), 2, 120.)
    r.now = 120.; draw('trial_settled')
    require(r.boards[compact]['rows'] == 6 and r.boards[full]['rows'] == 31, 'Settled trial should remain in detail only')
    r.state_call('reset'); draw('trial_reset')
    require(r.boards[full]['rows'] == 25, 'Idle trial left empty rows')
    r.invoke('TDDamageLedger_reset', r.ledger)
    r.invoke('TDDamageLedger_register', r.ledger, 2, '唯一新塔'); draw('tower_tail_shrink')
    require(r.boards[full]['rows'] == 16, 'Empty tower tail survived shrinking')
    r.set_active_lanes([2]); draw('lane_shrink')
    require(r.boards[compact]['rows'] == 3 and r.boards[full]['rows'] == 10, 'Inactive player rows survived shrinking')
    r.chat(1, '-hud compact'); draw('hide_last_full')
    r.invoke('tdLoseLife', 2, 1); draw('hidden_full_stale')
    r.chat(15, '-hud full'); draw('observer_first_full')
    require(r.boards[full]['visible'] == (local == 15), 'Observer command leaked display')
    full_player = r.boards[full]['cells'][(1, 1)]['value']
    require(full_player == str(r.invoke('tdGetLives', 2)), 'First full opening showed stale life')
    for index in range(20):
        viewer = (0, 1, 2, 3, 15)[index % 5]
        r.chat(viewer, '-hud'); draw('toggle_' + str(index))
    r.chat(2, '-hud nonsense'); draw('invalid_command')
    # Same native row count, but different section boundaries: styles and icons
    # must be invalidated as well as values when trial rows replace tower rows.
    r.set_active_lanes(range(4)); r.chat(15, '-hud full')
    r.invoke('TDDamageLedger_reset', r.ledger); r.add_rankings(); draw('same_size_before')
    r.invoke('TDDamageLedger_reset', r.ledger)
    for lane in range(4): r.invoke('TDDamageLedger_register', r.ledger, lane, '短榜塔')
    r.trial(); draw('same_size_active')
    require(r.boards[full]['rows'] == 25 and r.boards[full]['cells'][(19, 0)]['style'] == (True, True),
            'Same-size section move failed to render the trial icon')
    r.state_call('reset'); r.add_rankings(); draw('same_size_after')
    require(r.boards[full]['rows'] == 25 and r.boards[full]['cells'][(19, 0)]['style'] == (True, False)
            and r.boards[full]['cells'][(19, 0)]['icon'] == '', 'Old trial icon/style leaked into a tower row')
    # Identical commands on every client; visibility and fold state stay local.
    for mode, selected, other in (('compact', compact, full), ('full', full, compact)):
        for viewer in (0, 1, 2, 3, 15):
            r.chat(viewer, '-hud ' + mode)
        draw(mode + '_recovery_mode')
        for folded in (False, True):
            r.boards[selected]['minimized'] = folded
            snapshot = draw(mode + '_manual_fold_' + str(folded))
            require(r.boards[selected]['minimized'] == folded, 'Refresh changed manual fold state')
            require(not any(name == 'MultiboardMinimize' for name, _ in snapshot['calls']),
                    'Normal refresh forced the board open')
            steady_calls = snapshot['calls']
            r.boards[selected]['visible'] = False
            snapshot = draw(mode + '_recover_hidden_' + str(folded))
            require(r.boards[selected]['visible'] and not r.boards[other]['visible'],
                    'Refresh failed to restore the selected HUD mode')
            require(r.boards[selected]['minimized'] == folded, 'Recovery changed manual fold state')
            require([call for call in snapshot['calls'] if call[0] != 'MultiboardDisplay'] == steady_calls
                    and sum(name == 'MultiboardDisplay' for name, _ in snapshot['calls']) == 1,
                    'Visibility recovery allocated extra handles or rewrote the board')
            snapshot = draw(mode + '_recovered_stable_' + str(folded))
            require(snapshot['calls'] == steady_calls, 'Recovered board added repeated native UI writes')
    r.invoke('tdSetGameOver', True); draw('game_over')
    r.chat(0, '-hud full'); draw('game_over_switch')
    require(len(r.boards) == 2 and not r.items, 'Repeated switching leaked native handles')
    return out, full, compact


def compare_clients(runs):
    reference = runs[0][0]
    for local, (cases, _, _) in runs.items():
        for name, case in cases.items():
            require(handle_skeleton(case['calls']) == handle_skeleton(reference[name]['calls']),
                    f'Client-dependent handle skeleton: local={local}, case={name}')


def verify_local_cache_mutation(script):
    # A local-text dirty cache may preserve visible text while skipping native
    # item handle acquisition on just one client. The multi-client gate must fail.
    pattern = r'call multiboard_setItemValue\(TDHud_tdStatusBoard, (\w+), 2, (TDHud_tdPetHudSummaries\[[^\]]+\]|"旁观")\)'
    runtime = CompactRuntime(script)
    suffix = ', "negative local cache mutation"' if len(runtime.functions['tdHudProjectionSetValue'][0]) == 5 else ''
    mutated, count = re.subn(pattern, lambda m: f'call tdHudProjectionSetValue(0, {m[1]}, 2, {m[2]}{suffix})', script)
    require(count == 2, 'Missing production local baby-cell mutation targets')
    caught = False
    try:
        compare_clients({local: scenarios(mutated, local) for local in (0, 1)})
    except ValueError as error:
        require('Client-dependent handle skeleton' in str(error), 'Unrelated mutation failure: ' + str(error))
        caught = True
    require(caught, 'Local cell handle divergence mutation was not detected')
    return {'local_text_dirty_cache_handle_divergence_detected': True}


def baseline_costs(script):
    r = HudRuntime(script)
    out = {}
    r.set_active_lanes([0]); r.draw(); out['one_unchanged'] = summary(r.draw())
    r.set_active_lanes(range(4)); r.draw(); out['four_unchanged'] = summary(r.draw())
    r.add_rankings(); r.draw(); out['rankings_unchanged'] = summary(r.draw())
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate-map', required=True, type=Path)
    p.add_argument('--baseline-map', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    script, meta = read_map(a.candidate_map)
    baseline, base_meta = read_map(a.baseline_map)
    runs = {local: scenarios(script, local) for local in (0, 1, 2, 3, 15)}
    compare_clients(runs)
    cases, full, compact = runs[0]
    baseline_cases = baseline_costs(baseline)
    for label, old in (('one_unchanged', 'one_unchanged'), ('four_compact_unchanged', 'four_unchanged'),
                       ('compact_rankings_unchanged', 'rankings_unchanged')):
        require(len(cases[label]['calls']) == 0, 'Unchanged compact board made native writes')
        require(cases[label]['evaluated_expressions'] < baseline_cases[old]['evaluated_expressions'],
                'Compact board regressed expression work')
    report = {'status': 'PASS', 'candidate': meta, 'baseline': base_meta,
              'clients': [0, 1, 2, 3, 15], 'cases_per_client': len(cases), 'width_budget': {'compact': 0.25, 'full': 0.355},
              'candidate_cases': {label: summary(snap) for label, snap in cases.items()},
              'baseline_costs': baseline_cases, 'mutation': verify_local_cache_mutation(script),
              'layout_evidence': {label: {'compact': snap['rows'][compact], 'full': snap['rows'][full]}
                                  for label, snap in cases.items() if label in
                                  ('one_first', 'one_full_first', 'four_compact', 'mixed_full_first', 'trial_active', 'tower_tail_shrink')},
              'boundary': 'Exact packed JASS; modeled engine multiboard handles/clock/events. No rendered screenshot, Warcraft multiplayer or FPS claim.'}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('PASS: compact/detail actual packed HUD; five client handle traces, lazy shared snapshots, resize, trials, observers, repeated switch and cost comparison')


if __name__ == '__main__': main()
