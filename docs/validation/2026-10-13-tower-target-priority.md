# 塔自动选敌与临漏拦截验证

## 最新状态：用户已取消路线临漏优先

2026-10-13按用户明确最新指示，已移除3秒临漏override。当前只保留远程最低当前绝对HP、近战Boss > 小队长 > 普通、同路真实范围、手动/pending优先与近战720/780。下方3秒版本及其旧20a3地图报告仅为历史验证，**不表示当前仍启用**。

- 撤销源码`d40d63b`的三个生产文件与原Astra审查基础`e02532f`逐字节相同，未改720或攻击事务；源码审查PASS。
- 新门禁`f0176bf`删除路线估算专用fixtures，保留原9个packed反例及8条正式baseline轨迹；8源码测试/16源码反例PASS。
- 实际noETA组合地图SHA256 `5d6701cf84d4910fdcae6c2eaf299ae76e640577640e416564ba8ab38fac69d5`：近出口/速度0与10000仍只按HP/Boss，选敌不读取移动速度或出口矩形，原manual/pending/在途副箭/稀疏恢复PASS；五族8条轨迹65原生命中与正式baseline逐事件相等。
- 取消实际报告见`2026-10-13-remove-route-interception-result.json`。当前其它生命周期/QoL组合改动及其审查由同批验证记录负责；此处仅核验取消路线优先，没有回滚其它新包。

## 历史3秒版本

状态：正式源码/实际地图门禁通过；Astra 最终 **PASS WITH NOTES**，无生产或产物阻塞。此版本基于正式 `4abc225181e134b8e8f9de3d2bb3b52a78fc0b6b`，保留高台禁建、VFX、行走、65%捕获和资源瘦身，不恢复126项退休图标。

## 玩法范围

- 弓箭手、小鹿全部等级/分支按真实有效射程内当前绝对HP最低；兽人、步兵、食尸鬼按Boss > 小队长 > 普通，精英与试炼为普通等级。
- 仅普通敌人估算到实际出口矩形入口 ETA≤3秒时临时优先；多个紧急目标选最小ETA，相等保留合法当前目标，没有当前目标再用基础策略/handle稳定定序。无紧急目标完全回基础策略。
- 同路、本局合法敌人。手动attack/smart锁与pending单次确认保留，pending不因ETA变化再次扫描。试炼不会扣命，永不紧急但仍可按基础策略被选。
- ETA直接读取当前原生有效速度。P1按现有next waypoint与折线尾长，末段计算到真实出口矩形首次入口；4×6固定几何槽每epoch延迟建立，缺真实区域可重试，无每怪状态、新正常timer或第二次枚举。
- 出口内普通敌人ETA=0，即使冻结/停止；出口外paused/stunned/snared/实际控制buff/非move/异常速度不估算紧急，不把免控保护deadline当冻结时长。
- 唯一ATTACKED入口先裁决再登记副箭。正常选择事务至多1自动攻击令、2次ATTACKED；同步确认后native返回false也不会补登记旧副箭。
- 无合法候选仅暂停异常源：共享0.10秒恢复器，每tick至多4源，每源查询间隔≥0.50秒，空集停表；恢复重新读取真实装备范围。
- 同批合入用户授权近战射程下限720，兽族终极B既有780保留；14远程形态及装备仅远程加射程资格不变。装备、技能伤害/概率、分裂箭目标/倍率/伤害消费/VFX预算未变。

## 风险与审查

高风险：攻击开始与副箭登记、手动命令、装备acquisition、升级/出售/死亡/owner/路线和match生命周期共同改变契约。方案与只读审查为 GPT-6 Astra，实施与修复为 GPT-6.1 Sol。

- 原事务源码审查PASS；紧急扩展`cd26b2a`源码PASS。
- 首轮扩展typecheck发现局部index重名，`ae36428`仅一致改名tailIndex；Astra确认源码PASS继续适用。
- 最终门禁源码`340479d7577537a625e13e5dbd78a2654b605596`不改变任何生产Wurst；最终actual-map审查PASS WITH NOTES。所有生产字节与正式构建输入`ae364289d30a6ab733916641f4ea0eb1ca1fdc06`相同。

## 正式检查与实际地图

