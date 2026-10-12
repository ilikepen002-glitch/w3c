# 四个单 Boss 波次验收

## 来源与实现

高风险核心玩法、物编、生命周期及奖励变更。GPT-6 Astra 负责方案和只读审查，GPT-6.1 Sol 负责实现、修复和验证；没有模型替代或阶段豁免。GPT-6 Astra最终只读实现审查：PASS WITH NOTES，无阻塞；完整自动门禁通过，可交付本精确图和源码。非阻塞备注见末节。

独立组合树从真实正式精灵管理发布 `654771baa872241cf572b16a0ef884436fe4818c` 继承，其 parent 为 `b7e3d051e98c2b18caafed4ab6e036700a6ee64c`。三方合并保留经理20槽、四列排行榜、同步摘要缓存、对象生成和界面事务；九个 Manager/Damage 文件逐字相同。没有继承管理未提交快照。

## 玩法与经济

| 波次 | 每条继续路线 | HP / 护甲 | 机制 |
|---|---|---|---|
| 8 | 1个裂风猎王 | 3200 / 2 | 按存活时间每10秒预警1秒，再冲刺2秒，基础移动×1.30 |
| 16 | 1个黑曜棺卫 | 6800 / 10 | 额外法术承伤因子1.00；保留原生英雄法术减伤 |
| 24 | 1个蚀月织咒者 | 19000 / 9 | 每12秒预警1秒，250范围独立原生攻速减20个百分点，持续3秒 |
| 32 | 1个无冕深渊君王 | 36000 / 8 | 首次生命≤30%后基础移动×1.15 |

- 普通波、精英数量、普通技能与装备经济保持；删除 Boss 波普通怪/护卫及旧护卫护甲联动。32波必须击杀。前3个 Boss 漏怪或超时扣3生命，不发击杀奖励。
- PREPARING 自然等待旧怪生产/清场和野宠原60秒窗口。Boss真正登记/激活后显示90秒；击杀、漏怪、超时、离线仅一个终态，奖励 claim 在副作用之前。
- 移除附属怪的确定金币补偿为55/90/144/200，共489。进化要求220次真实击杀，实际敌人总数474，A130物编475层；AeEV只改一个阈值文字字段。
- 原 Boss 高品质共享 lootPlan 冻结优先；普通补偿尝试10/14/16/18，预算3/4/6/8；另有独立15%普通品质末槽，总上限4/5/7/9。不补模拟装备补刀或品质重掷，经济取舍已获用户同意。
- 球补偿11/15/18次2%抽取，遵守原每路每波随机球quota1；32波无球补偿。独立子claim避免重入重复发球。
- 四张原图、生成提示/清单及8张BTN/DISBTN BLP保存并打包；替换图标，不包含新3D模型。

## 实际组合产物

根图 `ExampleMap.w3x` 名称：深渊守望 20261012-1831-UTC+8。

- 正式管理基图 SHA256：`30714b250dc528275e94c6d1d6779e66dceeafbc2d7eaf3cd9ce7c4e1c7b0f7c`
- 组合图 SHA256：`be13ef7b9f7c2144a7feedbef88c79802b4c3e034e8336933e8f808735937d80`
- 实际 war3map.j SHA256：`7228cc50df34fe4fb438c04bc613b5961016dbf0874a25622c26661c67671ed0`
- 完整64生产源指纹逐文件绑定实际图模板；22个受控源owner、全部MPQ成员及物编差分闭合。
- 8图标的原始bytes、BLP1、64×64、七级mip及不透明alpha实际核验。
- Astra批准模板只由精确待审manifest改变两个review字段，批准manifest SHA256：`dc30765a11054133ce98c785fa2e6f5230fc0cede62037e186c37bcb20e62d49`。
- 1525个旧函数保留严格比较；47个本次SHA专属编译差异走封闭精确模板，其中13个明确删除。178个type comparison、81个allocator identity及1372个global声明通过；shell只忽略空行。没有未来包名前缀豁免。

