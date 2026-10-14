# Attached spirit silhouette sizing

Baseline: `779151ec`, fetched from `origin/codex/archer-split-arrow-shots`.

## Change and boundary

Only `pv01..pv0F` attached-display scale changes. Each species is rounded from 130 divided by the longest axis of its current MDX Display Float sequence extent. These extents are conservative animation envelopes, not screen-space or opaque-pixel measurements. The existing models were not geometrically normalized: their Float longest axes span approximately 86–167 model units. Applying 0.45 uniformly produced approximately 39–75 world units. The new values give 129–131 world units, with no model/texture/triangle/bone changes.

Wild scale remains 2.55 (three times the earlier 0.85 baseline); collection scale remains 0.65. Collision, combat, visual-unit count, animation cadence, timers and animation resources remain unchanged. Larger screen coverage can increase fill work slightly; no measured FPS claim.

The fly-height rule remains model-height profile × (0.95 + 0.03 × tower level) + 24. Fallback remains 160. Archer model-height profiles remain 110 for levels 1–4 and 160 for 5–6. All 35 tower rawcodes retain their existing heights. Changing fly-height together with scale would unnecessarily displace the familiar anchor. The most negative new display-pose Z is about −1.3, leaving about 22.7 units of the existing 24-unit art clearance. Tower head coordinates are approximate existing art profiles, not native measurements.

The 130 target bounds the longest idle silhouette; transient gestures peak at 161.3 units (Cinder Tail Fox). It avoids making long wings/tails five times their old size. Actual perspective, facing and native health-bar positioning can still cause overlap, especially tall spirits and closely spaced towers. Native normal-camera validation is not performed or claimed. The supplied archer screenshot confirms the current small appearance but cannot determine exact world-to-pixel scaling.

## Parameters

| Species | Old scale | New scale | Old Float max | New Float max | Max gesture |
|---|---:|---:|---:|---:|---:|
| 1 银鬃灵兽 | 0.45 | 0.83 | 70.9 | 130.7 | 143.6 |
| 2 锋翼隼 | 0.45 | 0.78 | 75.1 | 130.1 | 148.8 |
| 3 铜甲穿山灵 | 0.45 | 0.79 | 74.3 | 130.5 | 131.4 |
| 4 叶翼仙灵 | 0.45 | 1.07 | 54.5 | 129.6 | 138.2 |
| 5 树芽鹿 | 0.45 | 1.21 | 48.3 | 129.8 | 135.2 |
| 6 菌伞灵 | 0.45 | 1.46 | 40.2 | 130.4 | 135.8 |
| 7 潮尾灵蛟 | 0.45 | 0.81 | 72.6 | 130.7 | 132.7 |
| 8 霜鳍灵鲼 | 0.45 | 0.88 | 66.2 | 129.4 | 130.1 |
| 9 雪鬃水獭 | 0.45 | 0.98 | 59.6 | 129.8 | 130.4 |
| 10 赤翎火鸟 | 0.45 | 1.04 | 56.3 | 130.2 | 148.4 |
| 11 熔角火蜥 | 0.45 | 0.82 | 71.6 | 130.4 | 131.5 |
| 12 烬尾火狐 | 0.45 | 0.99 | 59.1 | 130.0 | 161.3 |
| 13 岩壳龟 | 0.45 | 1.06 | 55.3 | 130.4 | 132.8 |
| 14 磐臂山魈 | 0.45 | 1.50 | 38.9 | 129.6 | 138.6 |
| 15 砂环灵螺 | 0.45 | 1.17 | 50.0 | 130.0 | 132.3 |

## Verification

- `python3 tools/VerifyPetDisplayScale.py`: PASS. Checks exact attached-only object-source delta against the baseline, unchanged height/animation rules, all 15 Float envelopes, gesture envelope ≤165, and pose lower bound.
- `python3 -m unittest discover -s tests/python -p test_pet_display_scale.py -v`: 5 PASS, including oversize, wild-scale, height and normalization negative tests.
- Added Wurst parameter-range/species tests; execution awaits parent-coordinated checks/build. No Grill, map build or game launch in this task.
- `git diff --check`: PASS.
- Historical `test_all_pet_display_assets.py`: 6 PASS, old frozen-source assertion FAIL. Confirmed the same frozen gate already fails on untouched 779151ec because later TDPetState changes postdate its baseline; it now also detects this intentional scale addition. No weakening of historical gate.
- Historical wild visibility test still expects 4.25, while untouched current source is 2.55. Its expectation is already stale; unchanged in this narrow patch.

Parent must compile/check and build the integrated map, then verify actual packed `pv01..pv0F` `usca` values against this report and confirm wild, collection and other unit fields have no unrelated changes. Do not treat source tests as object-output or native-rendering proof.
