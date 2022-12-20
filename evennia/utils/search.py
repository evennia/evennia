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

# Import the manager methods to be wrapped

from django.contrib.contenttypes.models import ContentType
from django.db.utils import OperationalError, ProgrammingError

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


# import objects this way to avoid circular import problems
try:
    ObjectDB = ContentType.objects.get(app_label="objects", model="objectdb").model_class()
    AccountDB = ContentType.objects.get(app_label="accounts", model="accountdb").model_class()
    ScriptDB = ContentType.objects.get(app_label="scripts", model="scriptdb").model_class()
    Msg = ContentType.objects.get(app_label="comms", model="msg").model_class()
    ChannelDB = ContentType.objects.get(app_label="comms", model="channeldb").model_class()
    HelpEntry = ContentType.objects.get(app_label="help", model="helpentry").model_class()
    Tag = ContentType.objects.get(app_label="typeclasses", model="tag").model_class()
except (OperationalError, ProgrammingError):
    # this is a fallback used during tests/doc building
    print("Database not available yet - using temporary fallback for search managers.")
    from evennia.accounts.models import AccountDB
    from evennia.comms.models import ChannelDB, Msg
    from evennia.help.models import HelpEntry
    from evennia.objects.models import ObjectDB
    from evennia.scripts.models import ScriptDB
    from evennia.typeclasses.tags import Tag  # noqa

# -------------------------------------------------------------------
# Search manager-wrappers
# -------------------------------------------------------------------

#
# Search objects as a character
#
# NOTE: A more powerful wrapper of this method
#  is reachable from within each command class
#  by using self.caller.search()!
#
#    def object_search(self, ostring=None,
#                      attribute_name=None,
#                      typeclass=None,
#                      candidates=None,
#                      exact=True):
#
#        Search globally or in a list of candidates and return results.
#        The result is always a list of Objects (or the empty list)
#
#        Arguments:
#        ostring: (str) The string to compare names against. By default (if
#                  not attribute_name is set), this will search object.key
#                  and object.aliases in order. Can also be on the form #dbref,
#                  which will, if exact=True be matched against primary key.
#        attribute_name: (str): Use this named ObjectAttribute to match ostring
#                        against, instead of the defaults.
#        typeclass (str or TypeClass): restrict matches to objects having
#                  this typeclass. This will help speed up global searches.
#        candidates (list obj ObjectDBs): If supplied, search will only be
#                  performed among the candidates in this list. A common list
#                  of candidates is the contents of the current location.
#        exact (bool): Match names/aliases exactly or partially. Partial
#                  matching matches the beginning of words in the names/aliases,
#                  using a matching routine to separate multiple matches in
#                  names with multiple components (so "bi sw" will match
#                  "Big sword"). Since this is more expensive than exact
#                  matching, it is recommended to be used together with
#                  the objlist keyword to limit the number of possibilities.
#                  This keyword has no meaning if attribute_name is set.
#
#        Returns:
#        A list of matching objects (or a list with one unique match)
#    def object_search(self, ostring, caller=None,
#                      candidates=None,
#                      attribute_name=None):
#
search_object = ObjectDB.objects.search_object
search_objects = search_object
object_search = search_object
objects = search_objects

#
# Search for accounts
#
# account_search(self, ostring)

#     Searches for a particular account by name or
#     database id.
#
#     ostring = a string or database id.
#

search_account = AccountDB.objects.search_account
search_accounts = search_account
account_search = search_account
accounts = search_accounts

#
#   Searching for scripts
#
# script_search(self, ostring, obj=None, only_timed=False)
#
#     Search for a particular script.
#
#     ostring - search criterion - a script ID or key
#     obj - limit search to scripts defined on this object
#     only_timed - limit search only to scripts that run
#                  on a timer.
#

search_script = ScriptDB.objects.search_script
search_scripts = search_script
script_search = search_script
scripts = search_scripts
#
# Searching for communication messages
#
#
# message_search(self, sender=None, receiver=None, channel=None, freetext=None)
#
#     Search the message database for particular messages. At least one
#     of the arguments must be given to do a search.
#
#     sender - get messages sent by a particular account
#     receiver - get messages received by a certain account
#     channel - get messages sent to a particular channel
#     freetext - Search for a text string in a message.
#                NOTE: This can potentially be slow, so make sure to supply
#                one of the other arguments to limit the search.
#

