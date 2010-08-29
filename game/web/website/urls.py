"""
This structures the (simple) structure of the 
webpage 'application'. 
"""

from django.conf.urls.defaults import *

urlpatterns = patterns('game.web.website.views',
     (r'^$', 'page_index'),
)
