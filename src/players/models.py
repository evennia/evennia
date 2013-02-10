"""
Player

The Player class is a simple extension of the django User model using
the 'profile' system of django. A profile is a model that tack new
fields to the User model without actually editing the User model
(which would mean hacking into django internals which we want to avoid
for future compatability reasons).  The profile, which we call
'Player', is accessed with user.get_profile() by the property 'player'
defined on ObjectDB objects. Since we can customize it, we will try to
abstract as many operations as possible to work on Player rather than
on User.

We use the Player to store a more mud-friendly style of permission
system as well as to allow the admin more flexibility by storing
attributes on the Player.  Within the game we should normally use the
Player manager's methods to create users, since that automatically
adds the profile extension.

The default Django permission system is geared towards web-use, and is
defined on a per-application basis permissions. In django terms,
'src/objects' is one application, 'src/scripts' another, indeed all
folders in /src with a model.py inside them is an application. Django
permissions thus have the form
e.g. 'applicationlabel.permissionstring' and django automatically
defines a set of these for editing each application from its automatic
admin interface. These are still available should you want them.

For most in-game mud-use however, like commands and other things, it
does not make sense to tie permissions to the applications in src/ -
To the user these should all just be considered part of the game
engine. So instead we define our own separate permission system here,
borrowing heavily from the django original, but allowing the
permission string to look however we want, making them unrelated to
the applications.

To make the Player model more flexible for your own game, it can also
persistently store attributes of its own. This is ideal for extra
account info and OOC account configuration variables etc.

"""

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import smart_str

from src.server.caches import get_field_cache, set_field_cache, del_field_cache
from src.server.caches import get_prop_cache, set_prop_cache, del_prop_cache
from src.players import manager
from src.typeclasses.models import Attribute, TypedObject, TypeNick, TypeNickHandler
from src.typeclasses.typeclass import TypeClass
from src.commands.cmdsethandler import CmdSetHandler
from src.commands import cmdhandler
from src.utils import logger, utils
from src.utils.utils import inherits_from

__all__  = ("PlayerAttribute", "PlayerNick", "PlayerDB")

_SESSIONS = None
_AT_SEARCH_RESULT = utils.variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

_TYPECLASS = None

#------------------------------------------------------------
#
# PlayerAttribute
#
#------------------------------------------------------------

class PlayerAttribute(Attribute):
    """
    PlayerAttributes work the same way as Attributes on game objects,
    but are intended to store OOC information specific to each user
    and game (example would be configurations etc).
    """
    db_obj = models.ForeignKey("PlayerDB")

    class Meta:
        "Define Django meta options"
        verbose_name = "Player Attribute"

#------------------------------------------------------------
#
# Player Nicks
#
#------------------------------------------------------------

class PlayerNick(TypeNick):
    """

    The default nick types used by Evennia are:
    inputline (default) - match against all input
    player - match against player searches
    obj - match against object searches
    channel - used to store own names for channels
    """
    db_obj = models.ForeignKey("PlayerDB", verbose_name="player")

    class Meta:
        "Define Django meta options"
        verbose_name = "Nickname for Players"
        verbose_name_plural = "Nicknames Players"
        unique_together = ("db_nick", "db_type", "db_obj")

class PlayerNickHandler(TypeNickHandler):
    """
    Handles nick access and setting. Accessed through ObjectDB.nicks
    """
    NickClass = PlayerNick


#------------------------------------------------------------
#
# PlayerDB
#
#------------------------------------------------------------

