# AGENTS.md - WurstScript 地图项目协作说明

适用于本项目中与 `.wurst` 代码、测试、编译脚本、对象生成、依赖和地图构建相关的工作。

目标是让代理和协作者在这个仓库里：

- 更快找到正确入口
- 更稳定地改对地方
- 用统一方式验证结果
- 避免破坏构建、测试和地图部署流程

## 默认双 Agent 协作模式

本仓库默认采用“双 Agent”工作流：

- 开发者：Codex（负责实现、测试、修复、整理交付）
- 审查者：Gemini CLI（负责方案审查和代码审查）

默认流程：

1. Codex 接收需求并完成本地实现
2. Codex 运行本次改动所需的最小验证
3. Codex 调用 Gemini 审查本次方案或代码改动
4. 如果 Gemini 未通过，Codex 必须先修复再重新送审
5. 只有 Gemini 明确通过，或用户明确要求“本次跳过审查”，才允许进入最终交付或提交阶段

显式跳过审查规则：

- 只有当用户明确说出“跳过 Gemini”“这次不审查”“skip review”或同等含义时，才允许跳过 Gemini 审查
- “默认工作方式”优先于效率偏好；不要因为任务小就自动省略审查
- 如果 Gemini CLI 不可用、鉴权失败、代理异常或审查命令执行失败，默认视为“审查未完成”，必须如实报告
- 在 Gemini 不可用的情况下，只有用户再次明确同意“无审查交付”，才允许继续按跳过审查处理

## Agent 角色

### DevAgent（Codex）

职责：

- 负责需求拆解、Wurst 代码实现、测试补充、验证执行和最终交付
- 按本文件既有架构边界，把改动落在正确源码位置
- 在需要时调用 Gemini 审查，并根据审查意见继续修复
- 不得声称“已经过 Gemini 审查”，除非 Gemini 命令实际执行成功并返回了结果

### ReviewAgent（Gemini CLI）

职责：

- 只读审查，不直接修改仓库源码
- 审查技术方案、改动 diff、测试覆盖和风险点
- 对 Wurst 地图项目优先检查以下问题：
  - 游戏规则或状态推进是否可能回归
  - 初始化顺序、`init`/import 依赖是否存在隐患
  - compiletime 物编生成、rawcode、升级链、技能挂载是否一致
  - 核心玩法改动是否缺少最小验证
  - 是否误改生成物、测试 staging 目录或构建产物
- 输出必须包含明确结论：`PASS`、`PASS WITH NOTES` 或 `FAIL`

## Gemini 调用要求

调用 Gemini 时必须自动带代理配置。

Windows CMD 形式：

```cmd
set HTTP_PROXY=http://127.0.0.1:7890 && set HTTPS_PROXY=http://127.0.0.1:7890 && gemini
```

PowerShell 形式：

```powershell
$env:HTTP_PROXY = "http://127.0.0.1:7890"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"
gemini
```

本仓库统一入口脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\Invoke-GeminiReview.ps1 -Task "本次改动说明"
```

除非当前任务明确要求手工拼装 Gemini 命令，否则优先使用上面的脚本，不要每次临时重写一套调用参数。

## 默认审查门禁

以下动作默认要求先经过 Gemini 审查，除非用户明确跳过：

- 任何需要“完成交付”的代码改动
- 任何请求提交 commit、整理提交信息、准备 PR 的改动
- 任何影响核心玩法、初始化、波次、出怪、塔行为、物编生成、升级链或构建流程的改动

如果当前任务只是在做探索、定位问题、起草方案或验证猜想，可以先不送审；但一旦进入“准备交付改动”的阶段，默认必须送审。

## 审查输出约定

Gemini 审查结果在最终说明里至少要交代：

- 是否已实际调用 Gemini
- Gemini 的结论是 `PASS`、`PASS WITH NOTES` 还是 `FAIL`
- 如果未调用或调用失败，具体阻塞原因是什么
- 如果用户要求跳过审查，需要明确写出“按用户要求跳过 Gemini 审查”

## 示例工作流指令

适合本项目的示例：

```text
给某个塔系新增一个主动技能，补最小测试，跑 Wurst 检查，然后让 Gemini 审查这次改动。
```

跳过审查示例：

```text
修复这个 Wurst 类型错误，跑检查，这次跳过 Gemini 审查。
```

## 验证命令

验证脚本存在且能生成审查提示：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\Invoke-GeminiReview.ps1 -Task "验证 Gemini 审查脚本" -DryRun
```

