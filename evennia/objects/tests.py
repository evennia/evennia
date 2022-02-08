from evennia.utils.test_resources import BaseEvenniaTest
from evennia import DefaultObject, DefaultCharacter, DefaultRoom, DefaultExit
from evennia.objects.models import ObjectDB
from evennia.utils import create


class DefaultObjectTest(BaseEvenniaTest):

    ip = "212.216.139.14"

    def test_object_create(self):
        description = "A home for a grouch."
        home = self.room1.dbref

        obj, errors = DefaultObject.create(
            "trashcan", self.account, description=description, ip=self.ip, home=home
        )
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)
        self.assertEqual(obj.db_home, self.room1)

    def test_character_create(self):
        description = "A furry green monster, reeking of garbage."
        home = self.room1.dbref

        obj, errors = DefaultCharacter.create(
            "oscar", self.account, description=description, ip=self.ip, home=home
        )
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)
        self.assertEqual(obj.db_home, self.room1)

    def test_character_create_noaccount(self):
        obj, errors = DefaultCharacter.create("oscar", None, home=self.room1.dbref)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(obj.db_home, self.room1)

    def test_character_create_weirdname(self):
        obj, errors = DefaultCharacter.create(
            "SigurðurÞórarinsson", self.account, home=self.room1.dbref
        )
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(obj.name, "SigurXurXorarinsson")

    def test_room_create(self):
        description = "A dimly-lit alley behind the local Chinese restaurant."
        obj, errors = DefaultRoom.create("alley", self.account, description=description, ip=self.ip)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)

    def test_exit_create(self):
        description = "The steaming depths of the dumpster, ripe with refuse in various states of decomposition."
        obj, errors = DefaultExit.create(
            "in", self.room1, self.room2, account=self.account, description=description, ip=self.ip
        )
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)

    def test_urls(self):
        "Make sure objects are returning URLs"
        self.assertTrue(self.char1.get_absolute_url())
        self.assertTrue("admin" in self.char1.web_get_admin_url())

        self.assertTrue(self.room1.get_absolute_url())
        self.assertTrue("admin" in self.room1.web_get_admin_url())

    def test_search_stacked(self):
        "Test searching stacks"
        coin1 = DefaultObject.create("coin", location=self.room1)[0]
        coin2 = DefaultObject.create("coin", location=self.room1)[0]
        colon = DefaultObject.create("colon", location=self.room1)[0]

        # stack
        self.assertEqual(self.char1.search("coin", stacked=2), [coin1, coin2])
        self.assertEqual(self.char1.search("coin", stacked=5), [coin1, coin2])
        # partial match to 'colon' - multimatch error since stack is not homogenous
        self.assertEqual(self.char1.search("co", stacked=2), None)


