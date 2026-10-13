"""Compiled pet capability helper regressions, including evolved host abilities."""
from pathlib import Path
import sys
import unittest
from python_check_inputs import candidate_map

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from GenerateTowerTerrainMask import Mpq
import VerifyPetUIArtifact as verifier

CORRECTED_JASS = '''function tdPetSkillFitsAbilities takes integer skill, boolean hasSplitArrow, boolean hasCorpseExplosion returns boolean
    if skill == 9 then
        return hasSplitArrow
    endif
    if skill == 10 then
        return hasCorpseExplosion
    endif
    return true
endfunction
'''


class PetSkillFitsArtifactTests(unittest.TestCase):
    def test_actual_all_64_skill_and_host_capability_combinations(self):
        script = Mpq((candidate_map()).read_bytes()).extract('war3map.j').decode('utf-8')
        verifier.verify_skill_fit_abilities(script)


class PetSkillFitsMutationTests(unittest.TestCase):
    def test_corrected_compiled_fixture_accepts_all_64_combinations(self):
        verifier.verify_skill_fit_abilities(CORRECTED_JASS)

    def test_rejects_mixed_boolean_precedence_in_packaged_helper(self):
        bad = '''function tdPetSkillFitsAbilities takes integer skill, boolean hasSplitArrow, boolean hasCorpseExplosion returns boolean
    return skill != 9 or hasSplitArrow and skill != 10 or hasCorpseExplosion
endfunction
'''
        with self.assertRaisesRegex(ValueError, 'Ambiguous packaged scalar boolean precedence'):
            verifier.verify_skill_fit_abilities(bad)

    def test_rejects_wrong_split_or_corpse_skill_identity(self):
        for old, new, skill in [('skill == 9', 'skill == 8', 8),
                                ('skill == 10', 'skill == 11', 10)]:
            with self.subTest(skill=skill):
                with self.assertRaisesRegex(ValueError, f'Pet skill fit skill={skill}'):
                    verifier.verify_skill_fit_abilities(CORRECTED_JASS.replace(old, new))

    def test_rejects_swapped_or_always_enabled_required_capability(self):
        for old, new, skill in [('return hasSplitArrow', 'return hasCorpseExplosion', 9),
                                ('return hasCorpseExplosion', 'return hasSplitArrow', 10),
                                ('return hasSplitArrow', 'return true', 9),
                                ('return hasCorpseExplosion', 'return true', 10)]:
            with self.subTest(skill=skill, replacement=new):
                with self.assertRaisesRegex(ValueError, f'Pet skill fit skill={skill}'):
                    verifier.verify_skill_fit_abilities(CORRECTED_JASS.replace(old, new))

    def test_rejects_disabling_unrestricted_skills(self):
        with self.assertRaisesRegex(ValueError, 'Pet skill fit skill=0'):
            verifier.verify_skill_fit_abilities(CORRECTED_JASS.replace('return true', 'return false'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