验证 Gemini CLI 本体是否可被代理方式调用：

```powershell
$env:HTTP_PROXY = "http://127.0.0.1:7890"; $env:HTTPS_PROXY = "http://127.0.0.1:7890"; gemini --help
```

验证一次真实 Gemini 审查调用：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\Invoke-GeminiReview.ps1 -Task "验证 Gemini 审查链路"
```

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

除非用户明确要求修改这些设定，否则默认按当前项目现实处理：

- `wurst.build` 当前 `scriptMode: JASS`
- `wc3Patch: v1.28`
- 构建产物由 `grill build ExampleMap.w3x --quiet` 生成到 `_build/`
- 测试源码放在 `tests/wurst/`
- 检查脚本运行时会临时同步测试到 `wurst/_tests/`，结束后清理
- 最终编译和部署测试图必须走 `build-and-deploy-test-map.bat`

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

当前源码已经按“系统入口 + 塔子域拆分 + 测试独立目录”落地，后续改动默认遵守下面的边界：

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

塔系统子目录位于 `wurst/towers/`，当前职责如下：

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

测试结构约定：

- `tests/wurst/`
  测试源码真相目录。所有 `*Tests.wurst` 默认放这里。
- `wurst/_tests/`
  仅供 `tools/Run-WurstChecks.bat` 临时 staging 使用；不要手工维护，也不要把这里当作正式源码目录。

当前塔结构的演进方向是：

- 先保持 `TDTowers -> TDTowerData/TDTowerRuntime/TDTowerObjectGen` 这层稳定边界
- 当某个塔族出现明显独立的主动技能、状态机或专属复杂逻辑时，再进一步拆成按塔族分文件
- 在没有明确收益前，不要为了“每塔一个文件”而把共享平衡表、升级链和 compiletime 生成拆碎

## 实现归属边界

不是所有需求都应该用 Wurst 实现。开始实现前，先判断这件事更适合落在哪一层：

- `Wurst`
  适合游戏规则、状态流转、数值逻辑、触发行为、共享工具、compiletime 生成、可测试的程序逻辑。
- `wurst.build` 或构建脚本
  适合项目配置、构建流程、测试同步、地图元数据、打包与部署流程。
- `World Editor`
  适合更偏编辑器资产和可视化调校的工作，例如地形、装饰物摆放、区域/镜头/出生点布局、路径阻挡、手工可视资源校对，以及明显更适合在编辑器里直接调整的内容。

如果一个需求本质上更适合在 `World Editor` 完成：

- 不要为了“全部代码化”而强行用 Wurst 绕路实现
- 不要用脆弱脚本去替代本应由编辑器直接维护的可视化内容
- 应明确反馈给操作者：哪些部分应在 `World Editor` 中处理、为什么更适合在那里处理、需要操作者执行哪些具体步骤

如果需求同时跨越代码和编辑器边界：

- 先完成适合代码侧的部分
- 明确列出剩余需要在 `World Editor` 中手工完成的事项
- 在最终说明里把“已完成的代码改动”和“仍需操作者在编辑器中完成的步骤”分开写清楚

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

### 2. 改动前确认上下文

至少确认下面三件事：

- 你改的是源码，不是生成物
- 你知道改动对应的 package 和测试落点
- 你知道这次改动需要哪一级验证

### 3. Wurst 改动后的常规检查

先跑安静检查：

```bash
tools\Run-WurstChecks.bat
```

如果安静检查失败，再窄化重跑：

```bash
tools\Run-WurstChecks.bat typecheck
tools\Run-WurstChecks.bat test PackageOrTestName
```

根据失败信息里的文件、行号、package 名或测试名继续收缩范围。除非没有足够线索，否则不要反复全量 noisy 重跑。

### 4. 构建和部署测试图

凡是会影响地图构建、地图资源打包、对象生成、实际可玩性验证，必须使用：

```bash
build-and-deploy-test-map.bat
```

不要自己拼接一组零散命令替代它。

## 验证矩阵

按改动类型选择最小验证动作：

- 只改 `.wurst` 逻辑：
  先跑 `tools\Run-WurstChecks.bat`
- 只改测试：
  先跑 `tools\Run-WurstChecks.bat`
  如果知道具体测试名，优先再跑 `tools\Run-WurstChecks.bat test PackageOrTestName`
- 改 compiletime 生成、物编定义、技能/单位对象：
  跑 `tools\Run-WurstChecks.bat`
  然后跑 `build-and-deploy-test-map.bat`
- 改构建脚本、测试同步脚本、`wurst.build`、地图打包流程：
  必须跑 `build-and-deploy-test-map.bat`
- 改初始化、出怪、状态推进、塔行为等核心玩法：
  跑 `tools\Run-WurstChecks.bat`
  若改动可能影响实际游玩流程，再跑 `build-and-deploy-test-map.bat`

完成标准不是“代码看起来对”，而是“相关错误/警告已修复，或无法验证的部分已明确说明”。

## 测试约定

- 测试源码统一放在 `tests/wurst/`
- 不要把测试源码长期留在 `wurst/_tests/`；这个目录只用于检查脚本运行时的临时 staging
- 新增测试时，优先补最靠近改动行为的 package 级测试
- 修 bug 时，优先先补一个能复现问题的窄测试，再修实现
- 测试要小、确定、可重复，不依赖手工状态或外部编辑器步骤
- 如果 quiet 输出已经给出失败测试名，先重跑该测试，不要直接扩大到全部测试

示例：

```wurst
package MyTests
import Wurstunit

