# 精灵五行与最终塔专属整合验收

## 冻结范围

正式父为 `ec3d5555724fc6fb4879a970780bba726d3b6039`，保留用户 startup/LF 修复、装备/文案/Boss/光环按钮。生产输入冻结于 `95a79a62e36002b8e5e885420895cb4df430058a`；后续提交仅补验证工具、证据和本文，不改变此成品的 Wurst/imports 输入。

成品 `ExampleMap.w3x` 为 6,662,209 bytes，SHA256：

`611ee1b735c56dc8b2a27cbe1db7e17469d1e536f1000f278a5bf3ea2f65a3e3`

这是高风险游戏逻辑/生命周期/物编改动。GPT-6 Astra 提供批准方案并审查阶段2与阶段3，GPT-6.1 Sol 实施五行运行时、资源和公共整合，另一个明确的 GPT-6.1 Sol 实施十最终塔专属及其实际成品门禁。阶段2四项初审阻塞均已修复并获 SOURCE PASS，阶段3独立源码 PASS WITH NOTES；最终集成同一成品只读审查结论 **PASS WITH NOTES**，无阻塞项。未启动游戏、未部署到客户端。

## 最终目录与资源

- 有效43定义，目录上界49；退役4/9/10/13..15不会抽取。
- 主动22：通用狂热11、蓄力12；五行各四个固定白/绿/蓝/紫身份19..38。元素技能 ID/品质错配及异系洗练均拒绝。
- 被动21：11通用被动及39..48十最终塔专属。主动仅第1栏，最多3被动；锁栏也参与去重和最高拥有品质。
- 15 species，五行各3；480野生整数 rawcode，15随塔视觉，60品质展示，2410收藏互斥列表物编。反查逐个检查两个 wave nibble，再约束wave1..32。
- 15最终原创MDX800及15精确BLP1纹理，原始约5.125MiB。最小可再生模型源码/贴图源/许可保存在 `assets/source/elemental-spirits`，不提交动画预览或校验缓存。
- 图标为315 BTN及315 DIS：15种类基图、60种类×品质、240种类×品质×拥有技能数。来自最终MDX内嵌Portrait相机的实际头像；七mip、透明及DIS灰度逐项验证。
- 20主动机制与实际原生特效阶段/几何分别不同，见[表现对照](elemental-spirit-phase2-visuals-20261013.md)。原生目录核对按模型名/后缀归一化处理，不宣称 `.mdl` 与 `.mdx` 文本逐字相同。

## 生命周期与伤害契约

原击 early 捕获immutable D、preLife、context及试炼五handle/revision快照。全原击 early/post3 phase fence 完成后，异步队列才 pop-before-call 派发。闲时入队也可唤醒，最多一个待派发timer；current packet的busy与未post原击均阻止记录销毁。

CD只有一个绝对readyAt，来自标准metadata；换宠、洗练、取消或共鸣不重置。每次主动启动、CD写入、每段派生伤害都重验绑定和context。伤害归宿主；tagged派生不再计原击，Boss法抗只处理一次。

一个0.05 scheduler管理所有短时task，取消执行中task先标记、同次返回后回收；没有4秒猜测销毁。终局沿既有0.5生命周期callback取消队列/效果，等待 effectCount=0、pendingOriginal=0且busy=false，条件不满足保留callback重试。真实claim死亡先HeroForget(true)，再统一Forget(false)清理；退出、试炼换轮或RemoveUnit只清理，不传播。

共享原生控制使用盾击窄窗/Boss抗性。成功控制前必须进入有界身份表，取消只清自己的source/token。减速与阶段F弱化按来源独立清理，多个来源取最大。旧9/10专属和旧毒域已经退休，不保留双处理分支。没有Blz/EX/Frame、暂停怪物、改变怪物位置/道路命令或修改野精灵运动设置。

## 实际检查与证据

