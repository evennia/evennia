"""
Main test-suite runner of Evennia. The runner collates tests from
all over the code base and runs them.

Runs as part of the Evennia's test suite with 'evennia test evennia"

"""
from django.test.runner import DiscoverRunner
from unittest import mock


class EvenniaTestSuiteRunner(DiscoverRunner):
    """
    Pointed to by the TEST_RUNNER setting.
    This test runner only runs tests on the apps specified in evennia/
     avoid running the large number of tests defined by Django

    """

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        """
        Build a test suite for Evennia. test_labels is a list of apps to test.
        If not given, a subset of settings.INSTALLED_APPS will be used.
        """
        # the portal looping call starts before the unit-test suite so we
        # can't mock it - instead we stop it before starting the test - otherwise
        # we'd get unclean reactor errors across test boundaries.
        from evennia.server.portal.portal import PORTAL

        PORTAL.maintenance_task.stop()

        import evennia

        evennia._init()
        return super().build_suite(
            test_labels, extra_tests=extra_tests, **kwargs
        )
