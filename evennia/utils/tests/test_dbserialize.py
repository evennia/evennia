"""
Tests for dbserialize module
"""

from collections import defaultdict, deque

from django.test import TestCase
from parameterized import parameterized

from evennia.objects.objects import DefaultObject
from evennia.utils import dbserialize


class TestDbSerialize(TestCase):
    """
    Database serialization operations.
    """

    def setUp(self):
        self.obj = DefaultObject(db_key="Tester")
        self.obj.save()

    def test_constants(self):
        self.obj.db.test = 1
        self.obj.db.test += 1
        self.assertEqual(self.obj.db.test, 2)
        self.obj.db.test -= 3
        self.assertEqual(self.obj.db.test, -1)
        self.obj.db.test *= -2
        self.assertEqual(self.obj.db.test, 2)
        self.obj.db.test /= 2
        self.assertEqual(self.obj.db.test, 1)

    def test_saverlist(self):
        self.obj.db.test = [1, 2, 3]
        self.assertEqual(self.obj.db.test, [1, 2, 3])
        self.obj.db.test.append("4")
        self.assertEqual(self.obj.db.test, [1, 2, 3, "4"])
        self.obj.db.test.insert(1, 1.5)
        self.assertEqual(self.obj.db.test, [1, 1.5, 2, 3, "4"])
        self.obj.db.test.pop()
        self.assertEqual(self.obj.db.test, [1, 1.5, 2, 3])
        self.obj.db.test.pop(0)
        self.assertEqual(self.obj.db.test, [1.5, 2, 3])
        self.obj.db.test.reverse()
        self.assertEqual(self.obj.db.test, [3, 2, 1.5])

    def test_saverlist__sort(self):
        self.obj.db.test = [3, 2, 1.5]
        self.obj.db.test.sort()
        self.assertEqual(self.obj.db.test, [1.5, 2, 3])
        self.obj.db.test.extend([0, 4, 5])
        self.assertEqual(self.obj.db.test, [1.5, 2, 3, 0, 4, 5])
        self.obj.db.test.sort()
        self.assertEqual(self.obj.db.test, [0, 1.5, 2, 3, 4, 5])
        self.obj.db.test = [[4, 5, 6], [1, 2, 3]]
        self.assertEqual(self.obj.db.test, [[4, 5, 6], [1, 2, 3]])
        self.obj.db.test.sort()
        self.assertEqual(self.obj.db.test, [[1, 2, 3], [4, 5, 6]])
        self.obj.db.test = [{1: 0}, {0: 1}]
        self.assertEqual(self.obj.db.test, [{1: 0}, {0: 1}])
        self.obj.db.test.sort(key=lambda d: str(d))
        self.assertEqual(self.obj.db.test, [{0: 1}, {1: 0}])

    def test_saverdict(self):
        self.obj.db.test = {"a": True}
        self.obj.db.test.update({"b": False})
        self.assertEqual(self.obj.db.test, {"a": True, "b": False})
        self.obj.db.test |= {"c": 5}
        self.assertEqual(self.obj.db.test, {"a": True, "b": False, "c": 5})

    @parameterized.expand(
        [
            ("list", list, dbserialize._SaverList, [1, 2, 3]),
            ("dict", dict, dbserialize._SaverDict, {"key": "value"}),
            ("set", set, dbserialize._SaverSet, {1, 2, 3}),
            ("deque", deque, dbserialize._SaverDeque, deque(("a", "b", "c"))),
            (
                "OrderedDict",
                dbserialize.OrderedDict,
                dbserialize._SaverOrderedDict,
                dbserialize.OrderedDict([("a", 1), ("b", 2), ("c", 3)]),
            ),
        ]
    )
    def test_deserialize(self, _, base_type, saver_type, default_value):
        self.assertIsInstance(default_value, base_type)
        self.obj.db.test = default_value
        for value in (dbserialize.deserialize(self.obj.db.test), self.obj.db.test.deserialize()):
            self.assertIsInstance(value, base_type)
            self.assertNotIsInstance(value, saver_type)
            self.assertEqual(value, default_value)
        self.obj.db.test = {"a": True}
        self.obj.db.test.update({"b": False})
        self.assertEqual(self.obj.db.test, {"a": True, "b": False})

    def test_defaultdict(self):
        # baseline behavior for a defaultdict
        _dd = defaultdict(list)
        _dd["a"]
        self.assertEqual(_dd, {"a": []})

        # behavior after defaultdict is set as attribute

        dd = defaultdict(list)
        self.obj.db.test = dd
        self.obj.db.test["a"]
        self.assertEqual(self.obj.db.test, {"a": []})

        self.obj.db.test["a"].append(1)
        self.assertEqual(self.obj.db.test, {"a": [1]})
        self.obj.db.test["a"].append(2)
        self.assertEqual(self.obj.db.test, {"a": [1, 2]})
        self.obj.db.test["a"].append(3)
        self.assertEqual(self.obj.db.test, {"a": [1, 2, 3]})
        self.obj.db.test |= {"b": [5, 6]}
        self.assertEqual(self.obj.db.test, {"a": [1, 2, 3], "b": [5, 6]})


