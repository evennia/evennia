"""
EvAdventure NPCs. This includes both friends and enemies, only separated by their AI.

"""
from random import choice

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import make_iter

from .characters import LivingMixin
from .enums import Ability, WieldLocation
from .objects import WeaponEmptyHand
from .rules import dice


class EvAdventureNPC(LivingMixin, DefaultCharacter):
    """
    This is the base class for all non-player entities, including monsters. These
    generally don't advance in level but uses a simplified, abstract measure of how
    dangerous or competent they are - the 'hit dice' (HD).

    HD indicates how much health they have and how hard they hit. In _Knave_, HD also
    defaults to being the bonus for all abilities. HP is 4 x Hit die (this can then be
    customized per-entity of course).

    Morale is set explicitly per-NPC, usually between 7 and 9.

    Monsters don't use equipment in the way PCs do, instead they have a fixed armor
    value, and their Abilities are dynamically generated from the HD (hit_dice).

    If wanting monsters or NPCs that can level and work the same as PCs, base them off the
    EvAdventureCharacter class instead.

    The weapon of the npc is stored as an Attribute instead of implementing a full
    inventory/equipment system. This means that the normal inventory can be used for
    non-combat purposes (or for loot to get when killing an enemy).

    """

    is_pc = False

    hit_dice = AttributeProperty(default=1, autocreate=False)
    armor = AttributeProperty(default=1, autocreate=False)  # +10 to get armor defense
    morale = AttributeProperty(default=9, autocreate=False)
    hp_multiplier = AttributeProperty(default=4, autocreate=False)  # 4 default in Knave
    hp = AttributeProperty(default=None, autocreate=False)  # internal tracking, use .hp property
    allegiance = AttributeProperty(default=Ability.ALLEGIANCE_HOSTILE, autocreate=False)

    is_idle = AttributeProperty(default=False, autocreate=False)

    weapon = AttributeProperty(default=WeaponEmptyHand, autocreate=False)  # instead of inventory
    coins = AttributeProperty(default=1, autocreate=False)  # coin loot

    @property
    def strength(self):
        return self.hit_dice

    @property
    def dexterity(self):
        return self.hit_dice

    @property
    def constitution(self):
        return self.hit_dice

    @property
    def intelligence(self):
        return self.hit_dice

    @property
    def wisdom(self):
        return self.hit_dice

    @property
    def charisma(self):
        return self.hit_dice

    @property
    def hp_max(self):
        return self.hit_dice * self.hp_multiplier

    def at_object_creation(self):
        """
        Start with max health.

        """
        self.hp = self.hp_max

    def ai_combat_next_action(self):
        """
        The combat engine should ask this method in order to
        get the next action the npc should perform in combat.

        """
        pass


class EvAdventureTalkativeNPC(EvAdventureNPC):
    """
    Talkative NPCs can be addressed by `talk [to] <npc>`. This opens a chat menu with
    communication options. The menu is created with the npc and we override the .create
    to allow passing in the menu nodes.

    """

    menudata = AttributeProperty(dict(), autocreate=False)
    menu_kwargs = AttributeProperty(dict(), autocreate=False)
    # text shown when greeting at the start of a conversation. If this is an
    # iterable, a random reply will be chosen by the menu
    hi_text = AttributeProperty("Hi!", autocreate=False)

    def at_damage(self, damage, attacker=None):
        """
        Talkative NPCs are generally immortal (we don't deduct HP here by default)."

        """
        attacker.msg(f'{self.key} dodges the damage and shouts "|wHey! What are you doing?|n"')

    @classmethod
    def create(cls, key, account=None, **kwargs):
        """
        Overriding the creation of the NPC, allowing some extra `**kwargs`.

        Args:
            key (str): Name of the new object.
            account (Account, optional): Account to attribute this object to.

        Keyword Args:
            description (str): Brief description for this object (same as default Evennia)
            ip (str): IP address of creator (for object auditing) (same as default Evennia).
            menudata (dict or str): The `menudata` argument to `EvMenu`. This is either a dict of
                `{"nodename": <node_callable>,...}` or the python-path to a module containing
                such nodes (see EvMenu docs). This will be used to generate the chat menu
                chat menu for the character that talks to the NPC (which means the `at_talk` hook
                is called (by our custom `talk` command).
            menu_kwargs (dict): This will be passed as `**kwargs` into `EvMenu` when it
                is created. Make sure this dict can be pickled to an Attribute.

        Returns:
            tuple: `(new_character, errors)`. On error, the `new_character` is `None` and
            `errors` is a `list` of error strings (an empty list otherwise).


        """
        menudata = kwargs.pop("menudata", None)
        menu_kwargs = kwargs.pop("menu_kwargs", {})

        # since this is a @classmethod we can't use super() here
        new_object, errors = EvAdventureNPC.create(
            key, account=account, attributes=(("menudata", menudata), ("menu_kwargs", menu_kwargs))
        )

        return new_object, errors

    def at_talk(self, talker, startnode="node_start", session=None, **kwargs):
        """
        Called by the `talk` command when another entity addresses us.

        Args:
            talker (Object): The one talking to us.
            startnode (str, optional): Allows to start in a different location in the menu tree.
                The given node must exist in the tree.
            session (Session, optional): The talker's current session, allows for routing
                correctly in multi-session modes.
            **kwargs: This will be passed into the `EvMenu` creation and appended and `menu_kwargs`
                given to the NPC at creation.

        Notes:
            We pass `npc=self` into the EvMenu for easy back-reference. This will appear in the
            `**kwargs` of the start node.

        """
        menu_kwargs = {**self.menu_kwargs, **kwargs}
        EvMenu(talker, self.menudata, startnode=startnode, session=session, npc=self, **menu_kwargs)


