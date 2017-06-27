# -*- coding: utf-8 -*-
"""
Testing suite for contrib folder

"""

import datetime
from evennia.commands.default.tests import CommandTest
from evennia.utils.test_resources import EvenniaTest
from mock import Mock, patch

# Testing of rplanguage module

from evennia.contrib import rplanguage

mtrans = {"testing": "1", "is": "2", "a": "3", "human": "4"}
atrans = ["An", "automated", "advantageous", "repeatable", "faster"]

text = "Automated testing is advantageous for a number of reasons:" \
       "tests may be executed Continuously without the need for human " \
       "intervention, They are easily repeatable, and often faster."


class TestLanguage(EvenniaTest):
    def setUp(self):
        super(TestLanguage, self).setUp()
        rplanguage.add_language(key="testlang",
                                word_length_variance=1,
                                noun_prefix="bara",
                                noun_postfix="'y",
                                manual_translations=mtrans,
                                auto_translations=atrans,
                                force=True)

    def tearDown(self):
        super(TestLanguage, self).tearDown()
        rplanguage._LANGUAGE_HANDLER.delete()
        rplanguage._LANGUAGE_HANDLER = None

    def test_obfuscate_language(self):
        result0 = rplanguage.obfuscate_language(text, level=0.0, language="testlang")
        self.assertEqual(result0, text)
        result1 = rplanguage.obfuscate_language(text, level=1.0, language="testlang")
        result2 = rplanguage.obfuscate_language(text, level=1.0, language="testlang")
        self.assertNotEqual(result1, text)
        result1, result2 = result1.split(), result2.split()
        self.assertEqual(result1[:4], result2[:4])
        self.assertEqual(result1[1], "1")
        self.assertEqual(result1[2], "2")
        self.assertEqual(result2[-1], result2[-1])

    def test_available_languages(self):
        self.assertEqual(rplanguage.available_languages(), ["testlang"])

    def test_obfuscate_whisper(self):
        self.assertEqual(rplanguage.obfuscate_whisper(text, level=0.0), text)
        assert (rplanguage.obfuscate_whisper(text, level=0.1).startswith(
            '-utom-t-d t-sting is -dv-nt-g-ous for - numb-r of r--sons:t-sts m-y b- -x-cut-d Continuously'))
        assert(rplanguage.obfuscate_whisper(text, level=0.5).startswith(
            '--------- --s---- -s -----------s f-- - ------ -f ---s--s:--s-s '))
        self.assertEqual(rplanguage.obfuscate_whisper(text, level=1.0), "...")

# Testing of emoting / sdesc / recog system

from evennia import create_object
from evennia.contrib import rpsystem

sdesc0 = "A nice sender of emotes"
sdesc1 = "The first receiver of emotes."
sdesc2 = "Another nice colliding sdesc-guy for tests"
recog01 = "Mr Receiver"
recog02 = "Mr Receiver2"
recog10 = "Mr Sender"
emote = "With a flair, /me looks at /first and /colliding sdesc-guy. She says \"This is a test.\""


class TestRPSystem(EvenniaTest):
    def setUp(self):
        super(TestRPSystem, self).setUp()
        self.room = create_object(rpsystem.ContribRPRoom, key="Location")
        self.speaker = create_object(rpsystem.ContribRPCharacter, key="Sender", location=self.room)
        self.receiver1 = create_object(rpsystem.ContribRPCharacter, key="Receiver1", location=self.room)
        self.receiver2 = create_object(rpsystem.ContribRPCharacter, key="Receiver2", location=self.room)

    def test_ordered_permutation_regex(self):
        self.assertEqual(
            rpsystem.ordered_permutation_regex(sdesc0),
            '/[0-9]*-*A\\ nice\\ sender\\ of\\ emotes(?=\\W|$)+|/[0-9]*-*nice\\ sender\\ '
            'of\\ emotes(?=\\W|$)+|/[0-9]*-*A\\ nice\\ sender\\ of(?=\\W|$)+|/[0-9]*-*sender\\ '
            'of\\ emotes(?=\\W|$)+|/[0-9]*-*nice\\ sender\\ of(?=\\W|$)+|/[0-9]*-*A\\ nice\\ '
            'sender(?=\\W|$)+|/[0-9]*-*nice\\ sender(?=\\W|$)+|/[0-9]*-*of\\ emotes(?=\\W|$)+'
            '|/[0-9]*-*sender\\ of(?=\\W|$)+|/[0-9]*-*A\\ nice(?=\\W|$)+|/[0-9]*-*sender(?=\\W|$)+'
            '|/[0-9]*-*emotes(?=\\W|$)+|/[0-9]*-*nice(?=\\W|$)+|/[0-9]*-*of(?=\\W|$)+|/[0-9]*-*A(?=\\W|$)+')

    def test_sdesc_handler(self):
        self.speaker.sdesc.add(sdesc0)
        self.assertEqual(self.speaker.sdesc.get(), sdesc0)
        self.speaker.sdesc.add("This is {#324} ignored")
        self.assertEqual(self.speaker.sdesc.get(), "This is 324 ignored")
        self.speaker.sdesc.add("Testing three words")
        self.assertEqual(
            self.speaker.sdesc.get_regex_tuple()[0].pattern,
            '/[0-9]*-*Testing\\ three\\ words(?=\\W|$)+|/[0-9]*-*Testing\\ '
            'three(?=\\W|$)+|/[0-9]*-*three\\ words(?=\\W|$)+|/[0-9]*-*Testing'
            '(?=\\W|$)+|/[0-9]*-*three(?=\\W|$)+|/[0-9]*-*words(?=\\W|$)+')

    def test_recog_handler(self):
        self.speaker.sdesc.add(sdesc0)
        self.receiver1.sdesc.add(sdesc1)
        self.speaker.recog.add(self.receiver1, recog01)
        self.speaker.recog.add(self.receiver2, recog02)
        self.assertEqual(self.speaker.recog.get(self.receiver1), recog01)
        self.assertEqual(self.speaker.recog.get(self.receiver2), recog02)
        self.assertEqual(
            self.speaker.recog.get_regex_tuple(self.receiver1)[0].pattern,
            '/[0-9]*-*Mr\\ Receiver(?=\\W|$)+|/[0-9]*-*Receiver(?=\\W|$)+|/[0-9]*-*Mr(?=\\W|$)+')
        self.speaker.recog.remove(self.receiver1)
        self.assertEqual(self.speaker.recog.get(self.receiver1), sdesc1)

    def test_parse_language(self):
        self.assertEqual(
            rpsystem.parse_language(self.speaker, emote),
            ('With a flair, /me looks at /first and /colliding sdesc-guy. She says {##0}',
             {'##0': (None, '"This is a test."')}))

    def parse_sdescs_and_recogs(self):
        speaker = self.speaker
        speaker.sdesc.add(sdesc0)
        self.receiver1.sdesc.add(sdesc1)
        self.receiver2.sdesc.add(sdesc2)
        candidates = (self.receiver1, self.receiver2)
        result = ('With a flair, {#9} looks at {#10} and {#11}. She says "This is a test."',
                  {'#11': 'Another nice colliding sdesc-guy for tests', '#10':
                      'The first receiver of emotes.', '#9': 'A nice sender of emotes'})
        self.assertEqual(rpsystem.parse_sdescs_and_recogs(speaker, candidates, emote), result)
        self.speaker.recog.add(self.receiver1, recog01)
        self.assertEqual(rpsystem.parse_sdescs_and_recogs(speaker, candidates, emote), result)

    def test_send_emote(self):
        speaker = self.speaker
        receiver1 = self.receiver1
        receiver2 = self.receiver2
        receivers = [speaker, receiver1, receiver2]
        speaker.sdesc.add(sdesc0)
        receiver1.sdesc.add(sdesc1)
        receiver2.sdesc.add(sdesc2)
        speaker.msg = lambda text, **kwargs: setattr(self, "out0", text)
        receiver1.msg = lambda text, **kwargs: setattr(self, "out1", text)
        receiver2.msg = lambda text, **kwargs: setattr(self, "out2", text)
        rpsystem.send_emote(speaker, receivers, emote)
        self.assertEqual(
            self.out0, 'With a flair, |bSender|n looks at |bThe first receiver of emotes.|n '
            'and |bAnother nice colliding sdesc-guy for tests|n. She says |w"This is a test."|n')
        self.assertEqual(
            self.out1, 'With a flair, |bA nice sender of emotes|n looks at |bReceiver1|n and '
            '|bAnother nice colliding sdesc-guy for tests|n. She says |w"This is a test."|n')
        self.assertEqual(
            self.out2, 'With a flair, |bA nice sender of emotes|n looks at |bThe first '
            'receiver of emotes.|n and |bReceiver2|n. She says |w"This is a test."|n')

    def test_rpsearch(self):
        self.speaker.sdesc.add(sdesc0)
        self.receiver1.sdesc.add(sdesc1)
        self.receiver2.sdesc.add(sdesc2)
        self.speaker.msg = lambda text, **kwargs: setattr(self, "out0", text)
        self.assertEqual(self.speaker.search("receiver of emotes"), self.receiver1)
        self.assertEqual(self.speaker.search("colliding"), self.receiver2)


