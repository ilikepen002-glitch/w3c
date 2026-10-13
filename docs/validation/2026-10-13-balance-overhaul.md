# 整体数值与难度升级验证

风险：高风险，四档全局难度引入独立选择/锁定状态，并共同改变出怪、物编、HUD和奖励接口。GPT-6 Astra（gpt-6-astra）提供方案、试炼保护容量补充方案及最终只读审查；GPT-6.1 Sol（gpt-6.1-sol）实现、修复与验证。最终正式结论：**PASS WITH NOTES**，没有未解决阻塞。非阻塞备注仅为未实机验证生命强化效果、通关平衡、四路性能和联机同步；没有跳过必需阶段。

## 实现取舍

- 塔基础攻击和固定技能伤害、装备固定攻击/毒伤、精灵固定攻击均 ×5。骰子保持原来的 1 至 (6+等级) 小波动，tooltip仍与真实攻击范围对应；塔生命未放大（怪物不会攻击塔）。攻速、射程、百分比、护甲、减甲、控制时间和目标上限保留。
- 普通敌人 HP ×4、数量 ×2、间隔 ×0.75；精英/首领 HP ×5，数量和纯首领关不变。每路由474变934（920普通+10精英+4首领）。
- 货币、塔价格、工资、首领补偿与试炼奖金 ×10。普通单只基础/装备额外击杀金使用满额的1/2，精英/首领基础奖励满额；装备额外金币仍不奖励首领，预算由按类型的基础击杀收入计算。
- 普通装备掉落概率和普通精灵球概率减半；精英掉落、首领独立补偿抽取及其原掉落概率保留。守恒的是未受预算截断的期望，并不宣称预算截断后分布完全相同。
- 难度普通/困难/噩梦/传奇，HP倍率1/1.3/1.7/2.2。首波前编号最小的当前活跃路线玩家选择，退场后动态转移；有效首波启动通过guard后、生成之前锁定。后续界面调整改为居中按钮弹窗，移除聊天难度命令；状态reset复原。
- v1.28生命强化用与现有DamageEvent相同的AIl2/AbilityDefinitionMaxLifeBonusGreater，单级物编Ilif整数增量，创建后一次挂载并按实际maxHP补满。没有使用1.31 API。精灵野怪与试炼对象走独立创建，不加难度。
- 装备128级/精灵512级攻击能力保持级数，每级5点。真实runtime装备+攻击光环与ForItems使用同一纯映射；精灵固定/百分比攻击先除5再按旧版取整，保留旧版相对量化精度。
- 试炼保护HP从100万同步扩大至500万（容量保护，不是挑战难度）；保守原生片段界限108928，综合单段界限740710.4，低于保护容量15%。试炼积分与生命周期约定不变。
- 下一波提示根据实际数量、速度和护甲提示群攻/减速/破甲，首领提示集中火力。玩家可见尸爆、工资、猎金及试炼奖金文字同步。

## 自动验证记录

- `tools\Run-WurstChecks.bat`：类型检查通过；全量479测试中478通过，唯一剩余为新猎金说明的tooltip长度限制。压缩准确表述后通过定向 `tools\Run-WurstChecks.bat test TDPlayerTooltipTests`，7/7通过。未放宽320字符要求。
- 全量涵盖难度解析/权限/锁定/reset、32波数量与特殊关、四档HP和rawcode唯一、装备/精灵容量、收益预算、进化、试炼积分/并列/退场/部分失败等既有关键测试。
- 新增精确经济检查点与期望守恒断言后，定向 `tools\Run-WurstChecks.bat test TDDifficultyTests`：7/7通过。检查点1340/5630/14640/31680/54090均通过。
- 初次检查被锁定编译器patch的CRLF工作树字节阻断。主代理证明恢复LF与Git原始blob及锁定SHA256一致，保留jar/lock不变，并通过`.gitattributes`固定该patch LF。此后编译器门禁通过。
- 试炼740710量级的float32舍入单步为0.0625，固定界限断言使用0.1绝对容差；15%容量要求未放宽。进化固定技能108/72的浮点比较按同一尺度提高至0.0001绝对容差。
- `build-and-deploy-test-map.bat < NUL`：最终再次编译与部署通过，地图显示时间戳1554；最终源图及部署图文件时间15:55:17，构建日志 `_build/balance-build-deploy-final.log`。最终129个allocator旧版JASS门禁、实际MPQ冷却/动态能力角色门禁、精灵启动以及首波/HUD/相机/watchdog回放均通过。
- 最终候选运行 `python -X utf8 tools/VerifyBalanceArtifact.py _build/MyFirstWurstMap.w3x.w3x`：32普通/8特殊HP表、132个独立AIl2/Ilif能力、装备128级和精灵512级全部加攻字段、进化935级及440阈值、500万试炼容量、装备runtime+光环的共享/5映射均通过。额外核查A112原生字段108与tooltip108匹配。
- 最终候选运行 `python -X utf8 tools/VerifyEquipmentAbilityArtifact.py _build/MyFirstWurstMap.w3x.w3x`：128加攻/120攻速/30减甲/41冷却级数及字段、父对象别名、native buff通过。
- 最终候选运行 `python -X utf8 tools/VerifyPlayerTooltipArtifact.py _build/MyFirstWurstMap.w3x.w3x --shared-active-cooldown --current-pet-ui`：1927个真实打包tooltip按数值/规则/长度检查通过，包括普通与精英猎金差异、进化暴击和精灵毒域。
- 最终候选运行 `python -X utf8 tools/VerifyTrialArtifact.py _build/MyFirstWurstMap.w3x.w3x --shared-active-cooldown --current-pet-ui --output _build/balance-trial-artifact.json`：试炼对象所有显式字段、500万HP、图标字节及上述1927个tooltip通过。
- `python -X utf8 tools/VerifyTrialReplay.py _build/MyFirstWurstMap.w3x.w3x --output _build/balance-trial-replay.json`：PASS。覆盖8/24波两种释放竞争顺序、20目标创建/清理、11种伤害链边界、部分创建失败/重开/退出、4297次真实积分添加、超过2^31的总分区分、装备延迟片段和过期回调隔离。
- TrialReplay首次暴露旧离线fixture遗漏`init_Real`：真实JASS的min/max依赖Real_REAL_MAX/MIN，fixture未执行包初始化时默认0，导致模拟有效伤害归零。补执行真实`init_Real`，不硬设伤害或期望；随后回放通过。此次修复只改验证工具，没有改依赖或游戏代码。
- TrialReplay读取的是首轮候选；最后改动仅修compiletime暴击tooltip。以实际JASS字节SHA256相同证明复用回放，不以“文案改动”推测等价。最终其他MPQ字段检查全部读取最终候选。
- `git diff --check`通过；本轮修改的Python验证工具编译检查通过。原生波次/奖励探针的期望随规则迁移，未执行原生探针或启动游戏。

