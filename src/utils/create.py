"""
This module gathers all the essential database-creation
functions for the game engine's various object types.

Only objects created 'stand-alone' are in here, e.g. object Attributes
are always created directly through their respective objects.

Each creation_* function also has an alias named for the entity being
created, such as create_object() and object().  This is for
consistency with the utils.search module and allows you to do the
shorter "create.object()".

The respective object managers hold more methods for manipulating and
searching objects already existing in the database.

Models covered:
 Objects
 Scripts
 Help
 Message
 Channel
 Players
"""
from django.conf import settings
from django.db import IntegrityError
from src.utils.idmapper.models import SharedMemoryModel
from src.utils import utils, logger
from src.utils.utils import make_iter

# delayed imports
_User = None
_Object = None
_ObjectDB = None
_Script = None
_ScriptDB = None
_HelpEntry = None
_Msg = None
_Player = None
_PlayerDB = None
_to_object = None
_ChannelDB = None
_channelhandler = None


# limit symbol import from API
__all__ = ("create_object", "create_script", "create_help_entry",
           "create_message", "create_channel", "create_player")

_GA = object.__getattribute__

# Helper function

def handle_dbref(inp, objclass, raise_errors=True):
    """
    Convert a #dbid to a valid object of objclass. objclass
    should be a valid object class to filter against (objclass.filter ...)
    If not raise_errors is set, this will swallow errors of non-existing
    objects.
    """
    if not (isinstance(inp, basestring) and inp.startswith("#")):
        try:
            return inp.dbobj
        except AttributeError:
            return inp

    # a string, analyze it
    inp = inp.lstrip('#')
    try:
        if int(inp) < 0:
            return None
    except ValueError:
        return None

    # if we get to this point, inp is an integer dbref; get the matching object
    try:
        return objclass.objects.get(id=inp)
    except Exception:
        if raise_errors:
            raise
        return inp

#
# Game Object creation
#

def create_object(typeclass=None, key=None, location=None,
                  home=None, permissions=None, locks=None,
                  aliases=None, destination=None, report_to=None, nohome=False):
    """
    Create a new in-game object. Any game object is a combination
    of a database object that stores data persistently to
    the database, and a typeclass, which on-the-fly 'decorates'
    the database object into whataver different type of object
    it is supposed to be in the game.

    See src.objects.managers for methods to manipulate existing objects
    in the database. src.objects.objects holds the base typeclasses
    and src.objects.models hold the database model.

    report_to is an optional object for reporting errors to in string form.
              If report_to is not set, errors will be raised as en Exception
              containing the error message. If set, this method will return
              None upon errors.
    nohome - this allows the creation of objects without a default home location;
             this only used when creating the default location itself or during unittests
    """
    global _Object, _ObjectDB
    if not _Object:
        from src.objects.objects import Object as _Object
    if not _ObjectDB:
        from src.objects.models import ObjectDB as _ObjectDB

    # input validation

    if not typeclass:
        typeclass = settings.BASE_OBJECT_TYPECLASS
    elif isinstance(typeclass, _ObjectDB):
        # this is already an objectdb instance, extract its typeclass
        typeclass = typeclass.typeclass.path
    elif isinstance(typeclass, _Object) or utils.inherits_from(typeclass, _Object):
        # this is already an object typeclass, extract its path
        typeclass = typeclass.path
    typeclass = utils.to_unicode(typeclass)

    # Setup input for the create command

    location = handle_dbref(location, _ObjectDB)
    destination = handle_dbref(destination, _ObjectDB)
    home = handle_dbref(home, _ObjectDB)
    if not home:
        try:
            home = handle_dbref(settings.DEFAULT_HOME, _ObjectDB) if not nohome else None
        except _ObjectDB.DoesNotExist:
            raise _ObjectDB.DoesNotExist("settings.DEFAULT_HOME (= '%s') does not exist, or the setting is malformed." %
                                         settings.DEFAULT_HOME)

    # create new database object all in one go
    new_db_object = _ObjectDB(db_key=key, db_location=location,
                              db_destination=destination, db_home=home,
                              db_typeclass_path=typeclass)

    if not key:
        # the object should always have a key, so if not set we give a default
        new_db_object.key = "#%i" % new_db_object.dbid

    # this will either load the typeclass or the default one (will also save object)
    new_object = new_db_object.typeclass

    if not _GA(new_object, "is_typeclass")(typeclass, exact=True):
        # this will fail if we gave a typeclass as input and it still
        # gave us a default
        try:
            SharedMemoryModel.delete(new_db_object)
        except AssertionError:
            # this happens if object was never created
            pass
        if report_to:
            report_to = handle_dbref(report_to, _ObjectDB)
            _GA(report_to, "msg")("Error creating %s (%s).\n%s" % (new_db_object.key, typeclass,
                                                                 _GA(new_db_object, "typeclass_last_errmsg")))
            return None
        else:
            raise Exception(_GA(new_db_object, "typeclass_last_errmsg"))

    # from now on we can use the typeclass object
    # as if it was the database object.

    # call the hook methods. This is where all at_creation
    # customization happens as the typeclass stores custom
    # things on its database object.

    # note - this may override input keys, locations etc!
    new_object.basetype_setup()  # setup the basics of Exits, Characters etc.
    new_object.at_object_creation()

    # we want the input to override that set in the hooks, so
    # we re-apply those if needed
    if new_object.key != key:
        new_object.key = key
    if new_object.location != location:
        new_object.location = location
    if new_object.home != home:
        new_object.home = home
    if new_object.destination != destination:
        new_object.destination = destination

    # custom-given perms/locks do overwrite hooks
    if permissions:
        new_object.permissions.add(permissions)
    if locks:
        new_object.locks.add(locks)
    if aliases:
        new_object.aliases.add(aliases)

    # trigger relevant move_to hooks in order to display messages.
    if location:
        location.at_object_receive(new_object, None)
        new_object.at_after_move(None)

    # post-hook setup (mainly used by Exits)
    new_object.basetype_posthook_setup()

    return new_object

