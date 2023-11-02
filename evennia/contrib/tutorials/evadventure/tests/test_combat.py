"""
Test EvAdventure combat.

"""

from unittest.mock import Mock, call, patch

from evennia.utils import create
from evennia.utils.ansi import strip_ansi
from evennia.utils.test_resources import (
    BaseEvenniaTest,
    EvenniaCommandTestMixin,
    EvenniaTestCase,
)

from .. import combat_base, combat_turnbased, combat_twitch
from ..characters import EvAdventureCharacter
from ..enums import Ability, WieldLocation
from ..npcs import EvAdventureMob
from ..objects import EvAdventureConsumable, EvAdventureRunestone, EvAdventureWeapon
from ..rooms import EvAdventureRoom


class _CombatTestBase(EvenniaTestCase):
    """
    Set up common entities for testing combat:

    - `location` (key=testroom)
    - `combatant` (key=testchar)
    - `target` (key=testmonster)`

    We also mock the `.msg` method of both `combatant` and `target` so we can
    see what was sent.

    """

    def setUp(self):
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


class TestEvAdventureCombatBaseHandler(_CombatTestBase):
    """
    Test the base functionality of the base combat handler.

    """

    def setUp(self):
        """This also tests the `get_or_create_combathandler` classfunc"""
        super().setUp()
        self.combathandler = combat_base.EvAdventureCombatBaseHandler.get_or_create_combathandler(
            self.location, key="combathandler"
        )

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

    def test_get_combat_summary(self):
        """Test combat summary"""

        self.combathandler.get_sides = Mock(return_value=([self.combatant], [self.target]))

        # as seen from one side
        result = str(self.combathandler.get_combat_summary(self.combatant))

        self.assertEqual(
            strip_ansi(result),
            " testchar (Perfect)  vs  testmonster (Perfect) ",
        )

        # as seen from other side
        self.combathandler.get_sides = Mock(return_value=([self.target], [self.combatant]))
        result = str(self.combathandler.get_combat_summary(self.target))

        self.assertEqual(
            strip_ansi(result),
            " testmonster (Perfect)  vs  testchar (Perfect) ",
        )


