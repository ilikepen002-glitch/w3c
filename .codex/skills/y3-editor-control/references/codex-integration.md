# Codex 与 Y3 的连接

核对日期：2026-10-24。结论：可直接使用 Codex，不要求把对话迁到 Y3Maker，也不需要为了 MCP 更换 Codex 模型服务商或 API 密钥。

## 依据与服务边界

- [官方 AI 辅助开发说明](https://163.com/y3/docs/guides/Editor/AI_Development/AssistantDevelopment) 介绍知识库、物编/UI 热更新、截图和日志，并链接外部 Agent 教程。
- [官方 y3-helper 接入源码](https://github.com/y3-editor/y3-helper/blob/main/src/mcp/mcpInfo.ts) 明确列出 Codex 配置。本次核对源码版本 2.4.1，commit `58c7dd7f4269c8c45435db79f6d25a4db0aa3d28`。
- [OpenAI MCP 接入说明](https://developers.openai.com/learn/docs-mcp) 给出 Codex MCP 添加方式；实际可用性以当前 Codex 客户端为准。

| 服务 | 默认地址 | 作用与前提 |
| --- | --- | --- |
| Y3 Editor | http://127.0.0.1:8765/mcp | 编辑器工具；须打开目标地图。本机观察到 SSE，不能当普通 JSON POST 接口使用 |
| Y3 Helper | http://127.0.0.1:8766/mcp | VS Code 打开已初始化的 Y3 工程、Y3 开发助手已激活；Streamable HTTP |
| 游戏运行时 | http://127.0.0.1:8767/mcp | 扩展教程列出的运行时服务；本机尚未验证，不以监听端口推断工具能力 |
| VSCode Operator | http://127.0.0.1:19191/mcp | 已安装扩展 `sumneko.vscode-operator` 的官方代理；可按 workspacePath 路由执行命令、附加调试与求值。2026-10-24 已实测 |

三个服务分别发现工具，不假定同名或互相替代。8766 可提供 `get_game_status`、`execute_lua`、`get_logs`、`capture_screenshot`、`read_problems_lua`、`get_ui_canvas` 等工具。启动/停止/快速重启也有接口，但须遵循当前用户的启动约定。

## 接入步骤

1. 核对实际工程根目录（包含 header.project）、主地图与 script/main.lua。VS Code 与编辑器必须指向同一工程。当前聊天工作目录可能是 Wurst 仓库，不能默认其就是 Y3 工程。
2. 检查真正的 VS Code 版本和 `sumneko.y3-helper` 扩展；参考源码要求 VS Code >=1.102。安装/升级时核对当前扩展要求，不盲目重初始化已有 Lua 项目。仅安装扩展不代表它已激活。
3. 在用户要求接入的范围合并配置，保留已有配置。推荐当前工程范围；配置示例如下，不自动写入全局配置：

```toml
[mcp_servers.y3-helper]
url = "http://127.0.0.1:8766/mcp"
```

官方还提供 CLI：`codex mcp add y3-helper --url http://127.0.0.1:8766/mcp`。执行前确认它的配置范围；不要与项目配置重复创建。原生 8765 服务传输兼容性须实测，不能从 8766 可用推断全部端口均可直接注册。

4. 开发助手通常激活即启动服务，也提供 `y3-helper.startMCPServer` / `y3-helper.stopMCPServer` 命令。按当前 Codex 客户端要求重新加载配置或会话；不要承诺写文件后本轮立即出现新工具。
5. 验收：发现工具 → 只读核对工程 → 查询游戏状态（未运行是有效状态）→ 有运行环境后再核验日志与截图。连接别的项目即视为目标连接失败。

## 已在编辑器运行，但 Helper 显示 clients=[]

此流程用于已获调试授权的开发预览。2026-10-24 在安装版 y3-helper 2.4.0、VSCode Operator 1.2.12、官方 Lua commit `000437857cd501d4a318a7355cf43af3b54cc3cc` 上实测成功；不启动或重启游戏，不写自建控制服务，不修改官方安装。

### 先恢复 Helper 服务

1. `GET http://127.0.0.1:19191/health`，确认 `workspaces` 包含目标项目；POST `/mcp` 的 `tools/list`，核对当前 `vscodeOperator_executeCommand` schema。请求头接受 `application/json, text/event-stream`。不把别的工作区的端口当作本项目。
2. 8766 未监听时，通过已有 Operator 执行官方命令：

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"vscodeOperator_executeCommand","arguments":{"command":"y3-helper.startMCPServer","args":[],"workspacePath":"D:/Y3Projects/SpiritDefense"}}}
```

3. 对 8766 完成 MCP `initialize`、`tools/list`、`get_game_status`，读取响应正文与错误。实际注册工具后才视为服务可用。

已确认的自动启动陷阱：安装版 `extension.ts` 对 `env.y3RepoUri/.git` 只接受目录，Git 子模块常见的 `.git` 文件会被误判为未初始化；上述显式启动命令绕过该守卫，无需改变 Git 结构。全局脚本只有在 `global_script/.luarc.json` 文件和 `global_script/y3` 目录均存在时启用；否则库路径是当前地图的 `script/y3`。

缺 `.y3maker/mcp_settings.json` 是 McpHub 客户端配置错误，不是 8766 绑定的前置条件。需要使用该面板时，官方空配置为 `{"mcpServers":{}}`；无需为此拷入全套规则和技能，也不能把配置文件存在视为已连接。

### 附加现有运行并接通官方 Console

根因：`y3/develop/helper/helper.lua` 的自动初始化要求调试模式且启动参数存在 `lua_dummy`；该参数由 VS Code 的 `launchGame.ts` 添加，原生编辑器运行通常没有。官方提供 `y3.develop.helper.init()` 供其他启动方式手动连接。`8765` 编辑器 MCP、`12399` Lua 调试器、Helper Console 随机端口是不同通道。

1. 确认运行属于目标地图。通过 `vscodeOperator_executeCommand` 调用 `y3-helper.attach`，`args=[]`；这正是状态栏“附加”命令，连接现有游戏，不调用 `launchGame`。单人默认调试地址为 `127.0.0.1:12399`；多人使用 `12399-playerId`，以当前配置为准。此命令会先停止已有的地图调试会话。
2. 读取 `vscodeOperator_debugStatus`，取得此次 sessionId。用 `debugControl` 暂停目标会话，再用 `debugGetThreads` / `debugGetStackTrace` 取得真实 threadId 与 frameId；每一步按本机 tools/list schema 调用，不猜 ID。
3. 向 `vscodeOperator_debugEvaluate` **显式传入当前 frameId**，`context="repl"`，求值 `y3.develop.helper.init()`。本机未指定帧时未成功，指定暂停栈帧后成功。只在开发预览操作，不使用 `force=true` 创建重复连接。
4. 用 `debugControl` 继续同一会话，让网络回调推进。无论求值成功与否，完成诊断后恢复由本流程暂停的会话；不要把游戏留在暂停状态。已由用户暂停的会话保留原状态。
5. 再查 8766 的 `get_game_status`。实测返回 `running:true`、`clients:[{slot:0,...}]`。槽位可能变化，取实际返回值；不能固定写死 0。`session_id:null` 不代表失败：原生启动没有 MCP 创建的 session。
6. 后续 `execute_lua`、`get_logs`、`capture_screenshot` 显式传 `clientSlot`。官方 `resolveClient` 支持此方式，不需要为创建 session 调用 `launch_game`。

Console 端口由助手写入 `maps/<map>/script/log/helper_port.lua`，是随机端口，本次为 64704；不要硬编码。源码 `console/index.ts` / `server.ts` 负责监听，Lua 的 `helper.init()` 读取此文件并连接。

### 后续开发预览自动重连

如任务需要在每次原生预览或已授权快速重启后连接，可在权威 `main.lua` 的“游戏-初始化”回调内、玩法启动前调用：

```lua
if y3.game.get_start_mode()==1 and y3.game.is_debug_mode() then
    y3.develop.helper.init()
end
```

`require 'y3'` 后开发模块已加载，官方函数的 `_inited` 防止与 VS Code 自动连接重复；不传 force。`get_start_mode()==1` 限定编辑器，因为 `config.debug=true` 可覆盖 `is_debug_mode()` 的平台判定。此初始化位置已源码核对；后续版本仍需实测连接。助手应先打开正确工程并下发端口文件；官方 init 在端口文件缺失时也会设置 `_inited`，不能承诺无助手启动后自动发现新端口。连接是本机开发诊断，不让连接结果参与同步玩法。

源码依据：官方 helper 的 `src/debug.ts`、`src/debugPlayerSessions.ts`、`src/console/index.ts`、`src/mcp/gameSessionManager.ts`；官方 Lua 的 `develop/helper/helper.lua`、`game/game.lua`、`init.lua`。工具返回成功、连接成功与实际画面正确是独立验证层级。

## 已有 .y3maker 的迁移

[官方页面链接的扩展教程](https://y3share.natapp1.cc/docs/Y3AI开发教程/Agent部署教程/MCP接入) 推荐 [迁移技能仓库](https://github.com/BAIMOoo/y3maker-migration-skills) 中的 `sync-y3maker-to-codex`。

它复制知识、规则、技能等到 .codex 并转换 MCP 配置，保留原始 .y3maker。确需迁移时先审阅当前版本及脚本，按 inventory → dry-run → apply → verify 执行；明确 project/user/skip 范围，保留冲突项，不把旧记忆全部提升成项目规则。源码克隆不等于技能已安装或迁移已完成。

当前工程没有 .y3maker，故尚无可迁移资产。直接使用 helper MCP 与迁移知识库是两个可分开的工作；不要为满足迁移脚本而伪造 .y3maker。

## 版本差异

官方入门页列出的 `preview_ui`、`screenshot_ui_preview`、`run_game_and_screenshot` 与本机工具清单不同。本机编辑器出现 `screenshot_ui`；helper 源码对应游戏截图工具为 `capture_screenshot`。先查清单和参数，不照旧名称重复调用。
