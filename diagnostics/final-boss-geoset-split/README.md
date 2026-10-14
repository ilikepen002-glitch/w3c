# BossMeshSplitTest：最后两只Boss网格拆分诊断图

这是独立候选，未确认解决Warcraft 1.27a原生拉伸；不要代替正式 ExampleMap.w3x。仅供单人、玩家1测试模型。地图名和加载标题明确为“BossMeshSplitTest网格诊断”。

## 直接测试

打开本目录 BossMeshSplitTest.w3x。无需打到24/32波：

- 输入 `-boss24` 展示蚀月织咒者；`-boss32` 展示无冕深渊君王。旧测试单位先移除，只留一只。
- 镜头会聚焦测试单位。`-boss focus` 可重新聚焦；也可手动移开镜头再返回，观察是否再次拉伸。
- `-boss stand` 待机，`-boss walk` 原地行走动画，`-boss attack` 攻击/施法，`-boss hit` 受击，`-boss death` 死亡动画，`-boss portrait` 肖像动作。可重复输入重播。蚀月没有Attack，attack明确播放Spell；深渊播放Attack。`-boss spell` 是相同动作别名。
- `-boss move` 真实行走，每次在左右两个目标之间切换。`-boss turn` 转90度。动画命令会先停止当前移动再播放，不宣称支持移动中同时攻击。
- `-boss clear` 移除测试单位，可重复调用；`-boss help` 看帮助。

模型在固定坐标(-2048,1024)创建，使用原物编体型；中立被动、无敌、关闭寻路碰撞。未接入敌人注册、波次计数或奖励；未创建周期定时器。仅P1聊天事件可操作。普通波次仍按底图运行，测试结果不是正常闯关/战斗验证。

建议分别看两模型的待机、行走、转向、攻击/施法、死亡，并移动镜头离开再返回。记录具体命令与画面；如仍破面，请保留截图。离线检查不能证明原生镜头、动画混合或GPU兼容性。

## 构建与变更边界

底图：15204026e89f1da7d399b66d03d0d8bd9edbbc6c（包含升级取消全额返还）。最终地图SHA256：

37a1b54900e5e77e5b96031ceb543b27c220a0c33002ff7197ae2287ba803903

实际MPQ共有427项，仅4项与底图不同：两只MDX、war3map.j、war3map.w3i。其余423项逐字节相同，包括全部物编、贴图、地形、路径与其他模型。JASS新增7个诊断函数；既有代码只增加诊断初始化/回调引用与测试地图名称，已逐函数和globals严格核对。

两只MDX仅GEOS chunk改变：蚀月拆6片，深渊拆7片，每片≤3000顶点。保留原三角顺序、位置、法线、UV、骨骼绑定、矩阵组、骨骼metadata、动作、材质、extents与scale。完整有序角点及各模型606个采样姿态逐点等价，最大坐标差0。所有关键帧都纳入采样，8类负例门禁通过。**16384不是本次证明的旧引擎硬上限。**

官方Linux完整typecheck+全部Wurst测试PASS，官方build与实际MPQ/import/legacy JASS/启动门禁PASS；聊天命令离线重放PASS。未启动Warcraft，未实机验证。

## 文件及隔离重建

- source.patch：完整自包含二进制补丁，包含两MDX、诊断包、生成/门禁工具和诊断标题的构建配置。只可用于独立诊断工作树，切勿应用到正式源码。
- offline-report.json / negative-tests.txt：模型语义等价和负例。
- artifact-report.json / VerifyBossMeshSplitDiagnostic.py：最终MPQ差异和命令重放。
- *manifest.json / wurst-*.log：构建证据。第一次checks因引用私有rawcode常量失败，已局部改为诊断字面量并完整重跑通过；第一次build因正式地图标题门禁不接受测试名称失败，诊断专用Java标题与校验期望统一后完整重跑通过。未移除门禁。

在基于上述底图的新独立工作树应用source.patch，按现有恢复流程准备4个ignored Leoric资源，再执行官方入口，保持检查→构建串行：

    python3 tools/Run-WurstLinux.py checks --tools TOOLS --jdk JDK --stdlib STDLIB
    python3 tools/Run-WurstLinux.py build --tools TOOLS --jdk JDK --stdlib STDLIB --output /absolute/path/BossMeshSplitTest.w3x

TOOLS/JDK/STDLIB须为项目认可的已校验工具链路径。模型再生和离线门禁：设置MDX_PARSER_RUNTIME为已安装node_modules路径，然后运行 `node tools/SplitFinalBossGeosets.cjs --write` 和 `node tools/TestFinalBossGeosetGate.cjs`。冻结原模型缺失时脚本从固定a8094440地图提取同hash原始MDX；不是从候选反向生成。

最终核验：

    python3 diagnostics/final-boss-geoset-split/VerifyBossMeshSplitDiagnostic.py /absolute/path/BossMeshSplitTest.w3x /absolute/path/report.json /absolute/path/repo

时间戳变化使重建地图总hash不同，模型hash/语义门禁不变。正式production-manifest维持原hash，不为候选放宽生产冻结要求。

## 临时证据保留说明

磁盘紧张时，已保留日志和manifest后清除了本次两次checks的隔离临时目录linux-yet_9n5w及linux-7ffwnvfy。它们的完整失败/成功快照不再存在。两次build快照未删除。此目录保存已列出的可复核证据，不声称保存全部历史快照。
