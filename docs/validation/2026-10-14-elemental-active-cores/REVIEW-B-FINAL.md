# B 批最终只读审查：PASS WITH NOTES

时间：2026-10-14 02:55 UTC。结论：无剩余阻塞，可冻结下列候选图。高风险范围为20元素主动的核心/装饰分类、CastContext与视觉Runtime的共同准入/转交/清理协议；已按批准方案核对实际差异和最终同图证据。

## 锁定对象

- B 编译源码 `75202dd6d95eaab986733be5a1a5950822141e80`，审查差异基线 `b453393d9a1d979b88ac06a5572ccd9b176f2eb8`。
- `/workspace/shared/spirit-active-final-integration-20261014/ExampleMap.w3x`
- SHA-256 `c3a50d47b9a5c47677e52ca6cb5bd8081e2f4d792385f8f63a9ba3cef3cb85bc`。
- checks `_build/linux-0d_s6q2q/manifest.json`、build `_build/linux-8guim7ng/manifest.json` 均 PASS。独立核对1539项输入相同、27项B变更输入与实际源哈希一致、产物哈希一致。后续纯 Python 夹具改动不改变本图。

- 最终门禁提交 `0f7e49a`（前置 `5927413`）；最终diff除地图产物和文档外仅Python验证工具变化。已读项目最终证据README，23组分组合成及复用/原生未测边界描述准确。

## 已核对实现

- `TDPetCastContext.wurst:194–292`：每施法一个核心 point/line，pending 占原8槽之一；原生成功才持有40核心类别的存量。null消耗创建票但释放存量；原调度内0.25秒重试，不添加timer或敌人枚举；过期、无效或取消不迟播。
- 同技能核心line通过 MoveLightningEx 随真实阶段更新，不逐帧新建。point仅实际模式/模型/地面位置改变才替换；跨状态旧图先清，不假装仍有效。
- `TDPetActiveVisuals.wurst:309–319`：挂目标的core失效即清；24寄种转为最后记录位置的ground core，真实Spread也切相同ground状态；原生失败仍保留可重试新期望，不重新选敌。死亡后首次成功寄种直接ground，避免先挂死目标再重建多耗票。
- `retainVisualCore` 再查同步终击后的primary有效性；同一个native通过 `tdCombatVisualDemoteCore` 转装饰，不增加创建票。88装饰满就销毁释放核心；转交失败释放装饰类别。旧尾迹不挤占下一轮40核心。
- `TDCombatVisualRuntime.wurst:221`、`:612` 新增受限降级与已有line转交；没有新伤害、技能调度、冷却或随机入口。Direct/Periodic/Runtime三个战斗文件与基线逐字节相同。
- 29/33采用中性loop领域，不在MDX中预埋冻结或撞击结算时序；真实Freeze/IceBreak/MeteorImpact回调才加阶段装饰，避免越过真实phase fence。
- 最终packed重查过retry嵌套条件、point模式切换、目标失效、postmortem seed和demote/adopt分支，未发现源码与实际packed协议不一致。

## 已核对资源和前批复用

- 7件新MDX800 + 新白BLP实际MPQ与manifest/source导出一致；独立复制生成器后重生成并用锁定parser复现。Loop开始即显，Stand循环，Death透明；mesh-only，无粒子/事件/马甲，2材质/2骨骼。几何范围受真实技能半径约束。已查看两张实际contact sheet，不等于原生游戏镜头验收。
- all15动作前批已由root批准、门禁在9f8a2a52…图完成。独立比较9f8→c3，15MDX/15BLP逐字节不变，TDPetDisplayRuntime/Rules与b453393逐字节不变。可复用该前批证据，不能写成525组合等在c3重新执行。见 `B-all15-reuse-proof.json`。
- 当前c3 All22：264案全部identical且每案131帧；完整报告SHA-256 `4d959a62721cb525bd708182a69ff6e403c95c8d6a4bbbfdc05d53e61a41d96a`。ElementalVfx也已通过。

