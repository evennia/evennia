"""
Rerouting admin frontpage to evennia version.

These patterns are all under the admin/* namespace.

"""
from django.conf import settings
from django.contrib import admin
from django.conf.urls import url, include
from . import frontpage


urlpatterns = [
    # Django original admin page. Make this URL is always available, whether
    # we've chosen to use Evennia's custom admin or not.
    url(r"/django/", frontpage.admin_wrapper, name="django_admin"),
    # Admin docs
    url(r"/doc/", include("django.contrib.admindocs.urls")),
]

if settings.EVENNIA_ADMIN:

    urlpatterns += [
        # Our override for the admin.
        url("^$", frontpage.evennia_admin, name="evennia_admin"),
        # Makes sure that other admin pages get loaded.
        url(r"^/", admin.site.urls),
    ]
else:
    # Just include the normal Django admin.
    urlpatterns += [url(r"^/", admin.site.urls)]
