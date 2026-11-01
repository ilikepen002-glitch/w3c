# 我的宝宝有点猛 · Y3 / KK

本目录是新地图的唯一维护源；开发底座位于仓库根目录，用户新建的 Y3 原生空项目位于 `ProjectName001/`。Codex 是主要开发入口，VS Code 仅作为官方 Y3 Helper 的后台宿主。

用户于 2026-10-24 明确授权自动完成地图开发及所需环境安装、配置和维护，包括测试游戏控制、调试连接、资源导入、物编/UI/Lua 修改、部署与验证。用户于 2026-11-01 更新编辑器使用约定：每次需要编辑器时，先提醒用户提前打开 `Editor.exe` 和目标地图，由 Codex 核对身份后复用；已明确打开时直接核对复用。编辑器路径为 `E:/y3/games/2.0/game/Editor.exe`，不得把 `game.exe` 当作编辑器启动。Codex 不自行启动、关闭或重启编辑器；需要重开时请用户操作，重新连接后读回地图身份。此约定取代此前编辑器启动/重启授权。对当前开发任务内已授权动作自主执行，不因官方技能中的重复确认步骤再次询问；需要决策时优先依据既定目标和合理默认值推进。

独立任务可并行，但必须限定文件所有权；对同一地图的编辑器写入、导入与保存串行执行，不覆盖他人修改。自动化仍须读回结果，不能用受理成功、占位返回值或旧测试报告宣布完成。

## 源码与版本

- Lua 权威源码在 `development/src/`，离线测试在 `development/tests/`。部署目标为 `ProjectName001/maps/EntryMap/script/`；现有 `development/tools/deploy.py` 尚按仓库根目录查找 `header.project`，首次 Lua 开发前须适配该原生工程路径、接入官方库，再执行部署并核对哈希；不要写入官方库。
- 编辑器原生数据、UI、资源包及元数据属于源码。`custom/CustomImportRepo.local`、运行日志和锁是本机产物；不提交。保存原始图像和生成提示词。
- 官方 Lua 库保留在 `development/vendor/y3/`（包含官方示例），尚未接入 `ProjectName001/maps/EntryMap/script/y3/`，不直接修改其实现；依赖更新单独核对版本及变更。
- 当前开发分支 `codex/my-baby-is-fierce`（我的宝宝有点猛），旧地图分支 `codex/y3-spirit-defense` 保留，远程 `origin` 继续使用原 w3c 仓库。旧 Wurst 版本由 `backup/wurst-before-y3-20261023` 标签保存。未要求时不改 master，不强推，不删除旧分支或标签。

## 技能与工具

- 用户于 2026-10-24 明确禁止使用 `computer-use` 技能。开发与验证使用 Y3 官方 MCP、运行时接口和工程工具；不得改用其他桌面自动化绕过此限制。用户已打开地图时直接核对身份并复用，不重复启动。运行时事件验证与物理鼠标键盘验证须分开报告。
- 只安装和使用 `y3-editor/y3-maker-config` 官方 Y3 技能正文，不再维护自行总结的 Y3 技能。已删除 `y3-map-dev`、`y3-editor-control`；不得重建同义替代技能。Codex 所需路径/frontmatter 修正单独记录，不用自己的摘要替换官方流程。
- 开发入口为 `.codex/skills/y3-game-spec/SKILL.md`；按其官方路由调用环境、物编、UI、Lua、审查、资源、地形、ECA、模板和测试技能。`y3-ui-generator` 与 `y3-lua-review` 保持官方独立目录。`y3-memory-distill` 尚无官方 SKILL.md，仅保留草案与脚本。
- 先读 `.codex/rules/rules.mdc`，任务相关专题按该索引加载；`.mdc` 本身不自动生效，由此显式接入。知识与功能模板使用 `.codex/knowledge/`、`.codex/templates/`。来源和完整性见 `.codex/skills-installation.md`。
- 官方技能的客户端差异、本项目路径和当前工具绑定见 `.codex/compatibility.md`；这是接入配置与已证问题记录，不是替代技能。用户授权和当前真实 API 优先于上游旧示例；上游其他项目的 memory 不作为本项目事实或授权。
- 官方脚本、模板和知识优先复用。只为项目独有逻辑或已证实的工具缺口写新工具；不为套用教程重建/删除现有 Lua 库或覆盖整张地图。写入前核对范围并保留可恢复版本。
- 当前会话发现的工具、真实库签名和编辑器版本优先于旧教程。工具结果核验错误正文及读回状态；写入超时不盲目重试。
- 本地 UI 只提交意图，同步逻辑负责费用、随机、归属和版本校验。不得让本地显示/摄像机结果决定同步状态。

## 验证与交付

- Python 使用 `development/.venv/Scripts/python.exe`，依赖见 `development/requirements.txt` 与 `development/requirements-tools.txt`；Windows x64 / Python 3.13 的已验证版本锁在 `development/requirements-tools.lock.txt`。下述 `python` 均指此解释器。
- Lua 修改运行 `python development/tools/check.py`；新增功能时创建有意义的 `development/tests/<名称>.lua`，用 `python development/tools/check.py <名称>` 执行。旧地图专用测试已移除，空源码输出 SKIP，不当作验收通过。新 UI、同步、音效及推进逻辑仍须按实际改动验证关键路径和多人边界。
- 修改后部署并核对源文件哈希。离线通过、编辑器加载、实际操作通过分别报告，不互相替代。
- 技能/文档只做静态和引用检查。原始二进制资源不靠单元测试证明显示效果。
- 上一轮完整可玩版本任务截止于 2026-10-24 01:10 Asia/Shanghai；该轮到点保存并停止，未实现目标不得标为完成。此时间不作为后续明确新任务的截止时间；新任务遵循用户另行指定的范围与期限。

## 新地图初始化状态（2026-11-01）

- 已按用户要求清空旧地图内容，保留技能、规范、知识、模板、官方示例与通用工具。用户已新建原生空项目，2026-11-01 已读回磁盘上的 `ProjectName001/header.project` 与 `ProjectName001/maps/EntryMap/header.map`。
- 仓库根目录：`D:/Y3Projects/SpiritDefense`；原生工程根目录：`D:/Y3Projects/SpiritDefense/ProjectName001`。上游工具所称“项目根目录”若指含 `header.project` 的目录，应使用后者；`.codex/` 与 `development/` 仍在仓库根目录。
- 原生工程名 `ProjectName001`，项目 ID `71686893234877021280706013443497255478`；入口 `EntryMap`，地图 ID `72334914161781466780286770881149919798`。产品名仍为“我的宝宝有点猛”，不擅自重命名或搬动原生工程。核对 ID 时保留整数精度，不转为浮点数。
- 当前保留编辑器默认数据、UI 与触发器；`script/main.lua` 仅含默认注释，尚无业务 Lua。原生空项目已落盘不等于开发接入或可玩验收完成。
- 本次本机 Editor MCP `127.0.0.1:8765` 连接被拒绝，未核验编辑器当前打开的地图，也未运行游戏。后续编辑前须重新连接并读回工程路径与地图身份；不得将磁盘检查或旧报告当作运行验收。
- 原 `.git` 缺失，已从原仓库及远程恢复；旧分支 HEAD 为 `eee895be882522f91ea876aa09724d191a9888c4`。
- 完整旧工程备份在 `D:/Y3Projects/backups/SpiritDefense-before-my-baby-is-fierce-20261101/`；不得把旧版本测试报告当作新地图证据。
- 开发流程入口与官方库路径不同于上游默认值时，以 `.codex/compatibility.md` 为准。继续使用用户新建的空项目，不自动重建旧地图。
