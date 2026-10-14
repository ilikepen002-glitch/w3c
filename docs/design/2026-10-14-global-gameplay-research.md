# 契灵守卫战：全局设计依据与调研附录

日期：2026-10-14。对应[全局玩法与平衡设计方案](2026-10-14-global-gameplay-design.md)。

本轮源码基线：`9611f0e3951c26b28028c72487d730dfe45f667d`。读取时工作树无既有修改，分支`codex/archer-split-arrow-shots`跟踪同名origin分支。没有拉取、切分支、回退源码、构建或启动游戏。

用户目标：完整32波通关约35～45分钟，保留自己的特色，重视体验、持续可玩性、平衡与单局节奏。调研针对设计方法，不做当前热门流派排行或商业收益预测。

## 1. 证据的层次

| 标记 | 含义 | 可以支持什么 |
| --- | --- | --- |
| 源码事实 | 当前提交中可定位的规则 | 说明实现如何选择、计时、扣料和结算 |
| 静态推算 | 规则与明确假设下的算术 | 比较成本、时间预算与概率风险 |
| 外部资料 | 官方介绍、开发者演讲或署名设计者历史资料 | 提供可借鉴的方法和取舍 |
| 设计推断 | 从事实提出的体验或平衡假设 | 指导原型，不能替代试玩结果 |
| 验证缺口 | 当前没有取得的证据 | 明确不能据此下结论的事项 |

未重新跑所有旧验证报告，未把历史诊断局或旧构建的通过结论移用于当前玩法。当前HEAD含独立Boss-A诊断产物记录，也不因此视为普通完整局已通过。

## 2. 外部调研：采用什么，舍弃什么

### R1：Element TD——支援价值取决于与输出的关系

