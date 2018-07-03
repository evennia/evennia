"""
Unit tests for the prototypes and spawner

"""

from random import randint
import mock
from anything import Something
from django.test.utils import override_settings
from evennia.utils.test_resources import EvenniaTest
from evennia.utils.tests.test_evmenu import TestEvMenu
from evennia.prototypes import spawner, prototypes as protlib
from evennia.prototypes import menus as olc_menus

from evennia.prototypes.prototypes import _PROTOTYPE_TAG_META_CATEGORY

_PROTPARENTS = {
    "NOBODY": {},
    "GOBLIN": {
        "prototype_key": "GOBLIN",
        "typeclass": "evennia.objects.objects.DefaultObject",
        "key": "goblin grunt",
        "health": lambda: randint(1, 1),
        "resists": ["cold", "poison"],
        "attacks": ["fists"],
        "weaknesses": ["fire", "light"]
    },
    "GOBLIN_WIZARD": {
        "prototype_parent": "GOBLIN",
        "key": "goblin wizard",
        "spells": ["fire ball", "lighting bolt"]
    },
    "GOBLIN_ARCHER": {
        "prototype_parent": "GOBLIN",
        "key": "goblin archer",
        "attacks": ["short bow"]
    },
    "ARCHWIZARD": {
        "prototype_parent": "GOBLIN",
        "attacks": ["archwizard staff"],
    },
    "GOBLIN_ARCHWIZARD": {
        "key": "goblin archwizard",
        "prototype_parent": ("GOBLIN_WIZARD", "ARCHWIZARD")
    }
}


class TestSpawner(EvenniaTest):

    def setUp(self):
        super(TestSpawner, self).setUp()
        self.prot1 = {"prototype_key": "testprototype",
                      "typeclass": "evennia.objects.objects.DefaultObject"}

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
             'prototype_tags': [],
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
              'prototype_tags': 'KEEP',
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
                          'prototype_tags': [],
                          'typeclass': 'evennia.objects.objects.DefaultObject'},
                         new_prot)


class TestProtLib(EvenniaTest):

    def setUp(self):
        super(TestProtLib, self).setUp()
        self.obj1.attributes.add("testattr", "testval")
        self.prot = spawner.prototype_from_object(self.obj1)

    def test_prototype_to_str(self):
        prstr = protlib.prototype_to_str(self.prot)
        self.assertTrue(prstr.startswith("|cprototype key:|n"))

    def test_check_permission(self):
        pass


