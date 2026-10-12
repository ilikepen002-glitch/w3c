# 金币试炼运行时接线：Sol 实施证据

正式基线 `72b2c9c3406868d33969c087dd5e6015abc3ac7b`。GPT-6.1 Sol 实施；Astra 已审全部20生产文件，并定向通过最后路点tick后退出的release对账修复。最终产物门禁及整体终审由父任务收口，本文不宣称它们已经通过。

## 最终实际构建

统一已批准事务wrapper，串行 `all --repo integration-worktree --timestamp 20261012-2051-UTC+8 --verbose`；wrapper SHA `de59b76c08788f7241b7c5a2cf6c1ef6641ea214c0999491a4baed82e20bf9f6`。

- typecheck成功，实际395/395测试通过，其中Trial30个。
- 构图与wrapper退出0。
- 图名：深渊守望 20261012-2051-UTC+8。
- 根图 `ExampleMap.w3x` 与事务candidate逐字同SHA：`03921c61e64e5392f8f9100291ca62df539b3f0bb8c7c4af47e82fa2bba21dde`。
- 从实际MPQ提取JASS SHA：`a47a8d6226776bf27ab033bb6539fae258f3e889ed55746ccc6b9d219445536c`。
- 最终事务：`transaction-5c8656f1eb9347c3903f00a91dc86acb`；journal/status和stage均restored，child=null，临时staging/config/native脚本恢复，无活动compiler。
- typecheck原始389条warning，归并206个site/message；Trial生产和Trial测试新增warning为0。未扩大范围清理旧warning。

实际logs、提取JASS、20生产文件精确SHA清单和对账修复diff保存在worktree同级 `trial-formal-delivery/`；Astra与产物worker已取得固定candidate路径，避免根图覆盖导致错读。

## 实施范围

新增TrialIdentity/Runtime/Hook/Hud，接入TDInit/TDHud/TDDamageRuntime/TDEquipmentCombat/TDItemData/TDPetCombat/TDPetRuntime/TDPetState/TDTowerRuntime；纯Score/State增加精确十进制HUD接口和release资格对账。TDGame/TDWaveFlowState/正式Boss公共Hook/TDWaves未改。

- 每局Game reset后注册真实Hook，失败检查boolean、不覆盖旧hook。
- 独立每路5槽、最多20目标，独立路点/出口循环/异常死亡失效后延迟补空槽；不登记普通波次。
- priority0固定100万预补，priority4最终事件伤害分流到独立账本；不setAmount0、不改reduced伤害。
- 真实onRelease统一对账退出资格、seal、失效身份、清timer/native单位/装备及精灵debuff，再一次奖励；timer仅resume。
- 原生timer回调核GetExpiredTimer身份；装备毒/追加、分裂落点与精灵整proc均带epoch/generation/token及必要revision。pendingSerial防旧proc误清新pending。
- Trial异常尸爆显式拒绝rawcode及已remove目标；普通Boss/掉落/漏命/分数继续由既有主波登记过滤隔离。
- 屠王只在装备独立资格入口覆盖试炼，并修改对应说明；未扩大普通Boss白名单。
- 固定独立6行HUD，积分从整数分块精确十进制转换，>2^31相差1可区分；正小数<0.5显示<1；金币头像header明确启用icon style。

## 当前边界

未推送、未启动Warcraft、未实机。最终实际JASS链回放、W3U/MPQ/strict delta与整体Astra终审正在由其他任务验证，不能把纯测试或构图成功当作全部门禁通过。

原生模型仅有固定stdlib元数据与地图引用证据，云端没有合法1.28安装MPQ/SLK；不称安装实证。伤害上界只适用于当前72/654共用塔与旧装备源码及明确类型表前提；未来装备重做、新塔、百分比机制或cap变化必须重算，不承诺任意大一击不死。