# Testing of ExtendedRoom contrib

from django.conf import settings
from evennia.contrib import extended_room
from evennia import gametime
from evennia.objects.objects import DefaultRoom

class ForceUTCDatetime(datetime.datetime):

    """Force UTC datetime."""

    @classmethod
    def fromtimestamp(cls, timestamp):
        """Force fromtimestamp to run with naive datetimes."""
        return datetime.datetime.utcfromtimestamp(timestamp)

@patch('evennia.contrib.extended_room.datetime.datetime', ForceUTCDatetime)
class TestExtendedRoom(CommandTest):
    room_typeclass = extended_room.ExtendedRoom
    DETAIL_DESC = "A test detail."
    SPRING_DESC = "A spring description."
    OLD_DESC = "Old description."
    settings.TIME_ZONE = "UTC"

    def setUp(self):
        super(TestExtendedRoom, self).setUp()
        self.room1.ndb.last_timeslot = "afternoon"
        self.room1.ndb.last_season = "winter"
        self.room1.db.details = {'testdetail': self.DETAIL_DESC}
        self.room1.db.spring_desc = self.SPRING_DESC
        self.room1.db.desc = self.OLD_DESC
        # mock gametime to return April 9, 2064, at 21:06 (spring evening)
        gametime.gametime = Mock(return_value=2975000766)

    def test_return_appearance(self):
        # get the appearance of a non-extended room for contrast purposes
        old_desc = DefaultRoom.return_appearance(self.room1, self.char1)
        # the new appearance should be the old one, but with the desc switched
        self.assertEqual(old_desc.replace(self.OLD_DESC, self.SPRING_DESC),
                        self.room1.return_appearance(self.char1))
        self.assertEqual("spring", self.room1.ndb.last_season)
        self.assertEqual("evening", self.room1.ndb.last_timeslot)

    def test_return_detail(self):
        self.assertEqual(self.DETAIL_DESC, self.room1.return_detail("testdetail"))

    def test_cmdextendedlook(self):
        self.call(extended_room.CmdExtendedLook(), "here", "Room(#1)\n%s" % self.SPRING_DESC)
        self.call(extended_room.CmdExtendedLook(), "testdetail", self.DETAIL_DESC)
        self.call(extended_room.CmdExtendedLook(), "nonexistent", "Could not find 'nonexistent'.")

    def test_cmdextendeddesc(self):
        self.call(extended_room.CmdExtendedDesc(), "", "Details on Room", cmdstring="@detail")
        self.call(extended_room.CmdExtendedDesc(), "thingie = newdetail with spaces",
                  "Set Detail thingie to 'newdetail with spaces'.", cmdstring="@detail")
        self.call(extended_room.CmdExtendedDesc(), "thingie", "Detail 'thingie' on Room:\n", cmdstring="@detail")
        self.call(extended_room.CmdExtendedDesc(), "/del thingie",
                  "Detail thingie deleted, if it existed.", cmdstring="@detail")
        self.call(extended_room.CmdExtendedDesc(), "thingie", "Detail 'thingie' not found.", cmdstring="@detail")
        self.call(extended_room.CmdExtendedDesc(), "", "Descriptions on Room:")

    def test_cmdgametime(self):
        self.call(extended_room.CmdGameTime(), "", "It's a spring day, in the evening.")


# Test the contrib barter system

from evennia.contrib import barter

