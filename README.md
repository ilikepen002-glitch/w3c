# 深渊守望

## 地图文件

- 根目录 `ExampleMap.w3x` 是已编译、可供放入 Warcraft III 地图目录的打包产物。
- `maps/ExampleMap.source.w3x` 是 World Editor 源地图模板。地形、区域和编辑器资产应在这里修改；不要把根目录产物用作编译输入。
- Wurst 玩法源码在 `wurst/`，测试源码在 `tests/wurst/`。

原根目录源地图已原样保存到 `maps/ExampleMap.source.w3x`，SHA-256：
`627a64c012dcc46e1b5acc48dcbb20eeca0b465093718800799a2df37ded0b5e`。

## 后续构建

按项目规则运行 `tools\Run-WurstChecks.bat` 和 `build-and-deploy-test-map.bat`。
构建脚本先把 `maps\ExampleMap.source.w3x` 复制到 `_build\ExampleMap.input.w3x`，编译这个临时输入，在 `_build/` 生成地图，追加显示名时间戳后更新根目录 `ExampleMap.w3x`，然后部署到脚本配置的游戏目录。临时输入不会被当作部署产物。
发布玩法修改时，也要重新构建并提交根目录地图。历史方案文档中把 `ExampleMap.w3x` 当作源地图的路径，现对应 `maps/ExampleMap.source.w3x`。

## 本次打包验证（2026-10-08，2256）

- 基于 `4d69ea31a95d296138b0fd88c503c3ae701f2704`，保留 2228 版专用敌军电脑槽位 4 及移动命令修复。
- 所有 35 个塔等级/分支统一为显式建筑，192×192（6×6 路径格）占地，碰撞半径 96，使用原生禁建/不可走/水域过滤。允许自由摆放，不固定为十个槽位。
- 仅允许在自己的平坦高台建造，悬崖侧留 32：P1 左上、P2 右上、P3 右下、P4 左下；中心出口保留。运行时检查实际完整占地和现存塔，包括正在建造的塔，升级不另占位置。
- 源图从固定基线生成同源 WPM/Wurst 掩码，只给 9,764 个格增加 `0x08` 禁建位，另同步该 WPM 的 CRC32 元数据。W3E 地形、其他游戏成员、其他路径位逐字节未变；工人继续飞行移动。没有全图运行时路径循环。
- 使用固定官方工具链：类型检查通过，183/183 Wurst 测试通过，14/14 源图/归档回归通过；占地回归先在旧代码失败再通过。实际构建地图中 35/35 对象和导入 6×6 TGA 像素均核验通过。
- 原始源图备份：上述基线提交的 `maps/ExampleMap.source.w3x`，SHA-256 `627a64c012dcc46e1b5acc48dcbb20eeca0b465093718800799a2df37ded0b5e`。掩码源图 SHA-256 `3fd31a78aaa5d017565fca6c6f3758d40ed6131999c701bdf1f99557ba39e408`，构建前后不变。
- 未加时间戳的构建 SHA-256：`abe39cf62341f31c3dca0ca28ff164223e7a4b4ed449faaf9574b46ccc6f8cbd`。
- 根目录地图显示名与加载页标题为 `深渊守望 2256`，2256 是 2026-10-08 22:56（UTC+8）的构建标签。最终 SHA-256：`7e8617a32d895050137284785dd34f0762df2b5685c5222dbb50e77fce1ab3b2`。追加名称前后 JASS 和所有其他游戏资源一致。
- 按用户要求跳过 Gemini 审查，独立只读方案审查 PASS WITH NOTES、实现审查 PASS。保留 JASS、v1.28 和 pre1.29 标准库。
- 本次执行获准的 Linux 构建/测试，没有执行 Windows bat、Windows 部署或 Warcraft III 1.27a 实机试玩。自动测试验证的是规则与资产；原生建造预览、工人接近、取消退款/人口、升级和即时重建仍需游戏复核。跨象限限制由运行时执行，原生地形预览不区分玩家。

掩码再生成：`python3 tools/GenerateTowerTerrainMask.py --write`；一致性检查：`python3 tools/GenerateTowerTerrainMask.py --check`。输入固定为基线 Git 对象，不会对输出重复侵蚀；未审查的地形/路径修改会阻止覆盖。

源图回归：`python3 tools/VerifyTowerTerrainMask.py`。实际打包检查：`python3 tools/VerifyTowerPlacementArtifact.py ExampleMap.w3x`。

详见 [高台建塔解决记录](docs/solutions/2026-10-08-高台建塔占地与禁建掩码.md)。

## Linux 隔离检查与构建（2026-10-13 用户授权）

保留上面的 Windows 入口。Linux 使用一个独立入口，输出地图后由本机部署/试玩；此入口从不部署或启动 Warcraft。需要 Python 3、Git，以及现有 Python 产物检查所需的 Pillow/PyYAML。

准备以下真实材料，不修改 `tools/compiler/compiler-lock.json` 或 `tools/stdlib/lock.json`：
- 同一目录里的锁定 `wurstscript.jar` 和 `grill.jar`。
- 官方 OpenJDK 27+35-2325 Linux x64；入口校验 java、javac、release、modules 和 libjvm 的精确 SHA，实际 Grill compiler 子进程须解析到这个 Java。官方归档：https://jdk.java.net/archive/ ，归档 SHA256 为 `95fc37eb3a18a27a26d5904c2d89d52bace8dafa9a078ca27f4747fbc4bf070b`。
- 按 `tools/stdlib/README.md` 准备的独立 `pre1.29` Git 源树，tree 必须为 `90b45617eda50c15703e8cb2ec3241d3c7b61816`，包括真实 common.j/blizzard.j；不接受替代存根。

```bash
python3 tools/Run-WurstLinux.py checks --tools /绝对路径/verified-wurst-tools --jdk /绝对路径/jdk-27 --stdlib /绝对路径/WurstStdlib2-source
python3 tools/Run-WurstLinux.py test TDPetReleaseTests --tools /绝对路径/verified-wurst-tools --jdk /绝对路径/jdk-27 --stdlib /绝对路径/WurstStdlib2-source
python3 tools/Run-WurstLinux.py build --tools /绝对路径/verified-wurst-tools --jdk /绝对路径/jdk-27 --stdlib /绝对路径/WurstStdlib2-source
```

`checks` 串行 typecheck 和全部 Wurst tests，失败即中断；`typecheck` 和 `test` 可定向诊断。`build` 在没有测试 staging 的新事务中构建。检查/构建都复制实际 tracked、未提交/新增及 ignored imports 字节，拒绝未知链接和既有 staging，并记录输入哈希；只在临时配置精确映射那一条 stdlib URL。原始模板另复制给 Grill，不直接交给可能写 MPQ 的工具。

全仓库各 worktree 共用 Linux checks/build 锁。事务目录 `_build/linux-*` 保留日志和 manifest；结束或中断前停止整个子进程组，再清理该事务的测试 staging。编译前后校验工具/stdlib，最终地图先追加显示名，再通过原 `VerifyLegacyJass` 的真实 MPQ/JASS 门禁和独立 Python MPQ/对象表/全部 imports 字节检查；输入或候选变化、缺少/多个/旧输出均拒绝发布。所有门禁通过才原子更新根目录 `ExampleMap.w3x`（或显式 `--output` 地图路径），旧根图副本保留在事务目录。历史封闭 delta 检查仍要各自的真实历史基线，不能拿当前图冒充或放宽断言。
