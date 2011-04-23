"""
Test runner for Evennia test suite. Run with "game/manage.py test".  

"""

from django.conf import settings
from django.test.simple import DjangoTestSuiteRunner

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