class TestBarter(CommandTest):

    def setUp(self):
        super(TestBarter, self).setUp()
        self.tradeitem1 = create_object(key="TradeItem1", location=self.char1)
        self.tradeitem2 = create_object(key="TradeItem2", location=self.char1)
        self.tradeitem3 = create_object(key="TradeItem3", location=self.char2)

    def test_tradehandler_base(self):
        self.char1.msg = Mock()
        self.char2.msg = Mock()
        # test all methods of the tradehandler
        handler = barter.TradeHandler(self.char1, self.char2)
        self.assertEqual(handler.part_a, self.char1)
        self.assertEqual(handler.part_b, self.char2)
        handler.msg_other(self.char1, "Want to trade?")
        handler.msg_other(self.char2, "Yes!")
        handler.msg_other(None, "Talking to myself...")
        self.assertEqual(self.char2.msg.mock_calls[0][1][0], "Want to trade?")
        self.assertEqual(self.char1.msg.mock_calls[0][1][0], "Yes!")
        self.assertEqual(self.char1.msg.mock_calls[1][1][0], "Talking to myself...")
        self.assertEqual(handler.get_other(self.char1), self.char2)
        handler.finish(force=True)

    def test_tradehandler_joins(self):
        handler = barter.TradeHandler(self.char1, self.char2)
        self.assertTrue(handler.join(self.char2))
        self.assertTrue(handler.unjoin(self.char2))
        self.assertFalse(handler.join(self.char1))
        self.assertFalse(handler.unjoin(self.char1))
        handler.finish(force=True)

    def test_tradehandler_offers(self):
        handler = barter.TradeHandler(self.char1, self.char2)
        handler.join(self.char2)
        handler.offer(self.char1, self.tradeitem1, self.tradeitem2)
        self.assertEqual(handler.part_a_offers, [self.tradeitem1, self.tradeitem2])
        self.assertFalse(handler.part_a_accepted)
        self.assertFalse(handler.part_b_accepted)
        handler.offer(self.char2, self.tradeitem3)
        self.assertEqual(handler.list(), ([self.tradeitem1, self.tradeitem2], [self.tradeitem3]))
        self.assertEqual(handler.search("TradeItem2"), self.tradeitem2)
        self.assertEqual(handler.search("TradeItem3"), self.tradeitem3)
        self.assertEqual(handler.search("nonexisting"), None)
        self.assertFalse(handler.finish())  # should fail since offer not yet accepted
        handler.accept(self.char1)
        handler.decline(self.char1)
        handler.accept(self.char2)
        handler.accept(self.char1)  # should trigger handler.finish() automatically
        self.assertEqual(self.tradeitem1.location, self.char2)
        self.assertEqual(self.tradeitem2.location, self.char2)
        self.assertEqual(self.tradeitem3.location, self.char1)

    def test_cmdtrade(self):
        self.call(barter.CmdTrade(), "Char2 : Hey wanna trade?", "You say, \"Hey wanna trade?\"", caller=self.char1)
        self.call(barter.CmdTrade(), "Char decline : Nope!", "You say, \"Nope!\"", caller=self.char2)
        self.call(barter.CmdTrade(), "Char2 : Hey wanna trade?", "You say, \"Hey wanna trade?\"", caller=self.char1)
        self.call(barter.CmdTrade(), "Char accept : Sure!", "You say, \"Sure!\"", caller=self.char2)
        self.call(barter.CmdOffer(), "TradeItem3", "Your trade action: You offer TradeItem3",caller=self.char2)
        self.call(barter.CmdOffer(), "TradeItem1 : Here's my offer.", "You say, \"Here's my offer.\"\n  [You offer TradeItem1]")
        self.call(barter.CmdAccept(), "", "Your trade action: You accept the offer. Char2 must now also accept")
        self.call(barter.CmdDecline(), "", "Your trade action: You change your mind, declining the current offer.")
        self.call(barter.CmdAccept(), ": Sounds good.", "You say, \"Sounds good.\"\n"
                                      "  [You accept the offer. Char must now also accept.", caller=self.char2)
        self.call(barter.CmdDecline(), ":No way!", "You say, \"No way!\"\n  [You change your mind, declining the current offer.]", caller=self.char2)
        self.call(barter.CmdOffer(), "TradeItem1, TradeItem2 : My final offer!", "You say, \"My final offer!\"\n  [You offer TradeItem1 and TradeItem2]")
        self.call(barter.CmdAccept(), "", "Your trade action: You accept the offer. Char2 must now also accept.", caller=self.char1)
        self.call(barter.CmdStatus(), "", "Offered by Char:", caller=self.char2)
        self.tradeitem1.db.desc = "A great offer."
        self.call(barter.CmdEvaluate(), "TradeItem1", "A great offer.")
        self.call(barter.CmdAccept(), ":Ok then.", "You say, \"Ok then.\"\n  [You accept the deal.", caller=self.char2)
        self.assertEqual(self.tradeitem1.location, self.char2)
        self.assertEqual(self.tradeitem2.location, self.char2)
        self.assertEqual(self.tradeitem3.location, self.char1)

    def test_cmdtradehelp(self):
        self.call(barter.CmdTrade(), "Char2 : Hey wanna trade?", "You say, \"Hey wanna trade?\"", caller=self.char1)
        self.call(barter.CmdTradeHelp(), "", "Trading commands\n", caller=self.char1)
        self.call(barter.CmdFinish(), ": Ending.", "You say, \"Ending.\"\n  [You aborted trade. No deal was made.]")

# Test wilderness

from evennia.contrib import wilderness
from evennia import DefaultCharacter

