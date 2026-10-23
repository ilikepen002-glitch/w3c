---
name: y3-obj-edit
description: 查询、创建和修改 Y3 单位、技能、物品、魔法效果与投射物物编，保留对象 ID、字段类型和等级数据。
---

# Y3 物编

基于官方脚本，按当前工程和编辑器版本操作。来源见 [安装记录](../../skills-installation.md)，共同约束见 [技术边界](../../rules/y3-technical.md)。

1. 确认 `header.project`、地图和目标对象；通过当前 MCP 查询工具读取 ID 与待改字段。服务不可用时可以读取真实物编 JSON，不以模板 ID 当成现有对象 ID。
2. 按类型读取一份参数说明：[单位](reference/unit.md)、[技能](reference/ability.md)、[物品](reference/item.md)、[魔法效果](reference/modifier.md)、[投射物](reference/projectile.md)。字段语义按需查 [物编知识](../../knowledge/物编系统/01-概述.md)。
3. 优先使用 `scripts/y3_obj_edit.py`；先看 `--help`，传明确的 `-map`。脚本未支持的字段可以核对实际结构后精确编辑 JSON，或扩展脚本并测试，不猜字段。
4. 编辑器已打开时先保存，备份待改文件，再写盘、热更、读回核对，最后保存。失败先检查日志与状态，不重复创建。

脚本需要 Python 和 `mmh3`。名称/描述涉及语言文件哈希；不能只改显示名称漏掉语言条目。元组保持 `{"__tuple__": true, "items": [...]}`，等级数组中字符串与整数按实际字段保留。新 ID 先检查冲突；覆盖既有 ID 时确认它就是目标对象。修改后检查技能槽位、等级链、模型/图标引用。物编伤害字段只是数据，运行时正确引用才能造成伤害。

离线 JSON/脚本检查不能证明编辑器已加载或技能已生效；分别报告验证层级。

批量 Excel、跨场景物编迁移先查 [官方工具评估](../../../development/docs/upstream-tools.md)。旧 y3-tools 使用 Python 2.7 和覆盖式合并，不自动作为本脚本替代品运行。
