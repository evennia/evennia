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

from evennia.server.validators import EvenniaPasswordValidator
from evennia.utils.test_resources import EvenniaTest

from django.test.runner import DiscoverRunner

from evennia.server.throttle import Throttle

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
    """
    Class for simulating django.conf.settings. Created with a single value, and then sets the required
    WEBSERVER_ENABLED setting to True or False depending if we're testing WEBSERVER_PORTS.
    """
    def __init__(self, setting, value=None):
        setattr(self, setting, value)
        if setting == "WEBSERVER_PORTS":
            self.WEBSERVER_ENABLED = True
        else:
            self.WEBSERVER_ENABLED = False


class TestDeprecations(TestCase):
    """
    Class for testing deprecations.check_errors.
    """
    deprecated_settings = (
            "CMDSET_DEFAULT", "CMDSET_OOC", "BASE_COMM_TYPECLASS", "COMM_TYPECLASS_PATHS",
            "CHARACTER_DEFAULT_HOME", "OBJECT_TYPECLASS_PATHS", "SCRIPT_TYPECLASS_PATHS",
            "ACCOUNT_TYPECLASS_PATHS", "CHANNEL_TYPECLASS_PATHS", "SEARCH_MULTIMATCH_SEPARATOR",
            "TIME_SEC_PER_MIN", "TIME_MIN_PER_HOUR", "TIME_HOUR_PER_DAY", "TIME_DAY_PER_WEEK",
            "TIME_WEEK_PER_MONTH", "TIME_MONTH_PER_YEAR")

    def test_check_errors(self):
        """
        All settings in deprecated_settings should raise a DeprecationWarning if they exist.
        WEBSERVER_PORTS raises an error if the iterable value passed does not have a tuple as its
        first element.
        """
        for setting in self.deprecated_settings:
            self.assertRaises(DeprecationWarning, check_errors, MockSettings(setting))
        # test check for WEBSERVER_PORTS having correct value
        self.assertRaises(
            DeprecationWarning,
            check_errors, MockSettings("WEBSERVER_PORTS", value=["not a tuple"]))


class ValidatorTest(EvenniaTest):

    def test_validator(self):
        # Validator returns None on success and ValidationError on failure.
        validator = EvenniaPasswordValidator()

        # This password should meet Evennia standards.
        self.assertFalse(validator.validate('testpassword', user=self.account))

        # This password contains illegal characters and should raise an Exception.
        from django.core.exceptions import ValidationError
        self.assertRaises(ValidationError, validator.validate, '(#)[#]<>', user=self.account)


class ThrottleTest(EvenniaTest):
    """
    Class for testing the connection/IP throttle.
    """
    def test_throttle(self):
        ips = ('94.100.176.153', '45.56.148.77', '5.196.1.129')
        kwargs = {
            'limit': 5,
            'timeout': 15 * 60
        }

        throttle = Throttle(**kwargs)

        for ip in ips:
            # Throttle should not be engaged by default
            self.assertFalse(throttle.check(ip))

            # Pretend to fail a bunch of events
            for x in range(50):
                obj = throttle.update(ip)
                self.assertFalse(obj)

            # Next ones should be blocked
            self.assertTrue(throttle.check(ip))

            for x in range(throttle.cache_size * 2):
                obj = throttle.update(ip)
                self.assertFalse(obj)

            # Should still be blocked
            self.assertTrue(throttle.check(ip))

            # Number of values should be limited by cache size
            self.assertEqual(throttle.cache_size, len(throttle.get(ip)))

        cache = throttle.get()

        # Make sure there are entries for each IP
        self.assertEqual(len(ips), len(cache.keys()))

        # There should only be (cache_size * num_ips) total in the Throttle cache
        self.assertEqual(sum([len(cache[x]) for x in cache.keys()]), throttle.cache_size * len(ips))
