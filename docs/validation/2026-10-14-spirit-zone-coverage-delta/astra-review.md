# S1 区域减速差量更新：Astra 最终复审

日期：2026-10-14 UTC。最终结论：**PASS WITH NOTES**。

只批准下述 **e5fb76ea… 修复图**。旧 160ad325… 图仍为 FAIL，不可交付。原失败审查保留为 `astra-review-rejected-160ad325.md`，原反例、失败日志和地图均保留。

## 1. 范围、模型与精确版本

- 风险：高风险，涉及持续 cast 的覆盖/引用/贡献生命周期。实际阶段为 Astra PLAN → GPT-6.1 Sol 实施 → Astra REVIEW；首轮发现阻塞后，Astra 定向 PLAN 修订 → Sol 修复 → 本次 Astra 新图复审。
- 源码比较基线：`8b941e84eb392514a6c96434b3fdc1d6c11d9d7d`（已包含 A1/C1、最终 HUD/D2）。
- 修复生产提交：`872e5b40b950714059cf70a2967af321f2074b40`。
- 最终构图/验证工具提交：`d6f4c7000cc674fd9f30186f8d2a395d94107f8f`；审查结束时工作树干净，生产未再变。
- 地图：`zone-integrated-legacy-fixed.w3x`。
- 最终地图 SHA-256：`e5fb76ea50517db2d624639133e3d20688c7509845cfcb48dfdae9777d06d810`。
- 最终 JASS SHA-256：`177a6f48a6edec60ad4898534c0588111d12ae9497dbb41e8fd42935db95573b`。
- 对照地图 SHA-256：`c57d8d6b01818f1e77b90317ac7aa5ee630eccc9e76ef1ac5f7f16f96f09b720`。
- 对照 JASS SHA-256：`06db07c8082d148a7c73068dc041cf1c1101b34a6d00de8c3bc8b875d2abdbd2`。

本次审查读取实际源差异、打包函数、正式 manifest/日志和完整最终报告，并独立执行原回归反例、MPQ 差异及输入 hash 核验；未以源码推断替代实际地图证据。

## 2. 原阻塞 S1-R1 已关闭

首轮真实连续技能链 `28 → 30 → 26` 三次复用同一个 class ID：旧候选因区域离开清掉其它技能留下的 `hitCounts`，使最后一段从基线 4 击变成 12 击，每击 70。同类 `controlled` 搬动/清零也会改变后继根须的目标。大量每例新 Runtime 的旧门禁未发现此问题。

修复严格执行 `S1-plan-amendment-legacy-slots.md`：

- `swapZoneVictimSlots` 只移动 zone 真正拥有的六组字段：victims、revisions、targetPositions、last X/Y、zone power。
- zone 的 swap/forget 不再读写 `hitCounts`/`controlled`；这两组 legacy 物理槽在整个区域生命周期逐槽保持原样。
- 无备份数组或新增生命周期状态；没有修改 init/remember，也没有借机修复基线原有的跨技能残值规则。

关闭证据：

- `review-cross-skill-reuse-fixed.py/json/log`：Astra 对新图独立重跑原反例，只更换地图路径/输出名。真实 class IDs 仍为 `[1,1,1]`，最终严格恢复 **4→4 击**，完整阶段字段和伤害顺序相同。
- `cross-skill-paired-legacy-fixed.json`：8 条真实连续链覆盖 30/37、全离开、反序、多 zone、26 控制标记、自然结束/召回/失效退出；伤害、控制目标/时刻、CD、身份与最终清理对等。
- 误清/误交换 hitCounts/controlled 的 4 个新 packed mutant 均由后继真实伤害或控制目标断言拒绝，未仅靠 sentinel。

未剩余阻塞问题。

## 3. 实现契约核验

- 原 group 枚举、顺序和最多 12 覆盖保持。保留对象按当前 sample 顺序排列，zone-owned 平行字段同步移动；legacy 非 zone 字段不动。
- 交集要求目标/revision一致、目标位置记录匹配且未 retired、实际 Boss 调整后 power 相同。power 变化走离开+进入，避免原 exact source/identity/rank/power 键留下旧强度贡献。
- 相交者仍执行原 slow offer、完整 refresh 和封域 weakening offer。未引入 S2 聚合跳过；其它过期源、缺失 carrier、实际速度异常仍在原时点修复。
- 离开仅撤自己的 source+identity 和 source+cast token；先撤 slot ownership，再释放位置引用。scratch 在同步脉冲前清空。
- generation 在 executing cancel 中保留旧 active index，禁止旧清理与新代覆盖重叠；析构后新代可进入，迟到旧代入场被 binding 拒绝。
- 0.25 秒覆盖、0.5 秒伤害、4 秒终点、stage/nextAt/expiresAt、readyAt、原攻击 fence、scheduler 0.05 秒均未变。没有技能错峰、伤害漏跳、顺序或强度规则变化。

原 PLAN 的两处必要澄清均有明确依据：actual power 必须纳入交集；“整组移动”仅限 zone 实际拥有的字段，不能移动其它技能可跨代观察的 legacy 物理槽。

## 4. 最终新图证据

所有以下结果均指向 e5fb76ea…/177a6f48…，未复用旧失败地图的 PASS 证书。

