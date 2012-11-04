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
from django.contrib.auth.models import User
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
_Channel = None
_channelhandler = None


# limit symbol import from API
__all__ = ("create_object", "create_script", "create_help_entry", "create_message", "create_channel", "create_player")

_GA = object.__getattribute__

#
# Game Object creation
#

def create_object(typeclass, key=None, location=None,
                  home=None, player=None, permissions=None, locks=None,
                  aliases=None, destination=None, report_to=None):
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
    """
    global _Object, _ObjectDB
    if not _Object:
        from src.objects.objects import Object as _Object
    if not _ObjectDB:
        from src.objects.models import ObjectDB as _ObjectDB

    if not typeclass:
        typeclass = settings.BASE_OBJECT_TYPECLASS
    elif isinstance(typeclass, _ObjectDB):
        # this is already an objectdb instance, extract its typeclass
        typeclass = typeclass.typeclass.path
    elif isinstance(typeclass, _Object) or utils.inherits_from(typeclass, _Object):
        # this is already an object typeclass, extract its path
        typeclass = typeclass.path

    # create new database object
    new_db_object = _ObjectDB()

    # assign the typeclass
    typeclass = utils.to_unicode(typeclass)
    new_db_object.typeclass_path = typeclass

    # the name/key is often set later in the typeclass. This
    # is set here as a failsafe.
    if key:
        new_db_object.key = key
    else:
        new_db_object.key = "#%i" % new_db_object.dbid

    # this will either load the typeclass or the default one
    new_object = new_db_object.typeclass

    if not _GA(new_object, "is_typeclass")(typeclass, exact=True):
        # this will fail if we gave a typeclass as input and it still gave us a default
        SharedMemoryModel.delete(new_db_object)
        if report_to:
            _GA(report_to, "msg")("Error creating %s (%s):\n%s" % (new_db_object.key, typeclass,
                                                                 _GA(new_db_object, "typeclass_last_errmsg")))
            return None
        else:
            raise Exception(_GA(new_db_object, "typeclass_last_errmsg"))

    # from now on we can use the typeclass object
    # as if it was the database object.

    if player:
        # link a player and the object together
        new_object.player = player
        player.obj = new_object

    new_object.destination = destination

    # call the hook method. This is where all at_creation
    # customization happens as the typeclass stores custom
    # things on its database object.
    new_object.basetype_setup() # setup the basics of Exits, Characters etc.
    new_object.at_object_creation()

    # custom-given perms/locks overwrite hooks
    if permissions:
        new_object.permissions = permissions
    if locks:
         new_object.locks.add(locks)
    if aliases:
        new_object.aliases = aliases

    # perform a move_to in order to display eventual messages.
    if home:
        new_object.home = home
    else:
        new_object.home =  settings.CHARACTER_DEFAULT_HOME


    if location:
         new_object.move_to(location, quiet=True)
    else:
        # rooms would have location=None.
        new_object.location = None

    # post-hook setup (mainly used by Exits)
    new_object.basetype_posthook_setup()

    new_object.save()
    return new_object

#alias for create_object
object = create_object

#
# Script creation
#

def create_script(typeclass, key=None, obj=None, locks=None,
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
        # this will fail if we gave a typeclass as input and it still gave us a default
        SharedMemoryModel.delete(new_db_script)
        if report_to:
            _GA(report_to, "msg")("Error creating %s (%s): %s" % (new_db_script.key, typeclass,
                                                                 _GA(new_db_script, "typeclass_last_errmsg")))
            return None
        else:
            raise Exception(_GA(new_db_script, "typeclass_last_errmsg"))

    if obj:
        try:
            new_script.obj = obj
        except ValueError:
            new_script.obj = obj.dbobj

    # call the hook method. This is where all at_creation
    # customization happens as the typeclass stores custom
    # things on its database object.
    new_script.at_script_creation()

    # custom-given variables override the hook
    if key:
        new_script.key = key
    if locks:
        new_script.locks.add(locks)
    if interval != None:
        new_script.interval = interval
    if start_delay != None:
        new_script.start_delay = start_delay
    if repeats != None:
        new_script.repeats = repeats
    if persistent != None:
        new_script.persistent = persistent

    # a new created script should usually be started.
    if autostart:
        new_script.start()

    new_db_script.save()
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
                   locks=None, keep_log=True):
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
    global _Channel, _channelhandler
    if not _Channel:
        from src.comms.models import Channel as _Channel
    if not _channelhandler:
        from src.comms import channelhandler as _channelhandler
    try:
        new_channel = _Channel()
        new_channel.key = key
        if aliases:
            if not utils.is_iter(aliases):
                aliases = [aliases]
            new_channel.aliases = ",".join([alias for alias in aliases])
        new_channel.desc = desc
        new_channel.keep_log = keep_log
    except IntegrityError:
        string = "Could not add channel: key '%s' already exists." % key
        logger.log_errmsg(string)
        return None
    if locks:
        new_channel.locks.add(locks)
    new_channel.save()
    _channelhandler.CHANNELHANDLER.add_channel(new_channel)
    return new_channel

channel = create_channel

#
# Player creation methods
#

def create_player(name, email, password,
                  user=None,
                  typeclass=None,
                  is_superuser=False,
                  locks=None, permissions=None,
                  create_character=True, character_typeclass=None,
                  character_location=None, character_home=None,
                  player_dbobj=None, report_to=None):


    """
    This creates a new player, handling the creation of the User
    object and its associated Player object.

    If player_dbobj is given, this player object is used instead of
    creating a new one. This is called by the admin interface since it
    needs to create the player object in order to relate it automatically
    to the user.

    If create_character is
    True, a game player object with the same name as the User/Player will
    also be created. Its typeclass and base properties can also be given.

    Returns the new game character, or the Player obj if no
    character is created.  For more info about the typeclass argument,
    see create_objects() above.

    Note: if user is supplied, it will NOT be modified (args name, email,
    passw and is_superuser will be ignored). Change those properties
    directly on the User instead.

    If no permissions are given (None), the default permission group
    as defined in settings.PERMISSION_PLAYER_DEFAULT will be
    assigned. If permissions are given, no automatic assignment will
    occur.

    Concerning is_superuser:
     A superuser should have access to everything
     in the game and on the server/web interface. The very first user
     created in the database is always a superuser (that's using
     django's own creation, not this one).
     Usually only the server admin should need to be superuser, all
     other access levels can be handled with more fine-grained
     permissions or groups.
     Since superuser overrules all permissions, we don't
     set any in this case.

    """
    # The system should already have checked so the name/email
    # isn't already registered, and that the password is ok before
    # getting here.
    global _PlayerDB, _Player
    if not _PlayerDB:
        from src.players.models import PlayerDB as _PlayerDB
    if not _Player:
        from src.players.player import Player as _Player

    if not email:
        email = "dummy@dummy.com"
    if user:
        new_user = user
        email = user.email
    else:
        if is_superuser:
            new_user = User.objects.create_superuser(name, email, password)
        else:
            new_user = User.objects.create_user(name, email, password)
    try:
        if not typeclass:
            typeclass = settings.BASE_PLAYER_TYPECLASS
        elif isinstance(typeclass, _PlayerDB):
            # this is already an objectdb instance, extract its typeclass
            typeclass = typeclass.typeclass.path
        elif isinstance(typeclass, _Player) or utils.inherits_from(typeclass, _Player):
            # this is already an object typeclass, extract its path
            typeclass = typeclass.path
        if player_dbobj:
            try:
                _GA(player_dbobj, "dbobj")
                new_db_player = player_dbobj.dbobj
            except AttributeError:
                new_db_player = player_dbobj
            # use the typeclass from this object
            typeclass = new_db_player.typeclass_path
        else:
            new_db_player = _PlayerDB(db_key=name, user=new_user)
            new_db_player.save()
            # assign the typeclass
            typeclass = utils.to_unicode(typeclass)
            new_db_player.typeclass_path = typeclass

        # this will either load the typeclass or the default one
        new_player = new_db_player.typeclass

        if not _GA(new_db_player, "is_typeclass")(typeclass, exact=True):
            # this will fail if we gave a typeclass as input and it still gave us a default
            SharedMemoryModel.delete(new_db_player)
            if report_to:
                _GA(report_to, "msg")("Error creating %s (%s):\n%s" % (new_db_player.key, typeclass,
                                                                  _GA(new_db_player, "typeclass_last_errmsg")))
                return None
            else:
                raise Exception(_GA(new_db_player, "typeclass_last_errmsg"))

        new_player.basetype_setup() # setup the basic locks and cmdset
        # call hook method (may override default permissions)
        new_player.at_player_creation()

        # custom given arguments potentially overrides the hook
        if permissions:
            new_player.permissions = permissions
        elif not new_player.permissions:
            new_player.permissions = settings.PERMISSION_PLAYER_DEFAULT

        if locks:
            new_player.locks.add(locks)

        # create *in-game* 'player' object
        if create_character:
            if not character_typeclass:
                character_typeclass = settings.BASE_CHARACTER_TYPECLASS
            # creating the object automatically links the player
            # and object together by player.obj <-> obj.player
            new_character = create_object(character_typeclass, key=name,
                                          location=character_location, home=character_location,
                                          permissions=permissions,
                                          player=new_player, report_to=report_to)
            return new_character
        return new_player
    except Exception, e:
        # a failure in creating the character
        if not user:
            # in there was a failure we clean up everything we can
            logger.log_trace()
            try:
                new_user.delete()
            except Exception:
                pass
            try:
                new_player.delete()
            except Exception:
                pass
            try:
                del new_character
            except Exception:
                pass
        raise e

# alias
player = create_player
