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

## 本次打包验证（2026-10-08）

- 对应玩法源码提交：`e6f1d77b8bb1b1a69090baebfd6763f5f5ccd48d`。
- 使用原先固定、校验过的工具链，从迁移后的源地图重新构建成功；类型检查通过，173/173 自动测试通过。
- 测试后清理 staging 并再次编译，输出与原已验证候选地图逐字节一致。
- 加时间戳前的可复现地图 SHA-256：`916c81144aec86a4cbb70cdd97fd12a6cffcbfd95a2260b1e9f8ff337c82b343`。
- 按现有 `PatchMapDisplayName` 工具追加时间戳，地图名和加载页标题为 `深渊守望 2218`，对应 2026-10-08 22:18（UTC+8）。
- 最终根目录地图 SHA-256：`0d894e5025ca79ffd8006426e781fbc91b0f9304a1a63ad3fb8da820379e9ea0`；追加时间戳前后 JASS 逐字节一致。
- 已检查 MPQ 内容和嵌入的 JASS，包含重复移动命令修复。
- 保留 `scriptMode: JASS`、`wc3Patch: v1.28`、pre1.29 标准库。
- 本次执行的是获准的 Linux 构建/测试流程；没有执行 Windows bat、Windows 部署或 Warcraft III 1.27a 实机验证。自动测试与编译成功不能替代游戏实测。
- 按用户要求跳过 Gemini 审查；打包方案经过内部独立只读审查。
