---
name: war3-wurst-map-dev
description: Develop, diagnose, or review Warcraft III Wurst maps, including gameplay, object generation, image asset integration, and offline build validation. Run in-game playtests only when the user explicitly requests them.
---

# Warcraft III Wurst Map Development

Use this guide for Wurst map work. Discover project-specific paths, commands, collaboration gates, and test conventions from `AGENTS.md`, `wurst.build`, nearby source, and existing tests; do not import another map's layout or toolchain assumptions.

## Route by impact and reuse context

Use the project's [AGENTS.md](../../../AGENTS.md) as the sole source for risk tiers, required Astra/Sol stages, and the validation matrix. Classify the changed boundary before implementation; an unclear cause or ownership needs focused investigation before classification. Do not impose a second universal review gate from this skill.

Reuse confirmed context while the relevant source, dependencies, configuration, and environment remain unchanged. Read only the affected packages, nearby examples, tests, and references needed for the current decision. Delegate with the goal, relevant files, differences, risks, and validation evidence rather than full conversation history; follow AGENTS.md for model selection and minimal context.

## Establish the problem and boundary

Separate observed behavior, reproduction conditions, and hypotheses before implementing a proposed fix. Locate the owner of the rule or state and the nearest working pattern. Read `scriptMode`, `wc3Patch`, dependencies, and map metadata from project configuration before making runtime or compatibility decisions.

- Wurst owns rules, state transitions, triggers, combat behavior, testable helpers, and compiletime object generation.
- Configuration and build scripts own dependencies, test staging, packaging, map metadata, and deployment.
- World Editor owns terrain, decoration, visual placement, pathing/layout adjustment, and manual asset inspection where those are better handled visually.

Keep shared rules/data, runtime behavior, compiletime assets, and tests separate. Preserve existing public facades; change dependencies only when the task needs it. For mixed code/editor work, finish the code side and identify remaining editor steps.

## Default execution scope

For this project, when the user's initial task does not request in-game validation, complete development and only the automated checks, build/deployment, and offline artifact inspection required by the project's validation matrix, without launching or controlling Warcraft III. Gameplay, UI, performance, or visual changes do not implicitly authorize a playtest. Do not routinely ask whether to add one or block delivery merely because runtime behavior remains unobserved; report that boundary briefly.

A later explicit request to play, reproduce in game, or verify live behavior changes this scope. Only then use `war3-map-playtest` for the requested scenario. Build/deployment does not mean starting the game. Documentation or skill-only edits need skill/document validation, not a map rebuild or playtest.

## Generated art and imported assets

When creating or integrating bitmap icons, textures, or model-attachment art, read [image asset integration](references/image-assets.md). Use the available `imagegen` skill for requested AI artwork; preserve source images and prompts in the project, convert them reproducibly, and verify the exact references in the built map. Image generation produces raster artwork, not a ready-to-use animated Warcraft model. Do not load this workflow for unrelated gameplay edits.

## Warcraft and Wurst decisions

- Edit source, not generated scripts, dependency copies, or build outputs. Discover their locations from this project.
- For units, abilities, items, and upgrades, reuse compiletime wrappers and existing rawcode allocation. Check uniqueness, base objects, upgrade chains, ability attachment, button positions, and build menus together.
- Inspect import direction and initialization order before changing `init` or `initlater`. Do not use delayed initialization to conceal unclear state ownership or a dependency that can be removed.
- Identify cleanup ownership for handles, classes, stored closures, timers, groups, and effects. Check cancellation/death/removal paths as well as normal completion; tuples are values, while allocated objects commonly require `destroy`.
- Confirm the script mode before thread changes: JASS has an op limit; `execute()` can reset its counter, and measured long computations may need tick splitting. Lua does not have the same practical op-limit pressure; `execute()` is not an equivalent reset remedy.
- A count of unfinished asynchronous jobs is not recursion depth. Diagnose call-stack growth separately from pending work, queue limits, cancellation, and completion accounting.
- Base performance changes on an identified hot path, lifecycle defect, or relevant measurements. Without a requested playtest, use source analysis and offline tests; distinguish reduced work from measured FPS improvement. Prefer appropriate WurstStdlib helpers and `T:` containers where instance volume justifies them; do not add layers or scheduling merely from speculation.
- Follow adjacent valid Wurst examples when syntax or APIs are uncertain. Watch indentation, `array.length` versus live element count, and the restriction that `code` lambdas cannot capture local variables.

## Validation and conclusions

Use project-mandated checks and build/deploy entrypoints, with their required ordering and collaboration gates. Add a narrow reproduction test for a testable bug; keep test sources in the project's designated source location rather than generated staging.

Select validation by the changed boundary: logic needs relevant checks/tests; object generation and packaging need a real map build; imported assets need exact packaged-reference and format checks. In-game validation is a separate, explicitly requested activity, even for initialization or core gameplay changes. A successful typecheck cannot prove object output or live behavior. Narrow a failed check using its package, file, or test name before repeating broad runs.

Reuse successful checks for the same unchanged source, dependency, configuration, and environment state. Revalidate affected paths after later changes or failures; do not repeat checks merely at each handoff. Related small edits can share one validation batch. Run checks and map builds serially because they share staging and build outputs.

Report separately what is demonstrated by source review, automated checks, compiled objects/deployment, and observed gameplay. Include changed source areas, commands/results, unverified editor or runtime steps, and remaining risks. Treat a plausible hypothesis as unproven until the relevant path is verified.
