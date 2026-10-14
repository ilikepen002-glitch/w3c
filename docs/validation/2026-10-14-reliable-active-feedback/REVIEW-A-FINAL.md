# A 批最终只读审查：PASS WITH NOTES

审查时间：2026-10-14 02:32 UTC。未发现阻塞项；可冻结本候选产物。范围仅为狂热/蓄力持续塔身反馈、其共享视觉预算与重试、两件配套模型和独立的只读 dropdiag。B 的 20 元素核心化不在本结论中。

## 锁定对象

- 编译源码：`347dab20329e7c967564f49457ccebd948827464`。
- A 树：`/workspace/scratch/2106c0ab1fac/active-feedback-integration-20261014`。
- 实际 `ExampleMap.w3x` SHA-256：`05746604cc6cc7108d95619cd6538fa508d97db18dabb4aed184d125ed56d504`。
- packed JASS SHA-256：`a87b49da4c08c2bd73c514a423e49ce41002e73c60d01c7b8757593532466186`。
- 官方完整 checks/build：`_build/linux-hs0aqx3u/manifest.json`、`_build/linux-ga5x3d55/manifest.json` 均 PASS。已核对源码 HEAD、1507 项输入清单、变更输入哈希和产物哈希一致。
- 后续 `e9322da`、`b6626cd` 仅修改 Python 门禁；未变更生产编译输入或本图。最终提交可另外收录地图和证据，必须保持上述图哈希。

## 实际核验结果

1. 生命周期与预算：40 核心 + 88 装饰仍属于原 128 存量；40 核心 + 80 装饰创建仍属于原 120/秒。无新每塔 timer。成功原生创建前保留 desired；失败释放存量但不退创建票，原 tick 以 0.25 秒期限重试；同技能续期无重建，跨技能立即清旧；有效期、失效和解绑清理不延后。
2. 已查看最终 packed 嵌套分支：先判断 retryAt，再判断缺图/模型变化，旧编译器混合 and/or 降级问题已消除。旧 c7b7e81d… 地图仍为拒绝版本，不能替代本图。
3. 两件资源实际 MPQ 字节与输入一致，独立重生成并经锁定 parser 重解析复现。Stand 起始即显且循环；Death 透明；网格几何位于 origin 上方塔身高度。Frenzy 152 三角、Charge 176 三角，各 2 材质，无粒子、事件或马甲；既有 Atlas 字节不变。详见 `A-packed-resources-r2.json` 和项目 `resources-r2.json`。
4. FourSlot、CombatVisual、ElementalVfx 完整门禁通过。All22 对正式基线 22 技能 × 12 模式 × 131 帧，共 34,584 状态快照及完整有序战斗轨迹相同；覆盖伤害、目标、控制、冷却、随机和收益边界。报告 `all22-compact.json` 保留完整报告哈希。
5. Retention 的已注册 15 组全部获得通过证据，属于同图的穷尽组合覆盖，不是声称原整次执行成功。原 `retention.log` 前 10 生命周期组及 coreAdmission/buffAdmission 已通过，随后 retry 夹具因同时消耗存量与当秒创建票而失败；修正只改变 `verify_buff_retry`，重跑四组 admission 全通过；另一修正只改变实际 packed 调用的 mutation 锚点，19 个负向全部拒绝。独立 AST 比对确认只有这两函数改变；原前序函数、生产 JASS 和图未变。组合覆盖恰好等于 15 个注册组，无缺组。应保留原 FAIL 日志与两份 `completeGate:false` 分组报告。机器可核对摘要见 `A-retention-coverage-review.json`。
6. 重试五场景含独立 null/存量/速率、存量与速率组合、连续每 0.05 秒回调。连续组合场景在 21.00 仍待定，到 retryAt=21.10 才恢复；稀疏回调在 21.00 恢复。原有效截止时间不被推迟；续期无创建，跨技能清旧与 9 类取消条件通过。
7. dropdiag 源码仅观察原流程；实际同图 15 生命周期场景和 4 负向通过。默认关闭、输出与定时观察有上限，无玩法搬移或新订单。该诊断不等于已修复玩家实际丢物位置。

## 非阻塞说明与声明边界

- 已证明资源可解析、循环、引用与预算/生命周期正确；尚未在 Warcraft 原生引擎核验所有塔的附件贴合、遮挡、混合、出生动画选择或实际帧率。不得以句柄存在代替原生可见性/FPS 验收。
- 固定 40 塔同轮正常创建不会被装饰吞掉；原生返回 null、同秒反复换宠超 40 次尝试，仍可能暂缺图。失败受限重试只在真实有效期内发生；不承诺满负载保留所有装饰。
- `buffVisualModelsAreDistinctAndUseClassicAssets` 测试名称过时，不影响实际断言及资源核验，可日后改名。
- 本次没有新伤害、冷却或随机机制的授权，审查未发现这些机制变更；B 必须独立完成最终实际产物审查。

## 证据索引

- 门禁原始输出：`/workspace/shared/spirit-feedback-a-python-r2-20261014/`。
- 项目归档：`docs/validation/2026-10-14-reliable-active-feedback/`。
- 本审查目录：`/workspace/shared/active-feedback-plan-20261014/`。

本结论限于上列源码/地图与核验边界；不是原生游戏画面实测认证。
