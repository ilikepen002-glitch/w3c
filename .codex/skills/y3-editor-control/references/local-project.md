# 契灵守卫战本机事实

这是 2026-10-23 的定位记录，不保证下次运行状态不变。执行前做针对性核对。

| 用途 | 路径 |
| --- | --- |
| 开发源码与检查/部署工具 | D:\Y3Projects\SpiritDefense\development |
| 编辑器正式工程 | D:\Y3Projects\SpiritDefense\header.project |
| 当前主地图 | D:\Y3Projects\SpiritDefense\maps\EntryMap |
| 编辑器安装 | E:\y3 |
| 最初创建的工程，保留 | E:\y3\games\2.0\game\LocalData\ProjectName001 |
| 官方 Lua 库研究副本 | D:\Y3Projects\tooling\y3-lualib |
| 官方开发助手源码 | D:\Y3Projects\tooling\y3-helper |
| 实际 VS Code CLI | E:\Microsoft VS Code\bin\code.cmd |

当前 shell 的 code 指向 QoderCN，检查扩展时使用上表中的绝对路径。现已安装市场版本 sumneko.y3-helper 2.4.0 及其依赖；源码研究版本为 2.4.1。服务尚未验证激活，不能说运行时工具已接通。

地图 ID：`158606555474389256476812947136529777614`。旧原生日志证明曾加载地图及当时版本的初始化，不代表之后的特效、UI、重新开局已经实测。

2026-10-23 本次只读复核：8765 已监听，get_map_info 返回“Error: 请先打开地图。”。这说明接口可响应，但没有取得目标工程信息；不得在此状态下调用修改工具。

## 现有工具

- `development/tools/editor_mcp.py`：已使用过的 8765 SSE 客户端；无参数读取工具列表，`get_map_info` 只读查询工程。它是项目工具，不是完整官方 SDK；业务错误可能仍以进程退出码 0 返回，必须查看响应正文。
- `development/tools/editor-tools.json`：之前发现的参数清单，实际调用前刷新；不是永久固定 API。
- `development/tools/check.py`：离线规则/UI/战役检查；`tools/deploy.py` 部署源码。具体参数查脚本，不使用 Wurst 构建入口。

8765 实测流程为 GET /mcp 读取 SSE 广播的 endpoint URI，再向该 URI 发送 initialize、notifications/initialized 和工具请求；响应可能从 SSE 流返回。只对明确的本机服务使用客户端。不要猜测会话 URI，不能将旧客户端当作 8766 Streamable HTTP 客户端。

## 避免重复走弯路

用户已接手启动。不要调用 game.exe：之前它打开的是英雄三国 KK 客户端，并非所需工程测试。原生点击/快捷键曾未产生变化，根因未完全确定；没有证据不归因为权限。一次进程启动返回提权要求不意味着可以自动处理系统授权窗口。

源码在工程内 development/src，部署目标在 maps/EntryMap/script。部署后核对实际文件及编辑器加载状态，避免修目标副本后被下一次部署覆盖。新项目初始化可能重写已有 Lua 库和入口，当前工程不重复初始化。
