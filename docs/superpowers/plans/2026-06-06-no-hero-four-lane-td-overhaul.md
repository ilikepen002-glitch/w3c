# No-Hero Four-Lane TD Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current prototype into a playable no-hero Warcraft III TD with four lanes that merge into one center leak point, 100 starting gold, and five themed tower families with full upgrade chains.

**Architecture:** Keep all gameplay rules in Wurst. Rework lane geometry and balance in `TDConfig`/`TDWaves`, keep mutable match state in `TDState`, drive build and upgrade interactions from `TDTowers`, and enforce lane movement and leak handling from `TDSpawn` and `TDGame`. Use compile-time object editing for both towers and creeps so the resulting map does not rely on manual object editor work.

**Tech Stack:** WurstScript, compile-time object editing, Warcraft III `pre1.29`, `C:\Users\huawei\.wurst\grill.cmd`

---

### Task 1: Lock The New Rule Set With Tests

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfigTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDStateTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowersTests.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDWavesTests.wurst`

- [ ] Assert that starting gold is exactly `100` and tower choice count is exactly `5`.
- [ ] Assert that all four lanes share the same exit point and still expose multiple waypoints.
- [ ] Assert that the tower catalog supports five-level upgrade chains for archer, orc, human, dryad, and ghoul lines.
- [ ] Assert that the wave table now represents a longer playable session than the current six-wave prototype.
- [ ] Run `C:\Users\huawei\.wurst\grill.cmd test` and confirm the new expectations fail before production code changes.

### Task 2: Rebuild Shared Config And Economy

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDConfig.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDState.wurst`

- [ ] Set starting gold to `100`, keep four active defenders, and raise the tower-choice constants and helpers to cover five tower families.
- [ ] Redefine the four lane routes so they enter from four directions and merge into one center leak point.
- [ ] Tune build-plot positions so each route still has practical tower coverage on both sides.
- [ ] Keep the existing shared-score and per-lane resource model intact unless the new rules require a new helper.

### Task 3: Replace The Tower Catalog

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDTowers.wurst`

- [ ] Generate five custom tower families with compile-time object editing.
- [ ] Implement `弓箭手 -> 白虎` as a bouncing ranged line with a stronger final form.
- [ ] Implement `兽人战士 -> 剑圣` as a critical-strike melee line whose final form gains a bladestorm-like passive splash effect.
- [ ] Implement a useful `人族步兵` line as a control/support tower that can stun and later buff nearby towers.
- [ ] Implement `小鹿` as a poison/slow line and `食尸鬼` as a frenzy-style high-attack-speed line.
- [ ] Generalize runtime build and upgrade logic so every family upgrades through five stages from the same selection flow.

### Task 4: Rebuild Creeps And Wave Progression

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDWaves.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDSpawn.wurst`

- [ ] Generate custom creep templates that cannot fight back, use low collision, and are safe for queued lane movement.
- [ ] Expand the wave table to a more playable progression with enough reward pacing to support multi-family upgrading from a `100`-gold start.
- [ ] Keep wave spawns independent per lane while making every lane march toward the shared center exit.

### Task 5: Finish Match Flow And Verification

**Files:**
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDGame.wurst`
- Modify: `D:\War3Projects\MyFirstWurstMap\wurst\TDInit.wurst`
- Verify: `D:\War3Projects\MyFirstWurstMap\wurst.build`

- [ ] Refresh onboarding text so players understand the no-hero, farmer-build, four-lane-merge rules immediately.
- [ ] Make sure leak detection, wave-finished handling, and HUD text still make sense after the shared-center route change.
- [ ] Run `C:\Users\huawei\.wurst\grill.cmd test` until all tests pass.
- [ ] Run `C:\Users\huawei\.wurst\grill.cmd build` and verify the rebuilt map succeeds.
