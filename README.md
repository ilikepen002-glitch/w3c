# 我的宝宝有点猛 · Y3 / KK

新地图开发底座。分支 `codex/my-baby-is-fierce`，基于旧地图分支 `codex/y3-spirit-defense` 的 `eee895be882522f91ea876aa09724d191a9888c4`。

旧玩法、场景、物编、UI、资源、专用测试和运行记录已移出工程。用户已创建 Y3 原生空项目 `ProjectName001/`，入口地图 `EntryMap`，保留编辑器默认数据。已核对磁盘工程文件，尚未接入官方 Lua 库或完成游戏运行验收；玩法尚未确定，不沿用旧地图塔防设定。

## 保留内容

- `.codex/skills/`：官方完整技能及代码示例，入口 `y3-game-spec/SKILL.md`。
- `.codex/rules/`、`knowledge/`、`templates/`、`tools/`：规范、知识、模板、工具。
- `AGENTS.md`：开发约束；`.codex/compatibility.md`：本项目接入说明。
- `development/vendor/y3/`：官方 Lua 库及演示、文档、测试，子模块固定原版本。
- `development/tools/`：通用 Lua 检查、部署、MCP 客户端与会话状态检查。
- `development/src/`、`tests/`：新玩法源码、测试的空目录。
- `development/requirements*.txt`：Python 依赖。本机虚拟环境保留但不提交。
- `ProjectName001/`：用户新建的原生工程，包含 `header.project` 与 `maps/EntryMap/`。仓库根目录与原生工程根目录不同，路径绑定见 `AGENTS.md`。

## Git

仓库：https://github.com/ilikepen002-glitch/w3c

SSH：`git@github.com:ilikepen002-glitch/w3c.git`

开发分支跟踪 `origin/codex/my-baby-is-fierce`。旧 Y3 分支及 `backup/wurst-before-y3-20261023` 标签保留。克隆时使用 `git clone --recurse-submodules`；已有检出使用 `git submodule update --init`。

## 开发入口

先读 `AGENTS.md`、`.codex/rules/rules.mdc` 和 `.codex/skills/y3-game-spec/SKILL.md`。项目名称已写入 `.codex/spec-config.json`。

```powershell
development/.venv/Scripts/python.exe development/tools/check.py
development/.venv/Scripts/python.exe development/tools/y3_session.py
```

无 Lua 源文件时检查工具明确输出 SKIP，不代表地图测试通过。首次 Lua 开发前，需将 `development/tools/deploy.py` 的原生工程路径适配到 `ProjectName001/`，将固定版本官方库接入 `ProjectName001/maps/EntryMap/script/y3/`，再部署业务源码。部署只复制业务 Lua 并校验哈希，缺工程、库或源码时拒绝部署。

## 恢复旧版本

完整本机副本：`D:/Y3Projects/backups/SpiritDefense-before-my-baby-is-fierce-20261101/`。同级 `.sha256.json` 记录 2,541 个工程文件的哈希校验；虚拟环境和 Git 内部文件不在哈希审计范围。

旧内容另移入 `D:/Y3Projects/backups/SpiritDefense-retired-content-20261101/`，不放入新分支。原目录 `.git` 缺失，本轮从原仓库及远程恢复历史后建立新分支。历史提交不包含所有旧地图本机改动，完整恢复请使用上述副本。
