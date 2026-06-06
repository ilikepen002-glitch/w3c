# Single-Player TD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a playable single-player Warcraft III tower defense prototype with fixed tower pads, five waves, built-in Warcraft III towers/enemies, and clear win/lose conditions.

**Architecture:** Keep the prototype map simple and put the game rules in focused Wurst packages. Normalize the project first so `JASS + pre1.29` compiles cleanly, then add pure-data packages with Wurst unit tests, and finally wire gameplay systems such as spawning, leaks, pad selection dialogs, and round flow.

**Tech Stack:** WurstScript, Grill CLI, Warcraft III 1.27a, built-in Warcraft III units/buildings, WurstStdlib2 pre1.29

---

## File Structure

- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfig.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDState.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDWaves.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDSpawn.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDGame.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDInit.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfigTests.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDStateTests.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDWavesTests.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowersTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\Hello.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst.build`
- Modify: `D:\War3Projects\MyFirstWurstMap\.vscode\settings.json`
- Modify: `D:\War3Projects\MyFirstWurstMap\ExampleMap.w3x` for final lane/pad coordinates

### Task 1: Normalize The Project Runtime

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst.build`
- Modify: `D:\War3Projects\MyFirstWurstMap\.vscode\settings.json`
- Create/Move: `D:\War3Projects\MyFirstWurstMap\_build\dependencies\pre1.29\WurstStdlib2\...`

- [ ] **Step 1: Run a failing static verification**

Run:

```powershell
grill typecheck
```

Expected: fail because the current project still points at the wrong patch/runtime or cannot resolve the manually downloaded stdlib reliably.

- [ ] **Step 2: Rewrite the build configuration for `JASS + pre1.29`**

Replace `D:\War3Projects\MyFirstWurstMap\wurst.build` with:

```yaml
projectName: MyFirstWurstMap
dependencies:
  - https://github.com/wurstscript/WurstStdlib2:pre1.29
buildMapData:
  name: My First Wurst Map
  fileName: MyFirstWurstMap.w3x
  author: huawei
  scenarioData:
    suggestedPlayers: "1"
scriptMode: JASS
wc3Patch: pre1.29
```

- [ ] **Step 3: Normalize the local stdlib checkout into the path Grill expects**

Run:

```powershell
New-Item -ItemType Directory -Force 'D:\War3Projects\MyFirstWurstMap\_build\dependencies\pre1.29\WurstStdlib2' | Out-Null
Copy-Item 'D:\War3Projects\MyFirstWurstMap\_build\dependencies\WurstStdlib2\WurstStdlib2-pre1.29\*' 'D:\War3Projects\MyFirstWurstMap\_build\dependencies\pre1.29\WurstStdlib2' -Recurse -Force
```

This keeps the dependency URL stable in `wurst.build` while satisfying offline/local resolution.

- [ ] **Step 4: Keep VS Code pointed at the correct Warcraft III runtime**

Update `D:\War3Projects\MyFirstWurstMap\.vscode\settings.json` to:

```json
{
  "wurst.javaOpts": ["-XX:+UseStringDeduplication", "-Xmx4G"],
  "wurst.wc3path": "D:\\War3_1.27a\\Warcraft III Frozen Throne 1.27a publish",
  "wurst.gameExePath": "D:\\War3_1.27a\\Warcraft III Frozen Throne 1.27a publish\\Frozen Throne.exe",
  "wurst.mapDocumentPath": "D:\\War3_1.27a\\Warcraft III Frozen Throne 1.27a publish\\Maps\\Test",
  "files.associations": {
    "wurst.build": "yaml"
  },
  "search.useIgnoreFiles": false,
  "yaml.schemas": {
    "./.vscode/wbschema.json": "/wurst.build"
  }
}
```

- [ ] **Step 5: Re-run static verification and confirm the project typechecks**

Run:

```powershell
grill typecheck
```

Expected: pass with no dependency-resolution error.

- [ ] **Step 6: Commit the runtime normalization**

Run:

```powershell
git init
git add wurst.build .vscode/settings.json _build/dependencies/pre1.29/WurstStdlib2 docs/superpowers/specs/2026-06-05-single-player-td-design.md
git commit -m "chore: normalize wurst td project runtime"
```

