# 精灵捕获、永久释放奖励与弹窗离线验证

日期：2026-10-11。基线：已发布塔修复 `1aa173eefab2c2a4549515fd8aa3998c3f1b799a`。

## 风险与模型

- 高风险：拥有记录生命周期、材料入账、确认票据、原生弹窗事件桥接、compiletime 物编及自动 Channel 分配。
- GPT-6 Astra：只读方案与实现审查；发现固定 JASS 打印器布尔分组问题。
- GPT-6.1 Sol：源码实施、Wurst 回归、固定 Linux 检查/构建与 Python 真实产物验证。
- 最终 GPT-6 Astra 只读实现审查：PASS WITH NOTES，三个已确认编译分组阻塞均解除。非阻塞备注：仅离线验证、原生鼠标点击根因未复现、固定编译器未根治且四处其它既有中低风险保留。审查前候选图不发布。

## 实现范围

- 野生精灵只可捕获。删除猎杀状态、终态、事件处理、敌对切换、Phnt 对象与菜单挂载；死亡仅过期清理。中立无敌60秒、概率/教学/大师球、出现预算和路径速度保持。
- 主动释放永久消耗已有精灵，不退捕获球、不重新变野生。每次1洗练石，独立2%得1开栏石，进入本路精灵材料账户，不占背包。上阵必须先召回；召回保留精灵且无奖。
- 每路票据保存 slot、记录身份、revision、generation；递增 nonce 跨路唯一。Begin/Confirm 校验本人拥有、合法收藏位、active、未败/未结束/未离开、未释放、未上阵、无待洗练结果。有效确认先废票再重验，一次随机、无yield、成功移除后唯一入账；旧票不清新票。
- `tdPetDiscardOwned` 是无奖内部清理入口，测试/探针同步改名。记录仍保留到 match end，避免延迟闭包悬挂。材料 int 极限会提前拒绝，精灵保留；满收藏捕获不扣球。
- 玩家离开仅更新宠物域离开标记并废票，不改变全局胜负。野生失效单位/死亡/离线统一过期清理。
- 真实 UI 复用 `TDPetDialogSession`，验证 button表hasInt、本人归属、当前dialog、模式、按钮轮次与目标snapshot。合法点击消费当前轮；取消/关闭/切宠/导航/开菜单废票。释放使用独立 RELEASE_CONFIRM 模式，不能在培养模式只凭action14移除。
- Pc06 名称/提示均“洗练 / 开栏 / 释放(C)”，保留(2,2)、C与图标。捕获/收藏提示说明选中收藏展示后按C，并区分农民C功能菜单。
- 培养标题只显示目标/材料/成本与操作提示；按钮保留栏号/品质/技能短名，完整描述仍在信息页。空栏先开栏，已有共鸣锁定栏能洗练；预览保留旧新身份与不退石/冷却后果。失败原因在弹窗内，检查Resolve返回值。
- 真实 DialogAddButton 数字键：1..4选洗练栏；预览1保留/2替换；释放1确认/2取消。上阵释放提示明确先关闭弹窗后Q召回，再C释放。
- 功能书精确五技能 A119,Gupg,Dsta,Pmas,Pfor；min/max5，Pfor移(1,1)。删除Phnt后重新核对18个全局Channel对象唯一order和Pc00..07精确顺移值。
- 三处已证实且直接关联的旧JASS分组缺陷修复：宿主能力适配、洗练技能资格、路线存活敌人野生排除。见[独立解决记录](../solutions/2026-10-11-jass-boolean-grouping.md)。不修改编译器或其它系统。

## 验证证据

- RED：旧释放路径测试0/1，预期洗练石1、实际0。
- RED：旧塔成品 SHA45cf1f…在新的六项物编/真实数字键契约下失败；原塔/资源验收与坏突变保持通过。
- RED：2213审查前候选真实JASS能力helper被拒绝；独立wc3libs JASS语法证明旧分组反例，不以源测试通过覆盖此缺陷。
- 最终 Wurst typecheck PASS，289/289 tests PASS：原274项保留，新增15项释放/UI/资格回归。
- 新回归覆盖唯一入账、重复确认、取消、旧nonce、新票不误清、异路、错owner、revision/generation、同槽新宠、生产上阵否决predicate及召回再申请、待洗练、失守/结束/断线、无奖内部清理、不生野生、满收藏不扣球、材料极限和精确2/100概率helper。
- 真实 UI helper 回归覆盖模式/归属/轮次/当前dialog/重复按钮、snapshot、取消与实际数字键映射；Python验证实际map JASS调用链进入原生DialogAddButton整数参数，不仅验证标签。
- 最终 Python 114/114 tests PASS。实际map JASS：宿主能力64组合、技能资格2176组合、路线guard256组合、数字键102组合全部PASS；对应旧mixed表达式、类别/主动/重复mask、真实分类/bitset/power、null/野生/owner/lane/alive/found/wave与快捷键坏突变均能检出。物编含Phnt幽灵/挂载、五菜单、Pfor位置、全局Channel、文案/键位/资源坏突变，并保留原塔28项回归。
- 10项真实地图验收均PASS：精灵UI、五技能功能书，加八项既有塔升级、缓速、进化、塔UI、销售、装备、剑刃风暴与放置。全部验收针对同一最终成品SHA256，不复用审查前候选通过结果。

## 工具与成品

通过完整读取并使用固定外置 Linux 移植入口，按 install → checks all → build 串行完成，没有声称运行 Windows bat：

```sh
python3 "$KIT/bin/run-wurst-linux.py" install "$REPO"
python3 "$KIT/bin/run-wurst-linux.py" checks "$REPO" all
python3 "$KIT/bin/run-wurst-linux.py" build "$REPO"
python3 "$KIT/bin/run-wurst-linux.py" verify "$REPO"
python3 -m unittest discover -s tests/python -v
```

- 固定 stdlib tree：90b45617eda50c15703e8cb2ec3241d3c7b61816。
- 每轮动态选库164/164来自新固定根，ModelManager全部接受。旧依赖仅临时隔离，finally逐文件SHA/type/mode/mtime/tracked恢复；wurst.build和编辑器settings原字节与存在状态恢复。
- 不改生成源码或依赖；没有测试staging留在正式成品，tracked _build/config/settings无差异。源模板、地图地形/pathing和既有塔能力保留。
- 根成品：ExampleMap.w3x。
- 显示名/加载标题：深渊守望 20261011-2218-UTC+8。
- 成品SHA256：d31c1a9f254b395fe5443f94669b005a81cee19b7f4f4f2f658130872dc115f9。
- 模板SHA256：3fd31a78aaa5d017565fca6c6f3758d40ed6131999c701bdf1f99557ba39e408。

## 未验证与残余风险

未执行Windows部署、World Editor、Warcraft III、用户电脑或第三方模型；没有使用聊天token。源码和已发布JASS的事件注册/bridge有证据，未复现鼠标无法选择问题、未证实其原生根因；没有增加第二份button事件注册，也不宣称实机点击或数字键已实测。

自动检查证明状态事务、真实编译字段/脚本和离线资源符合授权；不能代替原生modal交互、技能效果、地图运行/性能或塔平衡观察。保留上一轮塔修复的未实机风险。只读同类审计仍有四处既有中低影响编译分组问题，本批不扩改；技术范围和未观察影响见解决记录“同类审计的剩余范围”，不能称全图已无逻辑缺陷。
