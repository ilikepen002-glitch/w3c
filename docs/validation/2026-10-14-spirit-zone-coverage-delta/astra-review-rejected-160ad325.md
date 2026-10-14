# S1 区域减速差量更新：Astra 实际差异审查

日期：2026-10-14 UTC。审查模型：GPT-6 Astra。结论：**FAIL，阻塞交付。**

本结论针对实际已构建候选；新增的跨技能、连续同运行时、真实 class ID 复用回放发现伤害次数变化。已有局部回归通过不能覆盖或豁免该差异。未启动 Warcraft III。

## 1. 精确审查对象

- 工作树：`/workspace/shared/performance-zone-delta-20261014`
- 源码比较基线：`8b941e84eb392514a6c96434b3fdc1d6c11d9d7d`（已包含 A1/C1 与 HUD/D2）
- 生产源码最后修改：`31aa99f0f17c15135c7ae7b67eb562f93dd7f490`
- 构图输入提交：`97331f267f5341317c27a544160eb4bef9bd757b`
- 最新验证工具提交：`749bfc8595b7775bee9872aa0e173562a36333e2`；构图后仅观察器/测试工具改变，生产、测试 Wurst 与配置未变
- 基线地图 SHA-256：`c57d8d6b01818f1e77b90317ac7aa5ee630eccc9e76ef1ac5f7f16f96f09b720`
- 基线 JASS SHA-256：`06db07c8082d148a7c73068dc041cf1c1101b34a6d00de8c3bc8b875d2abdbd2`
- 候选：`zone-integrated.w3x`
- 候选地图 SHA-256：`160ad32521c9caa974eda9ffb83da13a2545f3b359af4f28d56209f9734c3bfc`
- 候选 JASS SHA-256：`6fdc2d0dae95afbd9dc29e22247bd59bc707c398773294214af549f7bd924e66`

已读取项目 AGENTS、开发技能及 runtime 参考、Astra PLAN，审查实际源差异、packed 函数、正式检查/构图日志、manifest 与实际地图。

## 2. 阻塞问题 S1-R1：区域覆盖清理改变后续技能的历史计数

严重性：高。位置：`TDPetCastContext.wurst` 的 `swapVictimSlots`、`forgetZoneVictim`，尤其 `hitCounts`/`controlled` 的搬动与清零；交界为 `remember`、实际编译生成的 `TDPetCastContext_init` 和后续 `segment`/`fireChain`。

实际 packed `TDPetCastContext_init` 不清 `hitCounts[12]` 与 `controlled[12]`，`remember` 也不初始化这两组字段。原区域技能不使用或改动这些槽值；S1 在离开时清零、重排时搬动它们。相同 cast class ID 被下一种技能复用后，`segment` 与 `fireChain` 会先读 `hitCounts` 再决定是否伤害。因此这些表面上对区域无用的值跨生命周期仍可观察。

独立实际两图复现：

1. 一个宿主先后绑定三只合法四槽精灵；每次都走实际原攻击入场、实际 scheduler、实际 recall/析构。技能顺序为 28 → 30 → 26。
2. 技能 28 在 20.15 与 20.75 执行往返，前八个槽的实际 `hitCounts` 成为 2，然后召回。
3. 技能 30 在 21.15 覆盖十二个目标；把目标移出范围，在 21.40 正常采样离开，然后召回。
4. 技能 26 在 22.15 执行第一段。三次实际分配均复用 class ID 1。
5. 基线：只对 2008–2011 产生 4 次伤害，每次 70。
6. 候选：对 2000–2011 产生 12 次伤害，每次 70。同一时刻额外 8 击、560 伤害，并改变目标/事件顺序。

证据：

- `review-cross-skill-reuse.py`
- `review-cross-skill-reuse.json`（`status: FAIL`，记录两份实际地图/JASS SHA、三个实际 class ID、各阶段计数与完整末段伤害）
- `review-cross-skill-reuse.log`

该复现没有直接写 `hitCounts`/`controlled`，没有替换生产函数或修改 JASS。仅使用既有合法精灵构造夹具、原生位置/时钟边界，以及同一运行时内的连续实际施法。先前只观察到计数字段差异的初版另保留为 `review-cross-skill-counts-only.*`；最终明确产生真实伤害差异的是 `review-cross-skill-reuse.*`。

这是原有跨代残值问题被本次优化改变了可观察结果。不能把候选“顺便修复了旧 bug”当作满足本任务的严格等价要求，也不能通过放宽 trace、清空基线计数或只启动全新 Runtime 来接受它。

### 修复与复审要求

- 由 Sol 做窄修复，使 zone 生命周期不会改变后续 class ID 使用者在基线中能观察到的旧计数/控制槽；不得全局初始化这些字段而悄悄改变其它技能规则。
- 可评估 zone 进入前保存、退出时恢复这两组 legacy 物理槽值，或采用经明确论证的 zone 专用字段/交换边界。两者都须说明额外状态、初次/取消开销及所有析构路径，不能仅删一条 clear 后忽略 permutation 同样改变残值。
- 新增连续同 Runtime 的 28→30/37→26/38/34 等针对性回放，覆盖全离开、部分换入、集合不变重排、自然结束/召回、实际 class ID 复用。至少本次复现必须严格对等。
- `controlled` 也需覆盖：继承真实旧控制标记，再经 zone 重排/清理后，后续根须控制的成功次数和次序应与基线相同。
- 修改后按项目门禁定向检查、完整测试及重新构图；只接受新实际地图上的证据，并重新交 Astra 审查。

