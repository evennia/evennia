"""
Unit tests for the prototypes and spawner

"""

from random import randint
import mock
from anything import Anything, Something
from evennia.utils.test_resources import EvenniaTest
from evennia.prototypes import spawner, prototypes as protlib


_PROTPARENTS = {
    "NOBODY": {},
    "GOBLIN": {
        "key": "goblin grunt",
        "health": lambda: randint(1, 1),
        "resists": ["cold", "poison"],
        "attacks": ["fists"],
        "weaknesses": ["fire", "light"]
    },
    "GOBLIN_WIZARD": {
        "prototype": "GOBLIN",
        "key": "goblin wizard",
        "spells": ["fire ball", "lighting bolt"]
    },
    "GOBLIN_ARCHER": {
        "prototype": "GOBLIN",
        "key": "goblin archer",
        "attacks": ["short bow"]
    },
    "ARCHWIZARD": {
        "attacks": ["archwizard staff"],
    },
    "GOBLIN_ARCHWIZARD": {
        "key": "goblin archwizard",
        "prototype": ("GOBLIN_WIZARD", "ARCHWIZARD")
    }
}


class TestPrototypes(EvenniaTest):
    pass


class TestSpawner(EvenniaTest):

    def setUp(self):
        super(TestSpawner, self).setUp()
        self.prot1 = {"prototype_key": "testprototype"}

    def test_spawn(self):
        obj1 = spawner.spawn(self.prot1)
        # check spawned objects have the right tag
        self.assertEqual(list(protlib.search_objects_with_prototype("testprototype")), obj1)
        self.assertEqual([o.key for o in spawner.spawn(
                          _PROTPARENTS["GOBLIN"], _PROTPARENTS["GOBLIN_ARCHWIZARD"],
                          prototype_parents=_PROTPARENTS)], ['goblin grunt', 'goblin archwizard'])


class TestUtils(EvenniaTest):

    def test_prototype_from_object(self):
        self.maxDiff = None
        self.obj1.attributes.add("test", "testval")
        self.obj1.tags.add('foo')
        new_prot = spawner.prototype_from_object(self.obj1)
        self.assertEqual(
            {'attrs': [('test', 'testval', None, [''])],
             'home': Something,
             'key': 'Obj',
             'location': Something,
             'locks': ['call:true()',
                       'control:perm(Developer)',
                       'delete:perm(Admin)',
                       'edit:perm(Admin)',
                       'examine:perm(Builder)',
                       'get:all()',
                       'puppet:pperm(Developer)',
                       'tell:perm(Admin)',
                       'view:all()'],
             'prototype_desc': 'Built from Obj',
             'prototype_key': Something,
             'prototype_locks': 'spawn:all();edit:all()',
             'tags': [(u'foo', None, None)],
             'typeclass': 'evennia.objects.objects.DefaultObject'}, new_prot)

    def test_update_objects_from_prototypes(self):

        self.maxDiff = None
        self.obj1.attributes.add('oldtest', 'to_remove')

        old_prot = spawner.prototype_from_object(self.obj1)

        # modify object away from prototype
        self.obj1.attributes.add('test', 'testval')
        self.obj1.aliases.add('foo')
        self.obj1.key = 'NewObj'

        # modify prototype
        old_prot['new'] = 'new_val'
        old_prot['test'] = 'testval_changed'
        old_prot['permissions'] = 'Builder'
        # this will not update, since we don't update the prototype on-disk
        old_prot['prototype_desc'] = 'New version of prototype'

        # diff obj/prototype
        pdiff = spawner.prototype_diff_from_object(old_prot, self.obj1)

        self.assertEqual(
             pdiff,
             {'aliases': 'REMOVE',
              'attrs': 'REPLACE',
              'home': 'KEEP',
              'key': 'UPDATE',
              'location': 'KEEP',
              'locks': 'KEEP',
              'new': 'UPDATE',
              'permissions': 'UPDATE',
              'prototype_desc': 'UPDATE',
              'prototype_key': 'UPDATE',
              'prototype_locks': 'KEEP',
              'test': 'UPDATE',
              'typeclass': 'KEEP'})

        # apply diff
        count = spawner.batch_update_objects_with_prototype(
            old_prot, diff=pdiff, objects=[self.obj1])
        self.assertEqual(count, 1)

        new_prot = spawner.prototype_from_object(self.obj1)
        self.assertEqual({'attrs': [('test', 'testval_changed', None, ['']),
                                    ('new', 'new_val', None, [''])],
                          'home': Something,
                          'key': 'Obj',
                          'location': Something,
                          'locks': ['call:true()',
                                    'control:perm(Developer)',
                                    'delete:perm(Admin)',
                                    'edit:perm(Admin)',
                                    'examine:perm(Builder)',
                                    'get:all()',
                                    'puppet:pperm(Developer)',
                                    'tell:perm(Admin)',
                                    'view:all()'],
                          'permissions': 'builder',
                          'prototype_desc': 'Built from Obj',
                          'prototype_key': Something,
                          'prototype_locks': 'spawn:all();edit:all()',
                          'typeclass': 'evennia.objects.objects.DefaultObject'},
                         new_prot)


