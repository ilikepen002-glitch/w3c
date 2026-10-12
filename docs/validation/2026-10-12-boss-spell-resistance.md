# Boss 阶段法术抗性验证

## 变更与审查范围

- 源码基线：`0330fd12de4d66c4a1ca4980e10b771f0903fbfc`。
- 高风险：跨塔、装备、精灵发伤通道与敌军记录生命周期。
- GPT-6 Astra 方案通过；GPT-6.1 Sol 实施源码、测试与离线验证。Astra 正式只读终审：PASS WITH NOTES，无阻塞事项。
- 固定 pre1.29 标准库树：`90b45617eda50c15703e8cb2ec3241d3c7b61816`。不修改依赖。
- 云端范围；未启动游戏、未做本轮实机 HP 测量。
- 详见 [解决记录](../solutions/2026-10-12-Boss阶段法术抗性未消费.md)。

## 基线封存

基线是下述固定 Git commit 的原始地图与源码；私有恢复包另保留快照，不加入公开提交。

- `ExampleMap.w3x` SHA-256：`10a6eb992b4a9fb0edf2aa81db8700e5b78042462e5d5a130b71a2747907bb0f`。
- `wurst/` 为上述 HEAD 的 `git archive` 原始源码；`PROVENANCE.txt` 记录来源与地图 hash。
- 不以 `_build/` 缓存或旧编译脚本替代最终验证。

## 已完成静态核验

- `git diff --check`：通过。
- 全部生产 `damageTarget` 调用点：塔 3 点、装备 2 点、精灵 1 点，无新增发伤点。
- 显式法术缩放消费：风暴、尸爆、装备毒，以及精灵 wrapper 的尸爆毒域/雷链火冲；每处一次。
- `Tspl`、`Eadd`、精灵原 `damage()` 与 `onAttack` 的 `base * extra` 发伤通道/ID/来源保留。
- runtime 仅一个 `addUnreducedListener(2)` 注册；shutdown 不改独立 once 标志；compiletime 不注册；没有普通监听改量。
- 修改源码无 HP 写入、abort 重发或 DamageElement 改写。
- 原基线保护源码逐字节相同：TDConfig / TDState / TDGame / TDSpawn、塔 Catalog / Balance / Common / ObjectGen、EnemyMechanicObjectGen、DamageRuntime / DamageState。
- 固定库真实源码核验：先保存 code 布尔标记，之后负值重分类仍保留；early setAmount 同时更新 amount/unreducedAmount；原结算读取修改后的 amount。依赖没有改动。

## 已完成验证器自测

初版验证器自测 36 项通过，见 [构建前自测](2026-10-12-boss-spell-resistance/verifier-selftests-prebuild.log)。Astra 预审后修订再跑 `python -m unittest discover -s tests/python -p 'test_boss_spell_resistance_artifact.py' -v`：42 项通过；真实最终 MPQ test class 在新包尚未生成时明确 skip 1 次。日志见 [预审修订回归](2026-10-12-boss-spell-resistance/verifier-selftests-prereview-revision.log)。合成函数只用于检验验证器自身，不能当作本轮生产包通过。

- 自测执行已有基线包的真实固定依赖引擎与控制桩，覆盖 2160 个状态组合、48 个分类/早期结算/记账 capture 组合、11 条法术和派生发伤路径。
- 反例覆盖各法术入口漏缩放、双乘、code 标记丢失、Eadd/派生 Pdam 误缩放、early 换 late、错误 priority、重复监听、shutdown/compiletime 回归、四类物编字节变更、胜负变化、隐藏 HP/abort/type/element 补偿及解释器递归界限。
- 基线对照验证器执行确认：36 个经济/胜负/波次/记账保护函数。
- 既有 `test_verify_tower_upgrade_artifact.py` 的 28 项由验证器实施阶段通过；旧尸爆校验只增加共享缩放 wrapper 的兼容，不降低原有倍率消费要求。
- Python 语法编译与 `git diff --check` 通过。
- 新增 signed=0 的真实引擎函数边界：不 capture/hit、不进入结算；之后正常 native spell 仍缩放一次，code/ID 没有残留。
- 干净本地 clone、没有兄弟目录基线时，统一 resolver 从固定 Git 对象提取地图与源码，仅写 TemporaryDirectory。map SHA 及 59 个 Wurst 文件的路径/内容聚合 SHA 均固定校验。测试覆盖 env 显式覆盖无需 Git、错误 map/source hash 拒绝与缺历史明确前置说明。

