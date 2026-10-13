# Native inventory distance and decorative ownership

Inventory pickup, ground drop and give-to-unit now share a finite 1200 distance.
`imports/war3mapMisc.txt` is a root MPQ import with exactly `[Misc]` plus
`PickupItemRange`, `DropItemRange`, and `GiveItemRange`. The source map has no
existing `war3mapMisc.txt`, so no map-specific defaults are discarded.

Field/path evidence: Cheeder's original 2009 tutorial explicitly documents the
custom root import path and labels these three inventory gameplay constants:
https://www.hiveworkshop.com/threads/changing-gameplay-constants-for-roc-maps.149065/
This is legacy pre-1.27a editor evidence, not a verified 1.27a installation dump.
The locked stdlib's `AbilityDefinitionInventory` configures `inv1`–`inv5`; changing
its generic cast range does not establish pickup/drop semantics.

These constants are map-global. They change distance for units that already have
inventory, not who can own or carry items. No unit gains an inventory ability.
Farmer six slots, tower three slots, admission/duplicate rejection, item owner,
ground crafting and existing native pickup/drop event handlers are unchanged.
No order interception, teleporting items or substitute transfer system is added.
Run `python3 tools/VerifyInventoryRangeArtifact.py candidate.w3x` against the
actual final build to check root placement, exact bytes and no prefixed copy.
Engine behavior, movement beyond 1200, cliffs, give/drop/pickup event ordering
and Warcraft 1.27a user interaction remain untested without gameplay.

The source map creates exactly 21 P0 decorative units: 4 `nech`, 11 `nshe`,
2 `nfro`, 4 `npig`. A map-lifetime startup guard enumerates P0 once, transfers
only those four types to neutral passive, and destroys the temporary group.
This runs before creating farmers and registering gameplay. It does not run on
match reset and never scans periodically. Other owners and all non-whitelisted
rawcodes are unchanged; no map source/pathing closure is rewritten.

Source replay tests cover the whitelist across all 16 owners, one-time setup,
empty-group destruction, original map counts and startup placement. They are
not Wurst compilation or engine execution evidence. The general startup replay
stubs this independent decoration step explicitly; the focused source replay
executes its real body with bounded native group/ownership stubs.