## 3. 已成立的审查与回归结果

这些结果说明局部实现及证据链有效，但不能抵消 S1-R1。

### 源码与协议

- 12 个候选仍来自原 group 枚举顺序；无目标截断扩展或技能错峰。
- 相交判定包含单位、revision、非 retired 位置记录以及实际 Boss 调整后的 power。加入 actual power 是必要等价约束：原 slow offer 的键含 power，变更 power 时保留旧贡献会产生残留。
- 相交者仍走原 slow offer 与完整 refresh；source+identity、stage weakening 的 source+cast token 未重定义。未混入 S2 聚合快路。
- 0.25 秒覆盖、偶数 stage 脉冲、0.5 秒伤害、4 秒终点与 scheduler/readyAt 等调度规则源差异未改。
- slot 所有权先撤销再 release、scratch 在脉冲前清空方向正确；但“所有平行字段都可随区域记录移动”的假设未覆盖跨技能残值，导致上述阻塞。

### 正式输入与产物

独立 `review-support.json`/`review-support.py` 证明：

- typecheck、完整 tests、build 三个 PASS manifest，每份 235 个当前生产/测试/config 输入 hash 全部匹配；前两份从 SHA 验证的可恢复归档直接读取，未整包解压。
- typecheck/full-tests/build 日志无编译 warning。早期局部变量遮蔽 FAIL 日志完整保留，修正后重新通过。
- 两图 427 个成员及 427 个活动 MPQ hash 集合完全相同，无未知未列出成员。
- 425 个其它成员逐字节一致，包括物编与全部资源；只有 `war3map.j` 和 `war3map.w3i` 变化。
- W3I 仅地图名/加载标题中的构建时间戳不同，归一化这两个字段后其余字节全同。
- 未修改生成 JASS、依赖副本或工具链；未复制目录或重新构图。

### 已完成实际地图门禁

- `generation-admission.json`：执行中旧代取消保留 active index，阻止新代重叠；旧析构后新代可进入且实际强制 class ID 复用；迟到旧代入场被拒绝、新贡献与 CD 完整。10 个 S1 packed 负向变异全部被拒绝。
- `order-change.json`：第十三人替换、完整平行槽反序和后续同集合重排的局部区域回放对等。
- `active-regression/all-active-visual.json`：22 主动 × 12 模式，共 264 例，每例 131 状态点，严格 trace 相同。
- `active-regression/retention.json`：`completeGate=true`，23 个覆盖项（含 mutation 项）、24 lifetime、80 abort、26 个 packed mutant 全部拒绝。
- `active-regression/nonterminal-cancels.json`：8 种非终结技能 × 两种 tick 顺序，16 个取消/实际析构回放相同并归零。
- `hud-regression/summary.json`：155 个 HUD 对照、934 次击杀、13 项实际修复、17 生命周期与 10 分支等通过。
- `hotpath-regression/summary.json`：A1/C1 最终图主动冷却与目标优先级门禁、480 个选择用例、9+5 个负向变异通过。

上述大量用例每项从新 Runtime 或有限同技能重用开始，未覆盖本次发现的连续不同技能链。这是测试覆盖缺口，不是 Warcraft native 边界的借口。

`paired-zone-final.json` 随后终态 PASS：33 个区域场景严格对等，10 个负向变异全部拒绝。该结果仍针对已拒绝的 160ad325… 候选；它未包含本次独立跨技能连续复用链，不能覆盖 S1-R1 的实际失败。修复方案另见 `S1-plan-amendment-legacy-slots.md`，新源码/新图须单独复审。

## 4. 性能事实与非阻塞说明

已实际窄回放确认：

- 单源稳定采样表达式 37,574 → 21,272；脉冲采样 43,538 → 27,236。
- 第十三人换入并重排：表达式 36,330 → 24,050，解释器源行扫描 195,249 → 130,697。
- 首次 scheduler 覆盖采样表达式 25,926 → 28,970，增加约 11.7%，必须披露。
- 原攻击入场至建 cast 整条路径的 1/2/10/40 源及混合场景表达式/源行计数相同（`admission-counts.json`），不能把首覆盖采样混称创建峰值。
- 40 源夹具是合法四路各十宿主，同一次 scheduler 处理四十个 cast；每路 52 候选/12 覆盖，单目标至多十源，并非四十源叠在同一目标。
- 固定数组 dispatch、交集匹配与重排都在表达式计数内，但这些是解释器工作代理，不是 Warcraft opcode、帧时间或 FPS。

## 5. 实机边界及交付决定

未启动或操控 Warcraft III；真实 native 枚举、浮点、timer 投递、渲染、多人同步和帧时间未实测。按项目规则这本身不阻塞离线交付，也不能用来声称没有卡顿。

**当前阻塞是已在实际打包代码回放中确认的玩法差异。此候选不可交付，须修复 S1-R1 并通过新图 Astra 复审。**
