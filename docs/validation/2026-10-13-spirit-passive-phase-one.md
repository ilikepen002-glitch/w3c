# 精灵宿主被动改版：阶段一验证记录

## 范围与当前状态

高风险实施角色 GPT-6.1 Sol，基于 GPT-6 Astra 已批准的五行精灵分阶段方案。阶段一R3源码已由 Astra PASS；最新正式四项修复及测试分层工具已继承。真实 Linux Wurst checks/test/build 与同图 JASS 门禁已通过，当前待独立 Astra 最终成品复审。

仅阶段一：取消精灵统御/迟滞光环，统御身份4退休；减击5、破击6、蓄击7、追击8及连击16、决意一击17、猛击18。属性0..3、原分裂霜箭9/腐尸毒域10、原主动11..15保留。目录边界19包含退休空洞4，已实现身份实际18个，没有加入未来元素主动占位项。

旧槽位契约完整保留：0仅四种属性；1为通用非属性；2/3沿原类别且至多一个主动，共鸣和开栏不改。收藏、洗练候选、采用、释放奖励与紫色必得开栏石继续使用既有事务。未扩展物种、未动模型或野生运动。

## 数据与 UI

- 去除单 int BitSet；使用四个 owned 整数身份比较，包含锁栏，忽略正在替换的本栏。非法身份、品质与槽位不修改 revision。
- 品质由能力 level1..4承载，槽位身份只包含技能和亮/锁态。生产定义导出阶段一合法槽位76个、预览36个、箭头2个；旧490收藏变体保持。
- 整数 rawcode，新增合法000..FFF三hex helper；96个旧野生类型字节保持不变。尚未做阶段二的15物种/2410收藏扩展。
- 两个人工入口 Pcol/Pdep，经理只用一个原生 SPELL_EFFECT 桥；桥继续重验当前展示单位/owner/session/已挂载12格、实际等级及所有事务快照。注册成本与目录大小无关，实际打包启动回放验证2个入口注册+1个经理桥，重复 setup 不重注册。

## 战斗契约

- 单一 early priority3采样：继装备原始采样priority1、原生慢/法抗priority2之后，伤害榜priority4之前。D只读 getUnreducedOriginalAmount，命中前生命、技能品质、计数/随机、地面点、generation/pending和试炼快照先采样。
- 决意每第五次正有效主击，对当前 getAmount 乘以1.5/1.7/1.9/2.1，再 setAmount 一次。A102/A112实际能力存在时不适配，已有技能/候选不删除，剑圣原生暴击对象不改。新增原生暴击必须通过反向挂载目录 gate。
- 连击/蓄击/追击/猛击分别是最多一个带 Pdam+code 标记的追加段。早期只捕获低层队列包；所有正native原击（含无精灵来源）使用同一稳定code/spell/id/immutableD谓词early递增、post3递减，全局在途原击归零才从post唤起派发；派发入口和每包前再验零，不依赖0/0.01定时器deadline、登记FIFO或source/target/D匹配。生产abortCurrent会跳过全部post，目前调用点为零；源码与打包gate禁止未经重新审查引入。副箭基准也读 immutable original，不能继承决意倍率。只有法术 wrapper 缩放一次 Boss 法抗。实际回放已通过四阶段注册Boss物理决意100→210及32波原主动85×0.58=49.3一次缩放。
- 破击每来源单独3秒时限，当前最强有效值；弱来源不能延长强来源，强失效能恢复有效弱来源。减击每来源-目标独立1..5层，期限到点从1重计，同名max/异名sum/75%cap，Boss半强。使用已有统一速度写入，不写坐标/路径/命令。
- 召回/换绑/施工/采用失效 generation 与 pendingSerial，同时清两个计数和临时buff；不改 readyAt。失效/销毁按owner取消捕获包；终局和match records销毁前清包/取消派发，保留仍在途计数给真实post自然减完。四追加后、主动/CD前再次重验context和绑定，防同步终局后写旧buff/CD。单体追加重验原目标。旧地面主动可在主击杀后继续，但捕获五个试炼 handle/revision 值快照，不攻击后来补生的新身份。

## 单段条件包络

沿原明确前提 N=22016：基础/骰面/装备/精灵固定载体、原生百分比与暴击包络、安装攻击类型倍率与负甲倍率前提不变。决意只改主段，保守2.1N=46233.6；连击独立段按旧code通道保守×4为88064；蓄击/旧主动74854.4、追击44032、猛击26419.2。最大已知段仍是进化副箭1.2N×4=105676.8，低于原150000和100万生命的15%。原“精灵双追加149708.8”不再是当前实现的依据。

