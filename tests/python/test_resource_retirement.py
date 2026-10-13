"""Source-only safety guards for the reviewed resource retirement."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from AuditMapResourceReachability import retired_names, normalize
from BuildPetUiAssets import verify_manifest, EXPECTED_NAMES, ARCHIVED_NAMES
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
from VerifyPetUIArtifact import ICON_STEMS, phase_one_catalog


class ResourceRetirementTests(unittest.TestCase):
    def test_exact_retired_allowlist_and_all_svg_sources_preserved(self):
        manifest = json.loads((ROOT / 'assets/source/pet-ui/manifest.json').read_text())
        with redirect_stdout(io.StringIO()):
            verify_manifest(manifest, True)
        self.assertEqual(set(ICON_STEMS), EXPECTED_NAMES)
        self.assertEqual(len(ARCHIVED_NAMES), 63)
        self.assertEqual(len(retired_names()), 126)
        self.assertEqual({a[k] for a in manifest['archived_assets'] for k in ('warcraft_normal_path', 'warcraft_disabled_path')}, retired_names())
        for name in retired_names():
            self.assertFalse((ROOT / 'imports' / name.replace('\\', '/')).exists())

    def test_all_fifteen_new_species_and_quality_pairs_are_untouched(self):
        for species in range(1, 16):
            for suffix in ('', 'Q1', 'Q2', 'Q3', 'Q4'):
                stem = f'TDPetSpecies{species:02d}{suffix}'
                for prefix in ('war3mapImported/BTN', 'ReplaceableTextures/CommandButtonsDisabled/DISBTN'):
                    self.assertTrue((ROOT / 'imports' / (prefix + stem + '.blp')).is_file())

    def test_stable_skill_capacity_and_disabled_object_guards_remain(self):
        n = phase_one_catalog()
        self.assertEqual(n['TD_PET_SKILL_COUNT'], 49)
        self.assertEqual([s for s in range(49) if not n['tdPetSkillDefined'](s)], [4, 9, 10, 13, 14, 15])
        for skill in (4, 9, 10, 13, 14, 15):
            for slot in range(4):
                self.assertFalse(n['tdPetSkillAllowed'](skill, slot, False, False))
        source = (ROOT / 'wurst/pets/TDPetObjectGen.wurst').read_text()
        self.assertIn('if not tdPetSkillDefined(skill)', source)
        self.assertIn('if not tdPetSkillAllowed(skill, slot, false, false)', source)

    def test_epidemic_tooltip_uses_same_runtime_damage_basis(self):
        source = (ROOT / 'wurst/pets/TDPetHeroData.wurst').read_text()
        runtime = (ROOT / 'wurst/pets/TDPetHeroRuntime.wurst').read_text()
        self.assertIn('tdTooltipNumber(tdGhoulCorpseExplosionDamage() * power)', source)
        self.assertNotIn('36.0 * power', source)
        self.assertIn('tdGhoulCorpseExplosionDamage() * tdPetHeroPower(TD_PET_HERO_EPIDEMIC, quality)', runtime)
        e = SourceScalarEvaluator(read_sources())
        for quality, expected in enumerate((45, 72, 99, 126), 1):
            self.assertAlmostEqual(e.call('tdGhoulCorpseExplosionDamage', []) * e.call('tdPetHeroPower', [48, quality]), expected)

    def test_reference_normalization_retains_mdx_and_jass_paths(self):
        self.assertEqual(normalize(b'war3mapImported\\\\Atlas.BLP\x00'), b'war3mapimported\\atlas.blp\x00')
        self.assertEqual(normalize(b'war3mapImported/Atlas.BLP'), b'war3mapimported\\atlas.blp')


if __name__ == '__main__':
    unittest.main()
