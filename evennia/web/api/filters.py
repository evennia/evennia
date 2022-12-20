"""
FilterSets allow clients to specify querystrings that will determine the data
that is retrieved in GET requests. By default, Django Rest Framework uses the
'django-filter' package as its backend. Django-filter also has a section in its
documentation specifically regarding DRF integration.

https://django-filter.readthedocs.io/en/latest/guide/rest_framework.html

"""
from typing import Union

from django.db.models import Q
from django_filters.filters import EMPTY_VALUES, CharFilter
from django_filters.rest_framework.filterset import FilterSet

from evennia.accounts.models import AccountDB
from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB


def get_tag_query(tag_type: Union[str, None], key: str) -> Q:
    """
    Returns a Q object for searching by tag names for typeclasses
    Args:
        tag_type(str or None): The type of tag (None, 'alias', etc)
        key (str): The name of the tag

    Returns:
        A Q object that for searching by this tag type and name

    """
    return Q(db_tags__db_tagtype=tag_type) & Q(db_tags__db_key__iexact=key)


class TagTypeFilter(CharFilter):
    """
    This class lets you create different filters for tags of a specified db_tagtype.

    """

    tag_type = None

    def filter(self, qs, value):
        # if no value is specified, we don't use the filter
        if value in EMPTY_VALUES:
            return qs
        # if they enter a value, we filter objects by having a tag of this type with the given name
        return qs.filter(get_tag_query(self.tag_type, value)).distinct()


class AliasFilter(TagTypeFilter):
    """A filter for objects by their aliases (tags with a tagtype of 'alias'"""

    tag_type = "alias"


class PermissionFilter(TagTypeFilter):
    """A filter for objects by their permissions (tags with a tagtype of 'permission'"""

    tag_type = "permission"


SHARED_FIELDS = ["db_key", "db_typeclass_path", "db_tags__db_key", "db_tags__db_category"]


class BaseTypeclassFilterSet(FilterSet):
    """
    A parent class with filters for aliases and permissions

    """

    name = CharFilter(lookup_expr="iexact", method="filter_name", field_name="db_key")
    alias = AliasFilter(lookup_expr="iexact")
    permission = PermissionFilter(lookup_expr="iexact")

    @staticmethod
    def filter_name(queryset, name, value):
        """
        Filters a queryset by aliases or the key of the typeclass
        Args:
            queryset: The queryset being filtered
            name: The name of the field
            value: The value passed in from GET params

        Returns:
            The filtered queryset
        """
        query = Q(**{f"{name}__iexact": value})
        query |= get_tag_query("alias", value)
        return queryset.filter(query).distinct()


class ObjectDBFilterSet(BaseTypeclassFilterSet):
    """
    This adds filters for ObjectDB instances - characters, rooms, exits, etc

    """

    class Meta:
        model = ObjectDB
        fields = SHARED_FIELDS + [
            "db_location__db_key",
            "db_home__db_key",
            "db_location__id",
            "db_home__id",
        ]


class AccountDBFilterSet(BaseTypeclassFilterSet):
    """This adds filters for Account objects"""

    name = CharFilter(lookup_expr="iexact", method="filter_name", field_name="username")

    class Meta:
        model = AccountDB
        fields = [
            fi
            for fi in (SHARED_FIELDS + ["username", "db_is_connected", "db_is_bot"])
            if fi != "db_key"
        ]


class ScriptDBFilterSet(BaseTypeclassFilterSet):
    """This adds filters for Script objects"""

    class Meta:
        model = ScriptDB
        fields = SHARED_FIELDS + [
            "db_desc",
            "db_obj__db_key",
            "db_obj__id",
            "db_account__id",
            "db_account__username",
            "db_is_active",
            "db_persistent",
            "db_interval",
        ]


class HelpFilterSet(FilterSet):

    """
    Filter for help entries

    """

    name = CharFilter(lookup_expr="iexact", method="filter_name", field_name="db_key")
    category = CharFilter(lookup_expr="iexact", method="filter_name", field_name="db_category")
    alias = AliasFilter(lookup_expr="iexact")
