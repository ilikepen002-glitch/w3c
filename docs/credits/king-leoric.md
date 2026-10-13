# 黑曜棺卫：King Leoric 模型来源与重建

此改动仅将第16波黑曜棺卫 `uB16` 的模型替换为作者原版 King Leoric，并将该模型的视觉比例设为 **原版的1.30倍**。原对象仍继承 `Ocbh`；此前未显式设置模型比例。不是对旧牛头人模型体积的1.30倍比较。碰撞、路径、速度、射程、技能与战斗数值不变。

## 原作者与使用范围

- [原作者发布页](https://www.hiveworkshop.com/threads/diablo-iii-king-leoric.224358/)
- [作者资源的导入说明](https://www.hiveworkshop.com/resources/diablo-iii-king-leoric.33561/import)
- 网格：HappyTauren / TotallyAwesome
- 贴图：AnemicRoyalty / A.R.
- 动画与粒子：Tarrasque / Jigrael（原说明拼作 Terrasque）

作者将原项目的资源公开供地图使用，并在发布页回复中允许项目压缩贴图和缩减体积。本次使用未经修改的原始文件；不据此推定任意修改、单独资源再发布或标准开源许可证。Hive 的 [资源提交规则](https://www.hiveworkshop.com/threads/resource-submission-rules-models-skins-icons-spells-systems.237333/) 与 [地图提交规则](https://www.hiveworkshop.com/threads/map-submission-rules.228244/) 也不能替代作者授权。

原作者署名随地图嵌入 `Credits-KingLeoric.txt` 与作者包原始 `KingLeoric-original-readme.html`。项目没有现成 F9 帮助页；这些文件不是玩家屏幕上的署名页。来源和署名亦在本文保留。未向作者发送任何联系消息。

## 公开源码不包含独立模型二进制

原始 MDX/BLP 与原作者 readme 仅在私有素材备份和最终地图内保存，四个准备导入的文件被 `.gitignore` 精确排除。不将独立模型资源放入公开 Git。**仅 clone 仓库不能重建包含该模型的地图，必须先取得作者原包。**

1. 打开原作者发布页，使用其 Download 取得包含 Leoric 主模型、portrait 和贴图的 ZIP。
2. 从仓库根运行 `python3 tools/RestoreKingLeoricAssets.py /absolute/path/to/author-download.zip`。
3. 用 `--check` 再核对本地导入文件。脚本只读本地 ZIP，按清单校验每一个原始字节，不联网、不运行包内代码、不改模型，不覆盖与清单不同的已有文件。
4. 使用项目规定的检查与唯一地图构建入口；Linux 适配入口须遵循项目当次批准的方案，不能替换为旧版编译器。
5. 完成本次地图对象、精确 MPQ 路径、导入记录和资源哈希验证，之后才能宣称已接入。

确定性文件清单见 `assets/source/king-leoric.json`。主模型路径 `war3mapImported\Leoric.mdx`、同目录 `Leoric_Portrait.mdx`；贴图必须在地图根 `Leoric.blp`，不能移到 `war3mapImported`。portrait 按同目录同名前缀自动查找。

复用项目已锁定 `tools/asset-converter` 依赖后，可运行 `node tools/asset-converter/inspect-king-leoric.cjs` 只读检查准备好的 imports。合成门禁回归运行 `python3 -m unittest discover -s tests/python -p test_king_leoric_assets.py`。本次单独构图后，用 `python3 tools/VerifyKingLeoricArtifact.py new.w3x baseline.w3x` 检查实际地图；baseline 必须是同工具链、接入此模型前的正式版本，不能将其它功能发布的差异放宽成模型允许项。

## 已证实与待验证边界

离线解析：主模型 MDX800，972三角面，22骨骼、2 helper；portrait MDX800，486三角面。原贴图 BLP1、256×256、8bit alpha、9级 mip。主模型包含 Stand、Walk、Walk Fast、Death 等14个动画。原始字节未重导出、未优化或修改。

解析还发现主模型引用原生 `Textures\clouds_anim1.blp`、`Textures\RibbonBlur1.blp`，portrait 用原生 TeamGlow（replaceable ID 2），以及原生声音/脚印/溅射事件。它们不是作者包内遗漏的自带贴图。必须从目标 1.27a 安装资源核对；当前尚无该安装资源实证，不能只凭 MDX800 宣称全部依赖已证兼容。

离线预览只显示实际 MDX 网格、骨骼姿势和原 BLP 漫反射/alpha，采用中性离线灯光，不模拟原生粒子、拖尾、声音或脚印。比例、遮挡和帧率没有游戏实测。实际地图构建与物编打包验收仍是必要步骤，不能由离线渲染替代。
