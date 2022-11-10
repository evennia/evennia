"""
This structures the (simple) structure of the webpage 'application'.

"""
from django.urls import path

from . import views

app_name = "webclient"

urlpatterns = [path("", views.webclient, name="index")]
