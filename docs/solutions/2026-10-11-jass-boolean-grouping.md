# 固定 JASS 编译器的布尔分组丢失

## 现象与影响

固定 Wurst 编译器能通过 Wurst 类型检查与源语言测试，但某些含括号的 `and` / `or` 组合在最终 JASS 中失去必要括号。源测试成功不能证明真实地图语义一致。

已发布基线 `1aa173eefab2c2a4549515fd8aa3998c3f1b799a` 的地图 SHA256 为 `45cf1f19582729274851e543f6561439694a729b75cf793572bdcd38a2f7703c`，已包含以下适配与技能约束问题。本次离线审查又确认了同源的路线存活敌人筛选问题。未将它们归因于鼠标、客户端或原生弹窗事件。

固定 compiler SHA256：`ab3ce798fb1bca4802d64cfe27accd384abc5d68be2097b4e27f77251bd143e5`。脚本模式 JASS，项目目标补丁 v1.28。

## 精确源码与产物反例

1. `wurst/pets/TDPetCombat.wurst`，`tdPetSkillFitsAbilities`：
   - 源：`(skill != 9 or hasSplitArrow) and (skill != 10 or hasCorpseExplosion)`
   - 旧产物：`skill_1 != 9 or hasSplitArrow and skill_1 != 10 or hasCorpseExplosion`
   - 技能10且两种宿主能力均无：源语义 false，产物 true。
   - 技能9仅有尸爆能力：源语义 false，产物 true。
   - 基线源第30行，对应基线 JASS 第9445行。
2. `wurst/pets/TDPetRules.wurst`，`tdPetSkillAllowed`：
   - 源：`not numeric and (slot != 1 or universal) and (not hasActive or not activeSkill)`
   - 旧产物：`(not numeric) and slot != 1 or universal and (not hasActive) or (not activeSkill)`
   - 栏1、技能0、无重复、无主动：应否决数值技能，产物却 true。
   - 栏2、技能13、已有主动：应否决第二主动，产物却 true。
   - 基线源第42行，对应基线 JASS 第17053行。
3. `wurst/TDSpawn.wurst`，`tdLaneEnemyCheckEnum`：
   - 源：`eligible and (wantedWave == 0 or actualWave == wantedWave)`
   - 旧产物：`eligible and wantedWave == 0 or actualWave == wantedWave`
   - 外层资格 false 但波次匹配：应否决，产物 true；野生、外路、死亡或非敌方单位可能绕过前置限制。

以上缩写仅用于可读说明；验证读取的是地图内完整函数和真实字段。

## 独立证明与根因

不是依据 Python 自写表达式解析器推断：`tools/VerifyJassBooleanGrouping.java` 使用固定 jar 内独立的 `net.moonlightflower.wc3libs.antlr.JassParser.bool_expr()`，打印真实 parse tree，并求值五组成对反例。独立语法将 `and` 放在 conjunct 层，`or` 放在外层 disjunct；保留源码括号与旧产物的五组成对结果均不同。

`javap -c -p` 检查固定 jar 的 `de.peeeq.wurstscript.jassprinter.JassPrinter$2`：`case_JassOpAnd` 返回 0，`case_JassOpOr` 返回 1。`ExprPrinter` 按子优先级小于父优先级决定是否加括号，解释了为何这里省略 `or` 子表达式所需括号。原始证据与 parse tree 见 [验证记录](../validation/2026-10-11-jass-boolean-grouping-proof.txt)。

不能只在 Wurst 源中增加更多括号；该路径会再次由打印器处理。也不能只依赖既有 Wurst 测试，它们运行的是源语言语义。

## 最小修复

- 宿主适配：技能9直接返回分裂箭能力，技能10直接返回尸爆能力，其他技能返回 true。
- 技能约束：保留非法/重复否决与首栏数值规则；后续依次早退否决数值、栏1非通用、第二主动；最后返回 true。
- 路线筛选：先早退否决 null、已找到、野生、死亡、非敌方或外路；再单独否决非零目标波次不匹配；最后才设置 found。
- 新弹窗快捷键与模式规则同样用独立分支，不依赖混合 `and/or` 生成分组。

没有修改编译器、固定标准库、概率、技能类别、共鸣限制、宿主能力或全局胜负规则。本批仅修复这三处已证实且与捕获/洗练/野生排除直接相关的既有路径；其它系统不做全面重构。

## 验证与边界

- Wurst 全量 typecheck 与 289/289 测试通过，保留先前塔升级回归。
- 最终 Python 114/114 测试通过；真实地图 JASS 验证宿主能力64组合、技能类别/主动/重复mask共2176组合、路线资格与波次256组合；并保留旧产物反例及对应坏突变测试。数字键102组合与10项真实物编/脚本验收也全部通过。
- Java 独立语法反例证明可重跑：

```sh
java --source 25 --class-path <固定wurstscript.jar> tools/VerifyJassBooleanGrouping.java
python3 -m unittest discover -s tests/python -v
python3 tools/VerifyPetUIArtifact.py ExampleMap.w3x
```

固定 Linux 离线入口完成检查与构建，最终成品信息见 [精灵释放验证](../validation/2026-10-11-pet-release-rewards.md)。未执行 Windows bat、World Editor、Warcraft III 或用户电脑操作；语法/产物证据不等于实机行为观察。原生鼠标点击问题仍未复现，不能宣称已找到或验证其根因。

## 同类审计的剩余范围

只读检查仍发现四处既有中低影响问题，本批不扩改，也不宣称全图没有逻辑缺陷：

- `TDEnemyMechanicData.tdEnemySprintEnabled`：普通敌人在20/28波可能被分组失真误判为冲刺资格；原生速度上限的实际影响未观察，属中等玩法/平衡风险。
- `TDEnemyMechanicData.tdEnemyMechanicTracked`：BOSS类别可能在任意波被纳入跟踪；正常出生的BOSS均在8/16/24/32波，单独的过宽分支在当前正常出生配置中不触发，属中低生命周期/性能风险。
- `TDGroundItemRuntime.tdGroundCaptureItem`：收集队列的前置筛选可能过宽，后续移动/消费仍完整重验可用性，没有证实偷取、销毁或重复产物；未支持的group0物品可能访问未初始化队列，属中等健壮性风险，原生结果未观察。
- `TDDamageHud.tdDamagePrepareHud`：单路视图可能绕过active/rank筛选、重复同路四行；不改变伤害记账或经济，属低影响显示问题。

宠物WildState终态与教学必成表达式在最终JASS中保留正确分组；当前释放/所有权/容量/状态与本批三个改写后的资格守卫没有这类未分组混合表达式。后续应独立审查固定编译器修复/升级及全图语义回归；本批不修改依赖或工具链，也未查询上游修复状态。

## 可复用经验

涉及组合资格、状态筛选、材料消费或能力适配时，应核对最终 JASS，尤其是含括号的混合 `and/or`。源测试与真实产物语义枚举互补；对疑难编译差异，优先用独立语法工具和编译器字节码交叉验证。固定工具无法立即升级时，最小早退分支比依赖括号打印更稳妥。
