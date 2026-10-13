"""Actual map inheritance proof mutations; no production MPQ edits/writes."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import hashlib
import subprocess
import tempfile
import re
import sys
import types
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyEquipmentAbilityArtifact import ability_objects
from VerifySemanticIconArtifact import load_objects
from VerifyDamageRankingJass import functions
import VerifyPetManagerDelta as gate


class ManagerInheritanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This strict stage oracle remains b7 -> the published manager commit.
        # Later Boss deltas use their own actual-map source/MPQ/JASS proof.
        commit = '654771baa872241cf572b16a0ef884436fe4818c'
        data = subprocess.check_output(['git', 'show', commit + ':ExampleMap.w3x'], cwd=ROOT)
        if hashlib.sha256(data).hexdigest() != '30714b250dc528275e94c6d1d6779e66dceeafbc2d7eaf3cd9ce7c4e1c7b0f7c':
            raise AssertionError('Immutable formal manager map digest changed')
        cls.directory = tempfile.TemporaryDirectory(prefix='formal-manager-stage-')
        cls.addClassCleanup(cls.directory.cleanup)
        frozen = Path(cls.directory.name)
        gitdir = Path(subprocess.check_output(['git', 'rev-parse', '--absolute-git-dir'], cwd=ROOT).decode().strip())
        # Read-only shared git object lookup supports clone directories and
        # linked-worktree .git files; no index, refs or configuration is changed.
        (frozen / '.git').write_text('gitdir: ' + str(gitdir) + '\n')
        paths = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit, 'wurst'], cwd=ROOT).decode().splitlines()
        for relative in paths:
            target = frozen / relative; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=ROOT))
        scope = patch.object(gate, 'ROOT', frozen); scope.start(); cls.addClassCleanup(scope.stop)
        # This test proves the immutable published Manager stage. Its UI object
        # oracle must come from that same commit, never the current shortcut.
        ui_path = frozen / 'tools/VerifyPetUIArtifact.py'
        ui_path.parent.mkdir(parents=True, exist_ok=True)
        ui_path.write_bytes(subprocess.check_output(['git', 'show', commit + ':tools/VerifyPetUIArtifact.py'], cwd=ROOT))
        cls.frozen_ui = types.ModuleType('formal_manager_ui_oracle')
        cls.frozen_ui.__file__ = str(ui_path)
        exec(compile(ui_path.read_bytes(), str(ui_path), 'exec'), cls.frozen_ui.__dict__)
        ui_scope = patch.object(gate, 'verify_manager_objects', cls.frozen_ui.verify_manager_objects)
        ui_scope.start(); cls.addClassCleanup(ui_scope.stop)
        cls.current = Mpq(data)
        cls.before = gate.baseline_map()
        cls.script = cls.current.extract('war3map.j').decode()
        cls.baseline = cls.before.extract('war3map.j').decode()
        cls.maps = gate.source_maps()
        cls.objects, cls.prior = load_objects(cls.current), load_objects(cls.before)

    def test_actual_objects_members_sources_and_individual_inherited_bodies(self):
        proof = gate.validate(self.current)
        self.assertEqual(proof['objects']['added_abilities'], 175)
        self.assertEqual(proof['objects']['added_units'], 10)
        self.assertEqual(proof['archive']['new_assets'], 30)
        self.assertEqual(proof['global_channels'], 158)
        self.assertGreaterEqual(proof['jass']['protected_functions'], 1550)

    def test_historical_manager_oracle_rejects_current_release_cell_and_hotkey(self):
        original = ability_objects(self.current.extract('war3map.w3a'))
        for name, value in [('abpx', 3), ('ahky', 'W')]:
            abilities = deepcopy(original)
            key = next(k for k in abilities['Pm07'][1] if k[0] == name)
            kind, _ = abilities['Pm07'][1][key]
            abilities['Pm07'][1][key] = (kind, value)
            with self.subTest(field=name), self.assertRaises(ValueError):
                self.frozen_ui.verify_manager_commands(abilities)

    def assert_changed_function_rejected(self, name, transform):
        body = functions(self.script)[name][0]
        changed = transform(body)
        self.assertNotEqual(changed, body)
        script = self.script.replace(body, changed, 1)
        with self.assertRaises(ValueError):
            gate.prove_jass(script, self.baseline, self.maps)

    def test_rejects_inherited_boss_bloodlust_rank_and_wild_behavior(self):
        for name in ('tdWaveBossSpellDamageTakenFactor', 'tdRestoreBloodlustAutocast',
                     'tdDamagePlayerPrecedes', 'tdPetWildTravelSpeed'):
            with self.subTest(function=name):
                self.assert_changed_function_rejected(name, lambda t: t.replace('\n', '\n\tcall ClearTextMessages()\n', 1))

    def test_rejects_type_assignment_operator_reference_or_duplicate_owner(self):
        allocator = next(n for n in functions(self.script) if n.startswith('alloc_') and 'TDPetUISession' not in n)
        self.assert_changed_function_rejected(allocator, lambda t: gate.ASSIGN.sub(lambda m: m[1] + str(int(m[3])+1)+m[4], t, count=1))
        self.assert_changed_function_rejected('dispatch_TDPet_TDPet_setSkill', lambda t: t.replace(' == 0', ' != 0', 1))

    def test_rejects_diagnostic_line_even_when_behavior_text_is_equal(self):
        self.assert_changed_function_rejected('tdPetStore', lambda t: gate.DIAGNOSTIC.sub(lambda m: '"'+m[1]+str(int(m[3])+1)+'"', t, count=1))
        self.assert_changed_function_rejected('TDPet_skillPower', lambda t: gate.DIAGNOSTIC.sub(lambda m: '"'+m[1]+str(int(m[3])+1)+'"', t, count=1))

    def test_rejects_temp_type_or_inconsistent_use_site(self):
        self.assert_changed_function_rejected('call_doAfter_TDPetCombat', lambda t: t.replace('local real temp171_x', 'local integer temp171_x'))
        self.assert_changed_function_rejected('call_doAfter_TDPetCombat', lambda t: t.replace('set temp171_x = tuple_assignment', 'set temp171_x = tuple_assignment_1'))

    def test_rejects_callback_dispatch_target_and_argument_change(self):
        self.assert_changed_function_rejected('dispatch_CallbackSingle_CallbackSingle_call', lambda t: t.replace('call call_doAfter_TDPetUIView(this_1)', 'call call_doAfter_TDTowerRuntime(this_1)'))
        self.assert_changed_function_rejected('dispatch_CallbackSingle_CallbackSingle_call', lambda t: t.replace('call call_doAfter_TDPetUIView(this_1)', 'call call_doAfter_TDPetUIView(0)'))

    def test_rejects_main_init_glue_or_inherited_global_change(self):
        self.assert_changed_function_rejected('main', lambda t: t.replace('ref_function_init_TDPetUI)', 'ref_function_init_TDInit)'))
        changed = self.script.replace('integer TDPetData_TD_PET_BALL_LIMIT=0', 'integer TDPetData_TD_PET_BALL_LIMIT=1')
        self.assertNotEqual(changed, self.script)
        with self.assertRaises(ValueError): gate.prove_global_declarations(changed, self.baseline)

    def test_rejects_unrelated_object_field_and_locked_tooltip_change(self):
        for kind, rawcode, key in [('abilities', 'A131', ('acdn',1,0)),
                                   ('abilities', 's240', ('aub1',1,0)),
                                   ('units', 'p011', ('uabi',0,0))]:
            objects = deepcopy(self.objects)
            item = objects[kind][rawcode].fields[key]
            objects[kind][rawcode].fields[key] = replace(item, value='wrong', raw=item.raw+b'x')
            with self.subTest(object=rawcode), self.assertRaises(ValueError): gate.verify_objects(objects,self.prior)

    def test_rejects_display_metadata_without_shape_or_value_change(self):
        objects=deepcopy(self.objects);key=('uico',0,0)
        item=objects['units']['pd01'].fields[key]
        objects['units']['pd01'].fields[key]=replace(item,raw=item.raw[:-4]+b'evil')
        with self.assertRaisesRegex(ValueError,'metadata'): gate.verify_objects(objects,self.prior)

    def test_rejects_extra_object_without_allowlisting_new_set(self):
        objects=deepcopy(self.objects);objects['abilities']['Extra']=deepcopy(objects['abilities']['Pcol'])
        with self.assertRaises(ValueError):gate.verify_objects(objects,self.prior)


if __name__ == '__main__': unittest.main()
