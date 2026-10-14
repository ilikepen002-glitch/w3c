# HUD / 进化展示差异提交

## 范围与产物

本批在已冻结 A1/C1 `2fc31f1fc7d995c97b9b6f330da42f8f5723126b` 上集成 D1/D2，属于现有呈现职责内的普通改动。保留用户新增设计文档。

- D1 只缓存三段 HUD 的最终同步文本、图标、style、标题，使用三段平铺 scalar arrays。首次写入与合法空串分开，board identity、section 起始行/行数/列数变化均失效。没有新增 class、timer、调度或跨系统状态。
- 宝宝本地文本保留每次原样 get/set/release，其余同步格才差异提交。零秒合并、1 Hz 请求、kill 请求、终局刷新、伤害目录/排序/Top10、试炼准备/格式化顺序保持。
- D2 只在完整 `tdEvolutionRefresh` 内按 actual ability level/presence 跳过同值写和不存在能力的移除。每次 kill 仍完整 refresh，继续修复外部删状态/action。935级物编、进度、资格与时间未改。
- 首批 A1/C1 的生产改动一并保留；没有主动错峰、限频、伤害/攻击/玩法规则变化。

最终根地图 `ExampleMap.w3x` 已从独立构建产物逐字节复制：

- 显示名：契灵守卫战 20261014-1942-UTC+8
- map SHA-256：`c57d8d6b01818f1e77b90317ac7aa5ee630eccc9e76ef1ac5f7f16f96f09b720`
- packed JASS SHA-256：`06db07c8082d148a7c73068dc041cf1c1101b34a6d00de8c3bc8b875d2abdbd2`
- 独立地图：`/workspace/shared/performance-hud-diff-evidence-20261014/hud-evolution-flat.w3x`
- 对照首批地图 SHA：`d84f03d19c4e026c85968e4de9a9cf3057d0ff7ad4471aa4f1155a6bad450d43`
- 严格 MPQ 差分：427 个成员相同，仅 `war3map.j` 与合法构建时间戳 `war3map.w3i` 变化；归一化时间戳后 W3I 一致，其余物编/资源逐字节相同。官方构建检查407个imports。

## D1 实际 packed 对照

两份真实 MPQ 提取 JASS，未补丁旧图冒充候选。localPlayer=0/1/2/3/15，各31个连续场景，共155次完整 board 最终内容与旧的全量刷新相同。每种本地视角的 multiboard handle/native 调用骨架完全一致，仅已有的本地最终文字可以不同。

覆盖单格生命变化、标题/图标/style独立变化、空字符串首次写、排行并列/退场/Top10和尾行清空、宝宝详情/仅P1变更/过期详情/旁观、试炼倒计时/退出/结算/清空、1↔4路线布局、替换board、死亡败退和胜利终局。原四路宝宝摘要、catalog、refreshOrder、sortWith和trial准备调用顺序逐次对照一致。

| 场景 | multiboard natives | 实际求值表达式入口 | 解释器扫描步骤 |
| --- | --- | --- | --- |
| 单路首次 | 328 → 328 | 3038 → 5625 | 5618 → 8132 |
| 单路相同状态第二刷 | 328 → 3 | 3038 → 2430 | 5618 → 4638 |
| 单路仅生命一格变 | 328 → 6 | 3038 → 2445 | 5618 → 4658 |
| 四路布局首刷 | 355 → 355 | 3421 → 6089 | 6398 → 8999 |
| 四路相同状态第二刷 | 355 → 3 | 3421 → 2759 | 6398 → 5325 |
| 四路榜单相同状态 | 355 → 3 | 3935 → 3273 | 7247 → 6174 |
| 试炼相同状态 | 355 → 3 | 6428 → 5766 | 16137 → 15064 |

首次/布局失效刷新需要初始化缓存，所以首刷表达式成本增加，不能声称所有刷新都更便宜。稳态除了3次宝宝格 native，还降低了实际求值表达式入口与解释器扫描数。固定3次写及表达式减少均由最终gate断言。

解释器扫描步骤包含 inactive 分支的读取；新增的实际求值表达式入口指标只计真正进入求值的表达式。两者都不是 Warcraft opcode、CPU 毫秒或 FPS。字符串/目录/排序并未省略。LinkedList 存储/排序为明示模型边界，排序使用真实 packed comparator；native计数和最终UI模型不证明引擎渲染/多人同步实际表现。

负向变异把宝宝格改用本地dirty缓存，完整执行后在P1单独详情变化时检出不同客户端handle调用骨架；未将解释器异常算作检出。

## D2 实际 packed 对照

934次同塔击杀逐次最终 ability/资格/进化状态完全一致：

- SetUnitAbilityLevel：1868 → 934，恰好保留934次A130精确进度变化
- UnitRemoveAbility：934 → 0
- GetUnitAbilityLevel：1868 → 2802（新增实际presence读取，未隐瞒）
- 上述 ability native 总数：4670 → 3736
- 每kill解释器扫描：230 → 247；这里不宣称脚本求值也减少

13个actual状态修复场景通过：未资格时缺/错status、缺progress、多余choose；资格后缺choose、多余status；work/finished切换及缺status；进化后缺status；本路已用后另一塔错status。移除每kill完整refresh的actual-packed变异被修复断言检出。

最终地图运行既有完整进化replay也通过：四路独立资格/真实Boss结算、5种关闭路线、确认/取消/旧票据、17种生命周期、935次kill-only、10条终阶分支、宿主绑定/readyAt不变、翅膀一次性及nonce负向变异。

## 检查与保留失败

1. 初版集成完整官方 `Run-WurstLinux.py checks` PASS：typecheck + 全部Wurst测试。
2. 实际packed揭露初版class array[64]会编译成64路访问树，虽然native/等价/负测通过，仍主动拒绝该候选。旧图 `12228767…56ef` 仅留外部诊断，不交付。旧扫描数不当作真实opcode。
3. 改为平铺global scalar arrays，新增section隔离测试；官方定向 `test TDHudProjectionTests` 全部通过，官方build PASS。最终233个 `.wurst` 输入与这两个成功事务逐字节一致；与首次full checks的5个不同Wurst文件及其精准重验关系记录在validation-summary.json，未声称旧full checks直接覆盖修改后的helper。
4. 最终build通过JASS1.28、154 allocator gate、实际MPQ主动冷却合同、pet/game startup/HUD生命周期、对象表/imports/显示名门禁。工具链、锁、依赖和生成JASS未手改。
5. 初版probe开发的helper名字与继承fixture冲突、缺sortWith模型错误日志保留在外部证据目录。这些是fixture问题，未当作地图bug。
6. 最终HUD fixture显式运行新增projection package initializer，避免把所有section常量的默认0误作生产启动。

完整旧/新日志、manifest、两代候选图和失败均保留于 `/workspace/shared/performance-hud-diff-evidence-20261014` 和validation-summary.json所指事务。父线程将终态事务的重复assets恢复信息归档，不影响source/log/map/JASS/manifest。

未推送、未部署、未启动Warcraft。提交与发布由父线程处理。

## 复现

```text
python3 tools/VerifyHudProjectionReplay.py --baseline-map <首批final.w3x> --candidate-map ExampleMap.w3x --output <hud.json>
python3 tools/VerifyEvolutionProjectionReplay.py --baseline-map <首批final.w3x> --candidate-map ExampleMap.w3x --output <evolution.json>
python3 tools/VerifyTowerEvolutionReplay.py ExampleMap.w3x --output <evolution-regression.json>
```
