# Four Player TD Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the prototype into a four-lane cooperative TD where each player defends an independent route, scores contribute to a shared team score, arrow towers upgrade to level 5, and farmers must move to side plots to build or upgrade towers.

**Architecture:** Keep the game rules in Wurst and avoid terrain-heavy edits by defining lane geometry in code. Convert the current global single-player state into per-player lane state, spawn creeps with lane metadata, and drive build/upgrade interactions through player-owned farmers plus selection dialogs.

**Tech Stack:** WurstScript, compile-time object editing, Warcraft III pre1.29 map build via `C:\Users\huawei\.wurst\grill.cmd`

---

### Task 1: Lock The New Rules With Tests

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfigTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDStateTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDWavesTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowersTests.wurst`

- [ ] Add failing tests for four active players, multi-waypoint lanes, shared score, independent player economies, longer wave pacing, and the five-level arrow tower upgrade chain.
- [ ] Run `C:\Users\huawei\.wurst\grill.cmd test` and verify the build fails for the expected missing multiplayer APIs.

### Task 2: Build Lane Data And Per-Player State

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfig.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDState.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDWaves.wurst`

- [ ] Add four-lane geometry helpers, build-plot positions, farmer spawn points, and upgrade cost helpers.
- [ ] Replace single global gold/lives/wave values with per-player arrays plus a shared team score.
- [ ] Extend the wave table for a longer cooperative session with kill-gold and score values.

### Task 3: Rebuild The Tower Layer

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`

- [ ] Generate five custom arrow tower levels at compile time.
- [ ] Spawn per-player farmers and build plots along both sides of each route.
- [ ] Add build and upgrade dialogs that require the owning farmer to be near the selected plot or tower.

### Task 4: Rework Spawning And Game Flow

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDSpawn.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDGame.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDInit.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\Hello.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst.build`

- [ ] Tag every spawned enemy with lane and wave metadata, move them through waypoint routes, and resolve waves independently per player.
- [ ] Award gold and score on kills, deduct lives on leaks, and end the match when all lanes are either finished or defeated.
- [ ] Refresh the HUD for all four users and update the map metadata to expose four cooperative player slots.

### Task 5: Verify The Whole Map

**Files:**
- Verify: `D:\War3Projects\MyFirstWurstMap\wurst\*.wurst`
- Verify: `D:\War3Projects\MyFirstWurstMap\wurst.build`

- [ ] Run `C:\Users\huawei\.wurst\grill.cmd test` until all Wurst tests pass.
- [ ] Run `C:\Users\huawei\.wurst\grill.cmd build` and verify the map rebuild succeeds.
