"""
This module gathers all the essential database-creation functions for the game
engine's various object types.

Only objects created 'stand-alone' are in here. E.g. object Attributes are
always created through their respective objects handlers.

Each `creation_*` function also has an alias named for the entity being created,
such as create_object() and object(). This is for consistency with the
utils.search module and allows you to do the shorter `create.object()`.

The respective object managers hold more methods for manipulating and searching
objects already existing in the database.

"""

from django.contrib.contenttypes.models import ContentType
from django.db.utils import OperationalError, ProgrammingError

# limit symbol import from API
__all__ = (
    "create_object",
    "create_script",
    "create_help_entry",
    "create_message",
    "create_channel",
    "create_account",
)

_GA = object.__getattribute__

# import objects this way to avoid circular import problems
try:
    ObjectDB = ContentType.objects.get(app_label="objects", model="objectdb").model_class()
    ScriptDB = ContentType.objects.get(app_label="scripts", model="scriptdb").model_class()
    AccountDB = ContentType.objects.get(app_label="accounts", model="accountdb").model_class()
    Msg = ContentType.objects.get(app_label="comms", model="msg").model_class()
    ChannelDB = ContentType.objects.get(app_label="comms", model="channeldb").model_class()
    HelpEntry = ContentType.objects.get(app_label="help", model="helpentry").model_class()
    Tag = ContentType.objects.get(app_label="typeclasses", model="tag").model_class()
except (OperationalError, ProgrammingError):
    # this is a fallback used during tests/doc building
    print("Database not available yet - using temporary fallback for create managers.")
    from evennia.accounts.models import AccountDB
    from evennia.comms.models import ChannelDB, Msg
    from evennia.help.models import HelpEntry
    from evennia.objects.models import ObjectDB
    from evennia.scripts.models import ScriptDB
    from evennia.typeclasses.tags import Tag  # noqa

#
# Game Object creation
#
# Create a new in-game object.
#
# Keyword Args:
#     typeclass (class or str): Class or python path to a typeclass.
#     key (str): Name of the new object. If not set, a name of
#         `#dbref` will be set.
#     location (Object or str): Obj or #dbref to use as the location of the new object.
#     home (Object or str): Obj or #dbref to use as the object's home location.
#     permissions (list): A list of permission strings or tuples (permstring, category).
#     locks (str): one or more lockstrings, separated by semicolons.
#     aliases (list): A list of alternative keys or tuples (aliasstring, category).
#     tags (list): List of tag keys or tuples (tagkey, category) or (tagkey, category, data).
#     destination (Object or str): Obj or #dbref to use as an Exit's target.
#     report_to (Object): The object to return error messages to.
#     nohome (bool): This allows the creation of objects without a
#         default home location; only used when creating the default
#         location itself or during unittests.
#     attributes (list): Tuples on the form (key, value) or (key, value, category),
#         (key, value, lockstring) or (key, value, lockstring, default_access).
#         to set as Attributes on the new object.
#     nattributes (list): Non-persistent tuples on the form (key, value). Note that
#         adding this rarely makes sense since this data will not survive a reload.
#
# Returns:
#     object (Object): A newly created object of the given typeclass.
#
# Raises:
#     ObjectDB.DoesNotExist: If trying to create an Object with
#         `location` or `home` that can't be found.
#

create_object = ObjectDB.objects.create_object
# alias for create_object
object = create_object


#
# Script creation

# Create a new script. All scripts are a combination of a database
# object that communicates with the database, and an typeclass that
# 'decorates' the database object into being different types of
# scripts.  It's behaviour is similar to the game objects except
# scripts has a time component and are more limited in scope.
#
# Keyword Args:
#     typeclass (class or str): Class or python path to a typeclass.
#     key (str): Name of the new object. If not set, a name of
#         #dbref will be set.
#     obj (Object): The entity on which this Script sits. If this
#         is `None`, we are creating a "global" script.
#     account (Account): The account on which this Script sits. It is
#         exclusiv to `obj`.
#     locks (str): one or more lockstrings, separated by semicolons.
#     interval (int): The triggering interval for this Script, in
#         seconds. If unset, the Script will not have a timing
#         component.
#     start_delay (bool): If `True`, will wait `interval` seconds
#         before triggering the first time.
#     repeats (int): The number of times to trigger before stopping.
#         If unset, will repeat indefinitely.
#     persistent (bool): If this Script survives a server shutdown
#         or not (all Scripts will survive a reload).
#     autostart (bool): If this Script will start immediately when
#         created or if the `start` method must be called explicitly.
#     report_to (Object): The object to return error messages to.
#     desc (str): Optional description of script
#     tags (list): List of tags or tuples (tag, category).
#     attributes (list): List if tuples (key, value) or (key, value, category)
#        (key, value, lockstring) or (key, value, lockstring, default_access).
#
# Returns:
#     script (obj): An instance of the script created
#
# See evennia.scripts.manager for methods to manipulate existing
# scripts in the database.

