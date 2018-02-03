"""
Unit tests for typeclass base system

"""

from evennia.utils.test_resources import EvenniaTest

# ------------------------------------------------------------
# Manager tests
# ------------------------------------------------------------


class TestTypedObjectManager(EvenniaTest):
    def _manager(self, methodname, *args, **kwargs):
        return getattr(self.obj1.__class__.objects, methodname)(*args, **kwargs)

    def test_get_by_tag_no_category(self):
        self.obj1.tags.add("tag1")
        self.obj2.tags.add("tag2")
        self.obj2.tags.add("tag3")
        self.assertEquals(list(self._manager("get_by_tag", "tag1")), [self.obj1l])
