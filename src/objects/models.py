"""
This module defines the database models for all in-game objects, that
is, all objects that has an actual existence in-game.

Each database object is 'decorated' with a 'typeclass', a normal
python class that implements all the various logics needed by the game
in question. Objects created of this class transparently communicate
with its related database object for storing all attributes. The
admin should usually not have to deal directly with this database
object layer.

Attributes are separate objects that store values persistently onto
the database object. Like everything else, they can be accessed
transparently through the decorating TypeClass.
"""

import traceback
from django.db import models
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from src.typeclasses.models import TypedObject, NickHandler
from src.objects.manager import ObjectManager
from src.players.models import PlayerDB
from src.commands.cmdsethandler import CmdSetHandler
from src.commands import cmdhandler
from src.scripts.scripthandler import ScriptHandler
from src.utils import logger
from src.utils.utils import (make_iter, to_str, to_unicode, lazy_property,
                             variable_from_module, dbref)

MULTISESSION_MODE = settings.MULTISESSION_MODE
from django.utils.translation import ugettext as _

#__all__ = ("ObjectDB", )

_ScriptDB = None
_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))
_SESSIONS = None

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

# the sessid_max is based on the length of the db_sessid csv field (excluding commas)
_SESSID_MAX = 16 if MULTISESSION_MODE in (1, 3) else 1

class SessidHandler(object):
    """
    Handles the get/setting of the sessid
    comma-separated integer field
    """
    def __init__(self, obj):
        self.obj = obj
        self._cache = set()
        self._recache()

    def _recache(self):
        self._cache = list(set(int(val) for val in (_GA(self.obj, "db_sessid") or "").split(",") if val))

    def get(self):
        "Returns a single integer or a list"
        return self._cache if _SESSID_MAX > 1 else self._cache[0] if self._cache else None

    def add(self, sessid):
        "Add sessid to handler"
        _cache = self._cache
        if sessid not in _cache:
            if len(_cache) >= _SESSID_MAX:
                return
            _cache.append(sessid)
            _SA(self.obj, "db_sessid", ",".join(str(val) for val in _cache))
            _GA(self.obj, "save")(update_fields=["db_sessid"])

    def remove(self, sessid):
        "Remove sessid from handler"
        _cache = self._cache
        if sessid in _cache:
            _cache.remove(sessid)
            _SA(self.obj, "db_sessid", ",".join(str(val) for val in _cache))
            _GA(self.obj, "save")(update_fields=["db_sessid"])

    def clear(self):
        "Clear sessids"
        self._cache = []
        _SA(self.obj, "db_sessid", None)
        _GA(self.obj, "save")(update_fields=["db_sessid"])

    def count(self):
        "Return amount of sessions connected"
        return len(self._cache)


#------------------------------------------------------------
#
# ObjectDB
#
#------------------------------------------------------------

