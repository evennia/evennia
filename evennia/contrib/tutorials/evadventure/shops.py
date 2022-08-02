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

from dataclasses import dataclass
from random import choice

from evennia.prototypes.prototypes import search_prototype
from evennia.prototypes.spawner import flatten_prototype
from evennia.utils.evmenu import EvMenu, list_node
from evennia.utils.logger import log_err, log_trace
from evennia.utils.utils import make_iter

from .enums import Ability, ObjType, WieldLocation
from .npcs import EvAdventureShopKeeper


@dataclass
class BuyItem:
    """
    Storage container for storing generic info about an item for sale. This means it can be used
    both for real objects and for prototypes without constantly having to track which is which.

    """

    # skipping typehints here since we are not using them anywhere else

    # available for all buyable items
    key = ""
    desc = ""
    obj_type = ObjType.GEAR
    size = 1
    value = 0
    use_slot = WieldLocation.BACKPACK

    uses = None
    quality = None
    attack_type = None
    defense_type = None
    damage_roll = None

    # references the original (always only one of the two)
    obj = None
    prototype = None

    @staticmethod
    def create_from_obj(obj, shopkeeper):
        """
        Build a new BuyItem container from a real db obj.

        Args:
            obj (EvAdventureObject): An object to analyze.
            shopkeeper (EvAdventureShopKeeper): The shopkeeper.

        Returns:
            BuyItem: A general representation of the original data.

        """
        try:
            # mandatory
            key = obj.key
            desc = obj.db.desc
            obj_type = obj.obj_type
            size = obj.size
            use_slot = obj.use_slot
            value = obj.value * shopkeeper.upsell_factor
        except AttributeError:
            # not a buyable item
            log_trace("Not a buyable item")
            return None

        # getting optional properties

        return BuyItem(
            key=key,
            desc=desc,
            obj_type=obj_type,
            size=size,
            use_slot=use_slot,
            value=value,
            # optional fields
            uses=getattr(obj, "uses", None),
            quality=getattr(obj, "quality", None),
            attack_type=getattr(obj, "attack_type", None),
            defense_type=getattr(obj, "defense_type", None),
            damage_roll=getattr(obj, "damage_roll", None),
            # back-reference (don't set prototype)
            obj=obj,
        )

    @staticmethod
    def create_from_prototype(self, prototype_or_key, shopkeeper):
        """
        Build a new BuyItem container from a prototype.

        Args:
            prototype (dict or key): An Evennia prototype dict or the key of one
                registered with the system. This is assumed to be a full prototype,
                including having parsed and included parentage.

        Returns:
            BuyItem: A general representation of the original data.

        """

        def _get_attr_value(key, prot, optional=True):
            """
            We want the attribute's value, which is always in the `attrs` field of
            the prototype.

            """
            attr = [tup for tup in prot.get("attrs", ()) if tup[0] == key]
            try:
                return attr[0][1]
            except IndexError:
                if optional:
                    return None
                raise

        if isinstance(prototype_or_key, dict):
            prototype = prototype_or_key
        else:
            # make sure to generate a 'full' prototype with all inheritance applied ('flattened'),
            # otherwise we will not get inherited data when we analyze it.
            prototype = flatten_prototype(search_prototype(key=prototype_or_key))

        if not prototype:
            log_err(f"No valid prototype '{prototype_or_key}' found")
            return None

        try:
            # at this point we should have a full, flattened prototype ready to spawn. It must
            # contain all fields needed for buying
            key = prototype["key"]
            desc = _get_attr_value("desc", prototype, optional=False)
            obj_type = _get_attr_value("obj_type", prototype, optional=False)
            size = _get_attr_value("size", prototype, optional=False)
            use_slot = _get_attr_value("use_slot", prototype, optional=False)
            value = int(_get_attr_value("value", prototype, optional=False)
                        * shopkeeper.upsell_factor)
        except (KeyError, IndexError):
            # not a buyable item
            log_trace("Not a buyable item")
            return None

        return BuyItem(
            key=key,
            desc=desc,
            obj_type=obj_type,
            size=size,
            use_slot=use_slot,
            value=value,
            # optional fields
            uses=_get_attr_value("uses", prototype),
            quality=_get_attr_value("quality", prototype),
            attack_type=_get_attr_value("attack_type", prototype),
            defense_type=_get_attr_value("defense_type", prototype),
            damage_roll=_get_attr_value("damage_roll", prototype),
            # back-reference (don't set obj)
            prototype=prototype,
        )

    def get_sdesc(self):
        """
        Get the short description to show in buy list.

        """
        return self.key

    def get_detail(self):
        """
        Get more info when looking at the item.

        """
        return f"""
    |c{self.key}|n
    {self.desc}

    Slots: {self.size} Used from: {self.use_slot.value}



# Helper functions for building the shop listings and select a ware to buy
def _get_all_wares_to_buy(caller, raw_string, **kwargs):
    """
    This helper is used by `EvMenu.list_node` to build the list of items to buy.

    We rely on `**kwargs` being forwarded from `node_start_buy`, which in turns contains
    the `npc` kwarg pointing to the shopkeeper (`caller` is the one doing the buying).

    """
    shopkeep = kwargs["npc"]
    # items carried by the shopkeep are sellable (these are items already created, such as
    # things sold to the shopkeep earlier). We
    wares = [BuyItem.create_from_obj(obj) for obj in list(shopkeep.contents)] + [
        BuyItem.create_from_prototype(prototype) for prototype in shopkeep.common_ware_prototypes
    ]
    # clean out any ByItems that failed to create for some reason
    wares = [ware for ware in wares if ware]


# shop menu nodes to use for building a Shopkeeper npc


@list_node(_get_all_wares_to_buy, select=_select_ware_to_buy, pagesize=10)
def node_start_buy(caller, raw_string, **kwargs):
    """
    Menu node for the caller to buy items from the shopkeep. This assumes `**kwargs` contains
    a kwarg `npc` referencing the npc/shopkeep being talked to.

    Items available to sell are a combination of items in the shopkeep's inventory and
    the list of `prototypes` stored in the Shopkeep's "common_ware_prototypes` Attribute. In the
    latter case, the properties will be extracted from the prototype when inspecting it (object will
    only spawn when bought).

    """
