# NPC 商人

```
*** 欢迎来到旧剑店！ ***
   可供出售的物品（选择 1-3 检查，quit 退出）:
_________________________________________________________
1. 一把生锈的剑（5 金）
2. 一把皮革把手的剑（10 金）
3. Excalibur（100 金）
```

本文将介绍一个能够出售物品的 NPC。在实践中，这意味着当你与他们互动时，你将看到一个 _菜单_ 选项。Evennia 提供了 [EvMenu](../Components/EvMenu.md) 工具，以便轻松创建游戏内菜单。

我们将把商人的商品存放在他们的库存中。这意味着他们可能站在一个实际的商店房间里、在市场中或在路上漫游。我们还将使用“金”作为示例货币。要进入商店，只需在同一房间内使用 `buy/shop` 命令即可。

## 创建商人类

商人会对你在他们身边给出的 `shop` 或 `buy` 命令做出反应。

```python
# 在例如 mygame/typeclasses/merchants.py 中

from typeclasses.objects import Object
from evennia import Command, CmdSet, EvMenu

class CmdOpenShop(Command): 
    """
    打开商店！ 

    用法:
        shop/buy 

    """
    key = "shop"
    aliases = ["buy"]

    def func(self):
        # 这将位于商人上，即 self.obj。 
        # self.caller 是想要购买东西的玩家。    
        self.obj.open_shop(self.caller)
        

class MerchantCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdOpenShop())


class NPCMerchant(Object):

     def at_object_creation(self):
         self.cmdset.add_default(MerchantCmdSet)

     def open_shop(self, shopper):
         menunodes = {}  # TODO! 
         shopname = self.db.shopname or "商店"
         EvMenu(shopper, menunodes, startnode="shopfront", 
                shopname=shopname, shopkeeper=self, wares=self.contents)
```

我们也可以将命令放在单独的模块中，但为了紧凑性，我们将其与商人类型类放在一起。

注意我们将商人设置为一个 `Object`！因为我们没有给他们任何其他命令，所以将他们设为 `Character` 并没有太大意义。

我们创建了一个非常简单的 `shop`/`buy` 命令，并确保将其添加到商人的命令集中。

我们在 `shopper` 上初始化 `EvMenu`，但我们还没有创建任何 `menunodes`，所以此时不会实际做什么。重要的是，我们将 `shopname`、`shopkeeper` 和 `wares` 传递给菜单，这意味着它们将作为属性可用于 EvMenu 实例 - 我们可以在菜单内部访问它们。

## 编写购物菜单

[EvMenu](../Components/EvMenu.md) 将菜单拆分为由 Python 函数表示的 _节点_。每个节点表示菜单中的一个停靠点，用户必须在此做出选择。

为了简单起见，我们将在同一模块中的 `NPCMerchant` 类上方编写商店接口。

商店的起始节点名为“旧剑店！”如果有 3 种商品出售，它将如下所示：

```
*** 欢迎来到旧剑店！ ***
   可供出售的物品（选择 1-3 检查，quit 退出）:
_________________________________________________________
1. 一把生锈的剑（5 金）
2. 一把皮革把手的剑（10 金）
3. Excalibur（100 金）
```

```python
# 在 mygame/typeclasses/merchants.py 中

# 模块顶部，在 NPCMerchant 类之上。

def node_shopfront(caller, raw_string, **kwargs):
    "这是顶部菜单屏幕。"

    # 由于我们传递给 EvMenu，所以可用的菜单 
    menu = caller.ndb._evmenu
    shopname = menu.shopname
    shopkeeper = menu.shopkeeper 
    wares = menu.wares

    text = f"*** 欢迎来到 {shopname}! ***\n"
    if wares:
        text += f"   可供出售的物品（选择 1-{len(wares)} 检查）；quit 退出:"
    else:
        text += "   没有什么可出售的；quit 退出。"

    options = []
    for ware in wares:
        # 为商店中的每个物品添加一个选项
        gold_val = ware.db.gold_value or 1
        options.append({"desc": f"{ware.key} ({gold_val} 金)",
                        "goto": ("inspect_and_buy", 
                                 {"selected_ware": ware})
                       })
                       
    return text, options
```

在节点内部，我们可以通过 `caller.ndb._evmenu` 访问菜单。我们传递给 `EvMenu` 的额外关键字在此菜单实例上可用。借助这个信息，我们可以轻松呈现一个商店界面。每个选项将成为此屏幕上的一个编号选择。

注意我们将 `ware` 与每个选项一起传递，并将其标记为 `selected_ware`。这将在下一个节点的 `**kwargs` 参数中可访问。

如果玩家选择了一个商品，他们应该能够进行检查。如果他们在旧剑店选择了 `1`，它将如下所示：

