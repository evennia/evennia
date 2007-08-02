#
# File that determines what each URL points to. This uses _Python_ regular
# expressions, not Perl's.
#
# See:
# http://diveintopython.org/regular_expressions/street_addresses.html#re.matching.2.3
#

from django.conf.urls.defaults import *
import settings

urlpatterns = patterns('',
   # User Authentication
   (r'^accounts/login',  'django.contrib.auth.views.login'),
   (r'^accounts/logout', 'django.contrib.auth.views.logout'),

   # Admin interface
   (r'^admin/', include('django.contrib.admin.urls')),

   # Front page
   (r'^', include('apps.website.urls')),

   # News stuff
   (r'^news/', include('apps.news.urls')),

   # Page place-holder for things that aren't implemented yet.
   (r'^tbi/', 'apps.website.views.to_be_implemented'),
)

# If you'd like to serve media files via Django (strongly not recommended!),
# open up your settings.py file and set SERVE_MEDIA to True. This is
# appropriate on a developing site, or if you're running Django's built-in
# test server. Normally you want a webserver that is optimized for serving
# static content to handle media files (apache, lighttpd).
if settings.SERVE_MEDIA:
   urlpatterns += patterns('',
      (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
   )