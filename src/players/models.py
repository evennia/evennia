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
from src.scripts.models import ScriptDB
from src.typeclasses.models import Attribute, TypedObject, TypeNick, TypeNickHandler
from src.typeclasses.typeclass import TypeClass
from src.commands.cmdsethandler import CmdSetHandler
from src.commands import cmdhandler
from src.utils import logger, utils
from src.utils.utils import inherits_from, make_iter

from django.utils.translation import ugettext as _

__all__  = ("PlayerAttribute", "PlayerNick", "PlayerDB")

_ME = _("me")
_SELF = _("self")

_SESSIONS = None
_AT_SEARCH_RESULT = utils.variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))
_MULTISESSION_MODE = settings.MULTISESSION_MODE

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
    # store a connected flag here too, not just in sessionhandler.
    # This makes it easier to track from various out-of-process locations
    db_is_connected = models.BooleanField(default=False, verbose_name="is_connected", help_text="If player is connected to game or not")
    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField('cmdset', max_length=255, null=True,
                                         help_text="optional python path to a cmdset class. If creating a Character, this will default to settings.CMDSET_CHARACTER.")

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
    def objs_get(self):
        "Getter. Allows for value = self.obj"
        return list(self.db_objs.all())
    #@objs.setter
    def objs_set(self, value):
        "Setter. Allows for self.objs = value"
        raise Exception("Use access methods to add new characters instead.")
    #@obj.deleter
    def objs_del(self):
        "Deleter. Allows for del self.obj"
        raise Exception("Use access methods to delete new characters instead.")
    objs = property(objs_get, objs_set, objs_del)
    characters = property(objs_get, objs_set, objs_del)

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
    def __name_get(self):
        "Getter. Allows for value = self.name"
        name = get_prop_cache(self, "_name")
        if not name:
            name = _GA(self,"user").username
            set_prop_cache(self, "_name", name)
        return name
    #@name.setter
    def __name_set(self, value):
        "Setter. Allows for player.name = newname"
        _GA(self, "user").username = value
        _GA(self, "user").save()
        set_prop_cache(self, "_name", value)
    #@name.deleter
    def __name_del(self):
        "Deleter. Allows for del self.name"
        raise Exception("Player name cannot be deleted!")
    name = property(__name_get, __name_set, __name_del)
    key = property(__name_get, __name_set, __name_del)

    #@property
    def __uid_get(self):
        "Getter. Retrieves the user id"
        uid = get_prop_cache(self, "_uid")
        if not uid:
            uid = _GA(self, "user").id
            set_prop_cache(self, "_uid", uid)
        return uid
    def __uid_set(self, value):
        raise Exception("User id cannot be set!")
    def __uid_del(self):
        raise Exception("User id cannot be deleted!")
    uid = property(__uid_get, __uid_set, __uid_del)

    #@property
    def __is_superuser_get(self):
        "Superusers have all permissions."
        is_suser = get_prop_cache(self, "_is_superuser")
        if is_suser == None:
            is_suser = _GA(self, "user").is_superuser
            set_prop_cache(self, "_is_superuser", is_suser)
        return is_suser
    is_superuser = property(__is_superuser_get)

    #
    # PlayerDB class access methods
    #

    def msg(self, outgoing_string, from_obj=None, data=None, sessid=None):
        """
        Evennia -> User
        This is the main route for sending data back to the user from the server.

        outgoing_string (string) - text data to send
        from_obj (Object/Player) - source object of message to send
        data (dict) - arbitrary data object containing eventual protocol-specific options
        sessid - the session id of the session to send to. If not given, return to
                 all sessions connected to this player. This is usually only
                 relevant when using msg() directly from a player-command (from
                 a command on a Character, the character automatically stores and
                 handles the sessid).
        """
        if from_obj:
            # call hook
            try:
                _GA(from_obj, "at_msg_send")(outgoing_string, to_obj=self, data=data)
            except Exception:
                pass
        outgoing_string = utils.to_str(outgoing_string, force_string=True)

        session = _MULTISESSION_MODE == 2 and sessid and _GA(self, "get_session")(sessid) or None
        if session:
            obj = session.puppet
            if obj and not obj.at_msg_receive(outgoing_string, from_obj=from_obj, data=data):
                # if hook returns false, cancel send
                return
            session.msg(outgoing_string, data)
        else:
            # if no session was specified, send to them all
            for sess in _GA(self, 'get_all_sessions')():
                sess.msg(outgoing_string, data)

    def inmsg(self, ingoing_string, session):
        """
        User -> Evennia
        This is the reverse of msg - used by sessions to relay
        messages/data back into the game. It is not called
        from inside game code but only by the serversessions directly.

        ingoing_string - text string (i.e. command string)
        data - dictionary of optional data
        session - session sending this data (no need to look it up again)
        """
        if _MULTISESSION_MODE == 1:
            # many sessions - one puppet
            sessions = [session for session in self.get_all_sessions() if session.puppet]
            session = sessions and sessions[0] or session

        puppet = session.puppet
        if puppet:
            # execute command on the puppeted object (this will include
            # cmdsets both on object and on player)
            _GA(puppet, "execute_cmd")(ingoing_string, sessid=session.sessid)
        else:
            # a non-character session; this executes on player directly
            # (this will only include cmdsets on player)
            _GA(self, "execute_cmd")(ingoing_string, sessid=session.sessid)


    # session-related methods

    def get_session(self, sessid):
        """
        Return session with given sessid connected to this player.
        """
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        return _SESSIONS.session_from_player(self, sessid)

    def get_all_sessions(self):
        "Return all sessions connected to this player"
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        return _SESSIONS.sessions_from_player(self)
    sessions = property(get_all_sessions) # alias shortcut


    def disconnect_session_from_player(self, sessid):
        """
        Access method for disconnecting a given session from the player
        (connection happens automatically in the sessionhandler)
        """
        # this should only be one value, loop just to make sure to clean everything
        sessions = (session for session in self.get_all_sessions() if session.sessid == sessid)
        for session in sessions:
            # this will also trigger unpuppeting
            session.sessionhandler.disconnect(session)

    # puppeting operations

    def puppet_object(self, sessid, obj, normal_mode=True):
        """
        Use the given session to control (puppet) the given object (usually
        a Character type). Note that we make no puppet checks here, that must
        have been done before calling this method.

        sessid - session id of session to connect
        obj - the object to connect to
        normal_mode - trigger hooks and extra checks - this is turned off when
                     the server reloads, to quickly re-connect puppets.

        returns True if successful, False otherwise
        """
        session = self.get_session(sessid)
        if not session:
            return False
        if normal_mode and session.puppet:
            # cleanly unpuppet eventual previous object puppeted by this session
            self.unpuppet_object(sessid)
        if obj.player and obj.player.is_connected and obj.player != self:
            # we don't allow to puppet an object already controlled by an active
            # player. To kick a player, call unpuppet_object on them explicitly.
            return
        # if we get to this point the character is ready to puppet or it was left
        # with a lingering player/sessid reference from an unclean server kill or similar

        if normal_mode:
            _GA(obj.typeclass, "at_pre_puppet")(self.typeclass, sessid=sessid)
        # do the connection
        obj.sessid = sessid
        obj.player = self
        session.puid = obj.id
        session.puppet = obj
        # validate/start persistent scripts on object
        ScriptDB.objects.validate(obj=obj)
        if normal_mode:
            _GA(obj.typeclass, "at_post_puppet")()
        return True

    def unpuppet_object(self, sessid):
        """
        Disengage control over an object

        sessid - the session id to disengage

        returns True if successful
        """
        session = self.get_session(sessid)
        if not session:
            return False
        obj = hasattr(session, "puppet") and session.puppet or None
        if not obj:
            return False
        # do the disconnect
        _GA(obj.typeclass, "at_pre_unpuppet")()
        del obj.dbobj.sessid
        del obj.dbobj.player
        session.puppet = None
        session.puid = None
        _GA(obj.typeclass, "at_post_unpuppet")(self.typeclass, sessid=sessid)
        return True

    def unpuppet_all(self):
        """
        Disconnect all puppets. This is called by server
        before a reset/shutdown.
        """
        for session in self.get_all_sessions():
            self.unpuppet_object(session.sessid)

    def get_puppet(self, sessid, return_dbobj=False):
        """
        Get an object puppeted by this session through this player. This is the main
        method for retrieving the puppeted object from the player's end.

        sessid - return character connected to this sessid,
        character - return character if connected to this player, else None.

        """
        session = self.get_session(sessid)
        if not session:
            return None
        if return_dbobj:
            return session.puppet
        return session.puppet and session.puppet.typeclass or None

    def get_all_puppets(self, return_dbobj=False):
        """
        Get all currently puppeted objects as a list
        """
        puppets = [session.puppet for session in self.get_all_sessions() if session.puppet]
        if return_dbobj:
            return puppets
        return [puppet.typeclass for puppet in puppets]

    def __get_single_puppet(self):
        """
        This is a legacy convenience link for users of
        MULTISESSION_MODE 0 or 1. It will return
        only the first puppet. For mode 2, this returns
        a list of all characters.
        """
        puppets = self.get_all_puppets()
        if _MULTISESSION_MODE in (0, 1):
            return puppets and puppets[0] or None
        return puppets
    character = property(__get_single_puppet)

    # utility methods


    def delete(self, *args, **kwargs):
        """
        Deletes the player permanently.
        Makes sure to delete user also when deleting player - the two may never exist separately.
        """
        for session in self.get_all_sessions():
            # unpuppeting all objects and disconnecting the user, if any
            # sessions remain (should usually be handled from the deleting command)
            self.unpuppet_object(session.sessid)
            session.sessionhandler.disconnect(session, reason=_("Player being deleted."))

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

    def execute_cmd(self, raw_string, sessid=None):
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
        if not sessid and _MULTISESSION_MODE in (0, 1):
            # in this case, we should either have only one sessid, or the sessid
            # should not matter (since the return goes to all of them we can just
            # use the first one as the source)
            sessid = self.get_all_sessions()[0].sessid
        return cmdhandler.cmdhandler(self.typeclass, raw_string, sessid=sessid)

    def search(self, ostring, return_character=False, **kwargs):
        """
        This is similar to the ObjectDB search method but will search for Players only. Errors
        will be echoed, and None returned if no Player is found.

        return_character - will try to return the character the player controls instead of
                           the Player object itself. If no Character exists (since Player is
                           OOC), None will be returned.
        Extra keywords are ignored, but are allowed in call in order to make API more consistent
                           with objects.models.TypedObject.search.
        """
        # handle me, self
        if ostring in (_ME, _SELF, '*' + _ME, '*' + _SELF):
            return self

        matches = _GA(self, "__class__").objects.player_search(ostring)
        matches = _AT_SEARCH_RESULT(self, ostring, matches, global_search=True)
        if matches and return_character:
            try:
                return _GA(matches, "character")
            except:
                pass
        return matches
