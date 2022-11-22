"""
Tests for RP system

"""
import time

from anything import Anything

from evennia import create_object
from evennia.commands.default.tests import BaseEvenniaCommandTest
from evennia.utils.test_resources import BaseEvenniaTest

from . import rplanguage, rpsystem

mtrans = {"testing": "1", "is": "2", "a": "3", "human": "4"}
atrans = ["An", "automated", "advantageous", "repeatable", "faster"]

text = (
    "Automated testing is advantageous for a number of reasons: "
    "tests may be executed Continuously without the need for human "
    "intervention, They are easily repeatable, and often faster."
)


class TestLanguage(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        rplanguage.add_language(
            key="testlang",
            word_length_variance=1,
            noun_prefix="bara",
            noun_postfix="'y",
            manual_translations=mtrans,
            auto_translations=atrans,
            force=True,
        )
        rplanguage.add_language(
            key="binary",
            phonemes="oo ii a ck w b d t",
            grammar="cvvv cvv cvvcv cvvcvv cvvvc cvvvcvv cvvc",
            noun_prefix="beep-",
            word_length_variance=4,
        )

    def tearDown(self):
        super().tearDown()
        rplanguage._LANGUAGE_HANDLER.delete()
        rplanguage._LANGUAGE_HANDLER = None

    def test_obfuscate_language(self):
        result0 = rplanguage.obfuscate_language(text, level=0.0, language="testlang")
        self.assertEqual(result0, text)
        result1 = rplanguage.obfuscate_language(text, level=1.0, language="testlang")
        result2 = rplanguage.obfuscate_language(text, level=1.0, language="testlang")
        result3 = rplanguage.obfuscate_language(text, level=1.0, language="binary")

        self.assertNotEqual(result1, text)
        self.assertNotEqual(result3, text)
        result1, result2 = result1.split(), result2.split()
        self.assertEqual(result1[:4], result2[:4])
        self.assertEqual(result1[1], "1")
        self.assertEqual(result1[2], "2")
        self.assertEqual(result2[-1], result2[-1])

    def test_faulty_language(self):
        self.assertRaises(
            rplanguage.LanguageError,
            rplanguage.add_language,
            key="binary2",
            phonemes="w b d t oe ee, oo e o a wh dw bw",  # erroneous comma
            grammar="cvvv cvv cvvcv cvvcvvo cvvvc cvvvcvv cvvc c v cc vv ccvvc ccvvccvv ",
            vowels="oea",
            word_length_variance=4,
        )

    def test_available_languages(self):
        self.assertEqual(list(sorted(rplanguage.available_languages())), ["binary", "testlang"])

    def test_obfuscate_whisper(self):
        self.assertEqual(rplanguage.obfuscate_whisper(text, level=0.0), text)
        assert rplanguage.obfuscate_whisper(text, level=0.1).startswith(
            "-utom-t-d t-sting is -dv-nt-g-ous for - numb-r of r--sons: t-sts m-y b- -x-cut-d Continuously"
        )
        assert rplanguage.obfuscate_whisper(text, level=0.5).startswith(
            "--------- --s---- -s -----------s f-- - ------ -f ---s--s: --s-s "
        )
        self.assertEqual(rplanguage.obfuscate_whisper(text, level=1.0), "...")


# Testing of emoting / sdesc / recog system

sdesc0 = "A nice sender of emotes"
sdesc1 = "The first receiver of emotes."
sdesc2 = "Another nice colliding sdesc-guy for tests"
recog01 = "Mr Receiver"
recog02 = "Mr Receiver2"
recog10 = "Mr Sender"
emote = 'With a flair, /me looks at /first and /colliding sdesc-guy. She says "This is a test."'
fallback_emote = "/Me is distracted from /first by /nomatch."
case_emote = "/Me looks at /first. Then, /me looks at /FIRST, /First and /Colliding twice."
poss_emote = "/Me frowns at /first for trying to steal /me's test."


class TestRPSystem(BaseEvenniaTest):
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.room = create_object(rpsystem.ContribRPRoom, key="Location")
        self.speaker = create_object(rpsystem.ContribRPCharacter, key="Sender", location=self.room)
        self.receiver1 = create_object(
            rpsystem.ContribRPCharacter, key="Receiver1", location=self.room
        )
        self.receiver2 = create_object(
            rpsystem.ContribRPCharacter, key="Receiver2", location=self.room
        )

    def test_posed_contents(self):
        self.obj1 = create_object(rpsystem.ContribRPObject, key="thing", location=self.room)
        self.obj2 = create_object(rpsystem.ContribRPObject, key="thing", location=self.room)
        self.obj3 = create_object(rpsystem.ContribRPObject, key="object", location=self.room)
        room_display = self.room.return_appearance(self.speaker)
        self.assertIn("An object and two things are here.", room_display)
        self.obj3.db.pose = "is on the ground."
        room_display = self.room.return_appearance(self.speaker)
        self.assertIn("Two things are here.", room_display)
        self.assertIn("An object is on the ground.", room_display)

    def test_sdesc_handler(self):
        self.speaker.sdesc.add(sdesc0)
        self.assertEqual(self.speaker.sdesc.get(), sdesc0)
        self.speaker.sdesc.add("This is {#324} ignored")
        self.assertEqual(self.speaker.sdesc.get(), "This is 324 ignored")

    def test_recog_handler(self):
        self.speaker.sdesc.add(sdesc0)
        self.receiver1.sdesc.add(sdesc1)
        self.speaker.recog.add(self.receiver1, recog01)
        self.speaker.recog.add(self.receiver2, recog02)
        self.assertEqual(self.speaker.recog.get(self.receiver1), recog01)
        self.assertEqual(self.speaker.recog.get(self.receiver2), recog02)
        self.speaker.recog.remove(self.receiver1)
        self.assertEqual(self.speaker.recog.get(self.receiver1), None)

        self.assertEqual(self.speaker.recog.all(), {"Mr Receiver2": self.receiver2})

    def test_parse_language(self):
        self.assertEqual(
            rpsystem.parse_language(self.speaker, emote),
            (
                "With a flair, /me looks at /first and /colliding sdesc-guy. She says {##0}",
                {"##0": (None, '"This is a test."')},
            ),
        )

    def test_parse_sdescs_and_recogs(self):
        speaker = self.speaker
        speaker.sdesc.add(sdesc0)
        self.receiver1.sdesc.add(sdesc1)
        self.receiver2.sdesc.add(sdesc2)
        id0 = f"#{speaker.id}"
        id1 = f"#{self.receiver1.id}"
        id2 = f"#{self.receiver2.id}"
        candidates = (self.receiver1, self.receiver2)
        result = (
            "With a flair, {"
            + id0
            + "} looks at {"
            + id1
            + "} and {"
            + id2
            + '}. She says "This is a test."',
            {
                id2: self.receiver2,
                id1: self.receiver1,
                id0: speaker,
            },
        )
        self.assertEqual(
            rpsystem.parse_sdescs_and_recogs(speaker, candidates, emote, case_sensitive=False),
            result,
        )
        self.speaker.recog.add(self.receiver1, recog01)
        self.assertEqual(
            rpsystem.parse_sdescs_and_recogs(speaker, candidates, emote, case_sensitive=False),
            result,
        )

    def test_possessive_selfref(self):
        speaker = self.speaker
        speaker.sdesc.add(sdesc0)
        self.receiver1.sdesc.add(sdesc1)
        self.receiver2.sdesc.add(sdesc2)
        id0 = f"#{speaker.id}"
        id1 = f"#{self.receiver1.id}"
        id2 = f"#{self.receiver2.id}"
        candidates = (self.receiver1, self.receiver2)
        result = (
            "{" + id0 + "} frowns at {" + id1 + "} for trying to steal {" + id0 + "}'s test.",
            {
                id1: self.receiver1,
                id0: speaker,
            },
        )
        self.assertEqual(
            rpsystem.parse_sdescs_and_recogs(speaker, candidates, poss_emote, case_sensitive=False),
            result,
        )

    def test_get_sdesc(self):
        looker = self.speaker  # Sender
        target = self.receiver1  # Receiver1
        looker.sdesc.add(sdesc0)  # A nice sender of emotes
        target.sdesc.add(sdesc1)  # The first receiver of emotes.

        # sdesc with no processing
        self.assertEqual(looker.get_sdesc(target), "The first receiver of emotes.")
        # sdesc with processing
        self.assertEqual(
            looker.get_sdesc(target, process=True), "|bThe first receiver of emotes.|n"
        )

        looker.recog.add(target, recog01)  # Mr Receiver

        # recog with no processing
        self.assertEqual(looker.get_sdesc(target), "Mr Receiver")
        # recog with processing
        self.assertEqual(looker.get_sdesc(target, process=True), "|mMr Receiver|n")

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
        rpsystem.send_emote(speaker, receivers, emote, case_sensitive=False)
        self.assertEqual(
            self.out0[0],
            "With a flair, |mSender|n looks at |bThe first receiver of emotes.|n "
            'and |bAnother nice colliding sdesc-guy for tests|n. She says |w"This is a test."|n',
        )
        self.assertEqual(
            self.out1[0],
            "With a flair, |bA nice sender of emotes|n looks at |mReceiver1|n and "
            '|bAnother nice colliding sdesc-guy for tests|n. She says |w"This is a test."|n',
        )
        self.assertEqual(
            self.out2[0],
            "With a flair, |bA nice sender of emotes|n looks at |bThe first "
            'receiver of emotes.|n and |mReceiver2|n. She says |w"This is a test."|n',
        )

    def test_send_emote_fallback(self):
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
        rpsystem.send_emote(speaker, receivers, fallback_emote, fallback="something")
        self.assertEqual(
            self.out0[0],
            "|mSender|n is distracted from |bthe first receiver of emotes.|n by something.",
        )
        self.assertEqual(
            self.out1[0],
            "|bA nice sender of emotes|n is distracted from |mReceiver1|n by something.",
        )
        self.assertEqual(
            self.out2[0],
            "|bA nice sender of emotes|n is distracted from |bthe first receiver of emotes.|n by something.",
        )

    def test_send_case_sensitive_emote(self):
        """Test new case-sensitive rp-parsing"""
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
        rpsystem.send_emote(speaker, receivers, case_emote)
        self.assertEqual(
            self.out0[0],
            "|mSender|n looks at |bthe first receiver of emotes.|n. Then, |mSender|n "
            "looks at |bTHE FIRST RECEIVER OF EMOTES.|n, |bThe first receiver of emotes.|n "
            "and |bAnother nice colliding sdesc-guy for tests|n twice.",
        )
        self.assertEqual(
            self.out1[0],
            "|bA nice sender of emotes|n looks at |mReceiver1|n. Then, "
            "|ba nice sender of emotes|n looks at |mReceiver1|n, |mReceiver1|n "
            "and |bAnother nice colliding sdesc-guy for tests|n twice.",
        )
        self.assertEqual(
            self.out2[0],
            "|bA nice sender of emotes|n looks at |bthe first receiver of emotes.|n. "
            "Then, |ba nice sender of emotes|n looks at |bTHE FIRST RECEIVER OF EMOTES.|n, "
            "|bThe first receiver of emotes.|n and |mReceiver2|n twice.",
        )

    def test_rpsearch(self):
        self.speaker.sdesc.add(sdesc0)
        self.receiver1.sdesc.add(sdesc1)
        self.receiver2.sdesc.add(sdesc2)
        self.speaker.msg = lambda text, **kwargs: setattr(self, "out0", text)
        self.assertEqual(self.speaker.search("receiver of emotes"), self.receiver1)
        self.assertEqual(self.speaker.search("colliding"), self.receiver2)


class TestRPSystemCommands(BaseEvenniaCommandTest):
    def setUp(self):
        super().setUp()
        self.char1.swap_typeclass(rpsystem.ContribRPCharacter)
        self.char2.swap_typeclass(rpsystem.ContribRPCharacter)

    def test_commands(self):

        self.call(
            rpsystem.CmdSdesc(), "Foobar Character", "Char's sdesc was set to 'Foobar Character'."
        )
        self.call(
            rpsystem.CmdSdesc(),
            "BarFoo Character",
            "Char2's sdesc was set to 'BarFoo Character'.",
            caller=self.char2,
        )
        self.call(rpsystem.CmdSay(), "Hello!", 'Char says, "Hello!"')
        self.call(rpsystem.CmdEmote(), "/me smiles to /BarFoo.", "Char smiles to BarFoo Character")
        self.call(
            rpsystem.CmdPose(),
            "stands by the bar",
            "Pose will read 'Foobar Character stands by the bar.'.",
        )
        self.call(
            rpsystem.CmdRecog(),
            "barfoo as friend",
            "You will now remember BarFoo Character as friend.",
        )
        self.call(
            rpsystem.CmdRecog(),
            "",
            "Currently recognized (use 'recog <sdesc> as <alias>' to add new "
            "and 'forget <alias>' to remove):\n friend  (BarFoo Character)",
        )
        self.call(
            rpsystem.CmdRecog(),
            "friend",
            "You will now know them only as 'BarFoo Character'",
            cmdstring="forget",
        )
