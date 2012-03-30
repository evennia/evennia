# -*- coding: utf-8 -*-

"""
Unit testing of the 'objects' Evennia component.

Runs as part of the Evennia's test suite with 'manage.py test"

Please add new tests to this module as needed.

Guidelines:
 A 'test case' is testing a specific component and is defined as a class inheriting from unittest.TestCase.
 The test case class can have a method setUp() that creates and sets up the testing environment.
 All methods inside the test case class whose names start with 'test' are used as test methods by the runner.
 Inside the test methods, special member methods assert*() are used to test the behaviour.
"""

import sys
try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase
try:
    from django.utils import unittest
except ImportError:
    import unittest

from django.conf import settings
from src.objects import models, objects
from src.utils import create
from src.commands.default import tests as commandtests
from src.locks import tests as locktests

class TestObjAttrs(TestCase):
    """
    Test aspects of ObjAttributes
    """
    def setUp(self):
        "set up the test"
        self.attr = models.ObjAttribute()
        self.obj1 = create.create_object(objects.Object, key="testobj1", location=None)
        self.obj2 = create.create_object(objects.Object, key="testobj2", location=self.obj1)
    def test_store_str(self):
        hstring = u"sdfv00=97sfjs842 ivfjlQKFos9GF^8dddsöäå-?%"
        self.obj1.db.testattr = hstring
        self.assertEqual(hstring, self.obj1.db.testattr)
    def test_store_obj(self):
        self.obj1.db.testattr = self.obj2
        self.assertEqual(self.obj2 ,self.obj1.db.testattr)
        self.assertEqual(self.obj2.location, self.obj1.db.testattr.location)

def suite():
    """
    This function is called automatically by the django test runner.
    This also runs the command tests defined in src/commands/default/tests.py.
    """
    tsuite = unittest.TestSuite()
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(commandtests))
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(locktests))
    return tsuite
