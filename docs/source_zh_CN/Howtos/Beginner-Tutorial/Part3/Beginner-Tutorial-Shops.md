# 游戏内商店

```{warning}
本初学者教程的这一部分仍在开发中。
```

## 商店功能概述

在 _EvAdventure_ 中，我们希望能够创建一个简单的商店系统，使玩家可以购买、出售和交易物品。商店的功能包括：

- **查看可用商品**：玩家能够查看当前商店出售的所有物品及其价格。
- **购买物品**：玩家可以选择购买商品，消耗相应的游戏货币（例如金币）。
- **出售物品**：玩家可以将自己拥有的物品出售给商店以赚取货币。
- **交易物品**：允许角色之间交换物品。

## 商店设计基本结构

为了实现这一功能，我们需要定义商店类以及相关方法。基本的商店结构可以如下所示：

```python
class Shop:
    def __init__(self):
        self.inventory = {}  # 存储商品及其价格

    def add_item(self, item_name, price):
        """ 添加商品到商店 """
        self.inventory[item_name] = price

    def remove_item(self, item_name):
        """ 从商店移除商品 """
        if item_name in self.inventory:
            del self.inventory[item_name]

    def view_inventory(self):
        """ 显示商店当前所有商品 """
        for item, price in self.inventory.items():
            print(f"{item}: {price}金币")

    def buy_item(self, item_name, player):
        """ 玩家购买商品 """
        if item_name in self.inventory:
            price = self.inventory[item_name]
            if player.gold >= price:
                player.gold -= price
                player.add_item(item_name)
                print(f"你购买了 {item_name}！")
            else:
                print("金币不足！")
        else:
            print("该商品不存在。")

    def sell_item(self, item_name, player):
        """ 玩家出售商品 """
        if item_name in player.inventory:
            price = self.inventory.get(item_name) / 2  # 出售价格为一半
            player.gold += price
            player.remove_item(item_name)
            print(f"你出售了 {item_name}！")
        else:
            print("你没有这个商品。")
```

## 玩家类

我们还需要定义一个玩家类，以支持商店系统所需的基本功能，如持有金币和物品：

```python
class Player:
    def __init__(self):
        self.gold = 100  # 初始金币数
        self.inventory = []  # 玩家物品清单

    def add_item(self, item_name):
        """ 将物品添加到玩家背包 """
        self.inventory.append(item_name)

    def remove_item(self, item_name):
        """ 从玩家背包中移除物品 """
        if item_name in self.inventory:
            self.inventory.remove(item_name)
```

## 示例用法

下面是如何使用商店和玩家类的一个小示例：

```python
# 创建商店和玩家
shop = Shop()
player = Player()

# 添加商品到商店
shop.add_item("健康药水", 10)
shop.add_item("魔法卷轴", 50)

# 查看商店商品
shop.view_inventory()

# 玩家购买商品
shop.buy_item("健康药水", player)

# 玩家的当前金币和库存
print(f"当前金币: {player.gold}")
print(f"玩家库存: {player.inventory}")

# 玩家出售商品
shop.sell_item("健康药水", player)
```

## 接下来的开发

在本部分的进一步开发中，我们还可以考虑：

- **实现库存管理**：让商店能够在库存变化时自动更新。
- **增加商品种类**：允许商店出售不同类型的物品，如武器、护甲、道具等。
- **添加交易系统**：实现玩家之间的物品交易。

请继续关注该部分的更新！
