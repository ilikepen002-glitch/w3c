# HUD 恢复与附身表现合包

来源：HUD 冻结 `a581afb0edd1d47d401a9373c6b3c9182e73d146`；附身表现来源 `b97ce5b52cd22fca59367ae62d1f00e718b2855b`，在本树 cherry-pick 为 `b6b2faa`。未混入排名分页或 Boss 优化。

## 改动与生命周期核查

- HUD 隐藏后恢复当前模式，保留手动折叠；详见前一 HUD 验证记录。
- 附身精灵提高悬浮高度、调整附身模型比例，新增宿主 origin 上的一条冰白星点连接。野生/收藏大小、精灵普攻和技能战斗代码保持原样。
- 新效果由现有 TDPet 对象持有，重复初始化不重复创建；invalidateCombat、recall 和析构释放。既有 display tick 在失效状态重新初始化；没有新定时器或全局遍历。
- 按 AGENTS 归类为现有所有权与生命周期中的局部扩展，非完整新系统或跨系统生命周期重构；无必需的高风险三阶段缺失。

## 最终产物验证

- 官方完整 checks 和 build：PASS，事务及产物摘要见 `validation-summary.json`，完整日志见 `checks.log`、`build.log`。
- `VerifyPetPresence.py --map ExampleMap.w3x`：PASS，15种附身比例、35种塔位、最终 MPQ 对象/导入资源、原模型及战斗/野生源码一致性，见 `presence.json`。
- 最终 MPQ 的 HUD 回放：0/1/2/3/15 每视角66场景，全部 PASS；同步句柄序列相同，见 `hud-replay.json`、`hud-replay.log`。旧图恢复场景仍按预期失败。
- 既有完整 `VerifyPetDisplayReplay.py`：PASS，525种塔位/精灵组合、15种精灵动作、召回/换塔/升级、80只压力边界及5项故障注入，见 `display-replay.json`。
- 新连接效果的实际打包 JASS 窄生命周期回放：PASS，含首次挂载、幂等初始化、失效释放与重建、换塔、召回、重复召回、析构；原生效果模型严格拒绝未知/双重销毁。见 `link-lifecycle.json` 和可复跑脚本 `link_lifecycle_replay.py`。

源附身工作树的早期 checks 因“验证中输入变动”保护失败；随后重新完整 checks 已 PASS。本合包再次对冻结源码完整 checks/build，不复用该失败事务。

以上为离线验证。未启动或部署 Warcraft III，不能确认1.27a真实高度遮挡、星点视觉效果、帧率或联机表现。
