# Astra 定向 PLAN 修订：区域未拥有的 legacy 槽保持不动

日期：2026-10-14 UTC。模型：GPT-6 Astra。状态：**批准下述最小实施方案；尚非修复完成或 REVIEW 通过。**

依据：`astra-review.md` 的 S1-R1 及 `review-cross-skill-reuse.json`。当前实际候选 160ad325… 因 28→30→26 同 class ID 复用产生 4→12 击，仍为 FAIL。

## 1. 字段职责与等价条件

实际调用图中，zone 只用于技能 30/37。二者不消费 `hitCounts` 或 `controlled`：

- `hitCounts` 的有效消费者是 line（19/28）、segment（26/38）和 fireChain（34）。
- `controlled` 的消费者是 segment 的 roots 路径；区域没有使用该标记。
- 旧 zone 的覆盖离开/重采样均不写这两组字段。
- 编译后的构造初始化与 `remember` 不清这两组固定数组，故它们按物理槽保留的旧值会被后继复用 class ID 的技能观察。不能视为区域受害者记录中的合法 per-target 状态。

因此，原 PLAN 的“全部平行字段成组移动”需收窄为“**该 zone 实际拥有并使用的目标记录字段**成组移动”。`hitCounts`/`controlled` 在整个 zone 生命周期内按物理槽原封不动，才能与原实现对等。这是修正错误的字段所有权假设，不是改变旧技能规则。

## 2. Sol 最小改动

1. 将仅被 zone 使用的 `swapVictimSlots` 明确命名为 `swapZoneVictimSlots`，避免给其它技能误用的泛型含义。
2. helper 只成组交换：`victims`、`revisions`、`targetPositions`、`lastPositionX`、`lastPositionY`、`zoneSlowPowers`。
3. 从该 helper 删除所有 `hitCounts`/`controlled` 的读取与写入。
4. `forgetZoneVictim` 保留先撤销 ownership、清 zone-owned 尾槽、移除原 source/identity 与本 weakening token、release 位置引用的现有次序；删除 `hitCounts`/`controlled` 的清零。
5. 写清代码注释：30/37 不拥有 legacy 计数/控制数组；旧实现留下的物理槽值须跨 class ID 生命周期保持，以免改变后继技能。
6. 不新增备份数组或捕获/恢复状态，不改变构造初始化、remember、其它技能、共享 slow key、scheduler 或时间/伤害/控制规则。

这样无需新增生命周期状态；所有 zone owned 字段仍完整移动。原 `ondestroy` 本身没有清这两组数组，不应添加清零或恢复逻辑。

## 3. 定向验证

### 槽归属用例

修订 `coverage_order`：

- 目标位置引用、revision、last X/Y、zone power 继续按目标一起移动；幸存者引用必须保留，离开/进入只各一次 release/acquire。
- 将 `hitCounts[0..11]` 与 `controlled[0..11]` 作为物理槽 sentinel：反序、同集合置换、部分换入、全离开后，整个向量逐槽与进入 zone 前一致，不再按目标期待搬动。
- 必须验证尾部以及零 victimCount 情况，不能只看当前有效覆盖槽。

### 连续同 Runtime 的真实技能链

保留所有原命中、金额、目标、时钟、控制命令、CD、身份与最终引用归零比较。

1. 必须复用独立审查的实际 `28 → 30 → 26` 全离开链，三次真实 class ID 相同；修复后末段保持基线的 4 击，不能把基线清成 12 击。
2. 同样覆盖 `28 → 37 → 26`，以及至少一个 zone 覆盖集合不变、仅反序/置换后结束的链。需要精确比较目标顺序，不能只比伤害总数。
3. 至少一个多 zone 链，如 `28 → 30 → 37 → 26`，所有类 ID 真正复用；不写 legacy 值，初始计数必须由原技能真实执行产生。
4. 实际根须技能 26 先产生 `controlled` 标记，经过 30/37 的换入/离开或反序，再复用 ID 执行 26。比较完整控制目标/命令/时刻；成功数相同但目标不同也必须失败。安排足够原生时钟使既有控制保护窗不掩盖标记差异。
5. 覆盖 zone 自然结束和 recall/invalid-cancel 至少两类退出路径；后继 38/34 可增加窄用例，但无需机械展开全部组合。重点是消费者先读旧槽的实际路径。

### 负向与性能门禁

- 将误清或误交换 legacy hitCounts/controlled 重新注入实际候选 JASS 的窄变异，至少一个真实跨技能链须明确拒绝；不能只依赖改过预期的 sentinel 检查。
- 保留现有 33 场景与 10 个负向变异；因 helper 改名，更新定位只允许对应名称，不放宽原断言。
- 重新量首覆盖、steady、pulse、重排以及原攻击入场路径；固定槽 helper 成本要计入，不许只报 slow_refresh。
- 正式定向 typecheck、完整 tests、实际构图；新图的 zone paired 与跨技能链必须对等。共享析构/主动整体验证按影响复用或重跑：源/图已变则对新图重新执行相关 gate，不能把旧地图 PASS 当新图证书。
- 新实际地图由 Astra 复审后才可交付；先前全部失败证据保留。

## 4. 不接受的替代方案

- 全 init/remember 清零 legacy 字段，借优化修复其它技能旧行为。
- 仅删 forget 的 clear，却继续在 swap 搬动 legacy 槽。
- 把基线 fixture 清零、重新创建 Runtime，或只比较总伤害以藏掉跨代/目标差异。
- 通过技能错峰、延迟、改变伤害跳数或控制规则避开生命周期问题。