历史设计者指南明确区分输出塔、范围减速、减甲、伤害放大和塔增益；减速会形成聚集，改变范围攻击的命中数量。这说明支援应放在阵容中评价，不能拿单塔伤害榜判断其用途。[设计者指南，2008年](https://forums.eletd.com/topic/945-basics-of-element-td/)

对本图的推断：小鹿、步兵的测试应包含“帮输出塔多打了几次”和“范围技能实际命中了多少目标”。不照搬旧版的克制倍率、支援倍率或塔数量；该资料不是当前Element TD版本的平衡证明。

官方Element TD 2介绍也把元素组合、不同地图与玩法修改器列为内容结构；这里只用来确认其复玩维度，不把内容数量当作本项目需要追赶的规模。[Element Studios官方介绍](https://www.eletd.com/)

### R2：Kingdom Rush——升级需要有作战用途

官方资料强调不同升级与专精，并列出独立的塔能力和有技能的敌人。[Ironhide官方资料](https://www.kingdomrush.com/kingdom-rush-presskit)

对本图的推断：终阶分支应告诉玩家获得了什么解题工具，而非只展示更大的攻击值。我们没有同样的兵营拦截规则，不应照搬坦度、阻挡等职业补偿。

### R3：Bloons TD 6——先有组合深度，再扩展挑战内容

开发商商店说明列出多条升级路径、主动、Boss活动，以及可分享的挑战内容。[Ninja Kiwi官方商店页](https://store.steampowered.com/app/960090/Bloons_TD_6/)

对本图的推断：复玩可以来自同一套工具面对不同规则，未必每次都要新增塔。先做出三套可解释的阵容，再做限制条件与预设挑战。不据商店宣传推断任何具体机制导致了留存，也不照搬长期战力与商品系统。

### R4：Legion TD 2——随机与可修正的计划可以共存

开发者在2019年重选改版中，让玩家在原有阵容选项与新随机选项之间选择，而非只有全盘重抽；说明中强调保留起始选择的重要性，同时允许关键时刻调整。[v4.02开发说明，历史版本](https://beta.legiontd2.com/updates/v402-eternal-wanderer-samurai-soul-mastermind-reroll-rework/)

另一份历史更新明确讨论减少开局决定一切、移除带来过多挫折的系统，以及减少单位行进却不战斗的空档。[v4.00开发说明，历史版本](https://preview.legiontd2.com/updates/v400-season-4/)

对本图的推断：定向绿色培养和保留旧洗练结果可以保护已有计划；35～45分钟应花在战斗与选择上。历史说明不代表当前精确规则，不能直接挪用收入、出售比例或单位数。

### R5：Monster Train——主打法与补短板工具

开发商资料描述主副氏族组合、路线上的不同成长资源，也提到通过更新加入战斗波数与部分Boss的提前预览。[官方商店页](https://store.steampowered.com/app/1102190/Monster_Train/)

对本图的推断：无需让每个单核精灵同时擅长清群与首领。让玩家保有一个主打法，再用副核心补位；Boss预告要在还能调整投资时出现。不照搬多层战场与牌库管理。

### R6：Hades——随机组合服务玩家表达

Supergiant官方FAQ将不同组合、新挑战、玩家表达与复玩联系起来，同时说明难度有多种调节方式。[官方FAQ，页面标注2025-07-16更新](https://www.supergiantgames.com/blog/hades-faq/)

对本图的推断：玩家应能用抓到的不同精灵形成不同计划；困难程度与“有没有资格体验核心能力”分开。FAQ没有证明本图应使用某个掉率，不能据此主张必须加入永久战力或强制长线刷取。

### R7：Rogue Tower——覆盖形状与敌人分布本身就是资源

开发商介绍强调建造位置、道路扩展、随机升级以及敌人能力；不同道路汇合方式会影响范围输出的价值。[官方商店页](https://store.steampowered.com/app/1843760/Rogue_Tower/)

对本图的推断：射程相同不代表有效输出时间相同，技能半径相同也不代表命中人数相同。这进一步要求前置四路线与站位公平核验。随机扩路不是本图首轮需要的新系统。

### R8：Slay the Spire——指标是证据，仍需设计判断

联合创始人Anthony Giovannetti的GDC讲稿提出每个选项应有用途、避免过度扭曲环境，并把数据、玩家反馈、难度分层和持续迭代结合起来；也明确提醒不能过度依赖指标。[2019年GDC原始讲稿](https://media.gdcvault.com/gdc2019/presentations/Giovannetti_Anthony_SlayTheSpire.pdf)、[演讲说明](https://www.gdcvault.com/play/1025731/-Slay-the-Spire-Metrics)

对本图的推断：选取率、伤害和胜率需要结合获得概率、熟练度与适用场景解释。某技能胜率高，可能因为只有已经领先的玩家能拿到。20组种子只能作初筛，不能替代完整置信分析或实际体验。

本轮读取了原始讲稿的文本，不声称观看了全部演讲视频；没有借用其未展示的实验数据或把卡牌平衡参数移植到塔防。

## 3. 源码索引：关键事实落在哪里

下列行号用于本次快照定位；后续代码变化后应重新定位。链接指向源码文件，行号写在描述中。

| 内容 | 源码与定位 |
| --- | --- |
| 初始金币/生命、首波/波间、基础倍数 | [TDConfig](../../wurst/TDConfig.wurst)，4～25行 |
| 路点差异与fallback坐标 | [TDConfig](../../wurst/TDConfig.wurst)，74～125行，95行附近 |
| 难度四档生命倍率 | [TDDifficultyRules](../../wurst/TDDifficultyRules.wurst)，9行起；[TDSpawn](../../wurst/TDSpawn.wurst)，129～149行 |
| 普通波推进、清场与Boss准备 | [TDGame](../../wurst/TDGame.wurst)，362、492行附近 |
| 试炼与章间推进 | [TDGame](../../wurst/TDGame.wurst)，406行起 |
| Boss失败/最终Boss结算 | [TDGame](../../wurst/TDGame.wurst)，178、465、543行附近 |
| 团队结束与退出路线 | [TDGame](../../wurst/TDGame.wurst)，101、161行附近 |
| 收入归属、进化击杀记录 | [TDGame](../../wurst/TDGame.wurst)，317、337行附近 |
| 人口 | [TDState](../../wurst/TDState.wurst)，156行附近 |
| 波次数量、间隔、奖励 | [TDWaves](../../wurst/TDWaves.wurst)，118、725、746行附近 |
| Boss额外奖励 | [TDBossRewardRules](../../wurst/items/TDBossRewardRules.wurst)，6行起 |
| 塔成本、终阶、80%退款计算 | [TDTowerBalanceData](../../wurst/towers/TDTowerBalanceData.wurst)，161～259行 |
| 退款约定、工资、塔族能力 | [TDTowerCommonData](../../wurst/towers/TDTowerCommonData.wurst)，14、102、132、235行附近 |
| 工资触发、出售、尸爆 | [TDTowerRuntime](../../wurst/towers/TDTowerRuntime.wurst)，79、537、862行附近 |
| 440击杀与全图名额 | [TDTowerEvolutionState](../../wurst/towers/TDTowerEvolutionState.wurst)，3～21行；[Runtime](../../wurst/towers/TDTowerEvolutionRuntime.wurst)，全局实例与`tdEvolutionRefresh` |
| 塔族选敌规则 | [TDTowerTargetPriorityRules](../../wurst/towers/TDTowerTargetPriorityRules.wurst)，14行起 |
| 概率、栏位、阶段解锁、当前技能强度 | [TDPetRules](../../wurst/pets/TDPetRules.wurst)，9、15、73、155行附近 |
| 技能生成、释放与开栏、阶段补球 | [TDPetState](../../wurst/pets/TDPetState.wurst)，79、320、421、451行附近 |
| 捕获消耗与65%概率 | [TDPetRuntime](../../wurst/pets/TDPetRuntime.wurst)，捕获事件处理 |
| 精灵原生攻击与副箭排除 | [TDPetCombat](../../wurst/pets/TDPetCombat.wurst)，39行及`onAttack` |
| 元素主动各品质不同技能 | [TDPetElementData](../../wurst/pets/TDPetElementData.wurst) |
| 十个专属对应终阶分支 | [TDPetHeroRules](../../wurst/pets/TDPetHeroRules.wurst)，23行起 |
| 精灵数量与五行映射 | [TDPetData](../../wurst/pets/TDPetData.wurst)，10、44行附近 |
| 不适配/共鸣锁定提示 | [TDPetUIView](../../wurst/pets/TDPetUIView.wurst)，105行附近 |
| 悬浮与待机动作支持范围 | [TDPetDisplayRules](../../wurst/pets/TDPetDisplayRules.wurst)，当前专用动作支持判断 |
| 敌人机制与阶段法术承伤 | [TDEnemyMechanicData](../../wurst/enemies/TDEnemyMechanicData.wurst)、[TDEnemyMechanicRuntime](../../wurst/enemies/TDEnemyMechanicRuntime.wurst)、[TDEnemyMechanicState](../../wurst/enemies/TDEnemyMechanicState.wurst) |
| 装备掉率、品质与预算 | [TDDropLogic](../../wurst/items/TDDropLogic.wurst)，6、60、131、158行附近 |
| Boss掉落 | [TDBossRewardRuntime](../../wurst/items/TDBossRewardRuntime.wurst)，20行起；[TDBossLootPlan](../../wurst/items/TDBossLootPlan.wurst)，17行起 |
| 合成与装备物编约定 | [TDItemObjectGen](../../wurst/items/TDItemObjectGen.wurst)，17、47行附近；[TDInventoryRuntime](../../wurst/items/TDInventoryRuntime.wurst) |
| 拾取准入与跨路线转交 | [TDInventoryRuntime](../../wurst/items/TDInventoryRuntime.wurst)，215行附近 |
| 试炼时长、靶子、奖金 | [TDTrialRules](../../wurst/trial/TDTrialRules.wurst)，3、6、26、33行起 |
| 试炼提前结束与奖金资格 | [TDTrialState](../../wurst/trial/TDTrialState.wurst)，221、261行附近 |
| 试炼移动、生命与计分 | [TDTrialRuntime](../../wurst/trial/TDTrialRuntime.wurst)，101行附近；[TDTrialLifeRules](../../wurst/trial/TDTrialLifeRules.wurst)，7行起 |
| 当前HUD与提示缺口 | [TDHud](../../wurst/TDHud.wurst)，39、71、130行附近；[TDDamageHud](../../wurst/damage/TDDamageHud.wurst)，6行起 |

## 4. 静态预算与边界

### 4.1 时长

条件预算：首波30秒，28个普通波按60秒，4个Boss按90秒，第16波后30秒，两次试炼按120秒，合计2340秒。

快清下界的宽松估算：`30 + 429.615 + 28×0.65 + 28×20 + 30 ≈ 1067.815秒`，约17分48秒，再加Boss实际战斗、试炼实际时间和准备轮询。429.615是按当前普通波刷怪间隔累计的出怪时间；0.65来自刷完后等待与首个清场轮询。

它不是可实现的速通记录。最大耗时也不能由39分钟直接确定，因为Boss准备清场没有固定超时。未来统计需分别记录战斗、清场等待、波间整理、试炼与章间，而非只看最终总时间。

### 4.2 金币

按当前波次数量与奖励函数逐波求和：每路934只波次敌人，波奖励15410，含Boss补偿的击杀收入37680；加开局1000为54090。非Boss基础击杀收入为32500。

| 节点 | 含开局累计基础收入 | 备注 |
| --- | ---: | --- |
| 8 | 5630 | 全杀、Boss击杀 |
| 16 | 14640 | 同上 |
| 24 | 31680 | 同上 |
| 32 | 54090 | 同上 |

排除工资、装备额外金币、试炼、出售回款；工资按墙钟和施法时点发放，不能从波次表唯一推出。金币余额还必须扣掉已完成和在建投资。

试炼单人正常计分最高300+600=900，不因打出更多伤害增加单人奖金。到24波后若两次试炼均完成领取，基础加试炼为32580；仍不足四座最低价终阶35800。

### 4.3 培养随机性

独立捕获成功后，连续n只都不是天然四技能的概率为`0.9^n`：5只59.05%、8只43.05%、10只34.87%。这个示例没有计入开栏、释放补偿、玩家选择和实际捕获次数，不是完整局成型失败率。

当前释放规则：每只1洗练石；整体紫色必给开栏石；其他三技能5%、两技能2%。因为整体品质也受技能数量和单项品质影响，不能只用“开栏石5%”概括总获得率。

主方案候选保底合计2开栏、8洗练；每次定向绿色3洗练。最差两栏起点可用2开栏补至4栏，并有2次定向机会余2洗练。这是给定玩家选择下的材料预算，不保证任意全部技能达到指定品质。

### 4.4 路线几何

只用源码fallback中心折线计算的长度：7924.80、3802.38、3716.17、3675.72。除以试炼速度260约30.48、14.62、14.29、14.14秒。

实际优先World Editor区域坐标，还受到寻路、地形、区域判定、减速与碰撞影响，不能将这些数字写成游戏实测通过时间。当前足以提出公平性风险，不足以认定P1实际输出一定是其他路两倍。

## 5. 经济与体验的补充事实

### 装备

普通怪掉装随阶段增加，有每路每波最大预算，**普通波没有至少一件的保底**。精英必掉：第4波绿装，12/20/28波为25%蓝、75%绿；Boss击杀必有蓝/紫，另有额外掉落抽取。失败Boss缺少这些击杀收益。

普通装在已掉落条件下的品质概率，忽略幸运装备重掷：

| 波次 | 白 | 绿 | 蓝 |
| --- | ---: | ---: | ---: |
| 1～4 | 100% | 0 | 0 |
| 5～8 | 91% | 9% | 0 |
| 9～12 | 88% | 12% | 0 |
| 13～24 | 84% | 13.5% | 2.5% |
| 25～32 | 84% | 11% | 5% |

合成三件同品质白/绿/蓝升一档，同名定向、混名随机；紫不再合成。不花金币，装备也不是可售现金。塔3格、工人6格，塔不接受重复同rawcode装备。

因此“装备很多”可能首先是整理与选择负担，而非金币多；是否严重需要观察实际掉落、拾取和合成操作，不能仅按概率表推断。

### 试炼与多人

每路5个高生命靶，伤害前补满生命、按有效伤害计分，走到终点移除，不扣生命。全局等所有靶离场或120秒到期，单路余靶可拖延其他路线；已结束路线不能继续刷分。

首轮排名奖金300/240/180/120，次轮600/480/360/240。更多伤害不增加单人第一名奖金。若路线通过时间不同，总伤害排名可能混入地形优势；不能把它当纯阵容强度排名。

目前装备可物理转交，没有相同的精灵跨路转让机制。本轮未核实原生金币转移面板行为，不声称所有资源交易都已审计。

### 界面与输入

已经存在当前/下一波机制与策略提示、精灵信息、伤害榜和试炼榜。本方案需要整理信息优先级，**不是再新增一套重复的下一波提示系统**。

确认的缺口是普通波等待与强推截止时间没有像Boss、试炼那样显示剩余秒数。现有HUD总行数为活跃人数加27，是否遮挡严重需要在目标客户端查看，当前只将其列为体验风险。

## 6. 本轮设计评估与后续验证

高风险范围是拟议的培养、战斗底座、经济与进化职责变化；本次只执行方案阶段。GPT-6 Astra提供系统方案与反证，定向explorer核对节奏/经济，主代理核对最新塔与精灵源码、开展外部调研并编写文档。

实际游戏实现仍须另按项目三阶段流程完成。此次没有代码差异，不生成“代码审查PASS”结论；文档静态检查不能替代构建与实机证据。

最终文档一致性审阅与静态检查结果在主方案交付段记录。尚未完成的平衡、玩家反馈和实机性能不以任何外部资料或公式推演补成“已验证”。
