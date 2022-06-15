from evennia.utils.test_resources import EvenniaTest
from evennia import search_tag

class TestSearch(EvenniaTest):

    def test_search_script_tag(self):
        """Check that a script can be found by its tag."""
        script, errors = DefaultScript.create("a-script")
        script.tags.add("a-tag")
        found = search_tag("a-tag")
        self.assertEqual(len(found), 1)
        self.assertEqual(script.key, found[0].key)
        
