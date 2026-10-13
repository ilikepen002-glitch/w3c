# 无冕深渊君王：原创实际模型评审版

第32波 Boss 的原创模型。用户已确认造型，当前资源冻结并交由统一集成人员接入；本制作任务未修改主仓库、生产映射或玩法数值。

## 外形

黑钢宽肩重甲、分腿胫甲、单手下垂重剑、连续宽幅破披风、灰白发束及独立悬浮碎冠。面部有实际厚度的眉骨、颧骨、鼻梁、眼窝和咬合颌骨；冷光限制在眼、胸部和剑的一小段裂隙。

## 当前规格

- MDX800，6106三角面，27骨骼，154封闭组件
- 原创512×512 BLP1，10级mipmap，无透明贴片依赖
- Stand / Walk / Attack / Stand Hit / Death / Portrait
- 六序列各25姿态，共150姿态重新解析验证
- 全部组件封口、共边相向、正有向体积；源几何到MDX全部角点一致
- 二进制roundtrip、MDL再解析、骨/索引/法线/动画循环/包围范围及预览地面检查通过
- 包含主模型 Portrait 相机

## 原件

- original/UncrownedAbyssKing.mdx
- original/UncrownedAbyssKingAtlas.blp，模型内部路径 Textures\UncrownedAbyssKingAtlas.blp
- original/abyss-source.json

## 可再生流程

已安装的 Python、numpy、Pillow、Node、mdx-m3-viewer 及 Blender。

1. python3 build_abyss.py
2. node export_validate.cjs
3. node check_roundtrip.cjs
4. node check_surfaces.cjs
5. 将 original/palette-decoded.rgba 按512×512 RGBA保存为 UncrownedAbyssKingAtlas_decoded.png
6. blender -b -t 2 --python render_sampled.py -- --review-only

解析器依赖可通过 MDX_PARSER_RUNTIME 指向已安装的 node_modules 目录。

所有预览均由落盘MDX重新解析的真实蒙皮采样及BLP解码生成，不是概念图。已认可的全身与头像静图保持不变。六动作实际采样视频另行交付；尚未 Warcraft III 1.27a / World Editor 实测。

## 当前仓库接入

仅第32波uB32，模型 war3mapImported\UncrownedAbyssKing.mdx，视觉比例7.00。按实际模型体量与当前蚀月8倍顶部对齐；碰撞、选择圈、速度、路线和战斗数值不变。资源位于仓库 imports/，此目录保留最小再生源码。上述第1至4步生成实体，Blender仅预览，不是地图构建依赖；必须显式设置 MDX_PARSER_RUNTIME 指向既有 node_modules（mdx-m3-viewer5.7.9 / TypeScript4.9.5 / gl-matrix3.4.4），不安装新依赖或改项目锁。再生后核清单SHA再复制两个精确imports路径。未实机验证画面遮挡、Portrait回退或性能。
