# -*- coding: utf-8 -*-

"""
Unit testing of the 'objects' Evennia component.

Runs as part of the Evennia's test suite with 'manage.py test"

Please add new tests to this module as needed.

Guidelines:
 A 'test case' is testing a specific component and is defined as a class
 inheriting from unittest.TestCase. The test case class can have a method
 setUp() that creates and sets up the testing environment.
 All methods inside the test case class whose names start with 'test' are
 used as test methods by the runner. Inside the test methods, special member
 methods assert*() are used to test the behaviour.
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

from src.locks import tests as locktests
from src.utils import tests as utiltests
from src.commands.default import tests as commandtests

def suite():
    """
    This function is called automatically by the django test runner.
    This also collates tests from packages that are not formally django applications.
    """
    tsuite = unittest.TestSuite()
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))

    # test modules from non-django apps
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(commandtests))
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(locktests))
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(utiltests))
    return tsuite
