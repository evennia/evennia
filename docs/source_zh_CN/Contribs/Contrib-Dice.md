# Dice Roller

由 Griatch 贡献，2012, 2023

一个骰子滚动器，可以处理任意数量和面数的骰子。支持游戏内骰子掷骰（例如 `roll 2d10 + 1`），以及条件掷骰（低于/高于/等于目标）和用于代码中掷骰的函数。命令还支持隐藏或秘密掷骰，以供人类游戏主持人使用。

## 安装

将此模块中的 `CmdDice` 命令添加到角色的命令集中（然后重启服务器）：

```python
# 在 mygame/commands/default_cmdsets.py 中

# ...
from evennia.contrib.rpg import dice  <---

class CharacterCmdSet(default_cmds.CharacterCmdSet):
    # ...
    def at_cmdset_creation(self):
        # ...
        self.add(dice.CmdDice())  # <---
```

## 用法

    > roll 1d100 + 2
    > roll 1d20
    > roll 1d20 - 4

掷骰结果将反馈到房间。

你还可以指定标准 Python 运算符，以指定最终目标数字，并以公平和无偏见的方式获得结果。例如：

    > roll 2d6 + 2 < 8

这样掷骰将通知所有参与者结果是否确实低于 8。

    > roll/hidden 1d100

通知房间正在掷骰，而不透露结果。

    > roll/secret 1d20

这是一个隐藏的掷骰，不会通知房间它发生了。

## 从代码中掷骰

你可以将第一个参数指定为标准 RPG dice 语法（NdM 的字符串，其中 N 是掷骰的数量，M 是骰子的面数）：

```python
from evennia.contrib.rpg.dice import roll

roll("3d10 + 2")
```

你也可以提供条件（这时会返回 `True`/`False`）：

```python
roll("2d6 - 1 >= 10")
```

如果你将第一个参数指定为整数，则将被解释为掷骰的数量，然后可以更明确地构建掷骰。这在你将掷骰器与其他系统一起使用并希望从组件构建掷骰时会很有用。

```python
roll(dice, dicetype=6, modifier=None, conditional=None, return_tuple=False,
      max_dicenum=10, max_dicetype=1000)
```

以下是如何使用显式语法掷骰 `3d10 + 2`：

```python
roll(3, 10, modifier=("+", 2))
```

以下是如何掷骰 `2d6 - 1 >= 10`（将返回 `True`/`False`）：

```python
roll(2, 6, modifier=("-", 1), conditional=(">=", 10))
```

### 骰子池和其他变体

你一次只能掷一组骰子。如果你的 RPG 要求你以更复杂的方式掷多个骰子并将它们组合在一起，可以通过多个 `roll()` 调用来实现。根据你的需求，你也许想将其表达为特定于你游戏的辅助函数。

以下是如何掷 D&D 优势掷骰（掷两次 d20，选择最高的）：

```python
from evennia.contrib.rpg.dice import roll

def roll_d20_with_advantage():
    """获取两个 d20 掷骰中的最大结果"""
    return max(roll("d20"), roll("d20"))
```

以下是一个 Free-League 风格骰子池的示例，你掷一堆 d6，并想知道你获得了多少个 1 和 6：

```python
from evennia.contrib.rpg.dice import roll

def roll_dice_pool(poolsize):
    """返回 (number_of_ones, number_of_sixes)"""
    results = [roll("1d6") for _ in range(poolsize)]
    return results.count(1), results.count(6)
```

### 获取所有滚动细节

如果你需要单独的掷骰结果（例如，对于骰子池），请设置 `return_tuple` 关键字参数：

```python
roll("3d10 > 10", return_tuple=True)
(13, True, 3, (3, 4, 6))  # (结果, 结果, 差异, 掷骰结果)
```

返回的是一个元组 `(result, outcome, diff, rolls)`，其中 `result` 是掷骰的结果，`outcome` 是如果给定条件则为 `True/False`（否则为 `None`），`diff` 是条件与结果之间的绝对差（否则为 `None`），`rolls` 是一个包含单独掷骰结果的元组。


----

<small>此文档页面并非由 `evennia/contrib/rpg/dice/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