### Task 2: Add TD Constants And Pure Config Tests

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfig.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfigTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\Hello.wurst`

- [ ] **Step 1: Write the failing config tests**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDConfigTests.wurst`:

```wurst
package TDConfigTests
import TDConfig
import Wurstunit

@Test function startingValuesArePositive()
	TD_STARTING_LIVES.assertGreaterThan(0)
	TD_STARTING_GOLD.assertGreaterThan(0)

@Test function towerChoiceCountIsThree()
	TD_TOWER_CHOICE_COUNT.assertEquals(3)

@Test function padCountIsAtLeastThree()
	TD_PAD_COUNT.assertGreaterThanOrEqual(3)
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
grill test TDConfigTests
```

Expected: fail because package `TDConfig` and its constants do not exist yet.

- [ ] **Step 3: Add the minimum TD configuration package**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDConfig.wurst`:

```wurst
package TDConfig
import Vectors

public constant int TD_STARTING_LIVES = 20
public constant int TD_STARTING_GOLD = 300
public constant int TD_TOWER_CHOICE_COUNT = 3
public constant int TD_PAD_COUNT = 5
public constant real TD_TIME_BETWEEN_WAVES = 8.00

public constant int TD_PLAYER_ID = 0
public constant int TD_ENEMY_PLAYER_ID = PLAYER_NEUTRAL_AGGRESSIVE
public constant int TD_PAD_UNIT_ID = 'hhou'

public constant int TD_ARROW_TOWER_ID = 'hgtw'
public constant int TD_CANNON_TOWER_ID = 'hctw'
public constant int TD_LONG_RANGE_TOWER_ID = 'hatw'

public constant int TD_ARROW_TOWER_COST = 80
public constant int TD_CANNON_TOWER_COST = 125
public constant int TD_LONG_RANGE_TOWER_COST = 110

public constant vec2 TD_SPAWN_POS = vec2(-1024, 0)
public constant vec2 TD_END_POS = vec2(1024, 0)

public function tdPadPosition(int index) returns vec2
	if index == 0
		return vec2(-512, 256)
	if index == 1
		return vec2(-256, -256)
	if index == 2
		return vec2(0, 256)
	if index == 3
		return vec2(256, -256)
	return vec2(512, 256)
```

- [ ] **Step 4: Replace the demo init with a harmless placeholder entry point**

Replace `D:\War3Projects\MyFirstWurstMap\wurst\Hello.wurst` with:

```wurst
package Hello

init
	print("TD project bootstrap loaded.")
```

- [ ] **Step 5: Re-run config tests**

Run:

```powershell
grill test TDConfigTests
```

Expected: pass.

- [ ] **Step 6: Commit the config baseline**

Run:

```powershell
git add wurst/TDConfig.wurst wurst/TDConfigTests.wurst wurst/Hello.wurst
git commit -m "test: add td config baseline"
```

### Task 3: Add Pure State And Wave Definitions

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDState.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDStateTests.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDWaves.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDWavesTests.wurst`

- [ ] **Step 1: Write failing state tests**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDStateTests.wurst`:

```wurst
package TDStateTests
import TDState
import TDConfig
import Wurstunit

@Test function resetRestoresDefaults()
	tdResetState()
	tdGetLives().assertEquals(TD_STARTING_LIVES)
	tdGetGold().assertEquals(TD_STARTING_GOLD)
	tdGetCurrentWave().assertEquals(0)

@Test function spendGoldReducesBalance()
	tdResetState()
	tdSpendGold(50)
	tdGetGold().assertEquals(TD_STARTING_GOLD - 50)

@Test function losingLifeReducesLives()
	tdResetState()
	tdLoseLife(2)
	tdGetLives().assertEquals(TD_STARTING_LIVES - 2)
```

- [ ] **Step 2: Write failing wave tests**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDWavesTests.wurst`:

```wurst
package TDWavesTests
import TDWaves
import Wurstunit

@Test function waveCountIsFive()
	tdWaveCount().assertEquals(5)

@Test function waveOneSpawnsEnemies()
	tdWaveEnemyCount(1).assertGreaterThan(0)
	tdWaveReward(1).assertGreaterThan(0)

@Test function waveFiveIsHarderThanWaveOne()
	tdWaveEnemyCount(5).assertGreaterThan(tdWaveEnemyCount(1))
```

- [ ] **Step 3: Run the new tests and verify they fail**

Run:

