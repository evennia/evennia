from django.conf.urls import url, include

from evennia.web.urls import urlpatterns

#
# File that determines what each URL points to. This uses _Python_ regular
# expressions, not Perl's.
#
# See:
# http://diveintopython.org/regular_expressions/street_addresses.html#re.matching.2.3
#

# Add your own URL patterns to the patterns variable below, and then change
#
# These are Django URL patterns, so you should look up how to use these at
# https://docs.djangoproject.com/en/1.6/topics/http/urls/

# Follow the full Django tutorial to learn how to create web views for Evennia.
# https://docs.djangoproject.com/en/1.6/intro/tutorial01/

patterns = [
    # url(r'/desired/url/', view, name='example'),
]

urlpatterns = patterns + urlpatterns
