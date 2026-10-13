# 本地合并验证（2026-10-12）

合并分支：`codex/archer-split-arrow-shots`。本地提交 `92d2b369d64ba838f5d12d3b60a2c6931b0b9bdb`，远端提交 `009dae4dc2a27382477ff1ea624c6fd6a91b5a19`。唯一冲突为根目录 `ExampleMap.w3x`，暂取远端地图解决冲突后，使用合并源码重新构建。此次验证未修改玩法源码、正式验证器或断言，未启动游戏。

## 命令与结果

所有命令工作目录均为 `D:/War3Projects/MyFirstWurstMap`。

- `cmd /c tools\Run-WurstChecks.bat`：退出码 0，`Typecheck succeeded`、`All tests succeeded`。测试源码有 363 个 `@Test` 声明；quiet 输出未逐条列出执行数。未输出 Wurst warning。
- `cmd /c "build-and-deploy-test-map.bat < NUL"`：退出码 0，构建、标题修补、部署成功；地图名称和加载标题均为 `深渊守望 2204`。javac 提示 `PatchMapDisplayName.java` 使用过时 API，无编译错误。
- `python tools/VerifyTrialArtifact.py ExampleMap.w3x --output _build/merge-trial-artifact-result.json`：首次在 Windows 默认 GBK 环境因读取 UTF-8 源码失败（`UnicodeDecodeError`）。`PYTHONIOENCODING=utf-8` 仅设置标准输入输出，不能修复 `Path.read_text()` 的默认编码。
- `python -X utf8 tools/VerifyTrialArtifact.py ExampleMap.w3x --output _build/merge-trial-artifact-result.json`：退出码 0、PASS。未提供目标安装归档，原生模型/攻击类型安装验证仍为 `NOT_VERIFIED`。
- `python tools/VerifyTrialReplay.py ExampleMap.w3x --output _build/merge-trial-replay-result.json`：原始正式命令退出码 1，`Real trial score could not credit`。下述诊断解释此限制，不能将原始命令记为 PASS。
- 通过 `git show 009dae4:ExampleMap.w3x` 将远端原图写入 `_build/remote-009dae4.w3x`，执行 `python -X utf8 tools/VerifyTrialReplay.py _build/remote-009dae4.w3x --output _build/merge-remote-trial-replay-result.json`：退出码 0、完整 PASS。

## 三份地图一致性

以下文件 SHA256 均为 `C0DD7D485619979FA7E42C082552255983F1120A2B6B82FC5B5BE30C15A917E9`：

- `_build/MyFirstWurstMap.w3x.w3x`
- `ExampleMap.w3x`
- `D:/War3_1.27a/Warcraft III Frozen Throne 1.27a publish/Maps/Test/深渊守望.w3x`

## 原始 Replay 失败的定位与可重复诊断

同环境下，本地图与远端图的 ticket 均为 1，owner、token、generation、lane、slot、identity、revision、consumed、preLife 和 score 初态一致。相同 `min_2_1(123.0, 1000000.0)` 在本地图离线 runtime 返回 0、远端返回 123。

原因是离线 runtime 未执行标准库 `init_Real`，只扫描简单数值赋值。本地编译器输出 `set Real_REAL_MAX = 16777215. * 1073741824. * 1073741824. * 1073741824. * 16384.`，该表达式未被扫描器恢复，`Real_REAL_MAX` 留为 0。远端编译器输出单个数字字面量，扫描器恢复为约 `3.40282366920938e38`。这是离线解释器初始化覆盖限制，不是本次已证实的玩法回归。

当前构建 `_build/02_compiled.j.txt` 中，`init_Real` 位于 29962 行，乘法赋值位于 29963 行。`main` 于 30954 行注册 `init_Real`、30955 行调用 `TriggerEvaluate`，早于试炼规则（31219）、身份（31229）、运行时（31349）与 Hook（31354）初始化。真实产物初始化顺序包含该标准库初始化。

以下为实际使用的临时诊断脚本，在仓库根目录通过 `python -X utf8 -` 执行。它只追加执行实际 JASS 的 `init_Real`，不硬写常量、不替换得分逻辑、不修改正式验证器或断言，然后运行相同完整 `verify_replay`。退出码 0、PASS；结果存入 `_build/merge-trial-replay-init-real-diagnostic.json`，日志为同名 `.log`。这些 `_build` 文件是本地临时证据，本节代码可用于重现。

```python
import sys, json
from pathlib import Path
sys.path.insert(0, 'tools')
import VerifyTrialReplay as v

script = v.Mpq(Path('ExampleMap.w3x').read_bytes()).extract('war3map.j').decode()
original = v.TrialJassRuntime.__init__

def diagnostic_init(self, script):
    original(self, script)
    self.invoke('init_Real')

v.TrialJassRuntime.__init__ = diagnostic_init
try:
    result = v.verify_replay(script)
    Path('_build/merge-trial-replay-init-real-diagnostic.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('status=', result['status'])
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

## 审查与边界

本次为高风险构建/合并整合验证。GPT-6.1 Sol 执行验证与只读定位，GPT-6 Astra 审查结论为 **PASS WITH NOTES**。备注：正式 Replay 对当前本地编译输出不能直接通过，需披露上述离线初始化限制；完整临时诊断 PASS 不替代原始命令结果。未执行 Warcraft III 实机验证，原生单位、计时、渲染及 FPS 仍处于离线模型边界。