```powershell
grill test TDStateTests
grill test TDWavesTests
```

Expected: fail because `TDState` and `TDWaves` do not exist yet.

- [ ] **Step 4: Implement the minimum mutable state package**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDState.wurst`:

```wurst
package TDState
import TDConfig

int tdLives = TD_STARTING_LIVES
int tdGold = TD_STARTING_GOLD
int tdCurrentWave = 0
boolean tdGameOver = false

public function tdResetState()
	tdLives = TD_STARTING_LIVES
	tdGold = TD_STARTING_GOLD
	tdCurrentWave = 0
	tdGameOver = false

public function tdGetLives() returns int
	return tdLives

public function tdGetGold() returns int
	return tdGold

public function tdGetCurrentWave() returns int
	return tdCurrentWave

public function tdSetCurrentWave(int wave)
	tdCurrentWave = wave

public function tdSpendGold(int amount)
	tdGold -= amount

public function tdGainGold(int amount)
	tdGold += amount

public function tdLoseLife(int amount)
	tdLives -= amount

public function tdIsGameOver() returns boolean
	return tdGameOver

public function tdSetGameOver(boolean value)
	tdGameOver = value
```

- [ ] **Step 5: Implement explicit five-wave definitions**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDWaves.wurst`:

```wurst
package TDWaves

public function tdWaveCount() returns int
	return 5

public function tdWaveUnitId(int wave) returns int
	if wave == 1
		return 'hfoo'
	if wave == 2
		return 'hrif'
	if wave == 3
		return 'ogru'
	if wave == 4
		return 'orai'
	return 'otau'

public function tdWaveEnemyCount(int wave) returns int
	if wave == 1
		return 6
	if wave == 2
		return 8
	if wave == 3
		return 10
	if wave == 4
		return 12
	return 14

public function tdWaveSpawnInterval(int wave) returns real
	if wave <= 2
		return 1.00
	if wave <= 4
		return 0.85
	return 0.70

public function tdWaveReward(int wave) returns int
	if wave == 1
		return 60
	if wave == 2
		return 80
	if wave == 3
		return 100
	if wave == 4
		return 125
	return 160
```

- [ ] **Step 6: Re-run the pure logic tests**

Run:

```powershell
grill test TDStateTests
grill test TDWavesTests
```

Expected: both pass.

- [ ] **Step 7: Commit the state and wave layer**

Run:

```powershell
git add wurst/TDState.wurst wurst/TDStateTests.wurst wurst/TDWaves.wurst wurst/TDWavesTests.wurst
git commit -m "test: add td state and wave definitions"
```

### Task 4: Build Enemy Spawn And Leak Handling

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDSpawn.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDGame.wurst`

- [ ] **Step 1: Add a failing integration checkpoint**

Create a temporary reference to the not-yet-existing spawn API in `D:\War3Projects\MyFirstWurstMap\wurst\Hello.wurst`:

```wurst
package Hello
import TDSpawn

init
	tdSpawnWave(1)
```

- [ ] **Step 2: Run typecheck and verify it fails**

Run:

```powershell
grill typecheck
```

Expected: fail because package `TDSpawn` and `tdSpawnWave` do not exist yet.

- [ ] **Step 3: Implement enemy spawn scheduling**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDSpawn.wurst`:

```wurst
package TDSpawn
import TDConfig
import TDWaves
import ClosureTimers
import Unit
import Vectors

public function tdOrderEnemyToExit(unit enemy)
	enemy.issuePointOrderById(OrderId("move"), TD_END_POS)

public function tdCreateEnemy(int wave) returns unit
	let enemy = createUnit(Player(TD_ENEMY_PLAYER_ID), tdWaveUnitId(wave), TD_SPAWN_POS, 0 .fromDeg())
	tdOrderEnemyToExit(enemy)
	return enemy

public function tdSpawnWave(int wave)
	let count = tdWaveEnemyCount(wave)
	let interval = tdWaveSpawnInterval(wave)
	doPeriodicallyCounted(interval, count) cb ->
		tdCreateEnemy(wave)
```

- [ ] **Step 4: Implement base leak detection and life loss**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDGame.wurst`:

```wurst
package TDGame
import TDConfig
import TDState
import ClosureTimers
import Group
import Unit
import Vectors