#alias for create_object
object = create_object


#
# Script creation
#

def create_script(typeclass, key=None, obj=None, player=None, locks=None,
                  interval=None, start_delay=None, repeats=None,
                  persistent=None, autostart=True, report_to=None):
    """
    Create a new script. All scripts are a combination
    of a database object that communicates with the
    database, and an typeclass that 'decorates' the
    database object into being different types of scripts.
    It's behaviour is similar to the game objects except
    scripts has a time component and are more limited in
    scope.

    Argument 'typeclass' can be either an actual
    typeclass object or a python path to such an object.
    Only set key here if you want a unique name for this
    particular script (set it in config to give
    same key to all scripts of the same type). Set obj
    to tie this script to a particular object.

    See src.scripts.manager for methods to manipulate existing
    scripts in the database.

    report_to is an obtional object to receive error messages.
              If report_to is not set, an Exception with the
              error will be raised. If set, this method will
              return None upon errors.
    """
    global _Script, _ScriptDB
    if not _Script:
        from src.scripts.scripts import Script as _Script
    if not _ScriptDB:
        from src.scripts.models import ScriptDB as _ScriptDB

    if not typeclass:
        typeclass = settings.BASE_SCRIPT_TYPECLASS
    elif isinstance(typeclass, _ScriptDB):
        # this is already an scriptdb instance, extract its typeclass
        typeclass = typeclass.typeclass.path
    elif isinstance(typeclass, _Script) or utils.inherits_from(typeclass, _Script):
        # this is already an object typeclass, extract its path
        typeclass = typeclass.path

    # create new database script
    new_db_script = _ScriptDB()

    # assign the typeclass
    typeclass = utils.to_unicode(typeclass)
    new_db_script.typeclass_path = typeclass

    # the name/key is often set later in the typeclass. This
    # is set here as a failsafe.
    if key:
        new_db_script.key = key
    else:
        new_db_script.key = "#%i" % new_db_script.id

    # this will either load the typeclass or the default one
    new_script = new_db_script.typeclass

    if not _GA(new_db_script, "is_typeclass")(typeclass, exact=True):
        # this will fail if we gave a typeclass as input and it still
        # gave us a default
        SharedMemoryModel.delete(new_db_script)
        if report_to:
            _GA(report_to, "msg")("Error creating %s (%s): %s" % (new_db_script.key, typeclass,
                                                                 _GA(new_db_script, "typeclass_last_errmsg")))
            return None
        else:
            raise Exception(_GA(new_db_script, "typeclass_last_errmsg"))

    if obj:
        new_script.obj = obj
    if player:
        new_script.player = player

    # call the hook method. This is where all at_creation
    # customization happens as the typeclass stores custom
    # things on its database object.
    new_script.at_script_creation()

    # custom-given variables override the hook
    if key:
        new_script.key = key
    if locks:
        new_script.locks.add(locks)
    if interval is not None:
        new_script.interval = interval
    if start_delay is not None:
        new_script.start_delay = start_delay
    if repeats is not None:
        new_script.repeats = repeats
    if persistent is not None:
        new_script.persistent = persistent

    # must do this before starting the script since some
    # scripts may otherwise run for a very short time and
    # try to delete itself before we have a time to save it.
    new_db_script.save()

    # a new created script should usually be started.
    if autostart:
        new_script.start()

    return new_script