- Linux完整检查默认运行后，已按失败位置修复，串行锁定typecheck与无filter全量Wurst tests均PASS；包含13索敌纯测和21近战形态矩阵。复用已过类型检查，不重复相同输入编译。
- typecheck事务`linux-c3qz1rg3`、全测试`linux-j1dt1qn8`、build`linux-wytk0wbg`三个manifest均PASS，1292项输入完全相同，工具/JDK/stdlib锁定。没有手改生成JASS，没有启动游戏。
- 实际地图5450425字节，SHA256 `20a3f200c42734c020b4cef6469a828ecdbdcd306ba07b1039a5182e922dfd78`；实际JASS SHA256 `2bbdf53d024fdfddafb7c3ef543d9dd4e9cd96a5128cd813c95d03b61a6ffc3a`。
- Runner真实MPQ的1.28 JASS、startup、UI路由和35主机active-CD门禁PASS。633 Channels/93 slot displays、15模型/贴图和75 BTN/DIS pairs实际资源门禁PASS。
- 最终索敌工具SHA256 `1623e1886c8ddf18aff2080d533f9673e7b85dbd68f666e3b41c725a5648736c`，Python测试SHA256 `95550e675304f8a432234d4785974327e2ad2763169b709902dba97fee79412c`；9项源码测试PASS。
- 最终同版本实际MPQ门禁PASS：2304基础比较/1536紧急比较、22源码mutation与21 packed mutation（原事务9+紧急12）全部拒绝。每个packed反例记录对应语义断言、异常类型及reason；未知解释器/替换异常不能算拒绝证据。
- 实际CreateRegions→PrepareGeometry：P1索引0..5、三直路、缺rect重试/epoch、非法索引/容量、当前速度与buff/免控保护、手动/pending、后枚举currentEta反例。速度300时末路点到出口入口2.741秒，到中心4.083秒，正确跨越3秒阈值。
- 原攻击事务同步/异步、native true/false、同serial新intent、销毁重建、work/cast、trial身份、range/owner/epoch/可见性、A/B/A在途主箭与旧过期callback均PASS。原伤害侧无选敌或新命令。
- 40源×40合法候选：1600次ETA、40局部group、首epoch44次区域读取、零新timer/攻击令/RNG。40暂停源恢复实测每tick≤4源、每源≥0.50秒、公平轮转，无反复Stop；失败发令/新手动命令/空集停表均PASS。

## 伤害与资产闭包

基线真实地图SHA256 `59a519fbb47761840320241f08a3b95e8a717cd38fb603e5da0911abf9a3a8eb`。五族8条有限无重选场景、65原生命中逐事件相等：原始/派生伤害、实际精灵命中计数、CD、slow/armor载体及写速、RNG序列、damage ledger和真实死亡结算gold/score。CD场景在fixture now=10时readyAt=22，即12秒冷却，并非22秒冷却。此证据不是所有输入/模式的等价证明。

245实际loadout/inventory/refresh案例PASS，另覆盖parked acquisition=0与unpark当前范围重算。35塔source/packed范围一致。基线到候选仅57个单位字段差异，均为19个近战形态的ua1r/uacq/射程文案；其余全部单位字段相同，ability/item/buff/terrain/pathing/doodad/import payload字节相同，330个保留媒体/模型资源字节相同，archive成员集相同，126退休图未回包。

完整实际索敌报告见同目录 `2026-10-13-tower-target-priority-result.json`，对象/资源闭包见 `2026-10-13-tower-target-object-resource-closure.json`。可重现：

```
python3 tools/VerifyTowerTargetPriorityArtifact.py ExampleMap.w3x --baseline-map <4abc225正式地图> --output <报告路径>
python3 tools/VerifyTowerRangeEligibility.py ExampleMap.w3x
python3 tools/AuditMapResourceReachability.py ExampleMap.w3x --require-retired-absent
python3 tools/VerifyPetUIArtifact.py ExampleMap.w3x
```

## 非阻塞备注与未验证项

额外全Python source扫描并非全绿：243 selected/197 run/183 passed，10失败、9错误，36未覆盖。全部19个异常/子测试在干净正式4abc基线定向复现，异常类型、核心缺失符号/断言与测试assertion行对应；包含旧数值/整文件锁定、退休旧图、旧Git对象及fixture依赖。设置可信stdlib可恢复其中1项。未修不相关旧断言，不以同标题掩盖新异常，不把本次定向门禁PASS称作全部Python测试PASS。

切换可能重新开始一次原生前摇，并增加转身/命令处理时间；不声称零DPS/时序影响。ETA不预测碰撞、未来解控/变速、.20秒路点推进或.25秒漏怪结算，3秒不含塔前摇/飞行/击杀次数，不保证成功拦截。suffix优化只与本估算公式等价，不是实际寻路时间绝对下界。

非自动控制期间模块不发attack/Stop，但引擎真实交付且合法的ATTACKED可登记一次原副箭契约。1.28没有可核验命令token，不能保证任意合成“Stop后旧延迟事件”必零登记；同栈intent变更、明确working/casting与恢复不覆盖玩家命令已门禁。

未启动Warcraft III；客户端前摇/转身/实际DPS、FPS、渲染与多人同步未实测。
