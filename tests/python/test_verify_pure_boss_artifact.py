"""Closed-delta mutation tests using immutable formal manager 654771b, never MPQ editing.

Source tests inspect the real candidate sources. Object/resource fixtures are
explicit synthetic expected deltas; they are NOT described as compiled output.
Set PURE_BOSS_CANDIDATE_MAP and PURE_BOSS_BASELINE_SOURCE to add actual final-MPQ
runtime tests after the serial, authorized build has produced a candidate.
"""
from collections import OrderedDict, Counter
from copy import deepcopy
from dataclasses import replace
import os
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyPureBossArtifact as gate
from VerifySemanticIconArtifact import Field, Object, parse_objects
from GenerateTowerTerrainMask import Mpq
from VerifyBossSpellResistanceArtifact import BossJassRuntime
from VerifyTowerUpgradeArtifact import JassScalarEvaluator

FORMAL_B7 = '654771baa872241cf572b16a0ef884436fe4818c'


class PureBossInterpreterControlFlowTests(unittest.TestCase):
    """Synthetic evaluator unit cases, never substitutes for packaged gameplay."""
    def run_scalar(self, body):
        script = 'function probe takes nothing returns integer\n' + body + '\nendfunction\n'
        runtime = object.__new__(BossJassRuntime)
        JassScalarEvaluator.__init__(runtime, script)
        runtime.globals, runtime.calls = {}, Counter()
        runtime.execution_depth = runtime.executed_steps = 0
        runtime.native = lambda name, args: (False, None)
        return runtime.invoke('probe')

    def test_exitwhen_inside_if_unwinds_only_the_current_loop_branches(self):
        self.assertEqual(self.run_scalar('''local integer value
set value = 0
if true then
    loop
        set value = value + 1
        if value == 2 then
            if true then
                exitwhen true
            endif
        endif
    endloop
    set value = value + 10
else
    set value = 100
endif
return value'''), 12)

    def test_nested_loop_exit_and_inactive_loop_preserve_outer_control(self):
        self.assertEqual(self.run_scalar('''local integer outer
local integer total
set outer = 0
set total = 0
loop
    exitwhen outer == 3
    loop
        if true then
            set total = total + 1
            exitwhen true
        endif
    endloop
    set outer = outer + 1
endloop
if false then
    loop
        exitwhen false
    endloop
else
    set total = total + 7
endif
return total'''), 10)


def formal_sources():
    paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', FORMAL_B7, 'wurst'], cwd=ROOT).decode().splitlines()
    return {p.removeprefix('wurst/'): subprocess.check_output(['git', 'show', FORMAL_B7 + ':' + p], cwd=ROOT).decode()
            for p in paths if p.endswith('.wurst') and '/_tests/' not in p}


def altered_field(field, new):
    payload = new.encode() + b'\0' if field.kind == 3 else struct.pack('<i' if field.kind == 0 else '<f', new)
    header = len(field.raw) - (len(field.value.encode()) + 1 if field.kind == 3 else 4) - 4
    return replace(field, value=new, raw=field.raw[:header] + payload + field.raw[-4:])


