#
# File that determines what each URL points to. This uses _Python_ regular
# expressions, not Perl's.
#
# See:
# http://diveintopython.org/regular_expressions/street_addresses.html#re.matching.2.3
#

from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

# loop over all settings.INSTALLED_APPS and execute code in 
# files named admin.py ine each such app (this will add those
# models to the admin site)
admin.autodiscover()

# Setup the root url tree from / 

urlpatterns = patterns('',
    # User Authentication
    url(r'^accounts/login',  'django.contrib.auth.views.login'),
    url(r'^accounts/logout', 'django.contrib.auth.views.logout'),

    # Front page
    url(r'^', include('game.web.website.urls')),
    # News stuff
    url(r'^news/', include('game.web.news.urls')),

    # Page place-holder for things that aren't implemented yet.
    url(r'^tbi/', 'game.web.website.views.to_be_implemented'),
    
    # Admin interface
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    #url(r'^admin/(.*)', admin.site.root, name='admin'),

    # favicon
    url(r'^favicon\.ico$', 'django.views.generic.simple.redirect_to', {'url':'/media/images/favicon.ico'}),
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