class TestCombatActionsBase(_CombatTestBase):
    """
    A class for testing all subclasses of CombatAction in combat_base.py

    """

    def setUp(self):
        super().setUp()
        self.combathandler = combat_base.EvAdventureCombatBaseHandler.get_or_create_combathandler(
            self.location, key="combathandler"
        )
        # we need to mock all NotImplemented methods
        self.combathandler.get_sides = Mock(return_value=([], [self.target]))
        self.combathandler.give_advantage = Mock()
        self.combathandler.give_disadvantage = Mock()
        self.combathandler.remove_advantage = Mock()
        self.combathandler.remove_disadvantage = Mock()
        self.combathandler.get_advantage = Mock()
        self.combathandler.get_disadvantage = Mock()
        self.combathandler.has_advantage = Mock()
        self.combathandler.has_disadvantage = Mock()
        self.combathandler.queue_action = Mock()

    def test_base_action(self):
        action = combat_base.CombatAction(
            self.combathandler, self.combatant, {"key": "hold", "foo": "bar"}
        )
        self.assertEqual(action.key, "hold")
        self.assertEqual(action.foo, "bar")
        self.assertEqual(action.combathandler, self.combathandler)
        self.assertEqual(action.combatant, self.combatant)

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
    def test_attack__miss(self, mock_randint):
        actiondict = {"key": "attack", "target": self.target}

        mock_randint.return_value = 8  # target has default armor 11, so 8+1 str will miss
        action = combat_base.CombatActionAttack(self.combathandler, self.combatant, actiondict)
        action.execute()
        self.assertEqual(self.target.hp, 4)

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
    def test_attack__success(self, mock_randint):
        actiondict = {"key": "attack", "target": self.target}

        mock_randint.return_value = 11  # 11 + 1 str will hit beat armor 11
        self.target.hp = 20
        action = combat_base.CombatActionAttack(self.combathandler, self.combatant, actiondict)
        action.execute()
        self.assertEqual(self.target.hp, 9)

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
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
        action = combat_base.CombatActionStunt(self.combathandler, self.combatant, action_dict)
        action.execute()
        self.combathandler.give_advantage.assert_not_called()

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
    def test_stunt_advantage__success(self, mock_randint):
        action_dict = {
            "key": "stunt",
            "recipient": self.combatant,
            "target": self.target,
            "advantage": True,
            "stunt_type": Ability.STR,
            "defense_type": Ability.DEX,
        }
        mock_randint.return_value = 11  # 11+1 dex vs DEX 11 defence is success
        action = combat_base.CombatActionStunt(self.combathandler, self.combatant, action_dict)
        action.execute()
        self.combathandler.give_advantage.assert_called_with(self.combatant, self.target)

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
    def test_stunt_disadvantage__success(self, mock_randint):
        action_dict = {
            "key": "stunt",
            "recipient": self.target,
            "target": self.combatant,
            "advantage": False,
            "stunt_type": Ability.STR,
            "defense_type": Ability.DEX,
        }
        mock_randint.return_value = 11  # 11+1 dex vs DEX 11 defence is success
        action = combat_base.CombatActionStunt(self.combathandler, self.combatant, action_dict)
        action.execute()
        self.combathandler.give_disadvantage.assert_called_with(self.target, self.combatant)

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
        action = combat_base.CombatActionUseItem(self.combathandler, self.combatant, action_dict)
        action.execute()
        self.assertEqual(item.uses, 1)
        action.execute()
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
        self.assertEqual(self.combatant.weapon.key, "Bare hands")
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], None)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], None)

        # swap to sword

        actiondict = {"key": "wield", "item": sword}

        action = combat_base.CombatActionWield(self.combathandler, self.combatant, actiondict)
        action.execute()

        self.assertEqual(self.combatant.weapon, sword)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], sword)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], None)

        # swap to zweihander (two-handed sword)
        actiondict["item"] = zweihander

        action = combat_base.CombatActionWield(self.combathandler, self.combatant, actiondict)
        action.execute()

        self.assertEqual(self.combatant.weapon, zweihander)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], None)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], zweihander)

        # swap to runestone (also using two hands)
        actiondict["item"] = runestone

        action = combat_base.CombatActionWield(self.combathandler, self.combatant, actiondict)
        action.execute()

        self.assertEqual(self.combatant.weapon, runestone)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], None)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], runestone)

        # swap back to normal one-handed sword
        actiondict["item"] = sword

        action = combat_base.CombatActionWield(self.combathandler, self.combatant, actiondict)
        action.execute()

        self.assertEqual(self.combatant.weapon, sword)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.WEAPON_HAND], sword)
        self.assertEqual(self.combatant.equipment.slots[WieldLocation.TWO_HANDS], None)


