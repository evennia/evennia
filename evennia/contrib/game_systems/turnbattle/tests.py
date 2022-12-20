"""
Turnbattle tests.

"""

from mock import MagicMock, patch

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.objects.objects import DefaultRoom
from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaTest

from . import tb_basic, tb_equip, tb_items, tb_magic, tb_range


class TestTurnBattleBasicCmd(BaseEvenniaCommandTest):

    # Test basic combat commands
    def test_turnbattlecmd(self):
        self.call(tb_basic.CmdFight(), "", "You can't start a fight if you've been defeated!")
        self.call(tb_basic.CmdAttack(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_basic.CmdPass(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_basic.CmdDisengage(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_basic.CmdRest(), "", "Char rests to recover HP.")


class TestTurnBattleEquipCmd(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.testweapon = create_object(tb_equip.TBEWeapon, key="test weapon")
        self.testarmor = create_object(tb_equip.TBEArmor, key="test armor")
        self.testweapon.move_to(self.char1)
        self.testarmor.move_to(self.char1)

    # Test equipment commands
    def test_turnbattleequipcmd(self):
        # Start with equip module specific commands.
        self.call(tb_equip.CmdWield(), "weapon", "Char wields test weapon.")
        self.call(tb_equip.CmdUnwield(), "", "Char lowers test weapon.")
        self.call(tb_equip.CmdDon(), "armor", "Char dons test armor.")
        self.call(tb_equip.CmdDoff(), "", "Char removes test armor.")
        # Also test the commands that are the same in the basic module
        self.call(tb_equip.CmdFight(), "", "You can't start a fight if you've been defeated!")
        self.call(tb_equip.CmdAttack(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_equip.CmdPass(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_equip.CmdDisengage(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_equip.CmdRest(), "", "Char rests to recover HP.")


class TestTurnBattleRangeCmd(BaseEvenniaCommandTest):
    # Test range commands
    def test_turnbattlerangecmd(self):
        # Start with range module specific commands.
        self.call(tb_range.CmdShoot(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_range.CmdApproach(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_range.CmdWithdraw(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_range.CmdStatus(), "", "HP Remaining: 100 / 100")
        # Also test the commands that are the same in the basic module
        self.call(tb_range.CmdFight(), "", "There's nobody here to fight!")
        self.call(tb_range.CmdAttack(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_range.CmdPass(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_range.CmdDisengage(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_range.CmdRest(), "", "Char rests to recover HP.")


class TestTurnBattleItemsCmd(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.testitem = create_object(key="test item")
        self.testitem.move_to(self.char1)

    # Test item commands
    def test_turnbattleitemcmd(self):
        self.call(tb_items.CmdUse(), "item", "'Test item' is not a usable item.")
        # Also test the commands that are the same in the basic module
        self.call(tb_items.CmdFight(), "", "You can't start a fight if you've been defeated!")
        self.call(tb_items.CmdAttack(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_items.CmdPass(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_items.CmdDisengage(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_items.CmdRest(), "", "Char rests to recover HP.")


class TestTurnBattleMagicCmd(BaseEvenniaCommandTest):

    # Test magic commands
    def test_turnbattlemagiccmd(self):
        self.call(tb_magic.CmdStatus(), "", "You have 100 / 100 HP and 20 / 20 MP.")
        self.call(tb_magic.CmdLearnSpell(), "test spell", "There is no spell with that name.")
        self.call(tb_magic.CmdCast(), "", "Usage: cast <spell name> = <target>, <target2>")
        # Also test the commands that are the same in the basic module
        self.call(tb_magic.CmdFight(), "", "There's nobody here to fight!")
        self.call(tb_magic.CmdAttack(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_magic.CmdPass(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_magic.CmdDisengage(), "", "You can only do that in combat. (see: help fight)")
        self.call(tb_magic.CmdRest(), "", "Char rests to recover HP and MP.")


class TestTurnBattleBasicFunc(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.testroom = create_object(DefaultRoom, key="Test Room")
        self.attacker = create_object(
            tb_basic.TBBasicCharacter, key="Attacker", location=self.testroom
        )
        self.defender = create_object(
            tb_basic.TBBasicCharacter, key="Defender", location=self.testroom
        )
        self.joiner = create_object(tb_basic.TBBasicCharacter, key="Joiner", location=None)

    def tearDown(self):
        super().tearDown()
        self.turnhandler.stop()
        self.attacker.delete()
        self.defender.delete()
        self.joiner.delete()
        self.testroom.delete()

    # Test combat functions
    def test_tbbasicfunc(self):
        # Initiative roll
        initiative = tb_basic.COMBAT_RULES.roll_init(self.attacker)
        self.assertTrue(initiative >= 0 and initiative <= 1000)
        # Attack roll
        attack_roll = tb_basic.COMBAT_RULES.get_attack(self.attacker, self.defender)
        self.assertTrue(attack_roll >= 0 and attack_roll <= 100)
        # Defense roll
        defense_roll = tb_basic.COMBAT_RULES.get_defense(self.attacker, self.defender)
        self.assertTrue(defense_roll == 50)
        # Damage roll
        damage_roll = tb_basic.COMBAT_RULES.get_damage(self.attacker, self.defender)
        self.assertTrue(damage_roll >= 15 and damage_roll <= 25)
        # Apply damage
        self.defender.db.hp = 10
        tb_basic.COMBAT_RULES.apply_damage(self.defender, 3)
        self.assertTrue(self.defender.db.hp == 7)
        # Resolve attack
        self.defender.db.hp = 40
        tb_basic.COMBAT_RULES.resolve_attack(
            self.attacker, self.defender, attack_value=20, defense_value=10
        )
        self.assertTrue(self.defender.db.hp < 40)
        # Combat cleanup
        self.attacker.db.Combat_attribute = True
        tb_basic.COMBAT_RULES.combat_cleanup(self.attacker)
        self.assertFalse(self.attacker.db.combat_attribute)
        # Is in combat
        self.assertFalse(tb_basic.COMBAT_RULES.is_in_combat(self.attacker))
        # Set up turn handler script for further tests
        self.attacker.location.scripts.add(tb_basic.TBBasicTurnHandler)
        self.turnhandler = self.attacker.db.combat_turnHandler
        self.assertTrue(self.attacker.db.combat_turnHandler)
        # Set the turn handler's interval very high to keep it from repeating during tests.
        self.turnhandler.interval = 10000
        # Force turn order
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        # Test is turn
        self.assertTrue(tb_basic.COMBAT_RULES.is_turn(self.attacker))
        # Spend actions
        self.attacker.db.Combat_ActionsLeft = 1
        tb_basic.COMBAT_RULES.spend_action(self.attacker, 1, action_name="Test")
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "Test")
        # Initialize for combat
        self.attacker.db.Combat_ActionsLeft = 983
        self.turnhandler.initialize_for_combat(self.attacker)
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "null")
        # Start turn
        self.defender.db.Combat_ActionsLeft = 0
        self.turnhandler.start_turn(self.defender)
        self.assertTrue(self.defender.db.Combat_ActionsLeft == 1)
        # Next turn
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.next_turn()
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Turn end check
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.attacker.db.Combat_ActionsLeft = 0
        self.turnhandler.turn_end_check(self.attacker)
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Join fight
        self.joiner.location = self.testroom
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.join_fight(self.joiner)
        self.assertTrue(self.turnhandler.db.turn == 1)
        self.assertTrue(self.turnhandler.db.fighters == [self.joiner, self.attacker, self.defender])


class TestTurnBattleEquipFunc(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.testroom = create_object(DefaultRoom, key="Test Room")
        self.attacker = create_object(
            tb_equip.TBEquipCharacter, key="Attacker", location=self.testroom
        )
        self.defender = create_object(
            tb_equip.TBEquipCharacter, key="Defender", location=self.testroom
        )
        self.joiner = create_object(tb_equip.TBEquipCharacter, key="Joiner", location=None)

    def tearDown(self):
        super().tearDown()
        self.turnhandler.stop()
        self.attacker.delete()
        self.defender.delete()
        self.joiner.delete()
        self.testroom.delete()

    # Test the combat functions in tb_equip too. They work mostly the same.
    def test_tbequipfunc(self):
        # Initiative roll
        initiative = tb_equip.COMBAT_RULES.roll_init(self.attacker)
        self.assertTrue(initiative >= 0 and initiative <= 1000)
        # Attack roll
        attack_roll = tb_equip.COMBAT_RULES.get_attack(self.attacker, self.defender)
        self.assertTrue(attack_roll >= -50 and attack_roll <= 150)
        # Defense roll
        defense_roll = tb_equip.COMBAT_RULES.get_defense(self.attacker, self.defender)
        self.assertTrue(defense_roll == 50)
        # Damage roll
        damage_roll = tb_equip.COMBAT_RULES.get_damage(self.attacker, self.defender)
        self.assertTrue(damage_roll >= 0 and damage_roll <= 50)
        # Apply damage
        self.defender.db.hp = 10
        tb_equip.COMBAT_RULES.apply_damage(self.defender, 3)
        self.assertTrue(self.defender.db.hp == 7)
        # Resolve attack
        self.defender.db.hp = 40
        tb_equip.COMBAT_RULES.resolve_attack(
            self.attacker, self.defender, attack_value=20, defense_value=10
        )
        self.assertTrue(self.defender.db.hp < 40)
        # Combat cleanup
        self.attacker.db.Combat_attribute = True
        tb_equip.COMBAT_RULES.combat_cleanup(self.attacker)
        self.assertFalse(self.attacker.db.combat_attribute)
        # Is in combat
        self.assertFalse(tb_equip.COMBAT_RULES.is_in_combat(self.attacker))
        # Set up turn handler script for further tests
        self.attacker.location.scripts.add(tb_equip.TBEquipTurnHandler)
        self.turnhandler = self.attacker.db.combat_turnHandler
        self.assertTrue(self.attacker.db.combat_turnHandler)
        # Set the turn handler's interval very high to keep it from repeating during tests.
        self.turnhandler.interval = 10000
        # Force turn order
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        # Test is turn
        self.assertTrue(tb_equip.COMBAT_RULES.is_turn(self.attacker))
        # Spend actions
        self.attacker.db.Combat_ActionsLeft = 1
        tb_equip.COMBAT_RULES.spend_action(self.attacker, 1, action_name="Test")
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "Test")
        # Initialize for combat
        self.attacker.db.Combat_ActionsLeft = 983
        self.turnhandler.initialize_for_combat(self.attacker)
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "null")
        # Start turn
        self.defender.db.Combat_ActionsLeft = 0
        self.turnhandler.start_turn(self.defender)
        self.assertTrue(self.defender.db.Combat_ActionsLeft == 1)
        # Next turn
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.next_turn()
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Turn end check
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.attacker.db.Combat_ActionsLeft = 0
        self.turnhandler.turn_end_check(self.attacker)
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Join fight
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.join_fight(self.joiner)
        self.assertTrue(self.turnhandler.db.turn == 1)
        self.assertTrue(self.turnhandler.db.fighters == [self.joiner, self.attacker, self.defender])


class TestTurnBattleRangeFunc(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.testroom = create_object(DefaultRoom, key="Test Room")
        self.attacker = create_object(
            tb_range.TBRangeCharacter, key="Attacker", location=self.testroom
        )
        self.defender = create_object(
            tb_range.TBRangeCharacter, key="Defender", location=self.testroom
        )
        self.joiner = create_object(tb_range.TBRangeCharacter, key="Joiner", location=self.testroom)

    def tearDown(self):
        super().tearDown()
        self.turnhandler.stop()
        self.attacker.delete()
        self.defender.delete()
        self.joiner.delete()
        self.testroom.delete()

    # Test combat functions in tb_range too.
    def test_tbrangefunc(self):
        # Initiative roll
        initiative = tb_range.COMBAT_RULES.roll_init(self.attacker)
        self.assertTrue(initiative >= 0 and initiative <= 1000)
        # Attack roll
        attack_roll = tb_range.COMBAT_RULES.get_attack(
            self.attacker, self.defender, attack_type="test"
        )
        self.assertTrue(attack_roll >= 0 and attack_roll <= 100)
        # Defense roll
        defense_roll = tb_range.COMBAT_RULES.get_defense(
            self.attacker, self.defender, attack_type="test"
        )
        self.assertTrue(defense_roll == 50)
        # Damage roll
        damage_roll = tb_range.COMBAT_RULES.get_damage(self.attacker, self.defender)
        self.assertTrue(damage_roll >= 15 and damage_roll <= 25)
        # Apply damage
        self.defender.db.hp = 10
        tb_range.COMBAT_RULES.apply_damage(self.defender, 3)
        self.assertTrue(self.defender.db.hp == 7)
        # Resolve attack
        self.defender.db.hp = 40
        tb_range.COMBAT_RULES.resolve_attack(
            self.attacker, self.defender, attack_type="test", attack_value=20, defense_value=10
        )
        self.assertTrue(self.defender.db.hp < 40)
        # Combat cleanup
        self.attacker.db.Combat_attribute = True
        tb_range.COMBAT_RULES.combat_cleanup(self.attacker)
        self.assertFalse(self.attacker.db.combat_attribute)
        # Is in combat
        self.assertFalse(tb_range.COMBAT_RULES.is_in_combat(self.attacker))
        # Set up turn handler script for further tests
        self.attacker.location.scripts.add(tb_range.TBRangeTurnHandler)
        self.turnhandler = self.attacker.db.combat_turnHandler
        self.assertTrue(self.attacker.db.combat_turnHandler)
        # Set the turn handler's interval very high to keep it from repeating during tests.
        self.turnhandler.interval = 10000
        # Force turn order
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        # Test is turn
        self.assertTrue(tb_range.COMBAT_RULES.is_turn(self.attacker))
        # Spend actions
        self.attacker.db.Combat_ActionsLeft = 1
        tb_range.COMBAT_RULES.spend_action(self.attacker, 1, action_name="Test")
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "Test")
        # Initialize for combat
        self.attacker.db.Combat_ActionsLeft = 983
        self.turnhandler.initialize_for_combat(self.attacker)
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "null")
        # Set up ranges again, since initialize_for_combat clears them
        self.attacker.db.combat_range = {}
        self.attacker.db.combat_range[self.attacker] = 0
        self.attacker.db.combat_range[self.defender] = 1
        self.defender.db.combat_range = {}
        self.defender.db.combat_range[self.defender] = 0
        self.defender.db.combat_range[self.attacker] = 1
        # Start turn
        self.defender.db.Combat_ActionsLeft = 0
        self.turnhandler.start_turn(self.defender)
        self.assertEqual(self.defender.db.Combat_ActionsLeft, 2)
        # Next turn
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.next_turn()
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Turn end check
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.attacker.db.Combat_ActionsLeft = 0
        self.turnhandler.turn_end_check(self.attacker)
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Join fight
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.join_fight(self.joiner)
        self.assertTrue(self.turnhandler.db.turn == 1)
        self.assertTrue(self.turnhandler.db.fighters == [self.joiner, self.attacker, self.defender])
        # Now, test for approach/withdraw functions
        self.assertTrue(tb_range.COMBAT_RULES.get_range(self.attacker, self.defender) == 1)
        # Approach
        tb_range.COMBAT_RULES.approach(self.attacker, self.defender)
        self.assertTrue(tb_range.COMBAT_RULES.get_range(self.attacker, self.defender) == 0)
        # Withdraw
        tb_range.COMBAT_RULES.withdraw(self.attacker, self.defender)
        self.assertTrue(tb_range.COMBAT_RULES.get_range(self.attacker, self.defender) == 1)


class TestTurnBattleItemsFunc(BaseEvenniaTest):
    @patch("evennia.contrib.game_systems.turnbattle.tb_items.tickerhandler", new=MagicMock())
    def setUp(self):
        super().setUp()
        self.testroom = create_object(DefaultRoom, key="Test Room")
        self.attacker = create_object(
            tb_items.TBItemsCharacter, key="Attacker", location=self.testroom
        )
        self.defender = create_object(
            tb_items.TBItemsCharacter, key="Defender", location=self.testroom
        )
        self.joiner = create_object(tb_items.TBItemsCharacter, key="Joiner", location=self.testroom)
        self.user = create_object(tb_items.TBItemsCharacter, key="User", location=self.testroom)
        self.test_healpotion = create_object(key="healing potion")
        self.test_healpotion.db.item_func = "heal"
        self.test_healpotion.db.item_uses = 3

    def tearDown(self):
        super().tearDown()
        self.turnhandler.stop()
        self.attacker.delete()
        self.defender.delete()
        self.joiner.delete()
        self.user.delete()
        self.testroom.delete()

    # Test functions in tb_items.
    def test_tbitemsfunc(self):
        # Initiative roll
        initiative = tb_items.COMBAT_RULES.roll_init(self.attacker)
        self.assertTrue(initiative >= 0 and initiative <= 1000)
        # Attack roll
        attack_roll = tb_items.COMBAT_RULES.get_attack(self.attacker, self.defender)
        self.assertTrue(attack_roll >= 0 and attack_roll <= 100)
        # Defense roll
        defense_roll = tb_items.COMBAT_RULES.get_defense(self.attacker, self.defender)
        self.assertTrue(defense_roll == 50)
        # Damage roll
        damage_roll = tb_items.COMBAT_RULES.get_damage(self.attacker, self.defender)
        self.assertTrue(damage_roll >= 15 and damage_roll <= 25)
        # Apply damage
        self.defender.db.hp = 10
        tb_items.COMBAT_RULES.apply_damage(self.defender, 3)
        self.assertTrue(self.defender.db.hp == 7)
        # Resolve attack
        self.defender.db.hp = 40
        tb_items.COMBAT_RULES.resolve_attack(
            self.attacker, self.defender, attack_value=20, defense_value=10
        )
        self.assertTrue(self.defender.db.hp < 40)
        # Combat cleanup
        self.attacker.db.Combat_attribute = True
        tb_items.COMBAT_RULES.combat_cleanup(self.attacker)
        self.assertFalse(self.attacker.db.combat_attribute)
        # Is in combat
        self.assertFalse(tb_items.COMBAT_RULES.is_in_combat(self.attacker))
        # Set up turn handler script for further tests
        self.attacker.location.scripts.add(tb_items.TBItemsTurnHandler)
        self.turnhandler = self.attacker.db.combat_turnHandler
        self.assertTrue(self.attacker.db.combat_turnHandler)
        # Set the turn handler's interval very high to keep it from repeating during tests.
        self.turnhandler.interval = 10000
        # Force turn order
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        # Test is turn
        self.assertTrue(tb_items.COMBAT_RULES.is_turn(self.attacker))
        # Spend actions
        self.attacker.db.Combat_ActionsLeft = 1
        tb_items.COMBAT_RULES.spend_action(self.attacker, 1, action_name="Test")
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "Test")
        # Initialize for combat
        self.attacker.db.Combat_ActionsLeft = 983
        self.turnhandler.initialize_for_combat(self.attacker)
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "null")
        # Start turn
        self.defender.db.Combat_ActionsLeft = 0
        self.turnhandler.start_turn(self.defender)
        self.assertTrue(self.defender.db.Combat_ActionsLeft == 1)
        # Next turn
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.next_turn()
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Turn end check
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.attacker.db.Combat_ActionsLeft = 0
        self.turnhandler.turn_end_check(self.attacker)
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Join fight
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.join_fight(self.joiner)
        self.assertTrue(self.turnhandler.db.turn == 1)
        self.assertTrue(self.turnhandler.db.fighters == [self.joiner, self.attacker, self.defender])
        # Now time to test item stuff.
        # Spend item use
        tb_items.COMBAT_RULES.spend_item_use(self.test_healpotion, self.user)
        self.assertTrue(self.test_healpotion.db.item_uses == 2)
        # Use item
        self.user.db.hp = 2
        tb_items.COMBAT_RULES.use_item(self.user, self.test_healpotion, self.user)
        self.assertTrue(self.user.db.hp > 2)
        # Add contition
        tb_items.COMBAT_RULES.add_condition(self.user, self.user, "Test", 5)
        self.assertTrue(self.user.db.conditions == {"Test": [5, self.user]})
        # Condition tickdown
        tb_items.COMBAT_RULES.condition_tickdown(self.user, self.user)
        self.assertEqual(self.user.db.conditions, {"Test": [4, self.user]})
        # Test item functions now!
        # Item heal
        self.user.db.hp = 2
        tb_items.COMBAT_RULES.itemfunc_heal(self.test_healpotion, self.user, self.user)
        # Item add condition
        self.user.db.conditions = {}
        tb_items.COMBAT_RULES.itemfunc_add_condition(self.test_healpotion, self.user, self.user)
        self.assertTrue(self.user.db.conditions == {"Regeneration": [5, self.user]})
        # Item cure condition
        self.user.db.conditions = {"Poisoned": [5, self.user]}
        tb_items.COMBAT_RULES.itemfunc_cure_condition(self.test_healpotion, self.user, self.user)
        self.assertTrue(self.user.db.conditions == {})


class TestTurnBattleMagicFunc(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.testroom = create_object(DefaultRoom, key="Test Room")
        self.attacker = create_object(
            tb_magic.TBMagicCharacter, key="Attacker", location=self.testroom
        )
        self.defender = create_object(
            tb_magic.TBMagicCharacter, key="Defender", location=self.testroom
        )
        self.joiner = create_object(tb_magic.TBMagicCharacter, key="Joiner", location=self.testroom)

    def tearDown(self):
        super().tearDown()
        self.turnhandler.stop()
        self.attacker.delete()
        self.defender.delete()
        self.joiner.delete()
        self.testroom.delete()

    # Test combat functions in tb_magic.
    def test_tbbasicfunc(self):
        # Initiative roll
        initiative = tb_magic.COMBAT_RULES.roll_init(self.attacker)
        self.assertTrue(initiative >= 0 and initiative <= 1000)
        # Attack roll
        attack_roll = tb_magic.COMBAT_RULES.get_attack(self.attacker, self.defender)
        self.assertTrue(attack_roll >= 0 and attack_roll <= 100)
        # Defense roll
        defense_roll = tb_magic.COMBAT_RULES.get_defense(self.attacker, self.defender)
        self.assertTrue(defense_roll == 50)
        # Damage roll
        damage_roll = tb_magic.COMBAT_RULES.get_damage(self.attacker, self.defender)
        self.assertTrue(damage_roll >= 15 and damage_roll <= 25)
        # Apply damage
        self.defender.db.hp = 10
        tb_magic.COMBAT_RULES.apply_damage(self.defender, 3)
        self.assertTrue(self.defender.db.hp == 7)
        # Resolve attack
        self.defender.db.hp = 40
        tb_magic.COMBAT_RULES.resolve_attack(
            self.attacker, self.defender, attack_value=20, defense_value=10
        )
        self.assertTrue(self.defender.db.hp < 40)
        # Combat cleanup
        self.attacker.db.Combat_attribute = True
        tb_magic.COMBAT_RULES.combat_cleanup(self.attacker)
        self.assertFalse(self.attacker.db.combat_attribute)
        # Is in combat
        self.assertFalse(tb_magic.COMBAT_RULES.is_in_combat(self.attacker))
        # Set up turn handler script for further tests
        self.attacker.location.scripts.add(tb_magic.TBMagicTurnHandler)
        self.turnhandler = self.attacker.db.combat_turnHandler
        self.assertTrue(self.attacker.db.combat_turnHandler)
        # Set the turn handler's interval very high to keep it from repeating during tests.
        self.turnhandler.interval = 10000
        # Force turn order
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        # Test is turn
        self.assertTrue(tb_magic.COMBAT_RULES.is_turn(self.attacker))
        # Spend actions
        self.attacker.db.Combat_ActionsLeft = 1
        tb_magic.COMBAT_RULES.spend_action(self.attacker, 1, action_name="Test")
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "Test")
        # Initialize for combat
        self.attacker.db.Combat_ActionsLeft = 983
        self.turnhandler.initialize_for_combat(self.attacker)
        self.assertTrue(self.attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(self.attacker.db.Combat_LastAction == "null")
        # Start turn
        self.defender.db.Combat_ActionsLeft = 0
        self.turnhandler.start_turn(self.defender)
        self.assertTrue(self.defender.db.Combat_ActionsLeft == 1)
        # Next turn
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.next_turn()
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Turn end check
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.attacker.db.Combat_ActionsLeft = 0
        self.turnhandler.turn_end_check(self.attacker)
        self.assertTrue(self.turnhandler.db.turn == 1)
        # Join fight
        self.turnhandler.db.fighters = [self.attacker, self.defender]
        self.turnhandler.db.turn = 0
        self.turnhandler.join_fight(self.joiner)
        self.assertTrue(self.turnhandler.db.turn == 1)
        self.assertTrue(self.turnhandler.db.fighters == [self.joiner, self.attacker, self.defender])