#alias
script = create_script


#
# Help entry creation
#

def create_help_entry(key, entrytext, category="General", locks=None):
    """
    Create a static help entry in the help database. Note that Command
    help entries are dynamic and directly taken from the __doc__ entries
    of the command. The database-stored help entries are intended for more
    general help on the game, more extensive info, in-game setting information
    and so on.
    """
    global _HelpEntry
    if not _HelpEntry:
        from src.help.models import HelpEntry as _HelpEntry

    try:
        new_help = _HelpEntry()
        new_help.key = key
        new_help.entrytext = entrytext
        new_help.help_category = category
        if locks:
            new_help.locks.add(locks)
        new_help.save()
        return new_help
    except IntegrityError:
        string = "Could not add help entry: key '%s' already exists." % key
        logger.log_errmsg(string)
        return None
    except Exception:
        logger.log_trace()
        return None
# alias
help_entry = create_help_entry


#
# Comm system methods
#

def create_message(senderobj, message, channels=None,
                   receivers=None, locks=None, header=None):
    """
    Create a new communication message. Msgs are used for all
    player-to-player communication, both between individual players
    and over channels.
    senderobj - the player sending the message. This must be the actual object.
    message - text with the message. Eventual headers, titles etc
              should all be included in this text string. Formatting
              will be retained.
    channels - a channel or a list of channels to send to. The channels
             may be actual channel objects or their unique key strings.
    receivers - a player to send to, or a list of them. May be Player objects
               or playernames.
    locks - lock definition string
    header - mime-type or other optional information for the message

    The Comm system is created very open-ended, so it's fully possible
    to let a message both go to several channels and to several receivers
    at the same time, it's up to the command definitions to limit this as
    desired.
    """
    global _Msg
    if not _Msg:
        from src.comms.models import Msg as _Msg
    if not message:
        # we don't allow empty messages.
        return
    new_message = _Msg(db_message=message)
    new_message.save()
    for sender in make_iter(senderobj):
        new_message.senders = sender
    new_message.header = header
    for channel in make_iter(channels):
        new_message.channels = channel
    for receiver in make_iter(receivers):
        new_message.receivers = receiver
    if locks:
        new_message.locks.add(locks)
    new_message.save()
    return new_message
message = create_message


