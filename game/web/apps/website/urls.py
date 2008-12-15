from django.conf.urls.defaults import *

urlpatterns = patterns('webapps.website.views',
     (r'^$', 'page_index'),
)