@Test public function multiplicationWorks()
	12.assertEquals(3 * 4)
```

## 项目配置

`wurst.build` 是根 YAML 配置。重点字段：

- `projectName`
- `dependencies`
- `buildMapData`
- `scriptMode`
- `wc3Patch`

依赖由 `grill` 管理。默认依赖通常是 `wurstStdlib2`。如果问题来自上游依赖，优先考虑修上游或提出上游补丁，不要在复制出来的依赖内容里偷偷改。

## Lua 与 Jass

Warcraft III 地图可以运行在 Lua 或 Jass 模式。处理线程、性能和 `execute()` 前必须先确认目标。

本项目当前目标是：

```text
scriptMode: JASS
```

因此默认按 Jass 规则思考，除非用户明确要求切换或正在修改 `wurst.build`。

### Lua 模式

- 基本没有实际 op-limit 压力
- `execute()` 为性能上的空操作，不要把它当作重置 op-limit 的手段
- 只有真的需要异步延迟时才使用 timer

### Jass 模式

- 每个线程有操作数限制
- `execute()` 通过启动新线程来重置 op counter
- 重计算可能需要拆分到多个 tick

不要在未确认目标模式前，随意添加或删除 `execute()`、timer chunking 或“防卡线程”逻辑。

## Wurst 基础

每个 `.wurst` 文件都必须在 package 中：

```wurst
package MyPackage
import Wurstunit

init
	print("loaded")
```

Wurst 使用缩进定义代码块。统一使用 tab 或 4 个空格，不要混用。

常见声明：

```wurst
let immutable = 5
var mutable = 10
constant int SOME_ID = 'A000'
int array values = [1, 2, 3]

function max(int a, int b) returns int
	if a > b
		return a
	return b

function doThing()
	print("void functions omit returns")
```

- 非必要不使用 `var`
- 局部变量尽量靠近第一次使用
- 优先使用明显且安全的类型推断
- 不要写 Jass 风格的 `takes` / `returns nothing`

控制流：

```wurst
if x > y
	...
else if x < y
	...

switch kind
	case 1
		...
	default
		...

while keepGoing
	...

for i = 0 to 10
	...

for i = 10 downto 0
	...

for u in group
	...

for u from group
	...
