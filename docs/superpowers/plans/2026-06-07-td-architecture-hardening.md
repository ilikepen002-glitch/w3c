# TD Architecture Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the oversized tower package into stable runtime and data boundaries, and move tests into a dedicated source area that does not get packaged into the shipped map.

**Architecture:** Keep all production Wurst packages under `wurst/`, but split them by responsibility: shared tower data, compiletime object generation, and runtime gameplay hooks. Keep test files outside `wurst/` as canonical source, and stage them into a temporary generated folder only for `grill test` / `grill typecheck`, so production builds stay clean despite Grill parsing every `.wurst` file under `wurst/`.

**Tech Stack:** WurstScript, Grill CLI, PowerShell/BAT helper scripts, compiletime object editing

---

### Task 1: Lock Current Tower Behavior With Tests

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\tests\wurst\TDTowerArchitectureTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowersTests.wurst`

- [ ] Add tests that assert key public tower APIs remain stable across the refactor.
- [ ] Run the targeted tests and verify the new assertions fail before implementation.

### Task 2: Split Tower Code By Responsibility

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerData.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerObjectGen.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\wurst\towers\TDTowerRuntime.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`

- [ ] Move pure tower stats, labels, rawcodes, and tooltip helpers into a shared data package.
- [ ] Move compiletime ability/unit/building generation into a dedicated object-generation package.
- [ ] Move farmer, build-plot, upgrade, and combat event handlers into a dedicated runtime package.
- [ ] Keep `TDTowers` as the stable public facade so current imports do not break.

### Task 3: Separate Canonical Test Sources From Production Sources

**Files:**
- Create: `D:\War3Projects\MyFirstWurstMap\tests\wurst\*.wurst`
- Create: `D:\War3Projects\MyFirstWurstMap\tools\Sync-WurstTests.ps1`
- Create: `D:\War3Projects\MyFirstWurstMap\tools\Run-WurstChecks.bat`
- Modify: `D:\War3Projects\MyFirstWurstMap\build-and-deploy-test-map.bat`

- [ ] Move test packages into `tests/wurst/` so they are not treated as production source-of-truth.
- [ ] Add a sync script that mirrors test sources into a generated `wurst\_tests\` directory only during checks.
- [ ] Ensure the build script removes generated test sources before `grill build`.

### Task 4: Verify The New Workflow

**Files:**
- Verify: `D:\War3Projects\MyFirstWurstMap\wurst\**\*.wurst`
- Verify: `D:\War3Projects\MyFirstWurstMap\tests\wurst\*.wurst`
- Verify: `D:\War3Projects\MyFirstWurstMap\tools\*.ps1`
- Verify: `D:\War3Projects\MyFirstWurstMap\build-and-deploy-test-map.bat`

- [ ] Run quiet typecheck through the staged test workflow.
- [ ] Run quiet tests through the staged test workflow.
- [ ] Run the required production build script and verify the map builds without staged tests present.