rect tdEndRect = Rect(TD_END_POS.x - 96, TD_END_POS.y - 96, TD_END_POS.x + 96, TD_END_POS.y + 96)

public function tdRefreshHud()
	DisplayTimedTextToPlayer(Player(TD_PLAYER_ID), 0, 0, 1.0, "Lives: " + tdGetLives().toString() + " Gold: " + tdGetGold().toString() + " Wave: " + tdGetCurrentWave().toString())

public function tdHandleEnemyLeak(unit enemy)
	if enemy != null and enemy.isAlive()
		tdLoseLife(1)
		enemy.kill()
		tdRefreshHud()

public function tdStartLeakWatcher()
	doPeriodically(0.25) cb ->
		let g = CreateGroup()
		GroupEnumUnitsInRect(g, tdEndRect, null)
		ForGroup(g, () ->
			let u = GetEnumUnit()
			if GetOwningPlayer(u) == Player(TD_ENEMY_PLAYER_ID)
				tdHandleEnemyLeak(u)
		)
		DestroyGroup(g)
		if tdIsGameOver()
			destroy cb
```

- [ ] **Step 5: Restore the placeholder entry point to a non-destructive typecheckable form**

Replace `D:\War3Projects\MyFirstWurstMap\wurst\Hello.wurst` with:

```wurst
package Hello
import TDGame

init
	tdStartLeakWatcher()
```

- [ ] **Step 6: Re-run typecheck**

Run:

```powershell
grill typecheck
```

Expected: pass.

- [ ] **Step 7: Commit spawn and leak handling**

Run:

```powershell
git add wurst/TDSpawn.wurst wurst/TDGame.wurst wurst/Hello.wurst
git commit -m "feat: add td spawn and leak handling"
```

### Task 5: Add Tower Choice Mapping And Build Validation

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowersTests.wurst`

- [ ] **Step 1: Write failing tower tests**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDTowersTests.wurst`:

```wurst
package TDTowersTests
import TDTowers
import TDConfig
import TDState
import Wurstunit

@Test function towerChoiceMapsToExpectedCost()
	tdTowerCost(1).assertEquals(TD_ARROW_TOWER_COST)
	tdTowerCost(2).assertEquals(TD_CANNON_TOWER_COST)
	tdTowerCost(3).assertEquals(TD_LONG_RANGE_TOWER_COST)

@Test function playerCanAffordCheapTowerAtStart()
	tdResetState()
	tdCanAffordTower(1).assertTrue()

@Test function impossibleTowerChoiceReturnsZeroCost()
	tdTowerCost(999).assertEquals(0)
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
grill test TDTowersTests
```

Expected: fail because package `TDTowers` does not exist yet.

- [ ] **Step 3: Implement tower metadata and affordability**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`:

```wurst
package TDTowers
import TDConfig
import TDState
import Unit
import Vectors

unit array tdPads

public function tdTowerUnitId(int choice) returns int
	if choice == 1
		return TD_ARROW_TOWER_ID
	if choice == 2
		return TD_CANNON_TOWER_ID
	if choice == 3
		return TD_LONG_RANGE_TOWER_ID
	return 0

public function tdTowerCost(int choice) returns int
	if choice == 1
		return TD_ARROW_TOWER_COST
	if choice == 2
		return TD_CANNON_TOWER_COST
	if choice == 3
		return TD_LONG_RANGE_TOWER_COST
	return 0

public function tdCanAffordTower(int choice) returns boolean
	return tdGetGold() >= tdTowerCost(choice)

public function tdCreatePads()
	for i = 0 to TD_PAD_COUNT - 1
		tdPads[i] = createUnit(Player(PLAYER_NEUTRAL_PASSIVE), TD_PAD_UNIT_ID, tdPadPosition(i), 0 .fromDeg())

public function tdBuildTowerAtPad(int padIndex, int towerChoice) returns boolean
	if padIndex < 0 or padIndex >= TD_PAD_COUNT
		return false
	if tdPads[padIndex] == null
		return false
	if not tdCanAffordTower(towerChoice)
		return false
	let pos = tdPads[padIndex].getPos()
	tdPads[padIndex].kill()
	tdPads[padIndex] = null
	createUnit(Player(TD_PLAYER_ID), tdTowerUnitId(towerChoice), pos, 0 .fromDeg())
	tdSpendGold(tdTowerCost(towerChoice))
	return true
```

