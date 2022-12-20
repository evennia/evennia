"""
EvAdventure commands and cmdsets. We don't need that many stand-alone new
commands since a lot of functionality is managed in menus. These commands
are in additional to normal Evennia commands and should be added
to the CharacterCmdSet

New commands:
    attack/hit <target>[,...]
    inventory
    wield/wear <item>
    unwield/remove <item>
    give <item or coin> to <character>
    talk <npc>

To install, add the `EvAdventureCmdSet` from this module to the default character cmdset:

```python
    # in mygame/commands/default_cmds.py

    from evennia.contrib.tutorials.evadventure.commands import EvAdventureCmdSet  # <---

    # ...

    class CharacterCmdSet(CmdSet):
        def at_cmdset_creation(self):
            # ...
            self.add(EvAdventureCmdSet)   # <-----

```
"""

from evennia import CmdSet, Command, InterruptCommand
from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import inherits_from

from .combat_turnbased import CombatFailure, join_combat
from .enums import WieldLocation
from .equipment import EquipmentError
from .npcs import EvAdventureTalkativeNPC
from .utils import get_obj_stats


class EvAdventureCommand(Command):
    """
    Base EvAdventure command. This is on the form

        command <args>

    where whitespace around the argument(s) are stripped.

    """

    def parse(self):
        self.args = self.args.strip()


class CmdAttackTurnBased(EvAdventureCommand):
    """
    Attack a target or join an existing combat.

    Usage:
      attack <target>
      attack <target>, <target>, ...

    If the target is involved in combat already, you'll join combat with
    the first target you specify. Attacking multiple will draw them all into
    combat.

    This will start/join turn-based, combat, where you have a limited
    time to decide on your next action from a menu of options.

    """

    key = "attack"
    aliases = ("hit",)

    def parse(self):
        super().parse()
        self.targets = [name.strip() for name in self.args.split(",")]

    def func(self):

        # find if

        target_objs = []
        for target in self.targets:
            target_obj = self.caller.search(target)
            if not target_obj:
                # show a warning but don't abort
                continue
            target_objs.append(target_obj)

        if target_objs:
            try:
                join_combat(self.caller, *target_objs, session=self.session)
            except CombatFailure as err:
                self.caller.msg(f"|r{err}|n")
        else:
            self.caller.msg("|rFound noone to attack.|n")


class CmdInventory(EvAdventureCommand):
    """
    View your inventory

    Usage:
      inventory

    """

    key = "inventory"
    aliases = ("i", "inv")

    def func(self):
        loadout = self.caller.equipment.display_loadout()
        backpack = self.caller.equipment.display_backpack()
        slot_usage = self.caller.equipment.display_slot_usage()

        self.caller.msg(f"{loadout}\n{backpack}\nYou use {slot_usage} equipment slots.")


class CmdWieldOrWear(EvAdventureCommand):
    """
    Wield a weapon/shield, or wear a piece of armor or a helmet.

    Usage:
      wield <item>
      wear <item>

    The item will automatically end up in the suitable spot, replacing whatever
    was there previously.

    """

    key = "wield"
    aliases = ("wear",)

    out_txts = {
        WieldLocation.BACKPACK: "You shuffle the position of {key} around in your backpack.",
        WieldLocation.TWO_HANDS: "You hold {key} with both hands.",
        WieldLocation.WEAPON_HAND: "You hold {key} in your strongest hand, ready for action.",
        WieldLocation.SHIELD_HAND: "You hold {key} in your off hand, ready to protect you.",
        WieldLocation.BODY: "You strap {key} on yourself.",
        WieldLocation.HEAD: "You put {key} on your head.",
    }

    def func(self):
        # find the item among those in equipment
        item = self.caller.search(self.args, candidates=self.caller.equipment.all(only_objs=True))
        if not item:
            # An 'item not found' error will already have been reported; we add another line
            # here for clarity.
            self.caller.msg("You must carry the item you want to wield or wear.")
            return

        use_slot = getattr(item, "inventory_use_slot", WieldLocation.BACKPACK)

        # check what is currently in this slot
        current = self.caller.equipment.slots[use_slot]

        if current == item:
            self.caller.msg(f"You are already using {item.key}.")
            return

        # move it to the right slot based on the type of object
        self.caller.equipment.move(item)

        # inform the user of the change (and potential swap)
        if current:
            self.caller.msg(f"Returning {current.key} to the backpack.")
        self.caller.msg(self.out_txts[use_slot].format(key=item.key))


