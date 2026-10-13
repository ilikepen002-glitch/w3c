"""Focused source-only contracts for internally prepared purple specializations."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[2]
def read(p):return (ROOT/p).read_text()
class EquipmentPhaseC(unittest.TestCase):
    def test_existing_split_workflow_adds_one_arrow(self):
        tower=read('wurst/towers/TDTowerRuntime.wurst')
        self.assertIn('tdArcherSplitArrowTargetCount(level) - 1 + tdEquipmentArcherAdditionalArrows(source)',tower)
        self.assertIn('tdTryAddArcherSplitArrowShot(extraShots, source, victim, remainingTargets)',tower)
    def test_aoe_is_native_event_tagged_once_spell_resisted_and_no_pet_hook(self):
        runtime=read('wurst/items/TDEquipmentSpecialRuntime.wurst')
        self.assertIn('let eventAmount = DamageEvent.getAmount()',runtime)
        self.assertEqual(runtime.count('tdEnemyMechanicScaleSpellDamage('),1)
        self.assertIn('DamageEvent.setNextDamageFromCode()',runtime)
        self.assertIn('DamageEvent.setNextDamageId(damageId)',runtime)
        self.assertNotIn('tdPetOnCorpseExplosion',runtime)
        self.assertLess(runtime.index('tdDealSpecialSpell(source, primary'),runtime.index('for victim in targets'))
        self.assertIn('let center = target.getPos()',runtime)
        self.assertIn('doAfter(0.0)',runtime)
    def test_corpse_count_is_independent_of_current_target(self):
        rules=read('wurst/items/TDEquipmentSpecialRules.wurst')
        corpse=rules[rules.index('public class TDCorpseBurstState'):rules.index('public function tdWarStageName')]
        self.assertNotIn('currentTarget',corpse)
        self.assertIn('hits += 1',corpse)
        self.assertIn('stack = 0\n\t\treturn true',rules)
    def test_inventory_and_tower_lifecycle_clear_special_state(self):
        inventory=read('wurst/items/TDInventoryRuntime.wurst')
        combat=read('wurst/items/TDEquipmentCombat.wurst')
        self.assertIn('tdEquipmentSpecialLoadoutChanged(tower',inventory)
        self.assertIn('tdForgetEquipmentSpecial(tower)',combat)
        state=read('wurst/items/TDEquipmentSpecialState.wurst')
        self.assertIn('tdEquipmentSpecialByHandle.removeInt',state)
        self.assertIn('tdSpecialSyncBuff(record.tower',state)
    def test_shield_old_native_bash_is_no_damage_no_proc_every_level(self):
        obj=read('wurst/items/TDEquipmentObjectGen.wurst')
        bash=obj[obj.index('public function tdConfigureEquipmentBash'):obj.index('@compiletime function tdGenerateEquipmentArmorShred')]
        for field in ['setChancetoBash(level, 0.0)','setDamageMultiplier(level, 1.0)','setDamageBonus(level, 0.0)']:
            self.assertIn(field,bash)
        self.assertIn('for level = 1 to 61',bash)
    def test_shield_shared_reservation_rollback_then_bounded_spread(self):
        runtime=read('wurst/items/TDShieldRuntime.wurst')
        self.assertLess(runtime.index('record.window.reserve'),runtime.index('caster.castTarget'))
        self.assertIn('record.window.rollback(previous)',runtime)
        self.assertIn('Orders.thunderbolt',runtime)
        self.assertIn('TD_FOOT_PERFECT_BASH_ABILITY_ID',runtime)
        self.assertIn('tdIsBossUnitTypeId(GetUnitTypeId(target))',runtime)
        self.assertIn('tdIsBossUnitTypeId(GetUnitTypeId(victim))',runtime)
        self.assertNotIn('tdTowerEffectiveRange',runtime)
    def test_shield_native_parent_has_zero_damage_same_normal_hero_candidates(self):
        obj=read('wurst/items/TDEquipmentSpecialObjectGen.wurst')
        self.assertIn('AbilityDefinitionMountainKingThunderBolt',obj)
        self.assertIn('setDamage(level, 0.0)',obj)
        self.assertIn('setDurationNormal(level, duration)',obj)
        self.assertIn('setDurationHero(level, duration)',obj)
        self.assertIn('new AbilityDefinitionAttackSpeedIncrease(TD_WAR_INTENT_SPEED_CARRIER)',obj)
    def test_poison_timeout_and_all_upgrade_boundaries_clear_live_records(self):
        rules=read('wurst/items/TDEquipmentSpecialRules.wurst')
        self.assertIn('now >= lastHit + tdConfiguredPoisonBurstInactivity()',rules)
        self.assertIn('function hit(int targetKey, real now)',rules)
        runtime=read('wurst/items/TDEquipmentSpecialRuntime.wurst')
        self.assertIn('record.poison.hit(target.getHandleId(), now)',runtime)
        self.assertIn('record.poison.tick(getElapsedGameTime())',runtime)
        self.assertIn('doAfter(tdItemWarDuration())',runtime)
        self.assertIn('current.war.burstUntil == endTime',runtime)
        tower=read('wurst/towers/TDTowerRuntime.wurst')
        for function in ['tdHandleTowerUpgradeStarted','tdHandleTowerUpgradeCancelled','tdHandleTowerUpgradeFinished']:
            body=tower[tower.index('function '+function):]
            body=body[:body.index('\nfunction ',1)] if '\nfunction ' in body[1:] else body
            self.assertIn('tdForgetEquipmentSpecial(tower)',body)
    def test_retired_shield_damage_is_not_promised_by_tower_tooltip(self):
        balance=read('wurst/towers/TDTowerBalanceData.wurst')
        self.assertNotIn('追加20伤害',balance)
        self.assertNotIn('附伤20→24',balance)
        self.assertIn('tdConfiguredShieldNormalStunDuration()',balance)
    def test_new_runtime_setup_is_independent_and_ids_are_allocator_owned(self):
        init=read('wurst/TDInit.wurst')
        self.assertIn('tdSetupAuraRuntime()\n\ttdSetupEquipmentSpecialRuntime()',init)
        ids=read('wurst/items/TDEquipmentSpecialObjectIds.wurst')
        self.assertEqual(ids.count('compiletime(ABIL_ID_GEN.next())'),3)
        self.assertEqual(ids.count('compiletime(createDummyBuffObject('),6)
if __name__=='__main__':unittest.main()