这是带安装表/原生边界前提的源码/离线条件上界，不能保证任意未来技能或真实原生护甲/类型表，也不是引擎不死或 FPS 证明。最终需实际生产调用链验证priority0补血、HP/榜/派生顺序及异常死亡补位。

## 最终离线验证

最终正式父为911efd5a9c4c15b33de9c1d7f2c3816dbabdd8b0（含c5114cc用户共享spell listener/startup门禁、LF锁，以及cb784e24分层runner/6195055四项修复），完整保留用户 UTF8fix、装备/玩家文案、隐藏光环载体、地面升级整理和 Leoric Boss。生产构图父 0c715fc189956e27d575b0d4d72010e0b4ff319e；真实编译所需局部名/直接 import 与3个测试 fixture 窄修为4226e47，没有改变战斗生命周期契约。

- 地图 ExampleMap.w3x：SHA256 `033d58f4533eb3c843e09b17b75953c5a7eead9382aed5446769bf777e1b16f0`；JASS `7e1543b91429df51a4b3808dc23be46e27e0f3ee91a24c8692e1479fbd87afa7`；显示名“契灵守卫战 20261013-1214-UTC+8”。
- 使用既有锁定 Run-WurstLinux checks/build；JDK27+35-2325、stdlib tree90b45617eda50c15703e8cb2ec3241d3c7b61816。checks typecheck与全部Wurst测试 PASS（不以源码@Test声明数冒充实际执行数），build PASS。实际 Legacy JASS gate133 allocators；CD MPQ35塔宿主/2原生主动/40装备/57动态支持挂载；267 imports精确字节通过。
- 6512d54冻结时构图后只修 Python 验证器/记录；其573项 Wurst/测试源码/import/assets/config输入逐SHA与构图manifest一致。随后继承用户新增Wurst测试已重新checks；全部508项生产Wurst/import/assets/config输入仍逐SHA与原构图manifest一致。没有改锁、Windows入口或生成JASS。
- VerifyPetAttackArtifact 同图完整 PASS：4品质/D40/100/160、第5/10决意、A102/A112不适配且对象不变、原生HP补偿/priority4伤害榜/过杀封顶、20连击和5蓄击段、preHP边界、装备priority1原D25追加、副箭原D100而主击210及shot/volley/list回收、减甲8→8→2→0回退、6击独立减速/Boss半强、来源取消与死亡/移除/召回/施工/销毁、试炼priority0补血999790及最终210得分、主目标补生前旧地面主动只打4旧邻居且新身份0。
- 原击phase fence实际 PASS：250HP/D100的原post仍HP150，连击100+第4蓄击85随后致死，原尸爆0；移除compiled派发零计数守卫的只读mutation必须复现错误尸爆。双同源/目标/D逆post、派发前插入无宠原击、递归code、终局清队列保留计数再晚post自然闭合、underflow failclosed、追加同步终局/召回阻止旧active/CD都通过。计时投递专门手动逆post与提前派发，不依赖0/0.01精确deadline或FIFO；普通flush仅采用受控deadline/index，不声称实测引擎timer。
- 同图 TrialReplay 整链 PASS：真实注册hook、四种wave8/24关闭顺序、20目标独立创建/回收、11damage chain案例、旧timer/death/watchdog隔代拒绝、补位身份、精确大于2^31分数/HUD/rank/reward、原地AoE补生/封场隔离与capture事务。
- PetUI/精灵startup/global startup（--current-pet-ui）PASS：76槽位、36预览+2箭头，513 Channels+114passives，490收藏；2入口+1经理桥、原简化回放268语句；继承用户强化回放后829受控解释语句、runtime字符串扫描0（两个计数边界不同）。equipment combat/aura-special PASS；AuraTarget112装备/35塔/6退休精灵路线与四个隐藏载体 PASS。
- 定向 Python17测试全PASS，通过显式candidate+SHA运行；包括未知原生暴击反向挂载、退休光环重新offer8、活mutable getter缺field反例。分层runner登记新class，未跑全部历史Python或宣称全库绿色。
- 继承Boss实际engine48、mechanic451、hook/leave3离线子门禁 PASS。四Boss正式unit字段、Leoric MDX/Portrait/BLP/readme/credits及地形/pathing/preview与6195055字节一致。旧Boss闭差异规则矩阵要求pre-rewrite baseline、旧flow专用测试harness和孤立Leoric oracle不适用于此生产联合图，未据此宣称闭差异PASS；生产trial flow由上面的同图完整门禁覆盖。

