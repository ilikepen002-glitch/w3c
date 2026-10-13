"""Formal72 trial architecture contracts. These do not replace real JASS replay."""
from __future__ import annotations

import math
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = "72b2c9c3406868d33969c087dd5e6015abc3ac7b"


def text(path):
    return (ROOT / path).read_text(encoding="utf-8")


def locked_stdlib_text(path):
    """Inspect the configured locked source, never a retired pre1.29 cache."""
    lock = json.loads(text("tools/stdlib/lock.json"))
    source = Path(os.environ.get("WURST_STDLIB_SOURCE", str(ROOT / "_build/dependencies/WurstStdlib2-source")))
    if not source.exists() and "WURST_STDLIB_SOURCE" not in os.environ:
        source = Path(lock["source"])
    if not source.is_dir():
        raise ValueError("Missing trusted locked stdlib source; set WURST_STDLIB_SOURCE")
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=source, text=True).strip()
    if tree != lock["fixedTree"]:
        raise ValueError("Configured stdlib source differs from the project fixed tree")
    try:
        subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", path], cwd=source, check=True, capture_output=True)
    except subprocess.CalledProcessError as error:
        raise ValueError("Selected locked stdlib source file is dirty: " + path) from error
    if not (source / path).is_file():
        raise ValueError("Missing file in trusted locked stdlib source: " + path)
    return (source / path).read_text(encoding="utf-8")


