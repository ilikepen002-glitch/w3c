# 裂风猎王 · 已确认造型与六动作

造型为用户已确认的 v2：前倾分腿猎王、短而危险的活脸、连续银白后掠发束、三块不等宽黑骨甲与独立握柄月牙刃。本轮没有修改网格、UV、骨骼枢轴或BLP；仅把原先压缩式死亡占位改成保留身体比例的侧倒、手臂/武器收拢并逐关键帧落地校正。

## 资源
RiftwindHunter.mdx 为 MDX800；4352三角面、13056导出顶点、22骨/枢轴、1 geoset、1不透明单面材质、88闭合组件。RiftwindHunterAtlas.blp 为512×512 BLP1 diffuse，10级mip。模型内纹理路径固定 Textures\RiftwindHunterAtlas.blp。没有PBR/HD材质、第三方模型/贴图或额外原生纹理依赖。

## 动作
Stand 0–2400、Walk 2500–3700、Spell 3800–5300、Stand Hit 5400–6000、Death 6100–8100、Portrait 8200–10600。待机/走路/头像循环，其余不循环。没有额外 Walk Fast 序列或脚本依赖。单位沿路逃跑、不攻击，因此不添加 Attack。内嵌实际 Portrait 相机；客户端回退尚待1.27a验收。

实际重新解析MDX，25姿态×6，共150姿态。检查有限值、骨父子/引用、法线、索引、循环端点、全动作包围盒及地面范围。MDX二进制往返及MDL解析通过。88组件逐边闭合且相反方向、正体积；源三角角点与最终MDX逐项比对。采样法线经过inverse-transpose骨矩阵，预览使用模型的自定义法线而非错误的平面替代。

## 最小再生
Python3（numpy/Pillow），Node（mdx-m3-viewer5.7.9、TypeScript4.9.5、gl-matrix3.4.4），Blender4.3.2，FFmpeg。软件依赖不随资产包重新分发。MDX_PARSER_RUNTIME 可指定已经安装的node_modules目录，默认沿原云工作区可信依赖。

python3 build_riftwind.py；node export_validate.cjs；node check_roundtrip.cjs；node check_surfaces.cjs。build脚本自身已包含网格辅助函数，不需要实验用txt片段。原始模型JSON与atlas_source.png由这两份Python源生成。导出之后将palette-decoded.rgba按RGBA 512×512保存成RiftwindHunterAtlas_decoded.png，render_sampled.py从真实采样重建网格和实际贴图。

## 接入边界
production-manifest.json保存精确哈希、尺寸、源清单、Stand及全动作实际bounds。root最终指定uB08视觉倍率7.75；当前待机顶部144.411682×7.75≈1119.191，对齐蚀月139.981537×8≈1119.852。该倍率只用于视觉，不改变碰撞/选择圈/移动类型/速度/路径/战斗。实际地图接入由统一构图任务完成。

离线视频不等于客户端；未提供1.27a实际游戏渲染证据。形象与静图已确认，客户端动画/Portrait及尺寸仍须实测。未在本任务修改生产仓库。

## 当前仓库接入

仅第8波uB08，模型 war3mapImported\RiftwindHunter.mdx，视觉比例7.75。按实际模型体量与当前蚀月8倍顶部对齐；碰撞、选择圈、速度、路线和战斗数值不变。资源位于仓库 imports/，此目录保留最小再生源码。生成实体只需Python建模与三个Node导出/验证脚本；Blender仅预览，不是地图构建依赖。必须显式设置 MDX_PARSER_RUNTIME 指向既有 node_modules（mdx-m3-viewer5.7.9 / TypeScript4.9.5 / gl-matrix3.4.4），不安装新依赖或改项目锁。再生后核清单SHA再复制两个精确imports路径。未实机验证画面遮挡、Portrait回退或性能。
