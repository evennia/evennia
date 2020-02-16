from django_filters.rest_framework.filterset import FilterSet

from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB

SHARED_FIELDS = ["db_key", "db_typeclass_path", "db_tags__db_key", "db_tags__db_category"]


class ObjectDBFilterSet(FilterSet):
    class Meta:
        model = ObjectDB
        fields = SHARED_FIELDS + ["db_location__db_key", "db_home__db_key", "db_location__id",
                                  "db_home__id"]


class AccountDBFilterSet(FilterSet):
    class Meta:
        model = AccountDB
        fields = SHARED_FIELDS + ["username", "db_is_connected", "db_is_bot"]


class ScriptDBFilterSet(FilterSet):
    class Meta:
        model = ScriptDB
        fields = SHARED_FIELDS + ["db_desc", "db_obj__db_key", "db_obj__id", "db_account__id",
                                  "db_account__username", "db_is_active", "db_persistent"]
