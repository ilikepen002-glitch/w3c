# 装备技能预载与进化图标验证

## 变更与证据

- GPT-6 Astra 提出方案并完成实现审查，GPT-6.1 Sol 实现及验证。Astra 最终结论为 **PASS WITH NOTES**：源码和构建无阻塞问题；非阻塞备注为部署因锁图尚未完成、首次加载导致卡顿仍为假设、实机效果未验证。
- `TDInventoryRuntime` 在同步 package init 中预载 A128/A129，失败显式报错；装备技能已处于目标等级时跳过重复设置。装备数值、rawcode 和卸装排除物品规则保持原有语义。
- A130 普通/研究图标统一从 `tdTowerEvolutionProgressIconPath()` 读取原生 `ReplaceableTextures\CommandButtons\BTNMetamorphosis.blp`。本机 `war3.mpq` 可提取普通图标 7775 字节及对应禁用图标 4832 字节。
- 编译地图的 `war3map.j` 中 A128/A129 分别为 1093743160/1093743161；`init_Preloader` 先建立 dummy 并安排零秒 timer 清理，`init_TDInventoryRuntime` 在同步初始化期间调用两技能预载，未进入延迟 0.10 秒运行时 setup。

## 检查结果

- `tools\Run-WurstChecks.bat`：退出码 0，类型检查及全部测试通过。首次检查发现缺少显式 `ErrorHandling` import，补齐后通过。
- `build-and-deploy-test-map.bat`：地图构建、打包和显示名时间戳 1457 成功；部署阶段由于已有游戏锁定 `Maps\Test\深渊守望.w3x` 失败，入口退出码 1。未终止游戏。
- `python tools/VerifyEquipmentAbilityArtifact.py ExampleMap.w3x`：通过，A128 的全部 128 级攻击增益、A129 的全部 120 级攻速及 AIsx 继承验证成功。
- `python tools/VerifyEvolutionArtifact.py ExampleMap.w3x`：通过，A130 普通/研究图标精确匹配原生变身图标，且与四个攻击光环图标不同；保留其他技能导入图标要求。
- `ExampleMap.w3x` 与 `_build/MyFirstWurstMap.w3x.w3x` SHA256 一致：`8E23F54DF2B7B8F23D34BDBDFD7DC89C169AE68B95E2B7B308A9450013B89A7A`。
- 被锁定的旧部署地图 SHA256：`ABAD26AA28BBFA15A8931A1335FAD8708FAFB41067E79399AE0AB901B84EC037`，与新产物不同，当前游戏未使用本轮新图。

## 未验证项

首次加载多等级装备技能引发停顿仍为假设。以上检查证明预载、等级更新和图标配置已经编译进入新地图，不能证明实机停顿消失。新图尚未成功部署，未测首次/重复装备、卸装、实际攻速、画面帧时间或进化图标渲染；需用户退出当前游戏后重新走规定入口并实机验证。

本轮修改前的四个目标文件基线、独立 delta、检查/构建日志和提取脚本位于 `C:\Users\huawei\AppData\Local\Temp\war3-equip-evolution-20261011`，用于区分工作区此前已有改动。
