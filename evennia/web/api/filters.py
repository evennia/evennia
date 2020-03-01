"""
FilterSets allow clients to specify querystrings that will determine the data
that is retrieved in GET requests. By default, Django Rest Framework uses the
'django-filter' package as its backend. Django-filter also has a section in its
documentation specifically regarding DRF integration.

https://django-filter.readthedocs.io/en/latest/guide/rest_framework.html
"""
from django.db.models import Q
from django_filters.rest_framework.filterset import FilterSet
from django_filters.filters import CharFilter

from evennia.objects.models import ObjectDB
from evennia.accounts.models import AccountDB
from evennia.scripts.models import ScriptDB


class TagTypeFilter(CharFilter):
    """
    This class lets you create different filters for tags of a specified db_tagtype.
    """
    tag_type = None

    def filter(self, qs, value):
        return qs.filter(Q(db_tags__db_tagtype=self.tag_type) & Q(db_tags__db_key=value))


class AliasFilter(TagTypeFilter):
    """A filter for objects by their aliases (tags with a tagtype of 'alias'"""
    tag_type = "alias"


class PermissionFilter(TagTypeFilter):
    """A filter for objects by their permissions (tags with a tagtype of 'permission'"""
    tag_type = "permission"


SHARED_FIELDS = ["db_key", "db_typeclass_path", "db_tags__db_key", "db_tags__db_category"]


class BaseTypeclassFilterSet(FilterSet):
    """A parent class with filters for aliases and permissions"""
    alias = AliasFilter(lookup_expr="iexact")
    permission = PermissionFilter(lookup_expr="iexact")


class ObjectDBFilterSet(BaseTypeclassFilterSet):
    """This adds filters for ObjectDB instances - characters, rooms, exits, etc"""
    class Meta:
        model = ObjectDB
        fields = SHARED_FIELDS + ["db_location__db_key", "db_home__db_key", "db_location__id",
                                  "db_home__id"]


class AccountDBFilterSet(BaseTypeclassFilterSet):
    """This adds filters for Account objects"""
    class Meta:
        model = AccountDB
        fields = SHARED_FIELDS + ["username", "db_is_connected", "db_is_bot"]


class ScriptDBFilterSet(BaseTypeclassFilterSet):
    """This adds filters for Script objects"""
    class Meta:
        model = ScriptDB
        fields = SHARED_FIELDS + ["db_desc", "db_obj__db_key", "db_obj__id", "db_account__id",
                                  "db_account__username", "db_is_active", "db_persistent", "db_interval"]