```
你检查了一把生锈的剑：

这是一件旧武器，也许曾被一些
被遗忘的军队的士兵使用。它生锈了，状况不佳。
__________________________________________________________
1. 购买一把生锈的剑（5 金）
2. 寻找其他东西。
```

如果你购买，你会看到

```
你支付 5 金并购买了一把生锈的剑！
```
或者
```
你无法负担 5 金购买一把生锈的剑！
```

无论哪种情况，你都应该最终返回购物菜单的顶层，继续浏览或使用 `quit` 退出菜单。

以下是代码示例：

```python
# 在 mygame/typeclasses/merchants.py 中 

# 在其他节点之后

def _buy_item(caller, raw_string, **kwargs):
    "当买家选择购买时调用"
    selected_ware = kwargs["selected_ware"]
    value = selected_ware.db.gold_value or 1
    wealth = caller.db.gold or 0

    if wealth >= value:
        rtext = f"你支付 {value} 金并购买了 {selected_ware.key}！"
        caller.db.gold -= value
        move_to(caller, quiet=True, move_type="buy")
    else:
        rtext = f"你无法负担 {value} 金购买 {selected_ware.key}！"
    caller.msg(rtext)
    # 无论如何，返回商店的顶层
    return "shopfront"

def node_inspect_and_buy(caller, raw_string, **kwargs):
    "设置购买菜单屏幕。"

    # 从我们选择的选项中传递 
    selected_ware = kwargs["selected_ware"]

    value = selected_ware.db.gold_value or 1
    text = f"你检查了 {selected_ware.key}:\n\n{selected_ware.db.desc}"
    gold_val = selected_ware.db.gold_value or 1

    options = ({
        "desc": f"以 {gold_val} 金购买 {selected_ware.key}",
        "goto": (_buy_item, kwargs)
    }, {
        "desc": "寻找其他东西",
        "goto": "shopfront",
    })
    return text, options
```

在此节点中，我们从 `kwargs` 中获取 `selected_ware` - 这是我们从上一个节点的选项中传递过来的。我们展示它的描述和价值。如果用户购买，我们通过 `_buy_item` 辅助函数重新路由（这不是一个节点，它只是一个调用内存的函数，必须返回要转到的下一个节点的名称）。在 `_buy_item` 中，我们检查买家是否能负担商品，如果可以，我们将其移动到他们的库存中。无论如何，该方法返回 `shopfront` 作为下一个节点。

我们一直在提到两个节点：“shopfront”和“inspect_and_buy”，我们应该将它们映射到菜单中的代码。滚动到同一模块中的 `NPCMerchant` 类并找到之前未完成的 `open_shop` 方法：

```python
# 在 /mygame/typeclasses/merchants.py 中

def node_shopfront(caller, raw_string, **kwargs):
    # ... 

def _buy_item(caller, raw_string, **kwargs):
    # ...

def node_inspect_and_buy(caller, raw_string, **kwargs):
    # ... 

class NPCMerchant(Object):

     # ...

     def open_shop(self, shopper):
         menunodes = {
             "shopfront": node_shopfront,
             "inspect_and_buy": node_inspect_and_buy
         }
         shopname = self.db.shopname or "商店"
         EvMenu(shopper, menunodes, startnode="shopfront", 
                shopname=shopname, shopkeeper=self, wares=self.contents)
```

我们现在将节点添加到 Evmenu 中，并使用它们的正确标签。商人现在准备好了！

## 商店开张营业！

确保 `reload`。

让我们通过在游戏中创建商人和一些商品来尝试一下。请记住，我们还必须创建一些金币以推动经济发展。

```
> set self/gold = 8

> create/drop Stan S. Stanman;stan:typeclasses.merchants.NPCMerchant
> set stan/shopname = Stan 的二手船只

> create/drop A proud vessel;ship 
> set ship/desc = 这东西有洞。
> set ship/gold_value = 5

> create/drop A classic speedster;rowboat 
> set rowboat/gold_value = 2
> set rowboat/desc = 它不会快速离开这个地方。
```

请注意，没有任何 Python 代码访问权限的建造者现在可以仅使用游戏内命令设置个性化商人。商店一切都设置好后，我们只需待在同一个房间即可开始消费！

```
> buy
*** 欢迎来到 Stan 的二手船只！ ***
   可供出售的物品（选择 1-3 检查，quit 退出）:
_________________________________________________________
1. 一艘骄傲的船（5 金）
2. 一艘经典极速船（2 金）

> 1 

你检查了 A proud vessel:

这东西有洞。
__________________________________________________________
1. 购买一艘骄傲的船（5 金）
2. 寻找其他东西。

> 1
你支付 5 金并购买了一艘骄傲的船！

*** 欢迎来到 Stan 的二手船只！ ***
   可供出售的物品（选择 1-3 检查，quit 退出）:
_________________________________________________________
1. 一艘经典极速船（2 金）
```
