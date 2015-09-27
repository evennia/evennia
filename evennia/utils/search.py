
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

Example: To reach the search method 'get_object_with_player'
         in evennia/objects/managers.py:

> from evennia.objects.models import ObjectDB
> match = Object.objects.get_object_with_player(...)


"""

# Import the manager methods to be wrapped

from django.contrib.contenttypes.models import ContentType

# limit symbol import from API
__all__ = ("search_object", "search_player", "search_script",
           "search_message", "search_channel", "search_help_entry",
           "search_object_tag", "search_script_tag", "search_player_tag",
           "search_channel_tag")


# import objects this way to avoid circular import problems
ObjectDB = ContentType.objects.get(app_label="objects", model="objectdb").model_class()
PlayerDB = ContentType.objects.get(app_label="players", model="playerdb").model_class()
ScriptDB = ContentType.objects.get(app_label="scripts", model="scriptdb").model_class()
Msg = ContentType.objects.get(app_label="comms", model="msg").model_class()
Channel = ContentType.objects.get(app_label="comms", model="channeldb").model_class()
HelpEntry = ContentType.objects.get(app_label="help", model="helpentry").model_class()
Tag = ContentType.objects.get(app_label="typeclasses", model="tag").model_class()


#------------------------------------------------------------------
# Search manager-wrappers
#------------------------------------------------------------------

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
search_object = ObjectDB.objects.object_search
search_objects = search_object
object_search = search_object
objects = search_objects

#
# Search for players
#
# def player_search(self, ostring):
#     """
#     Searches for a particular player by name or
#     database id.
#
#     ostring = a string or database id.
#     """

search_player = PlayerDB.objects.player_search
search_players = search_player
player_search = search_player
players = search_players

#
#   Searching for scripts
#
# def script_search(self, ostring, obj=None, only_timed=False):
#     """
#     Search for a particular script.
#
#     ostring - search criterion - a script ID or key
#     obj - limit search to scripts defined on this object
#     only_timed - limit search only to scripts that run
#                  on a timer.
#     """

search_script = ScriptDB.objects.script_search
search_scripts = search_script
script_search = search_script
scripts = search_scripts
#
# Searching for communication messages
#
#
# def message_search(self, sender=None, receiver=None, channel=None, freetext=None):
#     """
#     Search the message database for particular messages. At least one
#     of the arguments must be given to do a search.
#
#     sender - get messages sent by a particular player
#     receiver - get messages received by a certain player
#     channel - get messages sent to a particular channel
#     freetext - Search for a text string in a message.
#                NOTE: This can potentially be slow, so make sure to supply
#                one of the other arguments to limit the search.
#     """

search_message = Msg.objects.message_search
search_messages = search_message
message_search = search_message
messages = search_messages

#
# Search for Communication Channels
#
# def channel_search(self, ostring)
#     """
#     Search the channel database for a particular channel.
#
#     ostring - the key or database id of the channel.
#     exact -  requires an exact ostring match (not case sensitive)
#     """

search_channel = Channel.objects.channel_search
search_channels = search_channel
channel_search = search_channel
channels = search_channels

#
# Find help entry objects.
#
# def search_help(self, ostring, help_category=None):
#     """
#     Retrieve a search entry object.
#
#     ostring - the help topic to look for
#     category - limit the search to a particular help topic
#     """

search_help = HelpEntry.objects.search_help
search_help_entry = search_help
search_help_entries = search_help
help_entry_search = search_help
help_entries = search_help


# Locate Attributes

#    search_object_attribute(key, category, value, strvalue) (also search_attribute works)
#    search_player_attribute(key, category, value, strvalue) (also search_attribute works)
#    search_script_attribute(key, category, value, strvalue) (also search_attribute works)
#    search_channel_attribute(key, category, value, strvalue) (also search_attribute works)

# Note that these return the object attached to the Attribute,
# not the attribute object itself (this is usually what you want)

def search_object_attribute(key=None, category=None, value=None, strvalue=None):
    return ObjectDB.objects.get_by_attribute(key=key, category=category, value=value, strvalue=strvalue)
def search_player_attribute(key=None, category=None, value=None, strvalue=None):
    return PlayerDB.objects.get_by_attribute(key=key, category=category, value=value, strvalue=strvalue)
def search_script_attribute(key=None, category=None, value=None, strvalue=None):
    return ScriptDB.objects.get_by_attribute(key=key, category=category, value=value, strvalue=strvalue)
def search_channel_attribute(key=None, category=None, value=None, strvalue=None):
    return Channel.objects.get_by_attribute(key=key, category=category, value=value, strvalue=strvalue)

# search for attribute objects
search_attribute_object = ObjectDB.objects.get_attribute

# Locate Tags

#    search_object_tag(key=None, category=None) (also search_tag works)
#    search_player_tag(key=None, category=None)
#    search_script_tag(key=None, category=None)
#    search_channel_tag(key=None, category=None)

# Note that this returns the object attached to the tag, not the tag
# object itself (this is usually what you want)
def search_object_tag(key=None, category=None):
    return ObjectDB.objects.get_by_tag(key=key, category=category)
search_tag = search_object_tag # this is the most common case
def search_player_tag(key=None, category=None):
    return PlayerDB.objects.get_by_tag(key=key, category=category)
def search_script_tag(key=None, category=None):
    return ScriptDB.objects.get_by_tag(key=key, category=category)
def search_channel_tag(key=None, category=None):
    return Channel.objects.get_by_tag(key=key, category=category)

# search for tag objects
search_tag_object = ObjectDB.objects.get_tag


