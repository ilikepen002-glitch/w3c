"""Actual packed JASS equipment checks; native engine behavior stays a boundary."""
import hashlib
import os
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from GenerateTowerTerrainMask import Mpq
from VerifyDamageRankingJass import functions
from VerifyEquipmentCombatReplay import verify_rules,verify_aura_apply,verify_new_aoe

class EquipmentPackedReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=os.environ.get('EQUIPMENT_CANDIDATE_MAP')
        if not path:raise unittest.SkipTest('Actual frozen equipment candidate not supplied')
        data=Path(path).read_bytes()
        expected=os.environ.get('TRIAL_CANDIDATE_MAP_SHA256')
        if not expected:raise ValueError('Frozen actual candidate SHA is required')
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Candidate does not match frozen SHA')
        cls.script=Mpq(data).extract('war3map.j').decode()

    def test_actual_aura_special_and_shield_rules(self):
        self.assertTrue(verify_rules(self.script)['actual_packed_rules'])

    def test_actual_carrier_failure_retry_and_independent_expiry(self):
        self.assertTrue(verify_aura_apply(self.script)['actual_carrier_failure_retry_same_rank_repair'])

    def test_actual_main_hit_aoe_contexts_and_handle_revisions(self):
        self.assertEqual(len(verify_new_aoe(self.script)['cases']),9)

    def test_slow_cap_mutation_rejected_for_the_specific_cap(self):
        body=functions(self.script)['tdCombinedEnemySlowFactor'][0]
        needle='TDAuraRules_TD_AURA_ENEMY_SLOW_CAP'
        self.assertIn(needle,body)
        mutant=self.script.replace(body,body.replace(needle,'0.90',1),1)
        with self.assertRaisesRegex(ValueError,'75% global cap'):
            verify_rules(mutant)

    def test_boss_shield_duration_mutation_rejected(self):
        body=functions(self.script)['tdShieldStunDuration'][0]
        needle='tdConfiguredShieldBossStunDuration()'
        self.assertIn(needle,body)
        mutant=self.script.replace(body,body.replace(needle,'0.50',1),1)
        with self.assertRaisesRegex(ValueError,'Boss separate shield window|Boss fixed stun'):
            verify_rules(mutant)

if __name__=='__main__':unittest.main()
