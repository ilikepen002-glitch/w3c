---
name: y3-ui-pipeline
description: 创建与修改 Y3 原生界面，复用官方 HTML 转 UI 转换器、控件模板和节点树工具，核验布局、资源与 Lua 绑定。
---

# Y3 UI

UI 生成器已合并为内部资源。来源见 [安装记录](../../skills-installation.md)，热更约束见 [技术边界](../../rules/y3-technical.md)。

- 已有原生或运行时生成 UI，先确认所有权；局部改动沿用实现，不为使用转换器重建界面。
- 新建静态界面可使用 [生成器流程](references/generator.md)，转换器位于 `generator/scripts/html_to_y3_ui.py`，模板和配置仍在 `generator` 内。
- 适配问题读 [适配规则](generator/references/adapter-rules.md)；绑定、预制体、场景 UI 按需读 [UI 知识](../../knowledge/UI系统/08-UI接入实战手册.md)。
- 绑定代码使用相邻 `y3-lua-pipeline` 的 UI 参考，以实际路径、UID 和当前 API 为准。静态节点树不代表运行时才创建的控件。

明确分辨率、锚点、父容器与层级。转换器用左上原点输入、Y3 左下原点输出，避免重复翻转。Grid/ScrollView 动态子项依赖有效 prefab；BuffList 自行管理子项，不强套网格预制体。模板图标 ID 须核验在本项目可用。

外部修改顺序：保存编辑器、修改 JSON、热更 UI、核对结果、保存。异步受理后以日志/对象状态证明完成。使用当前工具列表，不能调用教程中不存在的截图/导入工具。

验证遮挡、溢出、不同宽高比、按钮命中及经济操作结果。HTML 预览或静态截图不能代替交互。既有授权内的普通布局决策直接执行，不设逐步确认。
