# AGENTS.md - WurstScript 地图项目协作说明

适用于本项目中与 `.wurst` 代码、测试、编译脚本、对象生成、依赖和地图构建相关的工作。

目标是让代理和协作者在这个仓库里：

- 更快找到正确入口
- 更稳定地改对地方
- 用统一方式验证结果
- 避免破坏构建、测试和地图部署流程

## 30 秒速查

- 改源码，不改 `_build/`、`_build/dependencies/`、`war3map.j`
- 测试源码只放 `tests/wurst/`，不要手工维护 `wurst/_tests/`
- 常规检查跑 `tools\Run-WurstChecks.bat`
- 涉及物编、构建、核心玩法或实际可玩性时，加跑 `build-and-deploy-test-map.bat`
- 默认工作流是 `Codex 实现 -> Gemini 审查 -> Codex 修复/交付`
- 只有用户明确说“跳过 Gemini / 这次不审查 / skip review”时，才允许跳过审查
- Gemini 统一走 `tools\Invoke-GeminiReview.ps1`
- 看不清需求落点时，先查 `wurst/`、`wurst/towers/`、`tests/wurst/`、`wurst.build`

## 默认双 Agent 协作模式

本仓库默认使用：

- `DevAgent = Codex`：负责实现、测试、修复和最终交付
- `ReviewAgent = Gemini CLI`：负责方案审查和代码审查

默认流程：

1. Codex 完成本地实现和最小验证
2. 交付前默认调用 Gemini 审查
3. Gemini 未通过时，先修复再送审
4. 只有 Gemini 通过，或用户明确要求“跳过 Gemini / 这次不审查 / skip review”时，才允许按已完成交付

额外规则：

- 不要因为任务小就自动省略审查
- Gemini 不可用、鉴权失败或命令失败时，默认视为“审查未完成”，必须如实报告
- 只有用户再次明确同意“无审查交付”，才允许在 Gemini 不可用时继续结束任务

角色边界：

- Codex 负责把改动落在正确源码位置，并按本文件规则执行验证
- Gemini 只读审查，不直接改仓库
- Gemini 审查优先关注：玩法回归、初始化顺序、compiletime 物编、rawcode/升级链一致性、缺失验证、误改生成物
- Gemini 结论必须明确为 `PASS`、`PASS WITH NOTES` 或 `FAIL`

Gemini 调用：

