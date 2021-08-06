# NPC shop Tutorial

This tutorial will describe how to make an NPC-run shop. We will make use of the [EvMenu](../Components/EvMenu)
system to present shoppers with a menu where they can buy things from the store's stock.

Our shop extends over two rooms - a "front" room open to the shop's customers and a locked "store
room" holding the wares the shop should be able to sell. We aim for the following features:

 - The front room should have an Attribute `storeroom` that points to the store room.
 - Inside the front room, the customer should have a command `buy` or `browse`. This will open a
menu listing all items available to buy from the store room.
 - A customer should be able to look at individual items before buying.
 - We use "gold" as an example currency. To determine cost, the system will look for an Attribute
`gold_value` on the items in the store room. If not found, a fixed base value of 1 will be assumed.
The wealth of the customer should be set as an Attribute `gold` on the Character. If not set, they
have no gold and can't buy anything.
 - When the customer makes a purchase, the system will check the `gold_value` of the goods and
compare it to the `gold` Attribute of the customer. If enough gold is available, this will be
deducted and the goods transferred from the store room to the inventory of the customer.
 - We will lock the store room so that only people with the right key can get in there.

### The shop menu

We want to show a menu to the customer where they can list, examine and buy items in the store. This
menu should change depending on what is currently for sale. Evennia's *EvMenu* utility will manage
the menu for us. It's a good idea to [read up on EvMenu](../Components/EvMenu) if you are not familiar with it.

#### Designing the menu

The shopping menu's design is straightforward. First we want the main screen. You get this when you
enter a shop and use the `browse` or `buy` command:

```
*** Welcome to ye Old Sword shop! ***
   Things for sale (choose 1-3 to inspect, quit to exit):
_________________________________________________________
1. A rusty sword (5 gold)
2. A sword with a leather handle (10 gold)
3. Excalibur (100 gold)
```

There are only three items to buy in this example but the menu should expand to however many items
are needed. When you make a selection you will get a new screen showing the options for that
particular item:

```
You inspect A rusty sword:

This is an old weapon maybe once used by soldiers in some
long forgotten army. It is rusty and in bad condition.
__________________________________________________________
1. Buy A rusty sword (5 gold)
2. Look for something else.
```

Finally, when you buy something, a brief message should pop up:

```
You pay 5 gold and purchase A rusty sword!
```
or
```
You cannot afford 5 gold for A rusty sword!
```
After this you should be back to the top level of the shopping menu again and can continue browsing.

#### Coding the menu

EvMenu defines the *nodes* (each menu screen with options) as normal Python functions. Each node
must be able to change on the fly depending on what items are currently for sale. EvMenu will
automatically make the `quit` command available to us so we won't add that manually. For compactness
we will put everything needed for our shop in one module, `mygame/typeclasses/npcshop.py`.

```python
# mygame/typeclasses/npcshop.py

from evennia.utils import evmenu

def menunode_shopfront(caller):
    "This is the top-menu screen."

    shopname = caller.location.key
    wares = caller.location.db.storeroom.contents

    # Wares includes all items inside the storeroom, including the
    # door! Let's remove that from our for sale list.
    wares = [ware for ware in wares if ware.key.lower() != "door"]

    text = "*** Welcome to %s! ***\n" % shopname
    if wares:
        text += "   Things for sale (choose 1-%i to inspect);" \
                " quit to exit:" % len(wares)
    else:
        text += "   There is nothing for sale; quit to exit."

    options = []
    for ware in wares:
        # add an option for every ware in store
        options.append({"desc": "%s (%s gold)" %
                             (ware.key, ware.db.gold_value or 1),
                        "goto": "menunode_inspect_and_buy"})
    return text, options
```

In this code we assume the caller to be *inside* the shop when accessing the menu. This means we can
access the shop room via `caller.location` and get its `key` to display as the shop's name. We also
assume the shop has an Attribute `storeroom` we can use to get to our stock. We loop over our goods
to build up the menu's options.

