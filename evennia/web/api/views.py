"""
Views are the functions that are called by different url endpoints. The Django
Rest Framework provides collections called 'ViewSets', which can generate a
number of views for the common CRUD operations.

"""
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from django_filters.rest_framework import DjangoFilterBackend

from evennia.objects.models import ObjectDB
from evennia.objects.objects import DefaultCharacter, DefaultExit, DefaultRoom
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.web.api.serializers import (
    ObjectDBSerializer,
    AccountSerializer,
    ScriptDBSerializer,
    AttributeSerializer,
)
from evennia.web.api.filters import ObjectDBFilterSet, AccountDBFilterSet, ScriptDBFilterSet
from evennia.web.api.permissions import EvenniaPermission


class TypeclassViewSetMixin:
    """
    This mixin adds some shared functionality to each viewset of a typeclass. They all use the same
    permission classes and filter backend. You can override any of these in your own viewsets.

    The `set_atribute` action is  an example of a custom action added to a
    viewset. Based on the name of the method, it will create a default url_name
    (used for reversing) and url_path.  The 'pk' argument is automatically
    passed to this action because it has a url path of the format <object
    type>/:pk/set-attribute. The get_object method is automatically set in the
    expected viewset classes that will inherit this, using the pk that's passed
    along to retrieve the object.

    """

    # permission classes determine who is authorized to call the view
    permission_classes = [EvenniaPermission]
    # the filter backend allows for retrieval views to have filter arguments passed to it,
    # for example: mygame.com/api/objects?db_key=bob to find matches based on objects having a db_key of bob
    filter_backends = [DjangoFilterBackend]

    @action(detail=True, methods=["put", "post"])
    def set_attribute(self, request, pk=None):
        """
        This action will set an attribute if the db_value is defined, or remove
        it if no db_value is provided.

        """
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
            return Response(
                AttributeSerializer(obj.db_attributes.all(), many=True).data,
                status=status.HTTP_200_OK,
            )
        return Response(attr.errors, status=status.HTTP_400_BAD_REQUEST)


class ObjectDBViewSet(TypeclassViewSetMixin, ModelViewSet):
    """
    The Object is the parent for all in-game entities that have a location
    (rooms, exits, characters etc).

    """
    # An example of a basic viewset for all ObjectDB instances. It declares the
    # serializer to use for both retrieving and changing/creating/deleting
    # instances. Serializers are similar to django forms, used for the
    # transmitting of data (typically json).

    serializer_class = ObjectDBSerializer
    queryset = ObjectDB.objects.all()
    filterset_class = ObjectDBFilterSet


class CharacterViewSet(ObjectDBViewSet):
    """
    Characters are a type of Object commonly used as player avatars in-game.

    """

    queryset = DefaultCharacter.objects.typeclass_search(
        DefaultCharacter.path, include_children=True
    )


class RoomViewSet(ObjectDBViewSet):
    """
    Rooms indicate discrete locations in-game.

    """

    queryset = DefaultRoom.objects.typeclass_search(DefaultRoom.path, include_children=True)


class ExitViewSet(ObjectDBViewSet):
    """
    Exits are objects with a destination and allows for traversing from one
    location to another.

    """

    queryset = DefaultExit.objects.typeclass_search(DefaultExit.path, include_children=True)


class AccountDBViewSet(TypeclassViewSetMixin, ModelViewSet):
    """
    Accounts represent the players connected to the game

    """

    serializer_class = AccountSerializer
    queryset = AccountDB.objects.all()
    filterset_class = AccountDBFilterSet


class ScriptDBViewSet(TypeclassViewSetMixin, ModelViewSet):
    """
    Scripts are meta-objects for storing system data, running timers etc. They
    have no in-game existence.

    """

    serializer_class = ScriptDBSerializer
    queryset = ScriptDB.objects.all()
    filterset_class = ScriptDBFilterSet
