# 给对象添加重量

游戏中你可以接触到的所有物品通常都有一定的重量。重量的作用因游戏而异。通常，它限制你能携带多少东西。如果一块重石头掉在你身上，可能会比气球更疼。如果你想要更复杂的效果，压力板可能只有在踩上去的东西足够重时才会触发。

```python
# 在 mygame/typeclasses/objects.py 中

from evennia import DefaultObject 
from evennia import AttributeProperty 

class ObjectParent: 

    weight = AttributeProperty(default=1, autocreate=False)

    @property 
    def total_weight(self):
        return self.weight + sum(obj.total_weight for obj in self.contents) 


class Object(ObjectParent, DefaultObject):
    # ...
```

```{sidebar} 为什么不用质量？
是的，我们知道重量随着重力变化。“质量”更科学正确。但“质量”在 RPG 中不常用，所以我们在这里使用“重量”。只需知道，如果你的科幻角色可以在月球（地球重力的1/6）度假，你应该考虑到处使用 `mass`，并动态计算当前重量。
```

- **第6行**：我们使用 `ObjectParent` 混入类。由于此混入类用于 `Characters`、`Exits` 和 `Rooms` 以及 `Object`，这意味着所有这些都会自动拥有重量！
- **第8行**：我们使用 [AttributeProperty](../Components/Attributes.md#using-attributeproperty) 来设置“默认”重量为1（无论那是什么）。设置 `autocreate=False` 意味着在重量实际从默认的1更改之前，不会创建任何实际的 `Attribute`。请参阅 `AttributeProperty` 文档以了解其注意事项。
- **第10和11行**：在 `total_weight` 上使用 `@property` 装饰器意味着我们以后可以调用 `obj.total_weight` 而不是 `obj.total_weight()`。
- **第12行**：我们通过遍历 `self.contents` 来汇总所有“在”此对象中的物品的重量。由于现在 _所有_ 对象都有重量，这应该始终有效！

让我们检查一下几个可靠的箱子的重量：

```
> create/drop box1
> py self.search("box1").weight
1 
> py self.search("box1").total_weight
1 
``` 

让我们把另一个箱子放到第一个箱子里。

```
> create/drop box2 
> py self.search("box2").total_weight
1 
> py self.search("box2").location = self.search("box1")
> py self.search("box1").total_weight 
2
```

## 限制携带的重量

要限制你能携带的重量，你首先需要知道自己的力量。

```python
# 在 mygame/typeclasses/characters.py 中

from evennia import AttributeProperty

# ...

class Character(ObjectParent, DefaultCharacter): 

    carrying_capacity = AttributeProperty(10, autocreate=False)

    @property
    def carried_weight(self):
        return self.total_weight - self.weight
```

在这里，我们确保添加另一个 `AttributeProperty` 来告诉我们能携带多少。在实际游戏中，这可能基于角色的力量。当我们考虑已经携带的重量时，不应包括 _我们自己的_ 重量，所以我们减去它。

为了遵守这个限制，我们需要重写默认的 `get` 命令。

```{sidebar} 重写默认命令

在这个例子中，我们实现了 `CmdGet` 的开头，然后在结尾调用完整的 `CmdGet()`。这不是很高效，因为父类 `CmdGet` 将再次执行 `caller.search()`。为了更高效，你可能希望将 `CmdGet` 代码的全部内容复制到你自己的版本中并进行修改。
```

```python
# 在 mygame/commands/command.py 中

# ... 
from evennia import default_cmds 

# ...

class WeightAwareCmdGet(default_cmds.CmdGet):

    def func(self):
        caller = self.caller 
        if not self.args: 
            caller.msg("Get what?")
            return 

        obj = caller.search(self.args)

        if (obj.weight + caller.carried_weight 
                > caller.carrying_capacity):
            caller.msg("You can't carry that much!")
            return 
        super().func()
```

在这里，我们为尝试拾取的物品的重量添加了额外的检查，然后使用 `super().func()` 调用正常的 `CmdGet`。