Note that *all options point to the same menu node* called `menunode_inspect_and_buy`! We can't know
which goods will be available to sale so we rely on this node to modify itself depending on the
circumstances. Let's create it now.

```python
# further down in mygame/typeclasses/npcshop.py

def menunode_inspect_and_buy(caller, raw_string):
    "Sets up the buy menu screen."

    wares = caller.location.db.storeroom.contents
    # Don't forget, we will need to remove that pesky door again!
    wares = [ware for ware in wares if ware.key.lower() != "door"]
    iware = int(raw_string) - 1
    ware = wares[iware]
    value = ware.db.gold_value or 1
    wealth = caller.db.gold or 0
    text = "You inspect %s:\n\n%s" % (ware.key, ware.db.desc)

    def buy_ware_result(caller):
        "This will be executed first when choosing to buy."
        if wealth >= value:
            rtext = "You pay %i gold and purchase %s!" % \
                         (value, ware.key)
            caller.db.gold -= value
            ware.move_to(caller, quiet=True)
        else:
            rtext = "You cannot afford %i gold for %s!" % \
                          (value, ware.key)
        caller.msg(rtext)

    options = ({"desc": "Buy %s for %s gold" % \
                        (ware.key, ware.db.gold_value or 1),
                "goto": "menunode_shopfront",
                "exec": buy_ware_result},
               {"desc": "Look for something else",
                "goto": "menunode_shopfront"})

    return text, options
```

In this menu node we make use of the `raw_string` argument to the node. This is the text the menu
user entered on the *previous* node to get here. Since we only allow numbered options in our menu,
`raw_input` must be an number for the player to get to this point. So we convert it to an integer
index (menu lists start from 1, whereas Python indices always starts at 0, so we need to subtract
1). We then use the index to get the corresponding item from storage.

We just show the customer the `desc` of the item. In a more elaborate setup you might want to show
things like weapon damage and special stats here as well.

When the user choose the "buy" option, EvMenu will execute the `exec` instruction *before* we go
back to the top node (the `goto` instruction). For this we make a little inline function
`buy_ware_result`. EvMenu will call the function given to `exec` like any menu node but it does not
need to return anything. In `buy_ware_result` we determine if the customer can afford the cost and
give proper return messages. This is also where we actually move the bought item into the inventory
of the customer.

#### The command to start the menu

We could *in principle* launch the shopping menu the moment a customer steps into our shop room, but
this would probably be considered pretty annoying. It's better to create a [Command](../Components/Commands) for
customers to explicitly wanting to shop around.

```python
# mygame/typeclasses/npcshop.py

from evennia import Command

class CmdBuy(Command):
    """
    Start to do some shopping

    Usage:
      buy
      shop
      browse

    This will allow you to browse the wares of the
    current shop and buy items you want.
    """
    key = "buy"
    aliases = ("shop", "browse")

    def func(self):
        "Starts the shop EvMenu instance"
        evmenu.EvMenu(self.caller,
                      "typeclasses.npcshop",
                      startnode="menunode_shopfront")
```

This will launch the menu. The `EvMenu` instance is initialized with the path to this very module -
since the only global functions available in this module are our menu nodes, this will work fine
(you could also have put those in a separate module). We now just need to put this command in a
[CmdSet](../Components/Command-Sets) so we can add it correctly to the game:

```python
from evennia import CmdSet

class ShopCmdSet(CmdSet):
    def at_cmdset_creation(self):
        self.add(CmdBuy())
```

### Building the shop

There are really only two things that separate our shop from any other Room:

- The shop has the `storeroom` Attribute set on it, pointing to a second (completely normal) room.
- It has the `ShopCmdSet` stored on itself. This makes the `buy` command available to users entering
the shop.

For testing we could easily add these features manually to a room using `@py` or other admin
commands. Just to show how it can be done we'll instead make a custom [Typeclass](../Components/Typeclasses) for
the shop room and make a small command that builders can use to build both the shop and the
storeroom at once.

