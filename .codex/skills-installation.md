# 官方 Y3 开发资料

恢复日期：2026-11-01。来源：`https://github.com/y3-editor/y3-maker-config`，固定提交 `b9253889d74f07145bb2bd56721f8dfc406c263c`。

本机原 `.codex` 为空，使用已存在的官方 `.y3maker` 副本恢复 skills、rules、knowledge、templates、tools，共 313 个文件。保留完整官方内容和示例；未创建自行总结的替代技能。`y3-ui-generator`、`y3-lua-review` 保持独立，`y3-memory-distill` 无官方 SKILL.md，不伪造入口。

初始安装的兼容变换为 UTF-8 BOM 移除，以及文本内 `.codemaker/`、`.y3maker/` 到 `.codex/` 的路径替换。原始与安装后 SHA256 均记录于 [manifest.json](upstream-sources/manifest.json)。项目名称在 `spec-config.json` 中独立设置。

2026-11-01 按用户明确要求追加局部流程修正：编辑器由用户提前打开 `Editor.exe`，Codex 核对地图后复用；ECA、地形模板及相关执行案中的自动重启改为请用户不保存旧内存手动重开。相关脚本仅修改说明，不改执行逻辑。原始与初始安装哈希保留，修订文件的当前哈希记录在 manifest 的 `local_sha256`，修订原因见 `local_adaptation`；这项用户指定修正不代表重写官方技能。

上游 memory 未导入本项目。旧版本完整本机副本位于 `D:/Y3Projects/backups/SpiritDefense-before-my-baby-is-fierce-20261101/`，其中 `.y3maker` 保留原始字节与来源。当前路径和接口绑定见 [compatibility.md](compatibility.md)。
