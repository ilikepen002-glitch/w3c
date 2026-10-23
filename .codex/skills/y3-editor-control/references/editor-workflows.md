# 按工作类型操作

## UI 与管理面板

精灵、背包和塔管理优先用独立原生 UI、网格列表和可复用元件。UI 保存选择/展开等显示状态，费用、奖励、装备归属由同步业务层校验。不能让本地屏幕或选中状态直接决定全局游戏结果。

Y3 UI 原点与锚点不能套用网页坐标。新适配模式以高度 1080 为基准，宽度随比例变化；核对父控件、锚点、拉伸/等比模式。元件只有一个根，改模板时注意实例覆盖。检查长中文、窄屏、遮挡及鼠标事件拦截。

文件修改后热更新 UI，读回层级并截图；截图工具可能切换当前层和缩放，先保存现场。编辑器静态预览不能显示所有 Lua 动态创建内容，也不能证明运行时点击成功。真正交互核验需按按钮后观察业务状态与日志。

## 物编、模型与资源

- 先查询已有对象和 ID，再新增/导入。资源 ID、物编 ID、实例 ID 不是同一件事；相同 ID 的导入可能覆盖对象。
- 资源涉及 OriginalRes 原始资源、CustomImportRepo.local 缓存及 editor_table 元数据；仅有源图或源模型不代表编辑器已导入。使用官方导入工具，核对实际 ID、元数据和渲染结果。
- 官方下载调用的“已提交”仅是请求接收；检查下载日志与本地记录再引用。大型资源清单保存后筛选，不反复向会话倾倒全库。
- 资源清理不能完整识别 Lua 引用，不按编辑器“未引用”结果批量删除。不要用删除缓存作为常规修复。
- 模型检查比例、朝向、挂点及所需动画。Warcraft 模型转换工具存在不代表所有 MDX/BLP 和原生行为可直接复用。
- 技能配置的伤害数字不自动证明实际结算链已接通。原生建造的扣费/返还与 Lua 账本只能有一个明确责任方。
- 对象池只重置有限字段。自定义 KV、计时器、特效和事件订阅须核对回收责任，防止复用后残留。

## 地形、场景与表现

先核对地图边界和单位，再编辑坐标。点/区域/路径、地形格、植被格的坐标表示不可混用；先用一个可回读的小样确认转换。缩小地图会删除越界对象及路径，之后放大不能自动恢复。

战斗可读性先于装饰密度：道路、塔位、入口、出口、Boss 预警要明确。优先复用原生投射物、运动器、跳字和动画；为特效设寿命和数量上限。灯光、泛光和高密度植被必须用实际帧时间评估，静态截图不能验证性能。

## Lua 调试与多人

先查静态诊断，再查当次运行日志；不要用旧版本 SPIRIT_READY 证明新文件已加载。使用 execute_lua 时先读取状态，指定实际 clientSlot。向一个客户端直接修改同步资源/单位可能导致不同步；业务操作走项目同步入口。

主入口加载与游戏初始化事件分开。重新开局清理订阅、计时器、表现实体及本地 UI 状态；多人退出、重进或玩家槽为空时不访问旧对象。LuaTracy 与 ECA 火焰图针对不同执行层，选择能测到瓶颈的工具。

## 表格与云脚本（需要时再用）

表格导入先核对 config_ / kv_ 表结构，数值和多级键类型；公式应提供计算后的值。云脚本根目录 cloud_script/main.lua 与地图 script/main.lua 分开，meta 仅用于类型提示。

云回调身份与服务端鉴权为准，role_id、plat_aid 与本地玩家槽不要混用。显式比较返回码；0 在 Lua 中为真。存档读取 nil 或 JSON 解析失败不能静默重置为新档；接受请求、持久化完成和奖励送达要区分。教程列出的 Redis 封装不能推断支持完整事务。

## 官方出处

- [UI 定位与适配](https://163.com/y3/docs/guides/FunctionManual/UI_Editor/Positioning_and_Adaptation)
- [网格列表](https://163.com/y3/docs/guides/FunctionManual/UI_Editor/Grid)
- [自定义资源](https://163.com/y3/docs/guides/FunctionManual/Manage_Resources/Introduce)
- [资源文件](https://163.com/y3/docs/guides/FunctionManual/Manage_Resources/ResourceFile)
- [对象池](https://163.com/y3/docs/guides/FunctionManual/Object_Editor/ObjectPool)
- [建造系统](https://163.com/y3/docs/guides/FunctionManual/SystemFunction/BuildingFunction)
- [不同步](https://163.com/y3/docs/guides/CommonProblem/Asynchronous)
- [云脚本](https://163.com/y3/docs/guides/FunctionManual/CloudScript)
