"""
File that determines what each URL points to. This uses Python regular expressions.
This is the starting point when a user enters an URL.

1. The URL is matched with a regex, tying it to a given view. Note that this central url.py
   file includes url.py from all the various web-components found in views/ so the search
   space is much larger than what is shown here.
2. The view (a Python function or class is executed)
3. The view uses a template (a HTML file which may contain template markers for dynamically
   modifying its contents; the locations of such templates are given by
   `settings.TEMPLATES[0]['DIRS']`) and which may in turn may include static
   assets (CSS, images etc).
4. The view 'renders' the template into a finished HTML page, replacing all
   dynamic content as appropriate.
5. The HTML page is returned to the user.

"""

from django.conf import settings
from django.urls import include, path
from django.views.generic import RedirectView

# Setup the root url tree from /

urlpatterns = [
    # Front page (note that we shouldn't specify namespace here since we will
    # not be able to load django-auth/admin stuff (will probably work in Django>1.9)
    path("", include("evennia.web.website.urls")),
    # webclient
    path("webclient/", include("evennia.web.webclient.urls")),
    # admin -
    # path("admin/", include("evennia.web.admin.urls")),
    # favicon
    path("favicon.ico", RedirectView.as_view(url="/media/images/favicon.ico", permanent=False)),
]

if settings.REST_API_ENABLED:
    # Rest API
    urlpatterns += [path("api/", include("evennia.web.api.urls", namespace="api"))]
