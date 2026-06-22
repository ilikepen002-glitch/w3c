---
name: war3-wurst-map-dev
description: Use when working in MyFirstWurstMap or other Warcraft III map projects that use WurstScript, Grill, WurstStdlib2, .wurst files, wurst.build, wurst_run.args, compiletime object generation, Warcraft III gameplay systems, tower defense logic, map tests, or build-and-deploy-test-map.bat.
---

# Warcraft III Wurst Map Development

## Overview

Use this skill to adapt general Warcraft III map-development judgment to this Wurst/Grill project. Prefer the project workflow in `AGENTS.md`; use this skill as a compact decision guide for gameplay changes, object generation, testing, and map-build validation.

## First Read

Before changing code, read or re-check these anchors:

- `AGENTS.md` for project-specific collaboration rules and commands.
- `wurst.build` for `scriptMode`, `wc3Patch`, map metadata, players, forces, and dependencies.
- Nearby `.wurst` files in the same domain before inventing a new pattern.
- Matching tests in `tests/wurst/` before changing gameplay logic.

Do not apply TypeScript/Lua map-template assumptions here. This project uses WurstScript, Grill, WurstStdlib2, `scriptMode: JASS`, and Warcraft III patch `v1.28`.

## Domain Routing

| Need | Prefer |
| --- | --- |
| Map constants, routes, spawn points, tower coordinates | `wurst/TDConfig.wurst` |
| Runtime state such as lives, gold, waves, route state | `wurst/TDState.wurst` |
| Enemy creation and route spawning | `wurst/TDSpawn.wurst` |
| Wave progression, leaks, HUD, win/loss flow | `wurst/TDGame.wurst` |
| Startup orchestration and system wiring | `wurst/TDInit.wurst` |
| Wave definitions and reward cadence | `wurst/TDWaves.wurst` |
| Stable public tower facade | `wurst/TDTowers.wurst` |
| Tower catalog IDs, families, levels, upgrade chains | `wurst/towers/TDTowerCatalogData.wurst` |
| Tower balance, icons, models, button positions | `wurst/towers/TDTowerBalanceData.wurst` |
| Tower runtime behavior and events | `wurst/towers/TDTowerRuntime.wurst` |
| Tower object editor generation | `wurst/towers/TDTowerObjectGen.wurst` |
| Item object generation, inventory, drops, crafting | `wurst/items/` |
| Tests | `tests/wurst/*Tests.wurst` |

If a change spans multiple domains, split by responsibility: config, state, wave/spawn, tower/item data, runtime behavior, object generation, tests.

## Warcraft III Boundary Decisions

Choose the layer before coding:

- Use Wurst for rules, state transitions, combat behavior, triggers, deterministic helper logic, compiletime object generation, and tests.
- Use `wurst.build` or scripts for build metadata, dependencies, test staging, packaging, and deployment.
- Use World Editor for terrain, decorations, visual placement, regions, pathing blockers, camera/layout tweaks, and manual asset inspection.

When a request crosses code and editor work, complete the code side and report the remaining World Editor steps separately.

## Implementation Rules

- Modify source files, not generated files. Treat `_build/`, `_build/dependencies/`, and generated `war3map.j` as outputs.
- Keep package boundaries narrow. Add logic near the closest existing domain; preserve stable facades such as `TDTowers.wurst` unless the task is to change their API.
- For object editor data, prefer existing compiletime wrapper and ID allocation patterns. Avoid hand-writing batches of unrelated rawcodes.
- For initialization, inspect import direction and package init order before using `initlater`; use `initlater` only for a real dependency cycle.
- For JASS mode, remember op-limit constraints. Add `execute()` or timer chunking only when there is a concrete long-running-thread reason.
- For handles, classes, stored closures, timers, groups, and effects, decide who owns cleanup. `new` objects commonly need `destroy`.
- Use Wurst style: package per file, indentation as syntax, `let` by default, `var` only when mutation is needed, and Wurst declarations instead of Jass-style `takes` / `returns nothing`.

## Testing and Validation

Use the smallest validation that proves the change:

| Change | Validation |
| --- | --- |
| `.wurst` gameplay logic | `tools\Run-WurstChecks.bat` |
| Tests only | `tools\Run-WurstChecks.bat`, then targeted `tools\Run-WurstChecks.bat test PackageOrTestName` when useful |
| Compiletime object generation, unit/ability/item IDs, build menu, upgrades, icons, models | `tools\Run-WurstChecks.bat` and `build-and-deploy-test-map.bat` |
| `wurst.build`, scripts, packaging, deployment | `build-and-deploy-test-map.bat` |
| Core playable flow such as spawn, leaks, tower behavior, inventory, crafting | `tools\Run-WurstChecks.bat`; use `build-and-deploy-test-map.bat` when actual map behavior may be affected |

For bug fixes and behavior changes, add or update a narrow test in `tests/wurst/` when the behavior is testable without the World Editor.

## Common Mistakes

- Editing `_build/` or generated `war3map.j` instead of source.
- Copying TypeScript/Lua, YDWE/KKWE, or w3x2lni workflow assumptions into a Wurst/Grill project.
- Adding raw object IDs without checking existing catalog and object-generation patterns.
- Leaving tests in `wurst/_tests/`; that directory is staging, not source.
- Treating `array.length` as dynamic element count.
- Capturing locals in a lambda that will be used as `code`.
- Using `initlater` as a shortcut before understanding package initialization.
- Running ad hoc build commands instead of the project scripts.

## Completion Checklist

Before reporting completion:

- State which source/domain files changed.
- State which tests or build scripts ran.
- State what was not verified and why.
- If the change needs World Editor follow-up, list the exact manual steps.