class TrialStaticContracts(unittest.TestCase):
    def test_locked_stdlib_missing_source_is_rejected_without_old_cache_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            absent = str(Path(directory) / "absent")
            with patch.dict(os.environ, {"WURST_STDLIB_SOURCE": absent}):
                with self.assertRaisesRegex(ValueError, "Missing trusted locked stdlib source"):
                    locked_stdlib_text("wurst/objediting/UnitObjEditing.wurst")

    def test_locked_stdlib_wrong_tree_is_rejected_before_reading_api(self):
        # Inject only the external Git boundary; the actual helper/guard executes.
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"WURST_STDLIB_SOURCE": directory}), patch("subprocess.check_output", return_value="wrong-tree\n"):
                with self.assertRaisesRegex(ValueError, "differs from the project fixed tree"):
                    locked_stdlib_text("wurst/objediting/UnitObjEditing.wurst")

    def test_locked_stdlib_dirty_selected_file_is_rejected(self):
        fixed = json.loads(text("tools/stdlib/lock.json"))["fixedTree"]
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"WURST_STDLIB_SOURCE": directory}), patch("subprocess.check_output", return_value=fixed + "\n"), patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git diff")):
                with self.assertRaisesRegex(ValueError, "Selected locked stdlib source file is dirty"):
                    locked_stdlib_text("wurst/objediting/UnitObjEditing.wurst")

    def test_trial_dependency_direction_and_independent_native_runtime(self):
        pure = ("Rules", "Score", "State", "Targets", "LifeRules", "RouteRules")
        for name in pure:
            source = text("wurst/trial/TDTrial" + name + ".wurst")
            for forbidden in ("import TDGame", "import TDSpawn", "import TDTrialHook",
                              "tdCreateEnemy(", "tdGainGold(", "KillUnit("):
                self.assertNotIn(forbidden, source)
        identity = text("wurst/trial/TDTrialIdentity.wurst")
        self.assertNotIn("import TDTrialHook", identity)
        self.assertNotIn("import TDGame", identity)
        runtime = text("wurst/trial/TDTrialRuntime.wurst")
        self.assertNotIn("tdCreateEnemy(", runtime)
        self.assertNotIn("KillUnit(", runtime)
        self.assertNotIn("import TDTrialHook", runtime)
        hook = text("wurst/trial/TDTrialHook.wurst")
        self.assertIn("implements TDBossTransitionHook", hook)
        self.assertIn("tdResetAndRegisterTrialHook", hook)
        for path in ("wurst/TDHud.wurst", "wurst/damage/TDDamageRuntime.wurst",
                     "wurst/items/TDEquipmentCombat.wurst", "wurst/pets/TDPetCombat.wurst"):
            self.assertNotIn("import TDTrialHook", text(path))

    def test_formal_game_scheduler_wave_economy_and_build_contract_are_preserved(self):
        for path in ["wurst/TDGame.wurst", "wurst/TDWaves.wurst",
                     "tools/BuildEvolutionAssets.py", "wurst.build",
                     "wurst/TDWaveFlowState.wurst", "wurst/TDBossTransitionHook.wurst"]:
            with self.subTest(path=path):
                baseline = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
                self.assertEqual((ROOT / path).read_bytes(), baseline)
        source = text("wurst/TDInit.wurst")
        start = source.split("public function tdStartGame()", 1)[1]
        self.assertLess(start.index("tdShutdownGameFlow()"), start.index("tdResetState()"))
        self.assertLess(start.index("tdResetDamageStatistics()"), start.index("tdResetAndRegisterTrialHook()"))

    def test_object_identity_and_inherited_effects_are_explicit(self):
        source = text("wurst/trial/TDTrialObjectGen.wurst")
        self.assertIn("import Annotations", source)
        for expression in ["new UnitDefinition(TD_TRIAL_TARGET_UNIT_ID, UnitIds.battlegolem)",
                           "..setArmorType(ArmorType.Normal)", '..setNormalAbilities("")',
                           '..setDefaultActiveAbility("")', '..setUnitClassification("")',
                           "..setHitPointsMaximumBase(TD_TRIAL_TARGET_HP)",
                           "..setDefenseBase(0)", "..setSpeedMinimum(1)",
                           "..setSpeedMaximum(TD_TRIAL_TARGET_SPEED)",
                           "..setAttacksEnabled(0)", "..setAcquisitionRange(0.0)",
                           "..setCollisionSize(0.0)", "..setGoldBountyAwardedBase(0)",
                           "..setGoldBountyAwardedNumberofDice(0)", "..setGoldBountyAwardedSidesperDie(0)",
                           "..setPointValue(0)", "..setDeathType(0)",
                           "..setIconGameInterface(tdTrialIconPath())"]:
            self.assertIn(expression, source)
        self.assertNotIn("presetIcon(", source)
        wrapper = locked_stdlib_text("wurst/objediting/UnitObjEditing.wurst")
        for setter in set(re.findall(r"\.\.(set\w+)\(", source)):
            self.assertIn(f"function {setter}(", wrapper)
        assets = locked_stdlib_text("wurst/_wurst/assets/Units.wurst")
        self.assertIn('golemStatue1 = "Units\\\\Creeps\\\\GolemStatue\\\\GolemStatue.mdx"', assets)
        ids = locked_stdlib_text("wurst/_wurst/assets/UnitIds.wurst")
        self.assertIn("battlegolem = 'narg'", ids)

    def test_trial_rawcode_not_added_to_other_objects_or_boss_list(self):
        rules = text("wurst/trial/TDTrialRules.wurst")
        self.assertIn("TD_TRIAL_TARGET_UNIT_ID = 'uTrG'", rules)
        for path in (ROOT / "wurst").rglob("*.wurst"):
            if path.parent.name != "trial":
                self.assertNotIn("'uTrG'", path.read_text())
        catalog = text("wurst/enemies/TDEnemyMechanicData.wurst")
        self.assertNotIn("TD_TRIAL_TARGET_UNIT_ID", catalog)

    def test_score_conversions_are_bounded_and_no_hit_rounding(self):
        source = text("wurst/trial/TDTrialScore.wurst")
        source = "\n".join(line.split("//", 1)[0] for line in source.splitlines())
        block = source.split("function add(real effective)", 1)[1].split("function total()", 1)[0]
        self.assertIn("let carry = R2I(sum / TD_TRIAL_SCORE_CHUNK)", block)
        self.assertIn("remainder = sum - carry * TD_TRIAL_SCORE_CHUNK", block)
        self.assertIn("TD_TRIAL_SCORE_MAX_CHUNKS - carry", block)
        self.assertNotIn("R2I(effective", source)
        self.assertNotIn("R2I(total", source)
        self.assertIn("value != value", text("wurst/trial/TDTrialRules.wurst"))
        # Independent math oracle, not execution of the Wurst source.
        def accumulate(values):
            chunks, remainder = 0, 0.0
            for value in values:
                combined = remainder + value
                carry = int(combined / 1048576.0)
                chunks += carry
                remainder = combined - carry * 1048576.0
            rounded = int(remainder + 0.5)
            return chunks + rounded // 1048576, rounded % 1048576
        self.assertEqual(accumulate([0.25] * 3), (0, 1))
        self.assertEqual(accumulate([1000000.0] * 2148), (2048, 516352))
        self.assertEqual(accumulate([1000000.0, 48575.5]), (1, 0))
        self.assertFalse(math.nan >= 0 and math.nan <= 1e9)
        self.assertFalse(math.inf >= 0 and math.inf <= 1e9)
        self.assertEqual(min(1e12, 1e6), 1e6)
        self.assertEqual(min(math.inf, 1e6), 1e6)

    def test_settlement_and_rewards_are_guarded_by_active_token_and_cleanup(self):
        source = text("wurst/trial/TDTrialState.wurst")
        seal = source.split("function seal(", 1)[1].split("function markTargetsCleared(", 1)[0]
        self.assertIn("phase != TD_TRIAL_ACTIVE or not current(expectedToken, expectedGeneration)", seal)
        self.assertLess(seal.index("phase = TD_TRIAL_SEALED"), seal.index("rewards[lane] ="))
        self.assertIn("now >= deadline", seal)
        self.assertIn("not withdrawn[lane]", seal)
        self.assertIn("not scores[lane].isFaulted()", seal)
        self.assertIn("targets.clear()", seal)
        take = source.split("function takeReward(", 1)[1].split("function total(", 1)[0]
        self.assertIn("not canReturnToGame()", take)
        self.assertIn("not current(expectedToken, expectedGeneration)", take)
        self.assertIn("rewardTaken[lane] = true", take)
        self.assertNotIn("LinkedList", source)
        self.assertNotIn("HashSet", source)
        self.assertIn("private boolean array[2] attempted", source)

    def test_deadline_and_per_event_ticket_guards_are_present(self):
        source = text("wurst/trial/TDTrialState.wurst")
        self.assertIn("now >= deadline", source)
        self.assertIn("ticket.consumed = true", source)
        self.assertIn("sourceLane != ticket.lane", source)
        self.assertIn("ticket.revision", source)
        self.assertIn("generation += 1", source)
        life = text("wurst/trial/TDTrialLifeRules.wurst")
        self.assertIn("TD_TRIAL_REFILL_PRIORITY = 0", life)
        self.assertIn("TD_TRIAL_CREDIT_PRIORITY = 4", life)
        self.assertNotRegex(life, r"(?m)^\s*DamageEvent\.set(?:Reduced)?Amount\(")

    def test_current_source_damage_bound_stays_far_below_trial_hp(self):
        config = text("wurst/TDConfig.wurst")
        common = "\n".join(line.split("//", 1)[0] for line in text("wurst/towers/TDTowerCommonData.wurst").splitlines())
        balance = text("wurst/towers/TDTowerBalanceData.wurst")
        inventory = text("wurst/items/TDItemData.wurst")
        pets = text("wurst/pets/TDPetCombat.wurst")
        self.assertIn("TD_MAX_TOWER_LEVEL = 6", config)
        self.assertIn("TD_TOWER_EQUIPMENT_ATTACK_BONUS_MAX_LEVEL = 128", inventory)
        self.assertIn("abilityId == TD_PET_ATTACK_BONUS_ID ? 512 : 150", pets)
        damage_block = balance.split("function tdTowerBaseDamageCore", 1)[1].split("public function tdTowerBaseDamage(int", 1)[0]
        self.assertEqual(max(map(int, re.findall(r"return (\d+)\n", damage_block))), 260)
        self.assertIn("setAttack1DamageSidesperDie(6 + level)", text("wurst/towers/TDTowerObjectGen.wurst"))
        for function, value in [("tdEvolutionSkillMultiplier", "1.20"),
                                ("tdOrcCriticalStrikeMultiplier", "2.20"),
                                ("tdFootmanBashDamageMultiplier", "1.0"),
                                ("tdArcherAuraDamageBonus", "0.18"),
                                ("tdFootmanCommandAuraDamageBonus", "0.16")]:
            self.assertRegex(common, rf"function {function}\(\) returns real\n(?:\t\s*\n)*\treturn {re.escape(value)}\n")
        # Provisional source bound assumes armor amplification <2 and attack table <=2.
        # No target installation table is present: this is not an engine guarantee.
        self.assertLessEqual((0.18 + 0.16) * (1 + 1.2), 1.0)
        self.assertLessEqual(2.2 * 1.2, 3.0)
        native_bound = ((260 + 12 + 128 + 512) * 2 * 3 + 32) * 2 * 2
        split_bound = native_bound * 1.2 * 2 * 2
        # Current sealed catalog/mechanisms, no retired 45% Boss or native Bash bonus.
        catalog = text("wurst/items/TDItemCatalogConfig.wurst")
        self.assertRegex(common, r"function tdFootmanBashDamageBonus\(\) returns real\n(?:\t\s*\n)*\treturn 0.0\n")
        self.assertIn("TD_ITEM_EFFECT_EXECUTE", catalog)
        self.assertIn("TD_ITEM_EFFECT_BOSS_DAMAGE", catalog)
        import sys
        sys.path.insert(0, str(ROOT / 'tools'))
        from ReadEquipmentCatalog import catalog as read_catalog
        items = {item.rawcode: item for item in read_catalog(ROOT)}
        self.assertEqual(items['iB02'].secondary_value, .20)
        self.assertEqual(items['iP02'].secondary_value, .25)
        equipment_bound = native_bound * (items['iB02'].secondary_value + items['iP02'].secondary_value) * 4
        corpse_poison_bound = native_bound * .5 * 4
        pet_bound = native_bound * 1.7 * 4
        self.assertAlmostEqual(native_bound, 22016.0)
        self.assertAlmostEqual(pet_bound, 149708.8)
        self.assertLess(max(native_bound, split_bound, equipment_bound, corpse_poison_bound, pet_bound), 150000)
        self.assertEqual(150000, 1000000 * .15)
        self.assertIn("tdEquipmentTrialNativeEnvelope()", text("wurst/items/TDEquipmentTrialRules.wurst"))

    def test_wurst_sources_include_required_cases_without_generated_staging(self):
        source = text("tests/wurst/TDTrialStateTests.wurst")
        for name in ["trialFailedPartialPreparationCompletedReleaseCannotAward",
                     "trialTimerFirstAndGameWatchdogFirstBothSettleOnlyOnce",
                     "trialHitTicketsCreditEveryDistinctSegmentExactlyOnce",
                     "trialOldTargetRevisionAndGenerationCannotCreditReplacement",
                     "trialAbortAndUnexpectedEarlyReleaseAreZeroRewardCleanup",
                     "trialOpaqueTokensAndResetDoNotDependOnNumericOrdering"]:
            self.assertIn("@Test function " + name + "()", source)
        self.assertFalse((ROOT / "wurst/_tests/TDTrialStateTests.wurst").exists())
        self.assertFalse((ROOT / "wurst/_tests/TDTrialRulesTests.wurst").exists())


if __name__ == "__main__":
    unittest.main()
