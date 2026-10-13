# 运行时热点优化与验证边界

## 已实现的局部变化

- `TDAuraRuntime` 每次目标刷新，在原来的 `try` 内读取目标路线、位置、机械属性和冷却资格，然后传给每个光环源。没有新增跨 tick 缓存。冷却资格仅对塔计算。逐目标 Execute/try、源扫描顺序、prepared 提交、buff 修复重试、各类光环的 inclusive 距离条件保持原样。
- `TDEquipmentCombat` 以 `Table` 维护 unit handle → 现有 debuff 记录索引，链表继续负责稳定 tick 顺序。记录析构统一清除属于自己的索引，再移除护甲技能并释放单位引用；显式 forget、过期、目标失效、试炼清理都进入原来的析构路径。攻击已验证目标后，将同一 entry 和 now 交给内部护甲函数；公共护甲入口继续独立验证。
- `TDTowerRuntime` 先计算候选分裂箭飞行时间，只在列表未满或严格小于最远候选时创建 shot 和捕获试炼上下文。相等时仍保留先进入的候选。选中 shot 的销毁继续归 volley 所有，被替换 shot 立即销毁。

## 可确定的工作量变化

这里的收益是源码/成品执行次数，未测量 FPS。

设单次光环刷新遇到 S 个有效同路线塔源，源携带 C 个冷却光环装备：目标位置读取从 S 次变为 1 次，路线读取从每个有效塔源一次变为 1 次；敌人的机械属性从 S 次变为 1 次；塔的冷却资格扫描从 C 次变为 1 次，敌人的冷却资格扫描为 0 次。源遍历仍为 O(S)，每 tick 仍最多处理 16 个目标。没有冷却光环源时，塔目标现在也会计算一次冷却资格，这是局部快照的固定成本。

设有 N 条装备 debuff：攻击查询从 O(N) 链表查找变为 O(1) Table 查询；有护甲效果时，原来的第二次查询和第二次时钟读取被消除。tick 仍为 O(N)；显式 forget 的索引定位为 O(1)，但原 LinkedList.remove 仍为 O(N)，不能宣称整个 forget 为常数复杂度。

设分裂箭枚举 M 个有效候选，K 个最终目标，R 次替换：shot 分配与试炼上下文捕获从 M 次变为 K + R 次，拒绝候选为 0 次分配。最远目标扫描仍保持原来的 O(MK)，本轮没有增加排序或堆。

## 自动验证

`tests/python/test_runtime_hotpath_replay.py` 包含目标局部快照/公共入口的源码约束，以及实际成品 JASS 回放。回放复用现有 TrialJassRuntime，保留真实生产函数、构造、析构、身份验证和试炼清理；Table、LinkedList、单位能力和时钟为显式 native 边界。

```powershell
$env:HOTPATH_CANDIDATE_MAP = (Resolve-Path ExampleMap.w3x).Path
python -m unittest discover -s tests/python -p test_runtime_hotpath_replay.py -v
```

成品回放覆盖重复查找不创建多条记录、显式清理、重复/null forget、句柄数值重用、护甲精确到期、目标死亡、试炼 binding 清理，以及分裂箭空/未满/拒绝/同距/替换/volley 统一销毁。未提供新候选图时，成品测试明确 Skip，不作为通过证明。

2026-10-13 对冻结候选 `C:/Users/huawei/AppData/Local/Temp/wurst-legacy-hotpath-candidate.w3x`（SHA256 `F9A1B43CD8CF447FA3888B46D976BF0CFAC92E0A6B1C6B222EF4E758EE230D2B`）运行上述命令：4 项成品回放、2 项源码约束全部 PASS，共 6 项，10.848 秒。日志为 `C:/Users/huawei/AppData/Local/Temp/hotpath-replay-candidate.log`。重复查找 101 次仅创建 1 条记录、没有链表迭代；2 个入选加 1 次替换共创建 3 条 shot，两个被拒绝候选不创建 shot，volley 销毁后累计实际执行 3 次 shot 析构。

回放补充了 stdlib 非空链表销毁的 native 边界：list 节点销毁允许值仍在列表内，值本身的 shot/volley 析构仍执行成品生产 JASS，没有 mock 被测业务。统一 Wurst 检查、地图构建及最终发布图与冻结候选的脚本等价性由主代理串行验证并记录。

既有 `TDAuraTests` 和 `VerifyEquipmentCombatReplay.py` 继续承担光环排名、叠加上限、buff 重试以及真实试炼范围/修订语义的回归。没有启动游戏；原生 buff 显示、真实定时精度与 FPS 保留为未验证边界。

## 后续候选

定向检查还发现 TDSpawn 每 0.20 秒 waypoint 世界枚举、每路波清理每 0.40 秒世界枚举，以及 special 每 0.10 秒对每个塔重复 inventory scan。运行参数开启 stacktraces，inline/localOpt 关闭。它们属于待测量候选，不能仅凭频率判断真实瓶颈；本轮未改调度、世界枚举契约或诊断选项。