- 必须自动带代理：`HTTP_PROXY=http://127.0.0.1:7890`、`HTTPS_PROXY=http://127.0.0.1:7890`
- 统一使用仓库脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\Invoke-GeminiReview.ps1 -Task "本次改动说明"
```

审查门禁：

- 默认要求审查的场景：最终交付、提交前整理、核心玩法改动、物编生成改动、构建或部署流程改动
- 如果当前只是探索、定位问题或起草方案，可以先不送审；一旦进入“准备交付改动”，默认必须送审

最终说明至少要写明：

- 是否实际调用了 Gemini
- Gemini 的结论，或未执行成功的阻塞原因
- 如果跳过审查，明确写“按用户要求跳过 Gemini 审查”

## 工作原则

- 优先选择简单、可维护的方案。修根因，不堆脆弱补丁、重复分支或特殊判定。
- 改源码，不改生成物。`_build/`、`_build/dependencies/`、`war3map.j` 都不是源码真相。
- 优先复用 Wurst 标准库、项目辅助函数和已有模式，不要轻易退回 `common.j` 或纯 Jass 风格写法。
- 不确定 Wurst 语法、局部 API、初始化顺序或对象生成方式时，先找项目内相邻的可运行例子，再决定怎么写。
- 包保持聚焦，尽量控制在约 500 行以内；按功能、职责、数据类型拆分。
- 测试尽量小而准。优先补行为测试、共享工具测试、compiletime 生成测试，而不是大而全的端到端替代品。
- 避免与当前任务无关的大重构；只有在它能直接降低当前改动风险或明显简化实现时才做。

## 长期疑难问题沉淀

当一个长期未解决、曾多次排查失败，或根因明显不直观的问题最终被解决后，必须新建一篇独立解决记录，为后续提炼项目技能做准备。

- 记录统一放在 `docs/solutions/`，文件名使用 `YYYY-MM-DD-简短问题名.md`
- 不要只在提交信息、聊天记录或源码注释中提及；解决记录必须能独立说明问题
- 只记录具有复用价值的疑难问题，不为普通的小修复制造文档噪音
- 重点记录可迁移的诊断方法、关键线索和验证方式，不写冗长排查流水账
- 如果解决方案暴露出稳定、可重复的工作流，应在记录末尾列出“可提炼技能”，供后续创建或更新技能时使用

解决记录至少包含：

- 问题现象与影响范围
- 关键环境和触发条件
- 曾尝试但无效的方法，以及它们为什么无效
- 最终根因
- 最终解决方案及关键改动
- 验证命令、验证结果和残余风险
- 可复用经验与可提炼技能

## 先看哪里

开始改动前，优先确认这些位置：

- `wurst/`
  当前地图源码主目录。大部分游戏逻辑都在这里。
- `wurst/towers/`
  塔相关逻辑优先从这里找模式和入口。
- `tests/wurst/`
  测试源码主目录。新增或修改测试优先放这里。
- `tools/Run-WurstChecks.bat`
  日常类型检查和测试的统一入口。
- `tools/Sync-WurstTests.ps1`
  测试同步脚本。会把 `tests/wurst/` 临时同步到 `wurst/_tests/` 后再运行检查。
- `build-and-deploy-test-map.bat`
  唯一允许使用的“编译并部署测试地图”入口。
- `wurst.build`
  项目根配置，包含依赖、地图元数据、脚本模式、补丁版本等。

如果只是要理解当前业务结构，通常先看这些文件最划算：

- `wurst/TDConfig.wurst`
- `wurst/TDInit.wurst`
- `wurst/TDGame.wurst`
- `wurst/TDState.wurst`
- `wurst/TDSpawn.wurst`
- `wurst/TDTowers.wurst`
- `wurst/TDWaves.wurst`

## 当前项目事实

除非用户明确要求修改，否则默认按下面处理：

- `scriptMode: JASS`
- `wc3Patch: v1.28`
- 构建产物输出到 `_build/`
- 测试源码真相目录是 `tests/wurst/`
- `wurst/_tests/` 只是检查脚本的临时 staging 目录
- 最终编译与部署只允许走 `build-and-deploy-test-map.bat`

## 架构要求

下面这些不是“建议风格”，而是当前项目为了稳定迭代而明确采用的架构约束：

- 先按职责拆分，再按功能扩展；不要一开始就把系统做成很多横切抽象层。
- 共享规则、运行时行为、compiletime 物编生成、测试源码要分开，避免一个文件同时承担多种变更原因。
- 对外入口应稳定。允许内部继续拆文件，但尽量保留上层 facade，避免无意义地连锁修改 import。
- 新增逻辑优先挂到最贴近职责的位置；如果只是改某类数据，不要顺手改运行时触发或构建脚本。
- 重复达到 3 处以上、且未来大概率一起改的逻辑，优先提炼成共享 helper；但不要为了“抽象”把本来清晰的数据表绕复杂。
- 测试源码与生产源码分离，测试只能通过 staging 进入检查流程，不能长期混在最终打包源目录中。
- 任何会影响对象生成、升级链、rawcode、技能栏、建造菜单的改动，都应视为“架构敏感改动”，必须先看现有塔目录结构和相关测试。

## 当前结构

当前源码按“系统入口 + 塔子域拆分 + 测试独立目录”组织，默认按下面边界改：

- `wurst/TDConfig.wurst`
  地图级配置、塔位/路线/出生点等静态坐标与共享常量。
- `wurst/TDState.wurst`
  运行时状态容器，例如金币、生命、波次、路线状态。
- `wurst/TDSpawn.wurst`
  敌人生成、敌军单位归属与刷怪辅助。
- `wurst/TDGame.wurst`
  波次推进、漏怪、HUD、胜负结算等核心流程。
- `wurst/TDInit.wurst`
  地图启动、初始化编排、运行时系统挂接。
- `wurst/TDWaves.wurst`
  波次配置与奖励节奏定义。
- `wurst/TDTowers.wurst`
  塔系统的稳定 facade。外部优先 import 这里，而不是直接依赖某个子文件，除非当前任务就是在维护塔子域内部结构。

塔子目录 `wurst/towers/` 的职责：

- `TDTowerCatalogData.wurst`
  塔 rawcode、等级链、升级链、基础技能 rawcode、塔族与等级映射。
- `TDTowerCommonData.wurst`
  农民/工资/完美升级/共享技能调参等跨塔族共用配置。
- `TDTowerBalanceData.wurst`
  塔数值、文案、图标、模型、按钮位、攻击类型、表现层数据。
- `TDTowerData.wurst`
  上述 tower data 子包的聚合 facade；其他塔相关实现优先依赖它。
- `TDTowerRuntime.wurst`
  建塔占格、农民、升级事件、死亡事件、分裂箭、尸爆、工资施法等运行时行为。
- `TDTowerObjectGen.wurst`
  compiletime 单位/技能/建筑物编生成。新增塔等级、改升级链、改技能挂载时优先看这里。

- 测试统一放 `tests/wurst/`，不要手工维护 `wurst/_tests/`
- 保持 `TDTowers -> TDTowerData/TDTowerRuntime/TDTowerObjectGen` 这层稳定边界
- 只有当某个塔族已经出现独立复杂逻辑时，再考虑继续按塔族拆文件

## 实现归属边界

先判断需求应该落在哪一层：

- `Wurst`
  适合游戏规则、状态流转、数值逻辑、触发行为、共享工具、compiletime 生成、可测试的程序逻辑。
- `wurst.build` 或构建脚本
  适合项目配置、构建流程、测试同步、地图元数据、打包与部署流程。
- `World Editor`
  适合更偏编辑器资产和可视化调校的工作，例如地形、装饰物摆放、区域/镜头/出生点布局、路径阻挡、手工可视资源校对，以及明显更适合在编辑器里直接调整的内容。

- 适合 `World Editor` 的工作，不要强行代码化
- 如果任务跨越代码和编辑器，先完成代码侧，再明确列出剩余手工步骤

## 修改决策规则

- 新逻辑优先放到最贴近职责的现有 package；只有当现有文件已经混杂多类职责时，才新建 package。
- 如果改动涉及多个系统，先按“配置 / 状态 / 波次 / 出怪 / 塔 / 初始化 / 测试”拆分思路，再动手。
- 如果一个文件已经明显承载过多职责，允许做小范围整理，但整理必须服务当前任务，不能顺手做大搬家。
- 涉及对象编辑器数据、技能、单位、物编定义时，优先查 compiletime 生成和现有 ID 分配模式，不要手写一批裸 ID。
- 涉及初始化顺序、 `init`、`initlater`、模块装配时，先确认依赖方向；不要用 `initlater` 掩盖本可以通过结构调整解决的问题。
- 涉及性能或大量实例的泛型容器时，优先考虑 `T:` 泛型。
- 涉及句柄、对象和闭包生命周期时，先确认是否需要 `destroy`，再决定是否抽象。

## 标准工作流

### 1. 安装依赖

首次进入仓库或依赖状态不确定时：

```bash
grill install
```

### 2. 改动前确认

- 改的是源码，不是生成物
- 知道改动应落在哪个 package / 测试位置
- 知道这次改动需要跑到哪一级验证

### 3. 常规检查

先跑：

```bash
tools\Run-WurstChecks.bat
```

失败后再窄化：

```bash
tools\Run-WurstChecks.bat typecheck
tools\Run-WurstChecks.bat test PackageOrTestName
```

- 根据文件、行号、package 名或测试名继续缩小范围
- 除非没有线索，不要反复全量重跑

### 4. 构建和部署测试图

影响地图构建、资源打包、对象生成或实际可玩性时，必须使用：

```bash
build-and-deploy-test-map.bat
```

不要自己拼零散命令替代。

## 验证矩阵

按改动类型选择最小验证：

- `.wurst` 逻辑：`tools\Run-WurstChecks.bat`
- 只改测试：`tools\Run-WurstChecks.bat`；已知测试名时优先定向重跑
- compiletime 生成、物编定义、技能/单位对象：`tools\Run-WurstChecks.bat` + `build-and-deploy-test-map.bat`
- 构建脚本、测试同步脚本、`wurst.build`、地图打包流程：`build-and-deploy-test-map.bat`
- 初始化、出怪、状态推进、塔行为等核心玩法：先跑检查；可能影响实际游玩时再跑地图构建

完成标准不是“看起来对”，而是“相关错误已修复，或未验证部分已明确说明”。

## 测试约定

- 测试源码统一放在 `tests/wurst/`
- 不要把测试源码长期留在 `wurst/_tests/`；这个目录只用于检查脚本运行时的临时 staging
- 新增测试时，优先补最靠近改动行为的 package 级测试
- 修 bug 时，优先先补一个能复现问题的窄测试，再修实现
- 测试要小、确定、可重复，不依赖手工状态或外部编辑器步骤
- 如果 quiet 输出已经给出失败测试名，先重跑该测试，不要直接扩大到全部测试

## 项目配置

`wurst.build` 是根 YAML 配置，重点关注：`projectName`、`dependencies`、`buildMapData`、`scriptMode`、`wc3Patch`。

依赖由 `grill` 管理。问题来自上游依赖时，优先修上游，不要偷改依赖拷贝。

## Lua 与 Jass

Warcraft III 地图可以运行在 Lua 或 Jass 模式。处理线程、性能和 `execute()` 前必须先确认目标。

本项目当前目标是：

```text
scriptMode: JASS
```

因此默认按 Jass 规则思考，除非用户明确要求切换或正在修改 `wurst.build`。

- Lua：基本没有实际 op-limit 压力，`execute()` 不是重置手段
- Jass：有线程 op-limit，`execute()` 用于重置 op counter，重计算可能需要拆 tick
- 未确认目标模式前，不要随意改 `execute()`、timer chunking 或防卡线程逻辑

## Wurst 基础

- 每个 `.wurst` 文件都必须放在 `package` 内
- 缩进就是语义；统一用 tab 或 4 空格，不要混用
- 默认用 `let`，只有需要可变时才用 `var`
- 优先用安全的类型推断
- 不要写 Jass 风格 `takes` / `returns nothing`
- `continue` 会跳过当前迭代，`skip` 只是 no-op

## Package 与 API 形状

- package 成员默认是 private，需要导出时再加 `public`
- class 成员默认是 public，可用 `private` / `protected` 限制
- 每个 package 默认隐式导入 `Wurst`
- `import public` 会再导出名字；普通 `import` 不会
- 除非为了打破确实无法避免的初始化环，否则不要使用 `initlater`
- package 初始化顺序是自上而下，且被导入者先初始化

命名约定：

- package / class：`UpperCamelCase`
- tuple / function / member / local：`lowerCamelCase`
- 顶层常量：`UPPER_SNAKE_CASE`

## 推荐的 Wurst 风格

- 优先使用 cascade 和 extension function 提高可读性
- 优先使用 `vec2`，避免 `location`
- 优先用建模/多态替代大段 `instanceof` / `typeId` 分发
- 除非已证明安全，否则避免无保护 `castTo`
- lambda 必须有目标类型；作为 `code` 使用时不能带参数，也不能捕获局部变量

## 类、Tuple、泛型

- `new` 出来的对象通常需要 `destroy`
- tuple 是值类型，不能 `destroy`
- `super(...)` 必须是构造器第一句
- 重写方法必须写 `override`
- 对性能敏感或实例很多的容器，优先考虑 `T:` 泛型

## Compiletime 与对象生成

对象编辑器数据优先走 compiletime 生成，优先复用 wrapper 和既有 ID 分配策略。

- 除非现有代码就是刻意这么做，否则不要手写一批新的裸对象 ID
- 改对象生成逻辑后，通常需要跑地图构建，而不仅仅是类型检查

## 格式约定

- 二元运算符两边留空格
- 调用前不加空格；`.` / `..` 两边不加空格
- 注释使用 `// Comment`
- 不要手工水平对齐
- 故意未使用的变量用 `_` 前缀

