# 宝宝 DOT 转移与原生升级生命周期诊断

## 范围与夹具

Astra 批准方案，GPT-6.1 Sol 实现。独立 test-only 文件 `tests/wurst/runtime/TDNativePetLifecycleProbe.wurst`，不能进入普通发布；不 import 其他测试包，不修改生产。显式包含此包即 opt-in 自动五场景，启动等待真实 P1 工人最多 10 秒，须单 P1、正常活跃路线、空收藏；每局最多一次。

诊断授予 10000 金币/生命并创建两个 Orc I 宿主及五个暂停普通怪，均只关闭夹具 pathing。预置一只炎灵 Lv1/技能索引 3（灼烧），通过生产 store/deploy 登记及绑定；captureWave=32 阻止自然清波改变夹具技能，仍每 tick 核 Lv1/技能 3。不证明自然捕获或成长，也不是经济、平衡或通关证据。没有直接调用技能伤害处理器、工作开始/结束 helper 或经验接口。

## 五场景

1. 第一个宿主真实普攻击中第一个目标后暂停宿主，观察 Pdam 第 1/2/3 秒各一 tick。
2. 再次真实攻击，首个实际 Pdam 后至少 0.2 秒（0.1 秒 watcher 精度）调用生产 `tdPetDeploy` 转移到第二暂停宿主；代次须变化，旧目标只允许首 tick，后两 tick 必须消失。
3. 冷却自然结束后，第二宿主真实攻击新目标，观察完整三 tick。
4. 第二宿主真实攻击新目标，首 tick 后至少 0.2 秒解除暂停、stop 原攻击并下原生 Orc II 升级订单；必须观察实际 UPGRADE_START 和绑定代次变化，旧 DOT 仅保留首 tick。等待真实 UPGRADE_FINISH，不用返回值或手工 work helper 冒充。
5. 实际完成升级、宠物恢复绑定后，升级宿主再真实攻击新目标，观察完整三 tick。

每场只允许一个原生攻击。记录原生值、Pdam 时间/数量/值、source/target 句柄及宿主 rawcode、绑定 generation 和实际 HP。额外攻击、异源伤害、命中其他夹具/非夹具目标标污染，不能通过。

每场开始前明确将该诊断目标 HP 准备为 maxHP−1000（最低 200），为最长升级窗口保留回血空间；这是夹具准备，不是伤害校正。之后先测 0.25 秒实际回血率，再从原生首击前 HP 到样本结束 HP 对照 `native + Pdam`，容差为 2 + 1%；不在样本中修改 HP。结束时回满或死亡均 INVALID，避免 capped regen 造成错误结论。Pdam 时刻允许 ±0.20 秒。

未产生首击、缺首 tick、生产转移失败、未观察实际升级事件、代次未失效或夹具变级，均 INVALID；实际数量/时间/值/HP 不匹配为 FAIL SAMPLE。独立首击 6 秒、升级 START 3 秒/FINISH 12 秒、整轮 60 秒 watchdog。所有延迟闭包核 epoch，清理只移除本探针宿主/目标与自有宝宝记录；match-owned 已释放宠物按生产生命周期保留至局末，不直接销毁仍可能被旧 DOT 引用的对象。

## 命令与结果保留

- 自动开测，无须逐例聊天；`-pet-life` 可在启动条件满足时请求同一单次入口。
- `-pet-life-snapshot` 输出运行状态及五个场景汇总。
- `-pet-life-detail N`（1–5）输出该场已保存 HP/事件详情。
- `-pet-life-cleanup` 清理夹具并使 epoch 失效，保留已保存汇总/详情；诊断金币/生命不回退。

根代理定向 typecheck exit 0，唯一 `build-and-deploy-test-map.bat` 构建 exit 0。TEST-0454 构建时间 2026-10-10 04:54:49（Asia/Shanghai），根图与部署 SHA256 一致：`21C5E00C4FE09642FEB9FD98B2A06A640F57C7488F0C782A6BCCD86FBA781524`。原生自动五场景全部 **PASS SAMPLE**，见下方；自然成长已有独立 [正常经济样本](2026-10-10-normal-play.md)，不替代本批生命周期和实际 HP 证据。

## TEST-0454 原生结果

人工只输入只读 snapshot 与 detail 4、5，无玩法干扰。实际汇总：

| 场景 | native / Pdam 数量 | 实际 native base | generation | 关键事件 |
| --- | --- | --- | --- | --- |
| 1 基础 DOT | 1 / 3 | 24.324 | 1 → 1 | Pdam 2.919，各 @1/2/3 秒 |
| 2 首 tick 后转移 | 1 / 1 | 22.297 | 1 → 2 | 生产 transfer @1.242 秒；旧目标后两 tick 消失 |
| 3 新宿主再攻击 | 1 / 3 | 22.973 | 2 → 2 | Pdam 2.757，各 @1/2/3 秒 |
| 4 实际升级取消旧 DOT | 1 / 1 | 25.000 | 2 → 3 | 实际 UPGRADE_START，pausedPet=true；实际 FINISH 为 `uO12`（按常量确认字母 O） |
| 5 升级后再攻击 | 1 / 3 | 34.459 | 3 → 3 | Pdam 4.135，各 @1/2/3 秒 |

场景 4 详情：实际 HP 200.990 → 180.998，回血基线 1.500/秒；校正扣血 28.005 对照 native+Pdam 28.000，容差 2.280；`polluted=false timing=true upgradeStart/Finish=true/true`。唯一 Pdam 为 3.000 @1.000 秒，后两 tick 已停止。

场景 5 详情：校正实际扣血 46.863 对照 native+Pdam 46.865，容差 2.469；`polluted=false timing=true`。三次 Pdam 4.135 @1/2/3 秒。截图末 HP 小数辨识存在歧义，不精录该读数，也不以猜测补齐。

探针实际显示 DONE、CLEANED；HUD 球 3、收藏 0、上阵 0、人口 0/4，支持本探针夹具清理完成。原生证据证明已测炎灵 Lv1 灼烧在转移/升级代次变化后终止旧 DOT，以及新宿主/升级完成后能重新触发完整三 tick；不推广为所有物种、技能或异常路径通过。

本批仍不证明自然捕获/成长、正常经济、完整 32 波、多人，以及未测取消/死亡/超时边界。Astra 最终复审 **PASS WITH NOTES**，无新增阻塞。

## 最终普通地图恢复

根代理通过唯一普通构建入口恢复「深渊守望 0500」，exit 0，时间 2026-10-10 05:01:06（Asia/Shanghai）。根目录 `ExampleMap` 与 `Test/深渊守望.w3x` SHA256 一致：`1D70D01BB23A898F168BC648698F6CC7876449ED7AAF90744318A58F653A12A3`。

只读 MPQ 断言通过：JASS 无 `TDNative`、`-pet-life`、`-normal snapshot`、`-pet-skills`、`-equipment-damage`、`-pets fixture`；W3I 无 TEST，包含普通 0500 标题。生产 `TDPetCombat`、`TDEnemyMechanicRuntime` 保留，`wurst/_tests` 不存在。

Warcraft III 进程已退出，Errors 最新 Crash 仍为 2026-10-08 22:30:27，未见本轮新增 Crash。普通 0500 未重新进局；本轮原生证据对应 TEST-0454，产物恢复检查与实机结论分开记录。
