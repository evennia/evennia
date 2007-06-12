from django.conf.urls.defaults import *

urlpatterns = patterns('apps.news.views',
    (r'^show/(?P<entry_id>\d+)/$', 'show_news'),
#    (r'^news/categories/list/$', 'recent_kills'),
)
