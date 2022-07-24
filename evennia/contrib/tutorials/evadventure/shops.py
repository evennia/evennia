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

"""

from evennia.utils.evmenu import EvMenu


def start_npc_menu(caller, shopkeeper, **kwargs):
    """
    Access function - start the NPC interaction/shop interface.


    """
