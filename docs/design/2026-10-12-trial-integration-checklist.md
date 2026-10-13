# 金币试炼生产接线清单

基于 654771baa872241cf572b16a0ef884436fe4818c 的独立静态准备，尚未连接生产战斗。不得把本清单或纯测试当作实际地图通过。

## 当前文件归属

- `wurst/trial/TDTrialRules.wurst`：两节点、120 秒、5 槽、奖励池、范围和时钟规则。
- `TDTrialScore.wurst`：整数高位与实数余量两分量累计；统一最终舍入；显式累计上界与异常失败。
- `TDTrialTargets.wurst`：最多 20 个槽的身份与 revision，不使用普通波次登记。
- `TDTrialState.wurst`：准备、参赛快照、激活、退出冻结、事件票据、seal 和一次性奖励领取。
- `TDTrialLifeRules.wurst`：priority 0 补生命、priority 4 记账以及独立装备资格的纯判定。
- `TDTrialRouteRules.wurst`：首段错位位置与出口返起点 waypoint 重置规则。
- `TDTrialObjectGen.wurst`：专属 uTrG 物编，不是 Boss 白名单成员。

## 等 Boss 正式提交后

1. 基于 Boss 正式 HEAD 合并；不得生产同名 Hook stub，也不得复制 Boss token、过渡调度或开波代码。
2. 实际使用公共 `TDBossTransitionHook`：`onReady(completedWave, transitionToken) returns boolean`、`onRelease(transitionToken, reason)`。`tdRegisterBossTransitionHook` 与 `tdResumeBossTransition` 都必须检查 boolean 返回值。
3. `TDInit` 每局在 Game reset 后先清除上一局 native 目标、装备/精灵 debuff、timer，再 Trial reset、注册新的本局 Hook；DamageEvent 永久监听只注册一次。纯状态 generation 是每局身份，token 是不透明值，不能按数值排序。
4. `onReady` 只处理 8/24，捕获本局 generation 与 token；先建立 4 路参赛快照，再同步独立 createUnit，全部 5 槽成功后 activate 才返回 true。每节点一次尝试。失败先清净所有部分创建的 native 目标，再 rollback 并返回 false。Game 即使 onReady 返回 false 仍会调用 onRelease(COMPLETED)，未 ACTIVE 的状态必须拒绝 seal 和派奖。
5. Trial 不开波、不推进波次、不调用 `tdCreateEnemy`。自有 timer 仅检查 deadline，并请求 `tdResumeBossTransition(token)`；请求成功后 noteResumeAccepted、销毁 timer。失败允许在同一 active 身份下重试，Game 看门狗仍是上限。timer 绝不自行 seal 或派奖。
6. 实际结算唯一在 onRelease：先 seal（使 ACTIVE 无效、封账、失效槽身份），清 native/debuff/timer，确认全部清净后 markTargetsCleared，再用带 token/generation 的 takeReward 一次发金与结果 HUD，最后返回 Game。reason 1/2 且达到 deadline 正常奖，reason 3 无奖。异常提前或坏时钟 release 仍清理但零奖励。onRelease 内不 resume。

## 独立单位与普通系统隔离

- 独立 native unit handle 表保存 lane、slot、token、match generation、slot revision；不能仅凭 owner/wave/userData 认作主波或试炼目标。
- 专用 rawcode `uTrG` 不进入 TDWaves Boss 白名单、Boss 法伤减免、近卫保护、主波 living/行军/漏怪/结束判定。
- 当前 TDSpawn 和精灵/装备含 owner/userData 启发式。生产接线必须显式分支排除试炼目标：普通伤害榜、漏命、主波清场、杀敌金、装备杀敌额外金、掉落、捕获球、进化补刀、队伍分数等都不能触发。仅保持同路战斗资格的必要元数据。
- 屠王效果仅在装备的独立资格入口把当前、同路 trial target 视作可吃 Boss 额外伤害。不要扩展 `tdIsBossUnitTypeId`，也不赋予普通 Boss 的其他行为。接线时更新屠王文案说明“首领及金币试炼目标”。
- 精灵和装备的每个延迟伤害、debuff、弹道及补槽都带本局 generation/token 和 native 目标身份验证。旧 native 单位被移除后不得把延迟技能重新指向新 slot/新轮；route 出口同单位返初始错位点，不替换身份。
- 退出/失守先 withdraw、冻结占位且无奖，清本路目标/debuff；其已得伤害继续影响所占排名与并列池，未发份额不重分。
- 异常死亡只能在 ACTIVE、token/generation 有效且 now < deadline 时清该目标身份后补该空 slot；修订 revision。正常退出/结算使用 RemoveUnit，不使用 KillUnit。

