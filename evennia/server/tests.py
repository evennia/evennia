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
try:
    from django.utils.unittest import TestCase
except ImportError:
    from django.test import TestCase
try:
    from django.utils import unittest
except ImportError:
    import unittest

from django.test.runner import DiscoverRunner

from .deprecations import check_errors


class EvenniaTestSuiteRunner(DiscoverRunner):
    """
    This test runner only runs tests on the apps specified in evennia/
     avoid running the large number of tests defined by Django
    """

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        """
        Build a test suite for Evennia. test_labels is a list of apps to test.
        If not given, a subset of settings.INSTALLED_APPS will be used.
        """
        import evennia
        evennia._init()
        return super(EvenniaTestSuiteRunner, self).build_suite(test_labels, extra_tests=extra_tests, **kwargs)


class MockSettings(object):
    def __init__(self, setting, value=True):
        self.setting = value
        if setting == "WEBSERVER_PORTS":
            self.WEBSERVER_ENABLED = True
        else:
            self.WEBSERVER_ENABLED = False


class TestDeprecations(TestCase):
    deprecated_strings = ("CMDSET_DEFAULT", "CMDSET_OOC", "BASE_COMM_TYPECLASS", "COMM_TYPECLASS_PATHS",
                          "CHARACTER_DEFAULT_HOME", "OBJECT_TYPECLASS_PATHS", "SCRIPT_TYPECLASS_PATHS",
                          "ACCOUNT_TYPECLASS_PATHS", "CHANNEL_TYPECLASS_PATHS", "SEARCH_MULTIMATCH_SEPARATOR")

    @staticmethod
    def warning_raised_for_setting(settings):
        try:
            check_errors(settings)
        except DeprecationWarning:
            return True
        else:
            return False

    def test_check_errors(self):
        for setting in self.deprecated_strings:
            self.assertTrue(self.warning_raised_for_setting(MockSettings(setting)),
                            "Deprecated setting %s did not raise warning." % setting)
        self.assertTrue(self.warning_raised_for_setting(MockSetting("WEBSERVER_PORTS", value=["not a tuple"])),
                        "WEBSERVER_PORTS being invalid type (Not a tuple) did not raise a warning.")
