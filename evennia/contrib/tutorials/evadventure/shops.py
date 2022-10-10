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

from evennia.prototypes.prototypes import search_prototype
from evennia.prototypes.spawner import flatten_prototype, spawn
from evennia.utils.evmenu import list_node
from evennia.utils.logger import log_err, log_trace

from .enums import ObjType, WieldLocation
from .equipment import EquipmentError

# ------------------------------------ Buying from an NPC


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
            value = int(
                _get_attr_value("value", prototype, optional=False) * shopkeeper.upsell_factor
            )
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

    def __str__(self):
        """
        Get the short description to show in buy list.

        """
        return f"{self.key} [|y{self.value}|n coins]"

    def get_detail(self):
        """
        Get more info when looking at the item.

        """
        return f"""
|c{self.key}|n  Cost: |y{self.value}|n coins

{self.desc}

Slots: |w{self.size}|n Used from: |w{self.use_slot.value}|n
Quality: |w{self.quality}|n Uses: |wself.uses|n
Attacks using: |w{self.attack_type.value}|n against |w{self.defense_type.value}|n
Damage roll: |w{self.damage_roll}"""

    def to_obj(self):
        """
        Convert this into an actual database object that we can trade. This either means
        using the stored `.prototype` to spawn a new instance of the object, or to
        use the `.obj` reference to get the already existing object.

        """
        if self.obj:
            return self.obj
        return spawn(self.prototype)


def _get_or_create_buymap(caller, shopkeep):
    """
    Helper that fetches or creates the mapping of `{"short description": BuyItem, ...}`
    we need for the buy menu. We cache it on the `_evmenu` object on the caller.

    """
    if not caller.ndb._evmenu.buymap:
        # buymap not in cache - build it and store in memory on _evmenu object - this way
        # it will be removed automatically when the menu closes. We will need to reset this
        # when the shopkeep buys new things.
        # items carried by the shopkeep are sellable (these are items already created, such as
        # things sold to the shopkeep earlier). We
        obj_wares = [BuyItem.create_from_obj(obj) for obj in list(shopkeep.contents)]
        prototype_wares = [
            BuyItem.create_from_prototype(prototype)
            for prototype in shopkeep.common_ware_prototypes
        ]
        wares = obj_wares + prototype_wares
        caller.ndb._evmenu.buymap = {str(ware): ware for ware in wares if ware}

    return caller.ndb._evmenu.buymap


# Helper functions for building the shop listings and select a ware to buy
def _get_all_wares_to_buy(caller, raw_string, **kwargs):
    """
    This helper is used by `EvMenu.list_node` to build the list of items to buy.

    We rely on `**kwargs` being forwarded from `node_start_buy`, which in turns contains
    the `npc` kwarg pointing to the shopkeeper (`caller` is the one doing the buying).

    """
    shopkeep = kwargs["npc"]
    buymap = _get_or_create_buymap(caller, shopkeep)
    return [ware_desc for ware_desc in buymap]


def _select_ware_to_buy(caller, selected_ware_desc, **kwargs):
    """
    This helper is used by `EvMenu.list_node` to operate on what the user selected.
    We return `item` in the kwargs to the `node_select_buy` node.

    """
    shopkeep = kwargs["npc"]
    buymap = _get_or_create_buymap(caller, shopkeep)
    kwargs["item"] = buymap[selected_ware_desc]

    return "node_confirm_buy", kwargs


def _back_to_previous_node(caller, raw_string, **kwargs):
    """
    Back to previous node is achieved by returning a node of None.

    """
    return None, kwargs


def _buy_ware(caller, raw_string, **kwargs):
    """
    Complete the purchase of a ware. At this point the money is deducted
    and the item is either spawned from a prototype or simply moved from
    the sellers inventory to that of the buyer.

    We will have kwargs `item` and `npc` passed along to refer to the BuyItem we bought
    and the shopkeep selling it.

    """
    item = kwargs["item"]  # a BuyItem instance
    shopkeep = kwargs["npc"]

    # exchange money
    caller.coins -= item.value
    shopkeep += item.value

    # get the item - if not enough room, dump it on the ground
    obj = item.to_obj()
    try:
        caller.equipment.add(obj)
    except EquipmentError as err:
        obj.location = caller.location
        caller.msg(err)
        caller.msg(f"|w{obj.key} ends up on the ground.|n")

    caller.msg("|gYou bought |w{obj.key}|g for |y{item.value}|g coins.|n")


@list_node(_get_all_wares_to_buy, select=_select_ware_to_buy, pagesize=40)
def node_start_buy(caller, raw_string, **kwargs):
    """
    Menu node for the caller to buy items from the shopkeep. This assumes `**kwargs` contains
    a kwarg `npc` referencing the npc/shopkeep being talked to.

    Items available to sell are a combination of items in the shopkeep's inventory and
    the list of `prototypes` stored in the Shopkeep's "common_ware_prototypes` Attribute. In the
    latter case, the properties will be extracted from the prototype when inspecting it (object will
    only spawn when bought).

    """
    coins = caller.coins
    used_slots = caller.equipment.count_slots()
    max_slots = caller.equipment.max_slots

    text = (
        f'"Seeing something you like?" [you have |y{coins}|n coins, '
        f"using |b{used_slots}/{max_slots}|n slots]"
    )
    # this will be in addition to the options generated by the list-node
    extra_options = [{"key": ("[c]ancel", "b", "c", "cancel"), "goto": "node_start"}]

    return text, extra_options


