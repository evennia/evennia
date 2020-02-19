"""
This structures the (simple) structure of the
webpage 'application'.
"""
from django.conf.urls import *
from evennia.web.webclient import views as webclient_views

app_name = "webclient"
urlpatterns = [url(r"^$", webclient_views.webclient, name="index")]
