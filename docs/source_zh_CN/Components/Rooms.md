# 房间

**继承树：**

```
┌─────────────┐
│DefaultObject│
└─────▲───────┘
      │
┌─────┴─────┐
│DefaultRoom│
└─────▲─────┘
      │       ┌────────────┐
      │ ┌─────►ObjectParent│
      │ │     └────────────┘
    ┌─┴─┴┐
    │Room│
    └────┘
```

[房间](evennia.objects.objects.DefaultRoom) 是游戏内的 [对象](./Objects.md)，代表所有其他对象的根容器。

从技术上讲，将房间与任何其他对象区分开来的唯一因素是它们没有自己的 `location`，而且默认命令如 `dig` 会创建此类的对象——因此，如果你想通过更多功能扩展房间，只需继承自 `evennia.DefaultRoom`。

要更改 `dig`、`tunnel` 和其他默认命令创建的默认房间，请在设置中更改：

```python
BASE_ROOM_TYPECLASS = "typeclasses.rooms.Room"
```

`mygame/typeclasses/rooms.py` 中的空类是一个很好的起点！

虽然默认房间非常简单，但有几个 Evennia [贡献](../Contribs/Contribs-Overview.md) 定制和扩展了房间的更多功能。