@override_settings(PROT_FUNC_MODULES=['evennia.prototypes.protfuncs'], CLIENT_DEFAULT_WIDTH=20)
class TestProtFuncs(EvenniaTest):

    def setUp(self):
        super(TestProtFuncs, self).setUp()
        self.prot = {"prototype_key": "test_prototype",
                     "prototype_desc": "testing prot",
                     "key": "ExampleObj"}

    @mock.patch("evennia.prototypes.protfuncs.base_random", new=mock.MagicMock(return_value=0.5))
    @mock.patch("evennia.prototypes.protfuncs.base_randint", new=mock.MagicMock(return_value=5))
    def test_protfuncs(self):
        self.assertEqual(protlib.protfunc_parser("$random()"), 0.5)
        self.assertEqual(protlib.protfunc_parser("$randint(1, 10)"), 5)
        self.assertEqual(protlib.protfunc_parser("$left_justify(  foo  )"), "foo                 ")
        self.assertEqual(protlib.protfunc_parser("$right_justify( foo  )"), "                 foo")
        self.assertEqual(protlib.protfunc_parser("$center_justify(foo  )"), "        foo         ")
        self.assertEqual(protlib.protfunc_parser(
            "$full_justify(foo bar moo too)"), 'foo   bar   moo  too')
        self.assertEqual(
            protlib.protfunc_parser("$right_justify( foo  )", testing=True),
            ('unexpected indent (<unknown>, line 1)', '                 foo'))

        test_prot = {"key1": "value1",
                     "key2": 2}

        self.assertEqual(protlib.protfunc_parser(
            "$protkey(key1)", testing=True, prototype=test_prot), (None, "value1"))
        self.assertEqual(protlib.protfunc_parser(
            "$protkey(key2)", testing=True, prototype=test_prot), (None, 2))

        self.assertEqual(protlib.protfunc_parser("$add(1, 2)"), 3)
        self.assertEqual(protlib.protfunc_parser("$add(10, 25)"), 35)
        self.assertEqual(protlib.protfunc_parser(
            "$add('''[1,2,3]''', '''[4,5,6]''')"), [1, 2, 3, 4, 5, 6])
        self.assertEqual(protlib.protfunc_parser("$add(foo, bar)"), "foo bar")

        self.assertEqual(protlib.protfunc_parser("$sub(5, 2)"), 3)
        self.assertRaises(TypeError, protlib.protfunc_parser, "$sub(5, test)")

        self.assertEqual(protlib.protfunc_parser("$mult(5, 2)"), 10)
        self.assertEqual(protlib.protfunc_parser("$mult(  5 ,   10)"), 50)
        self.assertEqual(protlib.protfunc_parser("$mult('foo',3)"), "foofoofoo")
        self.assertEqual(protlib.protfunc_parser("$mult(foo,3)"), "foofoofoo")
        self.assertRaises(TypeError, protlib.protfunc_parser, "$mult(foo, foo)")

        self.assertEqual(protlib.protfunc_parser("$toint(5.3)"), 5)

        self.assertEqual(protlib.protfunc_parser("$div(5, 2)"), 2.5)
        self.assertEqual(protlib.protfunc_parser("$toint($div(5, 2))"), 2)
        self.assertEqual(protlib.protfunc_parser("$sub($add(5, 3), $add(10, 2))"), -4)

        self.assertEqual(protlib.protfunc_parser("$eval('2')"), '2')

        self.assertEqual(protlib.protfunc_parser(
            "$eval(['test', 1, '2', 3.5, \"foo\"])"), ['test', 1, '2', 3.5, 'foo'])
        self.assertEqual(protlib.protfunc_parser(
            "$eval({'test': '1', 2:3, 3: $toint(3.5)})"), {'test': '1', 2: 3, 3: 3})

        self.assertEqual(protlib.protfunc_parser("$obj(#1)", session=self.session), '#1')
        self.assertEqual(protlib.protfunc_parser("#1", session=self.session), '#1')
        self.assertEqual(protlib.protfunc_parser("$obj(Char)", session=self.session), '#6')
        self.assertEqual(protlib.protfunc_parser("$obj(Char)", session=self.session), '#6')
        self.assertEqual(protlib.protfunc_parser("$objlist(#1)", session=self.session), ['#1'])

        self.assertEqual(protlib.value_to_obj(
            protlib.protfunc_parser("#6", session=self.session)), self.char1)
        self.assertEqual(protlib.value_to_obj_or_any(
            protlib.protfunc_parser("#6", session=self.session)), self.char1)
        self.assertEqual(protlib.value_to_obj_or_any(
            protlib.protfunc_parser("[1,2,3,'#6',5]", session=self.session)),
                [1, 2, 3, self.char1, 5])


class TestPrototypeStorage(EvenniaTest):

    def setUp(self):
        super(TestPrototypeStorage, self).setUp()
        self.maxDiff = None

        self.prot1 = spawner.prototype_from_object(self.obj1)
        self.prot1['prototype_key'] = 'testprototype1'
        self.prot1['prototype_desc'] = 'testdesc1'
        self.prot1['prototype_tags'] = [('foo1', _PROTOTYPE_TAG_META_CATEGORY)]

        self.prot2 = self.prot1.copy()
        self.prot2['prototype_key'] = 'testprototype2'
        self.prot2['prototype_desc'] = 'testdesc2'
        self.prot2['prototype_tags'] = [('foo1', _PROTOTYPE_TAG_META_CATEGORY)]

        self.prot3 = self.prot2.copy()
        self.prot3['prototype_key'] = 'testprototype3'
        self.prot3['prototype_desc'] = 'testdesc3'
        self.prot3['prototype_tags'] = [('foo1', _PROTOTYPE_TAG_META_CATEGORY)]

    def test_prototype_storage(self):

        prot1 = protlib.create_prototype(**self.prot1)

        self.assertTrue(bool(prot1))
        self.assertEqual(prot1, self.prot1)

        self.assertEqual(prot1['prototype_desc'], "testdesc1")

        self.assertEqual(prot1['prototype_tags'], [("foo1", _PROTOTYPE_TAG_META_CATEGORY)])
        self.assertEqual(
            protlib.DbPrototype.objects.get_by_tag(
                "foo1", _PROTOTYPE_TAG_META_CATEGORY)[0].db.prototype, prot1)

        prot2 = protlib.create_prototype(**self.prot2)
        self.assertEqual(
            [pobj.db.prototype
             for pobj in protlib.DbPrototype.objects.get_by_tag(
                 "foo1", _PROTOTYPE_TAG_META_CATEGORY)],
            [prot1, prot2])

        # add to existing prototype
        prot1b = protlib.create_prototype(
            prototype_key='testprototype1', foo='bar', prototype_tags=['foo2'])

        self.assertEqual(
            [pobj.db.prototype
             for pobj in protlib.DbPrototype.objects.get_by_tag(
                 "foo2", _PROTOTYPE_TAG_META_CATEGORY)],
            [prot1b])

        self.assertEqual(list(protlib.search_prototype("testprototype2")), [prot2])
        self.assertNotEqual(list(protlib.search_prototype("testprototype1")), [prot1])
        self.assertEqual(list(protlib.search_prototype("testprototype1")), [prot1b])

        prot3 = protlib.create_prototype(**self.prot3)

        # partial match
        self.assertEqual(list(protlib.search_prototype("prot")), [prot1b, prot2, prot3])
        self.assertEqual(list(protlib.search_prototype(tags="foo1")), [prot1b, prot2, prot3])

        self.assertTrue(str(unicode(protlib.list_prototypes(self.char1))))