create_script = ScriptDB.objects.create_script
# alias
script = create_script


#
# Help entry creation
#

# """
# Create a static help entry in the help database. Note that Command
# help entries are dynamic and directly taken from the __doc__
# entries of the command. The database-stored help entries are
# intended for more general help on the game, more extensive info,
# in-game setting information and so on.
#
# Args:
#     key (str): The name of the help entry.
#     entrytext (str): The body of te help entry
#     category (str, optional): The help category of the entry.
#     locks (str, optional): A lockstring to restrict access.
#     aliases (list of str, optional): List of alternative (likely shorter) keynames.
#     tags (lst, optional): List of tags or tuples `(tag, category)`.
#
# Returns:
#     help (HelpEntry): A newly created help entry.
#

create_help_entry = HelpEntry.objects.create_help
# alias
help_entry = create_help_entry


#
# Comm system methods

#
# Create a new communication Msg. Msgs represent a unit of
# database-persistent communication between entites.
#
# Args:
#     senderobj (Object, Account, Script, str or list): The entity (or
#         entities) sending the Msg. If a `str`, this is the id-string
#         for an external sender type.
#     message (str): Text with the message. Eventual headers, titles
#         etc should all be included in this text string. Formatting
#         will be retained.
#     receivers (Object, Account, Script, str or list): An Account/Object to send
#         to, or a list of them. If a string, it's an identifier for an external
#         receiver.
#     locks (str): Lock definition string.
#     tags (list): A list of tags or tuples `(tag, category)`.
#     header (str): Mime-type or other optional information for the message
#
# Notes:
#     The Comm system is created to be very open-ended, so it's fully
#     possible to let a message both go several receivers at the same time,
#     it's up to the command definitions to limit this as desired.
#

create_message = Msg.objects.create_message
message = create_message
create_msg = create_message


# Create A communication Channel. A Channel serves as a central hub
# for distributing Msgs to groups of people without specifying the
# receivers explicitly. Instead accounts may 'connect' to the channel
# and follow the flow of messages. By default the channel allows
# access to all old messages, but this can be turned off with the
# keep_log switch.
#
# Args:
#     key (str): This must be unique.
#
# Keyword Args:
#     aliases (list of str): List of alternative (likely shorter) keynames.
#     desc (str): A description of the channel, for use in listings.
#     locks (str): Lockstring.
#     keep_log (bool): Log channel throughput.
#     typeclass (str or class): The typeclass of the Channel (not
#         often used).
#     tags (list): A list of tags or tuples `(tag, category)`.
#
# Returns:
#     channel (Channel): A newly created channel.
#

create_channel = ChannelDB.objects.create_channel
channel = create_channel


#
# Account creation methods
#

# This creates a new account.
#
# Args:
#     key (str): The account's name. This should be unique.
#     email (str or None): Email on valid addr@addr.domain form. If
#         the empty string, will be set to None.
#     password (str): Password in cleartext.
#
# Keyword Args:
#     typeclass (str): The typeclass to use for the account.
#     is_superuser (bool): Wether or not this account is to be a superuser
#     locks (str): Lockstring.
#     permission (list): List of permission strings.
#     tags (list): List of Tags on form `(key, category[, data])`
#     attributes (list): List of Attributes on form
#          `(key, value [, category, [,lockstring [, default_pass]]])`
#     report_to (Object): An object with a msg() method to report
#         errors to. If not given, errors will be logged.
#
# Returns:
#     Account: The newly created Account.
# Raises:
#     ValueError: If `key` already exists in database.
#
#
# Notes:
#     Usually only the server admin should need to be superuser, all
#     other access levels can be handled with more fine-grained
#     permissions or groups. A superuser bypasses all lock checking
#     operations and is thus not suitable for play-testing the game.

create_account = AccountDB.objects.create_account
# alias
account = create_account