## 构建和验证

使用已审固定 Linux cloud_wrapper，SHA256 `de59b76c08788f7241b7c5a2cf6c1ef6641ea214c0999491a4baed82e20bf9f6`，没有改wrapper。

```text
python cloud_wrapper.py all --repo integration-worktree-06 --timestamp 20261012-1831-UTC+8 --verbose
python cloud_wrapper.py checks --repo integration-worktree-06 --verbose
```

完整构建事务 `b6f0d8d1dfbf4626ab31beda72146d88`；最新fixture清理后检查事务 `2798e129ad6749769c4a1a163cf96b38`，365/365 Wurst测试通过。初次06构建有1条测试fixture冗余import warning，删除后最新完整verbose检查389条均为逐声明/源码statement对应正式654的旧site，新增0；不以warning总数相减作证明。生产64源和组合地图未因测试import清理而变化。

实际JASS执行结果：规则498、flow18、leave3、mechanics451、原生能力/伤害账本48。生产未注册hook，公开注册/resume被DCE；实际无hook 8/24执行真实30秒timer closure一次推进9/25。

同源隔离 NON-RELEASE hook图：map SHA256 `55816202fc9487390f887db1fc1851fe0db6c76fef460e6547a0ede29c8ea898`，script SHA256 `cb7dc6c28e1ddacc2610bb3ef8420d40a8a23dbf68f9e29d1d6f665e457e4042`，事务 `d1680aac45fe4830891f21d3a2e42065`。64生产源逐字等于组合图，仅额外fixture `tests/wurst/runtime/TDBossTransitionRuntimeHarness.wurst`，SHA256 `bbf97671349eae654f03955b9c780329a6e62dbf968f3599ace74e2be79fcb46`。真实allocator、interface dispatch、具体onReady/onRelease、cyc重入和timer closure执行10场景，原生账本48通过；未stub hook回调。一次性派生staging已经删除，64生产源恢复精确清单。

17项当前实际图门禁由16项通用CLI和Boss独立严格gate组成，覆盖装备、进化、地面升级、普通捕获/20槽经理、tooltip、slow、bladestorm、建造/出售/升级/上阵、工人A/B及嗜血C。经理严格delta仍针对冻结654图和源码；当前组合由独立Boss严格继承证明及经理现有shape/事件门禁保护。Slow显式`--pure-boss`只改变uG32(260,260)、uB08(240,312)、uB32(250,288)期望tuple；默认旧模式保持，旧模式拒绝当前图和错max的负例通过。8项历史阶段门禁由经理654严格delta与原7项CLI组成。原7项使用各阶段冻结正式源码/原工具/地图配对，不套当前图、不放宽旧oracle。

完整Python最终稳定批次441/441通过，335.774秒，0失败/错误/跳过；178个源码、工具和测试文件在该批次全过程及结束后指纹完全一致。定向最终Boss35/35通过，含实际完整gate、hook、native和slow负例。初跑修正历史输入/源码配对及测试生命周期，首批440项只有一个返回dict的测试断言形状错误，已窄修并在最终完整批次通过；未归为生产缺陷。最终结果和准确argv见同名证据目录。

## 扩展接口与未验证边界

未来trial应在每局`TDInit`启动中的`tdStartGame/reset`之后注册真实hook；模块init注册一次会被match reset置空。8/24可占用120秒，替代默认30秒；resume成功立即推进9/25。NORMAL/TIME_LIMIT/ABORTED三reason与CLOSING重入隔离已验证。现生产不注册dummy；未来注册模式必须编出真实公开API/dispatch/resume并恢复完整实际hook验收，不能沿用无hookDCE豁免。

没有启动Warcraft，没有Windows/BAT部署或实时性能/网络验证。原生负攻速叠加、画面/命令卡渲染、引擎timer时序及Boss平衡仍未实机观察。离线解释器在引擎I/O、时钟、timer队列和敌人最终生产处记录边界，执行实际业务状态与hook，不称为实机运行。