class TestWilderness(EvenniaTest):

    def setUp(self):
        super(TestWilderness, self).setUp()
        self.char1 = create_object(DefaultCharacter, key="char1")
        self.char2 = create_object(DefaultCharacter, key="char2")

    def get_wilderness_script(self, name="default"):
        w = wilderness.WildernessScript.objects.get("default")
        return w

    def test_create_wilderness_default_name(self):
        wilderness.create_wilderness()
        w = self.get_wilderness_script()
        self.assertIsNotNone(w)

    def test_create_wilderness_custom_name(self):
        name = "customname"
        wilderness.create_wilderness(name)
        w = self.get_wilderness_script(name)
        self.assertIsNotNone(w)

    def test_enter_wilderness(self):
        wilderness.create_wilderness()
        wilderness.enter_wilderness(self.char1)
        self.assertIsInstance(self.char1.location, wilderness.WildernessRoom)
        w = self.get_wilderness_script()
        self.assertEquals(w.db.itemcoordinates[self.char1], (0, 0))

    def test_enter_wilderness_custom_coordinates(self):
        wilderness.create_wilderness()
        wilderness.enter_wilderness(self.char1, coordinates=(1, 2))
        self.assertIsInstance(self.char1.location, wilderness.WildernessRoom)
        w = self.get_wilderness_script()
        self.assertEquals(w.db.itemcoordinates[self.char1], (1, 2))

    def test_enter_wilderness_custom_name(self):
        name = "customnname"
        wilderness.create_wilderness(name)
        wilderness.enter_wilderness(self.char1, name=name)
        self.assertIsInstance(self.char1.location, wilderness.WildernessRoom)

    def test_wilderness_correct_exits(self):
        wilderness.create_wilderness()
        wilderness.enter_wilderness(self.char1)

        # By default we enter at a corner (0, 0), so only a few exits should
        # be visible / traversable
        exits = [i for i in self.char1.location.contents
                 if i.destination and (
                  i.access(self.char1, "view") or
                  i.access(self.char1, "traverse"))]

        self.assertEquals(len(exits), 3)
        exitsok = ["north", "northeast", "east"]
        for each_exit in exitsok:
            self.assertTrue(any([e for e in exits if e.key == each_exit]))

        # If we move to another location not on an edge, then all directions
        # should be visible / traversable
        wilderness.enter_wilderness(self.char1, coordinates=(1, 1))
        exits = [i for i in self.char1.location.contents
                 if i.destination and (
                  i.access(self.char1, "view") or
                  i.access(self.char1, "traverse"))]
        self.assertEquals(len(exits), 8)
        exitsok = ["north", "northeast", "east", "southeast", "south",
                   "southwest", "west", "northwest"]
        for each_exit in exitsok:
            self.assertTrue(any([e for e in exits if e.key == each_exit]))

    def test_room_creation(self):
        # Pretend that both char1 and char2 are connected...
        self.char1.sessions.add(1)
        self.char2.sessions.add(1)
        self.assertTrue(self.char1.has_player)
        self.assertTrue(self.char2.has_player)

        wilderness.create_wilderness()
        w = self.get_wilderness_script()

        # We should have no unused room after moving the first player in.
        self.assertEquals(len(w.db.unused_rooms), 0)
        w.move_obj(self.char1, (0, 0))
        self.assertEquals(len(w.db.unused_rooms), 0)

        # And also no unused room after moving the second one in.
        w.move_obj(self.char2, (1, 1))
        self.assertEquals(len(w.db.unused_rooms), 0)

        # But if char2 moves into char1's room, we should have one unused room
        # Which should be char2's old room that got created.
        w.move_obj(self.char2, (0, 0))
        self.assertEquals(len(w.db.unused_rooms), 1)
        self.assertEquals(self.char1.location, self.char2.location)

        # And if char2 moves back out, that unused room should be put back to
        # use again.
        w.move_obj(self.char2, (1, 1))
        self.assertNotEquals(self.char1.location, self.char2.location)
        self.assertEquals(len(w.db.unused_rooms), 0)

    def test_get_new_coordinates(self):
        loc = (1, 1)
        directions = {"north": (1, 2),
                      "northeast": (2, 2),
                      "east": (2, 1),
                      "southeast": (2, 0),
                      "south": (1, 0),
                      "southwest": (0, 0),
                      "west": (0, 1),
                      "northwest": (0, 2)}
        for direction, correct_loc in directions.iteritems():  # Not compatible with Python 3
            new_loc = wilderness.get_new_coordinates(loc, direction)
            self.assertEquals(new_loc, correct_loc, direction)

# Testing chargen contrib
from evennia.contrib import chargen

class TestChargen(CommandTest):

    def test_ooclook(self):
        self.call(chargen.CmdOOCLook(), "foo", "You have no characters to look at", caller=self.player)
        self.call(chargen.CmdOOCLook(), "", "You, TestPlayer, are an OOC ghost without form.", caller=self.player)

    def test_charcreate(self):
        self.call(chargen.CmdOOCCharacterCreate(), "testchar", "The character testchar was successfully created!", caller=self.player)
        self.call(chargen.CmdOOCCharacterCreate(), "testchar", "Character testchar already exists.", caller=self.player)
        self.assertTrue(self.player.db._character_dbrefs)
        self.call(chargen.CmdOOCLook(), "", "You, TestPlayer, are an OOC ghost without form.",caller=self.player)
        self.call(chargen.CmdOOCLook(), "testchar", "testchar(", caller=self.player)

# Testing clothing contrib
from evennia.contrib import clothing
from evennia.objects.objects import DefaultRoom

class TestClothingCmd(CommandTest):

    def test_clothingcommands(self):
        wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        friend = create_object(clothing.ClothedCharacter, key="Friend")
        room = create_object(DefaultRoom, key="room")
        wearer.location = room
        friend.location = room
        # Make a test hat
        test_hat = create_object(clothing.Clothing, key="test hat")
        test_hat.db.clothing_type = 'hat'
        test_hat.location = wearer
        # Make a test scarf
        test_scarf = create_object(clothing.Clothing, key="test scarf")
        test_scarf.db.clothing_type = 'accessory'
        test_scarf.location = wearer
        # Test wear command
        self.call(clothing.CmdWear(), "", "Usage: wear <obj> [wear style]", caller=wearer)
        self.call(clothing.CmdWear(), "hat", "Wearer puts on test hat.", caller=wearer)
        self.call(clothing.CmdWear(), "scarf stylishly", "Wearer wears test scarf stylishly.", caller=wearer)
        # Test cover command.
        self.call(clothing.CmdCover(), "", "Usage: cover <worn clothing> [with] <clothing object>", caller=wearer)
        self.call(clothing.CmdCover(), "hat with scarf", "Wearer covers test hat with test scarf.", caller=wearer)
        # Test remove command.
        self.call(clothing.CmdRemove(), "", "Could not find ''.", caller=wearer)
        self.call(clothing.CmdRemove(), "hat", "You have to take off test scarf first.", caller=wearer)
        self.call(clothing.CmdRemove(), "scarf", "Wearer removes test scarf, revealing test hat.", caller=wearer)
        # Test uncover command.
        test_scarf.wear(wearer, True)
        test_hat.db.covered_by = test_scarf
        self.call(clothing.CmdUncover(), "", "Usage: uncover <worn clothing object>", caller=wearer)
        self.call(clothing.CmdUncover(), "hat", "Wearer uncovers test hat.", caller=wearer)
        # Test drop command.
        test_hat.db.covered_by = test_scarf
        self.call(clothing.CmdDrop(), "", "Drop what?", caller=wearer)
        self.call(clothing.CmdDrop(), "hat", "You can't drop that because it's covered by test scarf.", caller=wearer)
        self.call(clothing.CmdDrop(), "scarf", "You drop test scarf.", caller=wearer)
        # Test give command.
        self.call(clothing.CmdGive(), "", "Usage: give <inventory object> = <target>", caller=wearer)
        self.call(clothing.CmdGive(), "hat = Friend", "Wearer removes test hat.|You give test hat to Friend.", caller=wearer)
        # Test inventory command.
        self.call(clothing.CmdInventory(), "", "You are not carrying or wearing anything.", caller=wearer)