class EvAdventureTurnbasedCombatHandlerTest(_CombatTestBase):
    """
    Test methods on the turn-based combat handler and actions

    """

    maxDiff = None

    # make sure to mock away all time-keeping elements
    @patch(
        (
            "evennia.contrib.tutorials.evadventure."
            "combat_turnbased.EvAdventureTurnbasedCombatHandler.interval"
        ),
        new=-1,
    )
    def setUp(self):
        super().setUp()
        # add target to combat
        self.combathandler = (
            combat_turnbased.EvAdventureTurnbasedCombatHandler.get_or_create_combathandler(
                self.location, key="combathandler"
            )
        )
        self.combathandler.add_combatant(self.combatant)
        self.combathandler.add_combatant(self.target)

    def _get_action(self, action_dict={"key": "hold"}):
        action_class = self.combathandler.action_classes[action_dict["key"]]
        return action_class(self.combathandler, self.combatant, action_dict)

    def _run_actions(
        self, action_dict, action_dict2={"key": "hold"}, combatant_msg=None, target_msg=None
    ):
        """
        Helper method to run an action and check so combatant saw the expected message.
        """
        self.combathandler.queue_action(self.combatant, action_dict)
        self.combathandler.queue_action(self.target, action_dict2)
        self.combathandler.at_repeat()
        if combatant_msg is not None:
            # this works because we mock combatant.msg in SetUp
            self.combatant.msg.assert_called_with(combatant_msg)
        if target_msg is not None:
            # this works because we mock target.msg in SetUp
            self.combatant.msg.assert_called_with(target_msg)

    def test_combatanthandler_setup(self):
        """Testing all is set up correctly in the combathandler"""

        chandler = self.combathandler
        self.assertEqual(
            dict(chandler.combatants),
            {self.combatant: {"key": "hold"}, self.target: {"key": "hold"}},
        )
        self.assertEqual(
            dict(chandler.action_classes),
            {
                "hold": combat_turnbased.CombatActionHold,
                "attack": combat_turnbased.CombatActionAttack,
                "stunt": combat_turnbased.CombatActionStunt,
                "use": combat_turnbased.CombatActionUseItem,
                "wield": combat_turnbased.CombatActionWield,
                "flee": combat_turnbased.CombatActionFlee,
            },
        )
        self.assertEqual(chandler.flee_timeout, 1)
        self.assertEqual(dict(chandler.advantage_matrix), {})
        self.assertEqual(dict(chandler.disadvantage_matrix), {})
        self.assertEqual(dict(chandler.fleeing_combatants), {})
        self.assertEqual(dict(chandler.defeated_combatants), {})

    def test_remove_combatant(self):
        """Remove a combatant."""

        self.combathandler.remove_combatant(self.target)
        self.assertEqual(dict(self.combathandler.combatants), {self.combatant: {"key": "hold"}})

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
        self.assertEqual((allies, enemies), ([self.combatant, combatant2], [self.target, target2]))

        # allies to monster
        allies, enemies = self.combathandler.get_sides(self.target)
        self.assertEqual((allies, enemies), ([self.target, target2], [self.combatant, combatant2]))

    def test_queue_and_execute_action(self):
        """Queue actions and execute"""

        hold = {"key": "hold"}

        self.combathandler.queue_action(self.combatant, hold)
        self.assertEqual(
            dict(self.combathandler.combatants),
            {self.combatant: {"key": "hold"}, self.target: {"key": "hold"}},
        )

        mock_action = Mock()
        self.combathandler.action_classes["hold"] = Mock(return_value=mock_action)

        self.combathandler.execute_next_action(self.combatant)

        self.combathandler.action_classes["hold"].assert_called_with(
            self.combathandler, self.combatant, hold
        )
        mock_action.execute.assert_called_once()

    def test_execute_full_turn(self):
        """Run a full (passive) turn"""

        hold = {"key": "hold"}

        self.combathandler.queue_action(self.combatant, hold)
        self.combathandler.queue_action(self.target, hold)

        self.combathandler.execute_next_action = Mock()

        self.combathandler.at_repeat()

        self.combathandler.execute_next_action.assert_has_calls(
            [call(self.combatant), call(self.target)], any_order=True
        )

    def test_action__action_ticks_turn(self):
        """Test that action execution ticks turns"""

        actiondict = {"key": "hold"}
        self._run_actions(actiondict, actiondict)
        self.assertEqual(self.combathandler.turn, 1)

        self.combatant.msg.assert_not_called()

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
    def test_attack__success__kill(self, mock_randint):
        """Test that the combathandler is deleted once there are no more enemies"""
        actiondict = {"key": "attack", "target": self.target}

        mock_randint.return_value = 11  # 11 + 1 str will hit beat armor 11
        self._run_actions(actiondict)
        self.assertEqual(self.target.hp, -7)
        # after this the combat is over
        self.assertIsNone(self.combathandler.pk)

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
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

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
    def test_stunt_advantage__success(self, mock_randint):
        """Test so the advantage matrix is updated correctly"""
        action_dict = {
            "key": "stunt",
            "recipient": self.combatant,
            "target": self.target,
            "advantage": True,
            "stunt_type": Ability.STR,
            "defense_type": Ability.DEX,
        }
        mock_randint.return_value = 11  # 11+1 dex vs DEX 11 defence is success
        self._run_actions(action_dict)
        self.assertEqual(
            bool(self.combathandler.advantage_matrix[self.combatant][self.target]), True
        )

    @patch("evennia.contrib.tutorials.evadventure.combat_base.rules.randint")
    def test_stunt_disadvantage__success(self, mock_randint):
        """Test so the disadvantage matrix is updated correctly"""
        action_dict = {
            "key": "stunt",
            "recipient": self.target,
            "target": self.combatant,
            "advantage": False,
            "stunt_type": Ability.STR,
            "defense_type": Ability.DEX,
        }
        mock_randint.return_value = 11  # 11+1 dex vs DEX 11 defence is success
        self._run_actions(action_dict)
        self.assertEqual(
            bool(self.combathandler.disadvantage_matrix[self.target][self.combatant]), True
        )

    def test_flee__success(self):
        """
        Test fleeing twice, leading to leaving combat.

        """

        self.assertEqual(self.combathandler.turn, 0)
        action_dict = {"key": "flee", "repeat": True}

        # first flee records the fleeing state
        self.combathandler.flee_timeout = 2  # to make sure
        self._run_actions(action_dict)
        self.assertEqual(self.combathandler.turn, 1)
        self.assertEqual(self.combathandler.fleeing_combatants[self.combatant], 1)

        # action_dict should still be in place due to repeat
        self.assertEqual(self.combathandler.combatants[self.combatant], action_dict)

        self.combatant.msg.assert_called_with(
            text=(
                "You retreat, being exposed to attack while doing so (will escape in 1 turn).",
                {},
            ),
            from_obj=self.combatant,
        )
        # Check that enemies have advantage against you now
        action = combat_turnbased.CombatAction(self.combathandler, self.target, {"key": "hold"})
        self.assertTrue(action.combathandler.has_advantage(self.target, self.combatant))

        # second flee should remove combatant
        self._run_actions(action_dict)
        # this ends combat, so combathandler should be gone
        self.assertIsNone(self.combathandler.pk)


