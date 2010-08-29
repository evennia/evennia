"""
This module gathers all the essential database-creation
methods for the game engine's various object types.
Only objects created 'stand-alone' are in here,
e.g. object Attributes are always created directly through their
respective objects.

The respective object managers hold more methods for
manipulating and searching objects already existing in
the database. 

Models covered: 
 Objects
 Scripts
 Help
 PermissionGroup
 Message
 Channel 
 Players
"""

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError
from src.players.models import PlayerDB
from src.help.models import HelpEntry
from src.comms.models import Msg, Channel 
from src.comms import channelhandler 
from src.comms.managers import to_object
from src.permissions.permissions import set_perm
from src.permissions.models import PermissionGroup
from src.utils import logger
from src.utils.utils import is_iter

#
# Game Object creation 
#

def create_object(typeclass, key=None, location=None,
                  home=None, player=None, permissions=None, aliases=None):
    """
    Create a new in-game object. Any game object is a combination
    of a database object that stores data persistently to
    the database, and a typeclass, which on-the-fly 'decorates'
    the database object into whataver different type of object
    it is supposed to be in the game. 

    See src.objects.managers for methods to manipulate existing objects
    in the database. src.objects.objects holds the base typeclasses
    and src.objects.models hold the database model. 
    """
    # deferred import to avoid loops
    from src.objects.objects import Object
    from src.objects.models import ObjectDB
    #print "in create_object", typeclass
    if isinstance(typeclass, ObjectDB):
        # this is already an object instance!
        new_db_object = typeclass            
        typeclass = new_db_object.typeclass
    elif isinstance(typeclass, Object):
        # this is already an object typeclass!        
        new_db_object = typeclass.dbobj
        typeclass = typeclass.__class__
    else:
        # create database object 
        new_db_object = ObjectDB()
    #new_db_object = ObjectDB()
    if not callable(typeclass):
        # this means typeclass might be a path. If not,
        # the type mechanism will automatically assign
        # the BASE_OBJECT_TYPE from settings. 
        if typeclass:
            typeclass = str(typeclass)
            new_db_object.typeclass_path = typeclass
        new_db_object.save()
        # this will either load the typeclass or the default one
        typeclass = new_db_object.typeclass        
    new_db_object.save()
    # the name/key is often set later in the typeclass. This
    # is set here as a failsafe. 
    if key:
        new_db_object.name = key 
    else:
        dbref = new_db_object.id
        if typeclass and hasattr(typeclass, '__name__'):
            new_db_object.name = "%s%i" % (typeclass.__name__, dbref)
        else:
            new_db_object.name = "#%i" % dbref

    # initialize an object of this typeclass.
    new_object = typeclass(new_db_object)

    # from now on we can use the typeclass object 
    # as if it was the database object.

    if player:
        # link a player and the object together
        new_object.player = player
        player.obj = new_object
    
    if permissions:
        set_perm(new_object, permissions)
    if aliases:
        if not is_iter(aliases):
            aliases = [aliases]
        new_object.aliases = ",".join([alias.strip() for alias in aliases])

    # call the hook method. This is where all at_creation
    # customization happens as the typeclass stores custom
    # things on its database object.
    new_object.at_object_creation()

    # perform a move_to in order to display eventual messages.
    if home:
        new_object.home = home
    if location:
        new_object.move_to(location, quiet=True)
    else:
        # rooms would have location=None.
        new_object.location = None                             
    new_object.save()
    return new_object

#
# Script creation 
#

