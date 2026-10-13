# Player-facing tooltip rewrite — final integrated validation

## Scope

Based on published `bb767bc52453e45cea418c00deda64639b8580d7`, preserving the
preceding spirit-release, ground-upgrade, leak-life and semantic-icon changes.
Only player-facing strings, pure display formatting and matching tests change.
No gameplay value, ability attachment, rawcode, name, icon or asset is changed.

Effect first, then numbers/trigger, then costs and irreversible restrictions.
Tower descriptions show the true attack range and catalog base, e.g.
`攻击：186至197（基础185）`, without exposing implementation terminology.

## Important corrections

- All 61 poison/control levels now show their actual damage, move/attack slow,
  and normal/hero durations. Removed the old fixed-text overwrite.
- Bash probabilities/additive damage/durations and all 41 Bloodlust/Bladestorm
  cooldown levels match the actual fields. Passive function/display text agrees.
- Pet descriptions cover all 16 skills × 4 qualities and locked copies. Integer
  percentages now round for display instead of turning 20% into 19%; underlying
  powers are unchanged. Fractional tower percentages retain precise formatting.
- Pet triggered damage says “本次普攻伤害”; no unproven pre-armor, magic-damage or
  armor-bypass claim. Charge uses catalog base attack. Corpse poison remains
  36 × quality power, 180 radius, 3 seconds, up to 12 enemies per tick.
- Inclusive thresholds are 25% for corpse explosion and 30% for pet execution.
- Equipment states third identical copy's 50% effect; 500 range, 40% combined
  tower cooldown and 60% gear-control caps. Armor sums then rounds; different
  towers' armor/poison debuffs retain the strongest value.
- Backpack crafting retains 2-item 65% risk and 3-item guaranteed crafting.
  Ground crafting uses own-lane same-quality triples, one quality step per cast,
  unchanged 1–2 leftovers, and outputs in the corresponding quality pile.
- Cultivation distinguishes paid reroll retention, empty-slot opening, resonance
  locks and permanent release. Release keeps one reroll stone plus a separate
  2% slot-stone chance, with recall required before releasing an active spirit.
- Startup guidance states ordinary/elite-or-guard/boss leak costs of 1/2/3.

## Deliberate limits

Bash Hbh2 remains 1.45, but this old native field's live damage semantics have not
been established, so no new 1.45x claim is introduced. Hero durations remain
because this map uses hero parents for elite/boss enemies. At this commit the
existing three-spirit deployment cap, master-ball system and damage-statistics
entry remain implemented and accurately described; later behavior requests are
not mixed into this text-only change.

## Final evidence

GPT-6.1 Sol implemented the changes; an independent GPT-6.1 Sol performed read-only
review. Final independent review: PASS, no blocking issues.
Risk tier: low, existing text fields and pure presentation templates.

- Fixed Linux toolchain: typecheck PASS, 310/310 Wurst tests PASS.
- Python suite: 201 tests PASS, including deliberately bad tooltip, control,
  cooldown, threshold, rounding, damage-basis, missing-risk and attack-range cases.
- Actual packed tooltip matrix: 1523 instances PASS, including all 35 tower forms,
  28 equipment entries, pet skill qualities and relevant dynamic ability levels.
- Ten existing/ground artifact verifiers PASS: bladestorm, equipment, evolution,
  ground commands, actual-JASS ground batches, pet UI, slows, placement, sale,
  and tower/UI/ground consistency.
- Independent comparison with the exact baseline: 587 abilities, 184 units,
  29 items retain identical IDs. Only 974 ability descriptions, 35 tower
  descriptions and 29 item descriptions change. All other object fields match.
- All 126 packed BLP/TGA/model/audio resources and W3E/WPM/IMP remain byte-identical
  to the published icon baseline. No icon/asset regression is hidden by text tests.
- `git diff --check` PASS.

Root `ExampleMap.w3x`: `深渊守望 20261011-2345-UTC+8`.
SHA256: `d0e5a38101a136cb023ab2fc490da4c85906136565d8f1042040abfe26886f9c`.
Git blob: `0d6e19068644ae5ba70b84ac923c93d716166ecc`.

No Warcraft III launch, Windows deployment, native rendering, gameplay or
performance observation is claimed. Offline checks do not establish native
engine behavior beyond the explicitly inspected fields and compiled logic.
