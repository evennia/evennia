"""
This is a convenient container gathering all the main
search methods for the various database tables.

It is intended to be used e.g. as

> from evennia.utils import search
> match = search.objects(...)

Note that this is not intended to be a complete listing of all search
methods! You need to refer to the respective manager to get all
possible search methods. To get to the managers from your code, import
the database model and call its 'objects' property.

Also remember that all commands in this file return lists (also if
there is only one match) unless noted otherwise.

Example: To reach the search method 'get_object_with_account'
         in evennia/objects/managers.py:

> from evennia.objects.models import ObjectDB
> match = Object.objects.get_object_with_account(...)

"""

from django.utils.functional import SimpleLazyObject

# limit symbol import from API
__all__ = (
    "search_object",
    "search_account",
    "search_script",
    "search_message",
    "search_channel",
    "search_help_entry",
    "search_tag",
    "search_script_tag",
    "search_account_tag",
    "search_channel_tag",
    "search_typeclass",
)


# Lazy-loaded model classes
def _get_objectdb():
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get(app_label="objects", model="objectdb").model_class()


def _get_accountdb():
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get(app_label="accounts", model="accountdb").model_class()


def _get_scriptdb():
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get(app_label="scripts", model="scriptdb").model_class()


def _get_msg():
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get(app_label="comms", model="msg").model_class()


def _get_channeldb():
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get(app_label="comms", model="channeldb").model_class()


def _get_helpentry():
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get(app_label="help", model="helpentry").model_class()


def _get_tag():
    from django.contrib.contenttypes.models import ContentType

    return ContentType.objects.get(app_label="typeclasses", model="tag").model_class()


# Lazy model instances
ObjectDB = SimpleLazyObject(_get_objectdb)
AccountDB = SimpleLazyObject(_get_accountdb)
ScriptDB = SimpleLazyObject(_get_scriptdb)
Msg = SimpleLazyObject(_get_msg)
ChannelDB = SimpleLazyObject(_get_channeldb)
HelpEntry = SimpleLazyObject(_get_helpentry)
Tag = SimpleLazyObject(_get_tag)


# -------------------------------------------------------------------
# Search manager-wrappers
# -------------------------------------------------------------------


def search_object(*args, **kwargs):
    """
    Search for objects in the database.

    Args:
        key (str or int): Object key or dbref to search for. This can also
            be a list of keys/dbrefs. `None` (default) returns all objects.
        exact (bool): Only valid for string keys. If True, requires exact
            key match, otherwise also match key with case-insensitive and
            partial matching. Default is True.
        candidates (list): Only search among these object candidates,
            if given. Default is to search all objects.
        attribute_name (str): If set, search by objects with this attribute_name
            defined on them, with the value specified by `attribute_value`.
        attribute_value (any): What value the given attribute_name must have.
        location (Object): Filter by objects at this location.
        typeclass (str or TypeClass): Filter by objects having this typeclass.
            This can also be a list of typeclasses.
        tags (str or list): Filter by objects having one or more Tags.
            This can be a single tag key, a list of tag keys, or a list of
            tuples (tag_key, tag_category).
        nofetch (bool): Don't fetch typeclass and perms data from db.
            This is faster but gives less info.

    Returns:
        matches (list): List of Objects matching the search criteria.
    """
    return ObjectDB.objects.search_object(*args, **kwargs)


search_objects = search_object
object_search = search_object
objects = search_objects


def search_account(*args, **kwargs):
    """
    Search for accounts in the database.

    Args:
        key (str or int): Account key or dbref to search for. This can also
            be a list of keys/dbrefs. `None` (default) returns all accounts.
        exact (bool): Only valid for string keys. If True, requires exact
            key match, otherwise also match key with case-insensitive and
            partial matching. Default is True.
        candidates (list): Only search among these account candidates,
            if given. Default is to search all accounts.
        attribute_name (str): If set, search by accounts with this attribute_name
            defined on them, with the value specified by `attribute_value`.
        attribute_value (any): What value the given attribute_name must have.
        tags (str or list): Filter by accounts having one or more Tags.
            This can be a single tag key, a list of tag keys, or a list of
            tuples (tag_key, tag_category).
        nofetch (bool): Don't fetch typeclass and perms data from db.
            This is faster but gives less info.

    Returns:
        matches (list): List of Accounts matching the search criteria.
    """
    return AccountDB.objects.search_account(*args, **kwargs)


