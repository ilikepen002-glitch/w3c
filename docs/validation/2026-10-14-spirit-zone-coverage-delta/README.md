# S1 持续区域减速覆盖差量验证（2026-10-14 UTC）

**最终结论：Astra REVIEW `PASS WITH NOTES`，仅批准 e5fb76ea 修复图。**

风险为高风险覆盖/引用/贡献生命周期改动；实际流程为 GPT-6 Astra PLAN → GPT-6.1 Sol 实施 → Astra REVIEW，首轮真实跨技能回归 FAIL 后再按 Astra 定向 PLAN 修订修复并复审。A1/C1 与 HUD/D2 已从 `8b941e84eb392514a6c96434b3fdc1d6c11d9d7d` 集成，未覆盖前批。生产最终变更 `872e5b40b950714059cf70a2967af321f2074b40`，构图/最终验证源码 `d6f4c7000cc674fd9f30186f8d2a395d94107f8f`。本次冻结提交仅更新根地图与验证文档，未追加生产改变。

## 产物与范围

- 根 `ExampleMap.w3x` 是官方修复构图逐字节副本，SHA-256 `e5fb76ea50517db2d624639133e3d20688c7509845cfcb48dfdae9777d06d810`。
- 实际 packed JASS SHA-256 `177a6f48a6edec60ad4898534c0588111d12ae9497dbb41e8fd42935db95573b`。
- 对照图 SHA-256 `c57d8d6b01818f1e77b90317ac7aa5ee630eccc9e76ef1ac5f7f16f96f09b720`，JASS `06db07c8082d148a7c73068dc041cf1c1101b34a6d00de8c3bc8b875d2abdbd2`。
- 对照图已保存在 `/workspace/shared/performance-hud-diff-20261014/ExampleMap.w3x` 和 HUD 原证据目录。历史报告中的本树根 `ExampleMap.w3x` 是当时对照位置，现已换最终图；重跑应使用保留对照路径并核 SHA，不能再把当前根图当基线。
- 原完整 PLAN SHA-256 `86a57b712298614060becee60630167a630970a03631863387713accb588197f`；必要 legacy 修订见 `S1-plan-amendment-legacy-slots.md`。

仅优化原每 0.25 秒采样的 <=12 覆盖集合。交集按 unit/revision/未 retired position/**实际 Boss 调整后的 offer power** 判定，仍执行原完整 offer/refresh 和封域 token 续期；离开只撤本来源/identity/token并释放引用；当前枚举次序准确重排六组 zone-owned 字段。`hitCounts`、`controlled` 属其它技能的 legacy 物理槽，zone 整个周期保持原槽值不动。伤害仍在原偶数 stage 后、原 0.5 秒时钟及 4 秒端点执行。没有自动技能错峰、scheduler/队列/CD/规则数值/目标上限/伤害顺序/叠加规则改动；未合并 A2 cap 早退或 S2 聚合快路。

## 已完成门禁

所有终态均对应 e5fb 新图，未复用被否决图的通过证书。

1. 官方 Linux 入口串行执行定向 typecheck、完整 Wurst tests、完整 build，均 PASS，无 Wurst warning。事务分别 `linux-5lm_7i8_`、`linux-528rh545`、`linux-9wqv3sao`；三个日志随本包保存，manifest SHA/固定编译器/stdlib见 `source-freeze.json`。构图原生 allocator、主动 CD、精灵 startup、全 startup/import 407 等原门禁 PASS。
2. 主门禁 **41 场景 exact paired /14 实际 packed mutants 全拒绝**：单/2/10/40 同强与异强源、强源离开弱源回落/expiry、13 人换入/反序、同句柄退休/复活与 revision 换代、原生 Boss 类型动态变化、机械/异路/试炼、真实机关怪封域减抗、保留 offer 修复 native carrier、pulse 重入死亡/remove/move/recall/generation、owner/lane/epoch/试炼/游戏结束取消、ID复用、同host旧generation admission、自然结束。
3. 每次有序伤害时钟及原五玩法参数、DamageInstance/event/flags、命令时钟/目标、CD/stage/nextAt/expiry、score/RNG、速度/ability/timed行、弱化 source/token/expiry 精确对照。仅按明确签名断言排除末尾编译器 `w__wurst_stackPos` 诊断字符串，未放宽玩法值或时钟。全部清理目标 cast/tasks/position refs/index/timed/weakening/native FX/lightning 最终为零。
4. 专用真实同 Runtime **8 跨技能链**，实际写入 history、真实原 admission、相同 class ID 重用：28→30/37→26、26→30/37→26；全离开/反序、多 zone、recall/invalidate/natural。完整 gameplay trace 一致。四项误清/误 swap legacy hit/control mutants 被真实后继伤害/控制目标拒绝。Astra 独立原反例对新图同样 **4→4 击 PASS**。
5. 原全主动 retention **23 suites/24 lifetimes/80 aborts/26 mutants** PASS（candidate invariants，不称整套paired）；全主动视觉 **22×12=264 exact paired，131状态点/例**；额外 **8技能×2tick次序=16** 首真实turn recall 清理 exact paired PASS。广泛矩阵不能替代第4项 legacy 专门门禁。
6. 集成前批实际新图回归：A1 主动 CD/47 单测、2304 comparator/480 selector、9 target+5 hotpath mutants；HUD155 comparisons、934 evolution kills、13 repairs、17 lifecycle、10终态分支及负测，全部 PASS。明细见三个 `fixed-*-regression-summary.json`。
7. Astra 独立核三份正式 manifest 的 **235 输入**/锁定工具链及 MPQ。427 member/hash，无未知项；425其它成员逐字节相同，只 `war3map.j` 与合法 w3i 构建名/loading title时间变化；物编/rawcode/资源逐字节不变，见 `review-support-fixed.json`。
8. 攻击命中至创建的 admission 1/2/10/40 同强及2/10/40异强完整实际表达式/源码扫描计数不变。严格真实 recall/析构 1/10/40 各3种技能共9个窗口 PASS，下面准确披露增量。

