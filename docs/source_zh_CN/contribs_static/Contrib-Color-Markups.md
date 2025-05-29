# 附加颜色标记

由 Griatch 贡献，2017年

为 Evennia 提供额外的颜色标记样式（扩展或替换默认的 `|r`, `|234`）。添加对 MUSH 风格 (`%cr`, `%c123`) 和/或 传统 Evennia (`{r`, `{123`) 的支持。

## 安装

将所需的样式变量从此模块导入到 `mygame/server/conf/settings.py`，并将其添加到以下设置变量中。每个变量都指定为一个列表，可以为每个变量添加多个这样的列表以支持多种格式。请注意，列表顺序会影响应用的正则表达式优先级。您必须重新启动 Portal 和 Server 才能更新颜色标签。

将以下设置变量分配（参见下面的示例）：

- `COLOR_ANSI_EXTRA_MAP` - 正则表达式与 ANSI 颜色之间的映射
- `COLOR_XTERM256_EXTRA_FG` - 定义 XTERM256 前景色的正则表达式
- `COLOR_XTERM256_EXTRA_BG` - 定义 XTERM256 背景色的正则表达式
- `COLOR_XTERM256_EXTRA_GFG` - 定义 XTERM256 灰度前景色的正则表达式
- `COLOR_XTERM256_EXTRA_GBG` - 定义 XTERM256 灰度背景色的正则表达式
- `COLOR_ANSI_BRIGHT_BG_EXTRA_MAP` - ANSI 不支持明亮背景；我们通过将 ANSI 标记映射到匹配的明亮 XTERM256 背景来“伪造”这种效果

- `COLOR_NO_DEFAULT` - 设置为 True/False。如果为 False（默认），则扩展默认标记；否则完全替换它。

## 示例

要添加 `{` - "大括号" 风格，请在设置文件中添加以下内容，然后重启 Server 和 Portal：

```python
from evennia.contrib.base_systems import color_markups

COLOR_ANSI_EXTRA_MAP = color_markups.CURLY_COLOR_ANSI_EXTRA_MAP
COLOR_XTERM256_EXTRA_FG = color_markups.CURLY_COLOR_XTERM256_EXTRA_FG
COLOR_XTERM256_EXTRA_BG = color_markups.CURLY_COLOR_XTERM256_EXTRA_BG
COLOR_XTERM256_EXTRA_GFG = color_markups.CURLY_COLOR_XTERM256_EXTRA_GFG
COLOR_XTERM256_EXTRA_GBG = color_markups.CURLY_COLOR_XTERM256_EXTRA_GBG
COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP = color_markups.CURLY_COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP
```

要添加 `%c-` "mux/mush" 风格，请在设置文件中添加以下内容，然后重启 Server 和 Portal：

```python
from evennia.contrib.base_systems import color_markups

COLOR_ANSI_EXTRA_MAP = color_markups.MUX_COLOR_ANSI_EXTRA_MAP
COLOR_XTERM256_EXTRA_FG = color_markups.MUX_COLOR_XTERM256_EXTRA_FG
COLOR_XTERM256_EXTRA_BG = color_markups.MUX_COLOR_XTERM256_EXTRA_BG
COLOR_XTERM256_EXTRA_GFG = color_markups.MUX_COLOR_XTERM256_EXTRA_GFG
COLOR_XTERM256_EXTRA_GBG = color_markups.MUX_COLOR_XTERM256_EXTRA_GBG
COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP = color_markups.MUX_COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP
```
