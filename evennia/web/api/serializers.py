"""
Serializers in the Django Rest Framework are similar to Forms in normal django.
They're used for transmitting and validating data, both going to clients and
coming to the server. However, where forms often contained presentation logic,
such as specifying widgets to use for selection, serializers typically leave
those decisions in the hands of clients, and are more focused on converting
data from the server to JSON (serialization) for a response, and validating
and converting JSON data sent from clients to our enpoints into python objects,
often django model instances, that we can use (deserialization).
"""

from rest_framework import serializers

from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB
from evennia.typeclasses.attributes import Attribute
from evennia.typeclasses.tags import Tag


class AttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attribute
        fields = ["db_key", "db_value", "db_category", "db_attrtype"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["db_key", "db_category", "db_data", "db_tagtype"]


class SimpleObjectDBSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectDB
        fields = ["id", "db_key"]


class TypeclassSerializerMixin(object):
    db_attributes = AttributeSerializer(many=True)
    db_tags = TagSerializer(many=True)

    shared_fields = ["id", "db_key", "db_attributes", "db_tags", "db_typeclass_path"]


class ObjectDBSerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    contents = SimpleObjectDBSerializer(source="locations_set", many=True, read_only=True)

    class Meta:
        model = ObjectDB
        fields = ["db_location", "db_home", "contents"] + TypeclassSerializerMixin.shared_fields
        read_only_fields = ["id", "db_attributes", "db_tags"]


class AccountDBSerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    db_key = serializers.CharField(required=False)

    class Meta:
        model = AccountDB
        fields = ["username"] + TypeclassSerializerMixin.shared_fields
        read_only_fields = ["id", "db_attributes", "db_tags"]


class ScriptDBSerializer(TypeclassSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ScriptDB
        fields = ["db_interval", "db_persistent", "db_start_delay",
                  "db_is_active", "db_repeats"] + TypeclassSerializerMixin.shared_fields
        read_only_fields = ["id", "db_attributes", "db_tags"]