- [ ] **Step 4: Add the first-pass fixed-pad selection dialog**

Append this dialog logic to `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`:

```wurst
dialog tdBuildDialog = DialogCreate()
button tdArrowButton = null
button tdCannonButton = null
button tdLongRangeButton = null
int tdSelectedPad = -1

public function tdSetupBuildDialog()
	tdArrowButton = DialogAddButton(tdBuildDialog, "Arrow Tower", 0)
	tdCannonButton = DialogAddButton(tdBuildDialog, "Cannon Tower", 0)
	tdLongRangeButton = DialogAddButton(tdBuildDialog, "Long Range Tower", 0)

public function tdShowBuildDialogForPad(int padIndex)
	tdSelectedPad = padIndex
	DialogDisplay(Player(TD_PLAYER_ID), tdBuildDialog, true)
```

Then wire trigger callbacks in the same file:

```wurst
trigger tdDialogTrigger = CreateTrigger()
trigger tdPadSelectTrigger = CreateTrigger()

public function tdSetupPadSelection()
	TriggerRegisterPlayerUnitEvent(tdPadSelectTrigger, Player(TD_PLAYER_ID), EVENT_PLAYER_UNIT_SELECTED, null)
	TriggerAddAction(tdPadSelectTrigger, () ->
		let selected = GetTriggerUnit()
		for i = 0 to TD_PAD_COUNT - 1
			if tdPads[i] == selected
				tdShowBuildDialogForPad(i)
	)

public function tdSetupDialogTrigger()
	TriggerRegisterDialogEvent(tdDialogTrigger, tdBuildDialog)
	TriggerAddAction(tdDialogTrigger, () ->
		let clicked = GetClickedButton()
		if clicked == tdArrowButton
			tdBuildTowerAtPad(tdSelectedPad, 1)
		if clicked == tdCannonButton
			tdBuildTowerAtPad(tdSelectedPad, 2)
		if clicked == tdLongRangeButton
			tdBuildTowerAtPad(tdSelectedPad, 3)
		DialogDisplay(Player(TD_PLAYER_ID), tdBuildDialog, false)
	)
```

- [ ] **Step 5: Re-run the tower tests**

Run:

```powershell
grill test TDTowersTests
```

Expected: pass.

- [ ] **Step 6: Commit tower metadata and build flow**

Run:

```powershell
git add wurst/TDTowers.wurst wurst/TDTowersTests.wurst
git commit -m "feat: add td tower pad build flow"
```

### Task 6: Wire Full Round Flow, Victory, And Defeat

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDInit.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDGame.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\Hello.wurst`

- [ ] **Step 1: Add a failing bootstrap reference**

Replace `D:\War3Projects\MyFirstWurstMap\wurst\Hello.wurst` with:

```wurst
package Hello
import TDInit

init
	tdStartGame()
```

- [ ] **Step 2: Run typecheck and verify it fails**

Run:

```powershell
grill typecheck
```

Expected: fail because package `TDInit` and `tdStartGame` do not exist yet.

- [ ] **Step 3: Implement the round controller**

Append the following to `D:\War3Projects\MyFirstWurstMap\wurst\TDGame.wurst`:

```wurst
import TDWaves
import TDSpawn
import TDTowers
import ClosureTimers

public function tdStartNextWave()
	if tdIsGameOver()
		return
	let nextWave = tdGetCurrentWave() + 1
	tdSetCurrentWave(nextWave)
	tdRefreshHud()
	DisplayTimedTextToPlayer(Player(TD_PLAYER_ID), 0, 0, 5.0, "Wave " + nextWave.toString() + " begins!")
	tdSpawnWave(nextWave)

public function tdHandleWaveFinished(int wave)
	if wave >= tdWaveCount()
		tdSetGameOver(true)
		DisplayTimedTextToPlayer(Player(TD_PLAYER_ID), 0, 0, 20.0, "Victory!")
		return
	tdGainGold(tdWaveReward(wave))
	tdRefreshHud()
	doAfter(TD_TIME_BETWEEN_WAVES) ->
		tdStartNextWave()

public function tdHandleDefeat()
	if tdGetLives() <= 0 and not tdIsGameOver()
		tdSetGameOver(true)
		DisplayTimedTextToPlayer(Player(TD_PLAYER_ID), 0, 0, 20.0, "Defeat!")
