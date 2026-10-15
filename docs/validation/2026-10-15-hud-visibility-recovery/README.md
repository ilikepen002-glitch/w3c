# HUD 可见性恢复

## 范围与证据

基线：`7834f5c890f3a95f9935e40a30f514e5fd88a994`。
生产源码提交：`e4154e89297b0176885b8bb1d1010823040c77e7`。

用户报告右上 HUD 整块消失，并现场确认 `-hud full` 可恢复。源码与发布 MPQ 核对确认：原实现只有初次显示或显式模式切换时调用 show；常规刷新无法恢复已隐藏的表。首次隐藏的引擎原因未实机复现，不把这一恢复修复表述为已证实首次隐藏原因。

复用既有 viewer 循环，在本地分支查询所选模式的表是否显示；隐藏时只调用 show。无新增句柄、全局扫描或同步状态；普通刷新不 maximize，保留手动折叠。未添加玩家诊断文案，未改变排名或新增排名筛选。

## 验证

- 官方 Linux 定向 `test TDHudTests`：PASS。
- 官方 Linux 完整 `checks`：PASS。
- 官方 Linux `build`：PASS；输出根 `ExampleMap.w3x`，未部署或启动游戏。
- 旧发布图的实际 JASS 在新增“隐藏后恢复”场景产生预期失败，见 `baseline-expected-failure.json`。
- 候选实际 MPQ/JASS 按本地玩家 0/1/2/3/15 回放，比较同步句柄序列，见 `candidate-replay.json` 和 `replay.log`。
- 覆盖完整/精简、展开/手动折叠、隐藏后的恢复、恢复后不重复增加 UI 写入。完整模式本来保留宝宝说明单元格的同步 get/set/release；断言比较恢复前后调用差异，不能要求完整刷新完全没有 UI 调用。

`validation-summary.json` 保存各官方验证事务、工具链及产物证据；`checks.log`、`build.log` 保存完整入口输出。最后一次调整仅修正回放断言，没有改变已通过编译构图的生产源码。

回放执行原生显示模型，不证明 Warcraft III 1.27a 的真实渲染、手动折叠引擎行为或联机同步；尚未实机验证。

## 复跑

在仓库根执行，先用 `git show 7834f5c:ExampleMap.w3x` 导出基线到临时文件，然后执行 `python3 docs/validation/2026-10-15-hud-visibility-recovery/replay_driver.py <基线地图路径>`。脚本读取根候选图、复跑旧图预期失败和五视角的66个场景，再比较同步句柄序列。