def node_confirm_buy(caller, raw_string, **kwargs):
    """
    Menu node reached when a user selects an item in the buy menu. The `item` passed
    along in `**kwargs` is the selected item (see `_select_ware_to_buy`, where this is injected).

    """
    # this was injected in _select_ware_to_buy. This is an BuyItem instance.
    item = kwargs["item"]

    coins = caller.coins
    used_slots = caller.equipment.count_slots()
    max_slots = caller.equipment.max_slots

    text = item.get_detail()
    text += f"\n\n[You have |y{coins}|n coins] and are using |b{used_slots}/{max_slots}|n slots]"

    options = []

    if caller.coins >= item.value and item.size <= (max_slots - used_slots):
        options.append({"desc": f"Buy [{item.value} coins]", "goto": (_buy_ware, kwargs)})
    options.append({"desc": "Cancel", "goto": (_back_to_previous_node, kwargs)})

    return text, options


# node tree to inject for buying things
node_tree_buy = {"node_start_buy": node_start_buy, "node_confirm_buy": node_confirm_buy}


# ------------------------------------------------- Selling to an NPC


def _get_or_create_sellmap(self, caller, shopkeep):
    if not caller.ndb._evmenu.sellmap:
        # no sellmap, build one anew

        sellmap = {}
        for obj, wieldlocation in caller.equipment.all():
            key = obj.key
            value = int(obj.value * shopkeep.miser_factor)
            if value > 0 and obj.obj_type is not ObjType.QUEST:
                sellmap[f"|w{key}|n [{wieldlocation.value}] - sell price |y{value}|n coins"] = (
                    obj,
                    value,
                )
        caller.ndb._evmenu.sellmap = sellmap

    sellmap = caller.ndb._evmenu.sellmap

    return sellmap


def _get_all_wares_to_sell(caller, raw_string, **kwargs):
    """
    Get all wares available to sell from caller's inventory. We need to build a
    mapping between the descriptors and the items.

    """
    shopkeep = kwargs["npc"]
    sellmap = _get_or_create_sellmap(caller, shopkeep)
    return [ware_desc for ware_desc in sellmap]


def _sell_ware(caller, raw_string, **kwargs):
    """
    Complete the sale of a ware. This is were money is gained and the item is removed.

    We will have kwargs `item`, `value` and `npc` passed along to refer to the inventory item we
    sold, its (adjusted) sales cost and the shopkeep buying it.

    """
    item = kwargs["item"]
    value = kwargs["value"]
    shopkeep = kwargs["npc"]

    # move item to shopkeep
    obj = caller.equipment.remove(item)
    obj.location = shopkeep

    # exchange money - shopkeep always have money to pay, so we don't deduct from them
    caller.coins += value

    caller.msg("|gYou sold |w{obj.key}|g for |y{value}|g coins.|n")


def _select_ware_to_sell(caller, selected_ware_desc, **kwargs):
    """
    Selected one ware to sell. Figure out which one it is using the sellmap.
    Store the result as "item" kwarg.

    """
    shopkeep = kwargs["npc"]
    sellmap = _get_or_create_sellmap(caller, shopkeep)
    kwargs["item"], kwargs["value"] = sellmap[selected_ware_desc]

    return "node_examine_sell", kwargs


@list_node(_get_all_wares_to_sell, select=_select_ware_to_sell, pagesize=20)
def node_start_sell(caller, raw_string, **kwargs):
    """
    The start-level node for selling items from the user's inventory. This assumes
    `**kwargs` contains a kwarg `npc` referencing the npc/shopkeep being talked to.

    Items available to sell are all items in the player's equipment handler, including
    things in their hands.

    """
    coins = caller.coins
    used_slots = caller.equipment.count_slots()
    max_slots = caller.equipment.max_slots

    text = (
        f'"Anything you want to sell?" [you have |y{coins}|n coins, '
        f"using |b{used_slots}/{max_slots}|n slots]"
    )
    # this will be in addition to the options generated by the list-node
    extra_options = [{"key": ("[c]ancel", "b", "c", "cancel"), "goto": "node_start"}]

    return text, extra_options


def node_confirm_sell(caller, raw_string, **kwargs):
    """
    In this node we confirm the sell by first investigating the item we are about to sell.

    We have `item` and `value` available in kwargs here, added by `_select_ware_to_sell` earler.

    """
    item = kwargs["item"]
    value = kwargs["value"]

    coins = caller.coins
    used_slots = caller.equipment.count_slots()
    max_slots = caller.equipment.max_slots

    text = caller.equipment.get_obj_stats(item)
    text += f"\n\n[You have |y{coins}|n coins] and are using |b{used_slots}/{max_slots}|n slots]"

    options = (
        {"desc": f"Sell [{value} coins]", "goto": (_sell_ware, kwargs)},
        {"desc": "Cancel", "goto": (_back_to_previous_node, kwargs)},
    )

    return text, options


# node tree to inject for selling things
node_tree_sell = {"node_start_sell": node_start_sell, "node_confirm_sell": node_confirm_sell}


# Full shopkeep node tree - inject into ShopKeep NPC menu to add buy/sell submenus
node_tree_shopkeep = {**node_tree_buy, **node_tree_sell}
