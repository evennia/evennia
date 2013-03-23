"""
This structures the (simple) structure of the 
webpage 'application'. 
"""
from django.conf.urls import *

urlpatterns = patterns('',
   url(r'^$', 'src.web.webclient.views.webclient'),)
