# 契灵守卫战表现更新

## 静态检查点

- 最终成图对照基线为直接前序正式提交 `b729840e5ba0248810d18918e35a860bfa400ee2` 的地图，SHA256 为 `cc0444d9b6b88d0432239ffa072e94160100f9f87ea9b578868d1e26d7a1e983`。Python 内存 fixture 仍固定在 `9e32bb6f5fc20d3efc5bd6a7973047364094d206`，仅用于离线回归。
- 本次为品牌表现和隐藏预览位修复。不改玩法、物编、MDX结构或构建/打包调用顺序。隐藏预览位的写入归属从不可稳定保留的 YAML false 选项移至现有 Java 成图补丁；按高风险构建字段门禁执行 GPT-6 Astra 方案、GPT-6.1 Sol 实现与验证、GPT-6 Astra 只读审查，审查通过后才发布。
- 用户批准地图名称「契灵守卫战」、两张第二版源图及以下说明；作者仍为留白散人。

> 以塔为阵，与灵缔契！捕捉精灵、洗练绝技，让不同的契约与装备碰撞出意想不到的力量。打造属于你的王牌阵容，与契灵并肩，守到最后！

## 资源

- 原图和精确生成提示词见 `assets/source/branding/prompts-v2.json`；来源、哈希、确定性转换结果见同目录 `manifest.json`。
- `python tools/BuildMapBrandingAssets.py` 只转换离线美术资源，不调用编译或修改地图。加载背景整图缩放为1024×768，一次量化后分为四张 BLP1，共享调色板，保留原有不透明格式和完整十级mip链。先滤波整图再切分，可避免边界过滤接缝。
- 加载模型 `ui\Glues\Loading\Load-Generic\Load-Generic.mdx` 保留原字节，MDX800与四个精确TEXS路径均验证。
- 大厅缩略图为地图根路径 `war3mapPreview.tga`，256×256、32bit、未压缩、alpha255。没有替换真实 `war3mapMap.blp`。
- W3I隐藏预览位为 `0x0001`。`wurst.build` 省略 `hideMinimapPreview`：当前 Grill 会在配置序列化时自动省略显式 false，写出该键会触发事务配置哈希保护失败。`PatchMapDisplayName.java` 用当前 wc3libs 的 `MapFlag.HIDE_MINIMAP` 清位，保存原 flags，并在成图写入后回读断言等于 `originalFlags & ~0x0001`。其它位（特别是 `0x10`）必须保持。
- 源配置门禁允许该键缺省或严格布尔 false，拒绝 true、null、数字、字符串及其它类型；成图门禁仍严格要求前序 flags 只清 `0x0001`，未放宽完整 W3I、资源或 JASS 闭合校验。
- 标题、作者、说明由原生加载层叠字；源图无烧入文字。加载BLP重解码拼图和256/128缩略图已做实际离线视觉检查。

## 名称与版本核对

- `wurst.build` 的名称、加载标题、说明和加载文本使用批准内容。
- `PatchMapDisplayName.java` 的现有品牌常量及Windows部署文件名常量同步为新名，没有改变调用流程。跟踪的 `.class` 用现有同一JDK27重新编译，保源码/字节码一致。
- 历史闭合门禁 `normalize_info` 默认仍严校旧名；新名称必须显式给出 `expected_base_name`。没有全局替换历史oracle或放宽名称正则。
- 本次使用已适配品牌名的云端离线兼容入口，wrapper SHA256 为 `e87266f8e2bf702f811a9589538014bfa6dd4954296235f75bd70745ef3ed5ba`。本次窄修复没有修改共享工具或依赖。

## 已验证与待验证

静态回归入口：

```
python -m unittest discover -s tests/python -p 'test_map_branding_artifact.py' -v
python -m unittest discover -s tests/python -p 'test_global_rankings_artifact.py' -v
```

新测试覆盖完整mips、共享调色板、切块拼图与整图逐像素一致、TGA格式/alpha、MDX版本/精确纹理路径、批准元数据、flags误清`0x10`拒绝、错误作者/标题拒绝、游戏JASS/真实小地图/物编异常拒绝、preview路径/导入flag13及历史名称隔离。闭合地图回归使用内存fixture，不把fixture称作实际编图验证。

