# 野生精灵 Walk 动画速度候选修复

基线：`ca280b1854c3d3b08582bf93ec7a7cf229d14df9`。最终按用户要求将野生精灵改为原始大小的3倍：`usca=2.55`（原始0.85×3），同时显式设置 `uwal=50.0`、`urun=50.0`。不改任何 MDX、Boss、碰撞、移动速度、路径、捕获、附身或定时器。普通局部物编表现调整。

## 已确认的证据

- 15 个 imports MDX 均有 1000ms 循环 Walk，MoveSpeed 元数据为85。逐个验证 manifest SHA256、骨骼节点/mesh matrix binding、脚/翅膀/鳍/泳脊的局部变形、无 global sequence 覆盖及循环首尾连续性。
- 采样直接解析最终 imports MDX，并排除躯干/父骨移动；不是只检查关键帧数量。完整逐种结果见同目录 `2026-10-13-pet-walk-model-audit.json`。采样全部通过，因此复用原始动作，不重做模型。
- 野生单位从 `hpea` 派生，原源码没有指定 Walk/Run 动画参考速度；旧scale=4.25，最终scale=2.55，基础移速120、运行时路径移速最多150。已连接资料中没有目标游戏 hpea 原始 SLK，不能给出继承参考速度的确切数字。
- 精灵运行时没有 SetUnitTimeScale、SetUnitAnimation 或 stand 锁定。移动由原生 move 指令驱动，物编继承 hpea 移动类型；没有证据表明应改移动类型。附身视觉的 MovementType.None 是静止展示设计，不改变。

## 速度依据与推算边界

模型使用者在 [HIVE 原始问题及后续实测回复](https://www.hiveworkshop.com/threads/is-there-any-way-to-make-a-single-unit-animation-play-faster.292358/) 描述放大导入模型后滑行，并在修改动画参考速度后自行确认：降低该字段会加快 Walk。

模型作者/测试者 [HappyCockroach 的一手说明](https://www.hiveworkshop.com/threads/mercenary-hero-gnoll-warlock.275359/) 指出参考速度对应 scale=1 时模型表观运动速度，动画按真实速度与表观速度之比缩放。以上是社区作者的一手说明与复测，不是本项目目标补丁实机验证，也不是官方引擎源码证明。

据此推算，最终50×2.55=127.5，与先前候选30×4.25保持相同尺度/参考速度乘积；120–150真实移速时，1000ms Walk 预计约0.94–1.18周期/秒。此处是针对当前模型尺度的候选校准，不把推算写成观测值。更慢的路径移速仍由原生机制同步减慢动作。保持 Run 同值以免继续继承无关农民参数；模型只含 Walk，没有 Walk Fast。

## 离线核验

已执行：

- `MDX_PARSER_MODULES=<现有解析器node_modules> node tools/asset-converter/verify-pet-walk.cjs`：15/15 PASS。
- `python3 tools/VerifyPetWalkArtifact.py`：源定义覆盖32波×15种=480个派生对象，PASS。
- `git diff --check`：PASS。

待后续独立构建批次执行：Wurst检查、完整地图构建、`python3 tools/VerifyPetWalkArtifact.py changed.w3x baseline.w3x`。产物校验要求基线只差本修复，检查全部480个对象仅usca/uwal/urun三字段变化、Boss及其余字段不变、所有15个模型/纹理字节不变。组合VFX构建必须显式使用`--combined-runtime`并披露JASS预期变化；脚本由独立VFX源码围栏与全部22主动技能运行轨迹对比核验。源码检查不能替代编译输出。

未启动 Grill、构建、游戏；未读用户截图、未进行实机验证。最终游戏内动作是否恢复、停走切换与观感仍需在目标版本确认。若候选不能修复，应继续检查实际运行地图版本和原生播放行为，不能用高频强制重播掩盖原因。