def node_start(caller, raw_string, **kwargs):
    """
    This is the intended start menu node for the Talkative NPC interface. It will
    use on-npc Attributes to build its message and will also pick its options
    based on nodes named `node_start_*` are available in the node tree.

    """
    # we presume a back-reference to the npc this is added when the menu is created
    npc = kwargs["npc"]

    # grab a (possibly random) welcome text
    text = choice(make_iter(npc.hi_text))

    # determine options based on `node_start_*` nodes available
    toplevel_node_keys = [
        node_key for node_key in caller.ndb._evmenu._menutree if node_key.startswith("node_start_")
    ]
    options = []
    for node_key in toplevel_node_keys:
        option_name = node_key[11:].replace("_", " ").capitalized()

        # we let the menu number the choices, so we don't use key here
        options.append({"desc": option_name, "goto": node_key})

    return text, options


class EvAdventureQuestGiver(EvAdventureTalkativeNPC):
    """
    An NPC that acts as a dispenser of quests.

    """


class EvAdventureShopKeeper(EvAdventureTalkativeNPC):
    """
    ShopKeeper NPC.

    """

    # how much extra the shopkeeper adds on top of the item cost
    upsell_factor = AttributeProperty(1.0, autocreate=False)
    # how much of the raw cost the shopkeep is willing to pay when buying from character
    miser_factor = AttributeProperty(0.5, autocreate=False)
    # prototypes of common wares
    common_ware_prototypes = AttributeProperty([], autocreate=False)

    def at_damage(self, damage, attacker=None):
        """
        Immortal - we don't deduct any damage here.

        """
        attacker.msg(
            f"{self.key} brushes off the hit and shouts "
            '"|wHey! This is not the way to get a discount!|n"'
        )


class EvAdventureMob(EvAdventureNPC):
    """
    Mob (mobile) NPC; this is usually an enemy.

    """

    # chance (%) that this enemy will loot you when defeating you
    loot_chance = AttributeProperty(75, autocreate=False)

    def ai_combat_next_action(self, combathandler):
        """
        Called to get the next action in combat.

        Args:
            combathandler (EvAdventureCombatHandler): The currently active combathandler.

        Returns:
            tuple: A tuple `(str, tuple, dict)`, being the `action_key`, and the `*args` and
            `**kwargs` for that action. The action-key is that of a CombatAction available to the
            combatant in the current combat handler.

        """
        from .combat_turnbased import CombatActionAttack, CombatActionDoNothing

        if self.is_idle:
            # mob just stands around
            return CombatActionDoNothing.key, (), {}

        target = choice(combathandler.get_enemy_targets(self))

        # simply randomly decide what action to take
        action = choice(
            (
                CombatActionAttack,
                CombatActionDoNothing,
            )
        )
        return action.key, (target,), {}

    def at_defeat(self):
        """
        Mobs die right away when defeated, no death-table rolls.

        """
        self.at_death()

    def at_do_loot(self, looted):
        """
        Called when mob gets to loot a PC.

        """
        if dice.roll("1d100") > self.loot_chance:
            # don't loot
            return

        if looted.coins:
            # looter prefer coins
            loot = dice.roll("1d20")
            if looted.coins < loot:
                self.location.msg_location(
                    "$You(looter) loots $You() for all coin!",
                    from_obj=looted,
                    mapping={"looter": self},
                )
            else:
                self.location.msg_location(
                    "$You(looter) loots $You() for |y{loot}|n coins!",
                    from_obj=looted,
                    mapping={"looter": self},
                )
        elif hasattr(looted, "equipment"):
            # go through backpack, first usable, then wieldable, wearable items
            # and finally stuff wielded
            stealable = looted.equipment.get_usable_objects_from_backpack()
            if not stealable:
                stealable = looted.equipment.get_wieldable_objects_from_backpack()
            if not stealable:
                stealable = looted.equipment.get_wearable_objects_from_backpack()
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.SHIELD_HAND]]
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.HEAD]]
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.ARMOR]]
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.WEAPON_HAND]]
            if not stealable:
                stealable = [looted.equipment.slots[WieldLocation.TWO_HANDS]]

            stolen = looted.equipment.remove(choice(stealable))
            stolen.location = self

            self.location.msg_location(
                "$You(looter) steals {stolen.key} from $You()!",
                from_obj=looted,
                mapping={"looter": self},
            )
