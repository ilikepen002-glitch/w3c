# TD Equipment Drop Design Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first playable tower equipment system with shared ground drops, worker pickup/crafting, three-slot tower inventories, and lane-bound drop budgeting.

**Architecture:** Keep equipment responsibilities split into focused Wurst packages: item definitions/object generation, drop logic, tower inventory/runtime state, and crafting rules. Reuse existing lane metadata and tower facades so `TDGame` and `TDSpawn` only call thin equipment APIs instead of absorbing item logic.

**Tech Stack:** WurstScript, Grill CLI, compiletime object editing, Warcraft III item inventory mechanics

---

### Task 1: Lock The New Rules With Tests

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\tests\wurst\TDItemsTests.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\tests\wurst\TDDropsTests.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\tests\wurst\TDCraftingTests.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\tests\wurst\TDInventoryTests.wurst`

- [ ] Add failing tests for item catalog structure, quality progression, lane-budget tables, crafting outcomes, and tower three-slot aggregation rules.
- [ ] Run targeted checks and verify the new tests fail for the expected missing APIs.

### Task 2: Add Equipment Data And Compiletime Object Generation

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDItems.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\items\TDItemData.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\items\TDItemObjectGen.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDInit.wurst`

- [ ] Define qualities, effect kinds, rawcodes, names, tooltips, and quality colors for the launch equipment pool.
- [ ] Generate inventory/crafting abilities, passive items, and farmer/tower inventory object data at compiletime.
- [ ] Expose a stable `TDItems` facade for other gameplay systems.

### Task 3: Implement Drop Budgets And Crafting Rules

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDDrops.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\items\TDDropLogic.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDCrafting.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\items\TDCraftingLogic.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDState.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDGame.wurst`

- [ ] Track per-lane-per-wave drop budget state in `TDState`.
- [ ] Implement normal/elite/boss drop routing that always uses `originLaneId`.
- [ ] Implement `2 合 1` and `3 合 1` crafting rule selection and random upgrade resolution.

### Task 4: Implement Tower Inventory Runtime Integration

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\TDInventory.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\items\TDInventoryRuntime.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerRuntime.wurst`

- [ ] Add tower/farmer inventory runtime helpers and crafting button handling.
- [ ] Recompute per-tower equipment summaries from the current three slots.
- [ ] Hook item pickup/transfer/drop/use events without collapsing the tower runtime facade.

### Task 5: Verify Checks And Build Output

**Files:**
- Verify: `D:\War3Projects\MyFirstWurstMap\wurst\**\*.wurst`
- Verify: `D:\War3Projects\MyFirstWurstMap\tests\wurst\*.wurst`
- Verify: `D:\War3Projects\MyFirstWurstMap\build-and-deploy-test-map.bat`

- [ ] Run `tools\Run-WurstChecks.bat`.
- [ ] Run the required build script `build-and-deploy-test-map.bat`.
- [ ] Fix any compiletime/object generation regressions before closing the task.