class TestClothingFunc(EvenniaTest):

    def test_clothingfunctions(self):
        wearer = create_object(clothing.ClothedCharacter, key="Wearer")
        room = create_object(DefaultRoom, key="room")
        wearer.location = room
        # Make a test hat
        test_hat = create_object(clothing.Clothing, key="test hat")
        test_hat.db.clothing_type = 'hat'
        test_hat.location = wearer
        # Make a test shirt
        test_shirt = create_object(clothing.Clothing, key="test shirt")
        test_shirt.db.clothing_type = 'top'
        test_shirt.location = wearer
        # Make a test pants
        test_pants = create_object(clothing.Clothing, key="test pants")
        test_pants.db.clothing_type = 'bottom'
        test_pants.location = wearer

        test_hat.wear(wearer, 'on the head')
        self.assertEqual(test_hat.db.worn, 'on the head')

        test_hat.remove(wearer)
        self.assertEqual(test_hat.db.worn, False)

        test_hat.worn = True
        test_hat.at_get(wearer)
        self.assertEqual(test_hat.db.worn, False)

        clothes_list = [test_shirt, test_hat, test_pants]
        self.assertEqual(clothing.order_clothes_list(clothes_list), [test_hat, test_shirt, test_pants])

        test_hat.wear(wearer, True)
        test_pants.wear(wearer, True)
        self.assertEqual(clothing.get_worn_clothes(wearer), [test_hat, test_pants])

        self.assertEqual(clothing.clothing_type_count(clothes_list), {'hat':1, 'top':1, 'bottom':1})

        self.assertEqual(clothing.single_type_count(clothes_list, 'hat'), 1)




# Testing custom_gametime
from evennia.contrib import custom_gametime

def _testcallback():
    pass

class TestCustomGameTime(EvenniaTest):
    def setUp(self):
        super(TestCustomGameTime, self).setUp()
        gametime.gametime = Mock(return_value=2975000898.46) # does not seem to work
    def tearDown(self):
        if hasattr(self, "timescript"):
            self.timescript.stop()
    def test_time_to_tuple(self):
        self.assertEqual(custom_gametime.time_to_tuple(10000, 34,2,4,6,1), (294, 2, 0, 0, 0, 0))
        self.assertEqual(custom_gametime.time_to_tuple(10000, 3,3,4), (3333, 0, 0, 1))
        self.assertEqual(custom_gametime.time_to_tuple(100000, 239,24,3), (418, 4, 0, 2))
    def test_gametime_to_realtime(self):
        self.assertEqual(custom_gametime.gametime_to_realtime(days=2, mins=4), 86520.0)
        self.assertEqual(custom_gametime.gametime_to_realtime(format=True, days=2), (0,0,0,1,0,0,0))
    def test_realtime_to_gametime(self):
        self.assertEqual(custom_gametime.realtime_to_gametime(days=2, mins=34), 349680.0)
        self.assertEqual(custom_gametime.realtime_to_gametime(days=2, mins=34, format=True), (0, 0, 0, 4, 1, 8, 0))
        self.assertEqual(custom_gametime.realtime_to_gametime(format=True, days=2, mins=4), (0, 0, 0, 4, 0, 8, 0))
    def test_custom_gametime(self):
        self.assertEqual(custom_gametime.custom_gametime(), (102, 5, 2, 6, 21, 8, 18))
        self.assertEqual(custom_gametime.custom_gametime(absolute=True), (102, 5, 2, 6, 21, 8, 18))
    def test_real_seconds_until(self):
        self.assertEqual(custom_gametime.real_seconds_until(year=2300, month=11, day=6), 31911667199.77)
    def test_schedule(self):
        self.timescript = custom_gametime.schedule(_testcallback, repeat=True, min=5, sec=0)
        self.assertEqual(self.timescript.interval, 1700.7699999809265)

# Test dice module


@patch('random.randint', return_value=5)
class TestDice(CommandTest):
    def test_roll_dice(self, mocked_randint):
        # we must import dice here for the mocked randint to apply correctly.
        from evennia.contrib import dice
        self.assertEqual(dice.roll_dice(6, 6, modifier=('+', 4)), mocked_randint()*6 + 4)
        self.assertEqual(dice.roll_dice(6, 6, conditional=('<', 35)), True)
        self.assertEqual(dice.roll_dice(6, 6, conditional=('>', 33)), False)
    def test_cmddice(self, mocked_randint):
        from evennia.contrib import dice
        self.call(dice.CmdDice(), "3d6 + 4", "You roll 3d6 + 4.| Roll(s): 5, 5 and 5. Total result is 19.")
        self.call(dice.CmdDice(), "100000d1000", "The maximum roll allowed is 10000d10000.")
        self.call(dice.CmdDice(), "/secret 3d6 + 4", "You roll 3d6 + 4 (secret, not echoed).")

# Test email-login

from evennia.contrib import email_login

class TestEmailLogin(CommandTest):
    def test_connect(self):
        self.call(email_login.CmdUnconnectedConnect(), "mytest@test.com test", "The email 'mytest@test.com' does not match any accounts.")
        self.call(email_login.CmdUnconnectedCreate(), '"mytest" mytest@test.com test11111', "A new account 'mytest' was created. Welcome!")
        self.call(email_login.CmdUnconnectedConnect(), "mytest@test.com test11111", "", caller=self.player.sessions.get()[0])
    def test_quit(self):
        self.call(email_login.CmdUnconnectedQuit(), "", "", caller=self.player.sessions.get()[0])
    def test_unconnectedlook(self):
        self.call(email_login.CmdUnconnectedLook(), "", "==========")
    def test_unconnectedhelp(self):
        self.call(email_login.CmdUnconnectedHelp(), "", "You are not yet logged into the game.")

