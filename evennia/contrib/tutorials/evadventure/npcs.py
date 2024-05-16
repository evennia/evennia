"""
EvAdventure NPCs. This includes both friends and enemies, only separated by their AI.

"""

from random import choice

from evennia import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty
from evennia.typeclasses.tags import TagProperty
from evennia.utils.evmenu import EvMenu
from evennia.utils.utils import lazy_property, make_iter

from .ai import AIHandler
from .characters import LivingMixin
from .enums import Ability, WieldLocation
from .objects import get_bare_hands
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

    weapon = AttributeProperty(default=get_bare_hands, autocreate=False)  # instead of inventory
    coins = AttributeProperty(default=1, autocreate=False)  # coin loot

    # if this npc is attacked, everyone with the same tag in the current location will also be
    # pulled into combat.
    group = TagProperty("npcs")

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
        self.tags.add("npcs", category="group")

    def at_attacked(self, attacker, **kwargs):
        """
        Called when being attacked and combat starts.

        """
        pass

    def ai_next_action(self, **kwargs):
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

    # change this to make the mob more or less likely to perform different actions
    combat_probabilities = {
        "hold": 0.0,
        "attack": 0.85,
        "stunt": 0.05,
        "item": 0.0,
        "flee": 0.05,
    }

    @lazy_property
    def ai(self):
        return AIHandler(self)

    def ai_idle(self):
        """
        Do nothing.

        """
        pass

    def ai_combat(self):
        """
        Manage the combat/combat state of the mob.

        """
        if combathandler := self.nbd.combathandler:
            # already in combat
            allies, enemies = combathandler.get_sides(self)
            action = self.ai.random_probability(self.combat_probabilities)

            match action:
                case "hold":
                    combathandler.queue_action({"key": "hold"})
                case "combat":
                    combathandler.queue_action({"key": "attack", "target": random.choice(enemies)})
                case "stunt":
                    # choose a random ally to help
                    combathandler.queue_action(
                        {
                            "key": "stunt",
                            "recipient": random.choice(allies),
                            "advantage": True,
                            "stunt": Ability.STR,
                            "defense": Ability.DEX,
                        }
                    )
                case "item":
                    # use a random item on a random ally
                    target = random.choice(allies)
                    valid_items = [item for item in self.contents if item.at_pre_use(self, target)]
                    combathandler.queue_action(
                        {"key": "item", "item": random.choice(valid_items), "target": target}
                    )
                case "flee":
                    self.ai.set_state("flee")

        elif not (targets := self.ai.get_targets()):
            self.ai.set_state("roam")
        else:
            target = random.choice(targets)
            self.execute_cmd(f"attack {target.key}")

    def ai_roam(self):
        """
        roam, moving randomly to a new room. If a target is found, switch to combat state.

        """
        if targets := self.ai.get_targets():
            self.ai.set_state("combat")
            self.execute_cmd(f"attack {random.choice(targets).key}")
        else:
            exits = self.ai.get_traversable_exits()
            if exits:
                exi = random.choice(exits)
                self.execute_cmd(f"{exi.key}")

    def ai_flee(self):
        """
        Flee from the current room, avoiding going back to the room from which we came. If no exits
        are found, switch to roam state.

        """
        current_room = self.location
        past_room = self.attributes.get("past_room", category="ai_state", default=None)
        exits = self.ai.get_traversable_exits(exclude_destination=past_room)
        if exits:
            self.attributes.set("past_room", current_room, category="ai_state")
            exi = random.choice(exits)
            self.execute_cmd(f"{exi.key}")
        else:
            # if in a dead end, roam will allow for backing out
            self.ai.set_state("roam")

    def at_defeat(self):
        """
        Mobs die right away when defeated, no death-table rolls.

        """
        self.at_death()