class TestPrototypeStorage(EvenniaTest):

    def setUp(self):
        super(TestPrototypeStorage, self).setUp()
        self.prot1 = {"prototype_key": "testprototype"}
        self.prot2 = {"prototype_key": "testprototype2"}
        self.prot3 = {"prototype_key": "testprototype3"}

    def _get_metaproto(
            self, key='testprototype', desc='testprototype',
            locks=['edit:id(6) or perm(Admin)', 'use:all()'],
            tags=[], prototype={"key": "testprototype"}):
        return spawner.build_metaproto(key, desc, locks, tags, prototype)

    def _to_metaproto(self, db_prototype):
        return spawner.build_metaproto(
            db_prototype.key, db_prototype.desc, db_prototype.locks.all(),
            db_prototype.tags.get(category="db_prototype", return_list=True),
            db_prototype.attributes.get("prototype"))

    def test_prototype_storage(self):

        prot = spawner.save_db_prototype(self.char1, self.prot1, "testprot",
                                         desc='testdesc0', tags=["foo"])

        self.assertTrue(bool(prot))
        self.assertEqual(prot.db.prototype, self.prot1)
        self.assertEqual(prot.desc, "testdesc0")

        prot = spawner.save_db_prototype(self.char1, self.prot1, "testprot",
                                         desc='testdesc', tags=["fooB"])
        self.assertEqual(prot.db.prototype, self.prot1)
        self.assertEqual(prot.desc, "testdesc")
        self.assertTrue(bool(prot.tags.get("fooB", "db_prototype")))

        self.assertEqual(list(prot.__class__.objects.get_by_tag("foo", "db_prototype")), [prot])

        prot2 = spawner.save_db_prototype(self.char1, self.prot2, "testprot2",
                                          desc='testdesc2b', tags=["foo"])
        self.assertEqual(
            list(prot.__class__.objects.get_by_tag("foo", "db_prototype")), [prot, prot2])

        prot3 = spawner.save_db_prototype(self.char1, self.prot3, "testprot2", desc='testdesc2')
        self.assertEqual(prot2.id, prot3.id)
        self.assertEqual(
            list(prot.__class__.objects.get_by_tag("foo", "db_prototype")), [prot, prot2])

        # returns DBPrototype
        self.assertEqual(list(spawner.search_db_prototype("testprot", return_queryset=True)), [prot])

        prot = prot.db.prototype
        prot3 = prot3.db.prototype
        self.assertEqual(list(spawner.search_prototype("testprot")), [prot])
        self.assertEqual(
            list(spawner.search_prototype("testprot")), [self.prot1])
        # partial match
        self.assertEqual(list(spawner.search_prototype("prot")), [prot, prot3])
        self.assertEqual(list(spawner.search_prototype(tags="foo")), [prot, prot3])

        self.assertTrue(str(unicode(spawner.list_prototypes(self.char1))))
