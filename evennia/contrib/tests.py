"""
Testing suite for contrib folder

"""

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

from evennia.contrib import extended_room
from evennia import gametime
from evennia.objects.objects import DefaultRoom

class TestExtendedRoom(CommandTest):
    room_typeclass = extended_room.ExtendedRoom
    DETAIL_DESC = "A test detail."
    SPRING_DESC = "A spring description."
    OLD_DESC = "Old description."

    def setUp(self):
        super(TestExtendedRoom, self).setUp()
        self.room1.ndb.last_timeslot = "afternoon"
        self.room1.ndb.last_season = "winter"
        self.room1.db.details = {'testdetail': self.DETAIL_DESC}
        self.room1.db.spring_desc = self.SPRING_DESC
        self.room1.db.desc = self.OLD_DESC
        # mock gametime to return 7th month, 10 in morning
        gametime.gametime = Mock(return_value=2975000766) # spring evening

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
