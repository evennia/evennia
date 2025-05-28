# 制作系统

由 Griatch 贡献（2020）

这实现了一个完整的制作系统。其原理是基于“配方”，您可以将物品（标记为原料）组合起来创造出新的东西。配方还可以要求某些（不被消耗的）工具。例如，使用“面包配方”将“面粉”、“水”和“酵母”与“烤箱”组合在一起，以烘焙“一个面包条”。

配方过程可以理解为：

```
原料 + 工具 + 配方 -> 物品
```

这里，“原料”在制作过程中会被消耗，而“工具”是过程所必需的，但不会被销毁。

包含的 `craft` 命令的用法如下：

```
craft <recipe> [from <ingredient>,...] [using <tool>, ...]
```

## 示例

使用 `craft` 命令：

```
craft 玩具车 from 板材, 木轮, 钉子 using 锯, 锤子
```

配方不必使用工具或甚至多个原料：

```
 雪 + 雪球配方 -> 雪球
```

相反，也可以想象使用工具而不需要消耗品，比如：

```
 spell_book + wand + fireball_recipe -> fireball
```

这个系统足够通用，还可以用于类冒险解谜（但需要更改命令并根据所组合的内容确定配方）：

```
 stick + string + hook -> 临时钓竿
 临时钓竿 + storm_drain -> 钥匙
```

请参见 [剑的示例](evennia.contrib.game_systems.crafting.example_recipes)，了解如何设计用于制作剑的配方树。

## 安装和使用

从 `evennia/contrib/crafting/crafting.py` 导入 `CmdCraft` 命令，并将其添加到您的角色命令集（cmdset）中。重新加载后，您将能够使用 `craft` 命令：

```
craft <recipe> [from <ingredient>,...] [using <tool>, ...]
```

在代码中，您可以使用 `evennia.contrib.game_systems.crafting.craft` 函数进行制作：

```python
from evennia.contrib.game_systems.crafting import craft

result = craft(caller, "recipename", *inputs)
```

这里，`caller` 是正在进行制作的人，`*inputs` 是任何组合的消耗品和/或工具对象。系统将通过它们的 [标签](../Components/Tags.md) 来识别它们（见下文）。`result` 始终是一个列表。

要使用制作系统，您需要配方。请在 `mygame/server/conf/settings.py` 中添加一个新变量：

```python
CRAFT_RECIPE_MODULES = ['world.recipes']
```

这些模块中的所有顶级类（名称不以 `_` 开头）将被 Evennia 解析为可供制作系统使用的配方。根据上述示例，创建 `mygame/world/recipes.py` 并在其中添加配方：

一个简单的例子（后续会有更多细节）：

```python
from evennia.contrib.game_systems.crafting import CraftingRecipe, CraftingValidationError

class RecipeBread(CraftingRecipe):
    """
    面包很好，适合做三明治！
    """

    name = "bread"   # 用于识别此配方的名称在 'craft' 命令中
    tool_tags = ["bowl", "oven"]
    consumable_tags = ["flour", "salt", "yeast", "water"]
    output_prototypes = [
        {"key": "Loaf of Bread",
         "aliases": ["bread"],
         "desc": "一条漂亮的面包。",
         "typeclass": "typeclasses.objects.Food",  # 假设这个存在
         "tags": [("bread", "crafting_material")]  # 使其可在其他配方中使用 ...
        }
    ]

    def pre_craft(self, **kwargs):
        # 验证输入等。如果失败，抛出 `CraftingValidationError`

    def do_craft(self, **kwargs):
        # 执行制作 - 将错误直接报告给用户，如果失败返回 None，如果成功则返回创建的对象。

    def post_craft(self, result, **kwargs):
        # 任何后制作效果。始终调用，即使 do_craft 失败（结果将是 None）。
```

## 添加新配方

*配方* 是从 `evennia.contrib.game_systems.crafting.CraftingRecipe` 继承的类。这个类实现了最常见的制作形式 - 使用游戏内物品。每个配方都是一个单独的类，用您提供的消耗品/工具初始化。

为了让 `craft` 命令找到您的自定义配方，您需要告诉 Evennia 它们的位置。在 `mygame/server/conf/settings.py` 文件中添加新行，如下所示：

```python
CRAFT_RECIPE_MODULES = ["world.myrecipes"]
```

（添加后需要重新加载）。所有全局级别的类（名称不以 `_` 开头）都将被系统视为有效的配方。

这里我们假设您创建了 `mygame/world/myrecipes.py`，以匹配上述示例设置：

```python
# 在 mygame/world/myrecipes.py

from evennia.contrib.game_systems.crafting import CraftingRecipe

class WoodenPuppetRecipe(CraftingRecipe):
    """一个木偶"""
    name = "wooden puppet"  # 作为配方的名称
    tool_tags = ["knife"]
    consumable_tags = ["wood"]
    output_prototypes = [
        {"key": "一个雕刻的木偶",
         "typeclass": "typeclasses.objects.decorations.Toys",
         "desc": "一个小雕刻的娃娃"}
    ]
```

这指定了查找输入时要查看的标签。它定义了用于即时生成结果的配方 [原型](../Components/Prototypes.md)（配方可以在需要时生成多个结果）。可以通过提供现有原型的 `prototype_key` 列表来代替指定完整的原型字典。

