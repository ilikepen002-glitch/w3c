# Single-Player TD Design

**Date:** 2026-06-05

## Goal

Build a first playable Warcraft III tower defense prototype in WurstScript using only built-in Warcraft III units/buildings. The prototype should support one player, one enemy lane, fixed tower pads, five waves, gold income, base life, and clear win/lose conditions.

## Scope

### In scope

- Single-player only
- One lane from spawn to base
- Five waves
- Fixed tower pads
- Three tower choices using built-in Warcraft III towers
- No tower upgrades
- Enemy units use built-in Warcraft III units
- Base loses life when enemies reach the end
- Gold is spent to build towers
- Round flow: start, spawn, inter-wave pause, win, lose

### Out of scope

- Multiplayer
- Custom models, icons, sounds, or UI art
- Tower upgrades
- Save/load
- Hero control
- Random wave generation
- Advanced path blocking logic
- Polished terrain/art pass

## Recommended Implementation Approach

Use the existing `ExampleMap.w3x` as a temporary prototype map and move the game rules into Wurst code. Keep the map visually simple for now and prioritize a reliable gameplay loop. This gives the fastest route to a working prototype while keeping the rules centralized in code.

## Gameplay Design

### Core loop

1. Game starts with base life and starting gold.
2. The player builds on fixed tower pads.
3. A wave of enemy units spawns and walks along one fixed route.
4. Towers attack automatically.
5. Enemies that reach the base reduce base life.
6. Surviving the wave grants a short pause before the next wave.
7. Clearing wave 5 wins the game. Losing all base life ends the game.

### Tower model

The first version should support exactly three tower types:

- Arrow tower: cheap, balanced single-target tower
- Cannon tower: more expensive, splash-focused tower
- Long-range single-target tower: used as the third choice if a slow tower is inconvenient on patch `pre1.29`

The player will not place towers freely on terrain. Instead, each tower pad is a dedicated build point that can transform into one of the three tower choices.

### Enemy model

Enemy waves should use built-in melee/ranged units with predictable stats. Early waves should be weak foot units; later waves should add stronger or denser groups. The first prototype should emphasize readable pacing over perfect balance.

## Technical Design

### Project setup

The project must be normalized to the actual target runtime:

- `scriptMode: JASS`
- `wc3Patch: pre1.29`
- Warcraft III path points to the local `1.27a` install
- Wurst standard library dependency must resolve locally if Git-based install is unreliable

### Code structure

Create focused Wurst packages with clear responsibilities:

- `TDInit`
  - entry point
  - startup sequencing
- `TDConfig`
  - constants for life, gold, wave timing, tower costs, pad positions, spawn/end points
- `TDState`
  - mutable game state such as current wave, remaining lives, gold, active enemies, game-over flag
- `TDWaves`
  - wave definitions and spawn schedule
- `TDSpawn`
  - creates enemy units and sends them along the lane
- `TDTowers`
  - handles tower pads, build choices, costs, and tower creation
- `TDGame`
  - win/lose rules, HUD text/messages, wave progression

This keeps map rules separate from coordinates/configuration and makes later balancing easier.

### Map assumptions

The prototype map can stay minimal, but the code will assume:

- one spawn point
- one base/end point
- a fixed ordered route, represented either by rects/regions or by a short list of coordinates
- several predeclared tower pad locations

To move fast, the first implementation can use hard-coded coordinates from the prototype map instead of object editor markers.

### Tower pad interaction

The simplest reliable first version is:

- each tower pad starts as a neutral placeholder unit
- selecting/activating a build action replaces that pad with the chosen tower if the player has enough gold
- once built, the pad is consumed

If ability-based build menus are awkward on the first pass, a fallback is to use one worker unit restricted to tower pads and let Wurst validate allowed build positions.

The preferred first implementation is still fixed-pad replacement because it better matches the agreed design and avoids pathing issues.

### Wave progression

Waves should be defined in code as small data records:

- unit type
- number of enemies
- spawn interval
- reward on clear

The first version should use five explicit wave definitions rather than procedural scaling.

### Economy and life

- Player starts with enough gold to build 1-2 towers.
- Building a tower subtracts gold immediately.
- Clearing a wave grants bonus gold.
- Each escaped enemy removes one life.
- Base life reaching zero triggers defeat immediately.

## Balance Targets For Prototype

These are not final balance values, only starting targets:

- Starting life: 20
- Starting gold: 250 to 350
- Arrow tower cost: low
- Cannon tower cost: medium
- Third tower cost: medium/high
- Waves 1-2: low pressure
- Waves 3-4: require a reasonable build choice
- Wave 5: should threaten defeat if the player underbuilds

Exact numbers can be tuned during implementation once the loop is playable.

## Error Handling And Constraints

- If dependency install from GitHub fails, use the manually downloaded local stdlib directory.
- If third tower behavior is unstable on `1.27a`, swap it to another original direct-damage tower instead of blocking progress.
- If pad interaction via abilities proves too slow to wire up, use a simpler placeholder interaction for the first working version.
- Avoid custom assets and advanced triggers until the first playable loop passes.

## Testing Strategy

Testing should happen at two levels:

### Static verification

- project dependency resolution works
- Wurst project typechecks cleanly
- build pipeline can output a map

### Gameplay verification

- game starts without script crash
- waves spawn in order
- enemies move toward the base
- escaped enemies reduce life
- towers can be built only on pads
- gold is consumed correctly
- wave 5 victory works
- zero life defeat works

## Success Criteria

The design is successful when:

- the map launches from the Wurst project
- the player can build towers on fixed pads
- five waves play from start to finish
- the player can either win or lose through normal gameplay
- all towers and enemies use built-in Warcraft III content

## Current Known Setup Issues

- The project is not currently a Git repository, so the spec cannot be committed yet.
- The Wurst stdlib was downloaded manually and still needs to be wired into the project in the final usable form.
- The current `wurst.build` content must be corrected to `pre1.29` instead of `v2.0`.