def synthetic_expected_objects(before):
    after = deepcopy(before)
    abilities, units = after['war3map.w3a'], after['war3map.w3u']
    del abilities['Emar']
    dark = OrderedDict()
    for key, kind, value in [(('wurs', 0, 0), 0, 42), (('anam', 0, 0), 3, '暗潮攻速削减'), (('Isx1', 1, 1), 2, -.20),
                              (('aite', 0, 0), 0, 1), (('achd', 0, 0), 0, 0)]:
        payload = value.encode() + b'\0' if kind == 3 else struct.pack('<i' if kind == 0 else '<f', value)
        raw = key[0].encode() + struct.pack('<III', kind, key[1], key[2]) + payload + b'\0' * 4
        actual = struct.unpack('<f', struct.pack('<f', value))[0] if kind in (1, 2) else value
        dark[key] = Field(key, kind, actual, raw)
    abilities['Ebtd'] = Object(1, b'AIsxEbtd', dark)
    evolution = abilities['A130']
    evolution.fields = {key: field for key, field in evolution.fields.items() if key[1] <= 475}
    for key, field in list(evolution.fields.items()):
        if key == ('alev', 0, 0): evolution.fields[key] = altered_field(field, 475)
        elif key[0] == 'aub1': evolution.fields[key] = altered_field(field, field.value.replace('达到250击杀', '达到220击杀'))
    status = abilities['AeEV']
    key = ('aub1', 1, 0)
    status.fields[key] = altered_field(status.fields[key], status.fields[key].value.replace('累计250击杀', '累计220击杀'))
    for wave, hp, armor, name, stem in zip(gate.BOSS_WAVES, gate.BOSS_HP, gate.BOSS_ARMOR, gate.BOSS_NAMES, gate.ICON_STEMS):
        obj = units[f'uB{wave:02d}']
        changes = {'uhpm': hp, 'udef': armor, 'unam': name, 'uico': 'war3mapImported\\BTNTDBoss' + stem + '.blp', 'uabi': '',
                   'umas': int(gate.value(obj, 'umvs') * (1.3 if wave == 8 else 1.15 if wave == 32 else 1.0) + .5)}
        for field, value in changes.items():
            key = (field, 0, 0)
            if key in obj.fields:
                obj.fields[key] = altered_field(obj.fields[key], value)
            else:
                payload = value.encode() + b'\0'
                marker = next(iter(obj.fields.values())).raw[-4:]
                obj.fields[key] = Field(key, 3, value, field.encode() + struct.pack('<I', 3) + payload + marker)
    obj = units['uG32']; obj.fields['umas', 0, 0] = altered_field(obj.fields['umas', 0, 0], gate.value(obj, 'umvs'))
    return after


class PureBossSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current, cls.formal = gate.source_files(ROOT / 'wurst'), formal_sources()

    def verify(self, source):
        return gate.verify_source_delta(source, self.formal, gate.CHANGED_OWNERS)

    def mutate(self, owner, old, new):
        self.assertIn(old, self.current[owner], owner + ': fixture needle absent')
        result = dict(self.current); result[owner] = result[owner].replace(old, new, 1)
        return result

    def test_actual_candidate_source_preserves_formal_ordinary_rules(self):
        proof = self.verify(self.current)
        self.assertEqual(set(proof['changed_owners']), gate.CHANGED_OWNERS)
        self.assertIn('tdClaimEnemyKill', proof['changed_functions'])

    def test_approval_is_explicit_and_closed(self):
        with self.assertRaisesRegex(ValueError, 'explicit owner approval'):
            gate.verify_source_delta(self.current, self.formal, [])
        with self.assertRaisesRegex(ValueError, 'Unknown approved'):
            gate.verify_source_delta(self.current, self.formal, gate.CHANGED_OWNERS | {'TDConfig.wurst'})

    def test_ordinary_wave_stats_counts_reward_and_spawn_rejected(self):
        for old, new in [('return 8\n', 'return 9\n'),
                         ('tdScaledEconomyValue(10)', 'tdScaledEconomyValue(11)'),
                         ('tdScaledEnemyStat(240, tdEnemySpeedMultiplier())', 'tdScaledEnemyStat(241, tdEnemySpeedMultiplier())'),
                         ('return 1.05', 'return 1.06')]:
            with self.subTest(old=old), self.assertRaises(ValueError):
                self.verify(self.mutate('TDWaves.wurst', old, new))

    def test_tower_skill_native_damage_equipment_and_pet_skill_rejected(self):
        cases = [('towers/TDTowerRuntime.wurst', 'tdEnemyMechanicScaleSpellDamage(victim, damagePerTick)', 'tdEnemyMechanicScaleSpellDamage(victim, damagePerTick * 2.0)'),
                 ('items/TDEquipmentCombat.wurst', 'source.damageTarget(target, additional)', 'source.damageTarget(target, additional * 2.0)'),
                 ('pets/TDPetRules.wurst', 'return 8.0 * quality', 'return 9.0 * quality'),
                 ('pets/TDPetCombat.wurst', 'host.damageTarget(target, amount)', 'host.damageTarget(target, amount * 2.0)'),
                 ('items/TDDropLogic.wurst', '20', '21')]
        for owner, old, new in cases:
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                self.verify(self.mutate(owner, old, new))

    def test_unexpected_new_function_source_rawcode_and_owner_rejected(self):
        for owner, tail in [('TDGame.wurst', '\npublic function tdSneakInDamage()\n\tUnitDamageTarget(null, null, 999.0, true, true, null, null, null)\n'),
                            ('enemies/TDEnemyMechanicData.wurst', "\npublic constant int TD_FOREIGN_ABILITY = 'Bad1'\n")]:
            altered = dict(self.current); altered[owner] += tail
            with self.subTest(owner=owner), self.assertRaises(ValueError): self.verify(altered)
        changed = dict(self.current); changed['foreign.wurst'] = 'package foreign\n'
        with self.assertRaises(ValueError): self.verify(changed)

    def test_prep_cannot_cancel_spawn_leak_old_enemy_or_extend_wild_window(self):
        owner = 'TDGame.wurst'
        for call in ('tdClearLaneEnemies(0)', 'tdHandleEnemyLeak(null)', 'tdFlowCancelLane(0)', 'tdPetWildTransition(null, 0)'):
            altered = self.mutate(owner, 'function tdPrepareBossRound(int wave)\n', 'function tdPrepareBossRound(int wave)\n\t' + call + '\n')
            with self.subTest(call=call), self.assertRaises(ValueError): self.verify(altered)
        with self.assertRaises(ValueError): self.verify(self.mutate('pets/TDPetWildState.wurst', '60.0', '120.0'))

    def test_match_registry_required_before_waypoint_order_and_living_checks(self):
        for owner, name in [('TDSpawn.wurst', 'tdAdvanceEnemyWaypoint'), ('TDSpawn.wurst', 'tdLaneEnemyCheckEnum')]:
            block = gate.source_function(self.current[owner], name)
            altered = dict(self.current); altered[owner] = altered[owner].replace(block, block.replace('not tdEnemyBelongsToCurrentMatch(enemy) or ', ''), 1)
            with self.subTest(name=name), self.assertRaises(ValueError): self.verify(altered)

    def test_leave_listener_is_single_startup_owned_and_preserves_close_semantics(self):
        cases = [
            ('TDInit.wurst', 'if tdLanePlayerLeaveWatcherReady', 'if false'),
            ('TDInit.wurst', 'tdLanePlayerLeaveWatcherReady = true', 'tdLanePlayerLeaveWatcherReady = false'),
            ('TDInit.wurst', 'function tdHandleLanePlayerLeaveEvent)', 'function tdSetupLanePlayerLeaveWatcher)'),
            ('TDInit.wurst', 'public function tdStartGame()\n', 'public function tdStartGame()\n\ttdLanePlayerLeaveWatcherReady = false\n'),
            ('pets/TDPetRuntime.wurst', 'import TDBossRewardRules\n', 'import initlater TDGame\nimport TDBossRewardRules\n'),
            ('TDGame.wurst', ' or tdIsLaneFinished(playerId) or tdIsLaneDefeated(playerId)', ' or tdIsLaneDefeated(playerId)'),
            ('TDGame.wurst', '\ttdTryScheduleNextWave(tdGetGlobalWave())\n', ''),
        ]
        for owner, old, new in cases:
            with self.subTest(owner=owner, old=old), self.assertRaises(ValueError):
                self.verify(self.mutate(owner, old, new))
        for registration in ('\tregisterPlayerEvent(EVENT_PLAYER_LEAVE, function tdHandleLanePlayerLeaveEvent)\n',
                             '\ttdSetupLanePlayerLeaveWatcher()\n'):
            with self.subTest(registration=registration), self.assertRaises(ValueError):
                self.verify(self.mutate('TDInit.wurst', registration, ''))

    def test_kill_and_reward_claim_order_cannot_move_after_effects(self):
        altered = self.mutate('TDGame.wurst', '\t\tif not tdFlowClaimBossReward(playerId, wave, tdFlowEpoch())\n\t\t\treturn false\n', '')
        with self.assertRaises(ValueError): self.verify(altered)
        altered = self.mutate('items/TDBossRewardRuntime.wurst', 'not tdFlowClaimBossLoot(lane, wave)', 'not tdFlowBossRewardWasClaimed(lane, wave)')
        with self.assertRaises(ValueError): self.verify(altered)
        altered = self.mutate('pets/TDPetRuntime.wurst', 'not tdFlowClaimBossBallCompensation(lane, wave)', 'not tdFlowBossRewardWasClaimed(lane, wave)')
        with self.assertRaises(ValueError): self.verify(altered)

    def test_hook_signature_closing_reasons_and_direct_resume_rejected(self):
        cases = [('TDBossTransitionHook.wurst', 'function onRelease(int transitionToken, int reason)', 'function onRelease(int transitionToken)'),
                 ('TDBossTransitionHook.wurst', 'TD_BOSS_TRANSITION_TIME_LIMIT = 120.0', 'TD_BOSS_TRANSITION_TIME_LIMIT = 90.0'),
                 ('TDWaveFlowState.wurst', 'tdFlowTransitionState = 2', 'tdFlowTransitionState = 0'),
                 ('TDGame.wurst', '\ttdStartGlobalWave(wave + 1)\n', '\ttdScheduleWaveAfterDelay(wave, 30.0)\n')]
        for owner, old, new in cases:
            with self.subTest(owner=owner), self.assertRaises(ValueError): self.verify(self.mutate(owner, old, new))

    def test_dark_tide_epoch_generation_and_independent_native_ability_guards(self):
        cases = [('enemies/TDBossDarkTideRuntime.wurst', 'record.matchEpoch != tdFlowEpoch() or ', ''),
                 ('enemies/TDBossDarkTideRuntime.wurst', '!= record.bossGeneration', '!= 0'),
                 ('enemies/TDBossDarkTideRuntime.wurst', 'tower.removeAbility(TD_BOSS_DARK_TIDE_ABILITY_ID)', 'tower.removeAbility(0)'),
                 ('enemies/TDEnemyMechanicObjectGen.wurst', 'setItemAbility(true)', 'setItemAbility(false)'),
                 ('enemies/TDEnemyMechanicData.wurst', 'TD_BOSS_DARK_TIDE_ATTACK_SPEED = -0.20', 'TD_BOSS_DARK_TIDE_ATTACK_SPEED = 0.20')]
        for owner, old, new in cases:
            with self.subTest(owner=owner), self.assertRaises(ValueError): self.verify(self.mutate(owner, old, new))

    def test_hud_rows_ranking_columns_and_icon_cell_preserved(self):
        for old, new in [('tdCountActiveLanes() + 5 + TD_DAMAGE_HUD_ROWS', 'tdCountActiveLanes() + 7 + TD_DAMAGE_HUD_ROWS'),
                         ('setColumnCount(TD_DAMAGE_HUD_COLUMNS)', 'setColumnCount(3)'),
                         ('setItemIcon(row, 1, icon)', 'setItemIcon(row, 2, icon)'),
                         ('setStyle(false, icon != "")', 'setStyle(true, true)')]:
            with self.subTest(old=old), self.assertRaises(ValueError): self.verify(self.mutate('TDHud.wurst', old, new))

    def test_extra_effects_inside_approved_owners_are_rejected_by_exact_source_templates(self):
        for effect in ('tdGainGold(playerId, 1)', 'GetRandomInt(1, 100)',
                       'tdHandlePureBossLoot(enemy, playerId, wave)', 'tdLoseLife(playerId, 1)'):
            old = '\ttdEvolutionRecordKill(GetKillingUnit(), playerId)'
            altered = self.mutate('TDGame.wurst', old, '\t' + effect + '\n' + old)
            with self.subTest(effect=effect), self.assertRaisesRegex(ValueError, 'exact approved template'):
                self.verify(altered)
        block = gate.source_function(self.current['TDGame.wurst'], 'tdTryScheduleNextWave')
        self.assertIn('\ttdTryUnlockPopulationAfterWave(wave)\n', block)
        altered = dict(self.current)
        altered['TDGame.wurst'] = altered['TDGame.wurst'].replace(block, block.replace('\ttdTryUnlockPopulationAfterWave(wave)\n', ''), 1)
        with self.assertRaisesRegex(ValueError, 'exact approved template'): self.verify(altered)

    def test_foreign_prefixed_source_global_and_dependency_are_rejected(self):
        altered = dict(self.current)
        altered['TDGame.wurst'] += '\nint tdUnauthorizedRewardMultiplier = 2\n'
        with self.assertRaisesRegex(ValueError, 'unexpected production global'): self.verify(altered)
        altered = self.mutate('TDGame.wurst', 'import TDState\n', 'import TDState\nimport TDEquipmentRules\n')
        with self.assertRaisesRegex(ValueError, 'import'): self.verify(altered)

    def test_evolution_requirement_is_only_shared_evolution_edit(self):
        with self.assertRaises(ValueError): self.verify(self.mutate('towers/TDTowerEvolutionState.wurst', 'REQUIREMENT = 220', 'REQUIREMENT = 219'))
        with self.assertRaises(ValueError): self.verify(self.mutate('towers/TDTowerEvolutionState.wurst', 'return kills + 1', 'return kills + 2'))


class PureBossFormalArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mpq = Mpq(subprocess.check_output(['git', 'show', FORMAL_B7 + ':ExampleMap.w3x'], cwd=ROOT))
        cls.script = cls.mpq.extract('war3map.j').decode()
        cls.formal = formal_sources()
        cls.objects = {name: parse_objects(cls.mpq.extract(name), ext) for name, ext in gate.OBJECTS.items() if cls.mpq.has(name)}
        cls.synthetic_objects = synthetic_expected_objects(cls.objects)
        cls.empty_proof = {'changed_owners': [], 'changed_functions': [], 'changed_classes': []}

    def test_entire_immutable_formal_jass_identity_passes(self):
        evidence = gate.prove_jass_delta(self.script, self.script, self.formal, self.formal, self.empty_proof)
        self.assertEqual(evidence['preserved_functions'], 1652)
        self.assertEqual(evidence['allocator_identity_count'], 82)

    def test_native_damage_allocator_and_comparison_mutations_rejected(self):
        cases = [('UnitDamageTarget(', 'ForeignDamageTarget('),
                 ('TDEnemyMechanicRecord_maxIndex + 1', 'TDEnemyMechanicRecord_maxIndex + 2'),
                 ('TDEnemyMechanicState_typeId[this_1] == 0', 'TDEnemyMechanicState_typeId[this_1] == 1')]
        for old, new in cases:
            self.assertTrue(old in self.script, 'Missing bounded fixture needle: ' + old)
            with self.subTest(old=old), self.assertRaises(ValueError):
                gate.prove_jass_delta(self.script.replace(old, new, 1), self.script, self.formal, self.formal, self.empty_proof)

    def test_diagnostic_not_blanket_erased_and_local_alpha_is_bijective(self):
        old = 'when calling fromRawCode in TDPetData, line 14'; self.assertTrue(old in self.script, 'Missing bounded fixture needle: ' + old)
        with self.assertRaises(ValueError):
            gate.prove_jass_delta(self.script.replace(old, 'when calling fromRawCode in TDPetData, line 12', 1), self.script, self.formal, self.formal, self.empty_proof)
        from VerifyDamageRankingJass import functions
        fn = functions(self.script)['tdHandleOrcBladestormCast'][0]
        self.assertIn('local integer temp111', fn)
        renamed = fn.replace('temp111', 'temp9007')
        gate.prove_jass_delta(self.script.replace(fn, renamed, 1), self.script, self.formal, self.formal, self.empty_proof)
        with self.assertRaises(ValueError):
            gate.prove_jass_delta(self.script.replace(fn, renamed.replace('local integer temp9007', 'local real temp9007'), 1), self.script, self.formal, self.formal, self.empty_proof)

    def test_actual_changed_delta_requires_independent_compiled_template_approval(self):
        proof = dict(self.empty_proof); proof['changed_owners'] = ['TDGame.wurst']
        with self.assertRaisesRegex(ValueError, 'real build.*reviewer-approved'):
            gate.prove_jass_delta(self.script, self.script, self.formal, self.formal, proof)
        draft = gate.draft_jass_templates(self.script, self.script, self.formal)
        with self.assertRaisesRegex(ValueError, 'not been independently approved'):
            gate.verify_reviewed_jass_templates(self.script, self.script, self.formal, draft)

    def test_exact_reviewed_compiled_templates_reject_extra_effects_and_prefixed_globals(self):
        # This explicitly synthetic review fixture exercises the template guard;
        # it is not a real pure-Boss candidate or an approval of such a candidate.
        template = gate.draft_jass_templates(self.script, self.script, self.formal)
        template.update(review_status='APPROVED', review_reference='synthetic unit-test fixture only')
        gate.verify_reviewed_jass_templates(self.script, self.script, self.formal, template)
        fn = gate.functions(self.script)['tdHandleEnemyDeath'][0]
        for effect in ('call tdGainGold(0, 1)', 'call GetRandomInt(1, 100)',
                       'call tdHandleEnemyDrop(null, 0, 8, 0)', 'call tdLoseLife(0, 1)'):
            altered = self.script.replace(fn, fn.replace('endfunction', '\t' + effect + '\nendfunction'), 1)
            with self.subTest(effect=effect), self.assertRaisesRegex(ValueError, 'exact reviewed template'):
                gate.verify_reviewed_jass_templates(altered, self.script, self.formal, template)
        altered = self.script.replace('endglobals', 'integer TDGame_unapprovedGold=999\nendglobals', 1)
        with self.assertRaisesRegex(ValueError, 'exact reviewed declarations'):
            gate.verify_reviewed_jass_templates(altered, self.script, self.formal, template)
        different_source = dict(self.formal); different_source['TDGame.wurst'] += '\n'
        with self.assertRaisesRegex(ValueError, 'different complete source bytes'):
            gate.verify_reviewed_jass_templates(self.script, self.script, different_source, template)
        with self.assertRaisesRegex(ValueError, 'different immutable formal map'):
            gate.verify_reviewed_jass_templates(self.script, self.script + '\n', self.formal, template)

    def test_closed_mpq_member_import_and_existing_resource_mutations(self):
        before = gate.members(self.mpq)
        after = dict(before)
        paths = gate.icon_paths()
        for path in paths:
            after[path.casefold()] = (path, (ROOT / 'imports' / path.replace('\\', '/')).read_bytes())
        old_imp = before['war3map.imp'][1]
        version, count = struct.unpack_from('<II', old_imp)
        new_imp = struct.pack('<II', version, count + 8) + old_imp[8:] + b''.join(b'\r' + p.encode() + b'\0' for p in paths)
        after['war3map.imp'] = ('war3map.imp', new_imp)
        old_list = before['(listfile)'][1]
        new_list = old_list + (b'' if old_list.endswith(b'\n') else b'\n') + ('\n'.join(paths) + '\n').encode()
        after['(listfile)'] = ('(listfile)', new_list)
        token = object()
        def verify(data):
            with patch.object(gate, 'members', side_effect=lambda item: data if item is token else before):
                return gate.verify_archive_delta(token, self.mpq)
        self.assertEqual(len(verify(after)['new_resources']), 8)
        foreign = dict(after); foreign['foreign.blp'] = ('foreign.blp', b'foreign')
        with self.assertRaisesRegex(ValueError, 'MPQ resource'): verify(foreign)
        mutated = dict(after); name, data = mutated['war3map.w3t']; mutated['war3map.w3t'] = (name, data + b'\0')
        with self.assertRaisesRegex(ValueError, 'Unrelated MPQ member'): verify(mutated)
        mutated = dict(after); mutated['war3map.imp'] = ('war3map.imp', new_imp.replace(b'\rwar3mapImported\\BTNTDBossRiftwind', b'\x05war3mapImported\\BTNTDBossRiftwind', 1))
        with self.assertRaisesRegex(ValueError, 'import flags'): verify(mutated)

    def test_synthetic_explicit_object_delta_passes(self):
        evidence = gate.verify_object_delta(self.synthetic_objects, self.objects)
        self.assertEqual(evidence['added'], ['Ebtd'])
        self.assertEqual(evidence['removed'], ['Emar'])

    def test_ordinary_tower_equipment_pet_loot_rawcode_object_mutations_rejected(self):
        for member, code in [('war3map.w3u', 'uE01'), ('war3map.w3u', 'uO6A'),
                              ('war3map.w3a', 'A131'), ('war3map.w3a', 'Pcap'),
                              ('war3map.w3t', 'iW01'), ('war3map.w3u', 'p011')]:
            self.assertIn(code, self.synthetic_objects[member])
            changed = deepcopy(self.synthetic_objects)
            obj = changed[member][code]; key = next(iter(obj.fields))
            obj.fields[key] = replace(obj.fields[key], raw=b'unexpected')
            with self.subTest(code=code), self.assertRaises(ValueError): gate.verify_object_delta(changed, self.objects)
        changed = deepcopy(self.synthetic_objects); changed['war3map.w3a']['BAD1'] = changed['war3map.w3a']['Ebtd']
        with self.assertRaises(ValueError): gate.verify_object_delta(changed, self.objects)

    def test_native_dark_tide_attack_speed_parent_fields_and_emar_rejected(self):
        for mutate in ('positive', 'aggregate', 'foreign_parent', 'Emar'):
            changed = deepcopy(self.synthetic_objects)
            dark = changed['war3map.w3a']['Ebtd']
            if mutate == 'positive': dark.fields['Isx1', 1, 1] = altered_field(dark.fields['Isx1', 1, 1], .20)
            elif mutate == 'aggregate': dark.fields['Cool', 1, 1] = dark.fields['Isx1', 1, 1]
            elif mutate == 'foreign_parent': dark.identity = b'ANclEbtd'
            else: changed['war3map.w3a']['Emar'] = self.objects['war3map.w3a']['Emar']
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): gate.verify_object_delta(changed, self.objects)

    def test_a130_475_and_exact_220_tooltips_no_carrier_mutation(self):
        for key, value in [(('alev', 0, 0), 476), (('aub1', 221, 0), '达到250击杀'), (('Ocr1', 1, 1), 1.0)]:
            changed = deepcopy(self.synthetic_objects); obj = changed['war3map.w3a']['A130']
            obj.fields[key] = altered_field(obj.fields[key], value)
            with self.subTest(key=key), self.assertRaises(ValueError): gate.verify_object_delta(changed, self.objects)

    def test_boss_hp_armor_icon_abilities_speed_mutations_rejected(self):
        for field, wanted in [('uhpm', 3201), ('udef', 3), ('uico', 'foreign.blp'), ('uabi', 'Emar'), ('umas', 400)]:
            changed = deepcopy(self.synthetic_objects); obj = changed['war3map.w3u']['uB08']
            obj.fields[field, 0, 0] = altered_field(obj.fields[field, 0, 0], wanted)
            with self.subTest(field=field), self.assertRaises(ValueError): gate.verify_object_delta(changed, self.objects)

    def test_evolution_status_allows_only_exact_one_threshold_field(self):
        for key, value in [(('aub1', 1, 0), '累计221击杀'), (('atp1', 1, 0), 'unapproved label')]:
            changed = deepcopy(self.synthetic_objects); obj = changed['war3map.w3a']['AeEV']
            obj.fields[key] = altered_field(obj.fields[key], value)
            with self.subTest(key=key), self.assertRaises(ValueError): gate.verify_object_delta(changed, self.objects)

    def test_eight_approved_blp_headers_bytes_and_alpha(self):
        class FileArtifact:
            def __init__(self, mutation=None): self.mutation = mutation
            def extract(self, path):
                data = (ROOT / 'imports' / path.replace('\\', '/')).read_bytes()
                return self.mutation(data) if self.mutation and 'Riftwind' in path else data
        evidence = gate.verify_icons(FileArtifact(), ROOT / 'wurst')
        self.assertEqual(len(evidence), 8)
        for mutation in (lambda b: b'BLP2' + b[4:], lambda b: b[:1180] + bytes([b[1180] ^ 1]) + b[1181:], lambda b: b + b'\0'):
            with self.subTest(), self.assertRaises(ValueError): gate.verify_icons(FileArtifact(mutation), ROOT / 'wurst')