重新加载服务器后，此配方现在可供使用。为了尝试它，我们应该创建材料和工具以插入配方。

配方分析输入，查找具有特定标签类别的 [标签](../Components/Tags.md)。每个配方可以设置使用的标签类别（分别使用 `.consumable_tag_category` 和 `.tool_tag_category`）。默认情况下为 `crafting_material` 和 `crafting_tool`。对于木偶，我们需要一个带有 `wood` 标签的物品和另一个带有 `knife` 标签的物品：

```python
from evennia import create_object

knife = create_object(key="Hobby knife", tags=[("knife", "crafting_tool")])
wood = create_object(key="Piece of wood", tags=[("wood", "crafting_material")])
```

请注意，物品可以有任何名称，重要的是标签/标签类别。这意味着如果“刺刀”也有“刀”的制作标签，它也可以用于雕刻木偶。这对于使用在谜题中也很有趣，可以让用户进行实验，找到替代成分。

顺便说一句，还有一个简单的快捷方式：

```
tools, consumables = WoodenPuppetRecipe.seed()
```

`seed` 类方法将创建简单的虚拟对象，满足配方的要求。这非常适合测试。

假设这些物品已放入我们的库存中，我们现在可以使用游戏内命令进行制作：

```bash
> craft wooden puppet from wood using hobby knife
```

在代码中，我们可以这样做：

```python
from evennia.contrib.game_systems.crafting import craft
puppet = craft(crafter, "wooden puppet", knife, wood)
```

在调用 `craft` 时，`knife` 和 `wood` 的顺序无关紧要 - 配方将根据它们的标签进行分类。

## 更深入的配方自定义

要进一步自定义配方，了解如何直接使用配方类会有所帮助：

```python
class MyRecipe(CraftingRecipe):
    # ...

tools, consumables = MyRecipe.seed()
recipe = MyRecipe(crafter, *(tools + consumables))
result = recipe.craft()
```

这对于测试非常有用，可以让您直接使用类，而无需将其添加到 `settings.CRAFTING_RECIPE_MODULES` 的模块中。

即使不修改类属性，也有很多选项可以设置在 `CraftingRecipe` 类上。最简单的是参考 [CraftingRecipe API 文档](evennia.contrib.game_systems.crafting.crafting.CraftingRecipe)。例如，您可以自定义验证错误消息，决定是否必须完全正确的成分，失败时是否仍然消耗成分等等。

要获得更大的控制，您可以在您自己的类中重写钩子：

- `pre_craft` - 此方法应该处理输入验证并将数据存储在 `.validated_consumables` 和 `.validated_tools` 中。如果出错，它会将错误报告给手工艺者并引发 `CraftingValidationError`。
- `craft` - 只有在 `pre_craft` 完成没有异常的情况下，才会调用此方法。应通过生成原型返回制作结果。如果因某种原因制作失败，则返回空列表。这是添加技能检查或随机机会的地方。
- `post_craft` - 此方法从 `craft` 接收结果并处理错误消息，还可以根据需要删除任何消耗品。它也可以在返回之前修改结果。
- `msg` - 这是 `self.crafter.msg` 的包装，应该用于向制作者发送消息。将此集中处理意味着您可以轻松地在一个地方更改发送样式。

类构造函数（和 `craft` 访问函数）接受可选的 `**kwargs`。这些会被传递到每个制作钩子中。默认情况下，它们未使用，但可以用于按调用自定义。

### 熟练的工匠

制作系统的盒子里没有的就是“技能”系统 - 这个概念是如果你不够熟练就可能失败。技能会因游戏而异，因此要添加这个，您需要创建自己的配方父类，让您的配方从中继承。

```python
from random import randint
from evennia.contrib.game_systems.crafting import CraftingRecipe

class SkillRecipe(CraftingRecipe):
    """考虑技能的配方"""

    difficulty = 20

    def craft(self, **kwargs):
        """输入是可以的。确定制作是否成功"""

        # 这是在初始化时设置的
        crafter = self.crafter

        # 假设技能直接存储在工匠身上
        # - 技能范围为 0..100。
        crafting_skill = crafter.db.skill_crafting
        # 投掷骰子确定成功：
        if randint(1, 100) <= (crafting_skill - self.difficulty):
            # 一切顺利，开始制作
            return super().craft()
        else:
            self.msg("您不够好，无法制作这个。下次好运！")
            return []
```

在这个例子中，我们为配方引入了一个 `.difficulty`，并进行“掷骰子”，以查看是否成功。我们当然会让这个在完整游戏中更加身临其境和详细。原则上，您可以按照自己的想法自定义每个配方，但您也可以从中央父类继承，以减少工作量。

[sword recipe example module](evennia.contrib.game_systems.crafting.example_recipes) 也展示了如何在一个父类中实现随机技能检查，然后为多个使用继承。

## 更加定制

如果您想建立更自定义的东西（也许使用不同输入类型的验证逻辑），您也可以查看 `CraftingRecipe` 父类 `CraftingRecipeBase`。它实现了作为配方所需的最小内容，对于重大更改，您可能最好从这个类开始，而不是更具主观性的 `CraftingRecipe`。


----

<small>此文档页面并非由 `evennia/contrib/game_systems/crafting/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
