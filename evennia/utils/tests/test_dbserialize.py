"""
Tests for dbserialize module
"""

from django.test import TestCase
from evennia.utils import dbserialize
from evennia.objects.objects import DefaultObject


class TestDbSerialize(TestCase):
    """
    Database serialization operations.
    """

    def setUp(self):
        self.obj = DefaultObject(db_key="Tester",)
        self.obj.save()
        print(f"setUp {self.obj}")

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

    def test_dict(self):
        self.obj.db.test = {'a': True}
        self.obj.db.test.update({'b': False})
        self.assertEqual(self.obj.db.test, {'a': True, 'b': False})

    def test_defaultdict(self):
        from collections import defaultdict
        dd = defaultdict(list)
        self.obj.db.test = dd
        self.obj.db.test['a']
        self.assertEqual(self.obj.db.test, {'a': []})
        self.obj.db.test['a'].append(1)
        self.assertEqual(self.obj.db.test, {'a': [1, 2]})