# test gendersub contrib

from evennia.contrib import gendersub

class TestGenderSub(CommandTest):
    def test_setgender(self):
        self.call(gendersub.SetGender(), "male", "Your gender was set to male.")
        self.call(gendersub.SetGender(), "ambiguous", "Your gender was set to ambiguous.")
        self.call(gendersub.SetGender(), "Foo", "Usage: @gender")
    def test_gendercharacter(self):
        char = create_object(gendersub.GenderCharacter, key="Gendered", location=self.room1)
        txt = "Test |p gender"
        self.assertEqual(gendersub._RE_GENDER_PRONOUN.sub(char._get_pronoun, txt), "Test their gender")

# test mail contrib

from evennia.contrib import mail

class TestMail(CommandTest):
    def test_mail(self):
        self.call(mail.CmdMail(), "2", "'2' is not a valid mail id.", caller=self.player)
        self.call(mail.CmdMail(), "", "There are no messages in your inbox.", caller=self.player)
        self.call(mail.CmdMail(), "Char=Message 1", "You have received a new @mail from Char|You sent your message.", caller=self.char1)
        self.call(mail.CmdMail(), "Char=Message 2", "You sent your message.", caller=self.char2)
        self.call(mail.CmdMail(), "TestPlayer2=Message 2",
            "You have received a new @mail from TestPlayer2(player 2)|You sent your message.", caller=self.player2)
        self.call(mail.CmdMail(), "TestPlayer=Message 1", "You sent your message.", caller=self.player2)
        self.call(mail.CmdMail(), "TestPlayer=Message 2", "You sent your message.", caller=self.player2)
        self.call(mail.CmdMail(), "", "| ID:   From:            Subject:", caller=self.player)
        self.call(mail.CmdMail(), "2", "From: TestPlayer2", caller=self.player)
        self.call(mail.CmdMail(), "/forward TestPlayer2 = 1/Forward message", "You sent your message.|Message forwarded.", caller=self.player)
        self.call(mail.CmdMail(), "/reply 2=Reply Message2", "You sent your message.", caller=self.player)
        self.call(mail.CmdMail(), "/delete 2", "Message 2 deleted", caller=self.player)

# test map builder contrib

from evennia.contrib import mapbuilder

class TestMapBuilder(CommandTest):
    def test_cmdmapbuilder(self):
        self.call(mapbuilder.CmdMapBuilder(),
            "evennia.contrib.mapbuilder.EXAMPLE1_MAP evennia.contrib.mapbuilder.EXAMPLE1_LEGEND",
"""Creating Map...|≈≈≈≈≈
≈♣n♣≈
≈∩▲∩≈
≈♠n♠≈
≈≈≈≈≈
|Creating Landmass...|""")
        self.call(mapbuilder.CmdMapBuilder(),
            "evennia.contrib.mapbuilder.EXAMPLE2_MAP evennia.contrib.mapbuilder.EXAMPLE2_LEGEND",
"""Creating Map...|≈ ≈ ≈ ≈ ≈

≈ ♣♣♣ ≈
    ≈ ♣ ♣ ♣ ≈
  ≈ ♣♣♣ ≈

≈ ≈ ≈ ≈ ≈
|Creating Landmass...|""")


# test menu_login

from evennia.contrib import menu_login

class TestMenuLogin(CommandTest):
    def test_cmdunloggedlook(self):
        self.call(menu_login.CmdUnloggedinLook(), "", "======")


# test multidescer contrib

from evennia.contrib import multidescer

class TestMultidescer(CommandTest):
    def test_cmdmultidesc(self):
        self.call(multidescer.CmdMultiDesc(),"/list", "Stored descs:\ncaller:")
        self.call(multidescer.CmdMultiDesc(),"test = Desc 1", "Stored description 'test': \"Desc 1\"")
        self.call(multidescer.CmdMultiDesc(),"test2 = Desc 2", "Stored description 'test2': \"Desc 2\"")
        self.call(multidescer.CmdMultiDesc(),"/swap test-test2", "Swapped descs 'test' and 'test2'.")
        self.call(multidescer.CmdMultiDesc(),"test3 = Desc 3init", "Stored description 'test3': \"Desc 3init\"")
        self.call(multidescer.CmdMultiDesc(),"/list", "Stored descs:\ntest3: Desc 3init\ntest: Desc 1\ntest2: Desc 2\ncaller:")
        self.call(multidescer.CmdMultiDesc(),"test3 = Desc 3", "Stored description 'test3': \"Desc 3\"")
        self.call(multidescer.CmdMultiDesc(),"/set test1 + test2 + + test3", "test1 Desc 2 Desc 3\n\n"
                                             "The above was set as the current description.")
        self.assertEqual(self.char1.db.desc, "test1 Desc 2 Desc 3")

# test simpledoor contrib

from evennia.contrib import simpledoor

class TestSimpleDoor(CommandTest):
    def test_cmdopen(self):
        self.call(simpledoor.CmdOpen(), "newdoor;door:contrib.simpledoor.SimpleDoor,backdoor;door = Room2",
                "Created new Exit 'newdoor' from Room to Room2 (aliases: door).|Note: A doortype exit was "
                "created  ignored eventual custom returnexit type.|Created new Exit 'newdoor' from Room2 to Room (aliases: door).")
        self.call(simpledoor.CmdOpenCloseDoor(), "newdoor", "You close newdoor.", cmdstring="close")
        self.call(simpledoor.CmdOpenCloseDoor(), "newdoor", "newdoor is already closed.", cmdstring="close")
        self.call(simpledoor.CmdOpenCloseDoor(), "newdoor", "You open newdoor.", cmdstring="open")
        self.call(simpledoor.CmdOpenCloseDoor(), "newdoor", "newdoor is already open.", cmdstring="open")

# test slow_exit contrib

from evennia.contrib import slow_exit
slow_exit.MOVE_DELAY = {"stroll":0, "walk": 0, "run": 0, "sprint": 0}

class TestSlowExit(CommandTest):
    def test_exit(self):
        exi = create_object(slow_exit.SlowExit, key="slowexit", location=self.room1, destination=self.room2)
        exi.at_traverse(self.char1, self.room2)
        self.call(slow_exit.CmdSetSpeed(), "walk", "You are now walking.")
        self.call(slow_exit.CmdStop(), "", "You stop moving.")

