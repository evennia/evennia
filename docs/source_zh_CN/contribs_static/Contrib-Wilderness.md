# 荒野系统

由 titeuf87 贡献，2017年

这个贡献提供了一个荒野地图，而不需要实际创建大量房间——在你移动时，你实际上会回到同一个房间，但其描述会发生变化。这意味着你可以用较少的数据库存储创建大面积的地图，只要房间相对相似（例如，只有名称/描述变化）。

## 安装

这个贡献不提供任何新的命令。相反，默认的 `py` 命令被用来直接调用这个贡献中的函数/类。

## 使用

首先需要创建一张荒野地图。可以有不同的地图，每张地图都有自己的名称。如果未提供名称，则使用默认名称。内部，荒野是作为一个脚本存储的，名称由你指定。如果没有指定名称，将创建并使用一个名为“default”的脚本。

```python
py from evennia.contrib.grid import wilderness; wilderness.create_wilderness()
```

创建后，可以进入该荒野地图：

```python
py from evennia.contrib.grid import wilderness; wilderness.enter_wilderness(me)
```

所有使用的坐标都采用 `(x, y)` 元组格式。x 从左到右，y 从下到上。因此，`(0, 0)` 是地图的左下角。

> 你还可以通过在 GLOBAL_SCRIPT 设置中定义一个 WildernessScript 来添加荒野。如果这样做，请确保定义地图提供者。

## 自定义

虽然默认设置可以使用，但旨在进行自定义。在创建新的荒野地图时，可以提供一个“地图提供者”：这是一个足够智能的 Python 对象，用于创建地图。

默认提供者 `WildernessMapProvider` 只是创建一个无限大小的网格区域。

你可以通过子类化 `WildernessMapProvider` 来创建更有趣的地图，并自定义房间/出口类型类。

`WildernessScript` 还有一个可选的 `preserve_items` 属性，设置为 `True` 时，将不回收任何包含对象的房间。默认情况下，当房间没有玩家时，荒野房间会被回收。

此外，没有命令允许玩家进入荒野。这仍然需要添加：它可以是命令或出口，具体取决于你的需求。

## 示例

为了演示如何进行自定义，我们将创建一个非常简单（且较小）的荒野地图，其形状像个金字塔。地图将作为字符串提供：“.” 符号表示我们可以行走的位置。

让我们在 `world/pyramid.py` 中创建以下内容：

```python
# mygame/world/pyramid.py

map_str = '''
     .
    ...
   .....
  .......
'''

from evennia.contrib.grid import wilderness

class PyramidMapProvider(wilderness.WildernessMapProvider):

    def is_valid_coordinates(self, wilderness, coordinates):
        "验证这些坐标是否在地图内"
        x, y = coordinates
        try:
            lines = map_str.split("\n")
            # 反向需要，因为否则金字塔会是
            # 倒置的
            lines.reverse()
            line = lines[y]
            column = line[x]
            return column == "."
        except IndexError:
            return False

    def get_location_name(self, coordinates):
        "设置位置名称"
        x, y = coordinates
        if y == 3:
            return "金字塔顶部。"
        else:
            return "在一座金字塔内。"

    def at_prepare_room(self, coordinates, caller, room):
        "在展示之前对房间进行的任何其他更改"
        x, y = coordinates
        desc = "这是金字塔中的一间房间。"
        if y == 3:
            desc = "你可以从金字塔顶部看到远方。"
        room.ndb.active_desc = desc
```

请注意，当前活动描述存储在 `.ndb.active_desc` 中。当查看房间时，这就是将被提取并显示的内容。

> 房间的出口总是存在，但锁会隐藏那些未用于特定位置的出口。因此，请确保在使用超级用户时执行 `quell`（因为超级用户会忽略锁，否则这些出口不会被隐藏）。

现在，我们可以使用我们的新金字塔形状荒野地图。在 Evennia 中，我们创建一个新的荒野（使用名称“default”），但使用我们新的地图提供者：

```python
py from world import pyramid as p; p.wilderness.create_wilderness(mapprovider=p.PyramidMapProvider())
py from evennia.contrib.grid import wilderness; wilderness.enter_wilderness(me, coordinates=(4, 1))
```

## 实现细节

当角色进入荒野时，他们会获得自己的房间。如果他们移动，角色并不会被移动，房间将根据新的坐标进行更改。

如果角色在荒野中遇到另一个角色，他们的房间会合并。当其中一个角色再次离开时，他们各自会获得自己的房间。

房间会根据需要创建。未使用的房间会被存储，以避免未来再次创建新房间时的开销。
