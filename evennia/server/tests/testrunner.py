"""
Main test-suite runner of Evennia. The runner collates tests from
all over the code base and runs them.

Runs as part of the Evennia's test suite with 'evennia test evennia"

"""
from django.test.runner import DiscoverRunner


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
        import evennia

        evennia._init()
        return super(EvenniaTestSuiteRunner, self).build_suite(
            test_labels, extra_tests=extra_tests, **kwargs
        )