## 明确禁止

- 不要把 `_build/`、`_build/dependencies/`、`war3map.j` 当作源码去改
- 不要绕过 `tools\Run-WurstChecks.bat` 自己手动拼测试同步流程
- 不要绕过 `build-and-deploy-test-map.bat` 做“等价”的编译部署验证
- 不要在未确认脚本模式时随意引入 `execute()`、timer chunking 或线程拆分
- 不要因为赶进度而跳过相关测试；至少说明没跑什么、为什么没跑
- 不要在看不清初始化依赖关系时用 `initlater` 硬压过去
- 不要为了省事直接编辑依赖拷贝或生成产物

## 常见陷阱

- Wurst 代码必须放在 `package` 内
- 缩进就是语义
- `array.length` 只是初始长度，不是动态元素数量
- `new` 出来的对象和存储型闭包对象经常需要 `destroy`
- lambda 必须有已知目标类型
- 作为 `code` 使用的 lambda 不能捕获局部变量
- varargs 受 Jass 31 参数上限限制
- 编译器 warning 默认都应该修；只有明确知道原因时才允许保留

## 收尾标准

- 改动落在正确源码位置
- 相关检查已运行，或明确说明未运行部分
- 新增行为有测试，或说明为什么当前不适合补测试
- 影响构建、对象或玩法时，已用 `build-and-deploy-test-map.bat` 验证，或明确说明未验证原因
- 最终说明写清：改了什么、跑了什么、没跑什么、残余风险

## 编译要求

编译**必须**使用脚本：

```bash
build-and-deploy-test-map.bat
```
