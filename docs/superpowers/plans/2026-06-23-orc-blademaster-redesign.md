# Orc Blademaster Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the orc tower so level 5 becomes a single-target Sword Dance Blademaster, branch A becomes a Bloodlust-powered single-target finisher, and branch B becomes a balanced crit plus autocast Bladestorm tower with correct icons and tooltips.

**Architecture:** Keep the existing tower family shape and rawcode upgrade chain intact. Implement the redesign by updating orc tower constants, tooltip text, and object-generation ability wiring, then add a small runtime handler only for the custom autocast-friendly Bladestorm branch behavior.

**Tech Stack:** WurstScript, compiletime object generation, WurstStdlib2 object editing wrappers, project bat/ps1 validation scripts

---

### Task 1: Lock the new orc design in tests

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\tests\wurst\TDTowersTests.wurst`
- Reference: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerCatalogData.wurst`
- Reference: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerCommonData.wurst`

- [ ] **Step 1: Write the failing test**

```wurst
@Test function orcProgressionUsesSwordDanceBloodlustAndBladestorm()
	tdTowerNormalAbilitiesRawcodes(TD_TOWER_CHOICE_ORC, 5).assertEquals("A102,A103")
	tdTowerNormalAbilitiesRawcodesForBranch(TD_TOWER_CHOICE_ORC, 6, TD_TOWER_BRANCH_A).assertEquals("A102,A104,A130")
	tdTowerNormalAbilitiesRawcodesForBranch(TD_TOWER_CHOICE_ORC, 6, TD_TOWER_BRANCH_B).assertEquals("A102,A105,A130")

@Test function orcIconsAndTooltipsMatchRedesignedRoles()
	tdOrcSwordDanceIconPath().assertEquals("ReplaceableTextures\\CommandButtons\\BTNMirrorImage.blp")
	tdOrcBloodlustIconPath().assertEquals("ReplaceableTextures\\CommandButtons\\BTNBloodLust.blp")
	tdOrcBladestormIconPath().assertEquals("ReplaceableTextures\\CommandButtons\\BTNWhirlwind.blp")
	tdTowerTooltipExtended(TD_TOWER_CHOICE_ORC, 5).contains("剑舞").assertTrue()
	tdTowerTooltipExtendedForBranch(TD_TOWER_CHOICE_ORC, 6, TD_TOWER_BRANCH_A).contains("嗜血").assertTrue()
	tdTowerTooltipExtendedForBranch(TD_TOWER_CHOICE_ORC, 6, TD_TOWER_BRANCH_B).contains("剑刃风暴").assertTrue()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `tools\Run-WurstChecks.bat test TDTowersTests`

Expected: FAIL on the new orc ability rawcode and tooltip expectations because the old cleave-based design is still present.

- [ ] **Step 3: Expand the failing coverage for runtime tuning helpers**

```wurst
@Test function orcBranchTuningHelpersExposeCooldownAndDamagePlan()
	tdOrcSwordDanceAttackSpeedBonus().assertGreaterThan(0.0)
	tdOrcBloodlustCooldown().assertGreaterThan(0.0)
	tdOrcBladestormCooldown().assertGreaterThan(0.0)
	tdOrcBladestormDamagePerSecond().assertGreaterThan(0.0)
```

- [ ] **Step 4: Run test to verify it also fails for missing helper functions**

Run: `tools\Run-WurstChecks.bat test TDTowersTests`

Expected: FAIL with unknown identifier or mismatched expected values until the helpers are implemented.

### Task 2: Rewire orc data and compiletime abilities

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerCatalogData.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerCommonData.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerBalanceData.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerObjectGen.wurst`

- [ ] **Step 1: Add orc rawcodes and tuning helpers**

```wurst
public constant int TD_ORC_SWORD_DANCE_ABILITY_ID = 'A103'
public constant int TD_ORC_BLOODLUST_ABILITY_ID = 'A104'
public constant int TD_ORC_BLADESTORM_ABILITY_ID = 'A105'

public function tdOrcSwordDanceAttackSpeedBonus() returns real
	return 0.30
