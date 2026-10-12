# 2026-10-12 金币试炼独立静态准备验证

更新（11:34 UTC）：实际完整 typecheck 与370/370测试现已通过，其中试炼23/23；详情见 `2026-10-12-trial-wurst-checks.md`。以下保留10:57初次静态checkpoint的历史边界；其中“未运行Wurst”已由此次补验关闭，未构图/未接线/未实机边界仍有效。

## 范围、模型与门禁

基线：`654771baa872241cf572b16a0ef884436fe4818c`；独立分支：`trial/static-preparation-20261012`。

实际实施模型 GPT-6.1 Sol；正式设计由 GPT-6 Astra 只读审查 PASS WITH NOTES，见 `docs/design/2026-10-12-trial-approved-plan.md`。本改动触及专用状态与物编，属于高风险。此阶段是有意分离的静态准备，不是生产集成或发布，尚未执行 Astra 实际实现审查，也未豁免它。

未修改 TDGame、TDSpawn、TDInit、TDHud、TDDamageRuntime、装备/精灵战斗入口、TDWaves、构建配置或 BuildEvolutionAssets。没有同名 Hook stub，没有普通波次/计分/金币写入，没有自有开波调度。对象与所有 Wurst 测试尚未编译，本阶段不能声称试炼已经支持运行。

## 已执行与结果

1. `python tools/BuildTrialAssets.py`：通过。只复用 BuildEvolutionAssets.blp，没有调用其 main。独占两条试炼图标路径，保留原 PNG、exact prompt、Library 原图 ID 和生成清单。
2. `python -m unittest discover -s tests/python -p test_build_trial_assets.py -v`：6 项通过。重复转换逐字一致，source SHA 锁定、64x64、disabled 灰阶亮度 0.45 与 alpha 保留，BLP1 alpha8 七级 mip 64/32/16/8/4/2/1、无多余 payload、全 imports 路径大小写唯一。
3. `python -m unittest discover -s tests/python -p test_trial_static_contracts.py -v`：9 项通过。这是静态源码契约及独立数学 oracle，不是 Wurst 执行。确认共享入口逐字等于基线、专用 rawcode 不入普通 Boss/单位表、物编 setter 在锁定 stdlib 中存在、无 init/生产 Hook 或 native 状态写入、状态/时限/一次领奖/票据保护、分块转换范围以及有条件源码伤害上界。
4. `git diff --cached --check`：通过。全部新增字节已 staged，可导出含二进制资产的完整补丁。本地提交因该 clone 未配置 Git author identity 未生成，未改身份配置、未推送；HEAD 仍为基线。
5. 实际 view `assets/source/trial/gold-coin-golem-icons-preview.png`：64px 金币圆形主体、面部与肢体可辨；禁用态是较暗灰阶。预览是图标离线图，不是游戏截图或新 3D 模型。

### 图标哈希

- source PNG：`e18b1efb8a91a2fcea6179335ae6effe11006a867f632333d4035b166d8966c8`
- `war3mapImported\\BTNTDTrialGoldGolem.blp`：`5095926333d0e730aa9195cc25a5ee13800abb885ca96c0a8eb0a2813cc2be4f`
- `ReplaceableTextures\\CommandButtonsDisabled\\DISBTNTDTrialGoldGolem.blp`：`5acaa9f091a83f87b91e83b6b101191955167f1b7de3b39d9b2497c07e43f911`

### Wurst 测试源码，尚未执行

`TDTrialRulesTests.wurst` 10 个测试；`TDTrialStateTests.wurst` 13 个测试。覆盖：两节点/120秒/5槽/20总上限、奖励/同分池/0与正小数、异常超额封顶、分块大于 signed-int 累计及最终 carry、初始路线错位、槽身份/复用 revision、生命和独立装备资格、单人/4路/并列/退出冻结、普通账本隔离、精确 deadline、20目标×3段去重、嵌套上下文、旧 generation、部分创建失败后 COMPLETED release 零奖、timer/watchdog 两种先后、ABORTED/异常早退零奖、opaque token 与 reset、准备快照失败。

