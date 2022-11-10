"""
Tests of create functions

"""

from django.test import TestCase

from evennia.scripts.scripts import DefaultScript
from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest


class TestCreateScript(BaseEvenniaTest):
    def test_create_script(self):
        class TestScriptA(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.persistent = False

        script = create.create_script(TestScriptA, key="test_script")
        assert script is not None
        assert script.interval == 10
        assert script.key == "test_script"
        script.stop()

    def test_create_script_w_repeats_equal_1(self):
        class TestScriptB(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.repeats = 1
                self.persistent = False

        # script should still exist even though repeats=1, start_delay=False
        script = create.create_script(TestScriptB, key="test_script")
        assert script
        # but the timer should be inactive now
        assert not script.is_active

    def test_create_script_w_repeats_equal_1_persisted(self):
        class TestScriptB1(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.repeats = 1
                self.persistent = True

        # script is already stopped (interval=1, start_delay=False)
        script = create.create_script(TestScriptB1, key="test_script")
        assert script
        assert not script.is_active

    def test_create_script_w_repeats_equal_2(self):
        class TestScriptC(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.repeats = 2
                self.persistent = False

        script = create.create_script(TestScriptC, key="test_script")
        assert script is not None
        assert script.interval == 10
        assert script.repeats == 2
        assert script.key == "test_script"
        script.stop()

    def test_create_script_w_repeats_equal_1_and_delayed(self):
        class TestScriptD(DefaultScript):
            def at_script_creation(self):
                self.key = "test_script"
                self.interval = 10
                self.start_delay = True
                self.repeats = 1
                self.persistent = False

        script = create.create_script(TestScriptD, key="test_script")
        assert script is not None
        assert script.interval == 10
        assert script.repeats == 1
        assert script.key == "test_script"
        script.stop()


class TestCreateHelpEntry(TestCase):

    help_entry = """
    Qui laborum voluptas quis commodi ipsum quo temporibus eum. Facilis
    assumenda facilis architecto in corrupti. Est placeat eum amet qui beatae
    reiciendis. Accusamus vel aspernatur ab ex. Quam expedita sed expedita
    consequuntur est dolorum non exercitationem.

    Ipsa vel ut dolorem voluptatem adipisci velit. Sit odit temporibus mollitia
    illum ipsam placeat. Rem et ipsum dolor. Hic eum tempore excepturi qui veniam
    magni.

    Excepturi quam repellendus inventore excepturi fugiat quo quasi molestias.
    Nostrum ut assumenda enim a. Repellat quis omnis est officia accusantium. Fugit
    facere qui aperiam. Perspiciatis commodi dolores ipsam nemo consequatur
    quisquam qui non. Adipisci et molestias voluptatum est sed fugiat facere.

    """

    def test_create_help_entry__simple(self):
        entry = create.create_help_entry("testentry", self.help_entry, category="Testing")
        self.assertEqual(entry.key, "testentry")
        self.assertEqual(entry.entrytext, self.help_entry)
        self.assertEqual(entry.help_category, "Testing")

        # creating same-named entry should not work (must edit existing)
        self.assertFalse(create.create_help_entry("testentry", "testtext"))

    def test_create_help_entry__complex(self):
        locks = "foo:false();bar:true()"
        aliases = ["foo", "bar", "tst"]
        tags = [("tag1", "help"), ("tag2", "help"), ("tag3", "help")]

        entry = create.create_help_entry(
            "testentry",
            self.help_entry,
            category="Testing",
            locks=locks,
            aliases=aliases,
            tags=tags,
        )
        self.assertTrue(all(lock in entry.locks.all() for lock in locks.split(";")))
        self.assertEqual(list(entry.aliases.all()).sort(), aliases.sort())
        self.assertEqual(entry.tags.all(return_key_and_category=True), tags)


class TestCreateMessage(BaseEvenniaTest):

    msgtext = """
    Qui laborum voluptas quis commodi ipsum quo temporibus eum. Facilis
    assumenda facilis architecto in corrupti. Est placeat eum amet qui beatae
    reiciendis. Accusamus vel aspernatur ab ex. Quam expedita sed expedita
    consequuntur est dolorum non exercitationem.
    """

    def test_create_msg__simple(self):
        # from evennia import set_trace;set_trace()
        msg = create.create_message(self.char1, self.msgtext, header="TestHeader")
        msg.senders = "ExternalSender"
        msg.receivers = self.char2
        msg.receivers = "ExternalReceiver"
        self.assertEqual(msg.message, self.msgtext)
        self.assertEqual(msg.header, "TestHeader")
        self.assertEqual(msg.senders, [self.char1, "ExternalSender"])
        self.assertEqual(msg.receivers, [self.char2, "ExternalReceiver"])

    def test_create_msg__custom(self):
        locks = "foo:false();bar:true()"
        tags = ["tag1", "tag2", "tag3"]
        msg = create.create_message(
            self.char1,
            self.msgtext,
            header="TestHeader",
            receivers=[self.char1, self.char2, "ExternalReceiver"],
            locks=locks,
            tags=tags,
        )
        self.assertEqual(set(msg.receivers), set([self.char1, self.char2, "ExternalReceiver"]))
        self.assertTrue(all(lock in msg.locks.all() for lock in locks.split(";")))
        self.assertEqual(msg.tags.all(), tags)


class TestCreateChannel(TestCase):
    def test_create_channel__simple(self):
        chan = create.create_channel("TestChannel1", desc="Testing channel")
        self.assertEqual(chan.key, "TestChannel1")
        self.assertEqual(chan.db.desc, "Testing channel")

    def test_create_channel__complex(self):
        locks = "foo:false();bar:true()"
        tags = ["tag1", "tag2", "tag3"]
        aliases = ["foo", "bar", "tst"]

        chan = create.create_channel(
            "TestChannel2", desc="Testing channel", aliases=aliases, locks=locks, tags=tags
        )
        self.assertTrue(all(lock in chan.locks.all() for lock in locks.split(";")))
        self.assertEqual(chan.tags.all(), tags)
        self.assertEqual(list(chan.aliases.all()).sort(), aliases.sort())
