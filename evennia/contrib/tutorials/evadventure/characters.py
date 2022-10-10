"""
Character class.

"""

from evennia.objects.objects import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.evform import EvForm
from evennia.utils.evmenu import EvMenu, ask_yes_no
from evennia.utils.evtable import EvTable
from evennia.utils.logger import log_trace
from evennia.utils.utils import lazy_property

from . import rules
from .equipment import EquipmentError, EquipmentHandler
from .quests import EvAdventureQuestHandler
from .utils import get_obj_stats


class LivingMixin:
    """
    Mixin class to use for all living things.

    """

    is_pc = False

    @property
    def hurt_level(self):
        """
        String describing how hurt this character is.
        """
        percent = max(0, min(100, 100 * (self.hp / self.hp_max)))
        if 95 < percent <= 100:
            return "|gPerfect|n"
        elif 80 < percent <= 95:
            return "|gScraped|n"
        elif 60 < percent <= 80:
            return "|GBruised|n"
        elif 45 < percent <= 60:
            return "|yHurt|n"
        elif 30 < percent <= 45:
            return "|yWounded|n"
        elif 15 < percent <= 30:
            return "|rBadly wounded|n"
        elif 1 < percent <= 15:
            return "|rBarely hanging on|n"
        elif percent == 0:
            return "|RCollapsed!|n"

    def heal(self, hp, healer=None):
        """
        Heal by a certain amount of HP.

        """
        damage = self.hp_max - self.hp
        healed = min(damage, hp)
        self.hp += healed

        if healer is self:
            self.msg(f"|gYou heal yourself for {healed} health.|n")
        elif healer:
            self.msg(f"|g{healer.key} heals you for {healed} health.|n")
        else:
            self.msg(f"You are healed for {healed} health.")

    def at_damage(self, damage, attacker=None):
        """
        Called when attacked and taking damage.

        """
        self.hp -= damage

    def at_defeat(self):
        """
        Called when this living thing reaches HP 0.

        """
        # by default, defeat means death
        self.at_death()

    def at_death(self):
        """
        Called when this living thing dies.

        """
        pass

    def at_pay(self, amount):
        """
        Get coins, but no more than we actually have.

        """
        amount = min(amount, self.coins)
        self.coins -= amount
        return amount

    def at_looted(self, looter):
        """
        Called when being looted (after defeat).

        Args:
            looter (Object): The one doing the looting.

        """
        max_steal = rules.dice.roll("1d10")
        stolen = self.at_pay(max_steal)

        looter.coins += stolen

        self.location.msg_contents(
            f"$You(looter) loots $You() for {stolen} coins!",
            from_obj=self,
            mapping={"looter": looter},
        )

    def pre_loot(self, defeated_enemy):
        """
        Called just before looting an enemy.

        Args:
            defeated_enemy (Object): The enemy soon to loot.

        Returns:
            bool: If False, no looting is allowed.

        """
        pass

    def at_do_loot(self, defeated_enemy):
        """
        Called when looting another entity.

        Args:
            defeated_enemy: The thing to loot.

        """
        defeated_enemy.at_looted(self)

    def post_loot(self, defeated_enemy):
        """
        Called just after having looted an enemy.

        Args:
            defeated_enemy (Object): The enemy just looted.

        """
        pass


