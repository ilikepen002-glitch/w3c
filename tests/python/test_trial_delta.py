"""Strict exact trial-delta negative tests; no source-owned whitelist erasure."""
import copy
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyTrialDelta import source_delta, jass_delta, verify_contract

class TrialDeltaTests(unittest.TestCase):
    def test_new_runtime_must_exist_and_unrelated_owner_cannot_change(self):
        baseline = {'TDGame.wurst': b'game', 'TDInit.wurst': b'init'}
        now = {**baseline, **{f'trial/TDTrial{x}.wurst': x.encode() for x in ('Hook', 'Runtime', 'Identity')}}
        self.assertEqual(len(source_delta(now, baseline)['added']), 3)
        now['TDGame.wurst'] = b'mutant game'
        with self.assertRaises(ValueError): source_delta(now, baseline)
        now['TDGame.wurst'] = b'game'; now['trial/Unauthorized.wurst'] = b'foreign'
        with self.assertRaises(ValueError): source_delta(now, baseline)
    def test_diagnostics_and_callback_global_changes_are_not_normalized(self):
        before = 'globals\ninteger capture = 0\nendglobals\nfunction owner takes nothing returns nothing\ncall helper("line 1")\nendfunction\n'
        after = before.replace('line 1', 'line 2').replace('capture = 0', 'capture = 9')
        contract = jass_delta(after, before)
        self.assertIn('owner', contract['changed'])
        self.assertNotEqual(contract['before_complete_sha256'], contract['after_complete_sha256'])
        self.assertIn('line 2', contract['changed']['owner']['after'])
    def test_exact_contract_rejects_every_extra_or_modified_byte_contract(self):
        exact = {'candidate_map_sha256': 'approved', 'source': {'added': {}, 'changed': {}},
                 'jass': {'added': {}, 'changed': {}, 'deleted': {}, 'preserved': {}},
                 'objects': {}, 'archive': {'changed': {}}}
        self.assertEqual(verify_contract(exact, copy.deepcopy(exact))['status'], 'PASS')
        for key in exact:
            mutant = copy.deepcopy(exact); mutant[key] = 'mutant'
            with self.subTest(key=key), self.assertRaises(ValueError): verify_contract(mutant, exact)
        mutant = copy.deepcopy(exact); mutant['unreviewed'] = True
        with self.assertRaises(ValueError): verify_contract(mutant, exact)
if __name__ == '__main__': unittest.main()

class TrialCurrentManagerTests(unittest.TestCase):
    def test_actual_current_manager_stays_guarded_under_trial(self):
        from VerifyTrialDelta import verify_current_manager
        self.assertEqual(verify_current_manager(ROOT / 'wurst')['status'], 'PASS')

    def test_actual_current_manager_mutations_are_rejected(self):
        from unittest.mock import patch
        import VerifyPetManagerSource as manager
        from VerifyTrialDelta import verify_current_manager
        original = {name: manager.source(name) for name in manager.FILES}
        mutations = [('TDPetState', 'pet.proposalVersion != candidateVersion', 'false'),
                     ('TDPetUI', 'caster != tdPetDisplays[lane]', 'caster == tdPetDisplays[lane]'),
                     ('TDPetUIState', 'return eventKey == currentKey', 'return true')]
        for owner, old, new in mutations:
            changed = dict(original); self.assertIn(old, changed[owner]); changed[owner] = changed[owner].replace(old, new, 1)
            with self.subTest(owner=owner), patch.object(manager, 'source', side_effect=lambda name: changed[name]), self.assertRaises(ValueError):
                verify_current_manager(ROOT / 'wurst')
