"""
The Django Rest Framework provides a way of generating urls for different
views that implement standard CRUD operations in a quick way, using 'routers'
and 'viewsets'. A viewset implements standard CRUD actions and any custom actions
that you want, and then a router will automatically generate URLs based on the
actions that it detects for a viewset. For example, below we create a DefaultRouter.
We then register ObjectDBViewSet, a viewset for CRUD operations for ObjectDB
instances, to the 'objects' base endpoint. That will generate a number of URLs
like the following:

list objects:    action: GET, url: /objects/, view name: object-list
create object:   action: POST, url: /objects/, view name: object-list
retrieve object: action: GET, url: /objects/<:pk>, view name: object-detail
update object:   action: POST, url: /objects/<:pk>, view name: object-detail
delete object:   action: DELETE, url: /objects/<:pk>, view name: object-detail
set attribute:   action: POST, url: /objects/<:pk>/set-attribute, view name: object-set-attribute

"""

from django.urls import path
from django.views.generic import TemplateView
from rest_framework.schemas import get_schema_view

from evennia.web.api import views
from evennia.web.api.root import APIRootRouter

app_name = "api"

router = APIRootRouter()
router.trailing_slash = "/?"
router.register(r"accounts", views.AccountDBViewSet, basename="account")
router.register(r"objects", views.ObjectDBViewSet, basename="object")
router.register(r"characters", views.CharacterViewSet, basename="character")
router.register(r"exits", views.ExitViewSet, basename="exit")
router.register(r"rooms", views.RoomViewSet, basename="room")
router.register(r"scripts", views.ScriptDBViewSet, basename="script")
router.register(r"helpentries", views.HelpViewSet, basename="helpentry")

urlpatterns = router.urls

urlpatterns += [
    # openapi schema
    path(
        "openapi",
        get_schema_view(title="Evennia API", description="Evennia OpenAPI Schema", version="1.0"),
        name="openapi",
    ),
    # redoc auto-doc (based on openapi schema)
    path(
        "redoc/",
        TemplateView.as_view(
            template_name="rest_framework/redoc.html", extra_context={"schema_url": "api:openapi"}
        ),
        name="redoc",
    ),
]