## 实际门禁与覆盖结论

- B Retention最终动态注册23组全部获得通过证据；独立核对注册列表与证据并集恰好一致，无缺组。记录于 `B-retention-coverage-review.json`。这是同一生产图上的穷尽分组合成，不是一次完整最终工具运行通过。原admission失败日志保留，复用其失败前已完成的7组；独立AST比对这7个suite函数与26a6b5f相同。
- 核心压力最终 `core-overlap-root-r3.json`：40个合法来源、20元素、两种调度序都同秒拥有40核心，存量峰值core40/decor80/shared120；实际逐秒创建不超过总120、core40、decor80，最终任务/引用/索引归零，Fx池仍48。实际资源合同上限仍为128，并未因本场景仅达到120而改小。
- 共享目标位置使用生产引用计数。旧observer错误要求任一context析构就全局归零；最终observer快照Counter并严格检查每个context只释放自己的份额，单/双Vortex共享真实正例通过，40混合结束所有refs=0及positions索引空。没有改生产引用计数。
- 最终 `retention-mutations-root-r3.json` 实际26负向全部拒绝，含缺release精确delta错误、重复release的完整目标位置类invalid-object错误。没有泛化接受任意异常或提高解释器10000语句上限。该报告与最终核心压力的gate SHA-256同为 `4e059f5246c2b97d8106fddd9d4ae357491810c25f0eea9be1275848e13ed28b`。
- `remaining-lifecycle-root.json`实际验证15种目标核心退役情形、point/line降级后转交失败、死后首次寄种normal/null路径，以及21/31真实首阶段后的4种target-loss调度组合。旧开局target-loss继续保留；错误blanket-terminal被负向拒绝。
- 所有报告的图SHA均为上述c3候选。修复项只在Python夹具/observer：四路空间隔离、共享引用归属、晚期abort覆盖、packed调用/精确错误锚点；没有更改已编译的B源码或地图。
- 原先日志中的失败必须如实保留：错误四路重叠触发有限目标扫描的解释器上限；目标共享引用误断言；重复release被正确拒绝但错误字符串未匹配。它们已各以针对性证据闭环，不能改写原执行结果为PASS。
- 前序复用报告使用原observer；不能宣称整个工具逐字节不变或这些组以最终observer重跑。最终共享引用规则由单/双正例、40压力及漏放/双放负向实际覆盖，故本审查接受分组合成。

## 最终交付须保留的非阻塞边界

- 128/120是原受控短视觉预算，不是全引擎永久单位/展示模型总数；40/88与40/80不承诺无限native成功或满载保留全部装饰。
- 短施法在创建票恢复前已真实结束时不能迟播。以正常原生创建、固定40塔阵容的首轮核心呈现作为可靠性保证；null和合法同秒超额变更仍可暂时缺图。
- 原生Warcraft挂点、地形遮挡、内置模型出生/loop呈现、实际镜头辨识度和FPS未实测。线芯在装饰饱和时是过程的低成本摘要，不等于仍保留所有爆点/花朵/飞行体。
- 死后初次寄种分支仍有一件可降级MoonWell装饰与ground core同位；非阻塞的可选优化，不为此改变冻结生产图。

## 证据位置与冻结要求

- 实际报告：`/workspace/shared/spirit-feedback-b-python-20261014/`。
- 独立资源/input核验：`B-packed-initial.json`、`B-all15-reuse-proof.json`、`asset-review-b/`。
- 官方最终packed JASS SHA-256：`1f18e8034415ffca77f4b5741f0488fe2472a4be666c16d0e3ac29e9415a49c3`。
- 当前最终生产编译源码仍75202dd；后续只收录测试/文档/同哈希地图，不需要重复生产编译。若生产源码、资源或地图哈希改变，本结论不自动覆盖。

未发现越过批准方案、偷偷改变伤害/冷却/随机或扩大视觉总预算的阻塞问题。原生引擎视觉和FPS边界按上述说明披露。