def create_channel(key, aliases=None, desc=None,
                   locks=None, keep_log=True,
                   typeclass=None):
    """
    Create A communication Channel. A Channel serves as a central
    hub for distributing Msgs to groups of people without
    specifying the receivers explicitly. Instead players may
    'connect' to the channel and follow the flow of messages. By
    default the channel allows access to all old messages, but
    this can be turned off with the keep_log switch.

    key - this must be unique.
    aliases - list of alternative (likely shorter) keynames.
    locks - lock string definitions
    """
    global _ChannelDB, _channelhandler
    if not _ChannelDB:
        from src.comms.models import ChannelDB as _ChannelDB
    if not _channelhandler:
        from src.comms import channelhandler as _channelhandler
    if not typeclass:
        typeclass = settings.BASE_CHANNEL_TYPECLASS
    try:
        new_channel = _ChannelDB(typeclass=typeclass, db_key=key)
        new_channel.save()
        new_channel = new_channel.typeclass
        if aliases:
            if not utils.is_iter(aliases):
                aliases = [aliases]
            new_channel.aliases.add(aliases)
        new_channel.save()
        new_channel.db.desc = desc
        new_channel.db.keep_log = keep_log
    except IntegrityError:
        string = "Could not add channel: key '%s' already exists." % key
        logger.log_errmsg(string)
        return None
    if locks:
        new_channel.locks.add(locks)
    new_channel.save()
    _channelhandler.CHANNELHANDLER.add_channel(new_channel)
    new_channel.at_channel_create()
    return new_channel

channel = create_channel



#
# Player creation methods
#

def create_player(key, email, password,
                  typeclass=None,
                  is_superuser=False,
                  locks=None, permissions=None,
                  report_to=None):

    """
    This creates a new player.

    key - the player's name. This should be unique.
    email - email on valid addr@addr.domain form.
    password - password in cleartext
    is_superuser - wether or not this player is to be a superuser
    locks - lockstring
    permission - list of permissions
    report_to - an object with a msg() method to report errors to. If
                not given, errors will be logged.

    Will return the Player-typeclass or None/raise Exception if the
    Typeclass given failed to load.

    Concerning is_superuser:
     Usually only the server admin should need to be superuser, all
     other access levels can be handled with more fine-grained
     permissions or groups. A superuser bypasses all lock checking
     operations and is thus not suitable for play-testing the game.

    """
    global _PlayerDB, _Player
    if not _PlayerDB:
        from src.players.models import PlayerDB as _PlayerDB
    if not _Player:
        from src.players.player import Player as _Player

    if not email:
        email = "dummy@dummy.com"
    if _PlayerDB.objects.filter(username__iexact=key):
        raise ValueError("A Player with the name '%s' already exists." % key)

    # this handles a given dbref-relocate to a player.
    report_to = handle_dbref(report_to, _PlayerDB)

    try:

        # create the correct Player object
        if is_superuser:
            new_db_player = _PlayerDB.objects.create_superuser(key, email, password)
        else:
            new_db_player = _PlayerDB.objects.create_user(key, email, password)

        if not typeclass:
            typeclass = settings.BASE_PLAYER_TYPECLASS
        elif isinstance(typeclass, _PlayerDB):
            # this is an PlayerDB instance, extract its typeclass path
            typeclass = typeclass.typeclass.path
        elif isinstance(typeclass, _Player) or utils.inherits_from(typeclass, _Player):
            # this is Player object typeclass, extract its path
            typeclass = typeclass.path

        # assign the typeclass
        typeclass = utils.to_unicode(typeclass)
        new_db_player.typeclass_path = typeclass

        # this will either load the typeclass or the default one
        new_player = new_db_player.typeclass

        if not _GA(new_db_player, "is_typeclass")(typeclass, exact=True):
            # this will fail if we gave a typeclass as input
            # and it still gave us a default
            SharedMemoryModel.delete(new_db_player)
            if report_to:
                _GA(report_to, "msg")("Error creating %s (%s):\n%s" % (new_db_player.key, typeclass,
                                                                  _GA(new_db_player, "typeclass_last_errmsg")))
                return None
            else:
                raise Exception(_GA(new_db_player, "typeclass_last_errmsg"))

        new_player.basetype_setup()  # setup the basic locks and cmdset
        # call hook method (may override default permissions)
        new_player.at_player_creation()

        # custom given arguments potentially overrides the hook
        if permissions:
            new_player.permissions.add(permissions)
        elif not new_player.permissions:
            new_player.permissions.add(settings.PERMISSION_PLAYER_DEFAULT)
        if locks:
            new_player.locks.add(locks)
        return new_player

    except Exception:
        # a failure in creating the player; we try to clean
        # up as much as we can
        logger.log_trace()
        try:
            new_player.delete()
        except Exception:
            pass
        try:
            del new_player
        except Exception:
            pass
        raise

# alias
player = create_player
