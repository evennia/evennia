from evennia.scripts.scripts import DefaultScript
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.search import search_script_attribute, search_script_tag

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

