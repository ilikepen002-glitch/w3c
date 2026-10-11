# 2026-10-11 精灵 UI 离线验证

## 修改与边界

本轮为高风险物编/UI改动，由 GPT-6 Astra 提方案并只读审查，GPT-6.1 Sol 实现与验证。最终审查结论：**PASS WITH NOTES，无阻塞项**。本记录不代替另行进行的全塔升级生命周期只读审查。

- 农民三排依次为：移动/停止/保持/功能；巡逻/修理/闪烁/工资；建造/Q捕获/W收藏/E上阵。仅移动 `Geqb`→(3,0)、`Pcap`→(1,2)、`Pcol`→(2,2)、`Pdep`→(3,2)，坐标从零开始，其余原生及自定义位置不变。
- 保留巡逻，不删除或禁用 `Amov`，不引入全局 `CommandFunc` 覆盖或新版 native，避免改变移动/保持/巡逻共用能力及多选行为。原生实际布局和多人行为仍未实测。
- 收藏八命令保留位置、热键、目标类型与原 base order，分配八种语义图标。`pd01–pd03` 显式设置与炎灵/雷灵/幽灵模型匹配的 interface/score 图标。
- 空槽原来的红问号来自 `BTNSelectHeroOn` 本身的图样，是选图语义错误，并非证明该原生资源缺失。现在 variant 128 使用独立空槽图；64–127 保留对应技能灰图与共鸣锁定说明，0–63 保留亮图。全部 516 个被动变体的身份、位置及无战斗效果字段均验证。
- 图标路径集中在 `wurst/pets/TDPetUIData.wurst`；完整路径通过显式 normal/research setter 写入，防止快捷方法重复加前缀。功能菜单仍是原六命令。
- **野生精灵速度与阻挡未修改，不能据本轮验收宣称已解决。** 按用户要求未启动 Warcraft III；也未运行 Windows `.bat`、部署到用户电脑或进行实机试玩。模型头像、选中表现、实际按钮渲染与多人效果未验证。

## 资源

`assets/source/pet-ui/` 保存 13 张原创 SVG、`manifest.json` 与离线解码预览 `pet-ui-contactsheet.png`；转换入口为 `tools/BuildPetUiAssets.py`。预览不是游戏截图。

13 种图标为 MenuTools、Collection、Previous、Next、ReturnBuilder、Deploy、Recall、Cultivate、Info、EmptySlot、FlamePhoenix、StormFaerieDragon、GhostWisp，文件名统一带 `TDPet` 前缀。共 26 份 BTN/DISBTN：64×64、BLP1 palette/alpha8、七级 mip。正常路径为 `war3mapImported\BTN{Name}.blp`，禁用路径为 `ReplaceableTextures\CommandButtonsDisabled\DISBTN{Name}.blp`。

从本次地图 MPQ 按精确路径提取全部 26 份资源，解码、灰态变暗、资源差异与源文件 SHA256 一致性均通过。独立重建可重复；未重建其他技能或翅膀资源。

## 最终验证

- 固定工具：Grill `1.4.0.0-e55cf33`，Wurst `1.9.0.0-nightly-1-g436a944f1`；locked stdlib tree `90b45617eda50c15703e8cb2ec3241d3c7b61816`。
- 动态确认 164/164 个库均来自正确 locked 根目录，模型拒绝 0、错误根目录 0；typecheck PASS，Wurst **258/258 PASS**。
- Python 对象/资源正负回归 **44/44 PASS**，地形回归 **14/14 PASS**，地形生成一致性 PASS；九个产物验证脚本全部 PASS。
- 原源码七项图标接线约束与旧地图五项新 UI 正例先保留红灯；本次产物正例转绿。缺图、重复路径前缀、命令同图/重格/撞 order、物种错图、亮灰空混用、锁定身份/说明错误、BLP尺寸/mip/灰态/hash错误均有具体拒绝原因。

首次构建曾因旧嵌套依赖遮蔽正确库而出现 `ModelManager lib=null` NPE；早期检查不作为最终证据。经 Astra 批准，外置 Linux 等价入口临时隔离旧嵌套依赖后串行重新检查和构建，随后核验恢复其原文件、模式、时间及状态。仓库依赖、`wurst.build` 和 `.vscode/settings.json` 未永久改动；这不等于执行了 Windows 构建部署入口。

## 产物身份

- 地图：`ExampleMap.w3x`，显示名与加载标题均为 `深渊守望 20261011-1743-UTC+8`。
- 地图 SHA256：`631d3ac7c1868fa81292248129ccb02168547d5d6a9d04dfe80f332c456d942a`。
- 模板 `maps/ExampleMap.source.w3x` 未改，SHA256：`3fd31a78aaa5d017565fca6c6f3758d40ed6131999c701bdf1f99557ba39e408`。

## 仓库内离线重验

在仓库根目录运行 Python 3；资源 `--verify-only` 只检查，不生成资产或构建地图：

```sh
python -m unittest discover -s tests/python -v
python tools/VerifyTowerTerrainMask.py
python tools/GenerateTowerTerrainMask.py --check
python tools/BuildPetUiAssets.py --verify-only
python tools/VerifyPetUIArtifact.py ExampleMap.w3x
python tools/VerifyGroundItemArtifact.py ExampleMap.w3x
python tools/VerifyEvolutionArtifact.py ExampleMap.w3x
python tools/VerifyEquipmentAbilityArtifact.py ExampleMap.w3x
python tools/VerifySlowAbilityArtifact.py ExampleMap.w3x
python tools/VerifyBladestormAbilityArtifact.py ExampleMap.w3x
python tools/VerifyTowerPlacementArtifact.py ExampleMap.w3x
python tools/VerifyTowerSaleArtifact.py ExampleMap.w3x
python tools/VerifyTowerUiGroundArtifact.py ExampleMap.w3x
```
