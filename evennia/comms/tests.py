from evennia.utils.test_resources import EvenniaTest
from evennia import DefaultChannel


class ObjectCreationTest(EvenniaTest):
    def test_channel_create(self):
        description = "A place to talk about coffee."

        obj, errors = DefaultChannel.create("coffeetalk", description=description)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
