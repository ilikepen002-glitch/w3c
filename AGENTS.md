# 契灵守卫战 · Y3 / KK

本目录是正式工程与唯一维护源。用户已于 2026-10-23 明确恢复并行工作；独立任务可分派，但必须限定文件所有权，不覆盖他人修改。启动编辑器与游戏暂由用户处理；其余已授权开发工作自主完成。

## 源码与版本

- Lua 权威源码在 `development/src/`，离线测试在 `development/tests/`。`maps/EntryMap/script/main.lua` 和 `script/spirit/` 是部署副本，改源后执行 `python development/tools/deploy.py`。
- 编辑器原生数据、UI、资源包及元数据属于源码。`custom/CustomImportRepo.local`、运行日志和锁是本机产物；不提交。保存原始图像和生成提示词。
- 官方 Lua 库位于 `maps/EntryMap/script/y3/`，不直接修改其实现；依赖更新单独核对版本及变更。
- 当前开发分支 `codex/y3-spirit-defense`，远程 `origin` 继续使用原 w3c 仓库。旧 Wurst 版本由 `backup/wurst-before-y3-20261023` 标签保存。未要求时不改 master，不强推，不删除旧分支或标签。

## 技能与工具

- 项目整体开发读 `.codex/skills/y3-map-dev/SKILL.md`；编辑器连接/操作读 `y3-editor-control`。
- 物编用适配后的 `y3-obj-edit`；UI 文件生成用 `y3-ui-pipeline`；Lua 开发审查用 `y3-lua-pipeline`；资源用 `y3-resource-import`。
- 官方脚本、模板和知识优先复用。只为项目独有逻辑或已证实的工具缺口写新工具；先查 `.codex/skills-installation.md` 和 `development/docs/upstream-tools.md`。
- 当前会话发现的工具、真实库签名和编辑器版本优先于旧教程。工具结果核验错误正文及读回状态；写入超时不盲目重试。
- 本地 UI 只提交意图，同步逻辑负责费用、随机、归属和版本校验。不得让本地显示/摄像机结果决定同步状态。

## 验证与交付

- Lua 修改运行 `python development/tools/check.py`；UI 修改加 `python development/tools/check.py ui`；运行时同步接线修改加 `python development/tools/check.py runtime`；音效修改加 `python development/tools/check.py audio`；战役数值/推进修改加 `python development/tools/check.py campaign`（含单人与四玩家场景）。
- 修改后部署并核对源文件哈希。离线通过、编辑器加载、实际操作通过分别报告，不互相替代。
- 技能/文档只做静态和引用检查。原始二进制资源不靠单元测试证明显示效果。
- 截止时间为 2026-10-24 01:10 Asia/Shanghai；到点保存进度并停止，未实现的完整可玩目标不得标为完成。
