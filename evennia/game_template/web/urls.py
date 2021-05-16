"""
This is the starting point when a user enters a url in their web browser. 

The urls is matched (by regex) and mapped to a 'view' - a Python function or
callable class that in turn (usually) makes use of a 'template' (a html file
with slots that can be replaced by dynamic content) in order to render a HTML
page to show the user.

This file is already set up to correctly handle all of Evennia's existing web
pages (including the webclient). But if you want to add a new page you needs to
start add by adding its view to `custom_patterns`. 

Search the Django documentation for "URL dispatcher" for more help.

"""
from django.conf.urls import url, include

# default evennia patterns
from evennia.web.urls import urlpatterns as evennia_default_urlpatterns

# add custom patterns here
urlpatterns = [
    # url(r'/desired/url/regex', 'path.to.python.view', name='example'),
]

# 'urlpatterns' must be named such for Django to find it.
urlpatterns = urlpatterns + evennia_default_urlpatterns
