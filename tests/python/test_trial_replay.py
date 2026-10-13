"""Production hook acceptance is mandatory; historical empty DCE is rejected."""
import hashlib
import os
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from VerifyTrialReplay import production_contract, verify_replay, TrialJassRuntime, verify_damage_chain, verify_current_capture
from GenerateTowerTerrainMask import Mpq
from trial_formal72_fixture import map_bytes

class TrialProductionGateTests(unittest.TestCase):
    def test_formal72_empty_hook_is_never_trial_production_evidence(self):
        script = Mpq(map_bytes()).extract('war3map.j').decode()
        with self.assertRaisesRegex(ValueError, 'Production Trial APIs missing/DCE'):
            production_contract(script)

    def test_actual_trial_map_when_authorized_build_available(self):
        # This test remains explicit even before serial compilation. The final
        # aggregate command must supply the actual frozen trial map environment.
        path = os.environ.get('TRIAL_CANDIDATE_MAP')
        if not path:
            self.assertNotEqual(__import__('VerifyTrialDelta').REVIEWED_CONTRACT_SHA, '', 'Pending artifact boundary must remain visible')
            self.skipTest('Actual map NOT COVERED: TRIAL_CANDIDATE_MAP is required')
        data = Path(path).read_bytes()
        expected = os.environ.get('TRIAL_CANDIDATE_MAP_SHA256')
        self.assertTrue(expected, 'Final production replay requires frozen actual map SHA')
        self.assertEqual(hashlib.sha256(data).hexdigest(), expected)
        self.assertEqual(verify_replay(Mpq(data).extract('war3map.j').decode())['status'], 'PASS')
    def test_actual_production_native_timer_identity_mutation_rejected(self):
        path = os.environ.get('TRIAL_CANDIDATE_MAP')
        if not path: self.skipTest('Actual map NOT COVERED: TRIAL_CANDIDATE_MAP is required')
        script = Mpq(Path(path).read_bytes()).extract('war3map.j').decode()
        needle = 'GetExpiredTimer() != TDTrialHook_tdTrialResumeTimer'
        self.assertIn(needle, script)
        changed = script.replace(needle, 'false', 1)
        r = TrialJassRuntime(changed); r.initialize_match(); r.enter(8)
        old_timer = r.globals['TDTrialHook_tdTrialResumeTimer']
        r.initialize_match(); r.enter(8); r.now = r.state_call('getDeadline')
        r.fire_native_timer(old_timer)
        self.assertEqual(r.state_call('getPhase'), 3, 'Mutation fixture did not expose stale timer resuming the new match')

    def test_actual_production_refill_amount_mutation_rejected(self):
        path = os.environ.get('TRIAL_CANDIDATE_MAP')
        if not path: self.skipTest('Actual map NOT COVERED: TRIAL_CANDIDATE_MAP is required')
        from VerifyDamageRankingJass import functions
        script = Mpq(Path(path).read_bytes()).extract('war3map.j').decode()
        body = functions(script)['tdTrialRefillBeforeDamage'][0]
        self.assertIn('TDTrialRules_TD_TRIAL_TARGET_HP * 1.0', body)
        mutant = script.replace(body, body.replace('TDTrialRules_TD_TRIAL_TARGET_HP * 1.0', '15.0'), 1)
        with self.assertRaisesRegex(ValueError, 'Priority0 did not refill'):
            verify_damage_chain(mutant)

    def test_actual_current_capture_and_refund_mutation_rejected(self):
        path = os.environ.get('TRIAL_CANDIDATE_MAP')
        if not path: self.skipTest('Actual map NOT COVERED: TRIAL_CANDIDATE_MAP is required')
        from VerifyDamageRankingJass import functions
        script = Mpq(Path(path).read_bytes()).extract('war3map.j').decode()
        result = verify_current_capture(script)
        self.assertEqual(result['status'], 'PASS')
        body = functions(script)['tdPetHandleCapture'][0]
        lane = result['actual_lane_identifier']
        needle = 'call tdPetAddBall(' + lane + ')'
        self.assertIn(needle, body)
        mutant = script.replace(body, body.replace(needle, '// removed exact refund', 1), 1)
        with self.assertRaisesRegex(ValueError, 'refund and synchronize'):
            verify_current_capture(mutant)

if __name__ == '__main__': unittest.main()
