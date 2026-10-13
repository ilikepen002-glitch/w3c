# 2026-10-11 地面物品整理与范围升级验证

## 操作说明

- 地面装备每 30 秒按白、绿、蓝、紫品质集中到中央北高台边缘，捕获球另成一堆。整理保留物品句柄，不改变捕获球既有路线信息。
- 五组中心依次为 `(-576,800)`、`(-320,800)`、`(-64,800)`、`(192,800)`、`(448,800)`。每堆在中心横向 ±64、纵向 ±32 的小格分布；超过 15 件后循环堆叠，物品不会因容量上限丢弃。
- 农民 C“功能”技能书包含背包合成、范围升级和另一任务加入的伤害统计页面。选择“范围升级”（U），对地面点施法，范围半径 144。任意位置的地面装备均可参加，不限公共整理区。
- 只合成施法时圈内快照：同品质优先 3 合 1 必成，剩余 2 件按原有 65% 成功率合成，单件保留。失败材料损毁，成功产物继续与本次已有更高品质材料合成，最高到紫装。
- 库存装备、捕获球、紫装与圈外物品不消耗；施法后新掉入范围的物品不加入本批次。整理或另一批升级忙碌时，新范围升级请求会提示稍后重试。
- 原背包合成功能保留，仍使用前 3 格材料。书内按钮依次在 `(0,0)`、`(1,0)`、`(2,0)`。

## 自动验证与产物

最终源码冻结后串行执行，全部退出码为 0：

| 验证 | 结果 |
| --- | --- |
| `tools\Run-WurstChecks.bat` | `Typecheck succeeded`、`All tests succeeded`。quiet 输出不报告运行器总数；当前测试源码声明 215 个 `@Test`，其中地面规则 6 个。 |
| `build-and-deploy-test-map.bat` | 编译、修补显示名称、部署全部成功。显示版本“深渊守望 1534”，部署时间 2026-10-11 15:35:21。 |
| `python tools/VerifyGroundItemArtifact.py ExampleMap.w3x` | PASS：农民 `uF01` 挂载 `Geqb`；列表 `A119,Gupg,Dsta`；3/3 法术、冷却独立；顶层 C 格与书内三格正确；旧 C 热键保留；`Gupg` 点目标、范围圈、144 AoE；新指令 `whirlwind` 无冲突。 |
| `python tools/VerifyPetUIArtifact.py ExampleMap.w3x` | PASS：农民 12 个命令格无重叠，收藏图标路径正确。 |
| `python tools/VerifyEvolutionArtifact.py ExampleMap.w3x` | PASS：35 塔进度挂载、539 级统计、3 状态进化、分支/光环/图标/翅膀资源、正常地图无测试探针。 |
| `python tools/VerifySlowAbilityArtifact.py ExampleMap.w3x` | PASS：敌军速度边界、61 级毒/光环/Bash 参数及原生毒伤。 |

另一次旧 staging 的进化数量预期失败已按当前源码定向验证通过 `1/1`。地面规则定向曾被其他聊天构建清空 staging，产生读取错误；此环境错误已由最终串行全量成功验证覆盖。本任务引入的未使用 import 已删除。测试的非 quiet 定向日志保留既有 compiletime 注解和未使用 import warning；最终普通构建没有报告 Wurst warning。本轮未修改无关模块来消除既有 warning。

最终检查前、检查后与构建后全部 `wurst/`、`tests/wurst/` 源码 SHA-256 一致，未发生并发修改。以下三份地图 SHA-256 完全相同：

`D517EFE354C5D5EF09E78C20228646BB94EC98A0A599259B6B1D56452863BBCA`

- `D:/War3Projects/MyFirstWurstMap/_build/MyFirstWurstMap.w3x.w3x`
- `D:/War3Projects/MyFirstWurstMap/ExampleMap.w3x`
- `D:/War3_1.27a/Warcraft III Frozen Throne 1.27a publish/Maps/Test/深渊守望.w3x`

完整最终检查/构建日志、四项物编核查日志（地面日志含完整相关对象字段）、源码哈希清单与地图哈希清单保存在同名目录 [2026-10-11-ground-items](2026-10-11-ground-items/)。构建脚本的部分中文终端输出存在编码混杂，版本和部署路径已通过实际文件与物编结果复核。

## 实机边界与残余风险

按用户要求不做实机测试。自动检查和物编核查不能证明原生技能书实际渲染、范围圈视觉、快捷键在打开技能书时的实际表现、现场拾取与批次交错行为或地形上的视觉摆放效果。高台位置来自方案阶段源地图 W3E/WPM 的高度与可走性采样。

## 模型与审查

实际使用模型：GPT-6 Astra（`gpt-6-astra`）负责方案与最终只读实现审查；GPT-6.1 Sol（`gpt-6.1-sol`）负责实现、修复与自动验证。Astra 最终结论为 **PASS WITH NOTES**，无阻塞事项，可交付。非阻塞备注：按用户要求不做实机测试；技能书实际显示、圈选体验、多人拾取与大量地面物品的原生性能未实测。方案与实现审查均已执行，实机测试按用户要求跳过。
