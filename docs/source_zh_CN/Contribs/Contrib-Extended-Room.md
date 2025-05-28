# Extended Room

贡献者 - Griatch 2012, vincent-lg 2019, Griatch 2023

该功能扩展了正常的 `Room` 类型类，允许其描述根据时间、季节或其他状态（如洪水或黑暗）而变化。在描述中嵌入 `$state(burning, This place is on fire!)` 将允许根据房间状态更改描述。该房间还支持供玩家查看的 `details`（无需为每一个对象创建新的游戏内对象），并支持随机回声。该房间带有一组替代的 `look` 和 `@desc` 命令，以及新的命令 `detail`、`roomstate` 和 `time`。

## 安装

将 `ExtendedRoomCmdset` 添加到默认角色 cmdset 将添加所有新命令供使用。

更具体地说，在 `mygame/commands/default_cmdsets.py` 中：

```python
...
from evennia.contrib.grid import extended_room   # <---

class CharacterCmdset(default_cmds.CharacterCmdSet):
    ...
    def at_cmdset_creation(self):
        super().at_cmdset_creation()
        ...
        self.add(extended_room.ExtendedRoomCmdSet)  # <---
```

然后重新加载以使新命令可用。请注意，它们仅在具有 `ExtendedRoom` 类型类的房间中有效。使用正确的类型类创建新房间或使用 `typeclass` 命令切换现有房间。请注意，由于此贡献覆盖了 `look` 和 `@desc` 命令，因此您需要在 `super().at_cmdset_creation()` 之后将 `extended_room.ExtendedRoomCmdSet` 添加到默认角色 cmdset，否则它们将被默认的 look 命令覆盖。

要挖掘新的扩展房间：

```
dig myroom:evennia.contrib.grid.extended_room.ExtendedRoom = north,south
```

要使所有新房间成为 ExtendedRooms，而不必每次指定它，可以让您的 `Room` 类型类继承自 `ExtendedRoom`，然后重新加载：

```python
# 在 mygame/typeclasses/rooms.py 中

from evennia.contrib.grid.extended_room import ExtendedRoom

# ...

class Room(ObjectParent, ExtendedRoom):
    # ...
```

## 功能

### 状态依赖的描述槽

默认情况下，使用常规的 `room.db.desc` 描述。您可以通过 `room.add_desc(description, room_state=roomstate)` 或通过游戏内命令添加新的状态描述：

```
@desc/roomstate [<description>]
```

例如：

```
@desc/dark 这个房间一片漆黑。
```

这些将存储在属性 `desc_<roomstate>` 中。要设置默认回退描述，只需使用 `@desc <description>`。要在房间上激活某个状态，使用 `room.add/remove_state(*roomstate)` 或游戏内命令：

```
roomstate <state>      (再次使用以切换状态)
```

例如：

```
roomstate dark
```

有一个内置的、基于时间的状态 `season`。默认情况下，这些为 'spring'、'summer'、'autumn' 和 'winter'。`room.get_season()` 方法返回当前季节，基于游戏内时间。默认情况下，它们随 12 个月的游戏内时间安排变化。您可以通过以下方式控制它们：

```
ExtendedRoom.months_per_year      # 默认 12
ExtendedRoom.seasons_per_year      # 字典格式 {"season": (start, end), ...} 
                                      # 其中 start/end 是以整年比例给出的
```

要设置季节性描述，只需像往常一样使用 `room.add_desc` 或在游戏内用以下命令：

```
@desc/winter 这个房间充满了雪。
@desc/autumn 红色和黄色的树叶覆盖在地面上。
```

通常季节随游戏内时间变化，您也可以通过设置状态来“强制”设置某个季节：

```
roomstate winter
```

如果您像这样手动设置季节，直到您取消设置之前，它将不会再次自动变化。

您可以通过 `room.get_stateful_desc()` 获取房间的状态描述。

### 根据状态更改描述的部分

所有描述都可以嵌入 `$state(roomstate, description)` [FuncParser 标签](FuncParser) 中。以下是一个示例：

```py
room.add_desc("这是一个漂亮的海滩。 "
              "$state(empty, 它完全空无一人)"
              "$state(full, 它人满为患)。", room_state="summer")
```

这是一个带有特殊嵌入字符串的夏季描述。如果您设置房间为：

```
> room.add_room_state("summer", "empty")
> room.get_stateful_desc()
```

将得到：

```
这是一个漂亮的海滩。它完全空无一人。
```

```
> room.remove_room_state("empty")
> room.add_room_state("full")
> room.get_stateful_desc()
```

将得到：

```
这是一个漂亮的海滩。它人满为患。
```

有四个默认的时间状态，旨在与这些标签一起使用。房间会自动跟踪并更改这些状态。默认情况下，它们为 'morning'、'afternoon'、'evening' 和 'night'。您可以通过 `room.get_time_of_day` 获取当前时间段。您可以通过以下方式控制这些：

```
ExtendedRoom.hours_per_day    # 默认 24
ExtendedRoom.times_of_day      # 字典格式 {season: (start, end), ...} 
                                 # 其中 start/end 以比例形式给出
```

您可以在描述中正常使用这些：

```
"一个林间空地。 $(morning, 清晨的阳光透过树枝洒下。)"
```

### 详细信息

_详细信息_ 是在房间内查看的“虚拟”目标，而无需为每个目标创建新的数据库实例。这对于向位置添加更多信息非常有用。详细信息以字符串形式存储在字典中。

```
detail window = 有一扇窗户通往外面。
detail rock = 这块岩石上写着：“不要轻举妄动”。
```

当您在房间中时，您可以执行 `look window` 或 `look rock`，并获得匹配的详细描述。这需要新的自定义 `look` 命令。

### 随机回声

`ExtendedRoom` 支持随机回声。只需将其设置为属性列表 `room_messages`：

```python
room.room_message_rate = 120   # 秒数，0 表示禁用
room.db.room_messages = ["一辆车经过。", "听到汽车鸣笛的声音。"]
room.start_repeat_broadcast_messages()   # 也可以通过重新加载服务器来实现
```

这将开始每 120 秒随机回响到房间。

### 额外命令

- `CmdExtendedRoomLook` (`look`) - 支持房间详细信息的查看命令
- `CmdExtendedRoomDesc` (`@desc`) - 允许添加状态描述的描述命令
- `CmdExtendedRoomState` (`roomstate`) - 切换房间状态
- `CmdExtendedRoomDetail` (`detail`) - 列出及操作房间详细信息
- `CmdExtendedRoomGameTime` (`time`) - 显示房间中的当前时间和季节。


----

<small>此文档页面并非由 `evennia/contrib/grid/extended_room/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
