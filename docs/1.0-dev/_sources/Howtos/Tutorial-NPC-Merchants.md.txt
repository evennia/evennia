# NPC merchants

```
*** Welcome to ye Old Sword shop! ***
   Things for sale (choose 1-3 to inspect, quit to exit):
_________________________________________________________
1. A rusty sword (5 gold)
2. A sword with a leather handle (10 gold)
3. Excalibur (100 gold)
```

This will introduce an NPC able to sell things. In practice this means that when you interact with them you'll get shown a _menu_ of choices. Evennia  provides the [EvMenu](../Components/EvMenu.md) utility to easily create in-game menus. 

We will store all the merchant's wares in their inventory. This means that they may stand in an actual shop room, at a market or wander the road.  We will also use 'gold' as an example currency.  
To enter the shop, you'll just need to stand in the same room and use the `buy/shop` command.

## Making the merchant class 

The merchant will respond to you giving the `shop` or `buy` command in their presence. 

```python
# in for example mygame/typeclasses/merchants.py 

from typeclasses.objects import Object
from evennia import Command, CmdSet, EvMenu

class CmdOpenShop(Command): 
    """
    Open the shop! 

    Usage:
        shop/buy 

    """
    key = "shop"
    aliases = ["buy"]

    def func(self):
        # this will sit on the Merchant, which is self.obj. 
        # the self.caller is the player wanting to buy stuff.    
        self.obj.open_shop(self.caller)
        

class MerchantCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdOpenShop())


class NPCMerchant(Object):

     def at_object_creation(self):
         self.cmdset.add_default(MerchantCmdSet)

     def open_shop(self, shopper):
         menunodes = {}  # TODO! 
         shopname = self.db.shopname or "The shop"
         EvMenu(shopper, menunodes, startnode="shop_start", 
                shopname=shopname, shopkeeper=self, wares=self.contents)

```

We could also have put the commands in a separate module, but for compactness, we put it all with the merchant typeclass. 

Note that we make the merchant an `Object`! Since we don't give them any other commands, it makes little sense to let them be a `Character`.

We make a very simple `shop`/`buy` Command and make sure to add it on the merchant in its own cmdset. 

We initialize `EvMenu` on the `shopper` but we haven't created any `menunodes` yet, so this will not actually do much at this point. It's important that we we pass `shopname`, `shopkeeper` and `wares` into the menu, it means they will be made available as properties on the EvMenu instance - we will be able to access them from inside the menu.

## Coding the shopping menu

[EvMenu](../Components/EvMenu.md) splits the menu into _nodes_ represented by Python functions. Each node represents a stop in the menu where the user has to make a choice. 

For simplicity, we'll code the shop interface above the `NPCMerchant` class in the same module.

The start node of the shop named "ye Old Sword shop!" will look like this if there are only 3 wares to sell: 

```
*** Welcome to ye Old Sword shop! ***
   Things for sale (choose 1-3 to inspect, quit to exit):
_________________________________________________________
1. A rusty sword (5 gold)
2. A sword with a leather handle (10 gold)
3. Excalibur (100 gold)
```


```python
# in mygame/typeclasses/merchants.py

# top of module, above NPCMerchant class.

def node_shopfront(caller, raw_string, **kwargs):
    "This is the top-menu screen."

    # made available since we passed them to EvMenu on start 
    menu = caller.ndb._evmenu
    shopname = menu.shopname
    shopkeeper = menu.shopkeeper 
    wares = menu.wares

    text = f"*** Welcome to {shopname}! ***\n"
    if wares:
        text += f"   Things for sale (choose 1-{len(wares)} to inspect); quit to exit:"
    else:
        text += "   There is nothing for sale; quit to exit."

    options = []
    for ware in wares:
        # add an option for every ware in store
        gold_val = ware.db.gold_value or 1
        options.append({"desc": f"{ware.key} ({gold_val} gold)",
                        "goto": ("inspect_and_buy", 
                                 {"selected_ware": ware})
                       })
                       
    return text, options
```

Inside the node we can access the menu on the caller as `caller.ndb._evmenu`. The extra keywords we passed into `EvMenu` are available on this menu instance. Armed with this we can easily present a shop interface. Each option will become a numbered choice on this screen. 

