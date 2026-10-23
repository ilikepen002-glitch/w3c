# Y3 官方技能的 Codex 适配记录

日期：2026-10-24（本地）。上游：[y3-editor/y3-maker-config](https://github.com/y3-editor/y3-maker-config)，固定提交 `b9253889d74f07145bb2bd56721f8dfc406c263c`。原始来源校验值见 [manifest](upstream-sources/manifest.json)。原始 6 篇入口保存在 `upstream-sources/*.original.md` 与 `upstream-sources/y3-lua-review/original.md`，是历史对照资料，不是自动加载指令。

## 选择与安装范围

启用四个官方适配入口：

| 技能 | 复用内容 | 本地适配 |
| --- | --- | --- |
| [y3-obj-edit](skills/y3-obj-edit/SKILL.md) | 物编脚本、11 个数据模板、5 篇参数参考 | 精简入口；允许核对真实 JSON；保留 ID/tuple/语言哈希约束 |
| [y3-ui-pipeline](skills/y3-ui-pipeline/SKILL.md) | HTML 转 UI、13 个控件模板、图标配置、节点树 | generator 合并为内部目录，无重复发现入口；现有运行时 UI 可继续使用 |
| [y3-lua-pipeline](skills/y3-lua-pipeline/SKILL.md) | API/UI 专题参考 | review 合并为内部参考；真实源码优先，移除机械 API 替换和入口目录猜测 |
| [y3-resource-import](skills/y3-resource-import/SKILL.md) | 导入方法、格式检查脚本 | 当前工具 schema 优先；异步完成用证据确认，不强制每步问人 |

官方 35 篇知识资料在 [knowledge/INDEX.md](knowledge/INDEX.md)，按任务取用，不注入每次上下文。不导入上游整套 rules、memory、模型配置或专属工具绑定；只保留 [技术边界](rules/y3-technical.md)。项目专用开发/连接技能由项目规则管理，和这四条技术能力入口分工。

没有修改全局 Codex 配置，没有启动编辑器/游戏，没有对正式地图运行物编修改、UI 转换或资源导入。

## 修改明细

- 四篇 SKILL 改为标准 name/description，加入 `agents/openai.yaml`；没有 CodeMaker 专属发现规则。
- `y3-ui-generator` 移入 UI pipeline 的 `generator/`，其 SKILL 原文归档；`y3-lua-review` 原文归档并改写成 Lua pipeline 的内部 review 参考。
- 物编参数参考及知识资料中的 `.codemaker/`、`.y3maker/` 路径改成 `.codex/`；知识正文作为参考保留，旧流程不覆盖本地入口。
- 物编脚本的配置目录变量由 `CODEMAKER_DIR` 改名 `AGENT_CONFIG_DIR`；相对路径计算与字段处理保持原逻辑。
- 节点树脚本新增正常 `--help`，旧批处理生成改为显式 `--write-batch`；修正旧批处理的 `%1%` 参数写法。默认运行只输出节点树。
- TGA 排查脚本移除上游作者个人电脑默认路径，要求显式传入存在的资源目录。
- 上游 `test_scale.py` 与转换器 stack 结构不同步，测试输入由 2 项改为 3 项，并让缺模板/越界真正失败。未修改模板或转换算法来掩盖失败。
- 运行环境 `D:/Y3Projects/tooling/python` 安装 `mmh3 5.3.1`、`PyYAML 6.0.3`；物编脚本依赖前者，技能验证依赖后者。实际依赖锁定应由项目依赖文件维护。

## 已完成的验证

- 四条入口均通过 skill-creator `quick_validate.py`。
- 物编与 HTML 转换器 `--help` 可执行。
- 隔离临时目录创建单位、修改生命值、读回 ID/数值及语言哈希条目通过，未触碰正式地图。
- 隔离 HTML 转面板、转单根 prefab、生成两份节点树通过；默认未产生旧批处理文件。
- 四个技能内 Python 文件语法检查通过；技能 Markdown 本地相对链接检查通过。

## 已知限制与未验证

上游 card 模板 0.5 倍缩放测试报告 **15 处子节点越界**。部分位置可能是模板刻意装饰/动态列表布局，也可能是真实缺陷；尚未实机判定。不能把此模板当作已验证可用的成品，更不能宣称全部官方模板测试通过。实际使用 card 前按目标 UI 检查；当前项目界面不依赖该模板。本次仅证明简单面板/预制体生成通路。

未进行编辑器加载、热更、导入完成、游戏交互或多人同步验证。本地素材格式检查不是引擎导入验证；官方参考中的 API 仍需对照当前项目 lualib。

## 后续升级

先更新独立上游检出并对照固定提交/manifest，定向合并脚本或参考变化；保留这里的四入口结构和项目约束，不能直接用上游入口覆盖适配。新脚本行为在临时目录验证，涉及引擎时另做实际验证。
