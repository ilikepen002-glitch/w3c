# 局部战斗热路径第一批：等价减工

## 范围与不变量

基线 commit：`1949bc25e0c31aca8e9c6148d5c5b8e8bb4d902e`。本批属于普通局部改动，沿用现有接口职责和生命周期，只实施：

1. 主索敌私有组改为 `hasNext()/next()` 消耗遍历，保留唯一 `destr()`。扫描本身不发订单/伤害；合法当前目标优先、严格改善与 handle-id 决胜不依赖枚举顺序。
2. 副箭候选保留原 for-in、过滤、插入和严格 `<`/`>`。将同一次范围过滤已算出的真实距离传给原选箭 helper，沿用原速度保护与除法。主箭飞行时间仍独立计算。
3. 两个 native 冷却热循环使用 2 项有序子目录，仍引用原完整定义；不复制技能 rawcode、12/9 秒冷却数据。完整目录及其他查询不变。

没有跨系统缓存、新 scheduler、分帧/错峰、主副候选共享、平方距离替换。目标规则、6/7 副箭数量、每段伤害、飞行时长、`.03` 即时命中边界、readyAt、`.10` native tick、同步技能时序不变。

## 最终产物

- 地图：`ExampleMap.w3x`，显示名 `契灵守卫战 20261014-1836-UTC+8`
- 地图 SHA-256：`d84f03d19c4e026c85968e4de9a9cf3057d0ff7ad4471aa4f1155a6bad450d43`
- packed JASS SHA-256：`fd03a61e318de78bbcfa85c1d92e7c4c489f3815bd782c79d79c8b03fd5f607d`
- 基线地图 SHA-256：`cd662ef1454356687cd7e9383b702d5c33f2614e863b2bbdb059659ddf5ee651`
- 两图 427 个 MPQ 成员名称完全相同；仅 `war3map.j` 与合法构建时间戳 `war3map.w3i` 不同。归一化时间戳后 W3I 完全相同，其余物编/资源逐字节一致。
- 官方构建再次核对 407 个 imports；4 个 Leoric 输入保持 tracked 且与基线一致。compiler/Grill/stdlib/JDK/config 锁均未修改。

## 实际 packed 计数与等价 trace

`VerifyLocalCombatHotpathArtifact.py` 从两份真实 MPQ 执行生产函数，并执行真实 packed group 复制/遍历/销毁 helper。单位、原生区域枚举返回集、timer、ability、LinkedList 为明示模型边界；视觉预算预先压满以隔离战斗路径。

| 同路合法候选 | 范围查询 | CreateGroup | GroupAddUnit 复制 | GroupRemoveUnit 遍历 | SquareRoot |
| --- | --- | --- | --- | --- | --- |
| 16 | 2 → 2 | 4 → 3 | 32 → 16 | 32 → 32 | 49 → 34 |
| 52 | 2 → 2 | 4 → 3 | 104 → 52 | 104 → 104 | 157 → 106 |
| 104 | 2 → 2 | 4 → 3 | 208 → 104 | 208 → 208 | 313 → 210 |
| 308 | 2 → 2 | 4 → 3 | 616 → 308 | 616 → 616 | 925 → 618 |

308 候选仅为压力输入，不是正常单波实测。无 provider 的低级塔、有 provider 的高级塔两种温态光环场景，每次刷新完整目录调用均 `48 → 4`，能力读写/移除 native 边界计数与结果不变。

验证包括：
- 五塔族、4 种 current/严格改善场景、24 种枚举排列，共 480 个主索敌结果与基线完全一致，空集合亦正确且无组泄漏。
- 6/7 副箭等距溢出、近目标替换、range 与 +.405 边界、飞行差 `.03` 两侧、无副目标、空源/主目标。逐箭 `(target, flightTime, context, revision)`、顺序、到期延迟、即时/延迟伤害事件完全一致。
- 两个 native 同时存在并施放：actual level 19 的已锁 deadline、下一次 desired level、busy/结束、能力缺失/恢复、关闭路线清理与 autocast 订单逐项一致。
- 5 个 in-memory packed mutant（错误飞行除法、等距替换、即时命中阈值、漏第二 native、恢复主组复制）均完整执行后被 trace/成本差异检出。解释器异常不算 mutation 检出证据。

