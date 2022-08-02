"""
EvAdventure Shop system.


A shop is run by an NPC. It can provide one or more of several possible services:

- Buy from a pre-set list of (possibly randomized) items. Cost is based on the item's value,
  adjusted by how stingy the shopkeeper is. When bought this way, the item is
  generated on the fly and passed to the player character's inventory. Inventory files are
  a list of prototypes, normally from a prototype-file. A random selection of items from each
  inventory file is available.
- Sell items to the shop for a certain percent of their value. One could imagine being able
  to buy back items again, but we will instead _destroy_ sold items, so as to remove them
  from circulation. In-game we can say it's because the merchants collect the best stuff
  to sell to collectors in the big city later. Each merchant buys a certain subset of items
  based on their tags.
- Buy a service. For a cost, a certain action is performed for the character; this applies
  immediately when bought. The most notable services are healing and converting coin to XP.
- Buy rumors - this is echoed to the player for a price. Different merchants could have
  different rumors (or randomized ones).
- Quest - gain or hand in a quest for a merchant.

All shops are menu-driven. One starts talking to the npc and will then end up in their shop
interface.


This is a series of menu nodes meant to be added as a mapping via
`EvAdventureShopKeeper.create(menudata={},...)`.

To make this pluggable, the shopkeeper start page will analyze the available nodes
and auto-add options to all nodes in the three named `node_start_*`. The last part of the
node name will be the name of the option capitalized, with underscores replaced by spaces, so
`node_start_sell_items` will become a top-level option `Sell items`.



"""

from random import choice

from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import make_iter

from .npcs import EvAdventureShopKeeper

# shop menu nodes to use for building a Shopkeeper npc


def node_start_buy(caller, raw_string, **kwargs):
    """
    Menu node for the caller to buy items from the shopkeep. This assumes `**kwargs` contains
    a kwarg `npc` referencing the npc/shopkeep being talked to.

    Items available to sell are a combination of items in the shopkeep's inventory and prototypes
    the list of `prototypes` stored in the Shopkeep's "common_ware_prototypes` Attribute. In the
    latter case, the properties will be extracted from the prototype when inspecting it (object will
    only spawn when bought).

    """
