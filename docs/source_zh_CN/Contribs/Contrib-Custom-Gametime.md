# 自定义游戏时间

由 vlgeoff 贡献（2017）- 基于 Griatch 的核心原始实现

这个模块重写了 `evennia.utils.gametime`，但使用了一个 _自定义_ 日历（每周/月/年等的天数不寻常）以适应您的游戏世界。与原始模块一样，它允许安排在指定的游戏时间发生的事件，但现在考虑到这个自定义日历。

## 安装

以与正常的 `evennia.utils.gametime` 模块相同的方式导入和使用它。

通过向您的设置中添加 `TIME_UNITS` 字典来定制日历（见下面的示例）。

## 用法：

```python
from evennia.contrib.base_systems import custom_gametime

gametime = custom_gametime.realtime_to_gametime(days=23)

# 安排一个事件每游戏 10 小时触发一次
custom_gametime.schedule(callback, repeat=True, hour=10)
```

日历可以通过在设置文件中添加 `TIME_UNITS` 字典来定制。这个字典将单位名称映射到它们的长度，以最小单位表示。以下是一个默认示例：

```python
TIME_UNITS = {
    "sec": 1,
    "min": 60,
    "hr": 60 * 60,
    "hour": 60 * 60,
    "day": 60 * 60 * 24,
    "week": 60 * 60 * 24 * 7,
    "month": 60 * 60 * 24 * 7 * 4,
    "yr": 60 * 60 * 24 * 7 * 4 * 12,
    "year": 60 * 60 * 24 * 7 * 4 * 12,
}
```

使用自定义日历时，这些时间单位名称作为参数传递给该模块中的转换函数。即使您的日历使用其他名称表示月份/星期等，系统在内部仍然需要默认名称。


----

<small>此文档页面并非由 `evennia/contrib/base_systems/custom_gametime/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
