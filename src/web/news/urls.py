"""
This structures the url tree for the news application.
It is imported from the root handler, game.web.urls.py.
"""

from django.conf.urls import *

urlpatterns = [
    url(r'^show/(?P<entry_id>\d+)/$', 'show_news', name="show"),
    url(r'^archive/$', 'news_archive', name="archive"),
    url(r'^search/$', 'search_form', name="search"),
    url(r'^search/results/$', 'search_results', name="search_results")]