def create_script(typeclass, key=None, obj=None, autostart=True):
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
    """
    # deferred import to avoid loops.
    from src.scripts.scripts import Script
    #print "in create_script", typeclass    
    from src.scripts.models import ScriptDB    
    if isinstance(typeclass, ScriptDB):
        #print "this is already a script instance!", typeclass, typeclass.__class__
        new_db_object = typeclass            
        typeclass = new_db_object.typeclass
    elif isinstance(typeclass, Script):
        #print "this is already an object typeclass!"
        new_db_object = typeclass.dbobj
        typeclass = typeclass.__class__
    else:
        # create a new instance.
        new_db_object = ScriptDB()
    #new_db_object = ScriptDB()
    if not callable(typeclass):
        # try to load this in case it's a path
        if typeclass:
            typeclass = str(typeclass)
            new_db_object.typeclass_path = typeclass
        new_db_object.save()
        # this will load either the typeclass or the default one
        typeclass = new_db_object.typeclass
    new_db_object.save()    
    # the typeclass is initialized
    new_script = typeclass(new_db_object)
    # store variables on the typeclass (which means
    # it's actually transparently stored on the db object)
    if key:
        new_db_object.name = key 
    else:
        if typeclass and hasattr(typeclass, '__name__'):
            new_db_object.name = "%s" % typeclass.__name__
        else:
            new_db_object.name = "#%i" % new_db_object.id
    if obj:
        try:
            new_script.obj = obj
        except ValueError:
            new_script.obj = obj.dbobj
    # call the hook method. This is where all at_creation
    # customization happens as the typeclass stores custom
    # things on its database object.
    new_script.at_script_creation()
    
    new_script.save()

    # a new created script should always be started, so 
    # we do this now.
    if autostart:
        new_script.start()

    return new_script 

#
# Help entry creation
#

def create_help_entry(key, entrytext, category="General", permissions=None):
    """
    Create a static help entry in the help database. Note that Command
    help entries are dynamic and directly taken from the __doc__ entries
    of the command. The database-stored help entries are intended for more
    general help on the game, more extensive info, in-game setting information
    and so on. 
    """
    try:
        new_help = HelpEntry()
        new_help.key = key
        new_help.entrytext = entrytext
        new_help.help_category = category
        if permissions:
            set_perm(new_help, permissions)
        new_help.save()
        return new_help 
    except IntegrityError:
        string = "Could not add help entry: key '%s' already exists." % key
        logger.log_errmsg(string)
        return None
    except Exception:
        logger.log_trace()
        return None 

#
# Permission groups
#

def create_permission_group(group_name, desc=None, group_perms=None,
                            permissions=None):
    """
    Adds a new group

    group_name - case sensitive, unique key for group.
    desc - description of permission group
    group_perms - the permissions stored in this group - can be
                  a list of permission strings, a single permission
                  or a comma-separated string of permissions.
    permissions - can be a list of permission strings, a single
                  permission or a comma-separated string of permissions.
                  OBS-these are the group's OWN permissions, for editing
                  the group etc - NOT the permissions stored in it! 
    """

    new_group = PermissionGroup.objects.filter(db_key__exact=group_name)
    if new_group:
        new_group = new_group[0]
    else:
        new_group = PermissionGroup()
    new_group.key = group_name
    if desc:
        new_group.desc = desc 
    if group_perms:
        if is_iter(group_perms):
            group_perms = ",".join([str(perm) for perm in group_perms])
        new_group.group_permissions = group_perms
    if permissions:
        set_perm(new_group, permissions)
    new_group.save()
    return new_group



#
# Comm system methods 
#

def create_message(senderobj, message, channels=None,
                   receivers=None, permissions=None):
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
    permissions - permission string, or a list of permission strings.     

    The Comm system is created very open-ended, so it's fully possible
    to let a message both go to several channels and to several receivers
    at the same time, it's up to the command definitions to limit this as
    desired. 

    Since messages are often directly created by the user, this method (and all
    comm methods) raise CommErrors with different message strings to make it
    easier for the Command definition to give proper feedback to the user. 
    """
    
    def to_player(obj):
        "Make sure the object is a player object"
        if hasattr(obj, 'user'):
            return obj
        elif hasattr(obj, 'player'):
            return obj.player
        else:
            return None 

    if not message:
        # we don't allow empty messages. 
        return

    new_message = Msg()
    new_message.sender = to_player(senderobj)
    new_message.message = message
    new_message.save()
    if channels:
        if not is_iter(channels):
            channels = [channels]
        new_message.channels = [channel for channel in
                                [to_object(channel, objtype='channel')
                                 for channel in channels] if channel] 
    if receivers:
        #print "Found receiver:", receivers
        if not is_iter(receivers):
            receivers = [receivers]
        #print "to_player: %s" % to_player(receivers[0])
        new_message.receivers = [to_player(receiver) for receiver in
                                 [to_object(receiver) for receiver in receivers]
                                 if receiver] 
    if permissions:
        set_perm(new_message, permissions)
    new_message.save()
    return new_message

def create_channel(key, aliases=None, description=None,
                   permissions=None, keep_log=True):
    """
    Create A communication Channel. A Channel serves as a central
    hub for distributing Msgs to groups of people without
    specifying the receivers explicitly. Instead players may
    'connect' to the channel and follow the flow of messages. By
    default the channel allows access to all old messages, but
    this can be turned off with the keep_log switch. 

    key - this must be unique. 
    aliases - list of alternative (likely shorter) keynames.
    listen/send/admin permissions are strings if permissions separated
         by commas.
    """
    try:
        new_channel = Channel()
        new_channel.key = key 
        if aliases:
            if not is_iter(aliases):
                aliases = [aliases]
            new_channel.aliases = ",".join([str(alias) for alias in aliases])
        new_channel.description = description
        new_channel.keep_log = keep_log
    except IntegrityError:
        string = "Could not add channel: key '%s' already exists." % key
        logger.log_errmsg(string)
        return None
    if permissions:
        set_perm(new_channel, permissions)
    new_channel.save()
    channelhandler.CHANNELHANDLER.add_channel(new_channel)
    return new_channel 
    
#
# Player creation methods 
#

def create_player(name, email, password,
                  permissions=None, 
                  create_character=True,
                  location=None, typeclass=None, home=None,
                  is_superuser=False, user=None):
    
    """
    This creates a new player, handling the creation of the User
    object and its associated Player object. If create_character is
    True, a game player object with the same name as the User/Player will
    also be created. Returns the new game character, or the Player obj if no
    character is created.  For more info about the typeclass argument,
    see create_objects() above.
    
    Note: if user is supplied, it will NOT be modified (args name, email, 
    passw and is_superuser will be ignored). Change those properties 
    explicitly instead. 

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
    set any here.
    
    """
    # The system should already have checked so the name/email
    # isn't already registered, and that the password is ok before
    # getting here. 

    if user:
        new_user = user
    else:
        if is_superuser:
            new_user = User.objects.create_superuser(name, email, password)
        else:
            new_user = User.objects.create_user(name, email, password) 

    # create the associated Player for this User, and tie them together
    new_player = PlayerDB(user=new_user)        
    new_player.save()        

    # assign mud permissions 
    if not permissions:
        permissions = settings.PERMISSION_PLAYER_DEFAULT
    set_perm(new_player, permissions)

    # create *in-game* 'player' object 
    if create_character:
        if not typeclass:
            typeclass = settings.BASE_CHARACTER_TYPECLASS
        # creating the object automatically links the player
        # and object together by player.obj <-> obj.player
        new_character = create_object(typeclass, name,
                                      location, home,
                                      player=new_player)        
        set_perm(new_character, permissions)
        return new_character
    return new_player