# test talking npc contrib

from evennia.contrib import talking_npc

class TestTalkingNPC(CommandTest):
    def test_talkingnpc(self):
        npc = create_object(talking_npc.TalkingNPC, key="npctalker", location=self.room1)
        self.call(talking_npc.CmdTalk(), "","(You walk up and talk to Char.)|")
        npc.delete()


# tests for the tutorial world

# test tutorial_world/mob

from evennia.contrib.tutorial_world import mob

class TestTutorialWorldMob(EvenniaTest):
    def test_mob(self):
        mobobj = create_object(mob.Mob, key="mob")
        self.assertEqual(mobobj.db.is_dead, True)
        mobobj.set_alive()
        self.assertEqual(mobobj.db.is_dead, False)
        mobobj.set_dead()
        self.assertEqual(mobobj.db.is_dead, True)
        mobobj._set_ticker(0, "foo", stop=True)
        #TODO should be expanded with further tests of the modes and damage etc.

#  test tutorial_world/objects

from evennia.contrib.tutorial_world import objects as tutobjects

class TestTutorialWorldObjects(CommandTest):
    def test_tutorialobj(self):
        obj1 = create_object(tutobjects.TutorialObject, key="tutobj")
        obj1.reset()
        self.assertEqual(obj1.location, obj1.home)
    def test_readable(self):
        readable = create_object(tutobjects.Readable, key="book", location=self.room1)
        readable.db.readable_text = "Text to read"
        self.call(tutobjects.CmdRead(), "book","You read book:\n  Text to read", obj=readable)
    def test_climbable(self):
        climbable = create_object(tutobjects.Climbable, key="tree", location=self.room1)
        self.call(tutobjects.CmdClimb(), "tree", "You climb tree. Having looked around, you climb down again.", obj=climbable)
        self.assertEqual(self.char1.tags.get("tutorial_climbed_tree", category="tutorial_world"), "tutorial_climbed_tree")
    def test_obelisk(self):
        obelisk = create_object(tutobjects.Obelisk, key="obelisk", location=self.room1)
        self.assertEqual(obelisk.return_appearance(self.char1).startswith("|cobelisk("), True)
    def test_lightsource(self):
        light = create_object(tutobjects.LightSource, key="torch", location=self.room1)
        self.call(tutobjects.CmdLight(), "", "You light torch.", obj=light)
        light._burnout()
        if hasattr(light, "deferred"):
            light.deferred.cancel()
        self.assertFalse(light.pk)
    def test_crumblingwall(self):
        wall = create_object(tutobjects.CrumblingWall, key="wall", location=self.room1)
        self.assertFalse(wall.db.button_exposed)
        self.assertFalse(wall.db.exit_open)
        wall.db.root_pos = {"yellow":0, "green":0,"red":0,"blue":0}
        self.call(tutobjects.CmdShiftRoot(), "blue root right",
                "You shove the root adorned with small blue flowers to the right.", obj=wall)
        self.call(tutobjects.CmdShiftRoot(), "red root left",
                "You shift the reddish root to the left.", obj=wall)
        self.call(tutobjects.CmdShiftRoot(), "yellow root down",
                "You shove the root adorned with small yellow flowers downwards.", obj=wall)
        self.call(tutobjects.CmdShiftRoot(), "green root up",
                "You shift the weedy green root upwards.|Holding aside the root you think you notice something behind it ...", obj=wall)
        self.call(tutobjects.CmdPressButton(), "",
                "You move your fingers over the suspicious depression, then gives it a decisive push. First", obj=wall)
        self.assertTrue(wall.db.button_exposed)
        self.assertTrue(wall.db.exit_open)
        wall.reset()
        if hasattr(wall, "deferred"):
            wall.deferred.cancel()
        wall.delete()
    def test_weapon(self):
        weapon = create_object(tutobjects.Weapon, key="sword", location=self.char1)
        self.call(tutobjects.CmdAttack(), "Char", "You stab with sword.", obj=weapon, cmdstring="stab")
        self.call(tutobjects.CmdAttack(), "Char", "You slash with sword.", obj=weapon, cmdstring="slash")
    def test_weaponrack(self):
        rack = create_object(tutobjects.WeaponRack, key="rack", location=self.room1)
        rack.db.available_weapons = ["sword"]
        self.call(tutobjects.CmdGetWeapon(), "", "You find Rusty sword.", obj=rack)

# test tutorial_world/
from evennia.contrib.tutorial_world import rooms as tutrooms

class TestTutorialWorldRooms(CommandTest):
    def test_cmdtutorial(self):
        room = create_object(tutrooms.TutorialRoom, key="tutroom")
        self.char1.location = room
        self.call(tutrooms.CmdTutorial(), "", "Sorry, there is no tutorial help available here.")
        self.call(tutrooms.CmdTutorialSetDetail(), "detail;foo;foo2 = A detail", "Detail set: 'detail;foo;foo2': 'A detail'", obj=room)
        self.call(tutrooms.CmdTutorialLook(), "", "tutroom(", obj=room)
        self.call(tutrooms.CmdTutorialLook(), "detail", "A detail", obj=room)
        self.call(tutrooms.CmdTutorialLook(), "foo", "A detail", obj=room)
        room.delete()
    def test_weatherroom(self):
        room = create_object(tutrooms.WeatherRoom, key="weatherroom")
        room.update_weather()
        tutrooms.TICKER_HANDLER.remove(interval=room.db.interval, callback=room.update_weather, idstring="tutorial")
        room.delete()
    def test_introroom(self):
        room = create_object(tutrooms.IntroRoom, key="introroom")
        room.at_object_receive(self.char1, self.room1)
    def test_bridgeroom(self):
        room = create_object(tutrooms.BridgeRoom, key="bridgeroom")
        room.update_weather()
        self.char1.move_to(room)
        self.call(tutrooms.CmdBridgeHelp(), "", "You are trying hard not to fall off the bridge ...", obj=room)
        self.call(tutrooms.CmdLookBridge(), "", "bridgeroom\nYou are standing very close to the the bridge's western foundation.", obj=room)
        room.at_object_leave(self.char1, self.room1)
        tutrooms.TICKER_HANDLER.remove(interval=room.db.interval, callback=room.update_weather, idstring="tutorial")
        room.delete()
    def test_darkroom(self):
        room = create_object(tutrooms.DarkRoom, key="darkroom")
        self.char1.move_to(room)
        self.call(tutrooms.CmdDarkHelp(), "", "Can't help you until")
    def test_teleportroom(self):
        create_object(tutrooms.TeleportRoom, key="teleportroom")
    def test_outroroom(self):
        create_object(tutrooms.OutroRoom, key="outroroom")

