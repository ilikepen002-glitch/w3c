# HTML → Y3 转换器

生成器合并到 `../generator/`，无独立 SKILL 入口。脚本、模板与配置相对位置保持不变。

从本技能目录使用：

```text
python generator/scripts/html_to_y3_ui.py input.html output.json --panel-name ManagerPanel
python generator/scripts/html_to_y3_ui.py item.html prefab.json --prefab --prefab-name ManagerItem
python gen_ui_tree.py <project-root>
```

先在临时目录转换并读回，再写入地图 `ui/`。节点树脚本默认处理 `<project-root>/maps/EntryMap/ui`，输出 `ui_tree/`；其他地图需先核对脚本路径。`--write-batch` 才会生成旧式批处理文件，常规直接调用 Python 即可。节点树只供检索，不手改代替 UI。

用 div 的 `data-type/name/x/y/w/h` 描述节点，支持 layout、label、image、button、3dmodel、grid、list。左上原点转换为 Y3 左下原点。示例：

```html
<div data-type="layout" data-name="manager" data-x="100" data-y="100" data-w="400" data-h="300">
  <div data-type="label" data-name="title" data-x="16" data-y="16" data-w="368" data-h="36" data-text="契灵管理" data-font-size="24"></div>
</div>
```

按需读 [控件模板](../generator/widget_template_config.md)、[图标配置](../generator/icon_config.md)、[适配规则](../generator/references/adapter-rules.md)。图标 ID 必须在目标工程核验。转换器不是浏览器 CSS 引擎，CSS 不会自动转换为原生布局。

Grid 使用 data-item-w/h、行列与间距，宽度应匹配 `item_w * cols + gap_x * (cols - 1)`；其余属性核对脚本。预制体只有一个根，绑定真实 key。文本、命中、遮挡、适配仍需截图/实机，不能只读生成成功消息。保留 HTML 作为源文件，不强制删除。
