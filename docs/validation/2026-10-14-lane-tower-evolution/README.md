# 第4批：每路第24波终阶塔选择进化

## 冻结范围

- 整合基线：第2定向学习 + 第3固定工资冻结 `6cecf56e42eae2b273141b2ab51f02f37e215446`；基线地图 SHA256 `962da70b23e122e08f7ef82f0b5016ebf1c7d99d3373d5a90c64c1b8dd26476e`。
- 第4原实现 `a92a00f34f695b2a0530b30bcf4d89e30e7e7ca0`，由 `0c5948832a5692733638cd7be2285eed52622e87` 三方整合；最终实际候选 `194d0634008d445ba450bd980b005adcedfb4734`。
- 最终地图 `ExampleMap.w3x`：6,029,830 bytes，SHA256 `cd662ef1454356687cd7e9383b702d5c33f2614e863b2bbdb059659ddf5ee651`。独立输出及通过构图的 MPQ 与此逐字相同，未手改生成物。
- 高风险流程：Astra 方案、指定 GPT-6.1 Sol 实现、Astra 对实际差异和最终地图复核。最终审查 `PASS WITH NOTES`，绑定上述实际候选和地图；详见 `astra-review.md`。

本路第24波正式完成后取得一次资格，之后主动选择本路已完工6阶终阶塔，预览确认后沿用现有分支20%强化。每路分别认领，取消不耗资格；卖塔/死亡不返还，也不转移名额。任意击杀数都不自动进化；保留独立击杀统计。

资格、单次认领及塔状态由进化域持有；票据绑定玩家/lane、epoch、真实unit/record identity、rawcode/branch、工作generation、单次nonce。确认在任何 UI/native/equipment 刷新前消费票据并写入 spent/evolved。施工、owner改变、出售、死亡、路线关闭、终局、新局reset和真实取消选中使旧票据失效；旧确认/取消不能命中新票据。新局才恢复四路资格账本。

新增 `AeEC` 零CD原生Channel命令与状态互斥共格，热键 R，保留出售 V、精灵详情 D 和原核心战斗 E。第3旧工资 A109 仍退休。严格订单证明 AeEC=absorb、sale=acidbomb、全部既有Channel精确后移一槽；诊断 Pcap=ambush，与实际 MPQ 一致。

## 必要自动证据

- 官方完整 checks：`checks-manifest.json` / `final-checks.log`，事务 `linux-zedkpncq`，父提交 `5dc69cc`，typecheck/test 均 PASS。
- 官方完整 build：`build-manifest.json` / `final-build.log`，事务 `linux-ljbtepur`，父提交 `510b45e`，内置容量、CDR、注册路由与启动门禁 PASS；407份打包imports核对。
- `final-input-equivalence.json`：最终所有生产 `wurst/` 与 checks/build 输入逐字相同；`tests/wurst/` 与 build 逐字相同，相对 checks 仅 Pcap 单行注释纠正，无行为差异。构图后仅独立Python门禁与测试修正；不改生产、配置、依赖或地图字节。
- `final-strict-delta.json`：最终图对冻结第3图，允许改变仅 `war3map.j`、时间戳 `war3map.w3i`、严格指定 `war3map.w3a`；新增唯一 AeEC，935级统计文案、4级路线状态、卖塔本路文案、精确+1 Channel。单位/升级/数值/资源差异为0，未给予任意field或resource豁免。
- `final-packed-evolution.json`：实际 MPQ 生产 JASS 四路24结算、击杀/存活漏怪/存活超时、关闭路线；17陈旧生命周期、两类实际 deselection 桥；0..934共935击杀均不自动进化；十分支精确替换与非选中能力完整、装备库存/标量不变、精灵绑定/generation/readyAt不变、原生主动非零冷却不变、翅膀一次、刷新不重复、出售/死亡不退款；实际nonce绕确认变异被同一重放拒绝。
- `final-prior-batches-replay.json`：最终图上第3真实金币结算/四路32波/重复/关闭/旧epoch和3变异、第2库存0/2/3/4/随机旧入口拒绝/重复确认/库存争用/分页/真实管理器桥及3变异、第1保底材料独立/延迟/饱和/关闭回归均 PASS。早期批次的对象delta不拿来豁免第4差异；对象/资源保存由上述闭合严格delta独立证明。
- `final-full-ui.log`：真实 MPQ 完整精灵UI/rawcode/页面/按钮/热键/订单/目标、671管理器Channels、93栏位显示、61动态显示、15模型与图标字节 PASS。
- `evolution-artifact.log` / `upgrade-artifact.log`：最终图完整进化对象/资源和35塔/30升级边/十分支/JASS伤害接线 PASS。
- `upgrade-mutations.log`：31项真实图阳性及各技能/升级/属性/命令/资源/JASS负测 PASS；`current-carrier-mutations.log`：6项当前毒/盾击/光环载体逐字段、各61级、全诊断probe负测 PASS。两者显式设置 `PYTHON_CANDIDATE_MAP` 为本最终图，路径/SHA/命令见 `final-input-equivalence.json`。
- `final-source-delta-tests.log` 20项、`final-command-card-tests.log` 6项、`wage-source-tests.log` 4项、`integrated-source-tests.log` 中实际执行CDR 44项均 PASS。组合runner的30项未分类未运行，原 INCOMPLETE 保留，已用直接 unittest 补齐，不宣称组合runner全覆盖。
- `final-pet-source-current.log`：当前2110页/动作、1280品质、事务/身份/wiring，以明确的冻结第3HUD/wild源码作精确scope基线 PASS；`final-builder-control.log`：实际工人9格、工资空格、卖塔/升级与678全局唯一Channel PASS。
- 恢复的4份 Leoric 输入全部跟踪且继承冻结第3字节；原清单见 `restored-resource-inputs.json`。

