"""
This structures the (simple) structure of the
webpage 'application'.
"""
from django.conf.urls import *

urlpatterns = [
   url(r'^$', 'evennia.web.webclient.views.webclient', name="index")]
