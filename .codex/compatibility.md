# Codex / Y3 接入配置

更新：2026-11-01。新地图：我的宝宝有点猛。本文仅记录客户端和工程绑定，不替代官方技能。

- 当前根目录 `D:/Y3Projects/SpiritDefense`；官方配置目录为 `.codex`。上游 `.codemaker/`、`.y3maker/` 前缀已机械替换为 `.codex/`，技能正文未摘要或重写。
- 官方来源与逐文件 SHA256 见 [安装说明](skills-installation.md) 及 [清单](upstream-sources/manifest.json)。上游 memory 属于其他项目，没有作为新地图事实导入。
- 官方库现在位于 `development/vendor/y3/`，固定 `000437857cd501d4a318a7355cf43af3b54cc3cc`；其 `演示/` 为官方例子。创建原生地图前，不因上游默认路径不存在而重新下载或重建旧图。
- 当前无原生工程文件，无游戏运行验收记录。`.codex/spec-config.json` 已设置新名称。
- Python：`development/.venv/Scripts/python.exe`。依赖文件在 `development/`；虚拟环境不提交。
- Y3 Editor MCP 使用本机 `http://127.0.0.1:8765/mcp`；通用客户端 `development/tools/editor_mcp.py`。先获取真实 tools/list，再调用和读回身份。
- Y3 Helper MCP 通常为 `http://127.0.0.1:8766/mcp`，需官方 VS Code Helper 后台宿主。Runtime MCP 通常为 `http://127.0.0.1:8767/mcp`。端口和工具签名需在后续会话重新核验。
- `development/tools/y3_session.py` 只读进程/端口，不能证明地图就绪。`runtime_mcp.py` 触发运行时 UI 事件，不能代表物理鼠标验收。
- 明确禁止 computer-use 或其他桌面自动化绕过。开发使用官方 MCP、运行时和工程工具。
- 官方技能中的再次授权要求服从 AGENTS.md 与用户已有授权；异步导入、热更和保存仍要串行核验，超时不盲目重试。
- 本轮只进行仓库初始化及静态检查；上游健康检查中的既有缺项应按实测记录，不能将其当成新地图可玩证据。
- 官方健康检查提示 `y3-lua-pipeline/references/y3-ui-instance.md` 为 436 行、接近 500 行阈值；原样保留，不为通过行数检查精简官方正文。上游缺失的 `../../USER_GUIDE.md` 由项目导航页补齐。
