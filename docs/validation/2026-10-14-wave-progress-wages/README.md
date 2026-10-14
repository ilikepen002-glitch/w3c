# 第3批：按已完成波次结算的固定工资

最终地图 SHA-256：`962da70b23e122e08f7ef82f0b5016ebf1c7d99d3373d5a90c64c1b8dd26476e`，6,022,485 字节。第2批冻结基线 `ece2ff5d4673f5a8445c2007786e680c0dd6704c` 与正式第2批 `3b313b89b6d762d376b8a58e180f7082ded73e9a` 的 Git tree 完全相同；基线地图 SHA-256 为 `769baeff14204aaae592224bac48423e950a70f8dbe4e0080200ab8ac4293c17`。

生产实现 `6db4329`，资源输入及退休门禁 `72bca6d`。本次沿用已有 lane/wave claim 和金币结算，属于职责及影响可限定的普通改动；没有新增工资状态、账本、定时器、接口或生命周期。本冻结只提交已验证地图与证据，不推送；正式发布由父任务执行。

## 行为与范围

- 波次 1/4/7/10/13/16/19/22/25/28/31 完成时分别加 60/90/120/150/180/210/240/270/300/330/360；四路各自独立，总计每路 2310。
- 在 `tdHandleWaveFinished` 的原单次结算里先 claim，再与原波奖一次 `tdGainGold` 入账；使用事件原始 wave，拒绝重复、退出、失败、已结束及旧 epoch 回调。原 `tdWaveReward` 方法体与第2批基线逐字相同。
- 删除 A109 工资技能、注册、随机发钱函数、180秒辅助函数、解锁 watcher、对象与工人挂载；原 CDR 其他职责保留。原生正常游玩诊断同步退休旧工资指令，捕获订单匹配本次 MPQ 的 Pcap。
- 未改进化、路线、定向学习逻辑或战斗数值。第2批全部 38 个新增对象保留；所有其他物编字段、资源和地图设置保持精确边界。

## 官方检查与构建

- `checks-manifest.json` / `checks.log`：官方 Linux `checks` 事务 `linux-87ul3dde`，完整 typecheck 与全部 Wurst 测试 PASS。
- `build-manifest.json` / `build.log`：官方 Linux `build` 事务 `linux-qz2u1q8b`，构建、Legacy JASS、CDR、启动门禁和 407 个导入项检查 PASS；输出正是本最终图。
- `provenance.json`：checks、build、当前所有 `.wurst` 输入逐一 SHA-256 相同。build 的所有其他既有输入与当前文件相同，唯一不同是被官方构建替换的 `ExampleMap.w3x`。checks 后增加的原始资源和 Python 退休门禁均已包含在最终 build 输入中；不把它们误称为所有 checks 输入无差异。
- 冻结时无 Grill/Wurst 构建进程；接续交付仅做离线证据核验，无无意义重编译。

## 最终图门禁

- `packed-wages.json`：实际打包 Game/Flow/金币 JASS 的四路32波、重复/延迟、5关闭状态、5非法事件、Boss16存活/淘汰与Boss32失败、真实 clear/leave、旧epoch及原生资源同步通过；错wave、重复入账、退出后入账3个实际JASS变异被同一oracle拒绝。
- `artifact-delta.json`：独立重核 MPQ 成员集合一致；仅 `war3map.j/w3a/w3i/w3u` 改变。A109 是唯一删除对象、无新增对象；每个 Channel Ncl6 订单按锁定 stdlib 序列严格前移一个分配槽。单位仅移除 uabi 中 A109，其余字段精确一致；w3i 仅忽略构建显示名时间戳。
- `directed-regression.json`：当前最终图重放第2批付费事务、0/2/3/4库存、重复确认、两宠争3枚、11生命周期负例、分页/导航/空格、实际 onCommand 与generation旧页拒绝、新页提交；同oracle抓住免费旧随机采用定向、重复付费、残留第2级3个变异。四路32波保底补给、幂等/延迟/关闭与饱和边界也通过。
- 工资图不适用第2批“仅新增38对象”的历史 delta；该旧规则未放宽或伪称重跑。本批工资专用精确 delta 以第2最终图为基线证明38对象及其他字段原样保留，另运行当前完整定向对象门禁。`directed-regression.log` 和 `directed-source.log` 保留原始输出；对应 JSON 去掉 stdout 前缀后保存为有效 JSON。
- `full-ui-artifact.log` / `builder-control-artifact.log`：当前完整 UI、打包资源、20栏两页、固定单级定向对象、严格共享订单族与全局rawcode门禁 PASS；工人9格布局与退休工资按钮检查 PASS。
- `current-tooltip.log` / `current-tooltip-mutations.json`：现行 current40 的1774条提示检查及5个工资/定向付费/取消保留变异全部 PASS。
- `source-tests.log`：工资 Python 4/4 PASS；`builder-tests.log`：16/16 PASS；`cdr-all-tests.log`：完整 CDR 44/44 PASS，覆盖其他职责及工资对象/挂载退休。

## 已知历史测试失败，不声称全 Python 通过

扩展测试额外运行后发现以下失败，已用未修改的第2冻结工作树复现相同错误（`known-failures-directed-baseline.log`）：

- `known-historical-ui-tests.log`：47项中1 error，历史 Pbat fixture 一级值1，而旧契约期望5。
- `known-historical-map-tests.log`：18项中1 failure，历史 evolution gate 的 uO11 旧射程期望不匹配。
- `known-historical-tooltip-tests.log`：legacy72 10项，9 failure + 1 error；预检 A132/1 已不匹配，使多项负变异未能到达各自目标断言。它们不是通过的变异证据。

这是已复现的基线问题，本批不扩修历史 fixture 或改变当前生产数值。正式 Wurst checks、构图、当前物编/UI/Tooltip 与完整 CDR 结果如上分别陈述。

## 被拒绝的资源缺失中间图

第一次构图 `linux-xyxfcrq_` 输出 `d0b1fb5d6476f1cc16e61cba749d8a8baff5bf815949db342876270c0d7c02f6`，被工资精确 delta 以成员集合变化拒绝（`rejected-missing-resource-delta.log`）。缺失的4份 Leoric 原始输入已从第2冻结图恢复并提交，再走官方完整 build 得到最终图。`restored-resource-inputs.json` 和 `artifact-delta.json` 证明这些输入与第2及当前 MPQ 原始字节相同。被拒图不可发布，未计为最终验证通过；原事务与原始外部证据未删。

## 经济和验证边界

首波工资在完成后到账。取消随机墙钟工资会改变后续随机序列；不是旧技能的等价自动化，也不热迁移旧局。全杀累计收入至8/16/24/32波为5900/15450/33000/56400，非剩余余额或漏怪保证收入。

没有启动或控制 Warcraft III，没有部署用户本机。离线重放使用实际生产JASS，原生引擎handle/UI/计时交付受控；不证明游戏内按钮渲染、选择、真实网络排队、加载时间、FPS或实机手感。全图性能审查待当前所有批次完成后另做。