| 验证 | 结果与范围 |
|---|---|
| Wurst checks/test | r13 PASS；锁定JDK/compiler/Grill/stdlib |
| 实际 build | r2 PASS；147 allocator Legacy/31参数/8192容量、CD、完整玩法与精灵startup、927 imports字节 |
| UI packed/物编/资源 | PASS；2433 Channels、131合法slot display、61展示prototype、30模型纹理及315 BTN/DIS逐SHA |
| UI Python正负例 | 47 tests PASS，显式r2候选 |
| 元素源码规则 | 15 tests PASS；完整目录/480正反查/异系与槽限制/几何/取消契约 |
| 图标重建核验 | 315 pairs verify-only PASS |
| 受限JASS解释器回归 | 39 tests PASS；cache只复用语法树，每次重新读取scope并实际调用；local arrays局部性/默认值/8192边界；mixedand/or仍失败关闭 |
| 20元素实际正常链 | 完整r2 packed JASS PASS；精确命中数量/总量、几何与阶段、真实scheduler、CD与视觉回收 |
| r2元素负例 | PASS；详见下表及[机器结果](elemental-spirit-negative-r2-20261013.json) |
| 十Hero实际链 | 完整r2 gate PASS；43目录、40品质、精确最终rawcode、无宠跨塔归属、8serial边界及全部十效果 |
| 阶段1原击/追加回归 | 完整r2入口PASS；当前决意B/不可变D/副箭排除/250HP与100D尸爆时序/Boss/试炼身份；同handle/newrevision与移除identity守卫负例也PASS |

[构建摘要](elemental-spirit-build-r2-20261013.json)记录锁定hash及完整transaction manifest的SHA。完整生产输入和日志保留在隔离构建transaction，根图与以上冻结成品SHA一致。[20正常链及全部负例结果](elemental-spirit-full-r2-20261013.json)来自最终r2成品完整工具入口；另保留[r1正常链结果](elemental-spirit-normal-r1-20261013.json)作历史对照。

### r2 延迟/所有权负例

- 24：原主击致死仍3秒后传播一次；0原发tick、6弱邻居tick、只有1代。
- 29：12个受其它来源保护的目标占满身份表，第13个不能获得孤立控制；取消保留其它12来源。
- 原生控制order拒绝：回滚本次readyAt/token，下一次控制仍可成功，不错误刷新保护窗。
- 33：同epoch试炼死亡补位分别使用新handle及复用旧handle/newrevision；16旧邻居命中、替换目标0命中。
- 可选AddSpecialEffect返回null：仍准确140D，0视觉句柄，不改变命中授权。
- source invalidate/终局：task/visual/active-index归零，未触发的连爆不再伤害。
- 37：两来源不叠加；取消任一仍保留另一。Boss输入100：双来源与单来源均66.4，tagged命中66.4一次，全部取消回58；减速同样独立。
- 现有0.5终局callback：在真实popped追加包的UnitDamageTarget栈内gameover并清理，busy仍真且pet/records/callback存活；return后才允许销毁。再次调用同一个callback实际销毁records/pet并释放周期timer，scheduler随后自行释放自身周期timer，记录销毁前CD仍1000。
- 独立审查另直接执行真实scheduler tick体：效果damage栈内shutdown仍计executing=1并阻止记录销毁，返回后count归零；未post原击同样拒绝。不以谓词stub替代此证据。

### 复现

```bash
python3 tools/VerifyPetUIArtifact.py ExampleMap.w3x
python3 tools/VerifyElementalPetArtifact.py ExampleMap.w3x --report elemental-result.json
python3 tools/VerifyPetHeroArtifact.py ExampleMap.w3x
python3 tools/VerifyPetAttackArtifact.py ExampleMap.w3x
python3 tools/BuildElementalPetUiAssets.py --verify-only
```

这些工具只读取已冻结地图，使用MPQ内实际JASS函数及物编。物理原击D输入、时间、可枚举unit、原生Buff接受/拒绝与特效句柄为明确受控边界。每个native周期callback作为独立有界解释器turn，不据此宣称实际引擎操作上限、FPS或量化调度性能。Hero的split impact、full-storm completion、corpse death和accepted-shield通知使用明确受控入口刺激；没有把这些hook回放扩大为原生投射物/整轮风暴/尸爆/Buff的引擎全流程验证。

## 未验证与残余风险

Warcraft III 1.27a实机模型/相机/动画、20特效可辨识度、控制Buff实际显示、野精灵道路运动、多人同步排队事件及性能尚未观测。门禁证实的是源码与实际成品链/所有权/数值/身份，不是实机视觉或性能验收。此范围没有按用户要求跳过的源码或构图阶段。
