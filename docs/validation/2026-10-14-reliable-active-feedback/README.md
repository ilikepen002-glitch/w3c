# 狂热、蓄力持续反馈与手动丢装诊断

候选源码：347dab2。最终地图 SHA256：05746604cc6cc7108d95619cd6538fa508d97db18dabb4aed184d125ed56d504。
正式基线：9611f0e；正式基线地图 SHA256：f28f375462e64ea08e159eea88e386582cdcb1e2b3dc448fe979108a40468a13。

## 交付范围
- 狂热使用红色绕身焰环、蓄力使用金白封印；效果存在期间保留，结束清除。
- 原总上限128个视觉句柄、每秒120次创建不增加。其中核心保留40个/每秒40次，其余装饰使用88个/每秒80次。
- 创建失败按已有计时器低频重试；同技能续期不重复创建；换技能立即移除过时效果；解绑、死亡、结束、过期取消待重试请求。
- 本批不包含20种元素主动的后续核心改造，也不改变战斗伤害、目标和冷却。
- 手动丢装诊断默认关闭。游戏中输入 `-dropdiag` 开启，再丢放一次装备并截取诊断文字；再次输入关闭。
- 记录实际单位/物品坐标、悬崖层、可走性、坑道掩码及脚本搬移前后位置。无法读取原生拖放的鼠标目标点，不以此前移动指令冒充。

## 验证
Linux官方checks、build通过，构建摘要见build-summary.json。精确资源差分见resources-r2.json；实际成图诊断生命周期15场景及4个负向变异见dropdiag-r2.json。

资源复现：
```
python3 docs/validation/2026-10-14-reliable-active-feedback/verify_resources.py --map ExampleMap.w3x --baseline-map BASELINE.w3x
python3 tools/VerifyItemDropDiagnosticArtifact.py ExampleMap.w3x
```

实际成图回放使用受控原生桩，不等价于Warcraft III 1.27a引擎渲染、拖放算法或实测FPS。不能据此宣称“丢装跳高台”已修复。40塔正常首轮的核心容量得到保留，但原生创建失败或同秒频繁换装仍需低频重试，过期不补播。

旧候选c7b7e81因锁定编译器对混合and/or括号的降级被拒；已将重试期限判断改为嵌套if，并重新完整检查、构图。不要分发旧候选。

## 最终分组回放证据

同一冻结地图的15个登记检查组已完整覆盖：原347dab2运行在retry夹具失败前明确通过lifetimes、aborts、deliveredTargetDeath及7项lifecycle；其后e9322da隔离夹具的live/rate维度，4项admission定向全通过；b6626cd保留实际packed的stack参数修正负向变异锚点，19个变异全部被拒。这里复用已通过且未改变的检查组，不把原失败运行说成整次通过。原失败日志保留为retention.log；最终分组报告见retention-admission-final.json与retention-mutations-r3.json。

All22：22技能×12模式×131帧的完整有序战斗轨迹均与正式基线相同。FourSlot、CombatVisual、20元素视觉/移动回收也通过。逐帧大报告保留离线；仓库保存精简结果及完整报告哈希，避免为验证记录增加大量重复文本。

复现完整Retention及All22：
```
python3 tools/VerifySpiritActiveRetentionArtifact.py ExampleMap.w3x --output retention-full.json
python3 tools/VerifyAllSpiritActiveVisualTrace.py ExampleMap.w3x --baseline BASELINE.w3x --output all22-full.json
```

Python离线门禁修正不改变构建输入的游戏源码或地图，官方checks/build对应347dab2生产源码复用。两个负向/夹具修改已单独重新执行相应组。