class TestEvAdventureTwitchCombatHandler(EvenniaCommandTestMixin, _CombatTestBase):
    def setUp(self):
        super().setUp()

        # in order to use the EvenniaCommandTestMixin we need these variables defined
        self.char1 = self.combatant
        self.account = None

        self.combatant_combathandler = (
            combat_twitch.EvAdventureCombatTwitchHandler.get_or_create_combathandler(
                self.combatant, key="combathandler"
            )
        )
        self.target_combathandler = (
            combat_twitch.EvAdventureCombatTwitchHandler.get_or_create_combathandler(
                self.target, key="combathandler"
            )
        )

    def test_get_sides(self):
        sides = self.combatant_combathandler.get_sides(self.combatant)
        self.assertEqual(sides, ([self.combatant], [self.target]))

    def test_give_advantage(self):
        self.combatant_combathandler.give_advantage(self.combatant, self.target)
        self.assertTrue(self.combatant_combathandler.advantage_against[self.target])

    def test_give_disadvantage(self):
        self.combatant_combathandler.give_disadvantage(self.combatant, self.target)
        self.assertTrue(self.combatant_combathandler.disadvantage_against[self.target])

    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.repeat", new=Mock(return_value=999))
    def test_queue_action(self):
        """Test so the queue action cleans up tickerhandler correctly"""

        actiondict = {"key": "hold"}
        self.combatant_combathandler.queue_action(actiondict)

        self.assertIsNone(self.combatant_combathandler.current_ticker_ref)

        actiondict = {"key": "hold", "dt": 5}
        self.combatant_combathandler.queue_action(actiondict)
        self.assertEqual(self.combatant_combathandler.current_ticker_ref, 999)

    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.repeat", new=Mock())
    def test_execute_next_action(self):
        self.combatant_combathandler.action_dict = {
            "key": "hold",
            "dummy": "foo",
            "repeat": False,
        }  # to separate from fallback

        self.combatant_combathandler.execute_next_action()
        # should now be back to fallback
        self.assertEqual(
            self.combatant_combathandler.action_dict,
            self.combatant_combathandler.fallback_action_dict,
        )

    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.unrepeat", new=Mock())
    def test_check_stop_combat(self):
        """Test combat-stop functionality"""

        # noone remains (both combatant/target <0 hp
        # get_sides does not include the caller
        self.combatant_combathandler.get_sides = Mock(return_value=([], []))
        self.combatant_combathandler.stop_combat = Mock()

        self.combatant.hp = -1
        self.target.hp = -1

        self.combatant_combathandler.check_stop_combat()
        self.combatant.msg.assert_called_with(
            text=("Noone stands after the dust settles.", {}), from_obj=self.combatant
        )
        self.combatant_combathandler.stop_combat.assert_called()

        # only one side wiped out
        self.combatant.hp = 10
        self.target.hp = -1
        self.combatant_combathandler.get_sides = Mock(return_value=([self.combatant], []))
        self.combatant_combathandler.check_stop_combat()
        self.combatant.msg.assert_called_with(
            text=("The combat is over.", {}), from_obj=self.combatant
        )

    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.repeat", new=Mock())
    def test_hold(self):
        self.call(combat_twitch.CmdHold(), "", "You hold back, doing nothing")
        self.assertEqual(self.combatant_combathandler.action_dict, {"key": "hold"})

    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.repeat", new=Mock())
    def test_attack(self):
        """Test attack action in the twitch combathandler"""
        self.call(combat_twitch.CmdAttack(), self.target.key, "You attack testmonster!")
        self.assertEqual(
            self.combatant_combathandler.action_dict,
            {"key": "attack", "target": self.target, "dt": 3, "repeat": True},
        )

    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.repeat", new=Mock())
    def test_stunt(self):
        boost_result = {
            "key": "stunt",
            "recipient": self.combatant,
            "target": self.target,
            "advantage": True,
            "stunt_type": Ability.STR,
            "defense_type": Ability.STR,
            "dt": 3,
        }
        foil_result = {
            "key": "stunt",
            "recipient": self.target,
            "target": self.combatant,
            "advantage": False,
            "stunt_type": Ability.STR,
            "defense_type": Ability.STR,
            "dt": 3,
        }

        self.call(
            combat_twitch.CmdStunt(),
            f"STR {self.target.key}",
            "You prepare a stunt!",
            cmdstring="boost",
        )
        self.assertEqual(self.combatant_combathandler.action_dict, boost_result)

        self.call(
            combat_twitch.CmdStunt(),
            f"STR me {self.target.key}",
            "You prepare a stunt!",
            cmdstring="boost",
        )
        self.assertEqual(self.combatant_combathandler.action_dict, boost_result)

        self.call(
            combat_twitch.CmdStunt(),
            f"STR {self.target.key}",
            "You prepare a stunt!",
            cmdstring="foil",
        )
        self.assertEqual(self.combatant_combathandler.action_dict, foil_result)

        self.call(
            combat_twitch.CmdStunt(),
            f"STR {self.target.key} me",
            "You prepare a stunt!",
            cmdstring="foil",
        )
        self.assertEqual(self.combatant_combathandler.action_dict, foil_result)

    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.repeat", new=Mock())
    def test_useitem(self):
        item = create.create_object(
            EvAdventureConsumable, key="potion", attributes=[("uses", 2)], location=self.combatant
        )

        self.call(combat_twitch.CmdUseItem(), "potion", "You prepare to use potion!")
        self.assertEqual(
            self.combatant_combathandler.action_dict,
            {"key": "use", "item": item, "target": self.combatant, "dt": 3},
        )

        self.call(
            combat_twitch.CmdUseItem(),
            f"potion on {self.target.key}",
            "You prepare to use potion!",
        )
        self.assertEqual(
            self.combatant_combathandler.action_dict,
            {"key": "use", "item": item, "target": self.target, "dt": 3},
        )

    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.unrepeat", new=Mock())
    @patch("evennia.contrib.tutorials.evadventure.combat_twitch.repeat", new=Mock())
    def test_wield(self):
        sword = create.create_object(EvAdventureWeapon, key="sword", location=self.combatant)
        runestone = create.create_object(
            EvAdventureWeapon, key="runestone", location=self.combatant
        )

        self.call(combat_twitch.CmdWield(), "sword", "You reach for sword!")
        self.assertEqual(
            self.combatant_combathandler.action_dict, {"key": "wield", "item": sword, "dt": 3}
        )

        self.call(combat_twitch.CmdWield(), "runestone", "You reach for runestone!")
        self.assertEqual(
            self.combatant_combathandler.action_dict, {"key": "wield", "item": runestone, "dt": 3}
        )
