"""Narrow source contracts for the internally frozen aura preparation.
These assertions do not replace Wurst typecheck, generated-object validation or play.
"""
from pathlib import Path
import re
import unittest
ROOT = Path(__file__).resolve().parents[2]
def source(path): return (ROOT / path).read_text(encoding='utf-8')
class EquipmentPhaseB(unittest.TestCase):
    def test_stable_identities_and_bounded_real_buff_variants(self):
        rules = source('wurst/auras/TDAuraRules.wurst')
        ids = [int(x) for x in re.findall(r'TD_AURA_\w+ = (\d+)\n', rules) if int(x) <= 13]
        self.assertEqual(set(ids), set(range(1,14)))
        objects = source('wurst/auras/TDAuraObjectIds.wurst')
        self.assertEqual(objects.count('compiletime(createDummyBuffObject('), 38)
        self.assertEqual(objects.count('compiletime(ABIL_ID_GEN.next())'), 4)
    def test_rank_follows_coverage_and_never_identity_cross_max(self):
        rules = source('wurst/auras/TDAuraRules.wurst')
        self.assertLess(rules.index('if not covered'), rules.index('if tdAuraRankWins'))
        self.assertIn('powers[TD_AURA_VINES] + powers[TD_AURA_POISON_DART]', rules)
        runtime = source('wurst/auras/TDAuraRuntime.wurst')
        self.assertIn('normal > 0 and distance <= tdDryadAuraSlowRadius()', runtime)
        self.assertIn('wide > 0 and distance <= tdDryadWideAuraSlowRadius()', runtime)
        self.assertIn('source == target', runtime)
        self.assertIn('distance <= 600.0', runtime)
    def test_registered_round_robin_rotates_before_execute_and_timed_scan_is_local(self):
        runtime = source('wurst/auras/TDAuraRuntime.wurst')
        self.assertNotIn('enumUnitsInRect', runtime)
        self.assertIn('TD_AURA_TARGETS_PER_TICK = 16', runtime)
        self.assertIn('let success = try() ->', runtime)
        loop = runtime[runtime.index('for index = 1 to count'):]
        self.assertLess(loop.index('tdAuraTargets.add(record)'),loop.index('tdAuraRefresh(record)'))
        slow = source('wurst/auras/TDEnemySlowState.wurst')
        self.assertIn('for entry in record.timed', slow)
        self.assertNotIn('tdEnemyTimedSlows', slow)
        self.assertIn('entry.power == power', slow)
        state = source('wurst/auras/TDAuraState.wurst')
        self.assertIn('tdAuraTargetFor(target) != null', state)
        self.assertIn('tdAuraByHandle.removeInt', state)
    def test_one_speed_writer_preserves_saved_base_and_wild_branch(self):
        mechanic = source('wurst/enemies/TDEnemyMechanicRuntime.wurst')
        pet = source('wurst/pets/TDPetCombat.wurst')
        self.assertEqual(mechanic.count('SetUnitMoveSpeed('),1)
        self.assertNotIn('SetUnitMoveSpeed(',pet)
        self.assertIn('wild != null ? wild.travelSpeed : tdEnemyMechanicBaseSpeed(enemy)', mechanic)
        self.assertIn('tdRefreshEnemyMoveSpeed(record.enemy, record.state.originalBaseSpeed)',mechanic)
        self.assertNotIn('GetUnitMoveSpeed(',mechanic)
        self.assertIn('return record.state.baseSpeed()',mechanic)
        self.assertNotIn('return record.state.isSprinting() ?',mechanic)
        self.assertIn('tdDarkTideForgetBoss(record.enemy)',mechanic)
    def test_shared_cooldown_and_pet_host_only_no_old_world_loop(self):
        pet = source('wurst/pets/TDPetCombat.wurst')
        ability = source('wurst/items/TDEquipmentAbilities.wurst')
        self.assertNotIn('tdPetGlobalAura',pet)
        self.assertNotIn('enumUnitsInRect',pet)
        runtime = source('wurst/abilities/TDActiveCooldownRuntime.wurst')
        state = source('wurst/abilities/TDActiveSkillData.wurst')
        self.assertIn('tdStartScriptActiveCooldown(host, tdActiveSkillDefinitionForPetSkill(skill).key, getElapsedGameTime())', pet)
        self.assertIn('tdRefreshNativeActiveCooldowns(tower, cooldownReduction)', ability)
        self.assertIn('tdFinalCooldownReduction(personalReduction, tdPetCooldownReduction(tower), tdAuraPower(tower', runtime)
        self.assertIn('record.startCast(getElapsedGameTime(), active.baseCooldown, actualLevel)', runtime)
        self.assertIn('tdActiveCooldownReductionAtNativeLevel(actualLevel)', state)
        # Evaluate actual production aggregation, rather than duplicating its formula.
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        from VerifyActiveCooldownContract import SourceScalarEvaluator, read_sources
        rules = SourceScalarEvaluator(read_sources())
        self.assertAlmostEqual(rules.call('tdFinalCooldownReduction', [.10, .12, .18]), .40)
        self.assertAlmostEqual(rules.call('tdFinalCooldownReduction', [0, .12, .18]), .30)
        self.assertAlmostEqual(rules.call('tdFinalCooldownReduction', [-1, 0, .18]), .18)
    def test_native_only_movement_removed_and_percent_carriers_keep_parent_semantics(self):
        objects = source('wurst/items/TDEquipmentObjectGen.wurst')
        poison = objects[objects.index('public function tdConfigureEquipmentPoison'):objects.index('public function tdEquipmentSlowAuraReduction')]
        for preserved in ['setDamagePerSecond(level, dps)','setAttackSpeedFactor(level, 1.0 - attackFactor)','setDurationNormal(level, 5.0)','setDurationHero(level, 1.0)','"Bspo,Bssd"','"air,ground,organic"']:
            self.assertIn(preserved,poison)
        self.assertIn('setMovementSpeedFactor(level, 0.0)',poison)
        carriers = source('wurst/auras/TDAuraObjectGen.wurst')
        for parent in ['AbilityDefinitionMoonPriestessTrueshotAura','AbilityDefinitionItemAuraCommand']:
            self.assertIn(parent,carriers)
        self.assertEqual(carriers.count('setFlatBonus(1, false)'),2)
        self.assertEqual(carriers.count('setTargetsAllowed(1, "self")'),2)
    def test_on_hit_armor_scope_keeps_pet_independent(self):
        combat = source('wurst/items/TDEquipmentCombat.wurst')
        self.assertIn('RMaxBJ(tdEquipmentEffectForItems(item1, item2, item3, TD_ITEM_EFFECT_ARMOR_SHRED), tdAuraPower(source, TD_AURA_EQUIPMENT_ARMOR))', combat)
        pet = source('wurst/pets/TDPetCombat.wurst')
        self.assertIn('target.setAbilityLevel(TD_PET_ARMOR_ID, power.toInt())',pet)
    def test_cooldown_coverage_has_actual_supported_target_guard(self):
        runtime = source('wurst/auras/TDAuraRuntime.wurst')
        refresh = runtime[runtime.index('function tdAuraRefresh('):runtime.index('public function tdForgetAuraTarget(')]
        offer = runtime[runtime.index('function tdAuraOfferSource('):runtime.index('function tdAuraRefresh(')]
        self.assertIn('let cooldownEligible = record.tower and tdAuraCooldownTargetEligible(target)', refresh)
        self.assertEqual(refresh.count('tdAuraCooldownTargetEligible(target)'), 1)
        self.assertIn('tdAuraOfferSource(record, source.target, prepared, targetLane, targetPos, mechanical, cooldownEligible)', refresh)
        self.assertIn('boolean cooldownEligible)', offer)
        self.assertNotIn('tdAuraCooldownTargetEligible(', offer)
        # Unsupported cooldown items are rejected before offering a contribution.
        self.assertIn('if kind == TD_ITEM_AURA_COOLDOWN and not cooldownEligible\n\t\t\tcontinue', offer)
        self.assertLess(offer.index('if kind == TD_ITEM_AURA_COOLDOWN and not cooldownEligible'),
                        offer.index('aggregate.offer(tdEquipmentAuraIdentity(kind)'))
        self.assertIn('tdPetBindingValid(pet, target, pet.generation)',runtime)
        self.assertIn('tdPetUnlockedSlots(pet.level)',runtime)
        self.assertIn('tdPetSkillIsActive(skill) and tdPetSkillFitsHost(skill, target)',runtime)
        self.assertIn('tdAuraCooldownTargetSupported(tdHasNativeActiveCooldown(target), binding, activeUnlocked)',runtime)
        self.assertNotIn('TD_ORC_BLOODLUST_ABILITY_ID',runtime)
        self.assertNotIn('TD_ORC_BLADESTORM_ABILITY_ID',runtime)
    def test_native_percent_identity_has_only_one_buff_emitter(self):
        state = source('wurst/auras/TDAuraState.wurst')
        self.assertIn('identity <= TD_AURA_COMMANDER ? tdAuraCarrier(identity, rank) : stateBuff.abilId',state)
        self.assertIn('target.addPermanentAbility(carrier)',state)
    def test_shown_rank_commits_only_after_actual_carrier_and_missing_same_rank_repairs(self):
        state = source('wurst/auras/TDAuraState.wurst')
        self.assertIn('tdAuraCarrierRepairNeeded(rank, oldRank, carrierPresent)',state)
        self.assertIn('record.pendingApplications[identity] = true',state)
        self.assertIn('return // pending stays true',state)
        commit = state.index('record.shownRanks[identity] = tdAuraConfirmedAppliedRank')
        actual = state.rindex('carrierPresent = carrier != 0 and target.getAbilityLevel(carrier) > 0')
        self.assertLess(actual, commit)
    def test_low_state_has_no_runtime_dependency(self):
        state = source('wurst/auras/TDAuraState.wurst')
        imports = re.findall(r'^import (?:public )?(\w+)',state,re.M)
        self.assertFalse(set(imports)&{'TDInventoryRuntime','TDAuraRuntime','TDPetCombat','TDEnemyMechanicRuntime'})
        init = source('wurst/TDInit.wurst')
        self.assertIn('tdSetupInventoryRuntime()\n\ttdSetupAuraRuntime()',init)
if __name__ == '__main__': unittest.main()
