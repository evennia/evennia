"""
Rerouting admin frontpage to evennia version.

These patterns are all under the admin/* namespace.

"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from . import frontpage

urlpatterns = [
    # Django original admin page. Make this URL always available, whether
    # we've chosen to use Evennia's custom admin or not.
    path("django/", frontpage.admin_wrapper, name="django_admin"),
    # Admin docs
    path("doc/", include("django.contrib.admindocs.urls")),
]

if settings.EVENNIA_ADMIN:

    urlpatterns += [
        # Our override for the admin.
        path("", frontpage.evennia_admin, name="evennia_admin"),
        # Makes sure that other admin pages get loaded.
        path("", admin.site.urls),
    ]
else:
    # Just include the normal Django admin.
    urlpatterns += [path("", admin.site.urls)]
