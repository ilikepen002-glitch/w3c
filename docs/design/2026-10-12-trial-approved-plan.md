# 五目标金币试炼：正式衔接设计

基线654771baa872241cf572b16a0ef884436fe4818c。2026-10-12，gpt-6-astra只读设计审查PASS WITH NOTES，可由Sol独立准备，尚非实现审查。

用户已授权两次120秒、每路5目标、金币魔像形象。第8/24波后自然清场由Boss状态机负责，不额外设必须击杀Boss准入；活着且继续的路线可参加。试炼120秒替代30秒休整，无额外准备时间。5目标改善AOE表现但非公平绝对战力，尸爆/低血处决劣势用户接受，不造可刷小怪。

## Hook

未来依赖Boss正式公共package/interface TDBossTransitionHook：onReady(int completedWave,int transitionToken) returns boolean；onRelease(int transitionToken,int reason)。COMPLETED=1，TIME_LIMIT=2，ABORTED=3，Game时间上限120.0。TDGame公开tdRegisterBossTransitionHook(hook) returns boolean、tdResumeBossTransition(token) returns boolean。

Game独占过渡token、HELD→CLOSING、清理后开9/25。Trial不得直接开波。onReady只接受8/24新token及未完成节点，同步建立参赛快照、目标和deadline，全部成功才返回true；部分失败清净后返回false。Trial计时器仅请求resume，实际收尾统一onRelease。COMPLETED/TIME_LIMIT均正常结束；ABORTED只清理零奖励。先封账、冻结结果、清目标状态、一次性奖励HUD后返回Game，不在onRelease里resume。重复/旧token无效。每局TDInit在Game reset后Trial reset、注册新hook，再开波；DamageEvent永久监听仅装一次。

## 数值与目标语义

每目标1000000HP，0基础护甲，显式ArmorType.Normal，非英雄，清除魔像继承技能/抗魔/硬化皮肤和机械免疫；两轮移速260、min1/max260；无攻击/索敌/原生悬赏/碰撞。Normal不代表所有攻击倍率100%，不改全局类型表。独立rawcode，不列入普通Boss白名单/主波登记；仅装备资格helper使屠王有效。无Boss阶段法伤/近卫保护。装备及精灵仍有本路元数据。

独立createUnit，绝不tdCreateEnemy。自己推进路点/检测出口，5slot同tick首段spacing=min(96,length/8)，各自返初始错位点重置waypoint。自然控制可聚集，不强行分开。仅本路源塔→本路目标计分，目标属本轮且命中now<deadline。普通榜不计trial。本轮平均DPS分母实际经过时间，最终120秒。

## 生命

unreduced priority0每次正伤害前补满，priority4记最终事件伤害min(amount,prelife)，不setAmount0/不改reduced伤害。逐目标上下文，不用共享last target变量。库是在unreduced监听之后缓存生命，已经Astra逐行核对。100万附近浮点步长约0.0625，榜是事件有效伤害不是血条差值。合法单段上界需证明远低于100万；异常超额封顶、异常死只补对应空slot且token/deadline有效，无击杀奖。无法承诺任意大一击绝对不死。

不提高递归48/飘字80上限；分裂Tspl/code和精灵code已有防递归，AOE有3/12目标上限。20目标压力验证检查段数、去重与最终回收，不宣称未测FPS。

## 奖励

第一轮30/24/18/12，第二60/48/36/24。单人正伤害第一，零伤害无奖。同分均分占用名次奖金向下取整；最终总额统一舍入作同分，禁止逐击截断和对无界累计直接R2I。退出/失守冻结占位无奖。工资照常。无普通杀敌金、装备额外金、掉落、球、进化补刀或队伍分数。Boss补偿另列，不抵扣也不加试炼奖金。

## 清理

先active=false和generation失效，清装备/精灵debuff、目标remove不kill，最多20。延迟技能/弹道/补生不得打新slot或新轮。ABORTED不奖不推进。主波living/行军/漏怪/奖励由Boss登记资格隔离；接线时验证不能凭owner/wave误认trial。

## 资产

assets/source/trial已有原始生成图、exact prompt、工具与哈希。独立BuildTrialAssets仅import BuildEvolutionAssets.blp，不运行main。64x64 BTN/DISBTN，后者灰阶0.45，BLP1 alpha8全mip，独占BTNTDTrialGoldGolem名称。显式完整图标setter，避免presetIcon重加前缀。原生Units.golemStatue1 / UnitIds.battlegolem金色近似，最终核1.28原生资源，不称自制金币3D。

## 独立实施边界

现在可写专用rules/state/objectgen、资产和纯测试、独立目标登记/路线/保护模块草稿。未正式Boss前不改共享TDGame/TDSpawn/TDInit/TDHud/TDDamageRuntime/装备入口、不生产同名Hook stub、不复制Boss调度。真实适配待Boss正式HEAD。当前不完整构建或推送、不实机。新增字节及时Library完整备份。

测试含规则排序/并列/0/退出/预算；生命周期/旧token/部分创建失败；120秒timer与Game看门狗双序竞态只结算一次；ABORTED零奖；先remove再开9/25；每局reset后注册；20目标多段去重/退场归零；普通榜隔离；无击杀奖励；物编rawcode/技能/生命/甲/模型/图标路径与BLP全部mip。Boss正式后全项目检查、唯一构建入口、离线实物验证、Astra实际实现审查才可独立发布。

### Boss接口失败分支补充（10:43 UTC）

Boss lead确认：onReady返回false之后，Game仍会对该token调用一次onRelease(COMPLETED)，随后走默认30秒休整。Trial未成功进入RUNNING、部分创建失败或无参赛者时必须拒绝任何seal派奖，清理仍幂等；reason=COMPLETED单独不构成奖款资格。token视为不透明身份，不依赖单调大小；采用本局generation和8/24各一次节点标记。onReady失败只调用一次，trial不自行重试。
