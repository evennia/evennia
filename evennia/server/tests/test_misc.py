# -*- coding: utf-8 -*-

"""
Testing various individual functionalities in the server package.

"""
import unittest

from django.test import TestCase
from django.test.runner import DiscoverRunner

from evennia.server.throttle import Throttle
from evennia.server.validators import EvenniaPasswordValidator
from evennia.utils.test_resources import BaseEvenniaTest

from ..deprecations import check_errors


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
        "CMDSET_DEFAULT",
        "CMDSET_OOC",
        "BASE_COMM_TYPECLASS",
        "COMM_TYPECLASS_PATHS",
        "CHARACTER_DEFAULT_HOME",
        "OBJECT_TYPECLASS_PATHS",
        "SCRIPT_TYPECLASS_PATHS",
        "ACCOUNT_TYPECLASS_PATHS",
        "CHANNEL_TYPECLASS_PATHS",
        "SEARCH_MULTIMATCH_SEPARATOR",
        "TIME_SEC_PER_MIN",
        "TIME_MIN_PER_HOUR",
        "TIME_HOUR_PER_DAY",
        "TIME_DAY_PER_WEEK",
        "TIME_WEEK_PER_MONTH",
        "TIME_MONTH_PER_YEAR",
        "GAME_DIRECTORY_LISTING",
    )

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
            DeprecationWarning, check_errors, MockSettings("WEBSERVER_PORTS", value=["not a tuple"])
        )


class ValidatorTest(BaseEvenniaTest):
    def test_validator(self):
        # Validator returns None on success and ValidationError on failure.
        validator = EvenniaPasswordValidator()

        # This password should meet Evennia standards.
        self.assertFalse(validator.validate("testpassword", user=self.account))

        # This password contains illegal characters and should raise an Exception.
        from django.core.exceptions import ValidationError

        self.assertRaises(ValidationError, validator.validate, "(#)[#]<>", user=self.account)


class ThrottleTest(BaseEvenniaTest):
    """
    Class for testing the connection/IP throttle.
    """

    def test_throttle(self):
        ips = ("256.256.256.257", "257.257.257.257", "258.258.258.258")
        kwargs = {"name": "testing", "limit": 5, "timeout": 15 * 60}

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

        # Make sure the cache is populated
        self.assertTrue(throttle.get())

        # Remove the test IPs from the throttle cache
        # (in case persistent storage was configured by the user)
        for ip in ips:
            self.assertTrue(throttle.remove(ip))

        # Make sure the cache is empty
        self.assertFalse(throttle.get())
