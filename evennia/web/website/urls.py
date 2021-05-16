"""
This structures the website.

"""
from django.conf import settings
from django.contrib import admin
from django.conf.urls import url, include
from django import views as django_views
from . import views

urlpatterns = [
    url(r"^$", views.EvenniaIndexView.as_view(), name="index"),
    url(r"^tbi/", views.to_be_implemented, name="to_be_implemented"),

    # User Authentication (makes login/logout url names available)
    url(r"^auth/register", views.AccountCreateView.as_view(), name="register"),
    url(r"^auth/", include("django.contrib.auth.urls")),

    # Help Topics
    url(r"^help/$", views.HelpListView.as_view(), name="help"),
    url(
        r"^help/(?P<category>[\w\d\-]+)/(?P<topic>[\w\d\-]+)/$",
        views.HelpDetailView.as_view(),
        name="help-entry-detail",
    ),

    # Channels
    url(r"^channels/$", views.ChannelListView.as_view(), name="channels"),
    url(
        r"^channels/(?P<slug>[\w\d\-]+)/$",
        views.ChannelDetailView.as_view(),
        name="channel-detail",
    ),

    # Character management
    url(r"^characters/$", views.CharacterListView.as_view(), name="characters"),
    url(
        r"^characters/create/$",
        views.CharacterCreateView.as_view(),
        name="character-create",
    ),
    url(
        r"^characters/manage/$",
        views.CharacterManageView.as_view(),
        name="character-manage",
    ),
    url(
        r"^characters/detail/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        views.CharacterDetailView.as_view(),
        name="character-detail",
    ),
    url(
        r"^characters/puppet/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        views.CharacterPuppetView.as_view(),
        name="character-puppet",
    ),
    url(
        r"^characters/update/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        views.CharacterUpdateView.as_view(),
        name="character-update",
    ),
    url(
        r"^characters/delete/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$",
        views.CharacterDeleteView.as_view(),
        name="character-delete",
    ),

    # Django original admin page. Make this URL is always available, whether
    # we've chosen to use Evennia's custom admin or not.

    url(r"django_admin/", views.admin_wrapper, name="django_admin"),

    # Admin docs
    url(r"^admin/doc/", include("django.contrib.admindocs.urls")),
]

if settings.EVENNIA_ADMIN:
    urlpatterns += [
        # Our override for the admin.
        url("^admin/$", views.evennia_admin, name="evennia_admin"),
        # Makes sure that other admin pages get loaded.
        url(r"^admin/", admin.site.urls),
    ]
else:
    # Just include the normal Django admin.
    urlpatterns += [url(r"^admin/", admin.site.urls)]

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
