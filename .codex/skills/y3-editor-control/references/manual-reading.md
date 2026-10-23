# 教程阅读记录与检索入口

2026-10-23 阅读 [Y3 产品手册](https://163.com/y3/docs/guides/Editor/About) 目录下 132 个独立页面的文字正文，涵盖入门、项目设置、场景、资源、系统功能、ECA、UI、物编、调试、云脚本及发布。图片和视频未逐一观看，Lua API 全集未逐项核验。文字很短或为空的模板页面不能视为完整操作教程。

本机索引 `D:\Y3Projects\SpiritDefense\development\docs\official\manifest.json` 保存每页标题、URL、缓存文件名、字符数、图片引用及哈希；正文缓存同目录，合计约 18.6 万字符。该缓存用于定位出处，技能只保存影响操作决策的归纳，不复制整套手册。遇到具体字段争议，再读取对应原文、图片或当前源码。

| 问题 | 优先入口 |
| --- | --- |
| Codex、MCP、AI 知识库 | [AI 辅助开发](https://163.com/y3/docs/guides/Editor/AI_Development/AssistantDevelopment)；[本技能接入说明](codex-integration.md) |
| 工程、地图和入口 | [项目管理](https://163.com/y3/docs/guides/FunctionManual/MapSetting/multilevel/multilevel) |
| 场景编辑与地图大小 | [工具面板](https://163.com/y3/docs/guides/FunctionManual/ScenarioEditor/Tool_Palette) |
| UI 与精灵管理面板 | [画板](https://163.com/y3/docs/guides/FunctionManual/UI_Editor/Panel)；[定位适配](https://163.com/y3/docs/guides/FunctionManual/UI_Editor/Positioning_and_Adaptation) |
| 单位/技能/表现挂接 | [挂接指引](https://163.com/y3/docs/guides/FunctionManual/Object_Editor/Hook-Up-Guidance-Process) |
| 资源与模型导入 | [资产导入导出](https://163.com/y3/docs/guides/FunctionManual/Resource_Manager/Import-Export) |
| 调试、日志与性能 | [调试信息](https://163.com/y3/docs/guides/FunctionManual/Debug&Test/DebuggingInformation)；[LuaTracy](https://163.com/y3/docs/guides/FunctionManual/Debug&Test/LUADeveloperDocumentation/LUA_Tracy) |
| 存档、服务器状态 | [云脚本](https://163.com/y3/docs/guides/FunctionManual/CloudScript) |
| 联机差异 | [不同步相关](https://163.com/y3/docs/guides/CommonProblem/Asynchronous) |

## 已发现的资料边界

- AI 入门页的一部分工具名称与当前编辑器/助手实际清单不同，按运行中工具 schema 操作。
- 部分旧发布教程使用 header.map，本机新工程为 header.project；不可照旧文重命名当前工程。
- 存档相关新旧页面的限制存在差异，实际改存档前核对当前版本、服务端能力和项目现有数据。
- 外部 Y3AI 教程由官方页面链接，但其建议与迁移脚本仍需审阅；不自动把第三方规则覆盖进 AGENTS.md，不按教程替换现有 Codex 登录和模型配置。
- 阅读发布/商城教程不代表地图已发布，当前本地开发无须执行商业化配置。
