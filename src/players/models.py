"""
Player

The player class is an extension of the default Django user class,
and is customized for the needs of Evennia.

We use the Player to store a more mud-friendly style of permission
system as well as to allow the admin more flexibility by storing
attributes on the Player.  Within the game we should normally use the
Player manager's methods to create users so that permissions are set
correctly.

To make the Player model more flexible for your own game, it can also
persistently store attributes of its own. This is ideal for extra
account info and OOC account configuration variables etc.

"""

from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.encoding import smart_str

from src.players import manager
from src.scripts.models import ScriptDB
from src.typeclasses.models import (TypedObject, NickHandler)
from src.scripts.scripthandler import ScriptHandler
from src.commands.cmdsethandler import CmdSetHandler
from src.commands import cmdhandler
from src.utils import utils, logger
from src.utils.utils import to_str, make_iter, lazy_property

from django.utils.translation import ugettext as _

__all__ = ("PlayerDB",)

#_ME = _("me")
#_SELF = _("self")

_SESSIONS = None
_AT_SEARCH_RESULT = utils.variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))
_MULTISESSION_MODE = settings.MULTISESSION_MODE

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

_TYPECLASS = None


#------------------------------------------------------------
#
# PlayerDB
#
#------------------------------------------------------------

class PlayerDB(TypedObject, AbstractUser):
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
      is_bot - bool if this player is a bot and not a real player

    """

    #
    # PlayerDB Database model setup
    #
    # inherited fields (from TypedObject):
    # db_key, db_typeclass_path, db_date_created, db_permissions

    # store a connected flag here too, not just in sessionhandler.
    # This makes it easier to track from various out-of-process locations
    db_is_connected = models.BooleanField(default=False,
                                          verbose_name="is_connected",
                                          help_text="If player is connected to game or not")
    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField('cmdset', max_length=255, null=True,
        help_text="optional python path to a cmdset class. If creating a Character, this will default to settings.CMDSET_CHARACTER.")
    # marks if this is a "virtual" bot player object
    db_is_bot = models.BooleanField(default=False, verbose_name="is_bot", help_text="Used to identify irc/imc2/rss bots")

    # Database manager
    objects = manager.PlayerManager()

    # caches for quick lookups
    _typeclass_paths = settings.PLAYER_TYPECLASS_PATHS
    _default_typeclass_path = settings.BASE_PLAYER_TYPECLASS or "src.players.player.Player"

    class Meta:
        app_label = 'players'
        verbose_name = 'Player'

    # lazy-loading of handlers
    @lazy_property
    def cmdset(self):
        return CmdSetHandler(self, True)

    @lazy_property
    def scripts(self):
        return ScriptHandler(self)

    @lazy_property
    def nicks(self):
        return NickHandler(self)


    # alias to the objs property
    def __characters_get(self):
        return self.objs

    def __characters_set(self, value):
        self.objs = value

    def __characters_del(self):
        raise Exception("Cannot delete name")
    characters = property(__characters_get, __characters_set, __characters_del)

    # cmdset_storage property
    # This seems very sensitive to caching, so leaving it be for now /Griatch
    #@property
    def cmdset_storage_get(self):
        """
        Getter. Allows for value = self.name. Returns a list of cmdset_storage.
        """
        storage = _GA(self, "db_cmdset_storage")
        # we need to check so storage is not None
        return [path.strip() for path in storage.split(',')] if storage else []

    #@cmdset_storage.setter
    def cmdset_storage_set(self, value):
        """
        Setter. Allows for self.name = value. Stores as a comma-separated
        string.
        """
        _SA(self, "db_cmdset_storage", ",".join(str(val).strip() for val in make_iter(value)))
        _GA(self, "save")()

    #@cmdset_storage.deleter
    def cmdset_storage_del(self):
        "Deleter. Allows for del self.name"
        _SA(self, "db_cmdset_storage", None)
        _GA(self, "save")()
    cmdset_storage = property(cmdset_storage_get, cmdset_storage_set, cmdset_storage_del)

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

    #@property
    def __username_get(self):
        return _GA(self, "username")

    def __username_set(self, value):
        _SA(self, "username", value)

    def __username_del(self):
        _DA(self, "username")
    # aliases
    name = property(__username_get, __username_set, __username_del)
    key = property(__username_get, __username_set, __username_del)

    #@property
    def __uid_get(self):
        "Getter. Retrieves the user id"
        return self.id

    def __uid_set(self, value):
        raise Exception("User id cannot be set!")

    def __uid_del(self):
        raise Exception("User id cannot be deleted!")
    uid = property(__uid_get, __uid_set, __uid_del)

    #@property
    #def __is_superuser_get(self):
    #    "Superusers have all permissions."
    #    return self.db_is_superuser
    #    #is_suser = get_prop_cache(self, "_is_superuser")
    #    #if is_suser == None:
    #    #    is_suser = _GA(self, "user").is_superuser
    #    #    set_prop_cache(self, "_is_superuser", is_suser)
    #    #return is_suser
    #is_superuser = property(__is_superuser_get)

    #
    # PlayerDB class access methods
    #

    def msg(self, text=None, from_obj=None, sessid=None, **kwargs):
        """
        Evennia -> User
        This is the main route for sending data back to the user from the
        server.

        outgoing_string (string) - text data to send
        from_obj (Object/Player) - source object of message to send. Its
                 at_msg_send() hook will be called.
        sessid - the session id of the session to send to. If not given, return
                 to all sessions connected to this player. This is usually only
                 relevant when using msg() directly from a player-command (from
                 a command on a Character, the character automatically stores
                 and handles the sessid). Can also be a list of sessids.
        kwargs (dict) - All other keywords are parsed as extra data.
        """
        if "data" in kwargs:
            # deprecation warning
            logger.log_depmsg("PlayerDB:msg() 'data'-dict keyword is deprecated. Use **kwargs instead.")
            data = kwargs.pop("data")
            if isinstance(data, dict):
                kwargs.update(data)

        text = to_str(text, force_string=True) if text else ""
        if from_obj:
            # call hook
            try:
                _GA(from_obj, "at_msg_send")(text=text, to_obj=_GA(self, "typeclass"), **kwargs)
            except Exception:
                pass
        sessions = _MULTISESSION_MODE > 1 and sessid and _GA(self, "get_session")(sessid) or None
        if sessions:
            for session in make_iter(sessions):
                obj = session.puppet
                if obj and not obj.at_msg_receive(text=text, **kwargs):
                    # if hook returns false, cancel send
                    continue
                session.msg(text=text, **kwargs)
        else:
            # if no session was specified, send to them all
            for sess in _GA(self, 'get_all_sessions')():
                sess.msg(text=text, **kwargs)

    # session-related methods

    def get_session(self, sessid):
        """
        Return session with given sessid connected to this player.
        note that the sessionhandler also accepts sessid as an iterable.
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
    sessions = property(get_all_sessions)  # alias shortcut

    def disconnect_session_from_player(self, sessid):
        """
        Access method for disconnecting a given session from the player
        (connection happens automatically in the sessionhandler)
        """
        # this should only be one value, loop just to make sure to
        # clean everything
        sessions = (session for session in self.get_all_sessions()
                    if session.sessid == sessid)
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
        # if we get to this point the character is ready to puppet or it
        # was left with a lingering player/sessid reference from an unclean
        # server kill or similar

        if normal_mode:
            _GA(obj.typeclass, "at_pre_puppet")(_GA(self, "typeclass"), sessid=sessid)
        # do the connection
        obj.sessid.add(sessid)
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
        # do the disconnect, but only if we are the last session to puppet
        _GA(obj.typeclass, "at_pre_unpuppet")()
        obj.dbobj.sessid.remove(sessid)
        if not obj.dbobj.sessid.count():
            del obj.dbobj.player
            _GA(obj.typeclass, "at_post_unpuppet")(_GA(self, "typeclass"), sessid=sessid)
        session.puppet = None
        session.puid = None
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
        Get an object puppeted by this session through this player. This is
        the main method for retrieving the puppeted object from the
        player's end.

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
        puppets = [session.puppet for session in self.get_all_sessions()
                                                            if session.puppet]
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
    puppet = property(__get_single_puppet)

    # utility methods

    def delete(self, *args, **kwargs):
        """
        Deletes the player permanently.
        """
        for session in self.get_all_sessions():
            # unpuppeting all objects and disconnecting the user, if any
            # sessions remain (should usually be handled from the
            # deleting command)
            self.unpuppet_object(session.sessid)
            session.sessionhandler.disconnect(session, reason=_("Player being deleted."))
        self.scripts.stop()
        _GA(self, "attributes").clear()
        _GA(self, "nicks").clear()
        _GA(self, "aliases").clear()
        super(PlayerDB, self).delete(*args, **kwargs)

    def execute_cmd(self, raw_string, sessid=None):
        """
        Do something as this player. This method is never called normally,
        but only when the player object itself is supposed to execute the
        command. It takes player nicks into account, but not nicks of
        eventual puppets.

        raw_string - raw command input coming from the command line.
        """
        raw_string = utils.to_unicode(raw_string)
        raw_string = self.nicks.nickreplace(raw_string,
                          categories=("inputline", "channel"), include_player=False)
        if not sessid and _MULTISESSION_MODE in (0, 1):
            # in this case, we should either have only one sessid, or the sessid
            # should not matter (since the return goes to all of them we can
            # just use the first one as the source)
            try:
                sessid = self.get_all_sessions()[0].sessid
            except IndexError:
                # this can happen for bots
                sessid = None
        return cmdhandler.cmdhandler(self.typeclass, raw_string,
                                     callertype="player", sessid=sessid)

    def search(self, searchdata, return_puppet=False, **kwargs):
        """
        This is similar to the ObjectDB search method but will search for
        Players only. Errors will be echoed, and None returned if no Player
        is found.
        searchdata - search criterion, the Player's key or dbref to search for
        return_puppet  - will try to return the object the player controls
                           instead of the Player object itself. If no
                           puppeted object exists (since Player is OOC), None will
                           be returned.
        Extra keywords are ignored, but are allowed in call in order to make
                           API more consistent with objects.models.TypedObject.search.
        """
        #TODO deprecation
        if "return_character" in kwargs:
            logger.log_depmsg("Player.search's 'return_character' keyword is deprecated. Use the return_puppet keyword instead.")
            return_puppet = kwargs.get("return_character")

        matches = _GA(self, "__class__").objects.player_search(searchdata)
        matches = _AT_SEARCH_RESULT(_GA(self, "typeclass"), searchdata, matches, global_search=True)
        if matches and return_puppet:
            try:
                return _GA(matches, "puppet")
            except AttributeError:
                return None
        return matches

