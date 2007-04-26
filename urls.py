#
# File that determines what each URL points to. This uses _Python_ regular
# expressions, not Perl's.
#
# See:
# http://diveintopython.org/regular_expressions/street_addresses.html#re.matching.2.3
#

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Admin interface
    (r'^admin/', include('django.contrib.admin.urls')),
)
