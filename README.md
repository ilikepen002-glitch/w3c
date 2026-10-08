# 深渊守望

## 地图文件

- 根目录 `ExampleMap.w3x` 是已编译、可供放入 Warcraft III 地图目录的打包产物。
- `maps/ExampleMap.source.w3x` 是 World Editor 源地图模板。地形、区域和编辑器资产应在这里修改；不要把根目录产物用作编译输入。
- Wurst 玩法源码在 `wurst/`，测试源码在 `tests/wurst/`。

原根目录源地图已原样保存到 `maps/ExampleMap.source.w3x`，SHA-256：
`627a64c012dcc46e1b5acc48dcbb20eeca0b465093718800799a2df37ded0b5e`。

## 后续构建

按项目规则运行 `tools\Run-WurstChecks.bat` 和 `build-and-deploy-test-map.bat`。
构建脚本从 `maps\ExampleMap.source.w3x` 编译，在 `_build/` 生成地图，成功追加显示名时间戳后更新根目录 `ExampleMap.w3x`，然后部署到脚本配置的游戏目录。
发布玩法修改时，也要重新构建并提交根目录地图。历史方案文档中把 `ExampleMap.w3x` 当作源地图的路径，现对应 `maps/ExampleMap.source.w3x`。

## 本次打包验证（2026-10-08，2228）

- 基于 `23e45c1d889746cc526c258dc5f4f003fc3808fa`，敌人归属改为 `wurst.build` 已配置的专用电脑槽位 4；不再使用中立敌对玩家。
- 本次只调整敌人归属，不改路线、地形、碰撞、数值或移动命令逻辑；保留原有 CreepGuard、RemoveGuardPosition 和避免重复 move 命令的保护。
- 这是针对“拐角/受击后回头”的候选修复。中立敌对归属与专用敌军槽位不一致已确认，但尚未在 Warcraft III 1.27a 中证明它是全部回头现象的原因。
- 使用原先固定、校验过的官方工具链，从 `maps/ExampleMap.source.w3x` 重新构建；类型检查通过，176/176 自动测试通过。新增归属测试先在旧代码失败，再在修复后通过。
- 测试 staging 清理后再次编译成功。未加时间戳地图 SHA-256：`2757fcba98a45059c327dda6c0b3ce805d9f3551eb0e663cb06b16f9eea7ee38`。
- 按现有 `PatchMapDisplayName` 工具生成显示名和加载页标题 `深渊守望 2228`。2228 是 2026-10-08 22:28（UTC+8）的构建版本标签，不代表用户时区。
- 最终根目录地图 SHA-256：`a091cb2b121dad61fbc1bad238a9e04da4f59480cae23c1ab914c42c8b5b985c`；追加时间戳前后 JASS 逐字节一致。
- 已检查打包 JASS：敌人归属初始化为 4，槽位 4 为电脑且属敌军队伍 1，玩家 0–3 属防守队伍 0；生成、死亡监听、奖励和目标筛选继续使用同一归属常量，路线归属仍取自单位元数据。
- World Editor 源地图模板逐字节未变。保留 `scriptMode: JASS`、`wc3Patch: v1.28` 和 pre1.29 标准库。
- 按用户要求跳过 Gemini 审查，改用独立只读方案和实现审查。
- 本次执行获准的 Linux 构建/测试流程；未执行 Windows bat、Windows 部署或 Warcraft III 1.27a 实机试玩。请以 2228 版复核同一拐角、被塔攻击后的走向，以及击杀奖励和漏怪扣命。
