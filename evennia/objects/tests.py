from evennia.utils.test_resources import EvenniaTest
from evennia import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit


class DefaultObjectTest(EvenniaTest):

    ip = '212.216.139.14'

    def test_object_create(self):
        description = 'A home for a grouch.'
        obj, errors = DefaultObject.create('trashcan', self.account, description=description, ip=self.ip)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)

    def test_character_create(self):
        description = 'A furry green monster, reeking of garbage.'
        obj, errors = DefaultCharacter.create('oscar', self.account, description=description, ip=self.ip)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)

    def test_room_create(self):
        description = 'A dimly-lit alley behind the local Chinese restaurant.'
        obj, errors = DefaultRoom.create('alley', self.account, description=description, ip=self.ip)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)

    def test_exit_create(self):
        description = 'The steaming depths of the dumpster, ripe with refuse in various states of decomposition.'
        obj, errors = DefaultExit.create('in', self.account, self.room1, self.room2, description=description, ip=self.ip)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)

    def test_urls(self):
        "Make sure objects are returning URLs"
        self.assertTrue(self.char1.get_absolute_url())
        self.assertTrue('admin' in self.char1.web_get_admin_url())

        self.assertTrue(self.room1.get_absolute_url())
        self.assertTrue('admin' in self.room1.web_get_admin_url())
