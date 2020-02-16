from rest_framework import routers
from evennia.web.api.views import (
    ObjectDBViewSet,
    AccountDBViewSet,
    CharacterViewSet,
    ExitViewSet,
    RoomViewSet,
    ScriptDBViewSet
)

app_name = "api"

router = routers.DefaultRouter()
router.register(r'accounts', AccountDBViewSet, basename="account")
router.register(r'objects', ObjectDBViewSet, basename="object")
router.register(r'characters', CharacterViewSet, basename="character")
router.register(r'exits', ExitViewSet, basename="exit")
router.register(r'rooms', RoomViewSet, basename="room")
router.register(r'scripts', ScriptDBViewSet, basename="script")

urlpatterns = router.urls
