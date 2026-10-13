# 光环目标与受益载体按钮排查

## 基线与范围

- 正式分支：`codex/archer-split-arrow-shots`。
- 2026-10-13 定向读取并核对远端 HEAD：`710903bc772fa04092b58352b0617c251f0d9546`。
- 已发布根地图 SHA-256：`1d5c62b907009583282fabd5d3b1c29ea88000e9028d8e070792777a5ade0f44`。
- 本次为局部物编表现修正，沿用全部现有运行时、状态归属、对象 ID 和效果计算，不涉及系统级重构。

## 已确认的证据

1. 源码 `TDAuraRuntime.tdAuraOfferSource` 与根地图实际 `war3map.j` 均先检查来源玩家与目标路线。友方装备光环只进入塔分支，怪物分支只接收装备减速。精灵统御只给宿主，迟滞给本路范围内敌人。
2. 直接执行已发布 JASS 的 112 个装备目标用例、35 个塔光环目标用例、6 个精灵目标用例通过。测试包含自身、同玩家另一塔、队友塔、本路怪物、另一路怪物、范围边界/越界与冷却资格。
3. 疾风鼓实际 JASS 将自身和同玩家另一塔的 `A129` 设置到 4 级，并给同一单位添加疾风状态载体；队友和怪物均未获得。离开 350 范围后，该塔的数值载体和状态载体均被移除。这里模拟的是引擎原生函数边界，不是游戏实际攻速或状态栏观测。
4. 根地图 W3A 中四个百分比受益载体：`AM13/AM14` 继承 `AEar`，`AM15/AM16` 继承 `AIcd`。它们有 self 目标、真实 Buff、百分比数值和 `aite=1`，但没有覆盖 `abpx/abpy/aart/atp1/aub1`。运行时会把载体添加到每个受益塔，因此遗留原生强击/统帅按钮数据是已确认的配置缺口。
5. 真正来源 `A101/A111/A105/AeCM` 有独立定制的名称、图标和 `(1,1)` 按钮位。已发布 W3U 中 `A101` 仅在 `uA15/uA6A/uA6B`，`A105` 仅在 `uH15/uH6A/uH6B`；并非给所有塔挂上来源技能。
6. 疾风状态 Buff `BM09–BM0c` 已有自定义名称、鼓图标和描述，没有沿用“敌方减速”说明。其原生显示载体继承 `Aasl`，`atar=self`、`Slo1=0`。仅凭继承母体不能断言增益被施加给敌方；也不能凭 self 字段声称原生建筑 Buff 投射已实机验证。

## 最小修正

`wurst/auras/TDAuraObjectGen.wurst` 仅为白虎和统帅两族、各两级百分比受益载体增加按钮位 `(0,-11)`。

- 不移除、不禁用数值载体，不改变百分比、self 目标或 Buff。
- 不隐藏真正的光环来源技能。
- 不新增运行时分支、法术书或新版 `BlzUnitHideAbility` API。
- 其它状态载体沿用 `Aasl` 的既有隐藏实现；个人攻击/攻速等物品载体不属于本次暴露的 `AEar/AIcd` 百分比载体。

兼容性参考：[2017 年原帖的 1.26 实测记录](https://www.hiveworkshop.com/threads/cant-hide-effect-ability-button-using-disabled-spellbook.294133/) 报告 `(0,-11)` 可用。该帖也有未经作者验证的旧 Mac 风险讨论，因此这里只采用遗留物编字段，不能把社区记录提升为本次 1.27 实机验证。

## 校验与限制

- `python -m unittest discover -s tests/python -p test_aura_target_artifact.py -v`：8 项通过。
- 新门禁实际执行打包 JASS；三项反例分别删除同玩家限制、放开装备友方光环到怪物、放开精灵宿主限制，均被拒绝。
- 隐藏字段门禁的内存对象正例通过；逐个撤销四个载体的隐藏字段或隐藏真正来源按钮，均被拒绝。内存对象正例仅测试门禁自身，不是新地图产物。
- 已发布旧地图对 `verify_hidden_carriers` 为预期 RED：`AM13: internal percentage carrier button is not hidden`。
- `python tools/VerifyEquipmentAuraSpecialArtifact.py ExampleMap.w3x`：已发布基线门禁通过，证明既有数值、来源与 Buff 配置；不代表新按钮修正已打包。
- `git diff --check` 通过。
- 邻近装备物编/说明契约的 10 个受控测试通过；热点回归 6 项通过。地图回放输入是上述已发布基线，不是待编译修正图。
- 为装备说明套件指定 `EQUIPMENT_CANDIDATE_MAP=ExampleMap.w3x` 后，已发布基线的整图说明前置校验报既有错误 `cultivation risk/cost missing`（`VerifyPlayerTooltipArtifact.py:316`）。本次未改培养说明；统一文案与编图任务需要对新产物复测，不能把此套件记为全通过。
- Wurst 检查与地图构建未运行：当前云端是 Linux，已有批准入口为 Windows `.bat`；新 Linux 入口由统一构建任务准备，本任务未绕路编图或使用旧编译器。
- 未运行 Warcraft，未验证 1.27 原生按钮隐藏、建筑/英雄/无敌目标的原生 Buff 投射或用户“疾风在怪物上”的现场现象。

统一编图后必须运行：

```text
python tools/VerifyAuraTargetArtifact.py ExampleMap.w3x --require-hidden-carriers
python tools/VerifyEquipmentAuraSpecialArtifact.py ExampleMap.w3x
```

目前没有把友方数值增益改到敌方的源码/打包 JASS 证据，因此本修正不改目标算法。玩家文案由同批文案整理统一补齐作用对象。
