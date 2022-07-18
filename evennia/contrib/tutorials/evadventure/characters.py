"""
Character class.

"""

from evennia.objects.objects import DefaultCharacter
from evennia.typeclasses.attributes import AttributeProperty
from evennia.utils.utils import lazy_property

from . import rules
from .equipment import EquipmentHandler
from .quests import EvAdventureQuestHandler


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
        else:
            self.msg(f"|g{healer.key} heals you for {healed} health.|n")

    def at_damage(self, damage, attacker=None):
        """
        Called when attacked and taking damage.

        """
        pass

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

    def at_loot(self, looted):
        """
        Called when looting another entity.

        Args:
            looted: The thing to loot.

        """
        looted.get_loot()

    def get_loot(self, looter):
        """
        Called when being looted (after defeat).

        Args:
            looter (Object): The one doing the looting.

        """
        max_steal = rules.dice.roll("1d10")
        owned = self.coin
        stolen = max(max_steal, owned)
        self.coins -= stolen
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

    def post_loot(self, defeated_enemy):
        """
        Called just after having looted an enemy.

        Args:
            defeated_enemy (Object): The enemy just looted.

        """
        pass


class EvAdventureCharacter(LivingMixin, DefaultCharacter):
    """
    A Character for use with EvAdventure. This also works fine for
    monsters and NPCS.

    """

    is_pc = True

    # these are the ability bonuses. Defense is always 10 higher
    strength = AttributeProperty(default=1)
    dexterity = AttributeProperty(default=1)
    constitution = AttributeProperty(default=1)
    intelligence = AttributeProperty(default=1)
    wisdom = AttributeProperty(default=1)
    charisma = AttributeProperty(default=1)

    exploration_speed = AttributeProperty(default=120)
    combat_speed = AttributeProperty(default=40)

    hp = AttributeProperty(default=4)
    hp_max = AttributeProperty(default=4)
    level = AttributeProperty(default=1)
    xp = AttributeProperty(default=0)
    coins = AttributeProperty(default=0)  # copper coins

    morale = AttributeProperty(default=9)  # only used for NPC/monster morale checks

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
            **kwargs: Passed from move operation; unused here.

        Returns:
            bool: If move should be allowed or not.

        """
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
        self.equipment.add(moved_object)

    def at_pre_object_leave(self, leaving_object, destination, **kwargs):
        """
        Hook called when dropping an item. We don't allow to drop weilded/worn items
        (need to unwield/remove them first).

        """
        return self.equipment.can_remove(leaving_object)

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
            if self.hp > 0:
                # still alive, but lost some stats
                self.location.msg_contents(
                    "|y$You() $conj(stagger) back and fall to the ground - alive, "
                    "but unable to move.|n",
                    from_obj=self,
                )
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

    def get_loot(self, looter):
        """
        Called when being looted.

        """
        pass