Astra 预审确认生产源码符合方案、无阻塞代码缺陷；要求修正的基线可复现性与验证措辞已落实并定向回归。Astra 在 2026-10-12 的正式终审确认以下完整源码/产物证据，结论 PASS WITH NOTES；备注仅为下述实机/native shield/trigger timing 与 accounting capture stub 证明边界，均非阻塞。

## 已完成完整检查与构建

经审且冻结的 Linux 包装 `cloud_wrapper.py` SHA-256 为 `de59b76c08788f7241b7c5a2cf6c1ef6641ea214c0999491a4baed82e20bf9f6`。固定依赖、检查 staging、真实编译与最终发布检查串行运行，没有调用旧移植入口。

本轮使用已审 Linux 包装的 all 模式完成检查与构建。项目可复现实验入口为 `tools/Run-WurstChecks.bat` 与 `build-and-deploy-test-map.bat`；公开记录只保留阶段、输入版本/hash 和结果，不包含云端目录或环境变量。

- typecheck PASS；315/315 Wurst 测试 PASS（含新增 5 项 Boss 测试）。46 份 tests/wurst 文件与构建 staging hashes 一致，staging 已清理，临时配置/依赖已恢复。
- 首轮仅新测试有 3 个语法错误：局部变量 hides 与未括号的嵌套 ternary。定向修改测试变量名/括号后，上述完整 all 重跑成功，生产代码未因该问题改变。初失败日志保留，根成品在失败时保持原基线 SHA。
- 真实地图构建 PASS。云端产出根 `ExampleMap.w3x`；显示名及加载标题为 `深渊守望 20261012-0938-UTC+8`。
- 成品 map SHA-256：`1b2b9671d3ce7b05837811dbfbb8efa0815fe4bcea840f53f8dde4789761f96e`。
- 成品 `war3map.j` SHA-256：`247037e889f625c09f01e14672e89fcc97023e1b67e85ea1abc0f0b158781d83`，1,025,274 字节。
- 日志：[完整流程](2026-10-12-boss-spell-resistance/full-wurst-build.log)、[Wurst](2026-10-12-boss-spell-resistance/wurst-tests.log)、[构建结果](2026-10-12-boss-spell-resistance/build-result.json)。

`python -m unittest discover -s tests/python -v`

- 273/273 Python 测试 PASS，0 skip。专有 Boss 42 项自测/resolver 测试及 6 项真实 final-MPQ 测试全部通过；其余为既有回归。
- 日志：[全量 Python](2026-10-12-boss-spell-resistance/full-python-tests.log)。

## 实际最终 MPQ 与关联 artifact 验证

共 13 个完整 artifact CLI 成功，分为 1 个 Boss 专有、11 个通用、1 个玩家文案；下面的 source/helper 补验不混入这个计数。

