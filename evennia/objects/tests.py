from evennia import DefaultCharacter, DefaultExit, DefaultObject, DefaultRoom
from evennia.objects.models import ObjectDB
from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty
from evennia.typeclasses.tags import AliasProperty, PermissionProperty, TagProperty
from evennia.utils import create
from evennia.utils.test_resources import BaseEvenniaTest, EvenniaTestCase


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

    def test_exit_get_return_exit(self):
        ex1, _ = DefaultExit.create("north", self.room1, self.room2, account=self.account)
        single_return_exit = ex1.get_return_exit()
        all_return_exit = ex1.get_return_exit(return_all=True)
        self.assertEqual(single_return_exit, None)
        self.assertEqual(len(all_return_exit), 0)

        ex2, _ = DefaultExit.create("south", self.room2, self.room1, account=self.account)
        single_return_exit = ex1.get_return_exit()
        all_return_exit = ex1.get_return_exit(return_all=True)
        self.assertEqual(single_return_exit, ex2)
        self.assertEqual(len(all_return_exit), 1)

        ex3, _ = DefaultExit.create("also_south", self.room2, self.room1, account=self.account)
        all_return_exit = ex1.get_return_exit(return_all=True)
        self.assertEqual(len(all_return_exit), 2)

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


class SubAttributeProperty(AttributeProperty):
    pass


class SubTagProperty(TagProperty):
    pass


class CustomizedProperty(AttributeProperty):
    def at_set(self, value, obj):
        obj.settest = value
        return value

    def at_get(self, value, obj):
        return value + obj.awaretest


class TestObjectPropertiesClass(DefaultObject):
    attr1 = AttributeProperty(default="attr1")
    attr2 = AttributeProperty(default="attr2", category="attrcategory")
    attr3 = AttributeProperty(default="attr3", autocreate=False)
    attr4 = SubAttributeProperty(default="attr4")
    cusattr = CustomizedProperty(default=5)
    tag1 = TagProperty()
    tag2 = TagProperty(category="tagcategory")
    tag3 = SubTagProperty()
    testalias = AliasProperty()
    testperm = PermissionProperty()
    awaretest = 5
    settest = 0

    @property
    def base_property(self):
        self.property_initialized = True


class TestProperties(EvenniaTestCase):
    """
    Test Properties.

    """

    def setUp(self):
        self.obj: TestObjectPropertiesClass = create.create_object(
            TestObjectPropertiesClass, key="testobj"
        )

    def tearDown(self):
        self.obj.delete()

    def test_properties(self):
        """
        Test all properties assigned at class level.
        """
        obj = self.obj

        self.assertEqual(obj.db.attr1, "attr1")
        self.assertEqual(obj.attributes.get("attr1"), "attr1")
        self.assertEqual(obj.attr1, "attr1")

        self.assertEqual(obj.attributes.get("attr2", category="attrcategory"), "attr2")
        self.assertEqual(obj.db.attr2, None)  # category mismatch
        self.assertEqual(obj.attr2, "attr2")

        self.assertEqual(obj.db.attr3, None)  # non-autocreate, so not in db yet
        self.assertFalse(obj.attributes.has("attr3"))
        self.assertEqual(obj.attr3, "attr3")

        self.assertEqual(obj.db.attr4, "attr4")
        self.assertEqual(obj.attributes.get("attr4"), "attr4")
        self.assertEqual(obj.attr4, "attr4")

        obj.attr3 = "attr3b"  # stores it in db!

        self.assertEqual(obj.db.attr3, "attr3b")
        self.assertTrue(obj.attributes.has("attr3"))

        self.assertTrue(obj.tags.has("tag1"))
        self.assertTrue(obj.tags.has("tag2", category="tagcategory"))
        self.assertTrue(obj.tags.has("tag3"))

        self.assertTrue(obj.aliases.has("testalias"))
        self.assertTrue(obj.permissions.has("testperm"))

        # Verify that regular properties do not get fetched in init_evennia_properties,
        # only Attribute or TagProperties.
        self.assertFalse(hasattr(obj, "property_initialized"))

    def test_object_awareness(self):
        """Test the "object-awareness" of customized AttributeProperty getter/setters"""
        obj = self.obj

        # attribute properties receive on obj ref in the getter/setter that can customize return
        self.assertEqual(obj.cusattr, 10)
        self.assertEqual(obj.settest, 5)
        obj.awaretest = 10
        self.assertEqual(obj.cusattr, 15)
        obj.cusattr = 10
        self.assertEqual(obj.cusattr, 20)
        self.assertEqual(obj.settest, 10)

        # attribute value mutates if you do += or similar (combined get-set)
        obj.cusattr += 10
        self.assertEqual(obj.attributes.get("cusattr"), 30)
        self.assertEqual(obj.settest, 30)
        self.assertEqual(obj.cusattr, 40)
        obj.awaretest = 0
        obj.cusattr += 20
        self.assertEqual(obj.attributes.get("cusattr"), 50)
        self.assertEqual(obj.settest, 50)
        self.assertEqual(obj.cusattr, 50)
        del obj.cusattr
        self.assertEqual(obj.cusattr, 5)
        self.assertEqual(obj.settest, 5)
