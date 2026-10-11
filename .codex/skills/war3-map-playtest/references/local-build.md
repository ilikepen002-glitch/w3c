# 本机与构建（按需读取）

以下路径和行为来自 2026-10-08 实机验证。优先复用；路径失效再定位。游戏实际版本 `1.27.0.52240`，项目配置由 `wurst.build` 决定，不因版本数字不一致擅自改配置。

| 用途 | 路径 |
| --- | --- |
| 项目 | `D:\War3Projects\MyFirstWurstMap` |
| 检查 | 项目内 `tools\Run-WurstChecks.bat` |
| 编译部署 | 项目内 `build-and-deploy-test-map.bat` |
| Test 目录 | `D:\War3_1.27a\Warcraft III Frozen Throne 1.27a publish\Maps\Test` |
| 部署地图 | Test 内 `深渊守望.w3x` |
| 启动器 | `D:\War3_1.27a\Warcraft III Frozen Throne 1.27a publish\Frozen Throne.exe` |
| 编辑器 | 游戏目录内 `World Editor.exe`，普通试玩无需启动 |
| JDK 17 | `E:\jdk17\bin\java.exe`、`javac.exe` |

首次或环境变化时，可合并只读预检：git 状态、java/javac/grill 定位及版本、目标文件存在性。`PatchMapDisplayName.java` 依赖 class version 61；“61.0，应为 52.0”表示调用 Java 8 javac，先检查 JDK 17 并重试，不先重装。安装/迁移工具链时遵守用户不新增在 C 盘的要求；`E:\WurstToolchain\.wurst` 曾复制但未接入，目录存在不证明项目使用它。

旧局或编辑器可能锁住部署地图，退到结算或局域网也可能仍持锁。当前授权包含退出该测试时，直接强制关闭对应整个 `war3.exe` 并确认结束，再部署重启；只处理本次测试使用的 War3，不连带关闭编辑器或其他程序。拒绝访问时按 [UI 恢复](ui-recovery.md) 退出。

用户要求旧测试图直接删除，不备份。先列出并确认 Test 内属于本项目的具体文件（例如 `深渊守望*.w3x`、历史 `MyFirstWurstMap.w3x.w3x`）；只删除这些明确绝对路径，保留本次目标，不删除无关图或项目源图。通配名称只是候选识别线索，不能替代所属核实。递归操作前核实最终目标范围。

在项目根使用现有入口：

```powershell
& .\tools\Run-WurstChecks.bat
if ($LASTEXITCODE -ne 0) { throw 'Wurst checks failed; do not build.' }
# 等待检查任务全部结束后才执行；两者共享测试 staging。
cmd /c "build-and-deploy-test-map.bat <NUL"
```

`<NUL` 仅防脚本末尾 pause 阻塞。核对退出码和脚本各阶段结果，不改写构建逻辑。输出可能为 `_build\MyFirstWurstMap.w3x.w3x`，不要凭扩展名改名。记录实际输出所指源文件、部署文件及 SHA256 一致性和显示标题 HHmm 标记。

用户指定拉取后的根目录 `ExampleMap.w3x` 时，它是已打包地图：核对本次提交与哈希后直接部署；编辑器模板是 `maps/ExampleMap.source.w3x`，后续构建仍走唯一入口。

同名列表项只看行号/排序不可靠，须看右侧详细标题。HHmm 可重复；歧义时退出地图浏览，结合本次构建输出、文件时间和哈希识别候选，删除已确认旧项目图后刷新。不从后来磁盘覆盖反推已经加载的运行版本。
