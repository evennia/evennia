# Crafting System

由 Griatch 贡献，2020年

这个实现了一个完整的制作系统。其原则是“配方”，你将被标记为原料的物品组合以创造新的物品。该配方还可以要求某些（不被消耗的）工具。例如，使用“面包配方”将“面粉”、“水”和“酵母”与“烤箱”组合以烘焙“面包”。

配方过程可以理解为：

```
原料 + 工具 + 配方 -> 物品
```

这里，“原料”会在制作过程中被消耗，而“工具”是过程所需的，但不会被破坏。

包含的 `craft` 命令如下所示：

```
craft <recipe> [from <ingredient>,...] [using <tool>, ...]
```

## 示例

使用 `craft` 命令：

```
craft toy car from plank, wooden wheels, nails using saw, hammer
```

配方不必使用工具或多个原料：

```
snow + snowball_recipe -> snowball
```

反过来，你也可以想象使用工具而没有消耗品，比如：

```
spell_book + wand + fireball_recipe -> fireball
```

该系统足够通用，还可以用于冒险类谜题（但需要更改命令，以根据正在组合的内容确定配方）：

```
stick + string + hook -> makeshift_fishing_rod
makeshift_fishing_rod + storm_drain -> key
```

有关如何为制作剑设计配方树的示例，请参见 [剑的示例](evennia.contrib.game_systems.crafting.example_recipes)。

## 安装和使用

从 `evennia/contrib/crafting/crafting.py` 导入 `CmdCraft` 命令，并将其添加到你的角色命令集中。重新加载后，`craft` 命令将可用：

```
craft <recipe> [from <ingredient>,...] [using <tool>, ...]
```

在代码中，你可以使用 `evennia.contrib.game_systems.crafting.craft` 函数进行制作：

```python
from evennia.contrib.game_systems.crafting import craft

result = craft(caller, "recipename", *inputs)
```

这里，`caller` 是进行制作的人，`*inputs` 是任何组合的消耗品和/或工具对象。系统将根据其 [标签](../Components/Tags.md) 识别它们。`result` 总是一个列表。

要使用制作，你需要配方。在 `mygame/server/conf/settings.py` 中添加一个新变量：

```python
CRAFT_RECIPE_MODULES = ['world.recipes']
```

这些模块中的所有顶级类（名称不以 `_` 开头）将被 Evennia 解析为可用于制作系统的配方。使用上述示例，创建 `mygame/world/recipes.py` 并在其中添加你的配方：

一个快速的示例（详见下文）：

```python
from evennia.contrib.game_systems.crafting import CraftingRecipe, CraftingValidationError

class RecipeBread(CraftingRecipe):
    """
    面包非常适合制作三明治！
    """

    name = "bread"   # 用于在 'craft' 命令中识别此配方
    tool_tags = ["bowl", "oven"]
    consumable_tags = ["flour", "salt", "yeast", "water"]
    output_prototypes = [
        {"key": "Loaf of Bread",
         "aliases": ["bread"],
         "desc": "一条新鲜的面包。",
         "typeclass": "typeclasses.objects.Food",  # 假设存在
         "tags": [("bread", "crafting_material")]  # 使其可用于其他配方...
        }
    ]

    def pre_craft(self, **kwargs):
        # 验证输入等。如果失败，则引发 `CraftingValidationError`

    def do_craft(self, **kwargs):
        # 执行制作 - 直接向用户报告错误并返回 None（如果失败）和创建的物品（如果成功）。

    def post_craft(self, result, **kwargs):
        # 进行任何后续效果。无论 `do_craft` 是否失败，都会调用此方法（如果失败，结果将为 None）
```

## 添加新配方

一个 *配方* 是一个继承自 `evennia.contrib.game_systems.crafting.CraftingRecipe` 的类。该类实现了使用游戏内物品的最常见制作形式。每个配方是一个单独的类，使用你提供的消耗品/工具进行初始化。

为了让 `craft` 命令找到你的自定义配方，你需要告诉 Evennia 它们的位置。在 `mygame/server/conf/settings.py` 文件中添加一行，列表中包含任何新模块，其中有配方类。

```python
CRAFT_RECIPE_MODULES = ["world.myrecipes"]
```

（添加后需要重新加载）。所有全局级别的类（名称不以 `_` 开头）将被系统视为有效的配方。

假设你创建了 `mygame/world/myrecipes.py` 来匹配上述示例设置：

```python
# 在 mygame/world/myrecipes.py 中

from evennia.contrib.game_systems.crafting import CraftingRecipe

class WoodenPuppetRecipe(CraftingRecipe):
    """一个木偶"""
    name = "wooden puppet"  # 引用此配方的名称
    tool_tags = ["knife"]
    consumable_tags = ["wood"]
    output_prototypes = [
        {"key": "A carved wooden doll",
         "typeclass": "typeclasses.objects.decorations.Toys",
         "desc": "一只小木雕娃娃"}
    ]
```

这指定了输入中要查找的标签。它为配方定义了一个原型，以便在运行时生成结果（一个配方可以根据需要生成多个结果）。除了指定完整的原型字典外，你还可以仅提供现有原型的 `prototype_key` 列表。

