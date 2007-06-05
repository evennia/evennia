from django.conf.urls.defaults import *

urlpatterns = patterns('apps.website.views',
    (r'^$', 'page_index'),
)
