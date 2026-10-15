# Combined remaining fixes — 2026-10-15

Baseline: f0c5f45dc29790506886b24c973050e16291c280.
Candidate map SHA256: 14fa7cd13acce82bf71f95c64de0c152aad0fad2102a83551a3dcd34596f8aae.

## Included
- Inventory crafting delivers and verifies output before consuming three originals, with bounded recovery when the bag is full.
- The 21 original decorative critters receive native Ghost Visible, retaining terrain pathing and neutral ownership.
- Hero-specific spirit enhancements gain bounded ready/hit effects; storm completion uses whirlwind and four blades. Generic possessed-tower attack visuals remain disabled.

## Validation
- Official isolated Linux full Wurst checks and build PASS. Locked compiler/JDK/stdlib unchanged.
- Final packed inventory matrix: 24/24 methods PASS, no failures/errors/skips. Additional source/native-model checks passed as documented in review.
- Baseline cannot execute this new inventory matrix: its fixture lacks new recovery functions. This is NOT 24 baseline behavior failures or proof of 24 repaired differences.
- Same final verifier selection used on both maps; comparison reports no new failures, not a full-suite claim.
- Packed hero damage/visual budget/cancellation/native-null/expiry checks PASS. An initial verifier stub incorrectly represented JASS null as 0; corrected to None without changing production.
- MPQ: 433 members, no additions/removals; only JASS, A119 description and build-time metadata differ. Other 430 members unchanged, including terrain and all models/textures.
- Shared ground-command objects and inventory native constants PASS on both maps.
- No Warcraft 1.27a runtime test. No actual FPS or visual-quality guarantee from offline checks.

## Remaining
- Manual drops displaced to high ground: awaiting user -dropdiag output; not claimed fixed.
- Final two Boss model stretching: structural checks found no verified cause; production models unchanged.
- Native building placement with Ghost Visible requires user playtest.
- Inventory DROP callback before first observation can hide a pure unowned-item position change; documented review boundary remains.