1. Boss 专有 `VerifyBossSpellResistanceArtifact.py` PASS：真实最终包 helper/target adapter/native callback/once setup/shutdown/unregister/引擎结算函数执行，2160 个状态组合、48 个分类/结算/capture 组合、2 个零事件边界、11 条法术/派生发伤路径。6 个生产发伤点穷举且接线执行验证，保留代码标记、ID、来源与通道。36 个经济/波次/胜负/记账保护 JASS 函数与基线相同。完整 W3U/W3A/W3T 字节相同，W3Q 两边均缺省；未新挂护腕或探针。日志：[最终 Boss MPQ](2026-10-12-boss-spell-resistance/final-mpq-boss-artifact.log)。
2. 通用 11 个 CLI 全 PASS：TowerPlacement、EquipmentAbility、SlowAbility、BladestormAbility、Evolution、GroundItem、GroundUpgrade、PetUI、TowerSale、TowerUpgrade、TowerUiGround。各日志为同目录 `artifact-<名称>.log`。GroundUpgrade 执行 123 批次、256 可用状态、600 独立坐标与 144/145 边界；PetUI 执行 64 host capability、2176 skill admission 与 256 lane-enemy 组合。
3. PlayerTooltip CLI PASS：1523 个实际包文案实例，与数值/规则/长度约束一致。[日志](2026-10-12-boss-spell-resistance/artifact-PlayerTooltip.log)。

补验均 PASS：

- `BuildSemanticIcons.py --check`：32 对源图逐字节重建一致。[日志](2026-10-12-boss-spell-resistance/semantic-source-check.log)。
- 实际最终包图标 binding/object delta 使用真实 pre-Boss 基线；112 个实际 MPQ 图标的七 mip、hash/source/alpha 与 imports/manifest 核验，旧塔/精灵 UI artwork 只与真实 pre-icon `8dc9a2ce` 地图比较。没有混造或 normalize 基线。
- 实际部署 gate、多路线/合法 rebind/拒绝 guard 与原部署/recall/host/lifecycle/cooldown/population 编译结构保留；当前提示保持每塔一只。96 个 wild 对象 hpea/Aeth-only 与全部 61 Pcap/Pmas capture mask 保持。以上为当前合同补验，不冒称重新运行历史迁移专用 CLI。[补验日志](2026-10-12-boss-spell-resistance/current-icon-deployment-wild-contracts.log)。
- 两个真实 MPQ 共 144 成员，142 个逐字节相同；只有运行脚本和 W3I 显示时间标签改变。物编、地形/pathing、资源、imports 全不变。[成员比较](2026-10-12-boss-spell-resistance/mpq-member-equivalence.json)。

## 未执行与残余风险

- 未运行 Windows bat、Windows 部署、World Editor 或 Warcraft 实机。本轮不提供原生 HP、真实事件时机、护盾吸收、1.28 分类或完整平衡的实测结论。
- 没有目标 Warcraft 原始 MPQ，因此未执行 UnitParents 的原生目录 CLI；本轮完整单位物编与已发布基线逐字节相同。
- Python/Pillow 的 getdata() 未来弃用提示未影响当前验证；不是编译失败。
- 正式 Astra 终审 PASS WITH NOTES。按已明确授权独立 commit/push，仅更新 `codex/archer-split-arrow-shots`，发布前复核正式 HEAD `0330fd12`，禁止 force；核验远端 commit parent/tree/map Git blob。

离线 stub 执行证明生成脚本的规则、调用和生命周期契约。`tdDamageCaptureHit` 与 `tdEffectiveDamage` 真实执行，ledger credit/显示为采集 stub，验证最终 accounting capture/handoff 入参；没有执行完整 ledger.credit 累计。emit 在 early phase 后直接调用 onDamage，trigger/timer/native event 边界为模拟，不证明真实触发时机或原生护盾吸收；不会被表述为 Warcraft 原生 HP、1.28 原生分类或完整玩法平衡实测。

基线文件不在变更提交中。Python 测试默认从上述固定基线 HEAD 读取 `ExampleMap.w3x` 与 `wurst/`，不依赖兄弟目录布局；缺 Git 历史时明确提示前置条件。可显式设置 `BOSS_RESISTANCE_BASELINE` 与 `BOSS_RESISTANCE_BASELINE_SOURCE` 指向已核 hash 的封存输入；实际最终包 CLI 命令必须提供基线地图路径。

公开证据已最小脱敏：初失败只保留3项Wurst语法诊断，移除完整wrapper环境错误；其余记录去除云端绝对路径和不必要环境/命令设置。原始完整证据私有保存；生产源码、测试、validator与map字节未因此改变。
