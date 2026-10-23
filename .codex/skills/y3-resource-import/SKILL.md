---
name: y3-resource-import
description: 查询和导入 Y3 官方模型、特效、图标、声音及本地素材，核验异步完成、资源 ID、依赖与保存结果。
---

# Y3 资源导入

来源见 [安装记录](../../skills-installation.md)，异步约束见 [技术边界](../../rules/y3-technical.md)。以当前 MCP `tools/list` 的参数为准，教程工具名只是查找线索。

1. 确认工程、资源类型和用途。官方资源先查真实 ID、名称、类别与配套；本地资源核对绝对路径和格式，生成图片须先导出实际文件。
2. 官方下载可找 `download_editor_*_resource`；图标、FBX、MDX 分别找 `import_editor_icon`、`import_editor_fbx_model`、`import_mdx`。工具须真实存在，字段按当前 schema。
3. 受理后检查日志、生成元数据、源文件和资源 ID；超时结果未知，先查状态再重试。完成后保存，再修改引用。
4. 检查实际显示。复制 PNG 或收到下载受理不等于引擎导入；查询官方目录也不能证明已下载到本项目。

资源由源文件（通常 OriginalRes）、引擎缓存（CustomImportRepo.local）和 editor_table 元数据组成。保留 ID 和依赖，不随意清缓存。资源清理可能漏识别 Lua 动态引用，不能据此批量删除。

FBX 多材质/外部贴图/独立动画应先生成资源映射，核对当前格式；文档出现过列表/字典两种 animation 结构，不能照搬。默认动画图通常要求 `idle1`、`walk`、`die`，核验真实导入名称。静态自含模型不强制无用映射。MDX 依赖正确 War3 资源库，格式支持不等于转换完整。

物编 ZIP/UI 包先检查 ID 冲突，串行等导入完成再执行依赖操作。既有授权内常规素材处理不重复询问；真正阻塞的登录/系统对话框或无法判定的破坏性覆盖需具体说明。

`scripts/check_header.py`、`scripts/check_tga.py` 只用于格式排查。物编绑定由 `y3-obj-edit` 处理，UI 包由 `y3-ui-pipeline` 处理。