Note how we pass the `ware` with each option and label it `selected_ware`. This will be accessible in the next node's `**kwargs` argument

If a player choose one of the wares, they should be able to inspect it. Here's how it should look if they selected `1` in ye Old Sword shop:

```
You inspect A rusty sword:

This is an old weapon maybe once used by soldiers in some
long forgotten army. It is rusty and in bad condition.
__________________________________________________________
1. Buy A rusty sword (5 gold)
2. Look for something else.
```

If you buy, you'll see

```
You pay 5 gold and purchase A rusty sword!
```
or
```
You cannot afford 5 gold for A rusty sword!
```

Either way you should end up back at the top level of the shopping menu again and can continue browsing or quit the menu with `quit`. 

Here's how it looks in code:

```python
# in mygame/typeclasses/merchants.py 

# right after the other node

def _buy_item(caller, raw_string, **kwargs):
    "Called if buyer chooses to buy"
    selected_ware = kwargs["selected_ware"]
    value = selected_ware.db.gold_value or 1
    wealth = caller.db.gold or 0

    if wealth >= value:
        rtext = f"You pay {value} gold and purchase {ware.key}!"
        caller.db.gold -= value
        move_to(caller, quiet=True, move_type="buy")
    else:
        rtext = f"You cannot afford {value} gold for {ware.key}!"
    caller.msg(rtext)
    # no matter what, we return to the top level of the shop
    return "shopfront"

def node_inspect_and_buy(caller, raw_string, **kwargs):
    "Sets up the buy menu screen."

    # passed from the option we chose 
    selected_ware = kwargs["selected_ware"]

    value = selected_ware.db.gold_value or 1
    text = f"You inspect {ware.key}:\n\n{ware.db.desc}"
    gold_val = ware.db.gold_value or 1

    options = ({
        "desc": f"Buy {ware.key} for {gold_val} gold",
        "goto": (_buy_item, kwargs)
    }, {
        "desc": "Look for something else",
        "goto": "shopfront",
    })
    return text, options
```

In this node we grab the `selected_ware` from `kwargs` - this we pased along from the option on the previous node. We display its description and value. If the user buys, we reroute through the `_buy_item` helper function (this is not a node, it's just a callable that must return the name of the next node to go to.). In `_buy_item` we check if the buyer can affort the ware, and if it can we move it to their inventory. Either way, this method returns `shop_front` as the next node. 

We have been referring to two nodes here: `"shopfront"` and `"inspect_and_buy"` , we should map them to the code in the menu. Scroll down to the `NPCMerchant` class in the same module and find that unfinished `open_shop` method again: 


```python
# in /mygame/typeclasses/merchants.py

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
         shopname = self.db.shopname or "The shop"
         EvMenu(shopper, menunodes, startnode="shop_start", 
                shopname=shopname, shopkeeper=self, wares=self.contents)

```


We now added the nodes to the Evmenu under their right labels. The merchant is now ready! 


## The shop is open for business!

Make sure to `reload`.

Let's try it out by creating the merchant and a few wares in-game. Remember that we also must create some gold get this economy going. 

```
> set self/gold = 8

> create/drop Stan S. Stanman;stan:typeclasses.merchants.NPCMerchant
> set stan/shopname = Stan's previously owned vessles

> create/drop A proud vessel;ship 
> set ship/desc = The thing has holes in it.
> set ship/gold_value = 5

> create/drop A classic speedster;rowboat 
> set rowboat/gold_value = 2
> set rowboat/desc = It's not going anywhere fast.
```

Note that a builder without any access to Python code can now set up a personalized merchant with just in-game commands.  With the shop all set up, we just need to be in the same room to start consuming! 

```
> buy
*** Welcome to Stan's previously owned vessels! ***
   Things for sale (choose 1-3 to inspect, quit to exit):
_________________________________________________________
1. A proud vessel (5 gold)
2. A classic speedster (2 gold)

> 1 

You inspect A proud vessel:

The thing has holes in it.
__________________________________________________________
1. Buy A proud vessel (5 gold)
2. Look for something else.

> 1
You pay 5 gold and purchase A proud vessel!

*** Welcome to Stan's previously owned vessels! ***
   Things for sale (choose 1-3 to inspect, quit to exit):
_________________________________________________________
1. A classic speedster (2 gold)

```