每次 seal 先取消 ACTIVE 并失效 target identity，再由适配器完成 native 清理并确认后才 takeReward；重复 seal 或 takeReward 无效。跨轮/局 token 与 generation 均保护派奖。退出的已得伤害保留名次占位，但无奖；未支付份额不重分。生产 adapter 尚不存在。

## 合法单段：有条件源码上界，不是不死证明

当前40装备组合的条件单段参数包络已更新（原28装备120000/八分之一结论不再用于当前组合）。最高静态基础260、骰面12、装备固定载体128、精灵固定载体512；白虎/统帅最高身份合计40.8%由×2保守包络；暴击由×3、额外flat32包络；攻击类型倍率≤2、负甲倍率<2是必须独立核目标安装表/原生边界的前提。普通/英雄试炼均不是Boss法抗来源。

原生事件条件包络：`N=((260+12+128+512)×2×3+32)×2×2=22016`。代码派生段再保守×4：副箭105676.8；装备半血20%+Boss/试炼25%为39628.8；新尸气/森蚀每victim44032；精灵双追加149708.8、主动74854.4。固定DOT/风暴更小，脚本盾击伤害0。全部当前已知单段<150000<100万的15%。来源读当前40配置与实际载体；每个被接受的段须priority0补血、code/Tspl不递归；额外箭数/计数/攻速只改变段频次，不乘进单段上界。

此为当前参数和列明前提下的静态/回放条件包络，不保证任意异常伤害、未来装备、原生精度或未经核实安装表。每段先补血与异常死亡/补位仍是运行时防线。

尚未核实目标安装的实际类型表、native 对象输出、最终合入 Boss 后的所有攻击路径、监听代码及引擎结算。合法一击不会杀死目标的最终证明仍是生产集成门禁，不能把这个数学 oracle 或100万常量测试当作该证明。装备重做、新塔、新的百分比/生命相关伤害机制、升级或类型表变更后必须重新枚举路径并计算上界；未核对最终1.28实际类型表之前不能提升为引擎证明。

## 数值与异常边界

- 每段先取真正事件 effective = min(amount, preLife)。NaN、非正与非法 preLife 不计；正异常超额（包括正无穷）只得到 bounded preLife，并需 runtime 诊断。这里不修改原生伤害，因此极端单击仍可能致死，后续只补有效空槽。
- 账本分为 `chunks <= 1000000` 与 `[0, 1048576)` 实数余量。每段 effective <=1000000，进位计算 sum <2048576，R2I(carry) 只有 0/1。最终余量 R2I 小于等于1048576，高位不对累计实数直接转换。累计上界约1.049e12；超界 fail closed、该 lane 无奖、已得伤害继续占位。
- 不主动逐击整数截断；原生单精度仍可能丢失极小增加量，不声称所有小数无损。最终统一四舍五入用于同分，真实0单独分组；正小于0.5在 HUD 必须显示 `<1` 或小数。
- 票据只是纯上下文模型；若生产采用它，逐真实段 new/destroy，不能共享多段，也不能积压。可直接用每事件局部上下文实现，不必引入运行时票据分配。

## 明确未执行

- 未运行 `tools\\Run-WurstChecks.bat`；不占 Boss 共享 staging/工具链锁。因此 Wurst 语法、类型检查、23个测试的执行结果尚未验证。
- 未运行 `build-and-deploy-test-map.bat`；未读取新 W3U/MPQ/部署地图。UnitDefinition setter 名称静态存在不代表生成对象已验证。
- 未正式接 Hook、TDInit、计时器、HUD、装备资格、伤害监听、路线、补槽或清理。
- 未验证 1.28 native `Units\\Creeps\\GolemStatue\\GolemStatue.mdx` 实际资源。源映射 `UnitIds.battlegolem = narg` 已静态核对；tint255/220/120 是金色近似，生成图只有概念/头像，不是自制3D。
- 未推送、未完整构图、未启动 Warcraft、未实机或 FPS 测试。

后续详见 `docs/design/2026-10-12-trial-integration-checklist.md`。完成全部集成门禁、Astra 实际审查后才可发布。
