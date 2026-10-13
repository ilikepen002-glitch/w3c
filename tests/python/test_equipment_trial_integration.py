"""Final approved trial/equipment lifecycle source contracts, not gameplay."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
def src(p):return (ROOT/p).read_text()
class EquipmentTrialIntegration(unittest.TestCase):
    def test_independent_trial_register_and_remove_lifecycle(self):
        text=src('wurst/trial/TDTrialRuntime.wurst')
        self.assertIn('tdAuraRegisterTarget(target, false)',text)
        remove=text[text.index('public function tdTrialRemoveTarget'):text.index('public function tdTrialClearLaneTargets')]
        for fn in ['tdTrialForgetBinding(binding)','tdForgetAuraTarget(target)','tdForgetEquipmentShieldEnemy(target)','tdForgetEquipmentEnemy(target)','tdPetForgetEnemy(target)','target.remove()']:
            self.assertIn(fn,remove)
        self.assertLess(remove.index('tdTrialForgetBinding(binding)'),remove.index('tdForgetAuraTarget(target)'))
    def test_trial_speed_and_slow_require_live_independent_binding(self):
        text=src('wurst/enemies/TDEnemyMechanicRuntime.wurst')
        self.assertIn('tdTrialIsTargetType(enemy)',text)
        self.assertIn('tdTrialTargetValid(enemy, enemy.getUserData() div 10000)',text)
        self.assertIn('tdRefreshEnemyMoveSpeed(enemy, TD_TRIAL_TARGET_SPEED.toReal())',text)
        self.assertEqual(text.count('SetUnitMoveSpeed('),1)
        self.assertIn('tdTrialTargetValid(target, target.getUserData() div 10000)',src('wurst/auras/TDEnemySlowState.wurst'))
    def test_delayed_special_aoe_captures_context_and_exact_five_slot_revision(self):
        runtime=src('wurst/items/TDEquipmentSpecialRuntime.wurst')
        self.assertIn('let context = tdTrialCaptureContext(target)',runtime)
        self.assertIn('let snapshot = tdCaptureEquipmentTrialAoe(lane, context)',runtime)
        self.assertIn('if not tdTrialContextValid(context)',runtime)
        self.assertIn('snapshot.targetAt(slot)',runtime)
        self.assertIn('tdEquipmentTrialAoeVictimValid(victim, lane, context, snapshot.revisionAt(slot))',runtime)
        self.assertIn('tdTrialTargetContextValid(primary, lane, context, primaryRevision)',runtime)
        self.assertIn('tdTrialAoeTargetContextValid(victim, lane, context)',runtime)
        self.assertNotIn('tdTrialIsTargetType(target)\n\t\treturn',runtime)
    def test_retired_pet_slow_table_never_reappears_in_production(self):
        for path in (ROOT/'wurst').rglob('*.wurst'):
            self.assertNotIn('tdPetEnemySlowFactors',path.read_text(),str(path))
    def test_true_boss_identity_separate_from_current_trial_bonus(self):
        helper=src('wurst/items/TDItemTargetRules.wurst')
        self.assertIn('tdEquipmentBossDamageEligible(unit target, int sourceLane)',helper)
        self.assertIn('tdTrialEquipmentBossBonusEligible(tdTrialTargetValid(target, sourceLane)',helper)
        self.assertNotIn("'uTrG'",helper)
        pet=src('wurst/pets/TDPetCombat.wurst')
        self.assertIn('resolveActive(pet, host, generation, center, skill, strength, base, context)',pet)
        self.assertIn('tdFinalCooldownReduction(',pet)
        self.assertIn('pendingSerial',pet)
if __name__=='__main__':unittest.main()
