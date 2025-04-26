from unittest import skip

from evennia.objects.models import ObjectDB
from evennia.objects.objects import (
    DefaultCharacter,
    DefaultExit,
    DefaultObject,
    DefaultRoom,
)
from evennia.typeclasses.attributes import AttributeProperty
from evennia.typeclasses.tags import (
    AliasProperty,
    PermissionProperty,
    TagCategoryProperty,
    TagProperty,
)
from evennia.utils import create, search
from evennia.utils.ansi import strip_ansi
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

    def test_object_default_description(self):
        obj, errors = DefaultObject.create("void")
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertIsNone(obj.db.desc)
        self.assertEqual(obj.default_description, obj.get_display_desc(obj))

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

    def test_character_default_description(self):
        obj, errors = DefaultCharacter.create("dementor")
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertIsNone(obj.db.desc)
        self.assertEqual(obj.default_description, obj.get_display_desc(obj))

    def test_room_create(self):
        description = "A dimly-lit alley behind the local Chinese restaurant."
        obj, errors = DefaultRoom.create("alley", self.account, description=description, ip=self.ip)
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)

    def test_room_default_description(self):
        obj, errors = DefaultRoom.create("black hole")
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertIsNone(obj.db.desc)
        self.assertEqual(obj.default_description, obj.get_display_desc(obj))

    def test_exit_create(self):
        description = (
            "The steaming depths of the dumpster, ripe with refuse in various states of"
            " decomposition."
        )
        obj, errors = DefaultExit.create(
            "in", self.room1, self.room2, account=self.account, description=description, ip=self.ip
        )
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertEqual(description, obj.db.desc)
        self.assertEqual(obj.db.creator_ip, self.ip)

    def test_exit_default_description(self):
        obj, errors = DefaultExit.create("the nothing")
        self.assertTrue(obj, errors)
        self.assertFalse(errors, errors)
        self.assertIsNone(obj.db.desc)
        self.assertEqual(obj.default_description, obj.get_display_desc(obj))

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

    def test_exit_order(self):
        DefaultExit.create("south", self.room1, self.room2, account=self.account)
        DefaultExit.create("portal", self.room1, self.room2, account=self.account)
        DefaultExit.create("north", self.room1, self.room2, account=self.account)
        DefaultExit.create("aperture", self.room1, self.room2, account=self.account)

        # in creation order
        exits = strip_ansi(self.room1.get_display_exits(self.char1))
        self.assertEqual(exits, "Exits: out, south, portal, north, and aperture")

        # in specified order with unspecified exits alpbabetically on the end
        exit_order = ("north", "south", "out")
        exits = strip_ansi(self.room1.get_display_exits(self.char1, exit_order=exit_order))
        self.assertEqual(exits, "Exits: north, south, out, aperture, and portal")

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

    def test_search_plural_form(self):
        """Test searching for plural form of objects"""
        coin1 = DefaultObject.create("coin", location=self.room1)[0]
        coin2 = DefaultObject.create("coin", location=self.room1)[0]
        coin3 = DefaultObject.create("coin", location=self.room1)[0]
        # build the numbered aliases
        coin1.get_numbered_name(2, self.char1)
        coin2.get_numbered_name(3, self.char1)
        coin3.get_numbered_name(4, self.char1)

        self.assertEqual(self.char1.search("coin", quiet=True), [coin1, coin2, coin3])
        self.assertEqual(self.char1.search("coins", quiet=True), [coin1, coin2, coin3])

    def test_get_default_lockstring_base(self):
        pattern = (
            f"control:pid({self.account.id}) or id({self.char1.id}) or"
            f" perm(Admin);delete:pid({self.account.id}) or id({self.char1.id}) or"
            f" perm(Admin);edit:pid({self.account.id}) or id({self.char1.id}) or perm(Admin)"
        )
        self.assertEqual(
            DefaultObject.get_default_lockstring(account=self.account, caller=self.char1), pattern
        )

    def test_search_by_tag_kwarg(self):
        "Test the by_tag method"

        self.obj1.tags.add("plugh", category="adventure")

        self.assertEqual(self.char1.search("Obj", quiet=True), [self.obj1])
        # should not find a match
        self.assertEqual(self.char1.search("Dummy", quiet=True), [])
        # should still not find a match
        self.assertEqual(self.char1.search("Dummy", tags=[("plugh", "adventure")], quiet=True), [])

        self.assertEqual(list(search.search_object("Dummy", tags=[("plugh", "adventure")])), [])
        self.assertEqual(
            list(search.search_object("Obj", tags=[("plugh", "adventure")])), [self.obj1]
        )
        self.assertEqual(list(search.search_object("Obj", tags=[("dummy", "adventure")])), [])

    def test_get_default_lockstring_room(self):
        pattern = (
            f"control:pid({self.account.id}) or id({self.char1.id}) or"
            f" perm(Admin);delete:pid({self.account.id}) or id({self.char1.id}) or"
            f" perm(Admin);edit:pid({self.account.id}) or id({self.char1.id}) or perm(Admin)"
        )
        self.assertEqual(
            DefaultRoom.get_default_lockstring(account=self.account, caller=self.char1), pattern
        )

    def test_get_default_lockstring_exit(self):
        pattern = (
            f"control:pid({self.account.id}) or id({self.char1.id}) or"
            f" perm(Admin);delete:pid({self.account.id}) or id({self.char1.id}) or"
            f" perm(Admin);edit:pid({self.account.id}) or id({self.char1.id}) or perm(Admin)"
        )
        self.assertEqual(
            DefaultExit.get_default_lockstring(account=self.account, caller=self.char1), pattern
        )

    def test_get_default_lockstring_character(self):
        pattern = (
            f"puppet:pid({self.account.id}) or perm(Developer) or"
            f" pperm(Developer);delete:pid({self.account.id}) or"
            f" perm(Admin);edit:pid({self.account.id}) or perm(Admin)"
        )
        self.assertEqual(
            DefaultCharacter.get_default_lockstring(account=self.account, caller=self.char1),
            pattern,
        )

    def test_get_name_without_article(self):
        self.assertEqual(self.obj1.get_numbered_name(1, self.char1, return_string=True), "an Obj")
        self.assertEqual(
            self.obj1.get_numbered_name(1, self.char1, return_string=True, no_article=True), "Obj"
        )


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

    def test_get_objs_with_key_or_alias(self):
        query = ObjectDB.objects.get_objs_with_key_or_alias("Char")
        self.assertEqual(list(query), [self.char1])
        query = ObjectDB.objects.get_objs_with_key_or_alias(
            "Char", typeclasses="evennia.objects.objects.DefaultObject"
        )
        self.assertEqual(list(query), [])
        query = ObjectDB.objects.get_objs_with_key_or_alias(
            "Char", candidates=[self.char1, self.char2]
        )
        self.assertEqual(list(query), [self.char1])

        self.char1.aliases.add("test alias")
        query = ObjectDB.objects.get_objs_with_key_or_alias("test alias")
        self.assertEqual(list(query), [self.char1])

        query = ObjectDB.objects.get_objs_with_key_or_alias("")
        self.assertFalse(query)
        query = ObjectDB.objects.get_objs_with_key_or_alias("", exact=False)
        self.assertEqual(list(query), list(ObjectDB.objects.all().order_by("id")))

        query = ObjectDB.objects.get_objs_with_key_or_alias(
            "", exact=False, typeclasses="evennia.objects.objects.DefaultCharacter"
        )
        self.assertEqual(list(query), [self.char1, self.char2])

    def test_key_alias_search_partial_match(self):
        """
        verify that get_objs_with_key_or_alias will partial match the first part of
        any words in the name, when given in the correct order
        """
        self.obj1.key = "big sword"
        self.obj2.key = "shiny sword"

        # beginning of "sword", should match both
        query = ObjectDB.objects.get_objs_with_key_or_alias("sw", exact=False)
        self.assertEqual(list(query), [self.obj1, self.obj2])

        # middle of "sword", should NOT match
        query = ObjectDB.objects.get_objs_with_key_or_alias("wor", exact=False)
        self.assertEqual(list(query), [])

        # beginning of "big" then "sword", should match obj1
        query = ObjectDB.objects.get_objs_with_key_or_alias("b sw", exact=False)
        self.assertEqual(list(query), [self.obj1])

        # beginning of "sword" then "big", should NOT match
        query = ObjectDB.objects.get_objs_with_key_or_alias("sw b", exact=False)
        self.assertEqual(list(query), [])

    def test_search_object(self):
        self.char1.tags.add("test tag")
        self.obj1.tags.add("test tag")

        query = ObjectDB.objects.search_object("", exact=False, tags=[("test tag", None)])
        self.assertEqual(list(query), [self.obj1, self.char1])

        query = ObjectDB.objects.search_object("Char", tags=[("invalid tag", None)])
        self.assertFalse(query)

        query = ObjectDB.objects.search_object(
            "",
            exact=False,
            tags=[("test tag", None)],
            typeclass="evennia.objects.objects.DefaultCharacter",
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
    attr5 = AttributeProperty(default=list, autocreate=False)
    attr6 = AttributeProperty(default=[None], autocreate=False)
    attr7 = AttributeProperty(default=list)
    attr8 = AttributeProperty(default=[None])
    cusattr = CustomizedProperty(default=5)
    tag1 = TagProperty()
    tag2 = TagProperty(category="tagcategory")
    tag3 = SubTagProperty()
    testalias = AliasProperty()
    testperm = PermissionProperty()
    awaretest = 5
    settest = 0
    tagcategory1 = TagCategoryProperty("category_tag1")
    tagcategory2 = TagCategoryProperty("category_tag1", "category_tag2", "category_tag3")

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

    def test_attribute_properties(self):
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

    def test_tag_properties(self):
        obj = self.obj

        self.assertTrue(obj.tags.has("tag1"))
        self.assertTrue(obj.tags.has("tag2", category="tagcategory"))
        self.assertTrue(obj.tags.has("tag3"))

        self.assertTrue(obj.aliases.has("testalias"))
        self.assertTrue(obj.permissions.has("testperm"))

        # Verify that regular properties do not get fetched in init_evennia_properties,
        # only Attribute or TagProperties.
        self.assertFalse(hasattr(obj, "property_initialized"))

    def test_tag_category_properties(self):
        obj = self.obj

        self.assertFalse(obj.tags.has("category_tag1"))  # no category
        self.assertTrue(obj.tags.has("category_tag1", category="tagcategory1"))
        self.assertTrue(obj.tags.has("category_tag1", category="tagcategory2"))
        self.assertTrue(obj.tags.has("category_tag2", category="tagcategory2"))
        self.assertTrue(obj.tags.has("category_tag3", category="tagcategory2"))

        self.assertEqual(obj.tagcategory1, ["category_tag1"])
        self.assertEqual(
            set(obj.tagcategory2), set(["category_tag1", "category_tag2", "category_tag3"])
        )

    def test_tag_category_properties_external_modification(self):
        obj = self.obj

        self.assertEqual(obj.tagcategory1, ["category_tag1"])
        self.assertEqual(
            set(obj.tagcategory2), set(["category_tag1", "category_tag2", "category_tag3"])
        )

        # add extra tag to category
        obj.tags.add("category_tag2", category="tagcategory1")
        self.assertEqual(
            set(obj.tags.get(category="tagcategory1")),
            set(["category_tag1", "category_tag2"]),
        )
        self.assertEqual(set(obj.tagcategory1), set(["category_tag1", "category_tag2"]))

        # add/remove extra tags to category
        obj.tags.add("category_tag4", category="tagcategory2")
        obj.tags.remove("category_tag3", category="tagcategory2")
        self.assertEqual(
            set(obj.tags.get(category="tagcategory2", return_list=True)),
            set(["category_tag1", "category_tag2", "category_tag4"]),
        )
        # note that when we access the property again, it will be updated to contain the same tags
        self.assertEqual(
            set(obj.tagcategory2),
            set(["category_tag1", "category_tag2", "category_tag3", "category_tag4"]),
        )

        del obj.tagcategory1
        # should be deleted from database
        self.assertEqual(obj.tags.get(category="tagcategory1", return_list=True), [])
        # accessing the property should return the default value
        self.assertEqual(obj.tagcategory1, ["category_tag1"])

        del obj.tagcategory2
        # should be deleted from database
        self.assertEqual(obj.tags.get(category="tagcategory2", return_list=True), [])
        # accessing the property should return the default value
        self.assertEqual(
            set(obj.tagcategory2), set(["category_tag1", "category_tag2", "category_tag3"])
        )

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

    @skip("TODO: Needs more research")
    def test_stored_object_queries(self):
        """,
        Test https://github.com/evennia/evennia/issues/3155, where AttributeProperties
        holding another object references would lead to db queries not finding
        that nested object.

        """
        obj1 = create.create_object(TestObjectPropertiesClass, key="obj1")
        obj2 = create.create_object(TestObjectPropertiesClass, key="obj2")
        obj1.attr1 = obj2

        # check property works
        self.assertEqual(obj1.attr1, obj2)

        self.assertEqual(obj1.attributes.get("attr1"), obj2)
        obj1.attributes.reset_cache()
        self.assertEqual(obj1.attributes.get("attr1"), obj2)

        self.assertIn(obj1, TestObjectPropertiesClass.objects.get_by_attribute("attr1"))
        self.assertEqual(
            list(TestObjectPropertiesClass.objects.get_by_attribute("attr1", value=obj2)), [obj1]
        )

        # now we query for it by going via the Attribute table
        query = TestObjectPropertiesClass.objects.filter(
            db_attributes__db_key="attr1", db_attributes__db_value=obj2
        )

        self.assertEqual(list(query), [obj1])

        obj1.delete()
        obj2.delete()

    def test_not_create_attribute_with_autocreate_false(self):
        """
        Test that AttributeProperty with autocreate=False does not create an attribute in the database.

        """
        obj = create.create_object(TestObjectPropertiesClass, key="obj1")

        self.assertEqual(obj.attr3, "attr3")
        self.assertEqual(obj.attributes.get("attr3"), None)

        self.assertEqual(obj.attr5, [])
        self.assertEqual(obj.attributes.get("attr5"), None)

        obj.delete()

    def test_callable_defaults__autocreate_false(self):
        """
        Test https://github.com/evennia/evennia/issues/3488, where a callable default value like `list`
        would produce an infinitely empty result even when appended to.

        """
        obj1 = create.create_object(TestObjectPropertiesClass, key="obj1")
        obj2 = create.create_object(TestObjectPropertiesClass, key="obj2")

        self.assertEqual(obj1.attr5, [])
        obj1.attr5.append(1)
        self.assertEqual(obj1.attr5, [1])

        # check cross-instance sharing
        self.assertEqual(obj2.attr5, [], "cross-instance sharing detected")

    def test_mutable_defaults__autocreate_false(self):
        """
        Test https://github.com/evennia/evennia/issues/3488, where a mutable default value (like a
        list `[]` or `[None]`) would not be updated in the database when appended to.

        Note that using a mutable default value is not recommended, as the mutable will share the
        same memory space across all instances of the class. This means that if one instance modifiesA
        the mutable, all instances will be affected.

        """
        obj1 = create.create_object(TestObjectPropertiesClass, key="obj1")
        obj2 = create.create_object(TestObjectPropertiesClass, key="obj2")

        self.assertEqual(obj1.attr6, [None])
        obj1.attr6.append(1)
        self.assertEqual(obj1.attr6, [None, 1])

        obj1.attr6[1] = 2
        self.assertEqual(obj1.attr6, [None, 2])

        # check cross-instance sharing
        self.assertEqual(obj2.attr6, [None], "cross-instance sharing detected")

        obj1.delete()
        obj2.delete()

    def test_callable_defaults__autocreate_true(self):
        """
        Test callables with autocreate=True.

        """
        obj1 = create.create_object(TestObjectPropertiesClass, key="obj1")
        obj2 = create.create_object(TestObjectPropertiesClass, key="obj1")

        self.assertEqual(obj1.attr7, [])
        obj1.attr7.append(1)
        self.assertEqual(obj1.attr7, [1])

        # check cross-instance sharing
        self.assertEqual(obj2.attr7, [])

    def test_mutable_defaults__autocreate_true(self):
        """
        Test mutable defaults with autocreate=True.

        """
        obj1 = create.create_object(TestObjectPropertiesClass, key="obj1")
        obj2 = create.create_object(TestObjectPropertiesClass, key="obj2")

        self.assertEqual(obj1.attr8, [None])
        obj1.attr8.append(1)
        self.assertEqual(obj1.attr8, [None, 1])

        obj1.attr8[1] = 2
        self.assertEqual(obj1.attr8, [None, 2])

        # check cross-instance sharing
        self.assertEqual(obj2.attr8, [None])

        obj1.delete()
        obj2.delete()