## 伤害与生命

- unreduced priority 0 在每次正事件伤害前给当前有效 trial target 补到 1000000 HP。NaN 不补；正超额仍补，但不能承诺任意大一击绝对不死。
- unreduced priority 4 读最终事件 amount 和真正 preLife，记 `min(amount, preLife)`；有限超额如 1e12 仍封顶，正无穷也只可封顶并记录异常诊断，不得进入无穷累计。NaN/非正/非法 preLife 忽略。
- 不 setAmount(0)，不修改 reduced 伤害、不压制普攻/装备/精灵 proc。不得提高 DamageEvent 的递归 48 或普通飘字 80 上限。
- 库在 unreduced 全部监听后才缓存生命；仍须实际编译和离线核查监听顺序、生成脚本，以及目标实际 HP。合法单段上界必须以最终合入的塔/装备/精灵源码和目标补丁类型表重新证明；本阶段只有有条件源码估算，不能宣称不死保障已成立。装备重做、新塔或百分比伤害机制变化时必须重算。
- `TDTrialHitTicket` 是纯状态测试上下文，不要求生产每击分配对象。实际监听可用每事件局部上下文；若用 ticket，必须每个真实伤害段独立创建、事件结束立刻销毁，不能一技能的多段共用票据，不得修改伤害引擎来配合。嵌套事件不能覆写共享 last-target。
- 分块只是避免主动逐击整数截断和无界累计 R2I，仍有原生单精度舍入。超过 1000000 个 chunk 的 lane 标记 faulted、保留已得排名占位、停止累计且无奖；记录诊断。最终用于排名的 key 分量均安全落在 int 范围。

## 路线和 HUD

- 每路 5 个 slot 同 tick 生于首段，spacing = min(96, first-segment length / 8)，slot 0..4；出口返该 slot 初始错位点，waypoint 重置 0。保留正常减速、眩晕等造成的聚集，不强制分散。
- Trial 榜账本独立于普通榜；展示本轮累计有效伤害、实时平均 DPS（实际经过时间）、剩余秒数和参赛/退出状态。正常最终 DPS 分母 120 秒。
- 排名按最终累计总额统一四舍五入到整数比较；同分均分所占名次奖金并向下取整。真实 0 永不获奖。正伤害 <0.5 要显示 `<1` 或小数，不能显示为 0，且与真正零伤害单独分组。
- 同分行只用 lane ID 稳定排列显示，不以 lane ID 决定奖金。第一轮 30/24/18/12，第二轮 60/48/36/24。工资照常；Boss 补偿另列，不抵扣或加进试炼奖金。

## 发布前门禁

- 更新本阶段 `test_protected_production_sources_are_byte_unchanged`：它只用于独立准备阶段证明未越界，生产接线后改为验证本阶段指定改动范围或移入阶段专用检查；不能把旧基线硬锁当永久集成契约。
- 串行执行 `tools\\Run-WurstChecks.bat`，针对编译/测试问题修复并定向复跑；串行用唯一 `build-and-deploy-test-map.bat` 构建部署。
- 离线读取当前地图 W3U：uTrG 父对象 narg、100万 HP、0 甲、Normal 非 hero、空技能/机械分类、260 min1/max260、攻击/索敌/悬赏/碰撞为零、模型/金色 tint/准确图标引用。确认 1.28 native 模型存在。
- 从当前 MPQ 按完整路径提取 BTN/DISBTN，核 imports 哈希、BLP1 alpha8 和全 7 级 mip；不以“imports 有文件”替代实际打包验证。
- 接线补实际 Hook 注册失败、prepare 部分失败、deadline 双序、异常死补槽、退场全回收、主波隔离、奖励/进化/掉落不触发的集成测试与离线产物检查。
- GPT-6 Astra 只读实现审查 PASS/PASS WITH NOTES 后才可独立发布。没有明确实机请求，不运行 Warcraft；不宣称 FPS/实际外观/控制手感已验证。
