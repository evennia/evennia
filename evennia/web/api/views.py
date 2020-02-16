"""
Views are the functions that are called by different url endpoints.
The Django Rest Framework provides collections called 'ViewSets', which
can generate a number of views for the common CRUD operations.
"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action

from django_filters.rest_framework import DjangoFilterBackend

from evennia.objects.models import ObjectDB
from evennia.objects.objects import DefaultCharacter, DefaultExit, DefaultRoom
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.web.api.serializers import ObjectDBSerializer, AccountDBSerializer, ScriptDBSerializer, AttributeSerializer
from evennia.web.api.filters import ObjectDBFilterSet, AccountDBFilterSet, ScriptDBFilterSet
from evennia.web.api.permissions import EvenniaPermission


class TypeclassViewSetMixin(object):
    permission_classes = [EvenniaPermission]
    filter_backends = [DjangoFilterBackend]


class ObjectDBViewSet(TypeclassViewSetMixin, ModelViewSet):
    serializer_class = ObjectDBSerializer
    queryset = ObjectDB.objects.all()
    filterset_class = ObjectDBFilterSet

    @action(detail=True, methods=["put", "post"])
    def add_attribute(self, request, pk=None):
        attr = AttributeSerializer(data=request.data)
        obj = self.get_object()
        if attr.is_valid(raise_exception=True):
            key = attr.validated_data["db_key"]
            value = attr.validated_data.get("db_value")
            category = attr.validated_data.get("db_category")
            attr_type = attr.validated_data.get("db_attrtype")
            if attr_type == "nick":
                handler = obj.nicks
            else:
                handler = obj.attributes
            if value:
                handler.add(key=key, value=value, category=category)
            else:
                handler.remove(key=key, category=category)


class CharacterViewSet(ObjectDBViewSet):
    queryset = DefaultCharacter.objects.typeclass_search(DefaultCharacter.path, include_children=True)


class RoomViewSet(ObjectDBViewSet):
    queryset = DefaultRoom.objects.typeclass_search(DefaultRoom.path, include_children=True)


class ExitViewSet(ObjectDBViewSet):
    queryset = DefaultExit.objects.typeclass_search(DefaultExit.path, include_children=True)


class AccountDBViewSet(TypeclassViewSetMixin, ModelViewSet):
    serializer_class = AccountDBSerializer
    queryset = AccountDB.objects.all()
    filterset_class = AccountDBFilterSet


class ScriptDBViewSet(TypeclassViewSetMixin, ModelViewSet):
    serializer_class = ScriptDBSerializer
    queryset = ScriptDB.objects.all()
    filterset_class = ScriptDBFilterSet