class _InvalidContainer:
    """Container not saveable in Attribute (if obj is dbobj, it 'hides' it)"""

    def __init__(self, obj):
        self.hidden_obj = obj


class _ValidContainer(_InvalidContainer):
    """Container possible to save in Attribute (handles hidden dbobj explicitly)"""

    def __serialize_dbobjs__(self):
        self.hidden_obj = dbserialize.dbserialize(self.hidden_obj)

    def __deserialize_dbobjs__(self):
        self.hidden_obj = dbserialize.dbunserialize(self.hidden_obj)


class DbObjWrappers(TestCase):
    """
    Test the `__serialize_dbobjs__` and `__deserialize_dbobjs__` methods.

    """

    def setUp(self):
        super().setUp()
        self.dbobj1 = DefaultObject(db_key="Tester1")
        self.dbobj1.save()
        self.dbobj2 = DefaultObject(db_key="Tester2")
        self.dbobj2.save()

    def test_dbobj_hidden_obj__fail(self):
        with self.assertRaises(TypeError):
            self.dbobj1.db.testarg = _InvalidContainer(self.dbobj1)

    def test_consecutive_fetch(self):
        con = _ValidContainer(self.dbobj2)
        self.dbobj1.db.testarg = con
        attrobj = self.dbobj1.attributes.get("testarg", return_obj=True)

        self.assertEqual(attrobj.value, con)
        self.assertEqual(attrobj.value, con)
        self.assertEqual(attrobj.value.hidden_obj, self.dbobj2)

    def test_dbobj_hidden_obj__success(self):
        con = _ValidContainer(self.dbobj2)
        self.dbobj1.db.testarg = con

        # accessing the same data multiple times
        res1 = self.dbobj1.db.testarg
        res2 = self.dbobj1.db.testarg
        res3 = self.dbobj1.db.testarg

        self.assertEqual(res1, res2)
        self.assertEqual(res1, res3)
        self.assertEqual(res1, con)
        self.assertEqual(res2, con)
        self.assertEqual(res1.hidden_obj, self.dbobj2)
        self.assertEqual(res2.hidden_obj, self.dbobj2)
        self.assertEqual(res3.hidden_obj, self.dbobj2)

    def test_dbobj_hidden_dict(self):
        con1 = _ValidContainer(self.dbobj2)
        con2 = _ValidContainer(self.dbobj2)

        self.dbobj1.db.dict = {}

        self.dbobj1.db.dict["key1"] = con1
        self.dbobj1.db.dict["key2"] = con2

        self.assertEqual(self.dbobj1.db.dict["key1"].hidden_obj, self.dbobj2)
        self.assertEqual(self.dbobj1.db.dict["key1"].hidden_obj, self.dbobj2)
        self.assertEqual(self.dbobj1.db.dict["key2"].hidden_obj, self.dbobj2)
        self.assertEqual(self.dbobj1.db.dict["key2"].hidden_obj, self.dbobj2)

    def test_dbobj_hidden_defaultdict(self):

        con1 = _ValidContainer(self.dbobj2)
        con2 = _ValidContainer(self.dbobj2)

        self.dbobj1.db.dfdict = defaultdict(dict)

        self.dbobj1.db.dfdict["key"]["con1"] = con1
        self.dbobj1.db.dfdict["key"]["con2"] = con2

        self.assertEqual(self.dbobj1.db.dfdict["key"]["con1"].hidden_obj, self.dbobj2)

        self.assertEqual(self.dbobj1.db.dfdict["key"]["con1"].hidden_obj, self.dbobj2)
        self.assertEqual(self.dbobj1.db.dfdict["key"]["con2"].hidden_obj, self.dbobj2)
        self.assertEqual(self.dbobj1.db.dfdict["key"]["con2"].hidden_obj, self.dbobj2)