```python
# bottom of mygame/typeclasses/npcshop.py

from evennia import DefaultRoom, DefaultExit, DefaultObject
from evennia.utils.create import create_object

# class for our front shop room
class NPCShop(DefaultRoom):
    def at_object_creation(self):
        # we could also use add(ShopCmdSet, persistent=True)
        self.cmdset.add_default(ShopCmdSet)
        self.db.storeroom = None

# command to build a complete shop (the Command base class
# should already have been imported earlier in this file)
class CmdBuildShop(Command):
    """
    Build a new shop

    Usage:
        @buildshop shopname

    This will create a new NPCshop room
    as well as a linked store room (named
    simply <storename>-storage) for the
    wares on sale. The store room will be
    accessed through a locked door in
    the shop.
    """
    key = "@buildshop"
    locks = "cmd:perm(Builders)"
    help_category = "Builders"

    def func(self):
        "Create the shop rooms"
        if not self.args:
            self.msg("Usage: @buildshop <storename>")
            return
        # create the shop and storeroom
        shopname = self.args.strip()
        shop = create_object(NPCShop,
                             key=shopname,
                             location=None)
        storeroom = create_object(DefaultRoom,
                             key="%s-storage" % shopname,
                             location=None)
        shop.db.storeroom = storeroom
        # create a door between the two
        shop_exit = create_object(DefaultExit,
                                  key="back door",
                                  aliases=["storage", "store room"],
                                  location=shop,
                                  destination=storeroom)
        storeroom_exit = create_object(DefaultExit,
                                  key="door",
                                  location=storeroom,
                                  destination=shop)
        # make a key for accessing the store room
        storeroom_key_name = "%s-storekey" % shopname
        storeroom_key = create_object(DefaultObject,
                                       key=storeroom_key_name,
                                       location=shop)
        # only allow chars with this key to enter the store room
        shop_exit.locks.add("traverse:holds(%s)" % storeroom_key_name)

        # inform the builder about progress
        self.caller.msg("The shop %s was created!" % shop)
```

Our typeclass is simple and so is our `buildshop` command. The command (which is for Builders only)
just takes the name of the shop and builds the front room and a store room to go with it (always
named `"<shopname>-storage"`. It connects the rooms with a two-way exit. You need to add
`CmdBuildShop` [to the default cmdset](Starting/Adding-Command-Tutorial#step-2-adding-the-command-to-a-
default-cmdset) before you can use it. Once having created the shop you can now `@teleport` to it or
`@open` a new exit to it. You could also easily expand the above command to automatically create
exits to and from the new shop from your current location.

To avoid customers walking in and stealing everything, we create a [Lock](../Components/Locks) on the storage
door. It's a simple lock that requires the one entering to carry an object named
`<shopname>-storekey`. We even create such a key object and drop it in the shop for the new shop
keeper to pick up.

> If players are given the right to name their own objects, this simple lock is not very secure and
you need to come up with a more robust lock-key solution.

> We don't add any descriptions to all these objects so looking "at" them will not be too thrilling.
You could add better default descriptions as part of the `@buildshop` command or leave descriptions
this up to the Builder.

### The shop is open for business!

We now have a functioning shop and an easy way for Builders to create it. All you need now is to
`@open` a new exit from the rest of the game into the shop and put some sell-able items in the store
room. Our shop does have some shortcomings:

- For Characters to be able to buy stuff they need to also have the `gold` Attribute set on
themselves.
- We manually remove the "door" exit from our items for sale. But what if there are other unsellable
items in the store room? What if the shop owner walks in there for example - anyone in the store
could then buy them for 1 gold.
- What if someone else were to buy the item we're looking at just before we decide to buy it? It
would then be gone and the counter be wrong - the shop would pass us the next item in the list.

Fixing these issues are left as an exercise.

If you want to keep the shop fully NPC-run you could add a [Script](../Components/Scripts) to restock the shop's
store room regularly. This shop example could also easily be owned by a human Player (run for them
by a hired NPC) - the shop owner would get the key to the store room and be responsible for keeping
it well stocked.