class EvAdventureCharacter(LivingMixin, DefaultCharacter):
    """
    A Character for use with EvAdventure.

    """

    is_pc = True

    # these are the ability bonuses. Defense is always 10 higher
    strength = AttributeProperty(default=1)
    dexterity = AttributeProperty(default=1)
    constitution = AttributeProperty(default=1)
    intelligence = AttributeProperty(default=1)
    wisdom = AttributeProperty(default=1)
    charisma = AttributeProperty(default=1)

    hp = AttributeProperty(default=4)
    hp_max = AttributeProperty(default=4)
    level = AttributeProperty(default=1)
    coins = AttributeProperty(default=0)  # copper coins

    xp = AttributeProperty(default=0)
    xp_per_level = 1000

    @lazy_property
    def equipment(self):
        """Allows to access equipment like char.equipment.worn"""
        return EquipmentHandler(self)

    @lazy_property
    def quests(self):
        """Access and track quests"""
        return EvAdventureQuestHandler(self)

    @property
    def weapon(self):
        return self.equipment.weapon

    @property
    def armor(self):
        return self.equipment.armor

    def at_pre_object_receive(self, moved_object, source_location, **kwargs):
        """
        Hook called by Evennia before moving an object here. Return False to abort move.

        Args:
            moved_object (Object): Object to move into this one (that is, into inventory).
            source_location (Object): Source location moved from.
            **kwargs: Passed from move operation; the `move_type` is useful; if someone is giving
                us something (`move_type=='give'`) we want to ask first.

        Returns:
            bool: If move should be allowed or not.

        """
        # this will raise EquipmentError if inventory is full
        return self.equipment.validate_slot_usage(moved_object)

    def at_object_receive(self, moved_object, source_location, **kwargs):
        """
        Hook called by Evennia as an object is moved here. We make sure it's added
        to the equipment handler.

        Args:
            moved_object (Object): Object to move into this one (that is, into inventory).
            source_location (Object): Source location moved from.
            **kwargs: Passed from move operation; unused here.

        """
        try:
            self.equipment.add(moved_object)
        except EquipmentError as err:
            log_trace(f"at_object_receive error: {err}")

    def at_pre_object_leave(self, leaving_object, destination, **kwargs):
        """
        Hook called when dropping an item. We don't allow to drop weilded/worn items
        (need to unwield/remove them first). Return False to

        """
        return True

    def at_object_leave(self, moved_object, destination, **kwargs):
        """
        Called just before an object leaves from inside this object

        Args:
            moved_obj (Object): The object leaving
            destination (Object): Where `moved_obj` is going.
            **kwargs (dict): Arbitrary, optional arguments for users
                overriding the call (unused by default).

        """
        self.equipment.remove(moved_object)

    def at_defeat(self):
        """
        This happens when character drops <= 0 HP. For Characters, this means rolling on
        the death table.

        """
        if self.location.allow_death:
            rules.dice.roll_death(self)
        else:
            self.location.msg_contents("|y$You() $conj(yield), beaten and out of the fight.|n")
            self.hp = self.hp_max

    def at_death(self):
        """
        Called when character dies.

        """
        self.location.msg_contents(
            "|r$You() $conj(collapse) in a heap.\nDeath embraces you ...|n",
            from_obj=self,
        )

    def at_pre_loot(self):
        """
        Called before allowing to loot. Return False to block enemy looting.
        """
        # don't allow looting in pvp
        return not self.location.allow_pvp

    def at_looted(self, looter):
        """
        Called when being looted.

        """
        pass

    def add_xp(self, xp):
        """
        Add new XP.

        Args:
            xp (int): The amount of gained XP.

        Returns:
            bool: If a new level was reached or not.

        Notes:
            level 1 -> 2 = 1000 XP
            level 2 -> 3 = 2000 XP etc

        """
        self.xp += xp
        next_level_xp = self.level * self.xp_per_level
        return self.xp >= next_level_xp

    def level_up(self, *abilities):
        """
        Perform the level-up action.

        Args:
            *abilities (str): A set of abilities (like 'strength', 'dexterity' (normally 3)
                to upgrade by 1. Max is usually +10.
        Notes:
            We block increases above a certain value, but we don't raise an error here, that
            will need to be done earlier, when the user selects the ability to increase.

        """

        self.level += 1
        for ability in set(abilities[:3]):
            # limit to max amount allowed, each one unique
            try:
                # set at most to the max bonus
                current_bonus = getattr(self, ability)
                setattr(
                    self,
                    ability,
                    min(10, current_bonus + 1),
                )
            except AttributeError:
                pass

        # update hp
        self.hp_max = max(self.max_hp + 1, rules.dice.roll(f"{self.level}d8"))


# character sheet visualization


_SHEET = """
 +----------------------------------------------------------------------------+
 | Name: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
 +----------------------------------------------------------------------------+
 | STR: x2xxxxx  DEX: x3xxxxx  CON: x4xxxxx  WIS: x5xxxxx  CHA: x6xxxxx       |
 +----------------------------------------------------------------------------+
 | HP: x7xxxxx                                      XP: x8xxxxx  Level: x9x   |
 +----------------------------------------------------------------------------+
 | Desc: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
 | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
 | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
 +----------------------------------------------------------------------------+
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccc1ccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 | cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc |
 +----------------------------------------------------------------------------+
    """


def get_character_sheet(character):
    """
    Generate a character sheet. This is grouped in a class in order to make
    it easier to override the look of the sheet.

    """

    @staticmethod
    def get(character):
        """
        Generate a character sheet from the character's stats.

        """
        equipment = character.equipment.all()
        # divide into chunks of max 10 length (to go into two columns)
        equipment_table = EvTable(
            table=[equipment[i : i + 10] for i in range(0, len(equipment), 10)]
        )
        form = EvForm({"FORMCHAR": "x", "TABLECHAR": "c", "SHEET": _SHEET})
        form.map(
            cells={
                1: character.key,
                2: f"+{character.strength}({character.strength + 10})",
                3: f"+{character.dexterity}({character.dexterity + 10})",
                4: f"+{character.constitution}({character.constitution + 10})",
                5: f"+{character.wisdom}({character.wisdom + 10})",
                6: f"+{character.charisma}({character.charisma + 10})",
                7: f"{character.hp}/{character.hp_max}",
                8: character.xp,
                9: character.level,
                "A": character.db.desc,
            },
            tables={
                1: equipment_table,
            },
        )
        return str(form)
