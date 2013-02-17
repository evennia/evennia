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
    db_objs = models.ManyToManyField("objects.ObjectDB", null=True,
                                     verbose_name="characters", related_name="objs_set",
                                     help_text="In-game objects.")
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
    def objs_get(self):
        "Getter. Allows for value = self.obj"
        return self.db_objs.all()
        #return get_field_cache(self, "objs").all()
    #@obj.setter
    def objs_set(self, value):
        "Setter. Allows for self.obj = value"
        global _TYPECLASS
        if not _TYPECLASS:
            from src.typeclasses.typeclass import TypeClass as _TYPECLASS

        if isinstance(value, _TYPECLASS):
            value = value.dbobj
        try:
            self.db_objs.add(value)
            self.save()
            #set_field_cache(self, "obj", value)
        except Exception:
            logger.log_trace()
            raise Exception("Cannot assign %s as a player object!" % value)
    #@obj.deleter
    def objs_del(self):
        "Deleter. Allows for del self.obj"
        self.db_objs.clear()
        self.save()
        #del_field_cache(self, "obj")
    objs = property(objs_get, objs_set, objs_del)

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

        session = None
        if sessid:
            session = _GA(self, "get_session")(sessid)
        if session:
            char = _GA(self, "get_character")(sessid=sessid)
            if char and not char.at_msg_receive(outgoing_string, from_obj=from_obj, data=data):
                # if hook returns false, cancel send
                return
            session.msg(outgoing_string, data)
        else:
            # if no session was specified, send to them all
            for sess in _GA(self, 'get_all_sessions')():
                sess.msg(outgoing_string, data)

    def inmsg(self, ingoing_string, sessid):
        """
        User -> Evennia
        This is the reverse of msg - used by sessions to relay
        messages/data back into the game. It is normally not called
        from inside game code but only by the serversessions directly.

        ingoing_string - text string (i.e. command string)
        data - dictionary of optional data
        session - session sending this data
        """
        character = _GA(self, "get_character")(sessid=sessid)
        if character:
            # execute command on character
            _GA(character, "execute_cmd")(ingoing_string, sessid=sessid)
        else:
            # a non-character session; this goes to player directly
            _GA(self, "execute_cmd")(ingoing_string, sessid=sessid)

    def disconnect_session_from_player(self, sessid):
        """
        Access method for disconnecting a given session from the player.
        """
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        _SESSIONS.disconnect(sessid=sessid)



    def connect_session_to_character(self, sessid, character, force=False):
        """
        Connect the given session to a character through this player.
        Note that this assumes the character has previously been
        linked to the player using self.connect_character().

        force - drop existing connection to other character

        Returns True if connection was successful, False otherwise
        """
        # first check if we already have a character tied to this session
        char = _GA(self, "get_character")(sessid=sessid, return_dbobj=True)
        if char:
            if force and char != character:
                _GA(self, "disconnect_session_from_character")(sessid)
            else:
                return
        # do the connection
        character.sessid = sessid
        # update cache
        cache = get_prop_cache(self, "_characters") or {}
        cache[sessid] = character
        set_prop_cache(self, "_characters", cache)
        # call hooks
        character.at_init()
        if character:
            # start (persistent) scripts on this object
            #ScriptDB.objects.validate(obj=character)
            pass
        if character.db.FIRST_LOGIN:
            character.at_first_login()
            del character.db.FIRST_LOGIN
        character.at_pre_login()
        character.at_post_login()
        return True

    def disconnect_session_from_character(self, sessid):
        """
        Disconnect a session from the characterm (still keeping the
        connection to the Player)
        returns the newly disconnected character, if it existed
        """
        if not sessid:
            return
        char = _GA(self, "get_character")(sessid=sessid, return_dbobj=True)
        if char:
            # call hook before disconnecting
            _GA(char.typeclass, "at_disconnect")()
            del char.sessid
            # update cache
            cache = get_prop_cache(self, "_characters") or {}
            if sessid in cache:
                del cache[sessid]
            set_prop_cache(self, "_characters", cache)
        return char

    def reconnect_session_to_character(self, sessid):
        """
        Auto-re-connect a session to a character. This is called by the sessionhandler
        during a server reload. It goes through the characters stored in this player's
        db_objs many2many fields and checks if any of those has the given sessid
        stored on themselves - if so they connect them. This should ONLY be called
        automatically by sessionhandler after a reload - after a portal shutdown
        the portal sessids will be out of sync with whatever is stored on character
        objects which could lead to a session being linked to the wrong character.
        """
        char = _GA(self, "get_character")(sessid=sessid, return_dbobj=True)
        if not char:
            print "No reconnecting character found"
            return
        self.connect_session_to_character(sessid, char, force=True)

    def get_session(self, sessid):
        """
        Return session with given sessid connected to this player.
        """
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        return _SESSIONS.sessions_from_player(self, sessid=sessid)

    def get_all_sessions(self):
        "Return all sessions connected to this player"
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS
        return _SESSIONS.sessions_from_player(self)

    def get_character(self, sessid=None, character=None, return_dbobj=False):
        """
        Get the character connected to this player and sessid

        sessid - return character connected to this sessid,
        character - return character if connected to this player, else None.

        Combining both keywords will check the entire connection - if the
        given session is currently connected to the given char. If no
        keywords are given, returns all connected characters.
        """
        cache = get_prop_cache(self, "_characters") or {}
        if sessid:
            # try to return a character with a given sessid
            char = cache.get(sessid)
            if not char:
                char = _GA(self, "db_objs").filter(db_player=self, db_sessid=sessid) or None
                if char:
                    char = char[0]
                    cache[sessid] = char
                    set_prop_cache(self, "_characters", cache)
            if character:
                return char and (char == character.dbobj and (return_dbobj and char or char.typeclass)) or None
            return char and (return_dbobj and char or char.typeclass) or None
        elif character:
            char = _GA(self, "db_objs").filter(id=_GA(character.dbobj, "id"))
            return char and (return_dbobj and char[0] or char[0].typeclass) or None
        else:
            # no sessid given - return all available characters
            return list(return_dbobj and o or o.typeclass for o in self.db_objs.all())

    def get_all_characters(self):
        """
        Readability-wrapper for getting all characters
        """
        return _GA(self, "get_character")(sessid=None, character=None)

    def connect_character(self, character, sessid=None):
        """
        Use the Player to connect a Character to a session. Note that
        we don't do any access checks at this point. Note that if the
        game was fully restarted (including the Portal), this must be
        used, since sessids will have changed as players reconnect.

        if sessid is given, also connect the sessid to the character.
        """
        # first disconnect any other character from this session
        char = character.dbobj
        _GA(self, "disconnect_character")(char)
        char.player = self
        _GA(self, "db_objs").add(char)
        _GA(self, "save")()
        if sessid:
            return _GA(self, "connect_session_to_character")(sessid=sessid, character=char)
        return True

    def disconnect_character(self, character):
        """
        Disconnect a character from this player, either based
        on sessid or by giving the character object directly

        Returns newly disconnected character.
        """
        if not character:
            return
        char = _GA(self, "get_character")(character=character, return_dbobj=True)
        if char:
            err = _GA(self, "disconnect_session_from_character")(char.sessid)
            _GA(self, "db_objs").remove(char)
            del char.player
            self.save()
            # clear cache
            cache = get_prop_cache(self, "_characters") or {}
            [cache.pop(sessid) for sessid,stored_char in cache.items() if stored_char==char]
            set_prop_cache(self, "_characters", cache)
        return char


    def disconnect_all_characters(self):
        for char in self.db_objs.all():
            _GA(self, "disconnect_character")(char)

    def swap_character(self, old_character, new_character):
        """
        Swaps character between sessions, if possible
        """
        this_sessid = old_character.sessid
        other_sessd = new_character.sessid
        this_char = _GA(self, "disconnect_session_from_character")(this_sessid)
        other_char = _GA(self, "disconnect_session_from_character")(other_sessid)
        _GA(self, "connect_session_to_character")(this_sessid, other_char)
        _GA(self, "connect_session_to_character")(other_sessid, this_char)

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
        matches = _GA(self, "__class__").objects.player_search(ostring)
        matches = _AT_SEARCH_RESULT(self, ostring, matches, global_search=True)
        if matches and return_character:
            try:
                return _GA(matches, "character")
            except:
                pass
        return matches
