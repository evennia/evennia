"""
Unit test for the spawner

"""

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import spawner


class TestPrototypeStorage(EvenniaTest):

    def setUp(self):
        super(TestPrototypeStorage, self).setUp()
        self.prot1 = {"key": "testprototype"}
        self.prot2 = {"key": "testprototype2"}
        self.prot3 = {"key": "testprototype3"}

    def _get_metaproto(
            self, key='testprototype', desc='testprototype', locks=['edit:id(6) or perm(Admin)', 'use:all()'],
            tags=[], prototype={"key": "testprototype"}):
        return spawner.build_metaproto(key, desc, locks, tags, prototype)

    def _to_metaproto(self, db_prototype):
        return spawner.build_metaproto(
            db_prototype.key, db_prototype.desc, db_prototype.locks.all(),
            db_prototype.tags.get(category="db_prototype", return_list=True),
            db_prototype.attributes.get("prototype"))

    def test_prototype_storage(self):

        prot = spawner.save_db_prototype(self.char1, "testprot", self.prot1, desc='testdesc0', tags=["foo"])

        self.assertTrue(bool(prot))
        self.assertEqual(prot.db.prototype, self.prot1)
        self.assertEqual(prot.desc, "testdesc0")

        prot = spawner.save_db_prototype(self.char1, "testprot", self.prot1, desc='testdesc', tags=["fooB"])
        self.assertEqual(prot.db.prototype, self.prot1)
        self.assertEqual(prot.desc, "testdesc")
        self.assertTrue(bool(prot.tags.get("fooB", "db_prototype")))

        self.assertEqual(list(prot.__class__.objects.get_by_tag("foo", "db_prototype")), [prot])

        prot2 = spawner.save_db_prototype(self.char1, "testprot2", self.prot2, desc='testdesc2b', tags=["foo"])
        self.assertEqual(list(prot.__class__.objects.get_by_tag("foo", "db_prototype")), [prot, prot2])

        prot3 = spawner.save_db_prototype(self.char1, "testprot2", self.prot3, desc='testdesc2')
        self.assertEqual(prot2.id, prot3.id)
        self.assertEqual(list(prot.__class__.objects.get_by_tag("foo", "db_prototype")), [prot, prot2])

        # returns DBPrototype
        self.assertEqual(list(spawner.search_db_prototype("testprot")), [prot])

        # returns metaprotos
        prot = self._to_metaproto(prot)
        prot3 = self._to_metaproto(prot3)
        self.assertEqual(list(spawner.search_prototype("testprot")), [prot])
        self.assertEqual(list(spawner.search_prototype("testprot", return_meta=False)), [self.prot1])
        # partial match
        self.assertEqual(list(spawner.search_prototype("prot")), [prot, prot3])
        self.assertEqual(list(spawner.search_prototype(tags="foo")), [prot, prot3])

        self.assertTrue(str(unicode(spawner.list_prototypes(self.char1))))
