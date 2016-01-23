"""
This structures the website.

"""
from django.conf import settings
from django.contrib import admin
from django.conf.urls import url, include

# loop over all settings.INSTALLED_APPS and execute code in
# files named admin.py in each such app (this will add those
# models to the admin site)
admin.autodiscover()

urlpatterns = [
   url(r'^$', 'evennia.web.website.views.page_index', name="index"),
   url(r'^tbi/', 'evennia.web.website.views.to_be_implemented', name='to_be_implemented'),

   # User Authentication
   url(r'^accounts/login',  'django.contrib.auth.views.login', name="login"),
   url(r'^accounts/logout', 'django.contrib.auth.views.logout', name="logout"),

   # Django original admin page. Make this URL is always available, whether
   # we've chosen to use Evennia's custom admin or not.
   url(r'django_admin/', 'evennia.web.website.views.admin_wrapper', name="django_admin"),

   # Admin docs
   url(r'^admin/doc/', include('django.contrib.admindocs.urls'))
   ]

if settings.EVENNIA_ADMIN:
    urlpatterns += [
        # Our override for the admin.
        url('^admin/$', 'evennia.web.website.views.evennia_admin', name="evennia_admin"),

        # Makes sure that other admin pages get loaded.
        url(r'^admin/', include(admin.site.urls))]
else:
    # Just include the normal Django admin.
    urlpatterns += [url(r'^admin/', include(admin.site.urls))]

# This sets up the server if the user want to run the Django
# test server (this should normally not be needed).
if settings.SERVE_MEDIA:
    urlpatterns.extend([
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
        url(r'^static/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.STATIC_ROOT})
    ])