在重新加载服务器后，这个配方现在可用。要尝试它，我们应该创建材料和工具来插入到配方中。

配方会分析输入，查找具有特定标签类别的 [标签](../Components/Tags.md)。每个配方使用的标签类别可以通过（`.consumable_tag_category` 和 `.tool_tag_category`）设定。默认值是 `crafting_material` 和 `crafting_tool`。对于木偶，我们需要一个具有 `wood` 标签的物品和一个具有 `knife` 标签的物品：

```python
from evennia import create_object

knife = create_object(key="Hobby knife", tags=[("knife", "crafting_tool")])
wood = create_object(key="Piece of wood", tags=[("wood", "crafting_material")])
```

请注意，物品可以具有任何名称，唯一重要的是标签/标签类别。这意味着如果一把“刺刀”也具有“刀”的制作标签，它也可以用于雕刻木偶。这在谜题中也可能是有趣的，并允许用户实验并找到已知成分的替代品。

顺便说一下，还有一种简单的快捷方式可以做到这点：

```
tools, consumables = WoodenPuppetRecipe.seed()
```

`seed` 类方法将创建用于满足配方要求的简单虚拟物品。这对测试很有用。

假设这些物品已放入我们的库存中，现在我们可以使用游戏内命令进行制作：

```bash
> craft wooden puppet from wood using hobby knife
```

在代码中我们可以这样做：

```python
from evennia.contrib.game_systems.crafting import craft
puppet = craft(crafter, "wooden puppet", knife, wood)
```

在对 `craft` 的调用中，`knife` 和 `wood` 的顺序并不重要——配方将根据它们的标签进行分类。

## 深入定制配方

为了进一步定制配方，了解如何直接使用配方类会很有帮助：

```python
class MyRecipe(CraftingRecipe):
    # ...

tools, consumables = MyRecipe.seed()
recipe = MyRecipe(crafter, *(tools + consumables))
result = recipe.craft()
```

这对测试很有用，且允许你直接使用类，而无需将其添加到 `settings.CRAFTING_RECIPE_MODULES` 中的模块。

即使不修改类属性， `CraftingRecipe` 类上也有许多可选项。最简单的方式是参考 [CraftingRecipe api 文档](evennia.contrib.game_systems.crafting.crafting.CraftingRecipe)。例如，你可以自定义验证错误消息，决定成分是否必须完全正确，是否在失败的情况下仍然消耗成分等等。

要获得更多控制权，你可以在自己的类中重写钩子：

- `pre_craft` - 应处理输入验证并将其数据存储在 `.validated_consumables` 和 `.validated_tools` 中。如果出错，将向制作人报告错误并引发 `CraftingValidationError`。
- `craft` - 仅在 `pre_craft` 完成且没有异常时调用。应返回制作的结果，通过生成原型来生成结果。如果因任何原因造成制作失败，则应返回空列表。这是添加技能检查或随机几率的地方，如果你的游戏需要。
- `post_craft` - 接收来自 `craft` 的结果并处理错误消息，也根据需要删除任何消耗品。如果需要，它还可以在返回之前修改结果。
- `msg` - 这是一个 `self.crafter.msg` 的封装，应该用于向制作人发送消息。集中化这意味着你也可以在一个地方轻松地修改发送样式。

类构造函数（和 `craft` 访问函数）接受可选的 `**kwargs`。这些会传递到每个制作钩子中。默认情况下这些未被使用，但可以用于每次调用定制内容。

### 精通的工匠

目前制作系统没有内置“技能”系统——即如果你不够熟练则可能失败的概念。技能的工作方式依赖于游戏，因此要添加此功能，你需要创建自己的配方父类，让你的配方继承自它。

```python
from random import randint
from evennia.contrib.game_systems.crafting import CraftingRecipe

class SkillRecipe(CraftingRecipe):
    """考虑到技能的配方"""

    difficulty = 20

    def craft(self, **kwargs):
        """输入是正确的。确定制作是否成功"""

        # 这个是在初始化时设定的
        crafter = self.crafter

        # 假设技能直接存储在制作人身上
        # - 技能是 0..100。
        crafting_skill = crafter.db.skill_crafting
        # 骰子投掷决定成功与否：
        if randint(1, 100) <= (crafting_skill - self.difficulty):
            # 一切正常，开始制作
            return super().craft()
        else:
            self.msg("你不够优秀，无法制作这个。下次好运！")
            return []
```

在这个示例中，我们引入了配方的 `.difficulty`，并进行了“掷骰子”检查以确定是否成功。我们当然会让这在完整的游戏中更加生动详细。原则上，你可以根据自己的想法定制每一个配方，但你也可以继承一个中央父类来减少工作量。

[sword recipe example module](evennia.contrib.game_systems.crafting.example_recipes) 也展示了一个在父类中实现随机技能检查的示例，可供多次使用。

## 进一步的定制

如果你想构建更自定义的东西（也许使用不同的输入类型验证逻辑），你也可以查看 `CraftingRecipe` 父类的 `CraftingRecipeBase`。它实施了作为配方所需的最低限度，对于重大更改，你可能更好从这里开始，而不是从更具规范化的 `CraftingRecipe` 开始。
