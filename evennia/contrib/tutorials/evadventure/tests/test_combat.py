"""
Test EvAdventure combat.

"""

from collections import deque
from unittest.mock import Mock, call, patch

from evennia.utils import create
from evennia.utils.ansi import strip_ansi
from evennia.utils.test_resources import BaseEvenniaTest

from .. import combat
from ..characters import EvAdventureCharacter
from ..enums import Ability, WieldLocation
from ..npcs import EvAdventureMob
from ..objects import EvAdventureConsumable, EvAdventureRunestone, EvAdventureWeapon
from ..rooms import EvAdventureRoom
from .mixins import EvAdventureMixin


class EvAdventureCombatHandlerTest(BaseEvenniaTest):
    """
    Test methods on the turn-based combat handler

    """

    maxDiff = None

    # make sure to mock away all time-keeping elements
    @patch(
        "evennia.contrib.tutorials.evadventure.combat.EvAdventureCombatHandler.interval",
        new=-1,
    )
    @patch(
        "evennia.contrib.tutorials.evadventure.combat.delay",
        new=Mock(return_value=None),
    )
    def setUp(self):
        super().setUp()

        self.location = create.create_object(EvAdventureRoom, key="testroom")
        self.combatant = create.create_object(
            EvAdventureCharacter, key="testchar", location=self.location
        )

        self.location.allow_combat = True
        self.location.allow_death = True

        self.target = create.create_object(
            EvAdventureMob,
            key="testmonster",
            location=self.location,
            attributes=(("is_idle", True),),
        )

        # mock the msg so we can check what they were sent later
        self.combatant.msg = Mock()
        self.target.msg = Mock()

        self.combathandler = combat.get_or_create_combathandler(self.combatant)
        # add target to combat
        self.combathandler.add_combatant(self.target)

    def _get_action(self, action_dict={"key": "nothing"}):
        action_class = self.combathandler.action_classes[action_dict["key"]]
        return action_class(self.combathandler, self.combatant, action_dict)

    def _run_actions(
        self, action_dict, action_dict2={"key": "nothing"}, combatant_msg=None, target_msg=None
    ):
        """
        Helper method to run an action and check so combatant saw the expected message.
        """
        self.combathandler.queue_action(self.combatant, action_dict)
        self.combathandler.queue_action(self.target, action_dict2)
        self.combathandler.execute_full_turn()
        if combatant_msg is not None:
            # this works because we mock combatant.msg in SetUp
            self.combatant.msg.assert_called_with(combatant_msg)
        if target_msg is not None:
            # this works because we mock target.msg in SetUp
            self.combatant.msg.assert_called_with(target_msg)

    def test_combatanthandler_setup(self):
        """Testing all is set up correctly in the combathandler"""

        chandler = self.combathandler
        self.assertEqual(dict(chandler.combatants), {self.combatant: deque(), self.target: deque()})
        self.assertEqual(
            dict(chandler.action_classes),
            {
                "nothing": combat.CombatActionDoNothing,
                "attack": combat.CombatActionAttack,
                "stunt": combat.CombatActionStunt,
                "use": combat.CombatActionUseItem,
                "wield": combat.CombatActionWield,
                "flee": combat.CombatActionFlee,
            },
        )
        self.assertEqual(chandler.flee_timeout, 1)
        self.assertEqual(dict(chandler.advantage_matrix), {})
        self.assertEqual(dict(chandler.disadvantage_matrix), {})
        self.assertEqual(dict(chandler.fleeing_combatants), {})
        self.assertEqual(dict(chandler.defeated_combatants), {})

    def test_combathandler_msg(self):
        """Test sending messages to all in handler"""

        self.location.msg_contents = Mock()

        self.combathandler.msg("test_message")

        self.location.msg_contents.assert_called_with(
            "test_message",
            exclude=[],
            from_obj=None,
            mapping={"testchar": self.combatant, "testmonster": self.target},
        )

    def test_remove_combatant(self):
        """Remove a combatant."""

        self.combathandler.remove_combatant(self.target)

        self.assertEqual(dict(self.combathandler.combatants), {self.combatant: deque()})

    def test_stop_combat(self):
        """Stopping combat, making sure combathandler is deleted."""

        self.combathandler.stop_combat()
        self.assertIsNone(self.combathandler.pk)

    def test_get_sides(self):
        """Getting the sides of combat"""

        combatant2 = create.create_object(
            EvAdventureCharacter, key="testchar2", location=self.location
        )
        target2 = create.create_object(
            EvAdventureMob,
            key="testmonster2",
            location=self.location,
            attributes=(("is_idle", True),),
        )
        self.combathandler.add_combatant(combatant2)
        self.combathandler.add_combatant(target2)

        # allies to combatant
        allies, enemies = self.combathandler.get_sides(self.combatant)
        self.assertEqual((allies, enemies), ([combatant2], [self.target, target2]))

        # allies to monster
        allies, enemies = self.combathandler.get_sides(self.target)
        self.assertEqual((allies, enemies), ([target2], [self.combatant, combatant2]))

    def test_get_combat_summary(self):
        """Test combat summary"""

        # as seen from one side
        result = str(self.combathandler.get_combat_summary(self.combatant))

        self.assertEqual(
            strip_ansi(result),
            " testchar (Perfect)                   vs                testmonster (Perfect) ",
        )

        # as seen from other side
        result = str(self.combathandler.get_combat_summary(self.target))

        self.assertEqual(
            strip_ansi(result),
            " testmonster (Perfect)                 vs                  testchar (Perfect) ",
        )

    def test_queue_and_execute_action(self):
        """Queue actions and execute"""

        donothing = {"key": "nothing"}

        self.combathandler.queue_action(self.combatant, donothing)
        self.assertEqual(
            dict(self.combathandler.combatants),
            {self.combatant: deque([donothing]), self.target: deque()},
        )

        mock_action = Mock()
        self.combathandler.action_classes["nothing"] = Mock(return_value=mock_action)

        self.combathandler.execute_next_action(self.combatant)

        self.combathandler.action_classes["nothing"].assert_called_with(
            self.combathandler, self.combatant, donothing
        )
        mock_action.execute.assert_called_once()

    def test_execute_full_turn(self):
        """Run a full (passive) turn"""

        donothing = {"key": "nothing"}

        self.combathandler.queue_action(self.combatant, donothing)
        self.combathandler.queue_action(self.target, donothing)

        self.combathandler.execute_next_action = Mock()

        self.combathandler.execute_full_turn()

        self.combathandler.execute_next_action.assert_has_calls(
            [call(self.combatant), call(self.target)], any_order=True
        )

    def test_combat_action(self):
        """General tests of action functionality"""

        combatant = self.combatant
        target = self.target

        action = self._get_action({"key": "nothing"})

        self.assertTrue(action.can_use())

        action.give_advantage(combatant, target)
        action.give_disadvantage(combatant, target)

        self.assertTrue(action.has_advantage(combatant, target))
        self.assertTrue(action.has_disadvantage(combatant, target))

        action.lose_advantage(combatant, target)
        action.lose_disadvantage(combatant, target)

        self.assertFalse(action.has_advantage(combatant, target))
        self.assertFalse(action.has_disadvantage(combatant, target))

        action.msg(f"$You() attack $You({target.key}).")
        combatant.msg.assert_called_with(text=("You attack testmonster.", {}), from_obj=combatant)

    def test_action__do_nothing(self):
        """Do nothing"""

        actiondict = {"key": "nothing"}
        self._run_actions(actiondict, actiondict)
        self.assertEqual(self.combathandler.turn, 1)

        self.combatant.msg.assert_not_called()

    @patch("evennia.contrib.tutorials.evadventure.combat.rules.randint")
    def test_attack__miss(self, mock_randint):

        actiondict = {"key": "attack", "target": self.target}

        mock_randint.return_value = 8  # target has default armor 11, so 8+1 str will miss
        self._run_actions(actiondict)
        self.assertEqual(self.target.hp, 4)

    @patch("evennia.contrib.tutorials.evadventure.combat.rules.randint")
    def test_attack__success__still_alive(self, mock_randint):
        actiondict = {"key": "attack", "target": self.target}

        mock_randint.return_value = 11  # 11 + 1 str will hit beat armor 11
        # make sure target survives
        self.target.hp = 20
        self._run_actions(actiondict)
        self.assertEqual(self.target.hp, 9)

    @patch("evennia.contrib.tutorials.evadventure.combat.rules.randint")
    def test_attack__success__kill(self, mock_randint):
        actiondict = {"key": "attack", "target": self.target}

        mock_randint.return_value = 11  # 11 + 1 str will hit beat armor 11
        self._run_actions(actiondict)
        self.assertEqual(self.target.hp, -7)
        # after this the combat is over
        self.assertIsNone(self.combathandler.pk)

    @patch("evennia.contrib.tutorials.evadventure.combat.rules.randint")
    def test_stunt_fail(self, mock_randint):
        action_dict = {
            "key": "stunt",
            "recipient": self.combatant,
            "target": self.target,
            "advantage": True,
            "stunt_type": Ability.STR,
            "defense_type": Ability.DEX,
        }
        mock_randint.return_value = 8  # fails 8+1 dex vs DEX 11 defence
        self._run_actions(action_dict)
        self.assertEqual(self.combathandler.advantage_matrix[self.combatant], {})
        self.assertEqual(self.combathandler.disadvantage_matrix[self.combatant], {})

    @patch("evennia.contrib.tutorials.evadventure.combat.rules.randint")
    def test_stunt_advantage__success(self, mock_randint):
        action_dict = {
            "key": "stunt",
            "recipient": self.combatant,
            "target": self.target,
            "advantage": True,
            "stunt_type": Ability.STR,
            "defense_type": Ability.DEX,
        }
        mock_randint.return_value = 11  #  11+1 dex vs DEX 11 defence is success
        self._run_actions(action_dict)
        self.assertEqual(
            bool(self.combathandler.advantage_matrix[self.combatant][self.target]), True
        )

    @patch("evennia.contrib.tutorials.evadventure.combat.rules.randint")
    def test_stunt_disadvantage__success(self, mock_randint):
        action_dict = {
            "key": "stunt",
            "recipient": self.target,
            "target": self.combatant,
            "advantage": False,
            "stunt_type": Ability.STR,
            "defense_type": Ability.DEX,
        }
        mock_randint.return_value = 11  #  11+1 dex vs DEX 11 defence is success
        self._run_actions(action_dict)
        self.assertEqual(
            bool(self.combathandler.disadvantage_matrix[self.target][self.combatant]), True
        )

    def test_use_item(self):
        """
        Use up a potion during combat.

        """
        item = create.create_object(
            EvAdventureConsumable, key="Healing potion", attributes=[("uses", 2)]
        )

        item.use = Mock()

        action_dict = {
            "key": "use",
            "item": item,
            "target": self.target,
        }

        self.assertEqual(item.uses, 2)
        self._run_actions(action_dict)
        self.assertEqual(item.uses, 1)
        self._run_actions(action_dict)
        self.assertEqual(item.pk, None)  # deleted, it was used up

    def test_swap_wielded_weapon_or_spell(self):
        """
        First draw a weapon (from empty fists), then swap that out to another weapon, then
        swap to a spell rune.

        """
        sword = create.create_object(EvAdventureWeapon, key="sword")
        zweihander = create.create_object(
            EvAdventureWeapon,
            key="zweihander",
            attributes=(("inventory_use_slot", WieldLocation.TWO_HANDS),),
        )
        runestone = create.create_object(EvAdventureRunestone, key="ice rune")

        # check hands are empty
        self.assertEqual(self.combatant.weapon.key, "Empty Fists")
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], None)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], None)

        # swap to sword

        actiondict = {"key": "wield", "item": sword}

        self._run_actions(actiondict)
        self.assertEqual(self.combatant.weapon, sword)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], sword)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], None)

        # swap to zweihander (two-handed sword)
        actiondict["item"] = zweihander

        self._run_actions(actiondict)
        self.assertEqual(self.combatant.weapon, zweihander)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], None)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], zweihander)

        # swap to runestone (also using two hands)
        actiondict["item"] = runestone

        self._run_actions(actiondict)
        self.assertEqual(self.combatant.weapon, runestone)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], None)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], runestone)

        # swap back to normal one-handed sword
        actiondict["item"] = sword

        self._run_actions(actiondict)
        self.assertEqual(self.combatant.weapon, sword)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], sword)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], None)

    def test_flee__success(self):
        """
        Test fleeing twice, leading to leaving combat.

        """

        self.assertEqual(self.combathandler.turn, 0)
        action_dict = {"key": "flee"}

        # first flee records the fleeing state
        self._run_actions(action_dict)
        self.assertEqual(self.combathandler.turn, 1)
        self.assertEqual(self.combathandler.fleeing_combatants[self.combatant], 1)

        self.combatant.msg.assert_called_with(
            text=(
                "You retreat, leaving yourself exposed while doing so (will escape in 1 turn).",
                {},
            ),
            from_obj=self.combatant,
        )
        # Check that enemies have advantage against you now
        action = combat.CombatAction(self.combathandler, self.target, {"key": "nothing"})
        self.assertTrue(action.has_advantage(self.target, self.combatant))

        # second flee should remove combatant
        self._run_actions(action_dict)
        # this ends combat, so combathandler should be gone
        self.assertIsNone(self.combathandler.pk)
