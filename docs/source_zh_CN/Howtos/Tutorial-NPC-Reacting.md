# NPC 对你存在的反应

```
> north 
------------------------------------
草地
你站在一个绿色的草地上。 
这里有一个强盗。 
------------------------------------
强盗对你投以威胁的目光！
```

本教程展示了一个 NPC 对进入其位置的角色作出反应的实现。

我们需要以下内容：

- 一个当有人进入时能反应的 NPC 类型类。
- 一个可以通知 NPC 有人进入的自定义 [Room](../Components/Objects.md#rooms) 类型类。
- 我们还将略微调整我们的默认 `Character` 类型类。

```python
# 在 mygame/typeclasses/npcs.py 中（例如）

from typeclasses.characters import Character

class NPC(Character):
    """
    一个扩展了 Character 类的 NPC 类型类。
    """
    def at_char_entered(self, character, **kwargs):
        """
        一个简单的 is_aggressive 检查。
        可以在以后扩展。
        """
        if self.db.is_aggressive:
            self.execute_cmd(f"say Graaah! Die, {character}!")
        else:
            self.execute_cmd(f"say Greetings, {character}!")
```

```{sidebar} 传递额外信息
注意，我们在这里没有使用 `**kwargs` 属性。它可以用于在游戏的钩子中传递额外信息，并在制作自定义移动命令时使用。例如，如果你跑进房间，你可以通过 `obj.move_to(..., running=True)` 来通知所有钩子。也许你的图书管理员 NPC 对冲进他图书馆的人会有不同的反应！

我们确保从标准 `at_object_receive` 钩子（如下所示）传递 `**kwargs`。
```

在这里，我们在 `NPC` 上创建了一个简单的方法 `at_char_entered`。我们希望在（玩家）角色进入房间时调用它。我们实际上并没有提前设置 `is_aggressive` [属性](../Components/Attributes.md)，我们让管理员在游戏中激活它。如果没有设置，NPC 就是非敌对的。

每当 _某些东西_ 进入 `Room` 时，其 [at_object_receive](DefaultObject.at_object_receive) 钩子将被调用。因此，我们应该覆盖它。

```python
# 在 mygame/typeclasses/rooms.py 中

from evennia import utils

# ... 

class Room(ObjectParent, DefaultRoom):

    # ... 
    
    def at_object_receive(self, arriving_obj, source_location, **kwargs):
        if arriving_obj.account: 
            # 这有一个活跃的账户 - 一个玩家角色
            for item in self.contents:
                # 获取房间内所有 NPC 并通知他们
                if utils.inherits_from(item, "typeclasses.npcs.NPC"):
                    item.at_char_entered(arriving_obj, **kwargs)
```

```{sidebar} 通用对象方法
请记住，房间是 `Objects`，而其他对象也有这些相同的钩子。因此，当你捡起某物时，会触发 `at_object_receive` 钩子（使你“接收”它）。例如，将某样东西放入箱子时，也会如此。
```

当前操控的 Character 将有一个附属 `.account`。我们利用这一点来判断到达的东西是否是一个 Character。我们使用 Evennia 的 [utils.inherits_from](evennia.utils.utils.inherits_from) 辅助实用程序来获取房间内的每个 NPC，并可以调用它们新创建的 `at_char_entered` 方法。

确保执行 `reload`。

接下来，我们创建一个 NPC 并使其具有攻击性。为了举这个例子，假设你的名字是“Anna”，并且你当前的位置北边有一个房间。

```
> create/drop Orc:typeclasses.npcs.NPC
> north 
> south 
Orc says, Greetings, Anna!
```

现在让我们把兽人设置为攻击性。

```
> set orc/is_aggressive = True 
> north 
> south 
Orc says, Graah! Die, Anna!
```

这是一只容易激怒的兽人！