class ObjectDB(TypedObject):
    """
    All objects in the game use the ObjectDB model to store
    data in the database. This is handled transparently through
    the typeclass system.

    Note that the base objectdb is very simple, with
    few defined fields. Use attributes to extend your
    type class with new database-stored variables.

    The TypedObject supplies the following (inherited) properties:
      key - main name
      name - alias for key
      typeclass_path - the path to the decorating typeclass
      typeclass - auto-linked typeclass
      date_created - time stamp of object creation
      permissions - perm strings
      locks - lock definitions (handler)
      dbref - #id of object
      db - persistent attribute storage
      ndb - non-persistent attribute storage

    The ObjectDB adds the following properties:
      player - optional connected player (always together with sessid)
      sessid - optional connection session id (always together with player)
      location - in-game location of object
      home - safety location for object (handler)

      scripts - scripts assigned to object (handler from typeclass)
      cmdset - active cmdset on object (handler from typeclass)
      aliases - aliases for this object (property)
      nicks - nicknames for *other* things in Evennia (handler)
      sessions - sessions connected to this object (see also player)
      has_player - bool if an active player is currently connected
      contents - other objects having this object as location
      exits - exits from this object
    """

    #
    # ObjectDB Database model setup
    #
    #
    # inherited fields (from TypedObject):
    # db_key (also 'name' works), db_typeclass_path, db_date_created,
    # db_permissions
    #
    # These databse fields (including the inherited ones) should normally be
    # managed by their corresponding wrapper properties, named same as the
    # field, but without the db_* prefix (e.g. the db_key field is set with
    # self.key instead). The wrappers are created at the metaclass level and
    # will automatically save and cache the data more efficiently.

    # If this is a character object, the player is connected here.
    db_player = models.ForeignKey("players.PlayerDB", null=True, verbose_name='player', on_delete=models.SET_NULL,
                                  help_text='a Player connected to this object, if any.')
    # the session id associated with this player, if any
    db_sessid = models.CommaSeparatedIntegerField(null=True, max_length=32, verbose_name="session id",
                                    help_text="csv list of session ids of connected Player, if any.")
    # The location in the game world. Since this one is likely
    # to change often, we set this with the 'location' property
    # to transparently handle Typeclassing.
    db_location = models.ForeignKey('self', related_name="locations_set", db_index=True, on_delete=models.SET_NULL,
                                     blank=True, null=True, verbose_name='game location')
    # a safety location, this usually don't change much.
    db_home = models.ForeignKey('self', related_name="homes_set", on_delete=models.SET_NULL,
                                 blank=True, null=True, verbose_name='home location')
    # destination of this object - primarily used by exits.
    db_destination = models.ForeignKey('self', related_name="destinations_set", db_index=True, on_delete=models.SET_NULL,
                                       blank=True, null=True, verbose_name='destination',
                                       help_text='a destination, used only by exit objects.')
    # database storage of persistant cmdsets.
    db_cmdset_storage = models.CharField('cmdset', max_length=255, null=True, blank=True,
                                         help_text="optional python path to a cmdset class.")

    # Database manager
    objects = ObjectManager()

    # caches for quick lookups of typeclass loading.
    _typeclass_paths = settings.OBJECT_TYPECLASS_PATHS
    _default_typeclass_path = settings.BASE_OBJECT_TYPECLASS or "src.objects.objects.Object"

    # lazy-load handlers
    @lazy_property
    def cmdset(self):
        return CmdSetHandler(self, True)

    @lazy_property
    def scripts(self):
        return ScriptHandler(self)

    @lazy_property
    def nicks(self):
        return NickHandler(self)

    @lazy_property
    def sessid(self):
        return SessidHandler(self)

    def _at_db_player_postsave(self):
        """
        This hook is called automatically after the player field is saved.
        """
        # we need to re-cache this for superusers to bypass.
        self.locks.cache_lock_bypass(self)

    # cmdset_storage property. We use a custom wrapper to manage this. This also
    # seems very sensitive to caching, so leaving it be for now. /Griatch
    #@property
    def __cmdset_storage_get(self):
        """
        Getter. Allows for value = self.name.
        Returns a list of cmdset_storage.
        """
        storage = _GA(self, "db_cmdset_storage")
        # we need to check so storage is not None
        return [path.strip() for path in storage.split(',')] if storage else []
    #@cmdset_storage.setter
    def __cmdset_storage_set(self, value):
        """
        Setter. Allows for self.name = value.
        Stores as a comma-separated string.
        """
        _SA(self, "db_cmdset_storage", ",".join(str(val).strip() for val in make_iter(value)))
        _GA(self, "save")()
    #@cmdset_storage.deleter
    def __cmdset_storage_del(self):
        "Deleter. Allows for del self.name"
        _SA(self, "db_cmdset_storage", None)
        _GA(self, "save")()
    cmdset_storage = property(__cmdset_storage_get, __cmdset_storage_set, __cmdset_storage_del)

    # location getsetter
    def __location_get(self):
        "Get location"
        loc = _GA(_GA(self, "dbobj"), "db_location")
        return _GA(loc, "typeclass") if loc else loc

    def __location_set(self, location):
        "Set location, checking for loops and allowing dbref"
        if isinstance(location, (basestring, int)):
            # allow setting of #dbref
            dbid = dbref(location, reqhash=False)
            if dbid:
                try:
                    location = ObjectDB.objects.get(id=dbid)
                except ObjectDoesNotExist:
                    # maybe it is just a name that happens to look like a dbid
                    pass
        try:
            def is_loc_loop(loc, depth=0):
                "Recursively traverse target location, trying to catch a loop."
                if depth > 10:
                    return
                elif loc == self:
                    raise RuntimeError
                elif loc == None:
                    raise RuntimeWarning
                return is_loc_loop(_GA(_GA(loc, "dbobj"), "db_location"), depth + 1)
            try:
                is_loc_loop(location)
            except RuntimeWarning:
                pass
            # actually set the field
            _SA(_GA(self, "dbobj"), "db_location", _GA(location, "dbobj") if location else location)
            _GA(_GA(self, "dbobj"), "save")(update_fields=["db_location"])
        except RuntimeError:
            errmsg = "Error: %s.location = %s creates a location loop." % (self.key, location)
            logger.log_errmsg(errmsg)
            raise RuntimeError(errmsg)
        except Exception, e:
            errmsg = "Error (%s): %s is not a valid location." % (str(e), location)
            logger.log_errmsg(errmsg)
            raise Exception(errmsg)

    def __location_del(self):
        "Cleanly delete the location reference"
        _SA(_GA(self, "dbobj"), "db_location", None)
        _GA(_GA(self, "dbobj"), "save")(upate_fields=["db_location"])
    location = property(__location_get, __location_set, __location_del)

    class Meta:
        "Define Django meta options"
        verbose_name = "Object"
        verbose_name_plural = "Objects"

    #
    # ObjectDB class access methods/properties
    #

    #@property
    def __sessions_get(self):
        """
        Retrieve sessions connected to this object.
        """
        # if the player is not connected, this will simply be an empty list.
        if _GA(self, "db_player"):
            return _GA(_GA(self, "db_player"), "get_all_sessions")()
        return []
    sessions = property(__sessions_get)

    #@property
    def __has_player_get(self):
        """
        Convenience function for checking if an active player is
        currently connected to this object
        """
        return any(_GA(self, "sessions"))
    has_player = property(__has_player_get)
    is_player = property(__has_player_get)

    #@property
    def __is_superuser_get(self):
        "Check if user has a player, and if so, if it is a superuser."
        return (_GA(self, "db_player") and _GA(_GA(self, "db_player"), "is_superuser")
                and not _GA(_GA(self, "db_player"), "attributes").get("_quell"))
    is_superuser = property(__is_superuser_get)

    # contents

    def contents_get(self, exclude=None):
        """
        Returns the contents of this object, i.e. all
        objects that has this object set as its location.
        This should be publically available.

        exclude is one or more objects to not return
        """
        if exclude:
            return ObjectDB.objects.get_contents(self, excludeobj=exclude)
        return ObjectDB.objects.get_contents(self)
    contents = property(contents_get)

    #@property
    def __exits_get(self):
        """
        Returns all exits from this object, i.e. all objects
        at this location having the property destination != None.
        """
        return [exi for exi in _GA(self, "contents")
                if exi.destination]
    exits = property(__exits_get)

    #
    # Main Search method
    #

    def search(self, searchdata,
               global_search=False,
               use_nicks=True,  # should this default to off?
               typeclass=None,
               location=None,
               attribute_name=None,
               quiet=False,
               exact=False):
        """
        Returns the typeclass of an Object matching a search string/condition

        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully. By default, only
        objects in self's current location or inventory is searched.
        Note: to find Players, use eg. ev.player_search.

        Inputs:

        searchdata (str or obj): Primary search criterion. Will be matched
                    against object.key (with object.aliases second) unless
                    the keyword attribute_name specifies otherwise.
                    Special strings:
                        #<num> - search by unique dbref. This is always
                                 a global search.
                        me,self - self-reference to this object
                        <num>-<string> - can be used to differentiate
                                         between multiple same-named matches
        global_search (bool): Search all objects globally. This is overruled
                              by "location" keyword.
        use_nicks (bool): Use nickname-replace (nicktype "object") on the
                          search string
        typeclass (str or Typeclass, or list of either): Limit search only
                   to Objects with this typeclass. May be a list of typeclasses
                   for a broader search.
        location (Object): Specify a location to search, if different from the
                     self's given location plus its contents. This can also
                     be a list of locations.
        attribute_name (str): Define which property to search. If set, no
                      key+alias search will be performed. This can be used to
                      search database fields (db_ will be automatically
                      appended), and if that fails, it will try to return
                      objects having Attributes with this name and value
                      equal to searchdata. A special use is to search for
                      "key" here if you want to do a key-search without
                      including aliases.
        quiet (bool) - don't display default error messages - return multiple
                      matches as a list and no matches as None. If not
                      set (default), will echo error messages and return None.
        exact (bool) - if unset (default) - prefers to match to beginning of
                      string rather than not matching at all. If set, requires
                      exact mathing of entire string.

        Returns:
            quiet=False (default):
                no match or multimatch:
                auto-echoes errors to self.msg, then returns None
                    (results are handled by settings.SEARCH_AT_RESULT
                               and settings.SEARCH_AT_MULTIMATCH_INPUT)
                match:
                    a unique object match
            quiet=True:
                no match or multimatch:
                    returns None or list of multi-matches
                match:
                    a unique object match

        """
        is_string = isinstance(searchdata, basestring)

        if use_nicks:
            # do nick-replacement on search
            searchdata = self.nicks.nickreplace(searchdata, categories=("object", "player"), include_player=True)

        candidates=None
        if(global_search or (is_string and searchdata.startswith("#") and
                    len(searchdata) > 1 and searchdata[1:].isdigit())):
            # only allow exact matching if searching the entire database
            # or unique #dbrefs
            exact = True
        elif location:
            # location(s) were given
            candidates = []
            for obj in make_iter(location):
                candidates.extend([o.dbobj for o in obj.contents])
        else:
            # local search. Candidates are self.contents, self.location
            # and self.location.contents
            location = self.location
            candidates = self.contents
            if location:
                candidates = candidates + [location] + location.contents
            else:
                # normally we are included in location.contents
                candidates.append(self)
            # db manager expects database objects
            candidates = [obj.dbobj for obj in candidates]

        results = ObjectDB.objects.object_search(searchdata,
                                                 attribute_name=attribute_name,
                                                 typeclass=typeclass,
                                                 candidates=candidates,
                                                 exact=exact)
        if quiet:
            return results
        return  _AT_SEARCH_RESULT(self, searchdata, results, global_search)

    def search_player(self, searchdata, quiet=False):
        """
        Simple shortcut wrapper to search for players, not characters.

        searchdata - search criterion - the key or dbref of the player
                     to search for. If this is "here" or "me", search
                     for the player connected to this object.
        quiet - return the results as a list rather than echo eventual
                standard error messages.

        Returns:
            quiet=False (default):
                no match or multimatch:
                    auto-echoes errors to self.msg, then returns None
                    (results are handled by settings.SEARCH_AT_RESULT
                                 and settings.SEARCH_AT_MULTIMATCH_INPUT)
                match:
                    a unique player match
            quiet=True:
                no match or multimatch:
                    returns None or list of multi-matches
                match:
                    a unique object match
        """
        results = PlayerDB.objects.player_search(searchdata)
        if quiet:
            return results
        return _AT_SEARCH_RESULT(self, searchdata, results, global_search=True)

    #
    # Execution/action methods
    #

    def execute_cmd(self, raw_string, sessid=None):
        """
        Do something as this object. This method is a copy of the execute_
        cmd method on the session. This is never called normally, it's only
        used when wanting specifically to let an object be the caller of a
        command. It makes use of nicks of eventual connected players as well.

        Argument:
        raw_string (string) - raw command input
        sessid (int) - optional session id to return results to

        Returns Deferred - this is an asynchronous Twisted object that will
            not fire until the command has actually finished executing. To
            overload this one needs to attach callback functions to it, with
            addCallback(function). This function will be called with an
            eventual return value from the command execution.

            This return is not used at all by Evennia by default, but might
            be useful for coders intending to implement some sort of nested
            command structure.
        """
        # nick replacement - we require full-word matching.

        # do text encoding conversion
        raw_string = to_unicode(raw_string)
        raw_string = self.nicks.nickreplace(raw_string,
                     categories=("inputline", "channel"), include_player=True)
        return cmdhandler.cmdhandler(_GA(self, "typeclass"), raw_string, callertype="object", sessid=sessid)

    def msg(self, text=None, from_obj=None, sessid=0, **kwargs):
        """
        Emits something to a session attached to the object.

        message (str): The message to send
        from_obj (obj): object that is sending.
        data (object): an optional data object that may or may not
                       be used by the protocol.
        sessid (int): sessid to relay to, if any.
                      If set to 0 (default), use either from_obj.sessid (if set) or self.sessid automatically
                      If None, echo to all connected sessions

        When this message is called, from_obj.at_msg_send and self.at_msg_receive are called.

        """
        global _SESSIONS
        if not _SESSIONS:
            from src.server.sessionhandler import SESSIONS as _SESSIONS

        text = to_str(text, force_string=True) if text else ""

        if "data" in kwargs:
            # deprecation warning
            logger.log_depmsg("ObjectDB.msg(): 'data'-dict keyword is deprecated. Use **kwargs instead.")
            data = kwargs.pop("data")
            if isinstance(data, dict):
                kwargs.update(data)

        if from_obj:
            # call hook
            try:
                _GA(from_obj, "at_msg_send")(text=text, to_obj=_GA(self, "typeclass"), **kwargs)
            except Exception:
                logger.log_trace()
        try:
            if not _GA(_GA(self, "typeclass"), "at_msg_receive")(text=text, **kwargs):
                # if at_msg_receive returns false, we abort message to this object
                return
        except Exception:
            logger.log_trace()

        sessions = _SESSIONS.session_from_sessid([sessid] if sessid else make_iter(_GA(self, "sessid").get()))
        for session in sessions:
            session.msg(text=text, **kwargs)

    def msg_contents(self, message, exclude=None, from_obj=None, **kwargs):
        """
        Emits something to all objects inside an object.

        exclude is a list of objects not to send to. See self.msg() for
                more info.
        """
        contents = _GA(self, "contents")
        if exclude:
            exclude = make_iter(exclude)
            contents = [obj for obj in contents if obj not in exclude]
        for obj in contents:
            obj.msg(message, from_obj=from_obj, **kwargs)

    def move_to(self, destination, quiet=False,
                emit_to_obj=None, use_destination=True, to_none=False):
        """
        Moves this object to a new location.

        Moves this object to a new location. Note that if <destination> is an
        exit object (i.e. it has "destination"!=None), the move_to will
        happen to this destination and -not- into the exit object itself, unless
        use_destination=False. Note that no lock checks are done by this
        function, such things are assumed to have been handled before calling
        move_to.

        destination: (Object) Reference to the object to move to. This
                     can also be an exit object, in which case the destination
                     property is used as destination.
        quiet:  (bool)    If true, don't emit left/arrived messages.
        emit_to_obj: (Object) object to receive error messages
        use_destination (bool): Default is for objects to use the "destination"
                             property of destinations as the target to move to.
                             Turning off this keyword allows objects to move
                             "inside" exit objects.
        to_none - allow destination to be None. Note that no hooks are run when
                     moving to a None location. If you want to run hooks,
                     run them manually (and make sure they can manage None
                     locations).

        Returns True/False depending on if there were problems with the move.
                This method may also return various error messages to the
                emit_to_obj.
        """
        def logerr(string=""):
            trc = traceback.format_exc()
            errstring = "%s%s" % (trc, string)
            logger.log_trace()
            _GA(self, "msg")(errstring)

        errtxt = _("Couldn't perform move ('%s'). Contact an admin.")
        if not emit_to_obj:
            emit_to_obj = self

        if not destination:
            if to_none:
                # immediately move to None. There can be no hooks called since
                # there is no destination to call them with.
                self.location = None
                return True
            emit_to_obj.msg(_("The destination doesn't exist."))
            return
        if destination.destination and use_destination:
            # traverse exits
            destination = destination.destination

        # Before the move, call eventual pre-commands.
        try:
            if not self.at_before_move(_GA(destination, "typeclass")):
                return
        except Exception:
            logerr(errtxt % "at_before_move()")
            #emit_to_obj.msg(errtxt % "at_before_move()")
            #logger.log_trace()
            return False

        # Save the old location
        source_location = _GA(self, "location")
        if not source_location:
            # there was some error in placing this room.
            # we have to set one or we won't be able to continue
            if _GA(self, "home"):
                source_location = _GA(self, "home")
            else:
                default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
                source_location = default_home

        # Call hook on source location
        try:
            source_location.at_object_leave(_GA(self, "typeclass"), _GA(destination, "typeclass"))
        except Exception:
            logerr(errtxt % "at_object_leave()")
            #emit_to_obj.msg(errtxt % "at_object_leave()")
            #logger.log_trace()
            return False

        if not quiet:
            #tell the old room we are leaving
            try:
                self.announce_move_from(_GA(destination, "typeclass"))
            except Exception:
                logerr(errtxt % "at_announce_move()")
                #emit_to_obj.msg(errtxt % "at_announce_move()" )
                #logger.log_trace()
                return False

        # Perform move
        try:
            #print "move_to location:", destination
            _SA(self, "location", destination)
        except Exception:
            emit_to_obj.msg(errtxt % "location change")
            logger.log_trace()
            return False

        if not quiet:
            # Tell the new room we are there.
            try:
                self.announce_move_to(_GA(source_location, "typeclass"))
            except Exception:
                logerr(errtxt % "announce_move_to()")
                #emit_to_obj.msg(errtxt % "announce_move_to()")
                #logger.log_trace()
                return  False

        # Perform eventual extra commands on the receiving location
        # (the object has already arrived at this point)
        try:
            destination.at_object_receive(_GA(self, "typeclass"), _GA(source_location, "typeclass"))
        except Exception:
            logerr(errtxt % "at_object_receive()")
            #emit_to_obj.msg(errtxt % "at_object_receive()")
            #logger.log_trace()
            return False

        # Execute eventual extra commands on this object after moving it
        # (usually calling 'look')
        try:
            self.at_after_move(_GA(source_location, "typeclass"))
        except Exception:
            logerr(errtxt % "at_after_move")
            #emit_to_obj.msg(errtxt % "at_after_move()")
            #logger.log_trace()
            return False
        return True

    #
    # Object Swap, Delete and Cleanup methods
    #

    def clear_exits(self):
        """
        Destroys all of the exits and any exits pointing to this
        object as a destination.
        """
        for out_exit in [exi for exi in ObjectDB.objects.get_contents(self) if exi.db_destination]:
            out_exit.delete()
        for in_exit in ObjectDB.objects.filter(db_destination=self):
            in_exit.delete()

    def clear_contents(self):
        """
        Moves all objects (players/things) to their home
        location or to default home.
        """
        # Gather up everything that thinks this is its location.
        objs = ObjectDB.objects.filter(db_location=self)
        default_home_id = int(settings.DEFAULT_HOME.lstrip("#"))
        try:
            default_home = ObjectDB.objects.get(id=default_home_id)
            if default_home.dbid == _GA(self, "dbid"):
                # we are deleting default home!
                default_home = None
        except Exception:
            string = _("Could not find default home '(#%d)'.")
            logger.log_errmsg(string % default_home_id)
            default_home = None

        for obj in objs:
            home = obj.home
            # Obviously, we can't send it back to here.
            if not home or (home and home.dbid == _GA(self, "dbid")):
                obj.home = default_home
                home = default_home

            # If for some reason it's still None...
            if not home:
                string = "Missing default home, '%s(#%d)' "
                string += "now has a null location."
                obj.location = None
                obj.msg(_("Something went wrong! You are dumped into nowhere. Contact an admin."))
                logger.log_errmsg(string % (obj.name, obj.dbid))
                return

            if obj.has_player:
                if home:
                    string = "Your current location has ceased to exist,"
                    string += " moving you to %s(#%d)."
                    obj.msg(_(string) % (home.name, home.dbid))
                else:
                    # Famous last words: The player should never see this.
                    string = "This place should not exist ... contact an admin."
                    obj.msg(_(string))
            obj.move_to(home)

    def copy(self, new_key=None):
        """
        Makes an identical copy of this object. If you want to customize the
        copy by changing some settings, use ObjectDB.object.copy_object()
        directly.

        new_key (string) - new key/name of copied object. If new_key is not
                            specified, the copy will be named <old_key>_copy
                            by default.
        Returns: Object (copy of this one)
        """
        def find_clone_key():
            """
            Append 01, 02 etc to obj.key. Checks next higher number in the
            same location, then adds the next number available

            returns the new clone name on the form keyXX
            """
            key = _GA(self, "key")
            num = 1
            for obj in (obj for obj in self.location.contents
                        if obj.key.startswith(key) and
                            obj.key.lstrip(key).isdigit()):
                num += 1
            return "%s%03i" % (key, num)
        new_key = new_key or find_clone_key()
        return ObjectDB.objects.copy_object(self, new_key=new_key)

    delete_iter = 0
    def delete(self):
        """
        Deletes this object.
        Before deletion, this method makes sure to move all contained
        objects to their respective home locations, as well as clean
        up all exits to/from the object.
        """
        global _ScriptDB
        if not _ScriptDB:
            from src.scripts.models import ScriptDB as _ScriptDB

        if _GA(self, "delete_iter") > 0:
            # make sure to only call delete once on this object
            # (avoid recursive loops)
            return False

        if not self.at_object_delete():
            # this is an extra pre-check
            # run before deletion mechanism
            # is kicked into gear.
            _SA(self, "delete_iter", 0)
            return False

        self.delete_iter += 1

        # See if we need to kick the player off.

        for session in _GA(self, "sessions"):
            session.msg(_("Your character %s has been destroyed.") % _GA(self, "key"))
            # no need to disconnect, Player just jumps to OOC mode.
        # sever the connection (important!)
        if _GA(self, 'player'):
            _SA(_GA(self, "player"), "character", None)
        _SA(self, "player", None)

        for script in _ScriptDB.objects.get_all_scripts_on_obj(self):
            script.stop()
        #for script in _GA(self, "scripts").all():
        #    script.stop()

        # if self.player:
        #     self.player.user.is_active = False
        #     self.player.user.save(

        # Destroy any exits to and from this room, if any
        _GA(self, "clear_exits")()
        # Clear out any non-exit objects located within the object
        _GA(self, "clear_contents")()
        _GA(self, "attributes").clear()
        _GA(self, "nicks").clear()
        _GA(self, "aliases").clear()

        # Perform the deletion of the object
        super(ObjectDB, self).delete()
        return True
