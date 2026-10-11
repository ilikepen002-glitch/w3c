"""Actual compiled skill admission and lane-enemy guard regressions."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
import VerifyPetUIArtifact as verifier


def replace_body(script, name, body):
    match = verifier.jass_function(script, name)
    return script[:match.start(1)] + body + script[match.end(1):]


class PetCompiledRuleGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = Mpq((ROOT / 'ExampleMap.w3x').read_bytes()).extract('war3map.j').decode('utf-8')

    def test_actual_all_2176_skill_admission_combinations(self):
        verifier.verify_skill_allowed(self.script)

    def test_actual_all_256_lane_enemy_guard_combinations(self):
        verifier.verify_lane_enemy_guards(self.script)

    def test_rejects_old_compiled_skill_admission_mixed_precedence(self):
        body = '''    if skill_1 < 0 or skill_1 >= 16 or bitset_get(usedMask, skill_1) then
        return false
    endif
    if slot == 0 then
        return tdPetSkillIsNumeric(skill_1)
    endif
    return ( not tdPetSkillIsNumeric(skill_1)) and slot != 1 or tdPetSkillIsUniversal(skill_1) and ( not hasActive) or ( not tdPetSkillIsActive(skill_1))
'''
        with self.assertRaisesRegex(ValueError, 'Ambiguous packaged scalar boolean precedence'):
            verifier.verify_skill_allowed(replace_body(self.script, 'tdPetSkillAllowed', body))

    def test_rejects_each_missing_skill_admission_guard(self):
        original = verifier.jass_function(self.script, 'tdPetSkillAllowed').group(1)
        cases = [
            ('duplicate', original.replace(' or bitset_get(usedMask, skill_1)', '')),
            ('first numeric', original.replace('if slot == 0 then', 'if slot != 0 then')),
            ('later numeric', original.replace('\tif tdPetSkillIsNumeric(skill_1) then\n\t\treturn false\n\tendif\n', '')),
            ('second universal', original.replace('if slot == 1 and', 'if slot == 2 and')),
            ('one active', original.replace('\tif hasActive and tdPetSkillIsActive(skill_1) then\n\t\treturn false\n\tendif\n', '')),
        ]
        for name, body in cases:
            with self.subTest(guard=name):
                self.assertNotEqual(body, original, 'Mutation must change the real compiled body')
                with self.assertRaisesRegex(ValueError, 'Pet skill allowed'):
                    verifier.verify_skill_allowed(replace_body(self.script, 'tdPetSkillAllowed', body))

    def test_rejects_wrong_real_numeric_universal_and_active_helpers(self):
        for name, old, new, reason in [
            ('tdPetSkillIsNumeric', '<= 3', '<= 4', 'numeric skill classification'),
            ('tdPetSkillIsUniversal', '!= 9', '!= 8', 'universal skill classification'),
            ('tdPetSkillIsActive', '>= 11', '>= 12', 'active skill classification'),
        ]:
            with self.subTest(helper=name):
                body = verifier.jass_function(self.script, name).group(1)
                self.assertIn(old, body)
                with self.assertRaisesRegex(ValueError, reason):
                    verifier.verify_skill_allowed(replace_body(self.script, name, body.replace(old, new)))

    def test_rejects_wrong_real_bitset_get_and_contains_pow(self):
        for name, old, new in [('bitset_get', 'int_pow(2, index)', 'int_pow(2, index + 1)'),
                               ('bitset_containsPow', '>= pow', '> pow')]:
            with self.subTest(helper=name):
                body = verifier.jass_function(self.script, name).group(1)
                self.assertIn(old, body)
                with self.assertRaisesRegex(ValueError, 'bitset duplicate check'):
                    verifier.verify_skill_allowed(replace_body(self.script, name, body.replace(old, new)))

    def test_rejects_unverified_int_pow_implementation(self):
        body = verifier.jass_function(self.script, 'int_pow').group(1)
        self.assertIn('exitwhen i > temp', body)
        with self.assertRaisesRegex(ValueError, 'int_pow no longer implements'):
            verifier.verify_skill_allowed(replace_body(self.script, 'int_pow', body.replace('exitwhen i > temp', 'exitwhen i >= temp')))

    def test_rejects_old_compiled_wave_match_bypassing_enum_guards(self):
        body = '''    local unit enemy_1 = GetEnumUnit()
    if ( not tdPetIsWild(enemy_1)) and ( not TDSpawn_tdLaneEnemyCheckFound) and enemy_1 != null and unit_isAlive(enemy_1) and GetOwningPlayer(enemy_1) == Player(TDConfig_TD_ENEMY_PLAYER_ID) and tdEnemyLaneId(enemy_1) == TDSpawn_tdLaneEnemyCheckPlayer and TDSpawn_tdLaneEnemyCheckWave == 0 or tdEnemyWave(enemy_1) == TDSpawn_tdLaneEnemyCheckWave then
        set TDSpawn_tdLaneEnemyCheckFound = true
    endif
'''
        with self.assertRaisesRegex(ValueError, 'Ambiguous packaged scalar boolean precedence'):
            verifier.verify_lane_enemy_guards(replace_body(self.script, 'tdLaneEnemyCheckEnum', body))

    def test_rejects_removing_each_enum_guard_even_with_matching_wave(self):
        original = verifier.jass_function(self.script, 'tdLaneEnemyCheckEnum').group(1)
        conditions = ['enemy_1 == null', 'TDSpawn_tdLaneEnemyCheckFound or',
                      'tdPetIsWild(enemy_1)', '( not unit_isAlive(enemy_1))',
                      'GetOwningPlayer(enemy_1) != Player(TDConfig_TD_ENEMY_PLAYER_ID)',
                      'tdEnemyLaneId(enemy_1) != TDSpawn_tdLaneEnemyCheckPlayer']
        for condition in conditions:
            with self.subTest(guard=condition):
                self.assertIn(condition, original)
                replacement = 'false or' if condition.endswith(' or') else 'false'
                body = original.replace(condition, replacement)
                with self.assertRaisesRegex(ValueError, 'Lane enemy guards'):
                    verifier.verify_lane_enemy_guards(replace_body(self.script, 'tdLaneEnemyCheckEnum', body))

    def test_rejects_missing_wave_filter_or_wrong_found_assignment(self):
        original = verifier.jass_function(self.script, 'tdLaneEnemyCheckEnum').group(1)
        no_wave = re.sub(r'\tif TDSpawn_tdLaneEnemyCheckWave != 0 and[^\n]*\n\t\treturn\n\tendif\n', '', original)
        self.assertNotEqual(no_wave, original)
        for body in (no_wave, original.replace('set TDSpawn_tdLaneEnemyCheckFound = true',
                                               'set TDSpawn_tdLaneEnemyCheckFound = false')):
            with self.assertRaisesRegex(ValueError, 'Lane enemy guards'):
                verifier.verify_lane_enemy_guards(replace_body(self.script, 'tdLaneEnemyCheckEnum', body))


if __name__ == '__main__':
    unittest.main(verbosity=2)
