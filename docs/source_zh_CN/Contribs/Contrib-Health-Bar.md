# 血条

由 Tim Ashley Jenkins 贡献于 2017 年

此模块提供的函数让您可以轻松地将视觉条或计量器显示为彩色条，而不仅仅是一个数字。"血条" 只是其中最明显的用途，但该条高度可定制，可以用于除玩家健康外的任何适当数据。

现代玩家可能更习惯于看到诸如健康、耐力、魔法等统计数据以条形显示，而不是仅仅展示数值，因此使用此模块以这种方式呈现数据可能会使其更易于访问。然而，请记住，玩家也可能使用屏幕阅读器连接到您的游戏，而屏幕阅读器无法以任何方式表示条的颜色。默认情况下，表示的数值会以文本形式显示在条内，可以被屏幕阅读器读取。

## 用法

无需安装，只需从此模块导入并使用 `display_meter`：

```python
    from evennia.contrib.rpg.health_bar import display_meter

    # 健康值为 23/100
    health_bar = display_meter(23, 100)
    caller.msg(prompt=health_bar)
```

血条将考虑当前值高于最大值或低于 0 的情况，将其呈现为完全满或空的条，并在其中显示数值。
```


----

<small>此文档页面并非由 `evennia/contrib/rpg/health_bar/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
