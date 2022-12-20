"""
Main test-suite runner of Evennia. The runner collates tests from
all over the code base and runs them.

Runs as part of the Evennia's test suite with 'evennia test evennia"

"""
from unittest import mock

from django.test.runner import DiscoverRunner


class EvenniaTestSuiteRunner(DiscoverRunner):
    """
    Pointed to by the TEST_RUNNER setting.
    This test runner only runs tests on the apps specified in evennia/
     avoid running the large number of tests defined by Django

    """

    def setup_test_environment(self, **kwargs):
        # the portal looping call starts before the unit-test suite so we
        # can't mock it - instead we stop it before starting the test - otherwise
        # we'd get unclean reactor errors across test boundaries.
        from evennia.server.portal.portal import PORTAL

        PORTAL.maintenance_task.stop()

        # initialize evennia itself
        import evennia

        evennia._init()

        from django.conf import settings

        # set testing flag while suite runs
        settings._TEST_ENVIRONMENT = True
        super().setup_test_environment(**kwargs)

    def teardown_test_environment(self, **kwargs):

        # remove testing flag after suite has run
        from django.conf import settings

        settings._TEST_ENVIRONMENT = False

        super().teardown_test_environment(**kwargs)
