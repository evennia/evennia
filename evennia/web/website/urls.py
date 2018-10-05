"""
This structures the website.

"""
from django.conf import settings
from django.contrib import admin
from django.conf.urls import url, include
from django import views as django_views
from evennia.web.website import views as website_views

urlpatterns = [
    url(r'^$', website_views.page_index, name="index"),
    url(r'^tbi/', website_views.to_be_implemented, name='to_be_implemented'),

    # User Authentication (makes login/logout url names available)
    url(r'^auth/', include('django.contrib.auth.urls')),
    url(r'^auth/register', website_views.AccountCreationView.as_view(), name="register"),
    
    # Character management
    url(r'^characters/create/$', website_views.CharacterCreateView.as_view(), name="chargen"),
    url(r'^characters/manage/$', website_views.CharacterManageView.as_view(), name="manage-characters"),
    url(r'^characters/update/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$', website_views.CharacterUpdateView.as_view(), name="update-character"),
    url(r'^characters/delete/(?P<slug>[\w\d\-]+)/(?P<pk>[0-9]+)/$', website_views.CharacterDeleteView.as_view(), name="delete-character"),
    
    # Django original admin page. Make this URL is always available, whether
    # we've chosen to use Evennia's custom admin or not.
    url(r'django_admin/', website_views.admin_wrapper, name="django_admin"),

    # Admin docs
    url(r'^admin/doc/', include('django.contrib.admindocs.urls'))
]

if settings.EVENNIA_ADMIN:
    urlpatterns += [
        # Our override for the admin.
        url('^admin/$', website_views.evennia_admin, name="evennia_admin"),

        # Makes sure that other admin pages get loaded.
        url(r'^admin/', admin.site.urls)]
else:
    # Just include the normal Django admin.
    urlpatterns += [url(r'^admin/', include(admin.site.urls))]

# This sets up the server if the user want to run the Django
# test server (this should normally not be needed).
if settings.SERVE_MEDIA:
    urlpatterns.extend([
        url(r'^media/(?P<path>.*)$', django_views.static.serve, {'document_root': settings.MEDIA_ROOT}),
        url(r'^static/(?P<path>.*)$', django_views.static.serve, {'document_root': settings.STATIC_ROOT})
    ])
