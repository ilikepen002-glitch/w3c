# 弓箭连续攻击与分裂起手恢复

## 现象与边界

弓塔在新增自动目标优先级后出现连续起手分裂登记被吞、攻击中途重选目标的行为。实际客户端为 Warcraft III 1.27a；项目仍按原配置生成 JASS/v1.28。用户要求恢复早期顺畅版本，并明确拒绝改成主箭命中后才发副箭。

本次只恢复 catalog 识别的7种 ARCHER；其余28种塔保留当前目标优先级。没有整图回滚或改变攻击点、射程和旧TTL。

## 诊断方法和根因

只看当前副伤回调不足以定位，因为没有主箭对应的起手记录时，回调会正确地不产生副伤。必须把原生 ATTACKED、重下单、volley登记、原生主伤和expiry放在同一条链上检查。

历史源码及真实旧地图对照表明，Oct8 的 dbcbf14 仍采用 ATTACKED 直接登记并立即显示全部副箭。最近无优先级的对照是4abc225；68f8224引入新的ATTACKED接受门、重定向与park/recovery。该门在原生A起手而B血更低时可发出新的attack命令并拒绝A登记；在“原A主伤仍到达”的控制边界下，会出现没有A记录、没有A副伤的结果。这是可回放的脚本契约，不等于已测得1.27a的所有原生事件顺序。

单独恢复全箭显示无法消除接受门造成的起手吞登记。延长TTL也不能作为此次历史恢复的根因修复，因为旧源码和旧地图已经存在相同的flight+.35到期规则。主命中晚发副箭会改变用户要求的攻击表现，本次没有采用。

## 定向修复

- ARCHER的唯一ATTACKED入口读取现有施工/出售/施法/精灵忙碌安全状态，然后直接登记分裂，不创建或消费priority令牌，不重选/重发attack或stop。
- 对ARCHER排除priority的order、redirect、park和recovery控制。误留队列的弓塔取消pending、移出park并恢复真实射程，不发新命令。
- 装备刷新让弓塔直接使用当前effective range；其余族保留park投影。光环使用的working状态与全局priority事件注册仍保留。
- 分裂选靶、共享全箭视觉timer、immutable原伤、装备额外箭、pet impact、trial上下文和当前升级继承不变。
- 保留7df0ac0的生命周期修复：consume仅出队，expiry独占销毁；不可复制旧实现里命中立即destroy的部分，否则旧timer可能删掉复用的对象。

所有支持的塔移除路径均清理sale state：出售、拒绝建造、原生建造取消、死亡。未发现需要增加新handle身份系统的实际残留路径。

## 验证

官方检查与构图使用tools/Run-WurstLinux.py及现有锁定工具链，完整typecheck、Wurst tests、打包门禁通过。实际候选地图SHA256：c0f210f906b9d3437d5040be09373797387147e4acf224565ffbc3dcf657d67f。

定向命令：

- python3 tools/VerifyTowerTargetPriorityArtifact.py ExampleMap.w3x
- python3 tools/VerifySplitArrowVisualBudget.py ExampleMap.w3x
- python3 tools/VerifyTowerRangeEligibility.py ExampleMap.w3x

实际packed回放覆盖7弓各6次稳定目标与30次变HP/变主目标，共252次逐发登记、立即全副箭与11/23/37真实副伤；28塔原交易/手动锁/recovery回归；旧expiry对象复用；装备、pet、trial换代和deferred数据。26项source及18项packed负突变均被具体语义断言拒绝。另有1120箭同时在途清理和245组装备射程回放。

候选地图427个成员中，相对前一正式版只有war3map.j和时间标签war3map.w3i变化，其他物编和资源字节一致。完整证据和广域Python旧失败基线对照见[本次验证目录](../validation/2026-10-15-archer-native-flow/README.md)。广域旧Python suite未全绿，不能冒称整套PASS。

## 残余风险与经验

没有启动客户端，不能宣称已实测1.27a视觉顺畅度、前摇、转身、FPS或多人同步。旧TTL及原生取消后不可观测的导弹身份边界仍保留；不能把有限窗口内的回放扩大成全时序保证。

定位这类问题应先恢复用户认可的事件契约，再保留后续独立安全修复；历史回退不应照抄旧整文件，也不能把后来的生命周期修复一并退掉。
