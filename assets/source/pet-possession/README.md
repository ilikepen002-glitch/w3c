# Possession link

Self-authored ice-white, unshaded additive mesh stars. No downloaded artwork,
new particle emitters or timers. Rebuild with:

    python3 tools/BuildPetPossessionStars.py
    MDX_PARSER_MODULES=/path/to/pinned/node_modules node tools/BuildPetPossessionStars.cjs

The MDX800 uses one looping Stand, twelve independently bobbing/scaling bones,
96 vertices and 48 triangles. A single effect is mounted to the host's universal
origin rather than relying on optional native overhead attachments. It spans
roughly height 75–340 before host scale, covering all 35 catalog placement
profiles. Source and offline bounds checks do not establish native render,
occlusion or performance. `VerifyPetPresence.py --map final.w3x` verifies packed
resources alongside the source contract.

Only attached spirit object scales change. Fourteen authored rigs target a
230-unit longest Float envelope; the replacement phoenix keeps its prior 1.04
scale because its Float envelope is already larger. The existing float/jump/
sway/sleep/cast animations remain unchanged. Pet origin placement adds 110 units
above the estimated host head profile, versus the former 24.

The effect belongs to TDPet; combat invalidation, recall/rebinding, and destruction
release it. Display initialization recreates it only when absent. No attack,
damage, capture, collection, wild-scale, or additional census changes.
