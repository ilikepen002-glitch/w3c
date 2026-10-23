---
name: y3-lua-pipeline
description: 实现、诊断和审查 Y3 Lua 玩法与界面交互，核对当前 lualib API、事件、同步边界和对象生命周期。
---

# Y3 Lua 开发与审查

沿用现有入口和模块边界。检查真实 `main.lua`、加载方式与部署来源；不根据目录存在就将 `require` 强制改为 `include`。脚本可能位于 `maps/<map>/script` 或 `global_script`，以工程为准。来源见 [安装记录](../../skills-installation.md)，约束见 [技术边界](../../rules/y3-technical.md)。

当前 lualib 实现、`meta/event.lua` 优先于参考示例。对新增或可疑调用核对函数、参数、返回类型、事件字段和时机。没搜到时继续查封装，不凭参考遗漏判定 API 不存在。优先官方封装；确需底层 API 时隔离适配并核验版本。

按任务读取参考：

- 战斗：[unit](references/unit.md)、[ability](references/ability.md)、[buff](references/buff.md)、[item](references/item.md)。
- 计时与表现：[timer](references/timer.md)、[particle](references/particle.md)、[point](references/point.md)。
- UI：[事件](references/ui-events.md)、[静态路径](references/y3-ui-static.md)、[实例](references/y3-ui-instance.md)、[绑定](references/y3-ui-bindings.md)、[本地 UI](references/y3-local-ui.md)、[场景 UI](references/y3-scene-ui.md)。
- 审查：[合并后的审查流程](references/review.md)、[API 错误参考](references/api_errors.md)。历史错误只是线索，替换前核验源码及语义。
- 系统/字段语义见 [按需知识路由](../../knowledge/INDEX.md)。

同步玩法不能依赖本地 UI、墙钟、截图、帧率或单客户端调试结果。UI 操作通过现有同步命令改变游戏状态；表现更新保持本地。多人随机数种子、调用次数和顺序保持一致。Y3 定制 Lua 5.4/定点数与普通 Lua 有差异，离线测试不能证明引擎同步。

计时器、事件、UI、特效和单位有明确拥有者与清理时机。重开/离开后旧回调不能修改新局；模块加载避免过早创建引擎对象。原生扣费/返还与业务账本不能重复执行。

按风险选择确定规则测试、语法检查、API 核对、日志及实机路径，分别报告通过层级和未验证项。已授权修复直接处理；纯审查请求不扩展成新系统。
