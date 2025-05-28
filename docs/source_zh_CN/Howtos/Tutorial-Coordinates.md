# 在你的游戏中添加房间坐标

```{sidebar} XYZGrid 
另见 [XYZGrid 贡献](../Contribs/Contrib-XYZGrid.md)，它添加了坐标支持和路径查找。
```
本教程的内容难度适中。你可能需要熟悉和掌握一些 Python 概念（比如属性），以及可能的 Django 概念（比如查询），尽管本教程将尝试引导你完成过程，并在每一步提供足够的解释。如果你对数学感觉不太自信，请随时暂停，转到示例部分，查看小地图，并尝试熟悉代码或阅读解释。

Evennia 默认没有坐标系统。房间和其他对象通过位置和内容相互连接：

- 一个对象可以在一个位置，即另一个对象中。就像房间中的出口。
- 一个对象可以访问其内容。房间可以看到使用它作为位置的对象（包括出口、房间、角色等）。

这个系统提供了很大的灵活性，并且幸运的是可以通过其他系统扩展。在这里，我提供了一种方法，以便在每个房间中添加坐标，并且符合 Evennia 的设计。这也将向你展示如何使用坐标，例如查找给定点周围的房间。

## 将坐标作为标签

第一个概念可能在初看时最令人惊讶：我们将通过 [标签](../Components/Tags.md) 创建坐标。

那么，为什么不使用属性呢？这不是更简单吗？确实如此。我们可以做到像 `room.db.x = 3` 这样的事情。使用标签的优势在于搜索将变得简单有效。虽然现在这可能看起来不是一个巨大的优势，但如果你有数千个房间的数据库，可能会有所不同，特别是如果你有很多基于坐标的内容。

我将直接给你代码，而不是提供逐步的过程。注意我们使用属性轻松访问和更新坐标。这是一种 Pythonic 方法。以下是我们可以在 `typeclasses/rooms.py` 中修改的第一个 `Room` 类的代码：

```python
# 在 typeclasses/rooms.py 中

from evennia import DefaultRoom

class Room(DefaultRoom):
    """
    房间就像任何对象，除了它们的位置为 None
    （这是默认值）。它们还使用 basetype_setup() 增加锁定
    以便不能被操纵或拾起。
    （要更改此行为，请使用 at_object_creation）

    请参阅 examples/object.py 以获取所有
    对所有对象可用的属性和方法的列表。
    """
    
    @property
    def x(self):
        """返回 X 坐标或 None。"""
        x = self.tags.get(category="coordx")
        return int(x) if isinstance(x, str) else None

    @x.setter
    def x(self, x):
        """更改 X 坐标。"""
        old = self.tags.get(category="coordx")
        if old is not None:
            self.tags.remove(old, category="coordx")
        if x is not None:
            self.tags.add(str(x), category="coordx")

    @property
    def y(self):
        """返回 Y 坐标或 None。"""
        y = self.tags.get(category="coordy")
        return int(y) if isinstance(y, str) else None
    
    @y.setter
    def y(self, y):
        """更改 Y 坐标。"""
        old = self.tags.get(category="coordy")
        if old is not None:
            self.tags.remove(old, category="coordy")
        if y is not None:
            self.tags.add(str(y), category="coordy")

    @property
    def z(self):
        """返回 Z 坐标或 None。"""
        z = self.tags.get(category="coordz")
        return int(z) if isinstance(z, str) else None
    
    @z.setter
    def z(self, z):
        """更改 Z 坐标。"""
        old = self.tags.get(category="coordz")
        if old is not None:
            self.tags.remove(old, category="coordz")
        if z is not None:
            self.tags.add(str(z), category="coordz")
```