class CmdRemove(EvAdventureCommand):
    """
    Remove a remove a weapon/shield, armor or helmet.

    Usage:
      remove <item>
      unwield <item>
      unwear <item>

    To remove an item from the backpack, use |wdrop|n instead.

    """

    key = "remove"
    aliases = ("unwield", "unwear")

    def func(self):
        caller = self.caller

        # find the item among those in equipment
        item = caller.search(self.args, candidates=caller.equipment.all(only_objs=True))
        if not item:
            # An 'item not found' error will already have been reported
            return

        current_slot = caller.equipment.get_current_slot(item)

        if current_slot is WieldLocation.BACKPACK:
            # we don't allow dropping this way since it may be unexepected by users who forgot just
            # where their item currently is.
            caller.msg(
                f"You already stashed away {item.key} in your backpack. Use 'drop' if "
                "you want to get rid of it."
            )
            return

        caller.equipment.remove(item)
        caller.equipment.add(item)
        caller.msg(f"You stash {item.key} in your backpack.")


# give / accept menu


def _rescind_gift(caller, raw_string, **kwargs):
    """
    Called when giver rescinds their gift in `node_give` below.
    It means they entered 'cancel' on the gift screen.

    """
    # kill the gift menu for the receiver immediately
    receiver = kwargs["receiver"]
    receiver.ndb._evmenu.close_menu()
    receiver.msg("The offer was rescinded.")
    return "node_end"


def node_give(caller, raw_string, **kwargs):
    """
    This will show to the giver until receiver accepts/declines. It allows them
    to rescind their offer.

    The `caller` here is the one giving the item. We also make sure to feed
    the 'item' and 'receiver' into the Evmenu.

    """
    item = kwargs["item"]
    receiver = kwargs["receiver"]
    text = f"""
You are offering {item.key} to {receiver.get_display_name(looker=caller)}.
|wWaiting for them to accept or reject the offer ...|n
""".strip()

    options = {
        "key": ("cancel", "abort"),
        "desc": "Rescind your offer.",
        "goto": (_rescind_gift, kwargs),
    }
    return text, options


def _accept_or_reject_gift(caller, raw_string, **kwargs):
    """
    Called when receiver enters yes/no in `node_receive` below. We first need to
    figure out which.

    """
    item = kwargs["item"]
    giver = kwargs["giver"]
    if raw_string.lower() in ("yes", "y"):
        # they accepted - move the item!
        item = giver.equipment.remove(item)
        if item:
            try:
                # this will also add them to the equipment backpack, if possible
                item.move_to(caller, quiet=True, move_type="give")
            except EquipmentError:
                caller.location.msg_contents(
                    f"$You({giver.key.key}) $conj(try) to give "
                    f"{item.key} to $You({caller.key}), but they can't accept it since their "
                    "inventory is full.",
                    mapping={giver.key: giver, caller.key: caller},
                )
            else:
                caller.location.msg_contents(
                    f"$You({giver.key}) $conj(give) {item.key} to $You({caller.key}), "
                    "and they accepted the offer.",
                    mapping={giver.key: giver, caller.key: caller},
                )
        giver.ndb._evmenu.close_menu()
        return "node_end"


def node_receive(caller, raw_string, **kwargs):
    """
    Will show to the receiver and allow them to accept/decline the offer for
    as long as the giver didn't rescind it.

    The `caller` here is the one receiving the item. We also make sure to feed
    the 'item' and 'giver' into the EvMenu.

    """
    item = kwargs["item"]
    giver = kwargs["giver"]
    text = f"""
{giver.get_display_name()} is offering you {item.key}:

{get_obj_stats(item)}

[Your inventory usage: {caller.equipment.display_slot_usage()}]
|wDo you want to accept the given item? Y/[N]
    """
    options = ({"key": "_default", "goto": (_accept_or_reject_gift, kwargs)},)
    return text, options


