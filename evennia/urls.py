from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^evennia/', include('evennia.apps.foo.urls.foo')),

    # Uncomment this for admin:
     (r'^admin/', include('django.contrib.admin.urls')),
)