```

- `continue` 会跳过当前迭代
- `skip` 只是 no-op
- 语句通常在换行结束

常见运算符：

```wurst
+  -  *  /  div  %  mod
and  or  not
==  !=  <  <=  >  >=
```

```wurst
let label = count == 1 ? "unit" : "units"
```

## Package 与 API 形状

- package 成员默认是 private，需要导出时再加 `public`
- class 成员默认是 public，可用 `private` / `protected` 限制
- 每个 package 默认隐式导入 `Wurst`
- `import public` 会再导出名字；普通 `import` 不会
- 除非为了打破确实无法避免的初始化环，否则不要使用 `initlater`
- package 初始化顺序是自上而下，且被导入者先初始化

命名约定：

- package / class：`UpperCamelCase`
- tuple：`lowerCamelCase`
- function / member / local：`lowerCamelCase`
- 顶层常量：`UPPER_SNAKE_CASE`

## 推荐的 Wurst 风格

优先使用 cascade 语法组织 setup：

```wurst
CreateTrigger()
	..registerAnyUnitEvent(EVENT_PLAYER_UNIT_ISSUED_ORDER)
	..addCondition(Condition(function cond))
	..addAction(function action)
```

优先使用 extension function 提升可读性：

```wurst
public function unit.getX2() returns real
	return GetUnitX(this)
```

其他建议：

- 优先使用 `vec2` tuple，而不是 `location` 句柄，除非底层 API 强制要求
- 优先用建模和多态替代大段 `instanceof` / `typeId` 分发
- 除非已经证明安全，否则避免无保护的 `castTo`

Lambda 规则：

```wurst
Predicate<int> even = x -> x mod 2 == 0

doAfter(1.) ->
	print("later")
```

- lambda 必须有目标类型
- 单独写一个 lambda 不能自动推断
- 闭包按值捕获局部变量
- 被存储的闭包或对象背后的闭包通常需要清理
- 当 lambda 被当作 `code` 使用时，不能带参数，也不能捕获局部变量

## 类、Tuple、泛型

- `new` 出来的对象通常需要 `destroy`
- tuple 是值类型，不能 `destroy`

```wurst
class Missile
	function onCollide(unit u)

class Fireball extends Missile
	override function onCollide(unit u)
		...
```

- `super(...)` 必须是构造器第一句
- 重写方法必须写 `override`

接口和模块：

```wurst
interface Listener
	function onClick()

module HasOwner
	player owner

class Button
	use HasOwner
```

对性能敏感或实例很多的容器，优先考虑：

```wurst
class Box<T:>
	T value
```

旧式 `T` 泛型会通过整数转换擦除类型，且可能共享存储。

## Compiletime 与对象生成

对象编辑器数据优先走 compiletime 生成。优先使用 wrapper 和 ID 生成策略，确保 ID 稳定、可追踪、避免冲突。

```wurst
let value = compiletime(fac(5))

@compiletime function createSpell()
	new AbilityDefinitionMountainKingThunderBolt(SPELL_ID)
		..setName("Wurst Bolt")
		..presetDamage(lvl -> 400. + lvl * 100.)
```

- 除非现有代码就是刻意这么做，否则不要手写一串新的裸对象 ID
- 改对象生成逻辑后，通常需要跑地图构建，而不仅仅是类型检查

## 格式约定

- 二元运算符两边留空格：`a + b`
- 调用前不加空格：`foo(1)`
- `.` 和 `..` 两边不加空格
- `(`、`[` 后不加空格；`)`、`]` 前不加空格
- 注释使用 `// Comment`
- 不要手工水平对齐
- 故意未使用的变量用 `_` 前缀

Hot doc 注释：

```wurst
/** This appears in autocomplete. */
```

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

任务完成时，代理应尽量满足以下条件：

- 改动已经落在正确源码位置
- 相关检查已经运行，或明确说明未运行的部分
- 新增行为有对应测试，或说明为什么当前不适合补测试
- 如果改动影响构建/对象/玩法，已经使用 `build-and-deploy-test-map.bat` 验证，或明确说明未验证原因
- 最终说明里清楚写出：
  - 改了什么
  - 跑了什么
  - 没跑什么
  - 是否还有残余风险

## 编译要求

编译**必须**使用脚本：

```bash
build-and-deploy-test-map.bat
```