def node_end(caller, raw_string, **kwargs):
    return "", None


class CmdGive(EvAdventureCommand):
    """
    Give item or money to another person. Items need to be accepted before
    they change hands. Money changes hands immediately with no wait.

    Usage:
      give <item> to <receiver>
      give <number of coins> [coins] to receiver

    If item name includes ' to ', surround it in quotes.

    Examples:
      give apple to ranger
      give "road to happiness" to sad ranger
      give 10 coins to ranger
      give 12 to ranger

    """

    key = "give"

    def parse(self):
        """
        Parsing is a little more complex for this command.

        """
        super().parse()
        args = self.args
        if " to " not in args:
            self.caller.msg(
                "Usage: give <item> to <recevier>. Specify e.g. '10 coins' to pay money. "
                "Use quotes around the item name it if includes the substring ' to '. "
            )
            raise InterruptCommand

        self.item_name = ""
        self.coins = 0

        # make sure we can use '...' to include items with ' to ' in the name
        if args.startswith('"') and args.count('"') > 1:
            end_ind = args[1:].index('"') + 1
            item_name = args[:end_ind]
            _, receiver_name = args.split(" to ", 1)
        elif args.startswith("'") and args.count("'") > 1:
            end_ind = args[1:].index("'") + 1
            item_name = args[:end_ind]
            _, receiver_name = args.split(" to ", 1)
        else:
            item_name, receiver_name = args.split(" to ", 1)

        # a coin count rather than a normal name
        if " coins" in item_name:
            item_name = item_name[:-6]
        if item_name.isnumeric():
            self.coins = max(0, int(item_name))

        self.item_name = item_name
        self.receiver_name = receiver_name

    def func(self):
        caller = self.caller

        receiver = caller.search(self.receiver_name)
        if not receiver:
            return

        # giving of coins is always accepted

        if self.coins:
            current_coins = caller.coins
            if self.coins > current_coins:
                caller.msg(f"You only have |y{current_coins}|n coins to give.")
                return
            # do transaction
            caller.coins -= self.coins
            receiver.coins += self.coins
            caller.location.msg_contents(
                f"$You() $conj(give) $You({receiver.key}) {self.coins} coins.",
                from_obj=caller,
                mapping={receiver.key: receiver},
            )
            return

        # giving of items require acceptance before it happens

        item = caller.search(self.item_name, candidates=caller.equipment.all(only_objs=True))
        if not item:
            return

        # testing hook
        if not item.at_pre_give(caller, receiver):
            return

        # before we start menus, we must check so either part is not already in a menu,
        # that would be annoying otherwise
        if receiver.ndb._evmenu:
            caller.msg(
                f"{receiver.get_display_name(looker=caller)} seems busy talking to someone else."
            )
            return
        if caller.ndb._evmenu:
            caller.msg("Close the current menu first.")
            return

        # this starts evmenus for both parties
        EvMenu(
            receiver, {"node_receive": node_receive, "node_end": node_end}, item=item, giver=caller
        )
        EvMenu(caller, {"node_give": node_give, "node_end": node_end}, item=item, receiver=receiver)


class CmdTalk(EvAdventureCommand):
    """
    Start a conversations with shop keepers and other NPCs in the world.

    Args:
      talk <npc>

    """

    key = "talk"

    def func(self):
        target = self.caller.search(self.args)
        if not target:
            return

        if not inherits_from(target, EvAdventureTalkativeNPC):
            self.caller.msg(
                f"{target.get_display_name(looker=self.caller)} does not seem very talkative."
            )
            return
        target.at_talk(self.caller)


class EvAdventureCmdSet(CmdSet):
    """
    Groups all commands in one cmdset which can be added in one go to the DefaultCharacter cmdset.

    """

    key = "evadventure"

    def at_cmdset_creation(self):
        self.add(CmdAttackTurnBased())
        self.add(CmdInventory())
        self.add(CmdWieldOrWear())
        self.add(CmdRemove())
        self.add(CmdGive())
        self.add(CmdTalk())
