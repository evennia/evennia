#
# File that determines what each URL points to. This uses _Python_ regular
# expressions, not Perl's.
#
# See:
# http://diveintopython.org/regular_expressions/street_addresses.html#re.matching.2.3
#

from django.conf.urls import url, include
from django.views.generic import RedirectView

# Setup the root url tree from /

urlpatterns = [
    # Front page (note that we shouldn't specify namespace here since we will
    # not be able to load django-auth/admin stuff (will probably work in Django>1.9)
    url(r"^", include("evennia.web.website.urls")),  # , namespace='website', app_name='website')),
    # webclient
    url(r"^webclient/", include("evennia.web.webclient.urls", namespace="webclient")),
    # favicon
    url(r"^favicon\.ico$", RedirectView.as_view(url="/media/images/favicon.ico", permanent=False)),
]
