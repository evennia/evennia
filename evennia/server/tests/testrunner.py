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

    def setup_test_environment(self, **kwargs):
        import evennia

        evennia._init()

        from django.conf import settings

        # set testing flag while suite runs
        settings.TEST_ENVIRONMENT = True
        super().setup_test_environment(**kwargs)

    def teardown_test_environment(self, **kwargs):
        # remove testing flag after suite has run
        from django.conf import settings

        settings.TEST_ENVIRONMENT = False

        super().teardown_test_environment(**kwargs)
