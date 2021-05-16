"""
This structures the website.

"""
from django.conf import settings
from django.contrib import admin
from django.conf.urls import url, include
from django import views as django_views
from .views import (index, errors, accounts, help as helpviews, channels,
                    characters)

urlpatterns = [
    # website front page
    url(r"^$", index.EvenniaIndexView.as_view(), name="index"),

    # errors
    url(r"^tbi/", errors.to_be_implemented, name="to_be_implemented"),

    # User Authentication (makes login/logout url names available)
    url(r"^auth/register", accounts.AccountCreateView.as_view(), name="register"),
    url(r"^auth/", include("django.contrib.auth.urls")),

    # Help Topics
    url(r"^help/$", helpviews.HelpListView.as_view(), name="help"),
    url(r"^help/(?P<category>[\w\d\-]+)/(?P<topic>[\w\d\-]+)/$",
        helpviews.HelpDetailView.as_view(),
        name="help-entry-detail"),

    # Channels
    url(r"^channels/$", channels.ChannelListView.as_view(), name="channels"),
    url(r"^channels/(?P<slug>[\w\d\-]+)/$",
        channels.ChannelDetailView.as_view(),
        name="channel-detail"),

    # Character management
    url(r"^characters/$", characters.CharacterListView.as_view(), name="characters"),
    url(r"^characters/create/$",
        characters.CharacterCreateView.as_view(),
        name="character-create"),
    url(r"^characters/manage/$",
        characters.CharacterManageView.as_view(),
        name="character-manage"),
    url(r"^characters/detail/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        characters.CharacterDetailView.as_view(),
        name="character-detail"),
    url(r"^characters/puppet/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        characters.CharacterPuppetView.as_view(),
        name="character-puppet"),
    url(r"^characters/update/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        characters.CharacterUpdateView.as_view(),
        name="character-update"),
    url(r"^characters/delete/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        characters.CharacterDeleteView.as_view(),
        name="character-delete"),
]


# This sets up the server if the user want to run the Django
# test server (this should normally not be needed).
if settings.SERVE_MEDIA:
    urlpatterns.extend(
        [
            url(
                r"^media/(?P<path>.*)$",
                django_views.static.serve,
                {"document_root": settings.MEDIA_ROOT},
            ),
            url(
                r"^static/(?P<path>.*)$",
                django_views.static.serve,
                {"document_root": settings.STATIC_ROOT},
            ),
        ]
    )
