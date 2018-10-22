from evennia.utils.test_resources import EvenniaTest

class DefaultObjectTest(EvenniaTest):
    
    def test_urls(self):
        "Make sure objects are returning URLs"
        self.assertTrue(self.char1.get_absolute_url())
        self.assertTrue('admin' in self.char1.web_get_admin_url())
        
        self.assertTrue(self.room1.get_absolute_url())
        self.assertTrue('admin' in self.room1.web_get_admin_url())