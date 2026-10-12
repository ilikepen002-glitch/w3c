# 单 Boss 过场的实际编译验证

## 现象与环境

固定 JASS 模式/Wurst 编译链中，源码类型检查与Wurst测试通过，实际未注册hook的8波过场仍会提前return而无法进入9波。已知混合and/or打印风险详见`2026-10-11-jass-boolean-grouping.md`；本次定位说明为什么源码括号与源层测试仍不足以证明实际过场。

## 无效路径与根因

源码`(wave == 8 or wave == 24) and hasHook`的括号未保留在JASS中。实际输出`wave == 8 or wave == 24 and hasHook`，8波即使无hook仍进入hold分支，hold返回0后直接return。不能因注册API被DCE就跳过无hook推进验证。

另一个已改函数的旧问题是`role == ELITE and (wave == 12 or wave == 20 or wave == 28)`，普通20/28也会被错误判为冲刺；本次没有称其为新引入问题。

## 修复与精确证据

- 生产源将波次资格和hook存在拆成两个if；精英role不匹配时早退，再检查纯or波次。
- 所有本任务新增/修改的混合表达式定向检查，共5处显式拆分；不扩大修旧无关HUD/Ground表达式。
- 实际组合JASS资格role×wave执行432次predicate检查；mechanics总451，含冲刺/暗潮/狂怒边界。
- 生产图实际执行无hook8/24真实timer closure，30秒推进9/25且重复callback不重复推进。
- 未注册的API由生产DCE删除，通过同64生产源的独立测试图保活真实hook。递归onRelease→resume被编译为cyc状态机，必须按实际入口case绑定重放完整body和interface typeId dispatch；不能猜函数名或把hook stub为true。
- 10场景包含拒绝/接受hold、正常resume、120秒限时、旧token/重复resume、onRelease重入、全路线失守和reset后旧callback。

最终实际地图、源码、hook fixture、事务SHA和结果见`docs/validation/2026-10-12-pure-boss-rounds.md`及同名证据目录。修复后365/365 Wurst、实际生产规则/状态及独立compiled hook执行通过。没有实机timer或网络运行结论。

## 可复用经验

1. 固定编译链的逻辑安全问题必须读实际JASS并在真实输出上执行边界。
2. DCE是生产模式的一部分，API源码存在不表示实际图存在可调用函数。
3. 隔离fixture必须与生产源逐字配对，并保存测试图/源/事务指纹和staging清理证据。
4. 离线解释器对真实`exitwhen`必须清理当前loop内branch栈；增加小解释器测试，不替换业务helper。

可提炼技能：实际输出布尔边界验证、无hook生产与同源hook测试图配对、编译cyc入口的封闭case映射。
