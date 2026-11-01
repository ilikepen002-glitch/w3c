# 官方 Y3 开发资料

恢复日期：2026-11-01。来源：`https://github.com/y3-editor/y3-maker-config`，固定提交 `b9253889d74f07145bb2bd56721f8dfc406c263c`。

本机原 `.codex` 为空，使用已存在的官方 `.y3maker` 副本恢复 skills、rules、knowledge、templates、tools，共 313 个文件。保留完整官方内容和示例；未创建自行总结的替代技能。`y3-ui-generator`、`y3-lua-review` 保持独立，`y3-memory-distill` 无官方 SKILL.md，不伪造入口。

允许的兼容变换仅为 UTF-8 BOM 移除，以及文本内 `.codemaker/`、`.y3maker/` 到 `.codex/` 的路径替换。原始与安装后 SHA256 均记录于 [manifest.json](upstream-sources/manifest.json)。项目名称在 `spec-config.json` 中独立设置。

上游 memory 未导入本项目。旧版本完整本机副本位于 `D:/Y3Projects/backups/SpiritDefense-before-my-baby-is-fierce-20261101/`，其中 `.y3maker` 保留原始字节与来源。当前路径和接口绑定见 [compatibility.md](compatibility.md)。
