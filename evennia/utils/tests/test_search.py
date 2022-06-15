from evennia.scripts.scripts import DefaultScript
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.search import search_script_tag

class TestSearch(EvenniaTest):

    def test_search_script_tag(self):
        """Check that a script can be found by its tag."""
        script, errors = DefaultScript.create("a-script")
        script.tags.add("a-tag")
        found = search_script_tag("a-tag")
        self.assertEqual(len(found), 1)
        self.assertEqual(script.key, found[0].key)
        
    def test_search_script_tag_category(self):
        """Check that a script can be found by its tag."""
        script, errors = DefaultScript.create("a-script")
        script.tags.add("a-tag", category="a-category")
        found = search_script_tag("a-tag", category="a-category")
        self.assertEqual(len(found), 1)
        self.assertEqual(script.key, found[0].key)