search_accounts = search_account
account_search = search_account
accounts = search_accounts


def search_script(*args, **kwargs):
    """
    Search for scripts in the database.

    Args:
        key (str or int): Script key or dbref to search for. This can also
            be a list of keys/dbrefs. `None` (default) returns all scripts.
        exact (bool): Only valid for string keys. If True, requires exact
            key match, otherwise also match key with case-insensitive and
            partial matching. Default is True.
        candidates (list): Only search among these script candidates,
            if given. Default is to search all scripts.
        attribute_name (str): If set, search by scripts with this attribute_name
            defined on them, with the value specified by `attribute_value`.
        attribute_value (any): What value the given attribute_name must have.
        obj (Object): Filter by scripts defined on this object.
        account (Account): Filter by scripts defined on this account.
        typeclass (str or TypeClass): Filter by scripts having this typeclass.
            This can also be a list of typeclasses.
        tags (str or list): Filter by scripts having one or more Tags.
            This can be a single tag key, a list of tag keys, or a list of
            tuples (tag_key, tag_category).
        nofetch (bool): Don't fetch typeclass and perms data from db.
            This is faster but gives less info.

    Returns:
        matches (list): List of Scripts matching the search criteria.
    """
    return ScriptDB.objects.search_script(*args, **kwargs)


search_scripts = search_script
script_search = search_script
scripts = search_scripts


def search_message(*args, **kwargs):
    """
    Search for messages in the database.

    Args:
        sender (Object, Account or str): Filter by messages sent by this entity.
            If a string, this is an external sender name.
        receiver (Object, Account or str): Filter by messages received by this entity.
            If a string, this is an external receiver name.
        channel (Channel): Filter by messages sent to this channel.
        date (datetime): Filter by messages sent on this date.
        type (str): Filter by messages of this type.
        tags (str or list): Filter by messages having one or more Tags.
            This can be a single tag key, a list of tag keys, or a list of
            tuples (tag_key, tag_category).
        exclude_tags (str or list): Exclude messages with these tags.
        search_text (str): Search for text in message content.
        exact (bool): If True, require exact text match. Default False.

    Returns:
        matches (list): List of Messages matching the search criteria.
    """
    return Msg.objects.search_message(*args, **kwargs)


search_messages = search_message
message_search = search_message
messages = search_messages


def search_channel(*args, **kwargs):
    """
    Search for channels in the database.

    Args:
        key (str or int): Channel key or dbref to search for. This can also
            be a list of keys/dbrefs. `None` (default) returns all channels.
        exact (bool): Only valid for string keys. If True, requires exact
            key match, otherwise also match key with case-insensitive and
            partial matching. Default is True.
        candidates (list): Only search among these channel candidates,
            if given. Default is to search all channels.
        attribute_name (str): If set, search by channels with this attribute_name
            defined on them, with the value specified by `attribute_value`.
        attribute_value (any): What value the given attribute_name must have.
        typeclass (str or TypeClass): Filter by channels having this typeclass.
            This can also be a list of typeclasses.
        tags (str or list): Filter by channels having one or more Tags.
            This can be a single tag key, a list of tag keys, or a list of
            tuples (tag_key, tag_category).
        nofetch (bool): Don't fetch typeclass and perms data from db.
            This is faster but gives less info.

    Returns:
        matches (list): List of Channels matching the search criteria.
    """
    return ChannelDB.objects.search_channel(*args, **kwargs)


search_channels = search_channel
channel_search = search_channel
channels = search_channels


def search_help(*args, **kwargs):
    """
    Search for help entries in the database.

    Args:
        key (str or int): Help entry key or dbref to search for. This can also
            be a list of keys/dbrefs. `None` (default) returns all help entries.
        exact (bool): Only valid for string keys. If True, requires exact
            key match, otherwise also match key with case-insensitive and
            partial matching. Default is True.
        category (str): Filter by help entries in this category.
        tags (str or list): Filter by help entries having one or more Tags.
            This can be a single tag key, a list of tag keys, or a list of
            tuples (tag_key, tag_category).
        locks (str): Filter by help entries with these locks.

    Returns:
        matches (list): List of HelpEntries matching the search criteria.
    """
    return HelpEntry.objects.search_help(*args, **kwargs)