这些是已执行脚本/模型边界的次数，不是 Warcraft opcode、CPU 毫秒或 FPS。没有实机性能提升数值。

## 验证与保留的失败

- 官方 `Run-WurstLinux.py checks`：完整 typecheck + 全 Wurst tests PASS。
- 官方 `Run-WurstLinux.py build`：PASS；JASS 1.28、154 allocator legacy gate、真实 MPQ 主动 CD 合同、精灵/游戏启动门禁、物编解析/全部 imports/命名门禁通过，原子发布最终图。
- 已通过 checks 和最终 build 的全部生产 `.wurst` SHA 与最终树一致。之后只调整 Python fixture/证据，不改变生产源码；没有重复无变化的 Wurst 编译。
- 最终显式地图 target-priority Python 9 项全部 PASS（无 skip）；完整 source + actual packed 目标门禁通过，含 2304 comparator cases、手动/redirect/身份/trial、稀疏恢复、A/B/A 在途队列及 9 个 packed mutant。
- 最终主动冷却 Python 全套 47 项 PASS（259.462 秒，无 skip）；原始基线 44 项亦 PASS。native 子目录完整性/唯一性/顺序/无效 fallback 增加 Wurst 与 Python 负测；第三个合成 native 必须登记在子目录，两个消费者无需改动。
- 当前成长材料：4 路 32 波实际结算、重复/关闭/溢出/延迟结算及 3 个 mutant PASS。
- 当前塔进化 replay：10 条末级分支、935 kill-only cases、宿主绑定/readyAt 保留、旧票据与重复消费等 PASS。其他成长源未改，复用其既有验证。

定位并修正的测试问题，失败日志/manifest 均保留在外部证据目录：
1. 首次计数 fixture 未初始化 native 冷却链，读取空链得到 KeyError；加入真实包初始化后通过。
2. 首轮 build 的新 native façade gate 要求所有 tuple 输出，而编译器只保留实际使用的 key/driver/abilityId。源端仍验证完整 tuple，packed 端完整验证原总目录、强制所有被消费字段及所有额外输出；新增裁剪形式正测及缺必需字段/错数据负测。未放宽生产冷却合同，最终正式 build 重跑通过。
3. 历史 target fixture 的 `group_hasNext` cursor 只能处理先经 for-in clone 的组。改为执行真实 packed group helper，仅模型最底层 group native；最终真实地图完整门禁通过。没有改生产源码来迁就旧 fixture。

完整日志、两个成功及一个失败 transaction、baseline 地图均位于 `/workspace/shared/local-combat-hotpath-evidence-20261014` 或 `validation-summary.json` 指向的 transaction。源变更、必要正负 trace 和最终图一起冻结，未推送、未部署、未启动 Warcraft。

## 复现

```text
python3 tools/VerifyLocalCombatHotpathArtifact.py ExampleMap.w3x --baseline <baseline.w3x> --output <comparison.json>
python3 tools/VerifyTowerTargetPriorityArtifact.py ExampleMap.w3x --output <target.json>
python3 tools/VerifyActiveCooldownContract.py --map ExampleMap.w3x
python3 -m unittest discover -s tests/python -p test_active_cooldown_contract.py
PYTHON_CANDIDATE_MAP=<absolute-final-map> python3 -m unittest discover -s tests/python -p test_tower_target_priority_artifact.py
python3 tools/VerifyPetGrowthSupplyArtifact.py ExampleMap.w3x --baseline <baseline.w3x> --output <growth.json>
python3 tools/VerifyTowerEvolutionReplay.py ExampleMap.w3x --output <evolution.json>
```

官方完整 checks/build 使用仓库 `Run-WurstLinux.py` 与 manifest 中锁定的独立 tools/JDK/stdlib；严格串行。详细命令保留在相邻日志。
