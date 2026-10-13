"""Historical formal72 manager oracle mutation checks; no map or compiler.
Current trial manager inheritance is separately verified by VerifyTrialDelta.
"""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import subprocess
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyPetManagerSource as checker
import VerifyPetUIArtifact as artifact
import VerifyPureBossArtifact as boss
current_checker = checker
from BuildPetUiAssets import verify_manifest
from trial_formal72_fixture import Formal72SourceFixture, sources as formal72_sources


def quiet(call, *args):
    with redirect_stdout(io.StringIO()):
        return call(*args)


def field(fields, name, value, level=0, column=0):
    fields[(name, level, column)] = (3 if isinstance(value, str) else 2 if isinstance(value, float) else 0, value)


def current_manager_fixture():
    """Controlled future object shape tests the verifier, never claims packaging."""
    abilities, units = {}, {}
    for rawcode, (x, y, key, target, stem) in artifact.MANAGER_COMMANDS.items():
        fields = {}
        for name, value in [('alev', 1), ('abpx', x), ('abpy', y), ('ahky', key), ('aart', artifact.icon_path(stem)), ('arar', artifact.icon_path(stem))]:
            field(fields, name, value)
        field(fields, 'Ncl2', target, 1, 2)
        field(fields, 'Ncl6', 'fixture' + rawcode.lower(), 1, 6)
        abilities[rawcode] = ('ANcl', fields)
    for name in ('anam',):
        field(abilities['Pc06'][1], name, '洗练 / 开栏(C)')
    field(abilities['Pc06'][1], 'atp1', '洗练 / 开栏(C)', 1)
    field(abilities['Pc06'][1], 'aub1', '洗练；开栏', 1)
    for name in ('arhk', 'auhk'):
        field(abilities['Pc06'][1], name, 'C')
    field(abilities['Pm09'][1], 'anam', '保留原技能')
    field(abilities['Pm0A'][1], 'anam', '换成新技能')
    for cell in range(10):
        for variant in range(49):
            rawcode, fields = f'L{cell * 49 + variant:03X}', {}
            stem = 'TDPetEmptySlot' if variant == 0 else artifact.SPECIES[(variant - 1) // 16][1] + f'Q{((variant - 1) % 16) // 4 + 1}N{(variant - 1) % 4 + 1}'
            for name, value in [('alev', 2), ('abpx', cell % 4), ('abpy', cell // 4), ('ahky', artifact.LIST_KEYS[cell]), ('aart', artifact.icon_path(stem)), ('arar', artifact.icon_path(stem))]:
                field(fields, name, value)
            for name in ('aher', 'aite'):
                field(fields, name, 0)
            for level in (1, 2):
                for key, value, column in [('Ncl1', 0.0, 1), ('Ncl3', 1, 3), ('Ncl4', 0.0, 4), ('Ncl5', 0, 5), ('amcs', 0, 0), ('acdn', 0.0, 0)]:
                    field(fields, key, value, level, column)
                number = f'{(level - 1) * 10 + cell + 1:02d}'
                label = '空位' if variant == 0 else artifact.QUALITY_NAMES[((variant - 1) % 16) // 4] + ' 精灵'
                field(fields, 'atp1', number + ' · ' + label + f' ({artifact.LIST_KEYS[cell]})', level)
                description = number + ('空位，捕获后查看' if variant == 0 else str((variant - 1) % 4 + 1) + '个技能。查看技能')
                field(fields, 'aub1', description, level)
                field(fields, 'Ncl2', 0, level, 2)
                field(fields, 'Ncl6', 'listcell' + str(cell), level, 6)
            abilities[rawcode] = ('ANcl', fields)
    for position in range(2):
        for skill in range(16):
            rawcode, fields = f'Ps{position * 16 + skill:02X}', {}
            for name, value in [('alev', 4), ('abpx', 0 if position == 0 else 3), ('abpy', 0), ('aart', artifact.NORMAL_PREFIX + artifact.SKILL_ICONS[skill] + '.blp'), ('aher', 0), ('aite', 0), ('achd', 0), ('areq', '')]:
                field(fields, name, value)
            for quality in range(1, 5):
                field(fields, 'atp1', ('旧：' if position == 0 else '新：') + artifact.QUALITY_NAMES[quality - 1] + ' ' + artifact.SKILL_NAMES[skill], quality)
                field(fields, 'aub1', '对应真实洗练栏；候选采用前不计入品质', quality)
                field(fields, 'Ocr1', 0.0, quality, 1)
                field(fields, 'Ocr2', 1.0, quality, 2)
            abilities[rawcode] = ('AOcr', fields)
    for position in range(2):
        fields = {}
        for key, value in [('alev', 1), ('abpx', position + 1), ('abpy', 0), ('aart', artifact.icon_path('TDPetNext')), ('aher', 0), ('aite', 0), ('achd', 0), ('areq', '')]:
            field(fields, key, value)
        field(fields, 'Ocr1', 0.0, 1, 1)
        field(fields, 'Ocr2', 1.0, 1, 2)
        abilities[f'Pa{position:02X}'] = ('AOcr', fields)
    for index in range(13):
        model, stem = (artifact.SPECIES[2][0], 'TDPetCollection') if index == 0 else (artifact.SPECIES[(index - 1) // 4][0], artifact.SPECIES[(index - 1) // 4][1] + f'Q{(index - 1) % 4 + 1}')
        units[f'pd{index:02X}'] = {'umdl': model, 'uico': artifact.icon_path(stem), 'ussi': artifact.icon_path(stem), 'uabi': 'Avul', 'ubdg': 1, 'uaen': 0, 'umvs': 0, 'ufoo': 0, 'ubui': '', 'utra': '', 'uupt': '', 'upat': ''}
    return abilities, units


class RealSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.formal72 = Formal72SourceFixture()
        cls.frozen = {}
        for name in ('VerifyPetManagerSource', 'VerifyPetUIArtifact'):
            path = cls.formal72.root / 'tools' / (name + '.py')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.check_output(['git', 'show', '72b2c9c3406868d33969c087dd5e6015abc3ac7b:tools/' + name + '.py'], cwd=ROOT))
            module = types.ModuleType(name)
            module.__file__ = str(path)
            exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
            cls.frozen[name] = module

    @classmethod
    def tearDownClass(cls):
        cls.formal72.cleanup()

    def setUp(self):
        self.addCleanup(patch.stopall)
        patch(__name__ + '.checker', self.frozen['VerifyPetManagerSource']).start()
        patch.dict(sys.modules, self.frozen).start()
        patch.object(boss, 'source_files', return_value=formal72_sources()).start()

    def test_execute_actual_page_quality_rawcode_and_navigation_bodies(self):
        quiet(checker.verify_scalar_contracts)

    def test_actual_sync_session_transactions_selection_and_poll_wiring(self):
        quiet(boss.verify_manager_inherited_wiring)

    def test_historical_manager_wild_scope_is_still_strict(self):
        with self.assertRaisesRegex(ValueError, 'Wild encounter changes outside scope'):
            quiet(checker.verify_wiring)

    def test_reject_wrong_real_source_whitelist_or_hotkey_or_capacity_partition(self):
        originals = {name: checker.source(name) for name in checker.FILES}
        for package, old, new in [('TDPetUIState', 'return action == TD_PET_ACTION_FARMER ? 11 : -1', 'return action == TD_PET_ACTION_FARMER ? 10 : -1'),
                                  ('TDPetUIState', 'return "Y"', 'return "X"'),
                                  ('TDPetData', 'cell * 13 + variant, 130', 'cell * 12 + variant, 130'),
                                  ('TDPetRules', 'if count >= 4', 'if count >= 5')]:
            modified = dict(originals)
            self.assertIn(old, modified[package])
            modified[package] = modified[package].replace(old, new)
            with self.subTest(package=package, mutation=new), patch.object(checker, 'source', side_effect=lambda name: modified[name]), self.assertRaises(ValueError):
                quiet(checker.verify_scalar_contracts)

    def test_reject_mutated_real_bridge_authority_transactions_or_local_state(self):
        originals = {name: checker.source(name) for name in checker.FILES}
        mutations = [('TDPetUI', 'caster != tdPetDisplays[lane]', 'caster == tdPetDisplays[lane]'),
                     ('TDPetUI', 'GetUnitAbilityLevel(caster, abilityId)', '1'),
                     ('TDPetUIState', 'dirty or not snapshotCurrent()', 'false'),
                     ('TDPetUI', 'tdPetRefreshDisplay(lane)\n', 'tdPetRenderPage(lane, 0, 0, 0, 0)\n'),
                     ('TDPetUIView', 'tdPetCancelRelease(lane)\n', 'skip\n'),
                     ('TDPetState', 'pet.proposalVersion != candidateVersion', 'false'),
                     ('TDPetState', 'pet.revision != pet.proposalRevision', 'false'),
                     ('TDPetState', 'qualities[3])', '0)'),
                     ('TDPetUIState', 'return eventKey == currentKey', 'return true'),
                     ('TDPetUIView', 'if pet.paused', 'if false'),
                     ('TDPetUIView', 'SelectUnit(fresh, true)', 'tdPetDisplays[lane] = fresh\n\t\tSelectUnit(fresh, true)')]
        for package, old, new in mutations:
            modified = dict(originals)
            self.assertIn(old, modified[package])
            modified[package] = modified[package].replace(old, new)
            with self.subTest(package=package, mutation=new), patch.object(checker, 'source', side_effect=lambda name: modified[name]), self.assertRaises(ValueError):
                quiet(boss.verify_manager_inherited_wiring)

    def test_current_manifest_78_assets_and_original_28_remain_exact(self):
        with patch.object(current_checker, 'ROOT', ROOT):
            quiet(current_checker.verify_assets)

    def test_manifest_rejects_missing_quality_or_semantic_name(self):
        original = json.loads((ROOT / 'assets/source/pet-ui/manifest.json').read_text())
        for name in ('TDPetFlamePhoenixQ4', 'TDPetKeep', 'TDPetRelease', 'TDPetAdopt'):
            data = deepcopy(original)
            data['assets'] = [a for a in data['assets'] if a['name'] != name]
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'exact 78'):
                quiet(verify_manifest, data, True)


class CurrentArtifactVerifierMutationTests(unittest.TestCase):
    def setUp(self):
        self.abilities, self.units = current_manager_fixture()

    def test_controlled_current_list_command_preview_and_units_shape(self):
        artifact.verify_manager_commands(self.abilities)
        artifact.verify_manager_list(self.abilities)
        artifact.verify_manager_preview(self.abilities)
        artifact.verify_manager_units(self.units)

    def test_list_rejects_last_cell_level_number_icon_target_and_missing_state(self):
        for key, level, value in [('atp1', 2, '19 · 紫 精灵 (X)'), ('aart', 0, artifact.icon_path('TDPetFlamePhoenixQ1')), ('Ncl2', 2, 1), ('alev', 0, 1)]:
            abilities = deepcopy(self.abilities)
            field(abilities['L1E9'][1], key, value, level, 2 if key == 'Ncl2' else 0)
            with self.subTest(key=key), self.assertRaises(ValueError):
                artifact.verify_manager_list(abilities)
        del self.abilities['L1E9']
        with self.assertRaisesRegex(ValueError, 'Missing fixed collection state L1E9'):
            artifact.verify_manager_list(self.abilities)

    def test_commands_reject_confirm_target_hotkey_or_slot(self):
        for key, level, value in [('Ncl2', 1, 1), ('ahky', 0, 'Q'), ('abpx', 0, 1)]:
            abilities = deepcopy(self.abilities)
            field(abilities['Pm0B'][1], key, value, level, 2 if key == 'Ncl2' else 0)
            with self.subTest(key=key), self.assertRaises(ValueError):
                artifact.verify_manager_commands(abilities)

    def test_global_channel_collision_detected_at_second_list_level(self):
        field(self.abilities['L1E9'][1], 'Ncl6', 'fixture-Pm0B', 2, 6)
        with self.assertRaises(ValueError):
            artifact.verify_manager_commands(self.abilities)

    def test_preview_rejects_wrong_quality_combat_effect_or_channel(self):
        for key, level, value in [('atp1', 4, '新：白 风缚'), ('Ocr1', 4, 25.0), ('Ncl6', 1, 'fixture-Pm00')]:
            abilities = deepcopy(self.abilities)
            field(abilities['Ps1F'][1], key, value, level, 1 if key == 'Ocr1' else 6 if key == 'Ncl6' else 0)
            with self.subTest(key=key), self.assertRaises(ValueError):
                artifact.verify_manager_preview(abilities)

    def test_units_reject_pre_attached_commands_locust_food_movement_and_quality(self):
        for key, value in [('uabi', 'Avul,Pc00'), ('uabi', 'Aloc,Avul'), ('ufoo', 1), ('umvs', 100), ('ussi', artifact.icon_path('TDPetGhostWisp'))]:
            units = deepcopy(self.units)
            units['pd0C'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                artifact.verify_manager_units(units)


if __name__ == '__main__':
    unittest.main(verbosity=2)