class PlayerDB(TypedObject):
    """
    This is a special model using Django's 'profile' functionality
    and extends the default Django User model. It is defined as such
    by use of the variable AUTH_PROFILE_MODULE in the settings.
    One accesses the fields/methods. We try use this model as much
    as possible rather than User, since we can customize this to
    our liking.

    The TypedObject supplies the following (inherited) properties:
      key - main name
      typeclass_path - the path to the decorating typeclass
      typeclass - auto-linked typeclass
      date_created - time stamp of object creation
      permissions - perm strings
      dbref - #id of object
      db - persistent attribute storage
      ndb - non-persistent attribute storage

    The PlayerDB adds the following properties:
      user - Connected User object. django field, needs to be save():d.
      obj - game object controlled by player
      character - alias for obj
      name - alias for user.username
      sessions - sessions connected to this player
      is_superuser - bool if this player is a superuser

    """

    #
    # PlayerDB Database model setup
    #
    # inherited fields (from TypedObject):
    # db_key, db_typeclass_path, db_date_created, db_permissions

    # this is the one-to-one link between the customized Player object and
    # this profile model. It is required by django.
    user = models.ForeignKey(User, unique=True, db_index=True,
      help_text="The <I>User</I> object holds django-specific authentication for each Player. A unique User should be created and tied to each Player, the two should never be switched or changed around. The User will be deleted automatically when the Player is.")
    # the in-game object connected to this player (if any).
    # Use the property 'obj' to access.
    db_obj = models.ForeignKey("objects.ObjectDB", null=True, blank=True,
                               verbose_name="character", help_text='In-game object.')
    # store a connected flag here too, not just in sessionhandler.
    # This makes it easier to track from various out-of-process locations
    db_is_connected = models.BooleanField(default=False, verbose_name="is_connected", help_text="If player is connected to game or not")
    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField('cmdset', max_length=255, null=True,
                                         help_text="optional python path to a cmdset class. If creating a Character, this will default to settings.CMDSET_DEFAULT.")

    # Database manager
    objects = manager.PlayerManager()

    class Meta:
        app_label = 'players'
        verbose_name = 'Player'

    def __init__(self, *args, **kwargs):
        "Parent must be initiated first"
        TypedObject.__init__(self, *args, **kwargs)
        # handlers
        _SA(self, "cmdset", CmdSetHandler(self))
        _GA(self, "cmdset").update(init_mode=True)
        _SA(self, "nicks", PlayerNickHandler(self))

    # Wrapper properties to easily set database fields. These are
    # @property decorators that allows to access these fields using
    # normal python operations (without having to remember to save()
    # etc). So e.g. a property 'attr' has a get/set/del decorator
    # defined that allows the user to do self.attr = value,
    # value = self.attr and del self.attr respectively (where self
    # is the object in question).

    # obj property (wraps db_obj)
    #@property
    def obj_get(self):
        "Getter. Allows for value = self.obj"
        return get_field_cache(self, "obj")
    #@obj.setter
    def obj_set(self, value):
        "Setter. Allows for self.obj = value"
        global _TYPECLASS
        if not _TYPECLASS:
            from src.typeclasses.typeclass import TypeClass as _TYPECLASS

        if isinstance(value, _TYPECLASS):
            value = value.dbobj
        try:
            set_field_cache(self, "obj", value)
        except Exception:
            logger.log_trace()
            raise Exception("Cannot assign %s as a player object!" % value)
    #@obj.deleter
    def obj_del(self):
        "Deleter. Allows for del self.obj"
        del_field_cache(self, "obj")
    obj = property(obj_get, obj_set, obj_del)

    # whereas the name 'obj' is consistent with the rest of the code,
    # 'character' is a more intuitive property name, so we
    # define this too, as an alias to player.obj.
    #@property
    def character_get(self):
        "Getter. Allows for value = self.character"
        return get_field_cache(self, "obj")
    #@character.setter
    def character_set(self, character):
        "Setter. Allows for self.character = value"
        if inherits_from(character, TypeClass):
            character = character.dbobj
        set_field_cache(self, "obj", character)
    #@character.deleter
    def character_del(self):
        "Deleter. Allows for del self.character"
        del_field_cache(self, "obj")
    character = property(character_get, character_set, character_del)
    # cmdset_storage property
    # This seems very sensitive to caching, so leaving it be for now /Griatch
    #@property
    def cmdset_storage_get(self):
        "Getter. Allows for value = self.name. Returns a list of cmdset_storage."
        if _GA(self, "db_cmdset_storage"):
            return [path.strip() for path  in _GA(self, "db_cmdset_storage").split(',')]
        return []
    #@cmdset_storage.setter
    def cmdset_storage_set(self, value):
        "Setter. Allows for self.name = value. Stores as a comma-separated string."
        if utils.is_iter(value):
            value = ",".join([str(val).strip() for val in value])
        _SA(self, "db_cmdset_storage", value)
        _GA(self, "save")()
    #@cmdset_storage.deleter
    def cmdset_storage_del(self):
        "Deleter. Allows for del self.name"
        _SA(self, "db_cmdset_storage", "")
        _GA(self, "save")()
    cmdset_storage = property(cmdset_storage_get, cmdset_storage_set, cmdset_storage_del)

    #@property
    def is_connected_get(self):
        "Getter. Allows for value = self.is_connected"
        return get_field_cache(self, "is_connected")
    #@is_connected.setter
    def is_connected_set(self, value):
        "Setter. Allows for self.is_connected = value"
        set_field_cache(self, "is_connected", value)
    #@is_connected.deleter
    def is_connected_del(self):
        "Deleter. Allows for del is_connected"
        set_field_cache(self, "is_connected", False)
    is_connected = property(is_connected_get, is_connected_set, is_connected_del)

    class Meta:
        "Define Django meta options"
        verbose_name = "Player"
        verbose_name_plural = "Players"

    #
    # PlayerDB main class properties and methods
    #

    def __str__(self):
        return smart_str("%s(player %s)" % (_GA(self, "name"), _GA(self, "dbid")))

    def __unicode__(self):
        return u"%s(player#%s)" % (_GA(self, "name"), _GA(self, "dbid"))

    # this is required to properly handle attributes and typeclass loading
    _typeclass_paths = settings.PLAYER_TYPECLASS_PATHS
    _attribute_class = PlayerAttribute
    _db_model_name = "playerdb" # used by attributes to safely store objects
    _default_typeclass_path = settings.BASE_PLAYER_TYPECLASS or "src.players.player.Player"

    # name property (wraps self.user.username)
    #@property
    def name_get(self):
        "Getter. Allows for value = self.name"
        name = get_prop_cache(self, "_name")
        if not name:
            name = _GA(self,"user").username
            set_prop_cache(self, "_name", name)
        return name
    #@name.setter
    def name_set(self, value):
        "Setter. Allows for player.name = newname"
        _GA(self, "user").username = value
        _GA(self, "user").save()
        set_prop_cache(self, "_name", value)
    #@name.deleter
    def name_del(self):
        "Deleter. Allows for del self.name"
        raise Exception("Player name cannot be deleted!")
    name = property(name_get, name_set, name_del)
    key = property(name_get, name_set, name_del)

    #@property
    def uid_get(self):
        "Getter. Retrieves the user id"
        uid = get_prop_cache(self, "_uid")
        if not uid:
            uid = _GA(self, "user").id
            set_prop_cache(self, "_uid", uid)
        return uid
    def uid_set(self, value):
        raise Exception("User id cannot be set!")
    def uid_del(self):
        raise Exception("User id cannot be deleted!")
    uid = property(uid_get, uid_set, uid_del)

    # sessions property
    #@property
    def sessions_get(self):
        "Getter. Retrieve sessions related to this player/user"
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        return _SESSIONS.sessions_from_player(self)
    #@sessions.setter
    def sessions_set(self, value):
        "Setter. Protects the sessions property from adding things"
        raise Exception("Cannot set sessions manually!")
    #@sessions.deleter
    def sessions_del(self):
        "Deleter. Protects the sessions property from deletion"
        raise Exception("Cannot delete sessions manually!")
    sessions = property(sessions_get, sessions_set, sessions_del)

    #@property
    def is_superuser_get(self):
        "Superusers have all permissions."
        is_suser = get_prop_cache(self, "_is_superuser")
        if is_suser == None:
            is_suser = _GA(self, "user").is_superuser
            set_prop_cache(self, "_is_superuser", is_suser)
        return is_suser
    is_superuser = property(is_superuser_get)

    #
    # PlayerDB class access methods
    #

    def msg(self, outgoing_string, from_obj=None, data=None):
        """
        Evennia -> User
        This is the main route for sending data back to the user from the server.
        """
        if from_obj:
            try:
                _GA(from_obj, "at_msg_send")(outgoing_string, to_obj=self, data=data)
            except Exception:
                pass
        if (_GA(self, "character") and not
            _GA(self, "character").at_msg_receive(outgoing_string, from_obj=from_obj, data=data)):
            # the at_msg_receive() hook may block receiving of certain messages
            return

        outgoing_string = utils.to_str(outgoing_string, force_string=True)

        for session in _GA(self, 'sessions'):
            session.msg(outgoing_string, data)


    def swap_character(self, new_character, delete_old_character=False):
        """
        Swaps character, if possible
        """
        return _GA(self, "__class__").objects.swap_character(self, new_character, delete_old_character=delete_old_character)

    def delete(self, *args, **kwargs):
        "Make sure to delete user also when deleting player - the two may never exist separately."
        try:
            if _GA(self, "user"):
                _GA(_GA(self, "user"), "delete")()
        except AssertionError:
            pass
        try:
            super(PlayerDB, self).delete(*args, **kwargs)
        except AssertionError:
            # this means deleting the user already cleared out the Player object.
            pass
    #
    # Execution/action methods
    #

    def execute_cmd(self, raw_string):
        """
        Do something as this player. This command transparently
        lets its typeclass execute the command.
        raw_string - raw command input coming from the command line.
        """
        # nick replacement - we require full-word matching.

        raw_string = utils.to_unicode(raw_string)

        raw_list = raw_string.split(None)
        raw_list = [" ".join(raw_list[:i+1]) for i in range(len(raw_list)) if raw_list[:i+1]]
        for nick in PlayerNick.objects.filter(db_obj=self, db_type__in=("inputline","channel")):
            if nick.db_nick in raw_list:
                raw_string = raw_string.replace(nick.db_nick, nick.db_real, 1)
                break
        return cmdhandler.cmdhandler(self.typeclass, raw_string)

    def search(self, ostring, return_character=False):
        """
        This is similar to the ObjectDB search method but will search for Players only. Errors
        will be echoed, and None returned if no Player is found.

        return_character - will try to return the character the player controls instead of
                           the Player object itself. If no Character exists (since Player is
                           OOC), None will be returned.
        """
        matches = _GA(self, "__class__").objects.player_search(ostring)
        matches = _AT_SEARCH_RESULT(self, ostring, matches, global_search=True)
        if matches and return_character:
            try:
                return _GA(matches, "character")
            except:
                pass
        return matches