class _MockMenu(object):
    pass


class TestMenuModule(EvenniaTest):

    def setUp(self):
        super(TestMenuModule, self).setUp()

        # set up fake store
        self.caller = self.char1
        menutree = _MockMenu()
        self.caller.ndb._menutree = menutree

        self.test_prot = {"prototype_key": "test_prot",
                          "typeclass": "evennia.objects.objects.DefaultObject",
                          "prototype_locks": "edit:all();spawn:all()"}

    def test_helpers(self):

        caller = self.caller

        # general helpers

        self.assertEqual(olc_menus._get_menu_prototype(caller), {})
        self.assertEqual(olc_menus._is_new_prototype(caller), True)

        self.assertEqual(olc_menus._set_menu_prototype(caller, {}), {})

        self.assertEqual(
            olc_menus._set_prototype_value(caller, "key", "TestKey"), {"key": "TestKey"})
        self.assertEqual(olc_menus._get_menu_prototype(caller), {"key": "TestKey"})

        self.assertEqual(olc_menus._format_option_value(
            "key", required=True, prototype=olc_menus._get_menu_prototype(caller)), " (TestKey|n)")
        self.assertEqual(olc_menus._format_option_value(
            [1, 2, 3, "foo"], required=True), ' (1, 2, 3, foo|n)')

        self.assertEqual(olc_menus._set_property(
            caller, "ChangedKey", prop="key", processor=str, next_node="foo"), "foo")
        self.assertEqual(olc_menus._get_menu_prototype(caller), {"key": "ChangedKey"})

        self.assertEqual(olc_menus._wizard_options(
            "ThisNode", "PrevNode", "NextNode"),
            [{'goto': 'node_PrevNode', 'key': ('|wB|Wack', 'b'), 'desc': '|W(PrevNode)|n'},
             {'goto': 'node_NextNode', 'key': ('|wF|Worward', 'f'), 'desc': '|W(NextNode)|n'},
             {'goto': 'node_index', 'key': ('|wI|Wndex', 'i')},
             {'goto': ('node_validate_prototype', {'back': 'ThisNode'}),
                 'key': ('|wV|Walidate prototype', 'validate', 'v')}])

        self.assertEqual(olc_menus._validate_prototype(self.test_prot), (False, Something))
        self.assertEqual(olc_menus._validate_prototype(
            {"prototype_key": "testthing", "key": "mytest"}),
            (True, Something))

    def test_node_helpers(self):

        caller = self.caller

        with mock.patch("evennia.prototypes.menus.protlib.search_prototype",
                        new=mock.MagicMock(return_value=[self.test_prot])):
            # prototype_key helpers
            self.assertEqual(olc_menus._check_prototype_key(caller, "test_prot"),
                             "node_prototype_parent")
            caller.ndb._menutree.olc_new = True
            self.assertEqual(olc_menus._check_prototype_key(caller, "test_prot"),
                             "node_index")

            # prototype_parent helpers
            self.assertEqual(olc_menus._all_prototype_parents(caller), ['test_prot'])
            self.assertEqual(olc_menus._prototype_parent_examine(
                caller, 'test_prot'),
                "|cprototype key:|n test_prot, |ctags:|n None, |clocks:|n edit:all();spawn:all() "
                "\n|cdesc:|n None \n|cprototype:|n "
                "{\n  'typeclass': 'evennia.objects.objects.DefaultObject', \n}")
            self.assertEqual(olc_menus._prototype_parent_select(caller, self.test_prot), "node_key")
        self.assertEqual(olc_menus._get_menu_prototype(caller),
                         {'prototype_key': 'test_prot',
                          'prototype_locks': 'edit:all();spawn:all()',
                          'typeclass': 'evennia.objects.objects.DefaultObject'})

        # typeclass helpers
        with mock.patch("evennia.utils.utils.get_all_typeclasses",
                        new=mock.MagicMock(return_value={"foo": None, "bar": None})):
            self.assertEqual(olc_menus._all_typeclasses(caller),  ["bar", "foo"])
        self.assertTrue(olc_menus._typeclass_examine(
            caller, "evennia.objects.objects.DefaultObject").startswith("Typeclass |y"))

        self.assertEqual(olc_menus._typeclass_select(
            caller, "evennia.objects.objects.DefaultObject"), "node_key")
        # prototype_parent should be popped off here
        self.assertEqual(olc_menus._get_menu_prototype(caller),
                         {'prototype_key': 'test_prot',
                          'prototype_locks': 'edit:all();spawn:all()',
                          'typeclass': 'evennia.objects.objects.DefaultObject'})

        # attr helpers
        self.assertEqual(olc_menus._caller_attrs(caller), [])
        self.assertEqual(olc_menus._add_attr(caller, "test1=foo1"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._add_attr(caller, "test2;cat1=foo2"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._add_attr(caller, "test3;cat2;edit:false()=foo3"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._add_attr(caller, "test4;cat3;set:true();edit:false()=foo4"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._add_attr(caller, "test5;cat4;set:true();edit:false()=123"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._caller_attrs(
            caller),
            [("test1", "foo1", None, ''),
             ("test2", "foo2", "cat1", ''),
             ("test3", "foo3", "cat2", "edit:false()"),
             ("test4", "foo4", "cat3", "set:true();edit:false()"),
             ("test5", '123', "cat4", "set:true();edit:false()")])
        self.assertEqual(olc_menus._edit_attr(caller, "test1", "1;cat5;edit:all()"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._examine_attr(caller, "test1"), Something)

        # tag helpers
        self.assertEqual(olc_menus._caller_tags(caller), [])
        self.assertEqual(olc_menus._add_tag(caller, "foo1"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._add_tag(caller, "foo2;cat1"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._add_tag(caller, "foo3;cat2;dat1"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._caller_tags(
            caller),
            [('foo1', None, ""),
             ('foo2', 'cat1', ""),
             ('foo3', 'cat2', "dat1")])
        self.assertEqual(olc_menus._edit_tag(caller, "foo1", "bar1;cat1"), (Something, {"key": "_default", "goto": Something}))
        self.assertEqual(olc_menus._display_tag(olc_menus._caller_tags(caller)[0]), Something)
        self.assertEqual(olc_menus._caller_tags(caller)[0], ("bar1", "cat1", ""))

        protlib.save_prototype(**self.test_prot)

        # spawn helpers
        obj = olc_menus._spawn(caller, prototype=self.test_prot)

        self.assertEqual(obj.typeclass_path, "evennia.objects.objects.DefaultObject")
        self.assertEqual(obj.tags.get(category=spawner._PROTOTYPE_TAG_CATEGORY), self.test_prot['prototype_key'])
        self.assertEqual(olc_menus._update_spawned(caller, prototype=self.test_prot, objects=[obj]), 0)  # no changes to apply
        self.test_prot['key'] = "updated key"  # change prototype
        self.assertEqual(self._update_spawned(caller, prototype=self.test_prot, objects=[obj]), 1)  # apply change to the one obj


        # load helpers




@mock.patch("evennia.prototypes.menus.protlib.search_prototype", new=mock.MagicMock(
   return_value=[{"prototype_key": "TestPrototype",
                  "typeclass": "TypeClassTest", "key": "TestObj"}]))
@mock.patch("evennia.utils.utils.get_all_typeclasses", new=mock.MagicMock(
   return_value={"TypeclassTest": None}))
class TestOLCMenu(TestEvMenu):

    maxDiff = None
    menutree = "evennia.prototypes.menus"
    startnode = "node_index"

    debug_output = True
    expect_all_nodes = True

    expected_node_texts = {
        "node_index": "|c --- Prototype wizard --- |n"
    }

    expected_tree = \
        ['node_index',
         ['node_prototype_key',
          'node_typeclass',
          'node_aliases',
          'node_attrs',
          'node_tags',
          'node_locks',
          'node_permissions',
          'node_location',
          'node_home',
          'node_destination',
          'node_prototype_desc',
          'node_prototype_tags',
          'node_prototype_locks']]