| 门禁 | 最终结果 |
| --- | --- |
| 正式 typecheck、完整 tests、build | PASS，无 warning |
| 三份正式 manifest 的当前生产/测试/config 输入 | 每份 235 项 hash 全匹配 |
| 独立 MPQ 窄差异 | 427 成员与 427 活动 hash 相同；425 其它成员逐字节一致 |
| W3I | 仅地图名/加载标题构建时间戳不同，其余字节一致 |
| zone 全量 paired | 41/41 严格 trace 对等、全部清理归零 |
| zone packed 负向变异 | 14/14 拒绝，包括旧代 admission 与 legacy 回归 |
| 22 主动 × 12 模式 | 264/264 对等，每例 131 状态点 |
| 完整 retention gate | completeGate=true；23 覆盖项（含 mutations）、24 lifetime、80 abort、26 mutant 拒绝 |
| 额外非终结技能取消 | 8 技能 × 两种 tick 顺序，16/16 对等归零 |
| A1/C1 | 实际冷却/索敌 PASS；47 单测、2304 比较器、480 选择、9+5 mutant 通过 |
| HUD/D2 | 155 HUD 对照、934 击杀、13 修复、17 生命周期、10 分支及相关 mutants 通过 |

主要证据文件：

- `review-support-fixed.json` 与 `review-support-fixed.py`
- `paired-zone-legacy-fixed.json`（工具 SHA-256 `acc8dfb0e8080e2200efc27866ac5647f3a0825e0eb6549fd3bdba79e20be94e`，已与当前树核对）
- `fixed-active-regression/summary.json`、`retention.json`、`all-active-visual.json`、`nonterminal-cancels.json`
- `fixed-hotpath-regression/summary.json`、`fixed-hud-regression/summary.json`
- `official-typecheck-legacy-fixed.log`、`official-full-tests-legacy-fixed.log`、`official-build-legacy-fixed.log`

retention 是候选不变量门禁，不能冒称其自身为完整 paired 等价；整体等价由 zone 41 场景、专门跨技能链、264 主动对照和其它实际对照共同支持。

观察器修正也已审查：`tdPetSpellDamage` 仅排除明确签名命名的编译器末尾 `w__wurst_stackPos` 诊断字符串，其余五个玩法参数、时钟、native 伤害和事件继续严格比较。未放宽伤害、控制、CD 或身份字段。旧错误预期、debug 假差异及夹具解绑失败日志均保留。

## 5. 性能结果与必须披露的非阻塞备注

完整表达式计数包含固定数组 dispatch、匹配和重排成本；仅是离线解释器工作代理。

| 场景 | 基线表达式 | 最终表达式 |
| --- | ---: | ---: |
| 单源首次覆盖采样 | 25,926 | 28,970 |
| 单源稳态覆盖采样 | 37,574 | 21,272 |
| 单源带伤害脉冲采样 | 43,538 | 27,236 |
| 13 人换入并反序 | 36,330 | 23,626 |
| 10 同强源稳态 | 355,172 | 245,372 |
| 40 总同强源稳态 | 1,417,232 | 978,032 |

- 单源稳态 slow refresh **24→12**；timed new/destroy 各 **12→0**；位置 acquire/release 各 **12→0**；正常稳态速度写 **24→0**。
- 40 总源稳态 refresh **960→480**，timed new/destroy 各 **480→0**。相交仍做 full refresh，不能宣称 refresh 全部为零。
- 实际机关怪封域双源测试：weakening new/destroy 各 **24→0**，原 token 续期与减抗结果保持。
- 40 源是合法四路各十宿主、同次 scheduler 的总压力，每路 52 候选/12 覆盖，单目标最多十源；不是四十源叠同一目标。
- **首次覆盖采样增加约 11.7%**。原攻击事件至 cast 建立的 1/2/10/40 源全路径计数则逐项不变（`admission-counts-legacy-fixed.json`）。
- **实际 recall/析构有固定增量**：严格窗口只包原 `TDPet_recall` 及实际析构，排除 pre/post observer、断言、重复清理、visual shutdown 与 recycler。已实测三技能各 1/10/40 源，共 9 例：非 zone 28 表达式 **550→987、4690→9060、20428→37908**（每源 +437）；zone 30 **16087→16588、137378→142388、550670→570710**；zone 37 **16268→16769、140162→145172、555197→575237**（两种 zone 均每源 +501）。40 源增量 +17480/+20040 是实际测量，非外推。全部即刻 ref/timed/token/cast/tasks 清零、前后状态及 native 调用清单均与基线一致；见 `recall-costs-legacy-fixed.py/json/log`。这是低频、有界字段清理成本，无新增伤害、native 分配或生命周期残留，不要求为消掉微小增量再次扩改。旧含视觉 shutdown/recycle 的 `cleanup-costs-legacy-fixed-clean.json` 保留为历史窗口，不作为单独 recall 计数。
- 本次有意保持基线 legacy 跨技能残值规则；任何独立行为修复应另行提出，不能暗中夹入等价性能优化。

因此能支持“稳定覆盖重复工作显著减少”，不能支持“每条路径都更便宜”。

## 6. 实机边界与交付决定

未启动或操控 Warcraft III。真实引擎枚举、浮点、timer 投递、渲染、多人同步和帧时间未实测；计数不是 JASS opcode、CPU 时间或 FPS，不承诺不卡顿。按项目约定，这些实机边界本身不阻塞离线交付。

**最终 e5fb76ea… 候选通过高风险 REVIEW，可在披露首采样/退出增量和实机边界后交付。旧 160ad325… 候选继续禁止交付。**
