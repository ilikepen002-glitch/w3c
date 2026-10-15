# 15种精灵外观优化：最终接入验收

基底为已发布 `163b613d5d52a7190c9db3bf0b61b62658feaca7`。改动属于既有资源的局部外观与单种野生物编适配，不新增状态系统或运行时生命周期。没有运行 Warcraft III 客户端。

## 最终地图

- 根 `ExampleMap.w3x`：6,769,902 bytes；SHA256 `85122ec2ac7fc61d9eb8d945ffc3014369c53327dfbca9388b0e2130c29902ac`。
- 地图显示名：契灵守卫战 20261015-1711-UTC+8。
- 官方完整检查 PASS：`linux-j1n5k2qb`，类型检查和全部 Wurst 测试成功。
- 官方唯一构建 PASS：`linux-s7g2zpc2`，154个 legacy-JASS allocator、冷却、精灵/游戏启动及413个导入文件的实际MPQ字节门禁通过。
- 构建入口、锁定 compiler/Grill/JDK/stdlib、JASS/v1.28 配置均未改变。没有手改 `_build` 或 `war3map.j`。

## 资源与生产引用

所有15种已实际接入地图，保留已有满意轮廓；银鬃已认可图集逐字节保留，主要优化眼部。金木、水土及火狐/火蜥采用保存的 imagegen 新绘图集与可重建转换，部分眼部采用局部几何/UV调整。赤翎火鸟改为署名 johnwar 的 Phoenix (Re-Classic) 派生凤凰。

- 15个主模型共4,440,497 bytes、29,919三角形；14种原有模型的骨骼、所有动画关键帧、枢轴与基础动作保持。
- 主凤凰124,409 bytes、695三角形，维持原点和比例，供附身/收藏使用。附身scale仍1.04。
- 专用野生凤凰94,589 bytes，仅保留0–4基础动作和实际引用关键帧/事件、全部全局轨迹；贴图与主模型共享。
- 16张实际自定义纹理合计2,028,645 bytes；全部为目标支持的BLP1完整mip链。凤凰身体512²且每级独立8-bit alpha，其他主图为256²。
- 精确TEXS路径、alpha、材质、多geoset、所有动作的可见剔除边界从最终字节重新解析；主模型每段65点、野生257点采样通过。
- 实际MPQ中16个模型、全部自定义纹理、556个野生/收藏/附身及收藏入口单位引用均验证。地图内 `Credits-Phoenix.txt` 逐字节验证。

## 唯一物编差异与玩法不变

Wurst源码仅将species10野生单位模型改为 `EmberBirdWild.mdx`，scale改为1.375348；其余233个玩法/测试源码文件逐字节保留。32个对应野生单位的实际W3U只有 `umdl` 与 `usca` 变化，碰撞、移动/路径、生命、技能、攻击启用等字段不变。W3A/W3T/W3H均与基底逐字节相同。

最终 `war3map.j` 与基底地图 **逐字节相同**：2,875,451 bytes，SHA256 `55731ea0f66390da225c745cfb6483afbb1b3b777dfd89d6b983f59392504f06`。因此已恢复的弓原生攻击流、已取消的附身普攻外观、绑定星光、技能发动效果、所有玩法与调度均未改变，没有引入每帧脚本。按项目规则复用该相同已发布JASS的弓/战斗回放证据；没有把重复回放的中断记录标成新PASS。

## 凤凰预算与野生接地

最初密集烘焙候选曾达到1.617MB，未交付。最终按原生稀疏关键帧重映射整数毫秒，保留Hermite/Bezier控制值；时间最大舍入0.4958ms，201点/段测得最大顶点误差0.8262模型单位，约Float跨度的0.3673%。原13段完整动作留在可恢复源模型，生产主模型只含实际调用的0–9。

关闭常驻黄色glow网格和黄色装饰PRE2；Float/Walk/Cast等非死亡段PRE2为0。保留两条红色低量ribbon，每条10/s×0.25s，稳态估计共5段；保留Death专用短爆。这是静态/采样预算，不是实机FPS测量。

野生模型整体Z偏移+73，所有顶点、pivot、camera、collision和extents一致变换；保留的静态数据、动画key/tangent逐项相同。257点逐顶点验证世界位移误差不超过0.00003052。1001点Walk采样使旧/新野生最大世界跨度分别为309.71553与309.71563。Stand最低约1.12、Walk最低约22.64模型单位，实际MDX+BLP按最终scale的地面参照渲染已查看。

原Attack俯冲、Portrait锚点和Death下落未改写，部分羽片仍可低于地面。野生单位禁止攻击，正常不调用Attack；头像视角不使用场景地面；正常捕获/到期移除不依赖完整Death。Death后半下沉作为原版死亡表现明确保留。

## 可重建与验证入口

`BuildSpiritRefinementAssets.py` 从107个锁定源输入在临时目录完成 PNG→BLP→MDX→野生派生，32个最终二进制逐字节一致。它不靠修改hash接受差异。准确提示、接受的原PNG、主/野生模型源、节点/材质/动作适配和转换脚本均入库；图像生成本身不宣称确定性。

历史 `BuildPetDisplayModels.cjs --write` 已验证会在新资源启用时拒绝固定BASE覆盖。`VerifyAllPetDisplayArtifact.py` 自动转入当前资源契约验证，未放宽或删除历史保留断言。

证据：`asset-inspection.json`、`packed-resource-object-gate.json`、`deterministic-rebuild.json`、`wild-phoenix-variant.json`、`runtime-jass-equality.json`、`official-*-summary.json`和原始构建/检查日志。完整重建输入/命令/输出清单在 `assets/source/elemental-spirits/refinement-20261015/rebuild-plan.json`。

## 验证边界

Warcraft III 1.27a实机显示、原生纹理可用性、粒子/ribbon视觉连续性、遮挡、实际FPS及多人同步没有实测。凤凰9张原生纹理与teamcolor在manifest明确标记，本云环境未读取目标安装包；未把这些原生依赖误称为缺失自定义纹理或已核实兼容。Blender预览是实际导出网格和BLP的离线渲染，不是游戏截图。收藏图标保留现有UI版本，本次未重做全套图标。
