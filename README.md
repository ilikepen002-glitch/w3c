# 契灵守卫战 · Y3 / KK

四路独立防线的塔防地图：32 波战役、五类塔与终阶分支、精灵捕获和技能培养、装备升阶、契约选择，以及独立管理面板。图标为项目生成素材，来源与提示词在 `development/assets/`。

当前版本 0.2.1 处于开发中。已在原生编辑器重载，UI 半透明底图、按钮染色、槽位文字与窗口适配问题已修正，并保存整屏截图。战场单位存在但模型仍不可见，这是未解决的阻塞问题；完整操作及战役尚未通过实机验收，不能视为可玩成品。证据与后续入口见 `development/docs/evidence/20261024-session-status.md`。

## 打开与开发

用 Y3 编辑器双击打开根目录 `header.project`，主地图为 `EntryMap`。不通过 `game.exe` 打开 KK 客户端。VS Code 打开同一根目录，安装官方 `sumneko.y3-helper`。

克隆时使用 `git clone --recurse-submodules`；已有检出先执行 `git submodule update --init`。官方 Lua 库作为子模块固定版本，保留原始源码与 Git 初始化状态。

```powershell
python -m venv development/.venv
development/.venv/Scripts/python -m pip install -r development/requirements.txt
development/.venv/Scripts/python development/tools/check.py
development/.venv/Scripts/python development/tools/check.py ui
development/.venv/Scripts/python development/tools/deploy.py
```

维护 `development/src/`，部署写入 `maps/EntryMap/script/`。地图对象与生成脚本一起提交；编辑器热更新并确认完成后保存。源资产、导入包与元数据保留在仓库。新机器首次打开须在编辑器完成资源下载/修复并检查模型和图标显示；本机资源缓存不提交，纯 Lua 动态资源的依赖清单仍在核验。

## 历史与官方工具

- 新平台分支：`codex/y3-spirit-defense`。
- Wurst 备份标签：`backup/wurst-before-y3-20261023`，指向原远程开发分支的 `50d227e754abecca3d14e07e9d76af35c6502359`。
- 官方技能适配记录：`.codex/skills-installation.md`。
- 官方仓库下载与复用记录：`development/docs/upstream-tools.md`。
- 编辑器 MCP 与开发助手接入：`.codex/skills/y3-editor-control/references/codex-integration.md`。

原 `D:/Y3Projects/SpiritDefenseWork` 仅保留为迁移前本机备份；后续修改统一在本工程 `development/`。