```

Update `tdHandleEnemyLeak` in the same file to call defeat logic:

```wurst
public function tdHandleEnemyLeak(unit enemy)
	if enemy != null and enemy.isAlive()
		tdLoseLife(1)
		enemy.kill()
		tdRefreshHud()
		tdHandleDefeat()
```

- [ ] **Step 4: Implement the map bootstrap package**

Create `D:\War3Projects\MyFirstWurstMap\wurst\TDInit.wurst`:

```wurst
package TDInit
import TDState
import TDGame
import TDTowers
import TDConfig
import TDWaves
import ClosureTimers

public function tdStartGame()
	tdResetState()
	tdCreatePads()
	tdSetupBuildDialog()
	tdSetupPadSelection()
	tdSetupDialogTrigger()
	tdStartLeakWatcher()
	tdRefreshHud()
	DisplayTimedTextToPlayer(Player(TD_PLAYER_ID), 0, 0, 8.0, "Build your first towers.")
	doAfter(3.0) ->
		tdStartNextWave()
```

- [ ] **Step 5: Add a temporary end-of-wave scheduler for the prototype**

Append the following to `D:\War3Projects\MyFirstWurstMap\wurst\TDSpawn.wurst`:

```wurst
import TDGame

public function tdSpawnWave(int wave)
	let count = tdWaveEnemyCount(wave)
	let interval = tdWaveSpawnInterval(wave)
	doPeriodicallyCounted(interval, count) cb ->
		tdCreateEnemy(wave)
	doAfter(interval * count + 12.0) ->
		tdHandleWaveFinished(wave)
```

This uses a fixed timeout on purpose so the first prototype is playable before adding more exact active-enemy tracking.

- [ ] **Step 6: Re-run static verification and build the map**

Run:

```powershell
grill typecheck
grill build ExampleMap.w3x
```

Expected: typecheck passes and the map build completes with `MyFirstWurstMap.w3x` output.

- [ ] **Step 7: Commit the playable loop**

Run:

```powershell
git add wurst/TDInit.wurst wurst/TDGame.wurst wurst/TDSpawn.wurst wurst/Hello.wurst
git commit -m "feat: wire single-player td gameplay loop"
```

### Task 7: Manual Gameplay Verification

**Files:**
- Modify after testing: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfig.wurst`
- Modify after testing: `D:\War3Projects\MyFirstWurstMap\wurst\TDWaves.wurst`
- Modify after testing: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`

- [ ] **Step 1: Run the prototype in Warcraft III**

Run:

```powershell
grill build ExampleMap.w3x
```

Then launch the built map through the Wurst VS Code run command or by opening the built map from:

```text
D:\War3_1.27a\Warcraft III Frozen Throne 1.27a publish\Maps\Test
```

- [ ] **Step 2: Verify the minimum gameplay checklist**

Check these behaviors manually:

```text
1. The map starts and prints TD startup text.
2. Five tower pads are present.
3. Selecting a pad opens the tower choice dialog.
4. Building a tower reduces gold.
5. Enemies spawn in five waves and move toward the end point.
6. Leaked enemies reduce lives.
7. Victory appears after wave 5 if lives remain.
8. Defeat appears if lives reach zero.
```

- [ ] **Step 3: Apply the smallest balance corrections needed**

Only tune the values inside `D:\War3Projects\MyFirstWurstMap\wurst\TDConfig.wurst` and `D:\War3Projects\MyFirstWurstMap\wurst\TDWaves.wurst`, for example:

```wurst
public constant int TD_STARTING_GOLD = 325
public constant int TD_ARROW_TOWER_COST = 75
public function tdWaveEnemyCount(int wave) returns int
	if wave == 1
		return 5
	if wave == 2
		return 7
```

- [ ] **Step 4: Re-run tests and rebuild after balance edits**

Run:

```powershell
grill test TDConfigTests
grill test TDStateTests
grill test TDWavesTests
grill test TDTowersTests
grill build ExampleMap.w3x
```

Expected: all tests pass and the map rebuilds successfully.

- [ ] **Step 5: Commit the verified prototype**

Run:

```powershell
git add wurst/TDConfig.wurst wurst/TDWaves.wurst wurst/TDTowers.wurst
git commit -m "feat: finalize playable td prototype"
```
