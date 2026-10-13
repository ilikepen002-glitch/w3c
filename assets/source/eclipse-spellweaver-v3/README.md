# 蚀月织咒者 v3 · 原创模型

用户已认可危险骷髅脸、宽面经典手绘黑铁/金边/黑紫袍方向。本包实体及动作已经重新解析检查；地图接入由另外的构图流程负责，此处不等同于 1.27a 客户端验收。

## 实体与素材
MDX800，5654 三角面、16962 导出顶点、25 骨、1 geoset、1 不透明单面材质，109 个闭合组件。1 张 BLP1 512×512 diffuse，10 mip，无高清/PBR/外部原生纹理依赖。贴图路径必须为 Textures\EclipseSpellweaverAtlas.blp。

## 动作与头像
Stand 0–2400、Walk 2500–3700、Spell 3800–5300、Stand Hit 5400–6000、Death 6100–8100、Portrait 8200–10600。Stand/Walk/Portrait 循环，其余不循环。每段25实际 MDX 采样姿态，共150姿态。带实际 Portrait 相机；previews/portrait.png 使用该相机。没有额外 _Portrait.mdx 资源，接入者应验收客户端内置相机回退行为。

Walk 只改变悬浮姿态，不要求更改地面寻路、碰撞、速度、飞行高度。当前单位沿路逃跑、禁用攻击，因此模型未加 Attack。Death 为收束塌落动作，无粒子消散；没有额外 Decay 或 Attachment 节点。

## 验证
MDX binary roundtrip、MDL parse、索引/法线/骨父子/材质依赖、25×6姿态的有限值/模型范围/地面范围/循环端点检查通过。109组件每边恰好共享两次且方向相反、正体积无退化；导出MDX的全部三角角点顺序/坐标与源逐项核对。详见 validation-report.json、surface-integrity-report.json。

## 最小再生
Python3 + numpy/Pillow；Node + mdx-m3-viewer 5.7.9 / TypeScript 4.9.5 / gl-matrix 3.4.4；Blender 4.3.2；FFmpeg。没有捆绑第三方依赖代码。MDX_PARSER_RUNTIME 环境变量可指定已安装 node_modules；不设时使用本云工作区原已有依赖目录。

1. python3 build_eclipse.py
2. node export_validate.cjs
3. node check_roundtrip.cjs
4. node check_surfaces.cjs
5. 将 original/palette-decoded.rgba 按 RGBA 512×512 保存为 original/EclipseSpellweaverAtlas_decoded.png
6. blender -b -t 2 --python render_sampled.py
7. python3 package_delivery.py（须保留已有接受版静态预览；不覆盖其 Library 身份）

build_eclipse.py + primitives.py 是最小原创建模、骨架、动画和纹理源码，生成 original/eclipse-source.json 与 atlas_source.png/BLP。export_validate.cjs 是实际MDX导出和再解析采样入口，render_sampled.py 只使用重新解析的MDX姿态与真实BLP解码贴图。所有离线图片和视频均不是游戏截图。生产接入映射、哈希和建议视觉比例见 production-manifest.json。

## 当前仓库接入
仅第24波 uB24，模型 war3mapImported\EclipseSpellweaver.mdx，视觉比例8.00（按用户确认）；原1.50仅为历史离线建议，生产使用8.00。碰撞、选择圈、速度及战斗数值均沿用原值。8倍画面遮挡及客户端效果尚未实机验证。此目录只带最小原创再生源码；地图资源在 imports/。未附视频/Blender大预览。最小实体再生只需上述第1至4步；Blender/FFmpeg仅供预览，不是地图构建依赖。运行 Node 脚本必须显式设置 MDX_PARSER_RUNTIME 为既有 node_modules 路径，不使用工作区相对回退。再生后核对本清单 SHA 再将 MDX/BLP 复制到精确 imports 路径，不改项目工具链锁。