class TestObjectManager(BaseEvenniaTest):
    "Test object manager methods"

    def test_get_object_with_account(self):
        query = ObjectDB.objects.get_object_with_account("TestAccount").first()
        self.assertEqual(query, self.char1)
        query = ObjectDB.objects.get_object_with_account(self.account.dbref)
        self.assertEqual(query, self.char1)
        query = ObjectDB.objects.get_object_with_account("#123456")
        self.assertFalse(query)
        query = ObjectDB.objects.get_object_with_account("TestAccou").first()
        self.assertFalse(query)

        query = ObjectDB.objects.get_object_with_account("TestAccou", exact=False)
        self.assertEqual(tuple(query), (self.char1, self.char2))

        query = ObjectDB.objects.get_object_with_account(
            "TestAccou", candidates=[self.char1, self.obj1], exact=False
        )
        self.assertEqual(list(query), [self.char1])

    def test_get_objs_with_key_and_typeclass(self):
        query = ObjectDB.objects.get_objs_with_key_and_typeclass(
            "Char", "evennia.objects.objects.DefaultCharacter"
        )
        self.assertEqual(list(query), [self.char1])
        query = ObjectDB.objects.get_objs_with_key_and_typeclass(
            "Char", "evennia.objects.objects.DefaultObject"
        )
        self.assertFalse(query)
        query = ObjectDB.objects.get_objs_with_key_and_typeclass(
            "NotFound", "evennia.objects.objects.DefaultCharacter"
        )
        self.assertFalse(query)
        query = ObjectDB.objects.get_objs_with_key_and_typeclass(
            "Char", "evennia.objects.objects.DefaultCharacter", candidates=[self.char1, self.char2]
        )
        self.assertEqual(list(query), [self.char1])

    def test_get_objs_with_attr(self):
        self.obj1.db.testattr = "testval1"
        query = ObjectDB.objects.get_objs_with_attr("testattr")
        self.assertEqual(list(query), [self.obj1])
        query = ObjectDB.objects.get_objs_with_attr("testattr", candidates=[self.char1, self.obj1])
        self.assertEqual(list(query), [self.obj1])
        query = ObjectDB.objects.get_objs_with_attr("NotFound", candidates=[self.char1, self.obj1])
        self.assertFalse(query)

    def test_copy_object(self):
        "Test that all attributes and tags properly copy across objects"

        # Add some tags
        self.obj1.tags.add("plugh", category="adventure")
        self.obj1.tags.add("xyzzy")

        # Add some attributes
        self.obj1.attributes.add("phrase", "plugh", category="adventure")
        self.obj1.attributes.add("phrase", "xyzzy")

        # Create object copy
        obj2 = self.obj1.copy()

        # Make sure each of the tags were replicated
        self.assertTrue("plugh" in obj2.tags.all())
        self.assertTrue("plugh" in obj2.tags.get(category="adventure"))
        self.assertTrue("xyzzy" in obj2.tags.all())

        # Make sure each of the attributes were replicated
        self.assertEqual(obj2.attributes.get(key="phrase"), "xyzzy")
        self.assertEqual(self.obj1.attributes.get(key="phrase", category="adventure"), "plugh")
        self.assertEqual(obj2.attributes.get(key="phrase", category="adventure"), "plugh")


class TestContentHandler(BaseEvenniaTest):
    "Test the ContentHandler (obj.contents)"

    def test_object_create_remove(self):
        """Create/destroy object"""
        self.assertTrue(self.obj1 in self.room1.contents)
        self.assertTrue(self.obj2 in self.room1.contents)

        obj3 = create.create_object(key="obj3", location=self.room1)
        self.assertTrue(obj3 in self.room1.contents)

        obj3.delete()
        self.assertFalse(obj3 in self.room1.contents)

    def test_object_move(self):
        """Move object from room to room in various ways"""
        self.assertTrue(self.obj1 in self.room1.contents)
        # use move_to hook
        self.obj1.move_to(self.room2)
        self.assertFalse(self.obj1 in self.room1.contents)
        self.assertTrue(self.obj1 in self.room2.contents)

        # move back via direct setting of .location
        self.obj1.location = self.room1
        self.assertTrue(self.obj1 in self.room1.contents)
        self.assertFalse(self.obj1 in self.room2.contents)

    def test_content_type(self):
        self.assertEqual(
            set(self.room1.contents_get()),
            set([self.char1, self.char2, self.obj1, self.obj2, self.exit]),
        )
        self.assertEqual(
            set(self.room1.contents_get(content_type="object")), set([self.obj1, self.obj2])
        )
        self.assertEqual(
            set(self.room1.contents_get(content_type="character")), set([self.char1, self.char2])
        )
        self.assertEqual(set(self.room1.contents_get(content_type="exit")), set([self.exit]))

    def test_contents_order(self):
        """Move object from room to room in various ways"""
        self.assertEqual(
            self.room1.contents, [self.exit, self.obj1, self.obj2, self.char1, self.char2]
        )
        self.assertEqual(self.room2.contents, [])

        # use move_to hook to move obj1
        self.obj1.move_to(self.room2)
        self.assertEqual(self.room1.contents, [self.exit, self.obj2, self.char1, self.char2])
        self.assertEqual(self.room2.contents, [self.obj1])

        # move obj2
        self.obj2.move_to(self.room2)
        self.assertEqual(self.room1.contents, [self.exit, self.char1, self.char2])
        self.assertEqual(self.room2.contents, [self.obj1, self.obj2])

        # move back and forth - it should
        self.obj1.move_to(self.room1)
        self.assertEqual(self.room1.contents, [self.exit, self.char1, self.char2, self.obj1])
        self.obj1.move_to(self.room2)
        self.assertEqual(self.room2.contents, [self.obj2, self.obj1])

        # use move_to hook
        self.obj2.move_to(self.room1)
        self.obj2.move_to(self.room2)
        self.assertEqual(self.room2.contents, [self.obj1, self.obj2])