## 性能与成本披露

这是实际解释器 `evaluate` 表达式次数，包含 Wurst fixed array 展开、group复制、匹配/重排等完整当前调用工作；不是 JASS opcode、CPU、FPS。另列的 `interpreter_source_lines` 包括解释器 inactive 扫描，不能等同执行成本。完整逐场景/逐stage计数与 native节点在 `paired-zone-summary.json`。

| 场景 | 首覆盖 expressions 原→新 | 稳态 原→新 | pulse 原→新 |
|---|---:|---:|---:|
| 单源 | 25926→28970 | 37574→21272 | 43538→27236 |
| 10 同强源 | 198384→228824 | 355172→245372 | 416246→306446 |
| 40 总同强源 | 790080→911840 | 1417232→978032 | 1665904→1226704 |
| 40 总异强源 | 835384→957144 | 1477192→1009752 | 1604136→1136696 |
| 真实机关怪封域2源 | 45052→51140 | 61308→44384 | 61308→44384 |

- 单源首覆盖 +11.74%；稳态 -43.39%，pulse -37.44%。13人换入并反序 **36330→23626**，源码扫描 **195249→128193**；单源首/稳态/pulse扫描依次 **133185→145881 /196929→110229 /215412→128712**。所有其余逐stage扫描保留在摘要，不隐去首次成本。
- 单源稳定覆盖 slow_refresh **24→12**，timed new/destroy 各 **12→0**，position acquire/release 各 **12→0**，常规速度写 **24→0**。多同强重叠速度写原本已0，不能夸大这项收益。相交完整 refresh仍执行。
- 40源是合法 **4路各10宿主**、每路52候选/12覆盖的同scheduler压力，单目标最多10源。refresh **960→480**，timed new/destroy 各 **480→0**。不是40源同目标重叠。实际封域 weakening new/destroy 各 **24→0**，原24次offer/token续期保留。
- Admission全路径表达式原样：40同强 **131045→131045**，40异强 **168321→168321**。

**退出固定成本真实实测**（只包 actual `TDPet_recall`/cancel/析构；所有预/后observer、重复清理、视觉shutdown/recycler都在计数窗口外）。

| 技能 | 1源 expressions 原→新 | 10源 原→新 | 40源 原→新 | 每源增量 |
|---|---:|---:|---:|---:|
| 非zone28 | 550→987 | 4690→9060 | 20428→37908 | +437 |
| zone30 | 16087→16588 | 137378→142388 | 550670→570710 | +501 |
| zone37 | 16268→16769 | 140162→145172 | 555197→575237 | +501 |

共享析构的12槽纯scratch清理有低频、有界增量，包括非zone技能；无新增native分配/调度/伤害，所有立即贡献/ref/task清理及后续native清理相同。40源是实际测量，非乘法外推，完整严格窗口/扫描数在 `recall-costs-legacy-fixed.json`。先前包含recycler的窗口留在原证据中，不用其扫描数声称性能。

## 失败保留、复现和证据索引

首候选 `160ad325…` **仍为 FAIL，不可交付**。它把其它技能遗留hit/control槽跟victim移动或清零；Astra真实28→30→26链使末26从4击变12击，每击70。修复不重置init/remember，不加备份state，仅让zone不写其不拥有的legacy槽，原行为有意保持。拒绝审查及原/修复独立反例JSON随包保存，广泛矩阵局部PASS不能覆盖这项FAIL。

`evidence-index.json` 给保留外部目录内每个原始报告/日志/脚本/地图 SHA与大小；不复制8.8MB主trace、1.5MB跨技能trace等大文件。精简摘要保留全部case、exact结论、计数、cleanup、mutants及完整报告SHA。首次编译/错误模型断言、诊断参数观察器错误、invalid admission夹具与原FAIL日志均保留，没有抹掉失败或宽容断言。

主门禁可从仓库工具重跑（原锁定环境，明确对照路径）：

```sh
python3 tools/VerifyZoneCoverageArtifact.py --help
# baseline 必须选上述保留 c57d8d6 图，candidate 为根 e5fb76ea 图。
# 完整原执行参数与辅助observer脚本见 evidence-index 指向的原日志/脚本。
```

**未启动或操控 Warcraft III**。真实引擎枚举、浮点、timer投递、渲染、多人同步、帧时间尚未实测；不承诺所有路径变快或不卡顿。首覆盖/退出增量及以上实机边界是 Astra 接受的非阻塞备注。
