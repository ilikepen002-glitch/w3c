# 金币试炼独立模块：实际 Wurst 检查

2026-10-12 11:34 UTC。实施 GPT-6.1 Sol，仍基于正式 `654771baa872241cf572b16a0ef884436fe4818c`，不含 Boss 在途源码，也不含未来 40 件装备改版。

## 结论

- 完整 typecheck 成功。
- 真实测试 `370/370` 通过，其中试炼 `23/23`（规则 10、状态 13）。日志存在逐项 Running 与 OK，而非只看 launcher 退出。
- 最终检查 wrapper 退出 0；Trial 新增源码 warning 为 0。
- 15 项 Python 静态/资产测试复跑通过。
- 未完整构图、未打包新地图、未生产接线、未推送、未实机。本结论不能替代 W3U/MPQ 实物核验或实际伤害/计时/回收验证。

## 准确入口与证据

使用项目已批准的 Linux 事务包装入口实现 Run-WurstChecks 的串行检查流程，未自拼 staging、未编辑 wrapper 或依赖：

`python3 /workspace/scratch/2106c0ab1fac/toolchain-recovery-20261012/cloud_wrapper.py checks --repo /workspace/scratch/2106c0ab1fac/damage-trial-implementation-20261012/worktree --verbose`

wrapper SHA256：`de59b76c08788f7241b7c5a2cf6c1ef6641ea214c0999491a4baed82e20bf9f6`。

实际三次事务：

1. `transaction-b187a9e86be0493fa2476deb8e9eef6f`：typecheck 成功，测试369/370。唯一失败 `trialDamageCapsOverkillAndRejectsCorruptRanges`。
2. `transaction-42c27155ef334a01aa41202e1ad808a7`：用统一 wrapper 的 test 模式及 `--filter trialDamageCapsOverkillAndRejectsCorruptRanges --verbose` 定向复跑，1/1通过。
3. `transaction-a16b4d8e4c334c0c94906562d853bb1f`：最终完整 checks，typecheck 与370/370全部通过，退出0。

原始日志在工具链 state 对应事务中；可持久交接副本位于 worktree 同级 `trial-static-delivery/wurst-evidence/`。包含各事务 journal.json、存在的 result.json、typecheck.log、test.log，以及 checks-summary.json、warning-sites.json。launcher 日志为 trial-static-delivery 中 wurst-checks-first/targeted/final.log。完整交付清单另含各文件 SHA。

## 仅两处 Wurst 修正

- `tests/wurst/TDTrialRulesTests.wurst`：`1e9 + 1` 在单精度中会舍入到 `1e9`，并非真实越界输入。改为可表示且明确超出边界的 `1000001024.0`，保留范围拒绝断言。该修改不放宽规则。
- `wurst/trial/TDTrialObjectGen.wurst`：显式 `import Annotations`，使 @compiletime 解析到库中的正式 annotation，清除该新增 warning。保留 compiletime 对象生成，没有删注解或修改 stdlib。

修复小 diff 为同级交付目录 `wurst-check-fixes.patch`。没有改状态生命周期或扩展运行时。

## Warning 按 site 归并

最终 typecheck 原始396条 warning，按 `(文件:行, 内容)` 归并为210项，全部来自未修改的654源码；Trial为0。

- 176项显式 toString 冗余
- 9项既有 compiletime 注解解析 warning
- 24项未使用/可移除 import
- 1项既有局部赋值未读取

`warning-sites.json` 保留每个site、消息与重复次数。不顺手清理本任务以外的旧警告。

## 恢复与源码边界

三次 journal 均 `status=restored`，受管理 files/moves/stage 全部 restored，child=null；最终 active.json 不存在。原 wurst.build 与 .vscode/settings.json 的字节再次与HEAD核对一致，wurst/_tests、临时 wurst/war3map.j 和 wurst.dependencies均不存在。

Grill install 按 wrapper 设计留存 ignored `_build/dependencies/WurstStdlib2-source` 缓存目录，已验证 clean、内容树 `90b45617eda50c15703e8cb2ec3241d3c7b61816`。它不是源码改动，也不是残留临时link；不纳入 staged patch。原 tracked pre1.29 依赖由事务恢复，未手改生成物或共享依赖。

## 仍需后续门禁

Astra实际实现预审由父任务安排。本次 typecheck/纯状态测试通过，不代表 Hook、单位、装备资格、路线、生命保护或 HUD 已接入地图。正式集成需重新串行检查、唯一构图入口、当前产物验证与Astra实际审查。

静态合法单段估算仍只适用于654源码与明确的原生表前提。最终1.28类型表未核验；未来装备重做、新塔、百分比/生命伤害或cap变化必须重算，不能声称已兼容装备新版或已证明任意攻击不死。
