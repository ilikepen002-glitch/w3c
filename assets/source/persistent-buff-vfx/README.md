# 原创塔身持续强化特效

本目录只交付资源，没有修改任何 Wurst、战斗逻辑、准入/预算或清理责任，没有构建或启动游戏。集成者须让每种强化持有一个现有预算内的 effect handle，并在失效/死亡/出售时清理。

- `war3mapImported\TDPetBuffFrenzyOrbit.mdx`：红色双斜弧反向环绕，尖焰与菱形余烬。152 三角，2 材质，2 骨骼，1200 ms Stand 循环，每 400 ms 脉动。
- `war3mapImported\TDPetBuffChargeSeal.mdx`：金/暖白三层断环，四组竖向空心符文。176 三角，2 材质，4 骨骼，1800 ms Stand 缓脉，没有狂热式旋转。

两者均为 MDX800 的纯薄片 mesh，无粒子、ribbon、事件、灯光、额外挂载或全局序列。材质为 AddAlpha、Unshaded、TwoSided、NoDepthSet；保留正常深度测试，不会用巨大不透明球遮住宿主。Stand 0 ms 已可见，Death 2000–2050 ms 全透明。

## 纹理与出处

几何和动画是本任务用 `build_source.py` 原创生成的，没有第三方模型或新增贴图。唯一贴图是正式地图已有的 `Textures\TDPetVfxAtlas.blp`，使用已有暖白色 swatch 的 UV `[5.5/64, 3.5/64]`。该 atlas 的出处沿用 `../elemental-vfx/PROVENANCE.md`。

在正式提交 `2847c3f742a69661972cabb7a616e08e81cbae9c` 的 `ExampleMap.w3x` 内按精确路径提取，确认 atlas 12,102 字节与 imports 字节完全相同：

- atlas SHA-256：`d47bf6ab34bdbfc651954cbf460d8ff82c770de66da8d4e4c3259131b810fa1a`
- 正式地图 SHA-256：`f28f375462e64ea08e159eea88e386582cdcb1e2b3dc448fe979108a40468a13`

这只验证共享纹理已存在，不表示这两个新模型已打入正式地图。新地图的精确模型路径、hash 和 runtime 创建/清理仍由集成阶段检查。

## 重建与验证

使用工作区已存在的固定依赖：mdx-m3-viewer 5.7.9、TypeScript 4.9.5、gl-matrix 3.4.4。无需安装新软件。

```sh
python3 assets/source/persistent-buff-vfx/build_source.py
MDX_PARSER_RUNTIME=/absolute/path/to/pinned/node_modules node assets/source/persistent-buff-vfx/export_validate.cjs --check-imports
python3 assets/source/persistent-buff-vfx/render_preview.py
```

如果有意修改原创模型，先不传 `--check-imports` 重建，再把 `output/*.mdx` 复制至 `imports/war3mapImported/`，最后传该选项检查导出与 imports 字节一致。源码 JSON、作者/导出/预览脚本、紧凑 `manifest.json`、contact sheet 和 imports MDX 入库；MDL、完整采样记录、单帧大图与 actual-speed GIF 可重建，保留本地。

导出器读取实际写出的 MDX 字节，检查无损 roundtrip、MDX800、精确 TEXS 路径、纹理存在、三角/材质预算、骨骼引用、有限值/单位 normals、材质 flags 和循环标志。Stand 每 10 ms 采样动画与变换后的全部顶点，Death 每 1 ms 采样 alpha；0–50 ms 各层 alpha ≥0.75；循环端点几何与 alpha 一致。有限采样下：

- 狂热：高度 72.84–136，最大轮廓半径 56.21
- 蓄力：高度 48–135.80，最大轮廓半径 58.68

以上坐标相对 effect origin，按 effect 自身 1.0 scale 计算；没有声称符合每个宿主的 attachment transform。设计参考 `wurst/pets/TDPetDisplayRules.wurst` 的保守模型高度估计，以及 `wurst/towers/TDTowerObjectGen.wurst` 的等级 scaling（0.95 + level × 0.03），没有原生塔模型字节可测量真实躯干坐标。

## 预览边界

`previews/frame-contact-sheet.png` 和可重建 GIF 使用实际重解析 MDX 的三角形、UV swatch 和采样动画。灰柱是人为制作的 145 单位中性代理，并非 Warcraft 原生塔模型；它仅用于近似软件深度测试。预览不是游戏截图，不证明 1.27a 原生混合、遮挡、挂点、所有塔模型适配或 FPS；这些需要后续明确授权的实机观察。
