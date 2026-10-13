# 旧版 JASS 数组容量核查

本文保留 `ce64984` 基线诊断结果。后续修复和验证见 [2026-10-13 解决记录](../solutions/2026-10-13-旧版JASS数组边界与热点优化.md)。

## 结论

已快进拉取 `28f1668 -> ce64984`。云端反馈的兼容缺口成立，但属于此前地图已有的编译器产物问题，不能归因于本次装备整合，也不能据此认定开局必然崩溃。

当前地图暂不能视为已通过 Warcraft III 1.27a 的数组边界兼容验证。本次仅诊断，没有修复编译器、修改生成脚本或重新部署地图。

## 实际证据

- 本地编译器：`1.9.0.0-nightly-2-g82c1bd294`，与云端发布说明一致。
- 当前 `ExampleMap.w3x` SHA256：`00844e0a7272c7c37f5e19804895cb6980dfff7cf3a7bfcf92cb957da94811ed`，与发布说明一致。
- 直接解包当前地图的 `war3map.j`：129 个 `alloc_*` 函数使用 `< 32768`；所有 32768 命中均位于这些对象分配函数。
- 从 Git 直接读取 `28f1668:ExampleMap.w3x` 后解包：上一版也有 100 个这样的分配函数。
- 本机 `D:/War3_1.27a/Warcraft III Frozen Throne 1.27a publish` 的 `War3Patch.mpq`、`Patch127.mpq`、`patch.mpq` 中，`Scripts/common.j` 均定义 `JASS_MAX_ARRAY_SIZE = 8192`。
- 项目配置仍是 `scriptMode: JASS`、`wc3Patch: v1.28`；本地 `_build/common.j` 也定义 8192。
- `javap -constants de.peeeq.wurstscript.utils.Constants` 确认安装的编译器 JAR 内 `MAX_ARRAY_SIZE = 32768`。

当前地图脚本第 3380 行起，`alloc_LLEntry` 的关键逻辑如下（节选，仅用于说明）：

```jass
if LLEntry_maxIndex < 32768 then
    set LLEntry_maxIndex = LLEntry_maxIndex + 1
    set this_2 = LLEntry_maxIndex
    set LLEntry_typeId[this_2] = 742
```

8192 个数组槽位的有效下标是 0..8191。当该对象池没有空闲槽位、且最大下标已经为 8191 时，现有分配器仍会尝试写入下标 8192。对象销毁后可复用槽位，所以风险不能简单等同于“一局累计创建了 8192 个单位”；链表节点、闭包等 Wurst 对象也需要分别考虑所属对象池。

此处还说明：机械地把比较常量从 32768 替换为 8192 并不完整，因为代码先比较、再自增，仍会放行下标 8192。

## 配置选项核查

已检查本地 `-help` 和对应版本的 `RunArgs.java`。没有发现调整数组容量的公开命令行选项。`-legacyJassChecks` 只为 pre-1.24 的 JASS 返回类型不匹配放宽检查，并跳过 PJass；不改变对象分配器容量。项目已使用旧版 common.j，现有产物足以证明仅设置旧补丁版本没有约束该分配器。

上游对应版本源码：

- [Constants.java：硬编码容量](https://github.com/wurstscript/WurstScript/blob/82c1bd294/de.peeeq.wurstscript/src/main/java/de/peeeq/wurstscript/utils/Constants.java)
- [RunArgs.java：可用选项与 legacyJassChecks](https://github.com/wurstscript/WurstScript/blob/82c1bd294/de.peeeq.wurstscript/src/main/java/de/peeeq/wurstscript/RunArgs.java)

## 修复方向

优先修编译器源码，使 JASS 数组容量和分配边界服从目标版本，并锁定经过验证的工具链。需要覆盖最后合法下标、首次越界分配、销毁后复用，以及其他使用数组容量的编译器路径。若选择回退工具链，也必须先验证该版本的实际生成结果，不能仅凭版本更旧推定兼容。

后续修复完成后，应在发布前检查实际 MPQ 中的脚本，并通过项目规定的检查和构建入口重新验证。不要直接批量替换成品 `war3map.j` 中的数字。

## 本次验证与边界

- `git pull --ff-only`：成功，无冲突。
- `tools\Run-WurstChecks.bat`：退出码 0，输出 `Typecheck succeeded`、`All tests succeeded`。quiet 模式未输出数量；451 项是云端发布说明的数据，不冒称本次输出了该数量。
- 对当前图、上一版图、安装编译器及本机游戏 MPQ 的检查均为只读。
- 没有运行 `build-and-deploy-test-map.bat`：本次未修改构建或玩法，直接检查了已发布图；原编译器仍有已确认缺口，未重新生成并部署同类风险产物。
- 没有启动游戏；实际对象池峰值、触发越界后的引擎表现及装备实机行为未验证。
- 风险层级：普通诊断与验证文档；由当前 GPT-6 主代理完成，未启动 Astra/Sol 子代理。本记录不代表编译器修复或兼容审查通过。
