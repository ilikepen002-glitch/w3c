# 我的宝宝有点猛 · Y3 / KK

新地图开发底座。分支 `codex/my-baby-is-fierce`，基于旧地图分支 `codex/y3-spirit-defense` 的 `eee895be882522f91ea876aa09724d191a9888c4`。

旧玩法、场景、物编、UI、资源、专用测试和运行记录已移出工程。当前没有 `header.project` 或原生地图，不能直接启动游戏。下一阶段通过 Y3 官方工具创建新工程，再接入本仓库的资料；玩法尚未确定，不沿用旧地图塔防设定。

## 保留内容

- `.codex/skills/`：官方完整技能及代码示例，入口 `y3-game-spec/SKILL.md`。
- `.codex/rules/`、`knowledge/`、`templates/`、`tools/`：规范、知识、模板、工具。
- `AGENTS.md`：开发约束；`.codex/compatibility.md`：本项目接入说明。
- `development/vendor/y3/`：官方 Lua 库及演示、文档、测试，子模块固定原版本。
- `development/tools/`：通用 Lua 检查、部署、MCP 客户端与会话状态检查。
- `development/src/`、`tests/`：新玩法源码、测试的空目录。
- `development/requirements*.txt`：Python 依赖。本机虚拟环境保留但不提交。

## Git

仓库：https://github.com/ilikepen002-glitch/w3c

SSH：`git@github.com:ilikepen002-glitch/w3c.git`

本次创建本地分支，不自动推送。旧 Y3 分支及 `backup/wurst-before-y3-20261023` 标签保留。克隆时使用 `git clone --recurse-submodules`；已有检出使用 `git submodule update --init`。

## 开发入口

先读 `AGENTS.md`、`.codex/rules/rules.mdc` 和 `.codex/skills/y3-game-spec/SKILL.md`。项目名称已写入 `.codex/spec-config.json`。

```powershell
development/.venv/Scripts/python.exe development/tools/check.py
development/.venv/Scripts/python.exe development/tools/y3_session.py
```

无 Lua 源文件时检查工具明确输出 SKIP，不代表地图测试通过。创建原生地图后，将固定版本官方库接入地图 `script/y3`，再运行 `development/tools/deploy.py`。部署只复制业务 Lua 并校验哈希，缺工程、库或源码时拒绝部署。

## 恢复旧版本

完整本机副本：`D:/Y3Projects/backups/SpiritDefense-before-my-baby-is-fierce-20261101/`。同级 `.sha256.json` 记录 2,541 个工程文件的哈希校验；虚拟环境和 Git 内部文件不在哈希审计范围。

旧内容另移入 `D:/Y3Projects/backups/SpiritDefense-retired-content-20261101/`，不放入新分支。原目录 `.git` 缺失，本轮从原仓库及远程恢复历史后建立新分支。历史提交不包含所有旧地图本机改动，完整恢复请使用上述副本。
