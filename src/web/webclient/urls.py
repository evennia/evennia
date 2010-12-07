"""
This structures the (simple) structure of the 
webpage 'application'. 
"""
from django.views.generic.simple import direct_to_template
from django.conf.urls.defaults import *

urlpatterns = patterns('',
   url(r'^$', 'src.web.webclient.views.webclient'),)
   #url(r'^$', direct_to_template, {'template': 'webclient.html'}),)
