"""Narrow source fence: cosmetic hooks cannot alter existing hero gameplay."""
import re
import subprocess
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
BASE = 'f0c5f45dc29790506886b24c973050e16291c280'


def baseline(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT, text=True)


def strip_comments(text):
    return '\n'.join(line for line in text.splitlines() if not line.lstrip().startswith('//'))


class HeroFeedbackTests(unittest.TestCase):
    def test_models_cover_ten_hero_skills_only(self):
        ev = SourceScalarEvaluator(read_sources(ROOT))
        for skill in range(39, 49):
            self.assertTrue(ev.call('tdPetHeroVisualModel', [skill]).startswith('Abilities\\'))
        for skill in (0, 11, 12, 18, 19, 38, 49):
            self.assertEqual(ev.call('tdPetHeroVisualModel', [skill]), '')

    def test_native_failure_stub_returns_jass_null(self):
        from VerifyPetHeroArtifact import HeroRuntime
        runtime = HeroRuntime.__new__(HeroRuntime)
        runtime.fail_hero_art = True
        for name in ('AddSpecialEffect', 'AddSpecialEffectTarget'):
            handled, result = runtime.native(name, ('model', 0, 0))
            self.assertTrue(handled)
            self.assertIsNone(result)

    def test_storm_uses_whirlwind_and_four_blades(self):
        text = (ROOT/'wurst/pets/TDPetHeroVisuals.wurst').read_text()
        self.assertIn('TornadoElementalSmall.mdx', text)
        self.assertIn('GlaiveMissile.mdx', text)
        self.assertNotIn('WarStomp', text)
        self.assertEqual(text.count('tdPetHeroVisualPoint(host, lane, blade,'), 4)

    def test_effects_gameplay_projection_unchanged(self):
        path = 'wurst/pets/TDPetHeroEffects.wurst'
        text = (ROOT / path).read_text()
        text = text.replace('import TDPetHeroVisuals\n', '').replace('\tlet skill = ticket.skill\n', '')
        text = re.sub(r'^\t*tdPetHeroVisual\([^\n]+\)\n', '', text, flags=re.M)
        text = re.sub(r'^\t\tif tdPetBindingValid\(pet, host, generation\) and pet.revision == revision and tdTrialContextValid\((?:cast\.)?context\)\n', '', text, flags=re.M)
        old = baseline(path)
        old = re.sub(r'^\tlet rootVisual = AddSpecialEffect\([^\n]+\)\n\tDestroyEffect\(rootVisual\)\n', '', old, flags=re.M)
        self.assertEqual(text, old)

    def test_state_gameplay_projection_unchanged(self):
        path = 'wurst/pets/TDPetHeroState.wurst'
        text = (ROOT / path).read_text().replace('import TDPetHeroVisuals\n', '')
        text = re.sub(r'\t// Registration can destroy[^\n]+\n\tlet host = ticket.host\n\tlet lane = ticket.pet.lane\n\tlet context = ticket.context\n\tlet accepted = tdPetRegisterEffectTask\(ticket\)\n\tif accepted\n\t\ttdPetHeroVisualReady\(host, lane, context\)\n\treturn accepted', '\treturn tdPetRegisterEffectTask(ticket)', text)
        text = re.sub(r'^\ttdPetHeroVisualReady\(ticket.host[^\n]+\n', '', text, flags=re.M)
        self.assertEqual(text, baseline(path))

    def test_no_attack_visual_restore_or_gameplay_resource_edits(self):
        for path in ('wurst/pets/TDPetAttackRuntime.wurst', 'wurst/pets/TDPetHeroRules.wurst', 'wurst/pets/TDPetHeroRuntime.wurst', 'wurst/TDWaves.wurst', 'wurst/visuals/TDCombatVisualRuntime.wurst'):
            if (ROOT/path).exists():
                self.assertEqual((ROOT/path).read_text(), baseline(path), path)

    def test_bounded_owner_cleanup_and_no_gameplay_side_effect(self):
        text = strip_comments((ROOT/'wurst/pets/TDPetHeroVisuals.wurst').read_text())
        self.assertEqual(text.count('tdCombatVisualAcquireCast()'), 2)
        self.assertEqual(text.count('tdCombatVisualAdoptPetPoint('), 2)
        self.assertEqual(text.count('tdCombatVisualReleaseCast()'), 2)
        self.assertEqual(text.count('DestroyEffect(art)'), 2)
        self.assertEqual(text.count('getElapsedGameTime() + 0.45'), 2)
        self.assertEqual(text.count('not host.isAlive()'), 2)
        for forbidden in ('CreateTimer', 'doPeriodically', 'enumUnits', 'Issue', 'Damage(', 'GetRandom', 'SetUnit'):
            self.assertNotIn(forbidden, text)
        self.assertIn('AddSpecialEffectTarget(', text)


if __name__ == '__main__':
    unittest.main()
