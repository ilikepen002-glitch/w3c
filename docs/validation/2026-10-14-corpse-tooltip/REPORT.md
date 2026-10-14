# 尸爆说明与附身精灵显示比例整合

基线：96bddd3da25193f01d3eddaeb61c2c702d44f106（已发布紧凑HUD）。附身显示比例原提交 e686ee8398ffa620448552c83b5e36004230d13c，本树对应 50ca416b2bd5946c0a8fa0afe1ee14b73ec7f8c8。

## 尸爆事实

TDTowerRuntime.wurst 的 tdHandleGhoulCorpseExplosionDamage 排除法术与code伤害，要求实际拥有A116、目标不是试炼目标、攻击前生命≤25%、本次原生普攻足以击杀。仅伤害同路其他存活敌人，范围220。未改此文件及CommonData、CatalogData任何字节。

伤害：1–5阶180；6阶A进化前后180；6阶B未进化270、进化后324。

旧A116一级说明同时列180/270及『购买即』『同样需要』备注。新说明按实际状态显示：

普攻击杀敌人时，若其攻击前生命值
不高于25%，触发尸爆。
对周围220范围内其他本路敌人
造成180伤害。

血疫未进化/进化分别仅将末行数字换270/324，显式|n分行。升级/进化按钮已有对应270→324描述，保持不动。

## 最小实现

- A116原level1=180、level2=324保持，新增level3=270。沿用tdGeneratePassiveDisplay对每级显式设置0暴击率、1倍率、0附伤、neverMiss=false。
- tdEvolutionCorpseDisplayLevel扩展未进化B为3；tdEvolutionRefresh在技能存在且实际等级不同才修正展示。依据实际rawcode分支；不新增缺失技能、不更改伤害计算或触发。
- 完工、升级结束及延迟取消恢复的原路径都会refresh；原进化apply仍选择level2；出售删除原记录。
- 所有其他A116消费者仅检查>0，包括尸爆触发和精灵适配，没有技能级别伤害倍率。

## 范围

本轮优先修尸爆，避免扩大到其它分支展示逻辑。白虎战吼/统帅光环仍有同类混合升级说明，留下一小批处理，不能直接删掉分支数字导致显示失真。

## 验证状态

- 全部官方checks PASS，检查manifest保存在checks-manifest.json；Wurst全测试成功。
- Source evolution 11测试PASS；附身显示比例5测试PASS。
- 第一次checks在补充Python验证脚本期间输入变更，被发布门禁拒绝；源码冻结后完整重跑PASS。
- 官方build最终PASS，build-manifest.json保留完整输入和产物记录；最初磁盘满后按父协调腾空间并重试。
- 严格MPQ delta PASS：427成员，仅war3map.j/w3i、A116说明及中性第三等级、15个pv单位usca；其余资源/物编字段完全一致。
- VerifyCorpseTooltipArtifact实际地图PASS：7个rawcode节点；1→2、5→A/B升级、延迟取消恢复、预览取消、A/B进化、重复refresh零额外SetLevel、售卖句柄复用。
- 地图SHA256：b632d51143397128e623203b1f73017902b35cdcd86acf8d647434142883e28e。
- 本轮3个临时snapshot在通知抵达前已清理，manifest及外部日志保留，原始源码未删。第二次build收到停止指示后Ctrl-C；磁盘恢复获准后最终重试成功。
- 完整进化packed replay PASS：4路结算、17失效生命周期、935次仅击杀不自动进化、10终阶分支及nonce绕过负例。
- 升级物编/中性展示载体Python负例31测试PASS。
- 尚未实机验证；所有验证均为离线源码、Wurst或packed JASS/native状态模型。