## 必要旧门禁修复及失败保留

最终图先遇既有门禁的历史数值/架构/编译形状假设。只在阻塞本批必要进化验收的依赖内窄修，以冻结第3对象和当前源码为依据，没有恢复旧行为来通过。

- `VerifySlowAbilityArtifact.validate_slow_abilities` 锁定现有毒60/90/108、原生移动0、攻击慢0.16、5秒/英雄1秒与原buff；225/400半径的原生缓速零载体和61级准确显示；脚本盾击的原生carrier全部零伤/零概率/零眩晕。每字段仍有精确负测。
- 光环可见源是 self/零原生增益；实际隐藏 rank carrier 的双等级值18/20、21.6/24、16/18、19.2/21.6分别锁定，不再期待旧原生范围叠加。尸爆血疫购买270、进化324沿用原源规则。
- 精确结构验证绑定实际 chosen-record 参数、编译器标准可选stack参数与单一addPermanentAbility重载；分裂箭使用已有 `getUnreducedOriginalAmount`，伤害值仍须到达直接与延迟回调且不改主箭；精灵疫种沿当前实际 `tdPetHeroOnCorpseExplosionSettled` 的基尸爆×品质power传入真实ticket，不继承终阶进化乘数。
- 分组布尔表达式原已可正确处理；旧测试改为真正未分组and/or拒绝，并保留分组阳性。
- 普通图排除真实 `TDNative*Probe`，允许生产 `TDNativeActiveCooldown`；所有16种现行probe被负测拒绝。
- 合成命令卡fixture只检验明确的非碰撞合成动作，不冒充实际allocator证明；实际首槽/order由最终严格delta验证。原碰撞失败保留。

全部初次失败与修复前输出保留在本目录的同名阶段日志；通过状态以本文列出的最终成功文件和其内容为准；中途尝试即使文件名含 `final` / `fixed` / `pass` 也可能失败，文件名不当作通过证据。额外尝试的默认旧 `VerifyPetManagerSource` 历史引用 `c9d59e...` 在本checkout不可读，未声称默认历史CLI通过；当前wiring使用明确冻结第3基线，资源由完整UI真实MPQ门禁验证。未为此改源或删历史scope检查。独立旧敌人速度CLI的既有历史假设不属于本批修改范围，未把该默认CLI宣称通过。

## 未验证与风险

没有启动 Warcraft III。离线生产JASS重放仍以受控engine handles、单位/按钮/特效/时钟为边界，不能证明实机Dialog输入、同步事件队列、原生Buff投射/叠加、命令卡渲染、翅膀遮挡、35～45分钟手感、四人FPS或平衡已通过。

每路20%强化是原分支口径；未改塔大平衡、终阶路线、地图地形或工资/定向培养候选值。最终四路镜像公平是后续独立目标。