## 最终产物证明

- 最终图：`_build/MyFirstWurstMap.w3x.w3x`。
- 部署图：`D:\War3_1.27a\Warcraft III Frozen Throne 1.27a publish\Maps\Test\契灵守卫战.w3x`。
- 最终图与部署图SHA256均为`d3f4bf5bdcdbcdb20827a175222b2f7860ec493854fc3aa57e51083360c797dd`。
- 最终图JASS及已PASS的TrialReplay脚本SHA256均为`023c3f6853a5e40ed26647fc69a8e681db5ba5823d825fb027bf07ec22eb1464`。
- TrialReplay所读首轮MPQ SHA256为`07d9c162fa63853aceb07cac822499b15cc6035dafa46b4d7d916c186130235b`；与最终图对象tooltip/元数据不同，JASS字节相同。证据 `_build/balance-final-artifact-proof.json`。

## 未验证与残余风险

未启动Warcraft III。AIl2生命强化的目标引擎实际效果、四档胜率、密集波FPS与同步表现、玩家是否需要打破顺序造塔习惯均未实机验证。自动检查能证明配置、生成产物及测试行为，不能证明可玩性或挑战曲线已经调到最佳。


## 后续调整：开局居中难度弹窗

用户要求使用按钮弹窗，不手动输入命令。本次为普通改动，沿用 TDState 的选择权限、难度与首波锁定，由当前 GPT-6 主代理实现验证，未调用子代理；上文 Astra 审查对应此前整体数值升级。

- 新增 TDDifficultyDialog 表现包，使用 Warcraft 原生居中对话框，普通/困难/噩梦/传奇按钮直接展示生命倍率。玩家点击后关闭并广播，移除难度聊天入口和相关提示。
- 在延迟启动回调中展示，避免地图初始化期间显示原生对话框。单人原生对话框暂停游戏等待点击；多人沿用30秒首波时间，超时沿用当前难度（初始普通）。
- 当前选择者离开后转交下一位有效玩家；首波锁定和对局关闭时销毁弹窗/触发器，重开创建新弹窗。难度规则和倍率保持不变。
- `tools\Run-WurstChecks.bat`：类型检查与全量测试全部通过，日志 `_build/difficulty-dialog-checks.log`。
- `VerifyStartupArtifact.py` 回放真实地图 JASS，覆盖延迟展示、四档按钮、非法按钮/错误对话框/无权限点击、离开转交、首波默认/锁定、迟到点击及关闭重开清理，已通过。原生句柄与显示操作由测试替身建模，不等于实机验证。
- 首次构建在发布前被回放门禁阻止：新增包的 `init_TDDifficultyDialog` 未纳入测试环境初始化，导致默认选择者被误读为0。已改为执行地图包内的真实初始化函数，定向回放通过；未修改生产初始化规则或放宽断言。
- `VerifyBalanceArtifact.py` 数值物编检查通过；Python 语法检查与差异格式检查通过。
- 未启动 Warcraft，实际居中显示、单人暂停和多人点击同步尚未实机验证。

- 最终 `build-and-deploy-test-map.bat` 完整通过（日志 `_build/difficulty-dialog-build-final.log`），显示版本时间1623，产物时间16:24:48，已部署到测试地图目录；源图和部署图SHA256一致：`2b77a996f7eb036db5cf47ff8a43894fa4f82d0ee3a45b0146a2fc4fb168d839`。
