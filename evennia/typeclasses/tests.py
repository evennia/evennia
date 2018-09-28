"""
Unit tests for typeclass base system

"""

from evennia.utils.test_resources import EvenniaTest

# ------------------------------------------------------------
# Manager tests
# ------------------------------------------------------------


class TestTypedObjectManager(EvenniaTest):
    def _manager(self, methodname, *args, **kwargs):
        return list(getattr(self.obj1.__class__.objects, methodname)(*args, **kwargs))

    def test_get_by_tag_no_category(self):
        self.obj1.tags.add("tag1")
        self.obj1.tags.add("tag2")
        self.obj1.tags.add("tag2c")
        self.obj2.tags.add("tag2")
        self.obj2.tags.add("tag2a")
        self.obj2.tags.add("tag2b")
        self.obj2.tags.add("tag3 with spaces")
        self.obj2.tags.add("tag4")
        self.obj2.tags.add("tag2c")
        self.assertEquals(self._manager("get_by_tag", "tag1"), [self.obj1])
        self.assertEquals(self._manager("get_by_tag", "tag2"), [self.obj1, self.obj2])
        self.assertEquals(self._manager("get_by_tag", "tag2a"), [self.obj2])
        self.assertEquals(self._manager("get_by_tag", "tag3 with spaces"), [self.obj2])
        self.assertEquals(self._manager("get_by_tag", ["tag2a", "tag2b"]), [self.obj2])
        self.assertEquals(self._manager("get_by_tag", ["tag2a", "tag1"]), [])
        self.assertEquals(self._manager("get_by_tag", ["tag2a", "tag4", "tag2c"]), [self.obj2])

    def test_get_by_tag_and_category(self):
        self.obj1.tags.add("tag5", "category1")
        self.obj1.tags.add("tag6", )
        self.obj1.tags.add("tag7", "category1")
        self.obj1.tags.add("tag6", "category3")
        self.obj1.tags.add("tag7", "category4")
        self.obj2.tags.add("tag5", "category1")
        self.obj2.tags.add("tag5", "category2")
        self.obj2.tags.add("tag6", "category3")
        self.obj2.tags.add("tag7", "category1")
        self.obj2.tags.add("tag7", "category5")
        self.assertEquals(self._manager("get_by_tag", "tag5", "category1"), [self.obj1, self.obj2])
        self.assertEquals(self._manager("get_by_tag", "tag6", "category1"), [])
        self.assertEquals(self._manager("get_by_tag", "tag6", "category3"), [self.obj1, self.obj2])
        self.assertEquals(self._manager("get_by_tag", ["tag5", "tag6"],
                                        ["category1", "category3"]), [self.obj1, self.obj2])
        self.assertEquals(self._manager("get_by_tag", ["tag5", "tag7"],
                                        "category1"), [self.obj1, self.obj2])
        self.assertEquals(self._manager("get_by_tag", category="category1"), [self.obj1, self.obj2])
        self.assertEquals(self._manager("get_by_tag", category="category2"), [self.obj2])
        self.assertEquals(self._manager("get_by_tag", category=["category1", "category3"]),
                          [self.obj1, self.obj2])
        self.assertEquals(self._manager("get_by_tag", category=["category1", "category2"]),
                          [self.obj2])
        self.assertEquals(self._manager("get_by_tag", category=["category5", "category4"]), [])
