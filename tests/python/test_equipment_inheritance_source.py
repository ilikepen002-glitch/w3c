"""Current40 exact damage/HP sites and formal009 manager inheritance mutations."""
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import VerifyEquipmentInheritanceSource as gate


class CurrentEquipmentInheritanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = gate.verify(ROOT)

    def mutate(self, owner, old, new, verifier, reason):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            shutil.copytree(ROOT / 'wurst', root / 'wurst', ignore=shutil.ignore_patterns('_tests'))
            path = root / 'wurst' / owner
            text = path.read_text()
            self.assertEqual(text.count(old), 1, owner + ': nonunique/missing real-source mutation needle')
            path.write_text(text.replace(old, new, 1))
            with self.assertRaisesRegex(ValueError, reason):
                verifier(root)

    def test_current_reviewed_source_has_seven_damage_two_trial_hp_and_eight_preserved_pet_owners(self):
        self.assertEqual(self.proof['damage_hp'], {'damage_sites': 7, 'trial_hp_sites': 2})
        self.assertEqual(self.proof['manager']['preserved_owners'], 8)
        self.assertEqual(len(self.proof['manager']['exact_reviewed_changed_owners']), 5)

    def test_each_damage_site_deleted_duplicated_or_scaled_twice_is_rejected(self):
        for owner, function, call in gate.DAMAGE_SITES:
            for new in ('skip', call + '\n\t' + call, call.replace(', amount)', ', amount * 2.0)').replace(', additional)', ', additional * 2.0)').replace(', damagePerTick)', ', damagePerTick * 2.0)')):
                # Every declared operation must actually mutate its reviewed call.
                if new == call:
                    new = call.replace('damageTarget(', 'damageTarget(null, ', 1)
                with self.subTest(owner=owner, function=function, mutation=new):
                    self.mutate(owner, call, new, gate.verify_damage_and_hp, 'exact production damage inventory changed')

    def test_hidden_hp_compensation_in_any_old_or_new_damage_caller_is_rejected(self):
        for owner in ('towers/TDTowerRuntime.wurst', 'items/TDEquipmentCombat.wurst',
                      'items/TDEquipmentSpecialRuntime.wurst', 'pets/TDPetCombat.wurst'):
            with self.subTest(owner=owner):
                self.mutate(owner, 'package ' + Path(owner).stem,
                            'package ' + Path(owner).stem + '\nfunction hiddenCompensation(unit target)\n\ttarget.setLife(1000.0)',
                            gate.verify_damage_and_hp, 'forbidden HP/abort/type/element compensation')

    def test_trial_hp_refill_delete_duplicate_wrong_amount_or_foreign_owner_is_rejected(self):
        owner = 'trial/TDTrialRuntime.wurst'
        text = (ROOT / 'wurst' / owner).read_text()
        needle = 'function tdTrialRefillBeforeDamage'
        body = text.split(needle, 1)[1].split('\npublic function', 1)[0]
        call = 'target.setLife(TD_TRIAL_TARGET_HP * 1.0)'
        self.assertEqual(body.count(call), 1)
        for replacement in ('skip', call + '\n\t\t' + call, 'target.setLife(TD_TRIAL_TARGET_HP * 2.0)'):
            with self.subTest(mutation=replacement):
                self.mutate(owner, needle + body, needle + body.replace(call, replacement, 1),
                            gate.verify_damage_and_hp, 'forbidden HP/abort/type/element compensation')


    def test_hidden_damage_and_native_hp_calls_with_token_whitespace_are_rejected(self):
        for name, args, reason in (
            ('source.damageTarget', 'target, 999.0', 'exact production damage inventory changed'),
            ('SetWidgetLife', 'target, 1000.0', 'forbidden HP/abort/type/element compensation'),
        ):
            for gap in (' ', '\t', '\n\t', ' // comment between call tokens\n\t',
                        ' /* comment between call tokens */ ', ' /* multiple\nlines */\n\t'):
                owner = 'items/TDEquipmentSpecialRuntime.wurst'
                package = 'package TDEquipmentSpecialRuntime'
                extra = '\nfunction hiddenWhitespaceCall(unit source, unit target)\n\t' + name + gap + '(' + args + ')'
                with self.subTest(name=name, whitespace=gap):
                    self.mutate(owner, package, package + extra, gate.verify_damage_and_hp, reason)

    def test_existing_calls_accept_semantically_identical_token_whitespace(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            shutil.copytree(ROOT / 'wurst', root / 'wurst', ignore=shutil.ignore_patterns('_tests'))
            sites = gate.DAMAGE_SITES + gate.HP_SITES
            for owner, call in sorted({(owner, call) for owner, _, call in sites}):
                path = root / 'wurst' / owner
                text = path.read_text()
                expected_count = sum(relative == owner and statement == call for relative, _, statement in sites)
                self.assertEqual(text.count(call), expected_count)
                formatted = call.replace('(', ' // preserved call-token comment\n\t(\n\t\t', 1)
                path.write_text(text.replace(call, formatted))
            self.assertEqual(gate.verify_damage_and_hp(root), {'damage_sites': 7, 'trial_hp_sites': 2})

    def test_comment_and_string_pseudo_calls_do_not_create_damage_sites(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            shutil.copytree(ROOT / 'wurst', root / 'wurst', ignore=shutil.ignore_patterns('_tests'))
            path = root / 'wurst/items/TDEquipmentSpecialRuntime.wurst'
            path.write_text(path.read_text() + '\nfunction lexicalDiagnostic()\n'
                            '\tlet diagnostic = "SetWidgetLife (target, 1000.0), source.damageTarget (target, 999.0)"\n'
                            '\t// source.damageTarget (target, 999.0)\n'
                            '\t/* SetWidgetLife (target, 1000.0) */\n')
            self.assertEqual(gate.verify_damage_and_hp(root), {'damage_sites': 7, 'trial_hp_sites': 2})

    def test_relocating_reviewed_call_into_new_class_method_init_or_overload_is_rejected(self):
        owner = 'towers/TDTowerRuntime.wurst'
        function = 'tdDealArcherSplitArrowAttackDamage'
        call = next(call for relative, name, call in gate.DAMAGE_SITES if relative == owner and name == function)
        header = gate.SOURCE_DECLARATIONS[owner, function]
        text = (ROOT / 'wurst' / owner).read_text()
        match = re.search(r'^' + re.escape(header) + r'\n(?:[ \t][^\n]*\n|\n)*', text, re.M)
        self.assertIsNotNone(match)
        original = match[0]
        self.assertEqual(original.count(call), 1)
        for container in (
            'class ReviewMovedDamage\n\tfunction relocated(unit source, unit target, real amount)\n\t\t',
            'class ReviewMovedDamage\n\tfunction ' + function + '(unit source, unit target, real amount)\n\t\t',
            'init\n\t',
            'class ReviewMovedDamage\n\tondestroy\n\t\t',
            'class ReviewMovedDamage\n\tconstruct(unit source, unit target, real amount)\n\t\t',
            header.replace('int revision)', 'int revision, int extra)') + '\n\t',
        ):
            changed = original.replace(call, 'skip', 1) + '\n' + container + call + '\n\n'
            with self.subTest(container=container):
                self.mutate(owner, original, changed, gate.verify_damage_and_hp,
                            'exact production damage inventory changed')

    def test_each_changed_and_preserved_manager_owner_rejects_unreviewed_body(self):
        for owner in sorted(gate.REVIEWED_PET_OWNERS) + ['pets/TDPetUI.wurst', 'pets/TDPetUIState.wurst', 'pets/TDPetUIView.wurst']:
            package = 'package ' + Path(owner).stem
            reason = 'reviewed source hash differs' if owner in gate.REVIEWED_PET_OWNERS else 'changed owner set differs'
            with self.subTest(owner=owner):
                self.mutate(owner, package, package + '\nfunction foreignManagerMutation()\n\tskip', gate.verify_manager, reason)

    def test_foreign_prefixed_manager_source_does_not_expand_owner_set(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            shutil.copytree(ROOT / 'wurst/pets', root / 'wurst/pets')
            (root / 'wurst/pets/TDEquipmentManagerSneak.wurst').write_text('package TDEquipmentManagerSneak\n')
            with self.assertRaisesRegex(ValueError, 'exact source owner inventory changed'):
                gate.verify_manager(root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
