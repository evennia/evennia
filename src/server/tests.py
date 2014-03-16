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
import glob

try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase
try:
    from django.utils import unittest
except ImportError:
    import unittest

from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner
from src.utils.utils import mod_import


class EvenniaTestSuiteRunner(DjangoTestSuiteRunner):
    """
    This test runner only runs tests on the apps specified in src/ and game/ to
     avoid running the large number of tests defined by Django
    """
    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        """
        Build a test suite for Evennia. test_labels is a list of apps to test.
        If not given, a subset of settings.INSTALLED_APPS will be used.
        """
        if not test_labels:
            test_labels = [applabel.rsplit('.', 1)[1] for applabel in settings.INSTALLED_APPS
                           if (applabel.startswith('src.') or applabel.startswith('game.'))]
        return super(EvenniaTestSuiteRunner, self).build_suite(test_labels, extra_tests=extra_tests, **kwargs)


def suite():
    """
    This function is called automatically by the django test runner.
    This also collates tests from packages that are not formally django applications.
    """
    from src.locks import tests as locktests
    from src.utils import tests as utiltests
    from src.commands.default import tests as commandtests

    tsuite = unittest.TestSuite()
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))

    # test modules from non-django apps
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(commandtests))
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(locktests))
    tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(utiltests))

    for path in glob.glob("../src/tests/test_*.py"):
        testmod = mod_import(path)
        tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(testmod))

    #from src.tests import test_commands_cmdhandler
    #tsuite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_commands_cmdhandler))

    return tsuite
