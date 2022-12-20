"""
This redirects to website sub-pages.

"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from .views import accounts, channels, characters, errors
from .views import help as helpviews
from .views import index

urlpatterns = [
    # website front page
    path("", index.EvenniaIndexView.as_view(), name="index"),
    # errors
    path(r"tbi/", errors.to_be_implemented, name="to_be_implemented"),
    # User Authentication (makes login/logout url names available)
    path("auth/register", accounts.AccountCreateView.as_view(), name="register"),
    path("auth/", include("django.contrib.auth.urls")),
    # Help Topics
    path("help/", helpviews.HelpListView.as_view(), name="help"),
    path(
        r"help/<str:category>/<str:topic>/",
        helpviews.HelpDetailView.as_view(),
        name="help-entry-detail",
    ),
    # Channels
    path("channels/", channels.ChannelListView.as_view(), name="channels"),
    path("channels/<str:slug>/", channels.ChannelDetailView.as_view(), name="channel-detail"),
    # Character management
    path("characters/", characters.CharacterListView.as_view(), name="characters"),
    path("characters/create/", characters.CharacterCreateView.as_view(), name="character-create"),
    path("characters/manage/", characters.CharacterManageView.as_view(), name="character-manage"),
    path(
        "characters/detail/<str:slug>/<int:pk>/",
        characters.CharacterDetailView.as_view(),
        name="character-detail",
    ),
    path(
        "characters/puppet/<str:slug>/<int:pk>/",
        characters.CharacterPuppetView.as_view(),
        name="character-puppet",
    ),
    path(
        "characters/update/<str:slug>/<int:pk>/",
        characters.CharacterUpdateView.as_view(),
        name="character-update",
    ),
    path(
        "characters/delete/<str:slug>/<int:pk>/",
        characters.CharacterDeleteView.as_view(),
        name="character-delete",
    ),
]


# This sets up the server if the user want to run the Django test server (this
# is not recommended and is usually unnecessary).
if settings.SERVE_MEDIA:
    from django import views as django_views

    urlpatterns.extend(
        [
            path(
                "media/<str:path>",
                django_views.static.serve,
                {"document_root": settings.MEDIA_ROOT},
            ),
            path(
                "static/<str:path>",
                django_views.static.serve,
                {"document_root": settings.STATIC_ROOT},
            ),
        ]
    )
