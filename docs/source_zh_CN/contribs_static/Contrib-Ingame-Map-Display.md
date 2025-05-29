# 基本地图

贡献者 - helpme 2022

这个模块为给定的房间添加一个 ASCII `地图`，可以通过 `map` 命令查看。您可以轻松修改它以添加特殊字符、房间颜色等。显示的地图是在使用时动态生成的，支持所有罗盘方向以及上下方向。其他方向将被忽略。

如果您不希望地图频繁更新，可以选择将计算出的地图保存为房间的 .ndb 值，并渲染该值，而不是每次都重新运行地图计算。

## 安装：

将 `MapDisplayCmdSet` 添加到默认角色命令集将添加 `map` 命令。

具体来说，在 `mygame/commands/default_cmdsets.py` 中：

```python
...
from evennia.contrib.grid.ingame_map_display import MapDisplayCmdSet   # <---

class CharacterCmdset(default_cmds.CharacterCmdSet):
    ...
    def at_cmdset_creation(self):
        ...
        self.add(MapDisplayCmdSet)  # <---

```

然后 `reload` 以使新命令可用。

## 设置：

为了更改默认地图大小，您可以在 `mygame/server/settings.py` 中添加：

```python
BASIC_MAP_SIZE = 5  # 这将更改默认地图的宽度/高度。
```

## 特性：

### ASCII 地图（evennia 支持 UTF-8 字符甚至表情符号）

这为玩家生成一个可配置大小的 ASCII 地图。

### 新命令

- `CmdMap` - 查看地图