@unittest.skipUnless(os.environ.get('PURE_BOSS_CANDIDATE_MAP'), 'Actual combined candidate awaits authorized final build; no synthetic compile claim')
class PureBossActualCompiledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = Mpq(Path(os.environ['PURE_BOSS_CANDIDATE_MAP']).read_bytes())
        cls.baseline = Mpq(subprocess.check_output(['git', 'show', FORMAL_B7 + ':ExampleMap.w3x'], cwd=ROOT))
        cls.script = cls.candidate.extract('war3map.j').decode()
        cls.before = cls.baseline.extract('war3map.j').decode()

    def test_actual_packaged_rule_flow_and_mechanics(self):
        self.assertEqual(gate.verify_packaged_rule_matrix(self.script, self.before), 498)
        self.assertEqual(gate.verify_packaged_hook_mode(self.script)['mode'], 'pureBossNoHook')
        self.assertEqual(gate.verify_packaged_flow(self.script), 18)
        self.assertEqual(gate.verify_packaged_leave_listener(self.script), 3)
        self.assertGreater(gate.verify_packaged_mechanics(self.script), 10)
        self.assertEqual(gate.verify_engine_and_accounting(self.script, gate.PureBossJassRuntime,
            {8: 100.0, 16: 100.0, 24: 68.0, 32: 58.0}), 48)

    def test_actual_closed_reviewed_combined_artifact(self):
        # An actual-map run must supply the independently approved real-build
        # manifest and matching formal source; missing evidence is an error.
        reviewed = json.loads(Path(os.environ['PURE_BOSS_REVIEWED_JASS_TEMPLATES']).read_text())
        result = gate.validate_pure_boss_artifact(self.candidate, self.baseline,
            ROOT / 'wurst', Path(os.environ['PURE_BOSS_BASELINE_SOURCE']),
            gate.CHANGED_OWNERS, reviewed)
        self.assertEqual(result['jass']['preserved_functions'], 1525)
        self.assertEqual(len(result['jass']['exact_reviewed_compiler_adaptations']), 47)
        self.assertEqual(result['jass']['exact_reviewed_global_declarations'], 1372)

    def test_actual_same_source_compiled_hook_harness(self):
        harness = Mpq(Path(os.environ['PURE_BOSS_HOOK_HARNESS_MAP']).read_bytes())
        script = harness.extract('war3map.j').decode()
        self.assertEqual(gate.verify_packaged_transition_harness(script)['cases'], 10)

    def test_actual_slow_speed_stage_retains_historical_and_exact_current_bounds(self):
        from VerifySlowAbilityArtifact import validate_enemy_speed, validate_slow_abilities
        from VerifyTowerPlacementArtifact import unit_objects
        from VerifyEquipmentAbilityArtifact import ability_objects
        units = unit_objects(self.candidate.extract('war3map.w3u'))
        validate_enemy_speed(units, pure_boss=True)
        validate_slow_abilities(ability_objects(self.candidate.extract('war3map.w3a')))
        historical = unit_objects(self.baseline.extract('war3map.w3u'))
        validate_enemy_speed(historical)
        with self.assertRaises(ValueError):
            validate_enemy_speed(units)
        for owner in ('uG32', 'uB08', 'uB32', 'uS20', 'uE01'):
            altered = deepcopy(units)
            altered[owner]['umas'] += 1
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                validate_enemy_speed(altered, pure_boss=True)

    def test_actual_runtime_rule_mutations_rejected(self):
        cases = [
            ('init_TDBossRewardRules', 'TD_BOSS_BONUS_DROP_CHANCE = 15', 'TD_BOSS_BONUS_DROP_CHANCE = 16'),
            ('tdResetWaveFlowState', 'TDWaveFlowState_tdFlowMatchEpoch + 1', '0'),
            ('TDEnemyMechanicState_updateBoss', '0.30', '0.31'),
            ('TDEnemyMechanicState_baseSpeed', '1.30', '1.31'),
            ('tdBeginBossIntermission', 'if tdFlowHasTransitionHook() then', 'if true then'),
        ]
        for owner, old, new in cases:
            body = gate.functions(self.script)[owner][0]
            self.assertEqual(body.count(old), 1, owner + ': mutation must match exactly one actual compiled statement')
            changed = self.script.replace(body, body.replace(old, new, 1), 1)
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                gate.verify_packaged_rule_matrix(changed, self.before)
                gate.verify_packaged_flow(changed)
                gate.verify_packaged_mechanics(changed)


if __name__ == '__main__':
    unittest.main()
