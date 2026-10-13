# 源码与工具导航

仅在归属或入口不清楚时查阅；按当前任务选文件，不把本表当作必读清单。执行约束见根目录 [AGENTS.md](../../AGENTS.md)。

| 位置 | 职责 |
| --- | --- |
| `wurst/TDConfig.wurst` | 静态坐标、路线、出生点与地图共享常量 |
| `wurst/TDState.wurst` | 金币、生命、波次、路线等运行时状态 |
| `wurst/TDSpawn.wurst` | 敌人生成与归属 |
| `wurst/TDGame.wurst` | 波次推进、漏怪、HUD 与胜负 |
| `wurst/TDInit.wurst` | 启动编排和运行时系统挂接 |
| `wurst/TDWaves.wurst` | 波次配置和奖励 |
| `wurst/TDTowers.wurst` | 塔系统对外 facade |
| `wurst/towers/TDTowerCatalogData.wurst` | rawcode、等级与升级链、基础技能和塔族映射 |
| `wurst/towers/TDTowerCommonData.wurst` | 农民、工资、完美升级与共享配置 |
| `wurst/towers/TDTowerBalanceData.wurst` | 数值、文案、图标、模型和攻击表现 |
| `wurst/towers/TDTowerData.wurst` | 塔数据聚合 facade |
| `wurst/towers/TDTowerRuntime.wurst` | 塔运行时入口及建造、升级、死亡等事件 |
| `wurst/towers/TDTowerObjectGen.wurst` | compiletime 单位/技能/建筑物编 |
| `tests/wurst/` | 测试源码 |
| `tools/Run-WurstChecks.bat` | 统一检查入口 |
| `tools/Sync-WurstTests.ps1` | 检查时的测试 staging |
| `build-and-deploy-test-map.bat` | Windows 编译部署入口 |
| `wurst.build` | `projectName`、依赖、`buildMapData`、脚本模式与补丁版本 |

塔子域已有内部拆分，以上是查找入口而非所有文件清单；按功能在 `wurst/towers/` 中定向检索。依赖通过 `grill` 管理。
