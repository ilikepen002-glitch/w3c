# 宠物菜单图标源

13 个原创、可编辑、完全自包含的 SVG，统一铁质边框，分别使用齿轮、收藏册、方向箭头、农民、塔与精灵、回转箭头、晶石、卷轴、插槽、凤凰、仙女龙和小精灵轮廓。SVG 不含位图、外部字体或外部资源。正常图标与灰色禁用图标都是不透明的 64×64 BLP1，带 alpha8 和七级 mip。

原生 `BTNSelectHeroOn` 本来是红色问号；将它用于空宠物槽是选图语义错误，不能据此判断原生纹理不存在。`TDPetEmptySlot` 单独表示暗色空槽及加号，禁用技能则使用其对应灰图；没有将共鸣锁态与空槽混为同一种资源。

## 重建

从仓库根目录运行：

```sh
python tools/BuildPetUiAssets.py
python tools/BuildPetUiAssets.py --verify-only
```

已有记录使用 Inkscape 1.4（e7c3feb100）及 Pillow 12.3.0。可用 `--inkscape PATH` 显式指定 Inkscape CLI。相同版本下，SVG 先无外部依赖渲染到临时 256×256 PNG，再通过 Pillow LANCZOS 缩到 64×64，复用 `tools/BuildEvolutionAssets.py` 的 `blp()` 输出正常和亮度 0.45 的灰色禁用图。临时 PNG 和 Inkscape 配置随构建结束删除，不重建已有 11 技能或翅膀，不修改地图。

`manifest.json` 是源路径、用途、精确 Warcraft 导入路径和 SHA256 的集中清单。正常路径为 `war3mapImported\BTN{Name}.blp`；禁用路径为 `ReplaceableTextures\CommandButtonsDisabled\DISBTN{Name}.blp`。重建后会更新清单，并独立检查每一 BLP 的头、尺寸、所有 mip 的偏移/大小及 alpha、灰色禁用态和文件哈希。

`pet-ui-contactsheet.png` 从最终 BLP1 解码，顶部每对图放大 2 倍，底部提供实际 64 像素样本。它是离线纹理预览，不是游戏内截图；实际游戏显示及打包引用由地图侧独立验收。
