# 精灵管理：独立静态实施阶段

## 来源与门禁

- 独立基线：0330fd12de4d66c4a1ca4980e10b771f0903fbfc。
- 实施：GPT-6.1 Sol。风险：高风险；GPT-6 Astra / xhigh 的方案阶段已通过，实际实现终审尚未执行。
- 本阶段只在独立持久 worktree 改源码和资源。没有继承其他任务未提交源码；没有调用 Wurst 编译器、检查 wrapper、完整构建、共享 staging、游戏、push 或生成最终根地图。
- 这是可继续集成的静态候选，不是已验收发布版本。

## 实现

- 20 固定编号，2 页各 10 槽，释放留空、捕获补首空；满仓在扣球前拒绝。
- 品质取所有已拥有技能最大值，含共鸣锁定栏；未采用候选不计，可随正式技能替换下降。没有属性、捕获率或野生投放变化。
- 原生命令卡 LIST / DETAIL / CULTIVATE / PREVIEW / RELEASE_CONFIRM / CLOSED；没有常用 Dialog 或新版 Frame。
- 每次需要重新授权时生成全新展示单位，同步挂载页面能力，再公布新权限、退役旧单位，最后本地选择。旧身份、错误等级/页面/能力不获准；0 秒延后移除只负责清理，不声称网络队列已排空。
- 0.5 秒轮询只标脏或关闭，不重建或强制选择。脏点击消费旧权限、拒绝事务并刷新；无变化 W 刷新只输出摘要。
- 真实选择/取消选择关闭管理、取消释放票据，保留候选。旧展示迟到选择（包括已移除的 type=0 句柄）被忽略；不使用“程序选择”布尔掩码。
- 候选单调版本和源技能 revision；先确定合法随机候选再扣一次石。重开/离开/换绑不自动解决候选。采用拒绝变化的源；用户明确保留可丢弃该候选，不更改技能本体。
- 释放仍以 record / revision / generation / nonce 校验并先消费，失败不删、不奖；每塔 1 只、换绑先校验新塔、冷却保留。旧农民 Pdep 只导航，不直接部署。
- 物编设计：130 两等级收藏 Channel + 21 页面 Channel = 151；516 原技能被动 + 32 四品质比较被动 = 548；1 收藏 + 12 物种/品质展示原型 = 13。
- 28 SVG 图标/56 BTN+DIS BLP：保留原 13 原图与 BLP 字节，新增 12 品质边框和释放/保留/采用 3 语义。离线接触表已目视检查。
- 个人 HUD 只修改现有状态 board 的同一行摘要；不新建、不隐藏全玩家排行 board。未增加生效标签或生效数量。

## 本阶段已验证

1. python tools/VerifyPetManagerSource.py：通过。
   - 执行选定真实源码的 861 页面/动作组合、151/548 rawcode 分区、20 编号、1280 品质组合、200 跳空/200 lane 隔离组合及越界拒绝。
   - 源码接线检查：权限、消费顺序、同步/本地边界、脏轮询、候选/释放生命周期、完整原技能品质计算、野生投放文件不变、board 创建数量不变。
2. python -m unittest discover -s tests/python -p test_pet_manager_contracts.py -v：12 项通过。
   - 真实源码规则/接线变异拒绝；受控未来物编 shape 的页面、130 收藏/32 比较对象、品质/编号/target/cell/rawcode/order 等负例。
   - 受控 shape 验证的是 verifier，不冒充实际 W3A/W3U 打包。
3. python tools/BuildPetUiAssets.py --only-new 和 --verify-only：通过。
   - 28 精确名称，56 BLP1 alpha8，64×64，7 mip，路径/hash，禁用灰度和变暗，原 13 字节锁定。
4. 31 项历史物编 fixture / 当前源码图标接线 / 当前 56 图标资源负例：通过。
   - 历史 fixture 明确从基线 Git blob 读取，与当前管理验收分开。
5. 6 项历史 Dialog fixture 检查：通过；仅保留历史 regression，不用于新 UI 验收。
6. 14 项原语义图标纯源码/资源检查：通过，原 13 精灵资产 hash 未变。
7. 修改 Python 文件 py_compile 和 git diff --check：通过。

## 未运行与后续必需验证

- Wurst 语法/typecheck、所有 Wurst 测试与真实会话/事务测试未运行。已补 TDPetManagerTests 和更新容量/UIData/释放测试，须在合并后按项目 wrapper 串行运行。
- 未完整构建，未检查真实新 W3A/W3U/MPQ、订单池和 rawcode 全图唯一性、实际导入与哈希，未生成根目录时间戳地图。
- 新默认 VerifyPetUIArtifact 验收原生命令页和 13 展示原型，并要求前置大师球/合成移除已保留；旧 Dialog 和 12 槽差分只保留历史 helper/显式历史模式。
- 默认 VerifyPetDeploymentArtifact 已改 20 槽 gate fixture；--historical-differential 才执行旧 12 槽单尾差分。
- 必须在最新正式 HEAD 集成后统一完整验证和 Astra 实现终审 PASS / 非阻塞 PASS WITH NOTES，再按已授权发布要求独立 push。
- 没有实机：原生命令卡绘制、ESC 瞄准、shift 选择、网络迟到事件、实际性能均未观察。

## 最后集成注意

1. 只按本分支差异合入最新正式 HEAD，不能回写旧整文件。
2. TDPetData / State / Runtime / ObjectGen 基线仍有大师球和合成。本改动没有新增或恢复它们；合并时保留前置移除，不从本工作区整文件覆盖最新版。
3. 复核农民最终入口与布局：Q 捕获保留，Pcol/管理入口保持可达；若前置任务已移除 Pdep，则不要恢复它。本阶段存在的旧 Pdep 已改无目标导航。
4. TDHud 只移植短个人摘要到前置任务最终同一个排行/状态 Multiboard 的个人行，不覆盖最新版 HUD。
5. 最终农民布局/功能书 verifier 和旧语义图标 master/forge 断言属于前置移除任务的接口，须跟随最新正式状态适配；不把本阶段基线的残留当作最终需求。
6. 最终产物 gate 针对最新构建地图运行，不能用本阶段历史 fixture PASS 替代。
