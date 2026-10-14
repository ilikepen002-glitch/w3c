#!/usr/bin/env python3
"""Replay packed four-slot capture, session CD text and buff visual ownership.
Native handles, random draws, attack events and clock delivery are controlled
boundaries. This does not prove Warcraft rendering, native attack speed or FPS.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
from unittest.mock import patch
import VerifyPetCaptureBudgetArtifact as capture_replay
from GenerateTowerTerrainMask import Mpq
from VerifyCombatVisualArtifact import VisualRuntime
from VerifyElementalPetArtifact import ElementRuntime
from VerifyPetAttackArtifact import PetAttackRuntime, near
from VerifyEquipmentAbilityArtifact import require
from VerifyTowerUpgradeArtifact import rawcode
from SpiritVisualBudgetFixture import reserve, release, buff_count


class FourSlotRuntime(VisualRuntime):
    def __init__(self, script):
        self.roll_queue = []
        self.int_trace = []
        super().__init__(script)
        self.int_trace.clear()
        self.now = 0.  # This gate measures absolute cooldown/buff deadlines from the native fixture origin.

    def expression(self, text, scope):
        # Alias the actual packed error handler only for the parser's reserved
        # Python word. Its complete compiled body still runs.
        if text.startswith('try('):
            self.functions['packed_try'] = self.functions['try']
            text = 'packed_try' + text[3:]
        return super().expression(text, scope)

    def native(self, name, args):
        if name == 'ForForce':
            self.invoke(args[1]); return True, None
        if name == 'IsUnitType':
            require(args[0] in self.units, 'Unknown native fixture unit')
            return True, False  # The fixture host/enemy are neither mechanical nor hero.
        if name == 'GetRandomInt':
            value = self.roll_queue.pop(0) if self.roll_queue else args[0]
            require(args[0] <= value <= args[1], 'RNG fixture outside native range')
            self.int_trace.append((*args, value))
            return True, value
        return super().native(name, args)


def capture(script):
    cases = []
    # Orthogonal native boundaries, while the Wurst suite exhausts the full
    # 49ID x4slot x15species x4quality admission matrix independently.
    inputs = {(roll, 1, 45, 80, 50) for roll in (1, 55, 56, 90, 91, 100)}
    inputs.update((91, species, qroll, 80, branch)
                  for species in range(1, 16)
                  for qroll in (45, 46, 76, 96)
                  for branch in (50, 51, 75, 76))
    inputs.update((56, 1, qroll, group, 50)
                  for qroll in (45, 46, 75, 76, 95, 96)
                  for group in (80, 81))
    r = FourSlotRuntime(script)
    for count_roll, species, quality_roll, hero_branch, active_branch in sorted(inputs):
        r.executed_steps = 0  # Each capture is an independent native event.
        r.int_trace.clear()
        expected_count = 2 if count_roll <= 55 else (3 if count_roll <= 90 else 4)
        quality = 1 if quality_roll <= 45 else (2 if quality_roll <= 75 else (3 if quality_roll <= 95 else 4))
        p = r.invoke('new_TDPet', 0, species, 1)
        draws = [count_roll, quality_roll, 0, quality_roll, 0]
        if expected_count >= 3:
            draws += [quality_roll, hero_branch, 0]
        if expected_count == 4:
            draws += [quality_roll, active_branch]
        r.roll_queue = draws.copy()
        require(r.invoke('TDPet_rollCaptureSkills', p) is True, 'Valid capture did not complete')
        require(not r.roll_queue and len(r.int_trace) == {2: 5, 3: 8, 4: 10}[expected_count], 'Capture draw contract changed')
        require(r.globals['TDPet_skillCount'][p] == expected_count, 'Capture count distribution boundary changed')
        skills = [r.invoke('TDPet_skillAt', p, i) for i in range(expected_count)]
        expected = [0, 5]
        if expected_count >= 3:
            expected += [6 if hero_branch <= 80 else 39]
        if expected_count == 4:
            expected += [19 + ((species - 1) // 3) * 4 + quality - 1 if active_branch <= 50 else (11 if active_branch <= 75 else 12)]
        require(skills == expected and len(set(skills)) == len(skills), 'Role, duplicate, element or branch boundary changed')
        require(all(r.invoke('TDPet_qualityAt', p, i) == quality for i in range(expected_count)), 'Capture quality boundary changed')
        require(sum(r.invoke('tdPetSkillIsActive', x) for x in skills) == (expected_count == 4), 'Born-active admission changed')
        cases.append({'count': expected_count, 'species': species, 'quality': quality, 'hero': hero_branch, 'active': active_branch, 'draws': len(r.int_trace)})
        r.invoke('dispatch_TDPet_destroyTDPet', p)
    # No invalid input draws or partial record overwrite.
    r = FourSlotRuntime(script)
    p = r.invoke('new_TDPet', 0, 0, 1)
    require(r.invoke('TDPet_rollCaptureSkills', p) is False and not r.int_trace and r.globals['TDPet_skillCount'][p] == 0, 'Invalid species mutated capture or drew RNG')
    p = r.invoke('new_TDPet', 0, 1, 1)
    for slot, quality in ((-1, 1), (4, 1), (0, 0), (3, 5)):
        require(r.invoke('TDPet_rollSkill', p, slot, quality) == -1, 'Invalid roll admitted')
    require(not r.int_trace, 'Invalid rolls used randomness')
    r.invoke('TDPet_setSkill', p, 0, 0, 1)
    require(r.invoke('TDPet_rollCaptureSkills', p) is False and r.invoke('TDPet_skillAt', p, 0) == 0 and not r.int_trace, 'Capture overwrote existing record')
    # Mutate just the actual rollSkill body to reject slot1 after slot0 was
    # produced. The unchanged actual capture handler must discard/refund.
    match = re.search(r'^function TDPet_rollSkill takes ([^\n]+)\n(.*?)^endfunction', script, re.M | re.S)
    require(match is not None, 'Missing packed rollSkill failure fixture owner')
    arguments = re.findall(r'(?:integer|real|boolean|string) (\w+)', match.group(1))
    require(len(arguments) >= 3, 'Unknown packed rollSkill argument shape')
    slot_arg = arguments[1]
    body = match.group(2)
    lines = body.splitlines(True)
    first_statement = next(i for i, line in enumerate(lines) if line.strip() and not line.lstrip().startswith('local '))
    lines.insert(first_statement, '    if '+slot_arg+' == 1 then\n        return -1\n    endif\n')
    broken = script[:match.start(2)] + ''.join(lines) + script[match.end(2):]
    runtimes = []
    class FailedGenerationRuntime(capture_replay.CaptureRuntime):
        def __init__(self, packed):
            super().__init__(packed); runtimes.append(self)
    with patch.object(capture_replay, 'CaptureRuntime', FailedGenerationRuntime):
        result, _ = capture_replay.replay(broken, 'refund', 1, 1)
    failed = runtimes[0]
    require(result[0:2] == (3, 0) and result[-1] == 0, 'Failed generation spent ball, settled wild or stored partial pet')
    require(failed.calls.get('tdPetStore', 0) == 0, 'Partial generation reached collection insertion')
    return {'boundary_cases': len(cases), 'draws_by_count': {'2': 5, '3': 8, '4': 10}, 'invalid_zero_rng': True, 'mid_generation_refund': True}


def detail(script):
    r = FourSlotRuntime(script)
    p = r.pet([(11, 1)])
    session = r.invoke('new_TDPetUISession', 0)
    r.globals['TDPetUIState_tdPetUISessions'][0] = session
    def open_detail():
        require(r.invoke('TDPetUISession_open', session, 1, 0, 0, p, 0, 8000), 'Actual detail session rejected current record')
    def text(now):
        r.now = now
        r.invoke('tdPetRefreshDisplay', 0)
        return r.invoke('tdPetDetailHudTextForLane', 0)
    open_detail()
    r.globals['TDPet_readyAt'][p] = 14.
    require('冷却14秒' in text(0.), 'Detail does not read readyAt')
    require('冷却1秒' in text(13.999), 'Detail declared early readiness')
    require('就绪（待普攻）' in text(14.), 'Detail missed exact ready deadline')
    r.globals['TDPet_pendingSkill'][p] = True
    require('施放处理中' in text(14.), 'Pending CD state missing')
    r.globals['TDPet_pendingSkill'][p] = False
    r.globals['TDPet_buffSkill'][p] = 11
    r.globals['TDPet_buffUntil'][p] = 20.
    r.globals['TDPet_readyAt'][p] = 28.
    require('强化剩余6秒 / 冷却14秒' in text(14.), 'Buff/CD simultaneous state missing')
    require('强化剩余1秒' in text(19.999) and '强化剩余' not in text(20.), 'Buff text deadline changed')
    r.invoke('TDPetUISession_close', session)
    require(r.invoke('tdPetDetailHudTextForLane', 0) == '', 'Close retained detail HUD')
    open_detail(); text(20.)
    r.invoke('TDPet_invalidateCombat', p)
    require(r.invoke('tdPetDetailHudTextForLane', 0) == '', 'Generation invalidation retained cached detail')
    open_detail(); text(20.)
    r.globals['TDPet_level'][p] = 1
    require(r.invoke('tdPetDetailHudTextForLane', 0) == '', 'Stale resonance retained cached detail')
    open_detail()
    require('共鸣锁定' in text(20.), 'Owned fourth slot unlocked before wave8')
    r.globals['TDPet_level'][p] = 3
    open_detail(); r.globals['TDPet_host'][p] = None
    require('未绑定' in text(20.), 'Unbound restriction missing')
    r.globals['TDPet_paused'][p] = True
    open_detail()
    require('施工/升级暂停' in text(20.), 'Paused restriction missing')
    r.globals['TDPet_released'][p] = True
    require(r.invoke('tdPetDetailHudTextForLane', 0) == '', 'Release retained cached detail')
    return {'ceil_deadline': True, 'buff_plus_cd': True, 'pending': True, 'locked': True, 'unbound': True, 'paused': True, 'stale_close_release': True}


def offer_cdr(r, pet, reduction):
    if reduction:
        r.invoke('TDPet_setSkill', pet, 0, 3, 4)
        r.invoke('tdAuraRegisterTarget', 101, True)
        aura = r.invoke('tdAuraTargetFor', 101)
        aggregate = r.globals['TDAuraTarget_effective'][aura]
        r.invoke('TDAuraAggregate_offer', aggregate, 5, 4, .18, True)
        near(r.invoke('tdHostActiveCooldownReduction', 101), .4, 'Actual inspiration+aura40% cap')


def resonance(script):
    rows = []
    for level in (1, 2, 3):
        for skill in (11, 12):
            r = FourSlotRuntime(script); p = r.pet([(skill, 1)], level=level)
            r.emit(100.); r.tick_effects(0.)
            require(r.globals['TDPet_readyAt'][p] == (14. if level == 3 else 0.), 'Locked fourth slot triggered actual primary CD')
            require(r.globals['TDPet_buffSkill'][p] == (skill if level == 3 else -1), 'Locked fourth slot triggered buff')
            require(not r.globals['TDPet_pendingSkill'][p], 'Locked fourth slot queued an active')
            rows.append({'level': level, 'skill': skill, 'ready': r.globals['TDPet_readyAt'][p]})
    # A compatible final moon branch counts real primaries only after slot2
    # unlock. Inspect the actual registered counter, not a Python substitute.
    for level in (1, 2):
        r = FourSlotRuntime(script); p = r.pet([(40, 1)], level=level)
        r.units[101]['type'] = r.invoke('tdPetHeroHostTypeId', 40)
        require(r.invoke('tdPetSkillFitsHost', 40, 101), 'Hero resonance fixture lacks compatible final host')
        r.emit(100.); r.tick_effects(0.)
        table = r.tables[r.globals['TDPetHeroState_counters']]
        counter = table.get(p, 0)
        require(bool(counter) == (level == 2), 'Third-slot hero admitted before resonance')
        if counter:
            require(r.globals['TDPetHeroCounter_count'][counter] == 1, 'Actual primary did not advance hero counter')
        rows.append({'hero_level': level, 'counter': bool(counter)})
    return rows


def buffs(script):
    traces = []
    for skill in (11, 12):
        for reduction in (0., .4):
            for mode in ('normal', 'null', 'exhausted'):
                r = FourSlotRuntime(script); p = r.pet([(skill, 1)])
                offer_cdr(r, p, reduction)
                r.invoke('tdPetRefreshHost', 101, 0.)
                baseline = r.units[101]['abilities'].copy()
                r.reject_visual = mode == 'null'
                held = []
                if mode == 'exhausted':
                    r.now = -1.
                    held += reserve(r, 80)
                    r.now = 0.
                    held += reserve(r, 8)
                r.emit(100.); r.tick_effects(0.)
                cd = 14. * (1. - reduction)
                near(r.globals['TDPet_readyAt'][p], cd, 'Named buff actual cooldown')
                near(r.globals['TDPet_buffUntil'][p], 6., 'Named buff actual duration')
                require(r.globals['TDPet_buffSkill'][p] == skill and not r.native_damage, 'Named buff changed into damage')
                buffed = r.units[101]['abilities'].copy()
                bonus = rawcode('Pbsp') if skill == 11 else rawcode('Pbat')
                require(buffed.get(bonus, 0) > baseline.get(bonus, 0), 'Named buff did not install actual native bonus')
                require(buff_count(r) == (0 if mode == 'null' else 1),
                        'Decoration saturation starved the reserved buff core')
                before = {'ready': r.globals['TDPet_readyAt'][p], 'until': r.globals['TDPet_buffUntil'][p], 'power': r.globals['TDPet_buffPower'][p], 'score': r.score(), 'rng': r.random_real_draws.copy(), 'baseline': baseline, 'buffed': buffed}
                for now in (.1,):
                    r.now = now; r.emit(100.); r.tick_effects(0.)
                    require(r.globals['TDPet_readyAt'][p] == cd and r.globals['TDPet_buffUntil'][p] == 6., 'Pre-CD primary restarted buff')
                r.now = 5.999; r.invoke('tdPetRefreshHost', 101, 0.)
                require(r.units[101]['abilities'].get(bonus, 0) == buffed.get(bonus, 0), 'Native buff expired early')
                r.now = 6.; r.invoke('tdPetRefreshHost', 101, 0.); r.tick_visuals(0.)
                require(r.units[101]['abilities'].get(bonus, 0) == baseline.get(bonus, 0), 'Native bonus failed exact6second restoration')
                require(buff_count(r) == 0, 'Duration attachment did not expire')
                r.now = cd - .001; r.emit(100.); r.tick_effects(0.)
                require(r.globals['TDPet_readyAt'][p] == cd and r.globals['TDPet_buffUntil'][p] == 6., 'Last fractional cooldown second restarted buff')
                r.now = cd; r.emit(100.); r.tick_effects(0.)
                near(r.globals['TDPet_readyAt'][p], cd * 2., 'Named buff missed exact CD boundary')
                r.invoke('TDPet_recall', p)
                require(buff_count(r) == 0 and r.globals['TDPet_readyAt'][p] == cd * 2., 'Recall reset cooldown or leaked attachment')
                release(r, held); r.clear()
                traces.append({'skill': skill, 'cdr': reduction, 'mode': mode, 'gameplay': before, 'expired': True})
    for skill in (11, 12):
        for reduction in (0., .4):
            rows = [row['gameplay'] for row in traces if row['skill'] == skill and row['cdr'] == reduction]
            require(rows[0] == rows[1] == rows[2], 'Visual success/null/budget changed numeric/CD/RNG path')
    # One handle/source; all40 reserved cores succeed in one creation window.
    r = FourSlotRuntime(script)
    for i in range(41):
        host = 1000 + i
        r.units[host] = {**r.units[101], 'abilities': {}, 'inventory': {}, 'owner': 0, 'alive': True}
        r.invoke('tdCombatVisualStartPetBuff', host, 0, 11, 6.)
        require(buff_count(r) == min(i+1, 40),
                'Positive same-second40 buff attachments were starved')
    require(buff_count(r) == 40, 'Cap fixture did not reach40')
    r.now += 1.
    r.invoke('tdCombatVisualStartPetBuff', 1000, 0, 12, 6.)
    require(buff_count(r) == 40, 'Replacing source attachment exceeded cap')
    r.invoke('tdCombatVisualRefreshGear', 1000, 1, rawcode('iP01'), 0, 0)
    require(r.invoke('tdCombatVisualGearCount') == 1, 'Independent gear fixture missing')
    r.invoke('tdCombatVisualClearPet', 1000)
    require(buff_count(r) == 39 and r.invoke('tdCombatVisualGearCount') == 1, 'Pet cleanup removed gear or retained buff')
    r.invoke('tdCombatVisualClearLane', 0)
    require(buff_count(r) == 0 and not r.visual_handles, 'Lane clear leaked native handles')
    r.clear()
    for action in ('tdCombatVisualForgetSource', 'tdCombatVisualClearPet', 'tdCombatVisualShutdown'):
        r = FourSlotRuntime(script)
        r.invoke('tdCombatVisualStartPetBuff', 101, 0, 11, 6.)
        r.invoke(action, *([] if action.endswith('Shutdown') else [101]))
        require(buff_count(r) == 0, 'Lifecycle failed '+action)
    r = FourSlotRuntime(script)
    r.invoke('tdCombatVisualStartPetBuff', 101, 0, 11, 6.)
    r.invoke('tdResetWaveFlowState'); r.tick_visuals(.05)
    require(buff_count(r) == 0, 'Epoch reset retained buff')
    return {'named_modes': traces, 'one_per_host': True, 'global_cap': 40, 'gear_independent': True, 'lifecycle': True}


def rock(script):
    rows = []
    for reduction in (0., .4):
        r = ElementRuntime(script)
        p = r.pet(35)
        r.enemy(102); r.visible_units = [102]
        offer_cdr(r, p, reduction)
        cd = 10. * (1. - reduction)
        counts = []
        for t in (0., .1, cd - .001, cd):
            r.now = t; r.executed_steps = 0
            r.emit(100.); r.tick(0.)
            counts.append(len(r.native_damage))
        require(counts == [1, 1, 1, 2], 'Rock actual primary cooldown gate changed')
        rows.append({'cdr': reduction, 'deadline': r.globals['TDPet_readyAt'][p], 'hits': counts})
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('map', type=Path)
    a = p.parse_args()
    script = Mpq(a.map.read_bytes()).extract('war3map.j').decode('utf-8')
    require('tdPetSkillIsAttackPassive' in script, 'Map does not contain the four-role contract')
    report = {'sha256': hashlib.sha256(a.map.read_bytes()).hexdigest()}
    for name, run in (('capture', capture), ('detail', detail), ('resonance', resonance), ('buffs', buffs), ('rock', rock)):
        report[name] = run(script)
        print('PASS', name, flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
