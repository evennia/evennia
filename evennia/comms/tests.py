from evennia import DefaultChannel
from evennia.utils.create import create_message
from evennia.utils.test_resources import BaseEvenniaTest


class ObjectCreationTest(BaseEvenniaTest):
    def test_channel_create(self):
        description = "A place to talk about coffee."

        obj, errors = DefaultChannel.create("coffeetalk", description=description)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)

    def test_message_create(self):
        msg = create_message("peewee herman", "heh-heh!", header="mail time!")
        self.assertTrue(msg)
        self.assertEqual(str(msg), "peewee herman->: heh-heh!")


class ChannelWholistTests(BaseEvenniaTest):
    def setUp(self):
        super().setUp()
        self.default_channel, _ = DefaultChannel.create(
            "coffeetalk", description="A place to talk about coffee."
        )
        self.default_channel.connect(self.obj1)

    def test_wholist_shows_subscribed_objects(self):
        expected = "Obj"
        result = self.default_channel.wholist
        self.assertEqual(expected, result)

    def test_wholist_shows_none_when_empty(self):
        # No one hates dogs
        empty_channel, _ = DefaultChannel.create(
            "doghaters", description="A place where dog haters unite."
        )
        expected = "<None>"
        result = empty_channel.wholist
        self.assertEqual(expected, result)

    def test_wholist_does_not_show_muted_objects(self):
        self.default_channel.mute(self.obj2)
        expected = "Obj"
        result = self.default_channel.wholist
        self.assertEqual(expected, result)

    def test_wholist_shows_connected_object_as_bold(self):
        self.default_channel.connect(self.char1)
        expected = "Obj, |wChar|n"
        result = self.default_channel.wholist
        self.assertEqual(expected, result)