# test turnbattle
from evennia.contrib import turnbattle
from evennia.objects.objects import DefaultRoom

class TestTurnBattleCmd(CommandTest):

    # Test combat commands
    def test_turnbattlecmd(self):
        self.call(turnbattle.CmdFight(), "", "You can't start a fight if you've been defeated!")
        self.call(turnbattle.CmdAttack(), "", "You can only do that in combat. (see: help fight)")
        self.call(turnbattle.CmdPass(), "", "You can only do that in combat. (see: help fight)")
        self.call(turnbattle.CmdDisengage(), "", "You can only do that in combat. (see: help fight)")
        self.call(turnbattle.CmdRest(), "", "Char rests to recover HP.")

class TestTurnBattleFunc(EvenniaTest):

    # Test combat functions
    def test_turnbattlefunc(self):
        attacker = create_object(turnbattle.BattleCharacter, key="Attacker")
        defender = create_object(turnbattle.BattleCharacter, key="Defender")
        testroom = create_object(DefaultRoom, key="Test Room")
        attacker.location = testroom
        defender.loaction = testroom
        # Initiative roll
        initiative = turnbattle.roll_init(attacker)
        self.assertTrue(initiative >= 0 and initiative <= 1000)
        # Attack roll
        attack_roll = turnbattle.get_attack(attacker, defender)
        self.assertTrue(attack_roll >= 0 and attack_roll <= 100)
        # Defense roll
        defense_roll = turnbattle.get_defense(attacker, defender)
        self.assertTrue(defense_roll == 50)
        # Damage roll
        damage_roll = turnbattle.get_damage(attacker, defender)
        self.assertTrue(damage_roll >= 15 and damage_roll <= 25)
        # Apply damage
        defender.db.hp = 10
        turnbattle.apply_damage(defender, 3)
        self.assertTrue(defender.db.hp == 7)
        # Resolve attack
        defender.db.hp = 40
        turnbattle.resolve_attack(attacker, defender, attack_value=20, defense_value=10)
        self.assertTrue(defender.db.hp < 40)
        # Combat cleanup
        attacker.db.Combat_attribute = True
        turnbattle.combat_cleanup(attacker)
        self.assertFalse(attacker.db.combat_attribute)
        # Is in combat
        self.assertFalse(turnbattle.is_in_combat(attacker))
        # Set up turn handler script for further tests
        attacker.location.scripts.add(turnbattle.TurnHandler)
        turnhandler = attacker.db.combat_TurnHandler
        self.assertTrue(attacker.db.combat_TurnHandler)
        # Force turn order
        turnhandler.db.fighters = [attacker, defender]
        turnhandler.db.turn = 0
        # Test is turn
        self.assertTrue(turnbattle.is_turn(attacker))
        # Spend actions
        attacker.db.Combat_ActionsLeft = 1
        turnbattle.spend_action(attacker, 1, action_name="Test")
        self.assertTrue(attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(attacker.db.Combat_LastAction == "Test")
        # Initialize for combat
        attacker.db.Combat_ActionsLeft = 983
        turnhandler.initialize_for_combat(attacker)
        self.assertTrue(attacker.db.Combat_ActionsLeft == 0)
        self.assertTrue(attacker.db.Combat_LastAction == "null")
        # Start turn
        defender.db.Combat_ActionsLeft = 0
        turnhandler.start_turn(defender)
        self.assertTrue(defender.db.Combat_ActionsLeft == 1)
        # Next turn
        turnhandler.db.fighters = [attacker, defender]
        turnhandler.db.turn = 0
        turnhandler.next_turn()
        self.assertTrue(turnhandler.db.turn == 1)
        # Turn end check
        turnhandler.db.fighters = [attacker, defender]
        turnhandler.db.turn = 0
        attacker.db.Combat_ActionsLeft = 0
        turnhandler.turn_end_check(attacker)
        self.assertTrue(turnhandler.db.turn == 1)
        # Join fight
        joiner = create_object(turnbattle.BattleCharacter, key="Joiner")
        turnhandler.db.fighters = [attacker, defender]
        turnhandler.db.turn = 0
        turnhandler.join_fight(joiner)
        self.assertTrue(turnhandler.db.turn == 1)
        self.assertTrue(turnhandler.db.fighters == [joiner, attacker, defender])
        # Remove the script at the end
        turnhandler.stop()


# Test of the unixcommand module

from evennia.contrib.unixcommand import UnixCommand

class CmdDummy(UnixCommand):

    """A dummy UnixCommand."""

    key = "dummy"

    def init_parser(self):
        """Fill out options."""
        self.parser.add_argument("nb1", type=int, help="the first number")
        self.parser.add_argument("nb2", type=int, help="the second number")
        self.parser.add_argument("-v", "--verbose", action="store_true")

    def func(self):
        nb1 = self.opts.nb1
        nb2 = self.opts.nb2
        result = nb1 * nb2
        verbose = self.opts.verbose
        if verbose:
            self.msg("{} times {} is {}".format(nb1, nb2, result))
        else:
            self.msg("{} * {} = {}".format(nb1, nb2, result))


class TestUnixCommand(CommandTest):

    def test_success(self):
        """See the command parsing succeed."""
        self.call(CmdDummy(), "5 10", "5 * 10 = 50")
        self.call(CmdDummy(), "5 10 -v", "5 times 10 is 50")

    def test_failure(self):
        """If not provided with the right info, should fail."""
        ret = self.call(CmdDummy(), "5")
        lines = ret.splitlines()
        self.assertTrue(any(l.startswith("usage:") for l in lines))
        self.assertTrue(any(l.startswith("dummy: error:") for l in lines))

        # If we specify an incorrect number as parameter
        ret = self.call(CmdDummy(), "five ten")
        lines = ret.splitlines()
        self.assertTrue(any(l.startswith("usage:") for l in lines))
        self.assertTrue(any(l.startswith("dummy: error:") for l in lines))
