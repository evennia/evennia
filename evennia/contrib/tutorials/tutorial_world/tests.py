"""
Test tutorial_world/mob

"""

from mock import patch
from twisted.internet.base import DelayedCall
from twisted.trial.unittest import TestCase as TwistedTestCase

from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.create import create_object
from evennia.utils.test_resources import BaseEvenniaTest, mockdeferLater, mockdelay

from . import mob
from . import objects as tutobjects
from . import rooms as tutrooms


class TestTutorialWorldMob(BaseEvenniaTest):
    def test_mob(self):
        mobobj = create_object(mob.Mob, key="mob")
        self.assertEqual(mobobj.db.is_dead, True)
        mobobj.set_alive()
        self.assertEqual(mobobj.db.is_dead, False)
        mobobj.set_dead()
        self.assertEqual(mobobj.db.is_dead, True)
        mobobj._set_ticker(0, "foo", stop=True)
        # TODO should be expanded with further tests of the modes and damage etc.


#  test tutorial_world/objects


DelayedCall.debug = True


class TestTutorialWorldObjects(TwistedTestCase, BaseEvenniaCommandTest):
    def test_tutorialobj(self):
        obj1 = create_object(tutobjects.TutorialObject, key="tutobj")
        obj1.reset()
        self.assertEqual(obj1.location, obj1.home)

    def test_readable(self):
        readable = create_object(tutobjects.TutorialReadable, key="book", location=self.room1)
        readable.db.readable_text = "Text to read"
        self.call(tutobjects.CmdRead(), "book", "You read book:\n  Text to read", obj=readable)

    def test_climbable(self):
        climbable = create_object(tutobjects.TutorialClimbable, key="tree", location=self.room1)
        self.call(
            tutobjects.CmdClimb(),
            "tree",
            "You climb tree. Having looked around, you climb down again.",
            obj=climbable,
        )
        self.assertEqual(
            self.char1.tags.get("tutorial_climbed_tree", category="tutorial_world"),
            "tutorial_climbed_tree",
        )

    def test_obelisk(self):
        obelisk = create_object(tutobjects.Obelisk, key="obelisk", location=self.room1)
        self.assertEqual(obelisk.return_appearance(self.char1).startswith("|cobelisk("), True)

    @patch("evennia.contrib.tutorials.tutorial_world.objects.delay", mockdelay)
    @patch("evennia.scripts.taskhandler.deferLater", mockdeferLater)
    def test_lightsource(self):
        light = create_object(tutobjects.LightSource, key="torch", location=self.room1)
        self.call(
            tutobjects.CmdLight(),
            "",
            "A torch on the floor flickers and dies.|You light torch.",
            obj=light,
        )
        self.assertFalse(light.pk)

    @patch("evennia.contrib.tutorials.tutorial_world.objects.delay", mockdelay)
    @patch("evennia.scripts.taskhandler.deferLater", mockdeferLater)
    def test_crumblingwall(self):
        wall = create_object(tutobjects.CrumblingWall, key="wall", location=self.room1)
        wall.db.destination = self.room2.dbref
        self.assertFalse(wall.db.button_exposed)
        self.assertFalse(wall.db.exit_open)
        wall.db.root_pos = {"yellow": 0, "green": 0, "red": 0, "blue": 0}
        self.call(
            tutobjects.CmdShiftRoot(),
            "blue root right",
            "You shove the root adorned with small blue flowers to the right.",
            obj=wall,
        )
        self.call(
            tutobjects.CmdShiftRoot(),
            "red root left",
            "You shift the reddish root to the left.",
            obj=wall,
        )
        self.call(
            tutobjects.CmdShiftRoot(),
            "yellow root down",
            "You shove the root adorned with small yellow flowers downwards.",
            obj=wall,
        )
        self.call(
            tutobjects.CmdShiftRoot(),
            "green root up",
            "You shift the weedy green root upwards.|Holding aside the root you "
            "think you notice something behind it ...",
            obj=wall,
        )
        self.call(
            tutobjects.CmdPressButton(),
            "",
            "You move your fingers over the suspicious depression, then gives it a "
            "decisive push. First",
            obj=wall,
        )
        # we patch out the delay, so these are closed immediately
        self.assertFalse(wall.db.button_exposed)
        self.assertFalse(wall.db.exit_open)

    def test_weapon(self):
        weapon = create_object(tutobjects.TutorialWeapon, key="sword", location=self.char1)
        self.call(
            tutobjects.CmdAttack(), "Char", "You stab with sword.", obj=weapon, cmdstring="stab"
        )
        self.call(
            tutobjects.CmdAttack(), "Char", "You slash with sword.", obj=weapon, cmdstring="slash"
        )

    def test_weaponrack(self):
        rack = create_object(tutobjects.TutorialWeaponRack, key="rack", location=self.room1)
        rack.db.available_weapons = ["sword"]
        self.call(tutobjects.CmdGetWeapon(), "", "You find Rusty sword.", obj=rack)


class TestTutorialWorldRooms(BaseEvenniaCommandTest):
    def test_cmdtutorial(self):
        room = create_object(tutrooms.TutorialRoom, key="tutroom")
        self.char1.location = room
        self.call(tutrooms.CmdTutorial(), "", "Sorry, there is no tutorial help available here.")
        self.call(
            tutrooms.CmdTutorialSetDetail(),
            "detail;foo;foo2 = A detail",
            "Detail set: 'detail;foo;foo2': 'A detail'",
            obj=room,
        )
        self.call(tutrooms.CmdTutorialLook(), "", "tutroom(", obj=room)
        self.call(tutrooms.CmdTutorialLook(), "detail", "A detail", obj=room)
        self.call(tutrooms.CmdTutorialLook(), "foo", "A detail", obj=room)
        room.delete()

    def test_weatherroom(self):
        room = create_object(tutrooms.WeatherRoom, key="weatherroom")
        room.update_weather()
        tutrooms.TICKER_HANDLER.remove(
            interval=room.db.interval, callback=room.update_weather, idstring="tutorial"
        )
        room.delete()

    def test_introroom(self):
        room = create_object(tutrooms.IntroRoom, key="introroom")
        room.at_object_receive(self.char1, self.room1)

    def test_bridgeroom(self):
        room = create_object(tutrooms.BridgeRoom, key="bridgeroom")
        room.update_weather()
        self.char1.move_to(room, move_type="teleport")
        self.call(
            tutrooms.CmdBridgeHelp(),
            "",
            "You are trying hard not to fall off the bridge ...",
            obj=room,
        )
        self.call(
            tutrooms.CmdLookBridge(),
            "",
            "bridgeroom\nYou are standing very close to the the bridge's western foundation.",
            obj=room,
        )
        room.at_object_leave(self.char1, self.room1)
        tutrooms.TICKER_HANDLER.remove(
            interval=room.db.interval, callback=room.update_weather, idstring="tutorial"
        )
        room.delete()

    def test_darkroom(self):
        room = create_object(tutrooms.DarkRoom, key="darkroom")
        self.char1.move_to(room, move_type="teleport")
        self.call(tutrooms.CmdDarkHelp(), "", "Can't help you until")

    def test_teleportroom(self):
        create_object(tutrooms.TeleportRoom, key="teleportroom")

    def test_outroroom(self):
        create_object(tutrooms.OutroRoom, key="outroroom")
