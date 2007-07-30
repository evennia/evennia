from django.conf.urls.defaults import *

urlpatterns = patterns('apps.news.views',
    (r'^show/(?P<entry_id>\d+)/$', 'show_news'),
    (r'^archive/$', 'news_archive'),
    (r'^search/$', 'search_form'),
    (r'^search/results/$', 'search_results'),
)