如果你不熟悉 Python 中属性的概念，建议阅读一些关于该主题的好教程。[这篇关于 Python 属性的文章](https://www.programiz.com/python-programming/property) 写得很好，应该能帮助你理解这个想法。

让我们看一下 `x` 的属性。首先是读属性。

```python
    @property
    def x(self):
        """返回 X 坐标或 None。"""
        x = self.tags.get(category="coordx")
        return int(x) if isinstance(x, str) else None
```

这个方法做的事情很简单：

1. 获取类别为 `"coordx"` 的标签。它是我们存储 X 坐标的标签类别。`tags.get` 方法如果找不到标签将返回 `None`。
2. 如果标签是 `str`，我们将值转换为整数。请记住，标签只能包含 `str`，因此我们需要进行转换。

那么标签可以包含值吗？严格来说，它们不能：它们要么存在，要么不存在。但是使用标签类别，如我们所做的，我们只需知道类别就能获取标签。这就是本教程中坐标的基本方法。

现在，让我们看看设置房间中 `x` 时将调用的方法：

```python
    @x.setter
    def x(self, x):
        """更改 X 坐标。"""
        old = self.tags.get(category="coordx")
        if old is not None:
            self.tags.remove(old, category="coordx")
        if x is not None:
            self.tags.add(str(x), category="coordx")
```

1. 首先，移除旧的 X 坐标，如果它存在。否则，我们将最终在房间中有两个标签，类别为 "coordx"，这是不可接受的。
2. 然后我们添加新的标签，并赋予适当的类别。

如果你添加了此代码并重新加载游戏，一旦你用角色登录到房间，你可以尝试以下操作：

```plaintext
py here.x
py here.x = 0
py here.y = 3
py here.z = -2
py here.z = None
```

## 一些额外的搜索

拥有坐标对于多个原因是有用的：

1. 它可以帮助在地理上塑造一个真正合乎逻辑的世界，至少在这方面。
2. 它可以允许你按给定坐标查找特定房间。
3. 它可以帮助你快速找到位置周围的房间。
4. 它甚至可以用于路径查找（找到两个房间之间的最短路径）。

到目前为止，我们的坐标系统可以帮助完成第 1 点，但其他方面就不太行了。以下是我们可以向 `Room` 类型类添加的一些方法。这些方法将只是搜索方法。请注意，它们是类方法，因为我们希望获取房间。

### 查找一个房间

首先是一个简单的：如何找到给定坐标的房间？假设，X=0、Y=0、Z=0 处的房间是什么？

```python
class Room(DefaultRoom):
    # ...
    @classmethod
    def get_room_at(cls, x, y, z):
        """
        返回给定位置的房间，如果未找到则返回 None。

        参数：
            x (int): X 坐标。
            y (int): Y 坐标。
            z (int): Z 坐标。

        返回：
            该位置的房间（Room），如果未找到则为 None。
        """
        rooms = cls.objects.filter(
                db_tags__db_key=str(x), db_tags__db_category="coordx").filter(
                db_tags__db_key=str(y), db_tags__db_category="coordy").filter(
                db_tags__db_key=str(z), db_tags__db_category="coordz")
        if rooms:
            return rooms[0]

        return None
```

这个解决方案包含一些 [Django 查询](Basic-Tutorial-Django-queries)。基本上，我们做的是访问对象管理器并搜索带有匹配标签的对象。同样，别花太多时间担心机制，这个方法使用起来非常简单：

```plaintext
Room.get_room_at(5, 2, -3)
```

请注意，这是一个类方法：你将从 `Room`（类）调用它，而不是从实例调用。尽管你仍然可以：

```plaintext
py here.get_room_at(3, 8, 0)
```

### 查找多个房间

这是另一个有用的方法，允许我们查找给定坐标周围的房间。这是更高级的搜索，并且需要一些计算，小心一点！如果你感到困惑，请查看如下部分。

```python
from math import sqrt

class Room(DefaultRoom):

    # ...

    @classmethod
    def get_rooms_around(cls, x, y, z, distance):
        """
        返回给定坐标周围的房间列表。

        此方法返回一个包含 (距离, 房间) 元组的列表，
        该列表可以轻松浏览。此列表按距离排序（
        距离指定位置最近的房间始终位于列表顶部）。

        参数：
            x (int): X 坐标。
            y (int): Y 坐标。
            z (int): Z 坐标。
            distance (int): 到指定位置的最大距离。

        返回：
            包含距离指定位置的距离和该距离处房间的元组的列表。
            多个房间可能与位置相距相同。
        """
        # 快速搜索，仅获取房间在一个正方形内
        x_r = list(reversed([str(x - i) for i in range(0, distance + 1)]))
        x_r += [str(x + i) for i in range(1, distance + 1)]
        y_r = list(reversed([str(y - i) for i in range(0, distance + 1)]))
        y_r += [str(y + i) for i in range(1, distance + 1)]
        z_r = list(reversed([str(z - i) for i in range(0, distance + 1)]))
        z_r += [str(z + i) for i in range(1, distance + 1)]
        wide = cls.objects.filter(
                db_tags__db_key__in=x_r, db_tags__db_category="coordx").filter(
                db_tags__db_key__in=y_r, db_tags__db_category="coordy").filter(
                db_tags__db_key__in=z_r, db_tags__db_category="coordz")

        # 现在我们需要过滤这个列表，以找出这些房间是否真的足够接近，以及距离有多远
        # 简而言之：我们将正方形变成一个圆圈。
        rooms = []
        for room in wide:
            x2 = int(room.tags.get(category="coordx"))
            y2 = int(room.tags.get(category="coordy"))
            z2 = int(room.tags.get(category="coordz"))
            distance_to_room = sqrt(
                    (x2 - x) ** 2 + (y2 - y) ** 2 + (z2 - z) ** 2)
            if distance_to_room <= distance:
                rooms.append((distance_to_room, room))

        # 最后按距离对房间进行排序
        rooms.sort(key=lambda tup: tup[0])
        return rooms
```

这就更复杂了。

1. 我们将坐标作为参数。我们使用距离确定一个宽阔的范围。换句话说，对于每个坐标，我们创建一个可能匹配的列表。请查看下面的示例。
2. 然后我们搜索该更广泛范围内的房间。它会在位置周围给我们一个正方形。有些房间肯定在范围外。同样，请查看下面的示例以理解逻辑。
3. 我们过滤该列表，并按距离对其进行排序。

请注意，我们仅在步骤 2 开始搜索。因此，Django 搜索不会查找和缓存所有对象，只会查找比实际必要更广泛的范围。此方法返回点周围的圆形坐标。Django 寻找的是正方形。不适合圆形的部分在步骤 3 中被删除，而这只是包含系统计算的唯一部分。此方法经过优化，快速且高效。

### 示例

一个例子可能会有所帮助。考虑这个非常简单的地图（以下是文本描述）：

```
4 A B C D
3 E F G H
2 I J K L
1 M N O P
  1 2 3 4
```

X 坐标在下面给出。Y 坐标在左侧给出。这是一个简单的正方形，共有 16 个房间：每行 4 个，共 4 行。所有房间在这个示例中由字母标识：顶部第一行有房间 A 到 D，第二行有 E 到 H，第三行有 I 到 L，第四行有 M 到 P。左下角房间 X=1 和 Y=1 是 M。右上角房间 X=4 和 Y=4 是 D。
假设我们想查找房间 J 的所有邻居，距离 1。J 的坐标是 X=2，Y=2。

所以我们可以使用：

```python
Room.get_rooms_around(x=2, y=2, z=0, distance=1)
# 为了简单起见，我们假设 Z 坐标为 0
```

1. 首先，该方法会获取 J 周围的正方形房间。所以它将获取 E、F、G、I、J、K、M、N、O。
2. 接下来，我们浏览这个列表，检查 J（X=2，Y=2）和每个房间之间的实际距离。正方形的四个角并不在这个圆圈内。例如，J 和 M 之间的距离不是 1。如果你画出中心为 J、半径为 1 的圆，你会发现我们正方形的四个角（E、G、M 和 O）不在这条圆圈内。因此，我们将它们删除。
3. 我们按距离从 J 的距离进行排序。

最后，我们可能会得到如下结果：

```python
[
    (0, J), # 是的，J 也在这个圆圈内，距离为 0
    (1, F),
    (1, I),
    (1, K),
    (1, N),
]
```

你可以尝试更多示例，看看这个功能如何运作。

## 总结

你也可以使用此系统来映射其他对象，而不仅仅是房间。如果你只需要 `X` 和 `Y`，你可以轻松地移除 `Z` 坐标。
