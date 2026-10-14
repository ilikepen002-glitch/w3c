# 精灵技能图标审计与修补

基线：正式 `4abc225`。范围为展示资源和图标路径，不改技能规则、模型、变体数量或品质等级。

## 已核实的问题

43 个有效技能只使用 23 个实际路径。按大小写不敏感的完整 MPQ 路径归组，11 组复用共20个超额身份：

- SteelMelee：战意、猛击、天诛剑阵
- Glove：疾攻、连击、嗜猎余势；另与迅击手套系装备共图
- Brilliance：灵感、月光信标
- FaerieFire：破击、裂甲天锋、伏根刺
- CriticalStrike：追击、决意一击、万刃归宗、屠王血契
- InnerFire：蓄力、迟临审判、圣印接力
- EntanglingRoots：青藤缚足、万象森罗；另与树妖升级分支共图
- DeathAndDecay：繁花蚀骨、寄生毒芽、疫爆接力
- ColdArrows：寒星破、星轨霜箭
- ImmolationOn：烬火印、赤莲绽、业火连城
- ThunderClap：裂岩重击、崩山震、地脉天崩

蓄击的 CleavingAttack、噬生寄种的 EnvenomedSpear 也与升级分支复用。

## 实施

新建25组统一风格64×64原图与DISBTN。18个不冲突的原生路径保持原样；没有引入任何猜测的原生文件名。源atlas、精确提示词、裁切坐标与输出SHA-256保存在 `assets/source/spirit-skill-icons/`。`BuildSpiritSkillIcons.py`只做确定性裁切、缩放、禁用态转换和BLP编码。

正常态自定义资源使用 `war3mapImported` 实际路径；禁用态采用对应 `ReplaceableTextures/CommandButtonsDisabled/DISBTN...`。收藏技能槽及洗练新旧预览统一调用 `tdPetSkillIconPath`。不增加物编技能对象、品质或颜色变体。

43技能现有路径全部互异，与40件装备和10个升级分支的路径无交集。不同品质继续共用本技能底图。实际塔命令卡按进化技能替换前驱的关系检查，无真实同屏撞图；塔底部buff状态载体单独区分，不作为命令按钮误报或修改。

## 资源预算

50个BLP合计605,100字节。整文件zlib预估236,664字节；这不是实际MPQ体积。该组实际MPQ上限262,144字节，由最终地图门禁读取block table实测。源atlas和预览不导入地图。

## 验证状态

- 8项定向Python测试通过，涵盖43身份、共同路径入口、原图/禁用态SHA与mip、重建、大小写路径碰撞反例和退役ID排除。
- `BuildSpiritSkillIcons.py --check`逐字节重建通过。
- `VerifySpiritSkillIcons.py --baseline-map ExampleMap.w3x`源码/旧地图审计通过；不是新地图验证。
- `py_compile`与`git diff --check`通过。
- 既有宠物UI Python集合：34项中32通过、1跳过、1历史fixture失败；基线同样失败（Pbat level 1旧fixture数值1，当前契约要求5），与图标无关。
- 最新索敌+720基线上的完整Wurst检查、最终地图构建和真实MPQ门禁均已PASS；详见 `2026-10-13-equipment-icon-refresh.md` 最终验收。
- 未启动游戏，预览为离线64px正常/禁用态，不声称实机效果。

## 全局装备问题（已在独立后续提交修补）

装备3组跨路线复用：旗图（行军旗系、风行旗、统御号角）、鼓图（疾风鼓系、碎甲战印、裂甲战鼓）、心核图（饥饿心核、森蚀之种）。鹰眼望远镜当前为弓图，狂战战斧为勋章图。已新增5组最小必要图；同系合理品质复用继续保留，镜/斧已复用同系正确图。