## 验证器适配与证据边界

实际优化器已DCE未使用的 DamageInstance_unreducedAmount/getUnreducedAmount；只在field和getter同时不存在时不读死字段，活getter缺field必须failclosed。HP/榜/最终amount及immutable派生仍执行真实函数，不合成mutable金额。新min/max形状依赖Real_REAL_MAX/MIN，父回放执行实际 init_Real；负例置声明0会失去有效damage credit。原普通怪userdata真实置100；Boss-only iP02采样用实际uB08而非普通怪。低层List.destroy只回收节点，副箭gate另要求shot/volley typeId=0及list销毁；已DCE两个debug计数getter直接核对实际容器。

受控native边界为原生已过护甲D、时钟/随机、单位handle/group/order、原生扣血和timer投递。物理回放走真实 early→nullTimer wrapper登记→原生扣血→真实post closure/回收，再经phase queue追加；没有同步直调onDamage掩盖原击post顺序。无事件miss/无敌不会进入监听；实际0事件不计次/不入fence。Boss物理决意不套法伤抗性。未启动Warcraft III，原生护甲/类型表、无敌/吸收/命中、显示/多人生效、模型观感、平衡及FPS均未实机观察；性能只记录预算/事件计数，未做完整压力测量。

具体复跑命令：

```
python tools/VerifyPetAttackArtifact.py ExampleMap.w3x --baseline ../official-6195055.w3x
python tools/VerifyTrialReplay.py ExampleMap.w3x
python tools/VerifyPetUIArtifact.py ExampleMap.w3x
python tools/VerifyPetStartupArtifact.py ExampleMap.w3x
python tools/VerifyStartupArtifact.py ExampleMap.w3x --current-pet-ui
python tools/VerifyAuraTargetArtifact.py ExampleMap.w3x --require-hidden-carriers
python tools/VerifyEquipmentCombatReplay.py ExampleMap.w3x
python tools/VerifyEquipmentAuraSpecialArtifact.py ExampleMap.w3x
python tools/Run-PythonChecks.py test_pet_attack_phase_one test_aura_target_artifact --candidate-map ExampleMap.w3x --candidate-sha256 033d58f4533eb3c843e09b17b75953c5a7eead9382aed5446769bf777e1b16f0
```

阶段2/3新共用idle-wake队列契约已另由Astra批准，阶段一不纳入；合并时需保留phase0-only异步wake与每包fence重验。未来abortCurrent/early后取消原击会破坏成对post，源码/成品gate继续阻塞未经重审的调用。

## 911efd5 用户启动修复继承

发布前发现新正式父911efd5，已三方整合。阶段一原有Action(onManagerSpell→onCommand)与用户Condition(Filter(onCommand))均单SPELL_EFFECT桥，核心onCommand逐字相同；经root及Astra定向认可保留已构图的阶段一生产实现，未为了变量名/绑定形状重构图。强化门禁只接受这两个明确的唯一绑定形状，实际执行RegisterEvents、HashMap和16玩家注册loop；Action包装只允许调用一次onCommand，实际513按钮精确到admit，foreign/null/revoked拒绝，重复setup不重注册。默认2入口检查保留，515只作为必须失败的旧per-button负例。

用户.gitattributes LF锁、新增unrelated-spell不消耗session的Wurst测试、Linux/bat发布前startup门禁、修复说明完整保留。新的Run-WurstLinux checks typecheck/test已PASS（linux-71oq1ee_）；actualmap加强PetStartup与globalStartup均PASS。全局startup仍将与本门禁无关的tdSetupAuraRuntime列为显式边界，防原来的隐式trigger_addAction stub被取消后误执行未初始化的无关auratrigger；独立真实aura gate及原全部damage/fence/trial证据仍对应完全相同的map。

独立Astra新图窄审另回放用户四个unrelated spell均INVALID且session active/key/epoch不变，随后正确洗练仍单次消费；重复forward与漏第16玩家的compiled内存mutation均failclosed。所有生产输入508项与原build、地图SHA033d58f完全相等，因此不重构图；仅新的Wurst fixture与Python门禁重新验收。具体证据在启动整合checkpoint的real-checks-manifest.json、inherited-real-build-manifest.json、production-map-inheritance.json及logs。原6512d54成品已Astra PASS WITH NOTES；此继承最终冻结待窄复审确认。
