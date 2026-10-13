# 漏怪扣命分类与致死单次结算

日期：2026-10-11。基线：正式装备发布 `d3a00054a2c793cc9579b08af3de4a2c61781084`。

## 变更与风险

- 按实际漏入的单位类型分类：Boss扣3命，精英与近卫队长扣2命，普通怪扣1命。同一特殊波的普通怪仍扣1命。
- `TDGame`先拒绝null、死亡/已漏、非敌方、野生精灵、终局、非法/非活跃/已失败/已完成路线；有效单位先mark，再扣命。致死时先resolved/defeated，再kill，防同步死亡与第二敌人重入导致重复失败结算。
- `TDState.tdLoseLife`将生命截断到0，保留既有负amount调试加命行为。提示实际类别处罚及剩余生命，包括Boss扣3而余1命时显示“生命 -3，剩余 0”。
- 原漏怪不给金币、积分、装备或捕获球奖励路径保持；非致死不关闭其他路线，致死后的精灵/进化/清线/失败弹窗/HUD与全局结算顺序保留。
- 生产差异仅 `TDGame.wurst`、`TDState.wurst`，新增 `TDLeakTests.wurst` 与 `test_leak_life_artifact.py`。地图、记录随此独立需求交付，未混入后续需求。
- 高风险：生命状态、同步死亡重入与路线/胜负结算。GPT-6 Astra负责方案及只读终审；GPT-6.1 Sol负责应用方案、测试与构建。最终Astra只读审查：PASS WITH NOTES，无阻塞；非阻塞备注为受控native/外围结算stub不能替代原生死亡事件、多路同步、计时器和失败弹窗实机观察，详见成品边界。

## 验证

- 固定Linux工具按 `install → checks all → build` 串行完成；typecheck PASS，Wurst **295/295 PASS**，新增5条涵盖32波分类/每次spawn、反馈、零下限、其他路不变与调试加命。
- 固定stdlib tree `90b45617eda50c15703e8cb2ec3241d3c7b61816`，动态选库164/164均来自新固定根。旧依赖临时完整隔离并finally核验恢复，配置和settings原字节/存在状态恢复。
- 漏怪真实地图JASS定向 **6/6 PASS**：44个实际单位rawcode；四类别×余1/2/3/20命共16场景与真实反馈字符串；11个不合法状态guard；两种致死同步重入；调试负amount及零下限。
- 测试执行实际 `tdEnemyLeakLifeCost`、三类unit-type helper、`tdLoseLife`、`tdHandleEnemyLeak`、反馈函数及同步 `tdHandleEnemyDeath`。原生与外围运行时服务使用显式stub，任何击杀奖励路径都被禁止；不以Python重写处罚分类代替实际JASS。
- 六项坏突变能拒绝固定扣1命、整波误按Boss、漏标记guard缺失、mark迟于kill、负生命与反馈固定-1。首轮发现解释器未strip单独not guard前导空格，仅修Python一行后6/6通过；生产源码和成品不变，无重复构建。
- 完整Python **140/140 PASS**；同一成品11项既有artifact验收全部PASS：精灵UI、五技能功能书、塔升级、缓速、进化、塔UI、销售、装备、剑刃风暴、放置、地面三合一。上一批真实地面123/256/600回归保留。
- 全部Wurst生产/测试源码、源模板、配置/settings在检查及构建前后SHA256一致，无测试staging或tracked依赖/配置改动。
- 真实成品的技能、单位、物品、地形及pathing五项MPQ条目与已发布装备地图逐字节相同，未更改装备/精灵物编或地图布局。

## 成品与边界

- 根成品 `ExampleMap.w3x`，显示名及加载标题：深渊守望 `20261011-2315-UTC+8`。
- SHA256：`6bb99d0bb17fdbe929a33e4c24bf2ea9e730a41173c2dee7bd5ebcb8057e9c40`。
- 源模板SHA256：`3fd31a78aaa5d017565fca6c6f3758d40ed6131999c701bdf1f99557ba39e408`。
- 未运行Windows bat/部署、World Editor、Warcraft III、用户电脑或截图/实机测试，未换compiler/nightly/stdlib。
- 受控同步死亡、路线状态及禁奖励stub验证了实际编译分支和顺序，不能代替原生死亡事件调度、多人同步、失败弹窗、计时器、现场敌人移动或整图性能观察。保留上批装备与精灵的原生验证边界。