```

- [ ] **Step 2: Update the skill-bar routing**

```wurst
if towerChoice == TD_TOWER_CHOICE_ORC
	if level >= 5
		if level >= TD_MAX_TOWER_LEVEL
			if branch == TD_TOWER_BRANCH_B
				return commaList(TD_ORC_CRIT_ABILITY_ID, TD_ORC_BLADESTORM_ABILITY_ID, TD_TOWER_REFINE_ABILITY_ID)
			return commaList(TD_ORC_CRIT_ABILITY_ID, TD_ORC_BLOODLUST_ABILITY_ID, TD_TOWER_REFINE_ABILITY_ID)
		return commaList(TD_ORC_CRIT_ABILITY_ID, TD_ORC_SWORD_DANCE_ABILITY_ID)
	return TD_ORC_CRIT_ABILITY_ID.toRawCode()
```

- [ ] **Step 3: Regenerate orc ability definitions with matching icons, cooldowns, and tooltip text**

```wurst
new AbilityDefinitionAttackSpeedIncrease(TD_ORC_SWORD_DANCE_ABILITY_ID)
	..setName("剑舞")
	..presetIcon(tdOrcSwordDanceIconPath())

new AbilityDefinitionBloodlust(TD_ORC_BLOODLUST_ABILITY_ID)
	..setName("嗜血")
	..presetIcon(tdOrcBloodlustIconPath())
	..presetCooldown(lvl -> tdOrcBloodlustCooldown())

new ChannelAbilityPreset(TD_ORC_BLADESTORM_ABILITY_ID, 1, true)
	..setName("剑刃风暴")
	..presetIcon(tdOrcBladestormIconPath())
	..makeUnitSpell(0, tdOrcBladestormCooldown())
```

- [ ] **Step 4: Update orc lore and branch summaries**

```wurst
if towerChoice == TD_TOWER_CHOICE_ORC and level == 5
	return "剑圣以致命一击配合剑舞持续追砍高威胁目标。"
```

- [ ] **Step 5: Run tests to verify the data-layer changes pass**

Run: `tools\Run-WurstChecks.bat test TDTowersTests`

Expected: PASS for the updated orc progression assertions, but runtime-related branch B behavior may still be missing until Task 3 is complete.

### Task 3: Implement the branch B autocast-friendly Bladestorm runtime

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerRuntime.wurst`
- Reference: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerCommonData.wurst`
- Reference: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerCatalogData.wurst`

- [ ] **Step 1: Add a failing helper test for the branch B runtime gate**

```wurst
@Test function orcBladestormRuntimeHelpersPreferUltimateBranchB()
	tdOrcBladestormAutocastEnemyCount().assertGreaterThan(0)
	tdOrcBladestormDuration().assertGreaterThan(0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `tools\Run-WurstChecks.bat test TDTowersTests`

Expected: FAIL because the helper functions do not exist yet.

- [ ] **Step 3: Add the minimal runtime handler**

```wurst
function tdHandleOrcBladestormCast() returns boolean
	let tower = GetTriggerUnit()
	if tower == null
		return false
	tdStartOrcBladestormPulse(tower)
	return false
```

- [ ] **Step 4: Register the runtime spell effect and periodic damage pulse**

```wurst
registerSpellEffectEvent(TD_ORC_BLADESTORM_ABILITY_ID, function tdHandleOrcBladestormCast)
```

- [ ] **Step 5: Run checks to verify the runtime path compiles cleanly**

Run: `tools\Run-WurstChecks.bat`

Expected: PASS with the new branch B runtime support compiled into the map script.

### Task 4: Full validation and review gate

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\tests\wurst\TDTowersTests.wurst` (only if verification exposes gaps)
- Review: `D:\War3Projects\MyFirstWurstMap\tools\Invoke-GeminiReview.ps1`

- [ ] **Step 1: Run the project checks**

Run: `tools\Run-WurstChecks.bat`

Expected: PASS

- [ ] **Step 2: Run the gameplay-sensitive map build**

Run: `build-and-deploy-test-map.bat`

Expected: PASS because object generation and runtime spell wiring both changed.

- [ ] **Step 3: Run Gemini review**

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\Invoke-GeminiReview.ps1 -Task "重做兽人剑圣塔：5级改为致命一击+剑舞，6A为嗜血单体爆发，6B为可自动释放的剑刃风暴平衡分支，并修正技能图标与说明。"
```

Expected: `PASS` or `PASS WITH NOTES`

- [ ] **Step 4: If Gemini reports issues, fix them and re-run the affected verification commands**

Run: Repeat `tools\Run-WurstChecks.bat` and `build-and-deploy-test-map.bat` after each fix.

- [ ] **Step 5: Summarize exact verification evidence**

Record:
- Which tests ran
- Whether the map build succeeded
- Whether Gemini was executed and its final verdict
