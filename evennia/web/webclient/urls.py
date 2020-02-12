"""
This structures the (simple) structure of the
webpage 'application'.
"""
from django.urls import path
from evennia.web.webclient import views as webclient_views

app_name = "webclient"

urlpatterns = [path("", webclient_views.webclient, name="index")]
