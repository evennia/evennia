# 解谜系统

由 Henddher 贡献于 2018 年

该系统旨在用于冒险游戏风格的组合谜题，例如将水果和搅拌机组合以制作奶昔。它为可以组合（即一起使用）的对象提供了一个类型类和命令。与 `crafting` 贡献不同，每个谜题都是由独特的对象构建的，构建者可以完全在游戏中创建谜题。

一个 `Puzzle` 是一个配方，玩家必须组合哪些对象（即部分），以便自动创建一组新的对象（即结果）。

## 安装

将 `PuzzleSystemCmdSet` 添加到所有玩家（例如，在他们的角色类型类中）。

或者（用于快速测试）：

```python
py self.cmdset.add('evennia.contrib.game_systems.puzzles.PuzzleSystemCmdSet')
```

## 用法

考虑这个简单的谜题：

    橙子、芒果、酸奶、搅拌机 = 水果奶昔

作为构建者：

```bash
create/drop orange
create/drop mango
create/drop yogurt
create/drop blender
create/drop fruit smoothie

puzzle smoothie, orange, mango, yogurt, blender = fruit smoothie
...
Puzzle smoothie(#1234) created successfully.

destroy/force orange, mango, yogurt, blender, fruit smoothie

armpuzzle #1234
Part orange is spawned at ...
Part mango is spawned at ...
....
Puzzle smoothie(#1234) has been armed successfully
```

作为玩家：

```bash
use orange, mango, yogurt, blender
...
Genius, you blended all fruits to create a fruit smoothie!
```

## 详细信息

谜题是从现有对象创建的。给定的对象被内省以为谜题部分和结果创建原型。这些原型成为谜题配方。（参见 PuzzleRecipe 和 `puzzle` 命令）。一旦配方创建完成，所有部分和结果都可以处理（即销毁）。

稍后，构建者或脚本可以武装谜题并在其各自的位置生成所有谜题部分（参见 armpuzzle）。

普通玩家可以收集谜题部分并将其组合（参见 use 命令）。如果玩家指定了所有部分，则认为谜题已解决，所有谜题部分将被销毁，而谜题结果将在其对应位置生成。


----

<small>此文档页面并非由 `evennia/contrib/game_systems/puzzles/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
