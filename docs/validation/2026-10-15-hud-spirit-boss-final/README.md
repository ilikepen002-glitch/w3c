# 最终 HUD / 附身 / Boss 兼容候选

基于已验证 HUD+附身冻结 `0d53371`，合入 Boss 来源 `d713b813`（本树 `d53c2c0`）。Boss只改变GEOS网格组织；全部角点、UV、法线、矩阵及动画姿态等价，非GEOS区块不变。结构/姿态/负例检查 PASS，见 `boss-mesh.json` 和 `boss-structure.json`；这不证明1.27a原生渲染问题已消除。

最终官方 build：PASS，事务 `linux-h_81qcrc`。`final-package-binding.json` 确认最终MPQ两个Boss模型哈希与请求及导入源相符。与上一合包相比，war3map.j 字节完全相同，无需归一化时间；war3map.w3u、附身星点MDX/BLP也字节相同，Wurst源码与构建配置未改。因此复用前一合包完整checks、HUD五视角各66场景、PetDisplay全覆盖与故障注入、连接效果生命周期、附身资源验证，不重复整轮。

首次最终构图在发布门禁被拒绝，因为同时向仓库docs写入只读核验报告触发输入冻结保护；该候选未发布。待核验完全结束后冻结工作树，日志改写/tmp，重跑官方完整build成功，最终文件来自成功事务。

未启动或部署Warcraft III；Boss网格批次兼容、附身高度/大小/星点视觉、HUD引擎可见性仍需实机观察。本候选未增加排名分页，未恢复附身普攻，未改野生精灵大小。
