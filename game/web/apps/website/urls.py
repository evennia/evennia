from django.conf.urls.defaults import *

urlpatterns = patterns('game.web.apps.website.views',
     (r'^$', 'page_index'),
)
