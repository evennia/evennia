from evennia import DefaultObject, DefaultRoom
from evennia.objects.models import ObjectDB
from evennia.scripts.scripts import DefaultScript
from evennia.utils.search import (
    search_object_attribute,
    search_script,
    search_script_attribute,
    search_script_tag,
    search_typeclass,
)
from evennia.utils.test_resources import EvenniaTest


class TestSearch(EvenniaTest):
    def test_search_script_tag(self):
        """Check that a script can be found by its tag."""
        script, errors = DefaultScript.create("a-script")
        script.tags.add("a-tag")
        found = search_script_tag("a-tag")
        self.assertEqual(len(found), 1, errors)
        self.assertEqual(script.key, found[0].key, errors)

    def test_search_script_tag_category(self):
        """Check that a script can be found by its tag and category."""
        script, errors = DefaultScript.create("a-script")
        script.tags.add("a-tag", category="a-category")
        found = search_script_tag("a-tag", category="a-category")
        self.assertEqual(len(found), 1, errors)
        self.assertEqual(script.key, found[0].key, errors)

    def test_search_script_tag_wrong_category(self):
        """Check that a script cannot be found by the wrong category."""
        script, errors = DefaultScript.create("a-script")
        script.tags.add("a-tag", category="a-category")
        found = search_script_tag("a-tag", category="wrong-category")
        self.assertEqual(len(found), 0, errors)

    def test_search_script_tag_wrong(self):
        """Check that a script cannot be found by the wrong tag."""
        script, errors = DefaultScript.create("a-script")
        script.tags.add("a-tag", category="a-category")
        found = search_script_tag("wrong-tag", category="a-category")
        self.assertEqual(len(found), 0, errors)

    def test_search_script_attribute(self):
        """Check that a script can be found by its attributes."""
        script, errors = DefaultScript.create("a-script")
        script.db.an_attribute = "some value"
        found = search_script_attribute(key="an_attribute", value="some value")
        self.assertEqual(len(found), 1, errors)
        self.assertEqual(script.key, found[0].key, errors)

    def test_search_script_attribute_wrong(self):
        """Check that a script cannot be found by wrong value of its attributes."""
        script, errors = DefaultScript.create("a-script")
        script.db.an_attribute = "some value"
        found = search_script_attribute(key="an_attribute", value="wrong value")
        self.assertEqual(len(found), 0, errors)

    def test_search_script_key(self):
        """Check that a script can be found by its key value."""
        script, errors = DefaultScript.create("a-script")
        found = search_script("a-script")
        self.assertEqual(len(found), 1, errors)
        self.assertEqual(script.key, found[0].key, errors)

    def test_search_script_wrong_key(self):
        """Check that a script cannot be found by a wrong key value."""
        script, errors = DefaultScript.create("a-script")
        found = search_script("wrong_key")
        self.assertEqual(len(found), 0, errors)

    def test_search_typeclass(self):
        """Check that an object can be found by typeclass"""
        DefaultObject.create("test_obj")
        found = search_typeclass("evennia.objects.objects.DefaultObject")
        self.assertEqual(len(found), 1)

    def test_search_wrong_typeclass(self):
        """Check that an object cannot be found by wrong typeclass"""
        DefaultObject.create("test_obj_2")
        with self.assertRaises(ImportError):
            search_typeclass("not.a.typeclass")

    def test_search_object_attribute(self):
        """Check that an object can be found by its attributes."""
        object, errors = DefaultObject.create("an-object")
        object.db.an_attribute = "some value"
        found = search_object_attribute(key="an_attribute", value="some value")
        self.assertEqual(len(found), 1, errors)
        self.assertEqual(object.key, found[0].key, errors)

    def test_search_object_attribute_wrong(self):
        """Check that an object cannot be found by wrong value of its attributes."""
        object, errors = DefaultObject.create("an-object")
        object.db.an_attribute = "some value"
        found = search_object_attribute(key="an_attribute", value="wrong value")
        self.assertEqual(len(found), 0, errors)
