# 出口

**继承树：**

```
┌─────────────┐
│DefaultObject│
└─────▲───────┘
      │
┌─────┴─────┐
│DefaultExit│
└─────▲─────┘
      │       ┌────────────┐
      │ ┌─────►ObjectParent│
      │ │     └────────────┘
    ┌─┴─┴┐
    │Exit│
    └────┘
```

*出口* 是游戏中的 [Objects](./Objects.md)，用于连接其他对象（通常是 [Rooms](./Rooms.md)）。

> 注意，出口是单向对象，因此为了使两个房间双向连接，需要有两个出口。

一个名为 `north` 或 `in` 的对象可能是出口，也可能是 `door`、`portal` 或 `jump out the window`。

出口有两个与其他对象不同的地方：
1. 它们的 `.destination` 属性被设置并指向一个有效的目标位置。这使得在数据库中定位出口变得简单快速。
2. 出口在创建时会在自身上定义一个特殊的 [Transit Command](./Commands.md)。这个命令与出口对象同名，当被调用时，会处理将角色移动到出口 `.destination` 的实际操作——这让你只需输入出口的名字即可移动，就像你期望的那样。

默认的出口功能全部定义在 [DefaultExit](DefaultExit) 类型类中。原则上，你可以通过重写它来完全改变游戏中出口的工作方式——不过不推荐这样做，除非你非常清楚自己在做什么。

出口使用一种名为 *traverse* 的 `access_type` 来 [锁定](./Locks.md)，并利用一些挂钩方法来提供反馈，如果穿越失败。更多信息请参见 `evennia.DefaultExit`。

出口通常是按个案重写的，但如果你想改变房间创建的默认出口，比如 `dig`、`tunnel` 或 `open`，可以在设置中更改：

```python
BASE_EXIT_TYPECLASS = "typeclasses.exits.Exit"
```

在 `mygame/typeclasses/exits.py` 中，有一个空的 `Exit` 类供你修改。

### 出口详情

穿越出口的过程如下：

1. 穿越的 `obj` 发送一个与出口对象上的出口命令名称匹配的命令。[cmdhandler](./Commands.md) 检测到这一点，并触发在出口上定义的命令。穿越总是涉及“源”（当前位置）和 `destination`（存储在出口对象上）。
2. 出口命令检查出口对象上的 `traverse` 锁。
3. 出口命令在出口对象上触发 `at_traverse(obj, destination)`。
4. 在 `at_traverse` 中，触发 `object.move_to(destination)`。这依次触发以下挂钩：
    1. `obj.at_pre_move(destination)` - 如果返回 False，移动将被中止。
    2. `origin.at_pre_leave(obj, destination)`
    3. `obj.announce_move_from(destination)`
    4. 通过将 `obj.location` 从源位置更改为 `destination` 来执行移动。
    5. `obj.announce_move_to(source)`
    6. `destination.at_object_receive(obj, source)`
    7. `obj.at_post_move(source)`
5. 在出口对象上，触发 `at_post_traverse(obj, source)`。

如果移动因任何原因失败，出口将查找自身上的 `err_traverse` 属性并将其显示为错误消息。如果找不到此属性，出口将改为调用自身上的 `at_failed_traverse(obj)`。

### 在代码中创建出口

有关如何以编程方式创建出口的示例，请参见 [此指南](../Howtos/Beginner-Tutorial/Part1/Beginner-Tutorial-Creating-Things.md#linking-exits-and-rooms-in-code)。
