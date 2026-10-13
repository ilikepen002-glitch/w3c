# Phase 2 elemental spirit visual contract

These are actual native effect emissions in `TDPetActiveVisuals`, `Direct` and
`Periodic`, not descriptions substituted for implementation. Art is optional:
all targets/hits/CD remain independent. One existing 0.05 scheduler, <=8 retained
handles per cast, <=128 globally, explicit context cancellation/destruction.
No unit path, position, order, pause or later-engine effect setter is used.
Native resource paths are checked against the locked stdlib Abilities catalogue
by normalized model name/suffix (.mdl/.mdx aliases), not literal suffix equality.
Warcraft III 1.27a appearance/performance acceptance remains a separate gate.

| ID / skill | Geometry and actual stage feedback |
|---|---|
| 19 流光穿刺 | Three-sample Glaive blade trail advances along the fixed 650 line over .25s |
| 20 裂甲天锋 | Faerie Fire fracture/armor marker at original target, retained for armor window |
| 21 万刃归宗 | Four alternating left/right Cleave sword impacts on the same original at 0/.2/.4/.6 |
| 22 天诛剑阵 | Five Monsoon impacts at fixed center/cardinal radius180, refreshed at each 1s strike |
| 23 青藤缚足 | Entangling Roots at the original, tied to .75s control context |
| 24 噬生寄种 | Initial Rejuvenation seed, original tick pulses, one seed-to-three PoisonSting branch at3s, weak tick feedback4/5s |
| 25 繁花蚀骨 | Three Tranquility flowers on road points; first whole-cast contact adds Rejuvenation feedback |
| 26 万象森罗 | Three sequential ImpaleCaster root-thorn eruptions on road points at0/.4/.8s |
| 27 寒星破 | .25s ColdArrow flight to original center, followed by a retained FrostArmor slow marker |
| 28 回澜引 | BreathOfFrost trail outward0.. .3s; FrostWyrm trail reverses from fixed600 endpoint at.6.. .9s |
| 29 霜华镜狱 | Five FrostArmor warning points; Blizzard on remembered freeze targets at.6s; five FrostNova shatter points at.95s |
| 30 沧海归墟 | Five Tornado center/rim swirls; .5s pulse refresh plus FrostNova center feedback |
| 31 烬火印 | Four original-target FlameStrikeDamageTarget pulses at1/2/3/4s |
| 32 赤莲绽 | Center plus four FlameStrike1 petal impacts at radius160 |
| 33 焚星坠 | MarkOfChaos warning footprint; RainOfFire fall at.75s; FlameStrikeEmbers at1.75/2.75/3.75s |
| 34 业火连城 | Up to four initial MarkOfChaos marks; successive five-point Incinerate explosions at each mark's last position |
| 35 裂岩重击 | ThunderclapTarget fracture at original and shared narrow stagger window |
| 36 崩山震 | Three WarStomp eruptions distributed across the actual 90degree fan |
| 37 镇岳印 | Center/four Earthquake seal points, retained for fixed4s slow/resistance-weakening area |
| 38 地脉天崩 | Four sequential ImpaleHitTarget rifts at road points0/.2/.4/.6s |

Legacy10 remains a distinct DeathAndDecay field per real corpse proc, with its
original independently overlapping 3x1s ticks and at most12 victims per tick.
It shares owner/generation cancellation; there is no new one-field damage cap.