search_message = Msg.objects.search_message
search_messages = search_message
message_search = search_message
messages = search_messages

#
# Search for Communication Channels
#
# channel_search(self, ostring)
#
#     Search the channel database for a particular channel.
#
#     ostring - the key or database id of the channel.
#     exact -  requires an exact ostring match (not case sensitive)
#

search_channel = ChannelDB.objects.search_channel
search_channels = search_channel
channel_search = search_channel
channels = search_channels

#
# Find help entry objects.
#
# search_help(self, ostring, help_category=None)
#
#     Retrieve a search entry object.
#
#     ostring - the help topic to look for
#     category - limit the search to a particular help topic
#

search_help = HelpEntry.objects.search_help
search_help_entry = search_help
search_help_entries = search_help
help_entry_search = search_help
help_entries = search_help


# Locate Attributes

#    search_object_attribute(key, category, value, strvalue) (also search_attribute works)
#    search_account_attribute(key, category, value, strvalue) (also search_attribute works)
#    search_script_attribute(key, category, value, strvalue) (also search_attribute works)
#    search_channel_attribute(key, category, value, strvalue) (also search_attribute works)

# Note that these return the object attached to the Attribute,
# not the attribute object itself (this is usually what you want)


def search_object_attribute(
    key=None, category=None, value=None, strvalue=None, attrtype=None, **kwargs
):
    return ObjectDB.objects.get_by_attribute(
        key=key, category=category, value=value, strvalue=strvalue, attrtype=attrtype, **kwargs
    )


def search_account_attribute(
    key=None, category=None, value=None, strvalue=None, attrtype=None, **kwargs
):
    return AccountDB.objects.get_by_attribute(
        key=key, category=category, value=value, strvalue=strvalue, attrtype=attrtype, **kwargs
    )


def search_script_attribute(
    key=None, category=None, value=None, strvalue=None, attrtype=None, **kwargs
):
    return ScriptDB.objects.get_by_attribute(
        key=key, category=category, value=value, strvalue=strvalue, attrtype=attrtype, **kwargs
    )


def search_channel_attribute(
    key=None, category=None, value=None, strvalue=None, attrtype=None, **kwargs
):
    return ChannelDB.objects.get_by_attribute(
        key=key, category=category, value=value, strvalue=strvalue, attrtype=attrtype, **kwargs
    )


# search for attribute objects
search_attribute_object = ObjectDB.objects.get_attribute

# Locate Tags

#    search_object_tag(key=None, category=None) (also search_tag works)
#    search_account_tag(key=None, category=None)
#    search_script_tag(key=None, category=None)
#    search_channel_tag(key=None, category=None)

# Note that this returns the object attached to the tag, not the tag
# object itself (this is usually what you want)


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
        matches (list): List of Accounts with tags matching
            the search criteria, or an empty list if no
            matches were found.

    """
    return AccountDB.objects.get_by_tag(key=key, category=category, tagtype=tagtype, **kwargs)


def search_script_tag(key=None, category=None, tagtype=None, **kwargs):
    """
    Find script based on tag or category.

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
        matches (list): List of Scripts with tags matching
            the search criteria, or an empty list if no
            matches were found.

    """
    return ScriptDB.objects.get_by_tag(key=key, category=category, tagtype=tagtype, **kwargs)


def search_channel_tag(key=None, category=None, tagtype=None, **kwargs):
    """
    Find channel based on tag or category.

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
        matches (list): List of Channels with tags matching
            the search criteria, or an empty list if no
            matches were found.

    """
    return ChannelDB.objects.get_by_tag(key=key, category=category, tagtype=tagtype, **kwargs)


# search for tag objects (not the objects they are attached to
search_tag_object = ObjectDB.objects.get_tag


# Locate Objects by Typeclass

# search_objects_by_typeclass(typeclass="", include_children=False, include_parents=False) (also search_typeclass works)
# This returns the objects of the given typeclass


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
