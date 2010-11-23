"""
This structures the url tree for the news application. 
It is imported from the root handler, game.web.urls.py.
"""

from django.conf.urls.defaults import *

urlpatterns = patterns('src.web.news.views',
     (r'^show/(?P<entry_id>\d+)/$', 'show_news'),
     (r'^archive/$', 'news_archive'),
     (r'^search/$', 'search_form'),
     (r'^search/results/$', 'search_results'),
)