隐藏位修复新增缺省/严格 false 配置边界和恢复 `0x0001` 的拒绝用例。品牌 Python 回归 14/14 通过。`tests/java/PatchMapDisplayNamePreviewFlagTest.java` 使用同一 JDK27 和正式 g82 compiler jar，在真实 MPQ 副本上覆盖 `0`、`1`、`0x10`、`0x11`、`56433`、`0x4001`、`0x40010011`、`0x8000DC71`、`0xFFFFFFFF`，全部 9/9 通过；验证其它 W3I 字段保持及重复补丁幂等。手动 javac 与矩阵执行持 live wrapper 的同一全局锁，且确认无 active 事务。

首轮云端 `all` 已通过 typecheck、451 项 Wurst tests 和构图，但显式 false 的配置恢复保护失败，因此不能把首轮作为可发布闭合结果。该事务已正常 recover。玩法源码、测试源码和依赖未变，本次复用成功的 Wurst 检查，不重复 451 项；删除该 YAML 键后重新运行 build。历史 rankings 回归中的 20 pass / 2 fail 为既有 g82 旧断言，不在本次品牌范围内。

本次实际命令是经授权的 Linux 云端离线兼容入口，不是执行 Windows BAT，也未启动 Warcraft III：

```
/workspace/scratch/2106c0ab1fac/python-3.13.5-project/run python /workspace/scratch/2106c0ab1fac/toolchain-recovery-20261012/cloud_wrapper.py build --repo /workspace/scratch/2106c0ab1fac/map-branding-20261012/release-worktree --no-publish --verbose
```

最终构图后运行实际候选地图校验：

```
python tools/VerifyMapBrandingArtifact.py <实际 candidate.w3x> --baseline-map /workspace/scratch/2106c0ab1fac/map-branding-20261012/release-evidence/baseline-b729840.w3x
```

该校验必须读取本次实际成图，要求源/成图MDX不变、四BLP和root preview精确路径/导入flag13、其它flags/完整W3I结构不变、真实小地图/物编/其它资源字节不变、JASS仅允许名称和说明两个config字符串变化，并严格校验地图名/加载标题构建时间戳一致。

最终云端 `build --no-publish --verbose` 和实际 `VerifyMapBrandingArtifact.py` 均通过。候选地图来自事务 `96278520dab0457a932cd5e92eea7d42`，显示名为 `契灵守卫战 20261012-2359-UTC+8`，SHA256 为 `603fcffbbbb690bdfffef50de36847af5e03b0ed8deb04f62f08e7a518288476`。成图共有 182 项资源，flags 从 `56433` 精确变为 `56432`；完整 W3I 规范化一致，JASS 仅两处 metadata config 字符串变化，MDX、真实小地图、物编和其它资源保持原字节。

同事务 `result.json` 已生成，`journal.json` 状态为 `restored`，所有受管文件均恢复，active 事务和测试 staging 均不存在，跟踪 patcher class 与该构图实际使用的 class 哈希相同。日志、实际成图门禁输出和哈希/闭合诊断保存在任务的 `release-evidence/preview-flag-*` 证据中。GPT-6 Astra 最终只读审查结论为 `PASS WITH NOTES`，无阻塞项；独立重跑实际成品门禁、基线字节、跟踪 class 和事务恢复检查均通过。经审查的同一候选复制为根 `ExampleMap.w3x`，哈希为上述候选哈希。未执行 Windows BAT、Windows 部署或游戏实机显示检查。

构建 `result.json` 的 `sourceCommit/sourceTree` 指向修复前本地 HEAD `ae28f761c359970449b57911754a69964ead25e9`，不能单独代表完整构建输入；当次未提交修复的精确差异和逐文件哈希已保留，且本次发布包含这批已审查、已构图的输入。品牌修复未触及既有 g82 类分配上限与旧版 Warcraft 数组容量的兼容风险，仍按用户要求保留供本地检查。
