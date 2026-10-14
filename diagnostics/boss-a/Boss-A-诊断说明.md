# Boss-A 拉伸诊断图

这是独立诊断候选，不是已确认修复，不替代正式 `ExampleMap.w3x`。加载副标题含“Boss-A诊断（原生效果未验证）”。

- 基于正式提交 `2847c3f742a69661972cabb7a616e08e81cbae9c`，保留该版所有玩法、塔/精灵平衡、尸体清理及野怪标记修复。
- 仅将 EclipseSpellweaver 模型的 25 个骨骼 GeosetId 从 -1 改为 0，精确变动 100 字节；网格、动画、骨骼层级、绑定、材质、纹理及边界全部保持原字节。这个候选用于排查模型元数据兼容性，不保证解决拉伸。
- 官方 Linux 完整检查、全部 Wurst 测试、地图构建和最终 MPQ 核验通过。没有启动 Warcraft III；实际拉伸、动作表现及渲染兼容性仍需游戏内观察。
- 与正式图比较：MPQ 清单 418 项，无新增/删除，416 项原字节不变。仅模型及 `war3map.w3i` 不同；后者只增加诊断副标题及正常构建时间（09:32 → 09:34，UTC+8）。脚本、全部单位/技能对象、地形、路径、纹理及其他资源均相同；四个 Boss 对象不变，uB24 缩放仍为 8.0。

建议使用相同 Warcraft 版本、相同场景对比正式图与 Boss-A 图，重点观察原先拉伸发生时的 Boss 动作。若表现没有改善，这个结果只排除本次 GeosetId 假设，不代表其它动画或引擎兼容因素已排除。

## 文件校验

- Boss-A诊断.w3x SHA256：`d27ad697450a342ed08ba4eccd261be395482c48023758eb4da18d0c886a3349`
- 正式 ExampleMap.w3x SHA256：`f28f375462e64ea08e159eea88e386582cdcb1e2b3dc448fe979108a40468a13`
- 候选模型 SHA256：`f928308fbb4f09e14703852feaa0251e623e4e6b462f12b1809ab50609a70d73`
- 原模型 SHA256：`b19878db04cfef6dc053d6443281e312f95ff1375dd3f4a38007a29c7ea90406`

## 隔离复现（Linux）

同目录 `Boss-A-diagnostic.patch` 是完整、自包含且含二进制差异的小补丁，不依赖未发布诊断提交。请勿应用到正式工作树；生产模型与生产 wurst.build 应保留原样。下列路径变量请换成自己的绝对路径。工具链须是项目官方 Linux 入口认可的已校验工具链。

```bash
REPO=/absolute/path/to/formal-checkout
EVIDENCE=/absolute/path/to/this-diagnostic-directory
WORK=/absolute/path/to/new-boss-a-worktree
TC=/absolute/path/to/verified-toolchain
OUTPUT=/absolute/path/to/Boss-A诊断.w3x
BASE=2847c3f742a69661972cabb7a616e08e81cbae9c

git -C "$REPO" worktree add --detach "$WORK" "$BASE"
git -C "$WORK" apply --check "$EVIDENCE/Boss-A-diagnostic.patch"
git -C "$WORK" apply "$EVIDENCE/Boss-A-diagnostic.patch"

# 四个被 Git 忽略的原始 Leoric 资源，从已核验的正式工作树复制。
for FILE in imports/KingLeoric-original-readme.html imports/Leoric.blp \
  imports/war3mapImported/Leoric.mdx imports/war3mapImported/Leoric_Portrait.mdx; do
  cp "$REPO/$FILE" "$WORK/$FILE"
  cmp "$REPO/$FILE" "$WORK/$FILE" || exit 1
done

cd "$WORK"
python3 tools/VerifyEclipseBossCandidate.py
python3 tools/Run-WurstLinux.py checks \
  --tools "$TC/library-inputs/verified-wurst-tools" \
  --jdk "$TC/jdk-27" --stdlib "$TC/WurstStdlib2-source"
python3 tools/Run-WurstLinux.py build \
  --tools "$TC/library-inputs/verified-wurst-tools" \
  --jdk "$TC/jdk-27" --stdlib "$TC/WurstStdlib2-source" --output "$OUTPUT"
python3 tools/VerifyEclipseBossCandidate.py \
  --map "$OUTPUT" --reference-map "$REPO/ExampleMap.w3x"
```

检查与构建必须串行。若正式工作树缺失上述 ignored 文件，先使用仓库 `tools/RestoreKingLeoricAssets.py` 的既有恢复流程，从已核验正式地图恢复，不要生成替代资源。参考图须核对上面的正式 SHA256。重新构建会自动更新时间戳，因此完整地图 SHA256 会不同；候选模型 SHA256 和 100 字节差异应完全一致。

本次四个 ignored 输入 SHA256：

```
0e6547dac6b9c642e3ca7805fa56235dd66f716a851ae089d151192e15e99be3  imports/KingLeoric-original-readme.html
c7b229e3ddae7cda6ea632e9fbabfe6f1c8863d37d6fef7c97b51318c600ed2c  imports/Leoric.blp
f68cc2971589fac2518d934a8f445e8667812ecd5f1a7d26fb295bf26a1e5245  imports/war3mapImported/Leoric.mdx
1c9a56c3025369a5eb5eb00481b7b7a7239a68c730f7b0fb2dae03830fce143f  imports/war3mapImported/Leoric_Portrait.mdx
```