search_help_entry = search_help
search_help_entries = search_help
help_entry_search = search_help
help_entries = search_help


def search_object_attribute(
    key=None, category=None, value=None, strvalue=None, attrtype=None, **kwargs
):
    """
    Search for objects by their attributes.
    """
    return ObjectDB.objects.get_by_attribute(
        key=key, category=category, value=value, strvalue=strvalue, attrtype=attrtype, **kwargs
    )


def search_account_attribute(
    key=None, category=None, value=None, strvalue=None, attrtype=None, **kwargs
):
    """
    Search for accounts by their attributes.
    """
    return AccountDB.objects.get_by_attribute(
        key=key, category=category, value=value, strvalue=strvalue, attrtype=attrtype, **kwargs
    )


def search_script_attribute(
    key=None, category=None, value=None, strvalue=None, attrtype=None, **kwargs
):
    """
    Search for scripts by their attributes.
    """
    return ScriptDB.objects.get_by_attribute(
        key=key, category=category, value=value, strvalue=strvalue, attrtype=attrtype, **kwargs
    )


def search_channel_attribute(
    key=None, category=None, value=None, strvalue=None, attrtype=None, **kwargs
):
    """
    Search for channels by their attributes.
    """
    return ChannelDB.objects.get_by_attribute(
        key=key, category=category, value=value, strvalue=strvalue, attrtype=attrtype, **kwargs
    )


# Replace direct assignments with functions
def search_attribute_object(*args, **kwargs):
    """
    Search for attribute objects.
    """
    return ObjectDB.objects.get_attribute(*args, **kwargs)


def search_object_by_tag(key=None, category=None, tagtype=None, **kwargs):
    """
    Find object based on tag or category.

    Args:
        key (str, optional): The tag key to search for.
        category (str, optional): The category of tag
            to search for. If not set, uncategorized
            tags will be searched.
        tagtype (str, optional): 'type' of Tag, by default
            this is either `None` (a normal Tag), `alias` or
            `permission`. This always apply to all queried tags.
        kwargs (any): Other optional parameter that may be supported
            by the manager method.

    Returns:
        matches (list): List of Objects with tags matching
            the search criteria, or an empty list if no
            matches were found.
    """
    return ObjectDB.objects.get_by_tag(key=key, category=category, tagtype=tagtype, **kwargs)


search_tag = search_object_by_tag  # this is the most common case


def search_account_tag(key=None, category=None, tagtype=None, **kwargs):
    """
    Find account based on tag or category.
    """
    return AccountDB.objects.get_by_tag(key=key, category=category, tagtype=tagtype, **kwargs)


def search_script_tag(key=None, category=None, tagtype=None, **kwargs):
    """
    Find script based on tag or category.
    """
    return ScriptDB.objects.get_by_tag(key=key, category=category, tagtype=tagtype, **kwargs)


def search_channel_tag(key=None, category=None, tagtype=None, **kwargs):
    """
    Find channel based on tag or category.
    """
    return ChannelDB.objects.get_by_tag(key=key, category=category, tagtype=tagtype, **kwargs)


# Replace direct assignment with function
def search_tag_object(*args, **kwargs):
    """
    Search for tag objects.
    """
    return ObjectDB.objects.get_tag(*args, **kwargs)


def search_objects_by_typeclass(typeclass, include_children=False, include_parents=False):
    """
    Searches through all objects returning those of a certain typeclass.

    Args:
        typeclass (str or class): A typeclass class or a python path to a typeclass.
        include_children (bool, optional): Return objects with
            given typeclass *and* all children inheriting from this
            typeclass. Mutuall exclusive to `include_parents`.
        include_parents (bool, optional): Return objects with
            given typeclass *and* all parents to this typeclass.
            Mutually exclusive to `include_children`.

    Returns:
        objects (list): The objects found with the given typeclasses.
    """
    return ObjectDB.objects.typeclass_search(
        typeclass=typeclass,
        include_children=include_children,
        include_parents=include_parents,
    )


search_typeclass = search_objects_by_typeclass
