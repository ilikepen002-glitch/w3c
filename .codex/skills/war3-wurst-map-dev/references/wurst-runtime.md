# Wurst 易错点与运行时诊断

只读本次修改涉及的章节；项目约束与验证要求见根目录 AGENTS.md。

## 语法与 API

- `.wurst` 必须在 `package` 内；缩进有语义，统一 tab 或 4 空格，不混用。使用 Wurst 语法，不写 Jass 的 `takes` / `returns nothing`。
- 默认 `let`，需要可变再用 `var`；优先安全的类型推断。`continue` 跳过当前迭代，`skip` 只是 no-op。
- package 成员默认 private，class 成员默认 public；按需导出。隐式导入 `Wurst`；`import public` 再导出，普通 import 不再导出。被导入包先初始化，包内按自上而下顺序初始化。
- 优先 WurstStdlib、项目 helper、cascade、extension 和 `vec2`；避免无保护 `castTo`。类型分派确有复杂度时再考虑建模/多态。
- `array.length` 是初始长度，不是实时元素数。lambda 需要目标类型；作为 `code` 时不能带参数或捕获局部变量。varargs 受 Jass 31 参数上限限制。
- `super(...)` 必须是构造器第一句，重写方法使用 `override`。
- package/class 用 `UpperCamelCase`，tuple/函数/成员/局部变量用 `lowerCamelCase`，顶层常量用 `UPPER_SNAKE_CASE`。二元运算符两侧空格，调用前及点号两侧无空格；注释用 `//`，不手工水平对齐，故意未使用的变量加 `_` 前缀。

## 生命周期

改变句柄、类、存储型闭包、timer、group 或 effect 的创建/持有/销毁时，明确清理责任，并覆盖受影响的取消、死亡、移除和正常完成路径。分配的对象通常需 `destroy`；tuple 是值，不能销毁。

## 线程与性能

- 线程/兼容性决策前确认相关配置；本项目默认值见 AGENTS.md，配置未变且已有确认结果时无需重读。
- JASS 有 op limit；`execute()` 可重置 op counter，已确认的重计算可能需拆 tick。Lua 没有相同的实际 op-limit 压力，不能把 `execute()` 当作同等重置手段。
- 未完成异步任务数不是递归深度；分别诊断调用栈、排队上限、取消与完成计数。
- 性能修改基于已定位热点、生命周期缺陷或测量，不凭猜测新增调度层。大量实例或性能敏感容器优先考虑 `T:` 泛型。
- 源码减少工作量不等于实测 FPS 提升；没有实机请求时用离线证据并说明尚未实测。
