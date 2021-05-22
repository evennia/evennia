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

from rest_framework import routers
from evennia.web.api.views import (
    ObjectDBViewSet,
    AccountDBViewSet,
    CharacterViewSet,
    ExitViewSet,
    RoomViewSet,
    ScriptDBViewSet,
)

app_name = "api"

router = routers.DefaultRouter()
router.trailing_slash = "/?"
router.register(r"accounts", AccountDBViewSet, basename="account")
router.register(r"objects", ObjectDBViewSet, basename="object")
router.register(r"characters", CharacterViewSet, basename="character")
router.register(r"exits", ExitViewSet, basename="exit")
router.register(r"rooms", RoomViewSet, basename="room")
router.register(r"scripts", ScriptDBViewSet, basename="script")

urlpatterns = router.urls
