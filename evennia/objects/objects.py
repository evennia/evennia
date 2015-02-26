"""
This is the basis of the typeclass system.

The idea is have the object as a normal class with the
database-connection tied to itself through a property.

The instances of all the different object types are all tied to their
own database object stored in the 'dbobj' property.  All attribute
get/set operations are channeled transparently to the database object
as desired. You should normally never have to worry about the database
abstraction, just do everything on the TypeClass object.

That an object is controlled by a player/user is just defined by its
'user' property being set.  This means a user may switch which object
they control by simply linking to a new object's user property.
"""

import traceback
from django.conf import settings

from evennia.typeclasses.models import TypeclassBase
from evennia.typeclasses.attributes import NickHandler
from evennia.objects.manager import ObjectManager
from evennia.objects.models import ObjectDB
from evennia.scripts.scripthandler import ScriptHandler
from evennia.commands import cmdset, command
from evennia.commands.cmdsethandler import CmdSetHandler
from evennia.commands import cmdhandler
from evennia.utils.logger import log_depmsg, log_trace, log_errmsg
from evennia.utils.utils import (variable_from_module, lazy_property,
                             make_iter, to_str, to_unicode)

MULTISESSION_MODE = settings.MULTISESSION_MODE

_ScriptDB = None
_SESSIONS = None

_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))
# the sessid_max is based on the length of the db_sessid csv field (excluding commas)
_SESSID_MAX = 16 if MULTISESSION_MODE in (1, 3) else 1

from django.utils.translation import ugettext as _

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
        self._cache = list(set(int(val) for val in (self.obj.db_sessid or "").split(",") if val))

    def get(self):
        "Returns a list of one or more session ids"
        return self._cache
    all = get # alias

    def add(self, sessid):
        "Add sessid to handler"
        _cache = self._cache
        if sessid not in _cache:
            if len(_cache) >= _SESSID_MAX:
                return
            _cache.append(sessid)
            self.obj.db_sessid = ",".join(str(val) for val in _cache)
            self.obj.save(update_fields=["db_sessid"])

    def remove(self, sessid):
        "Remove sessid from handler"
        _cache = self._cache
        if sessid in _cache:
            _cache.remove(sessid)
            self.obj.db_sessid =  ",".join(str(val) for val in _cache)
            self.obj.save(update_fields=["db_sessid"])

    def clear(self):
        "Clear sessids"
        self._cache = []
        self.obj.db_sessid = None
        self.obj.save(update_fields=["db_sessid"])

    def count(self):
        "Return amount of sessions connected"
        return len(self._cache)



#
# Base class to inherit from.
#

class DefaultObject(ObjectDB):
    """
    This is the root typeclass object, representing all entities
    that have an actual presence in-game. Objects generally have a
    location. They can also be manipulated and looked at. Most
    game entities you define should inherit from Object at some distance.
    Evennia defines some important subclasses of Object by default, namely
    Characters, Exits and Rooms (see the bottom of this module).

    Note that all new Objects and their subclasses *must* always be
    created using the evennia.create_object() function. This is so the
    typeclass system can be correctly initiated behind the scenes.


    Object Typeclass API:

    * Available properties (only available on *initiated* typeclass objects)

     key (string) - name of object
     name (string) - same as key
     aliases (list of strings) - aliases to the object. Will be saved to
                 database as AliasDB entries but returned as strings.
     dbref (int, read-only) - unique #id-number. Also "id" can be used.
     date_created (string) - time stamp of object creation
     permissions (list of strings) - list of permission strings

     player (Player) - controlling player (if any, only set together with
                      sessid below)
     sessid (int, read-only) - session id (if any, only set together with
                      player above)
     location (Object) - current location. Is None if this is a room
     home (Object) - safety start-location
     sessions (list of Sessions, read-only) - returns all sessions
                 connected to this object
     has_player (bool, read-only)- will only return *connected* players
     contents (list of Objects, read-only) - returns all objects inside
                     this object (including exits)
     exits (list of Objects, read-only) - returns all exits from this
                 object, if any
     destination (Object) - only set if this object is an exit.
     is_superuser (bool, read-only) - True/False if this user is a superuser

    * Handlers available

     locks - lock-handler: use locks.add() to add new lock strings
     db - attribute-handler: store/retrieve database attributes on this
                             self.db.myattr=val, val=self.db.myattr
     ndb - non-persistent attribute handler: same as db but does not
                             create a database entry when storing data
     scripts - script-handler. Add new scripts to object with scripts.add()
     cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
     nicks - nick-handler. New nicks with nicks.add().

    * Helper methods (see evennia.objects.objects.py for full headers)

     search(ostring, global_search=False, use_nicks=True,
            typeclass=None,
            attribute_name=None, use_nicks=True, location=None,
            quiet=False, exact=False)
     execute_cmd(raw_string)
     msg(text=None, from_obj=None, sessid=0, **kwargs)
     msg_contents(message, exclude=None, from_obj=None, **kwargs)
     move_to(destination, quiet=False, emit_to_obj=None,
             use_destination=True, to_none=False)
     copy(new_key=None)
     delete()
     is_typeclass(typeclass, exact=False)
     swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
     access(accessing_obj, access_type='read', default=False)
     check_permstring(permstring)

    * Hook methods

     basetype_setup()     - only called once, used for behind-the-scenes
                            setup. Normally not modified.
     basetype_posthook_setup() - customization in basetype, after the
                             object has been created; Normally not modified.

     at_object_creation() - only called once, when object is first created.
                            Object customizations go here.
     at_object_delete() - called just before deleting an object. If
                          returning False, deletion is aborted. Note that
                          all objects inside a deleted object are
                          automatically moved to their <home>, they don't
                          need to be removed here.

     at_init()            called whenever typeclass is cached from
                          memory, at least once every server restart/reload
     at_cmdset_get(**kwargs) - this is called just before the command
                            handler requests a cmdset from this object, usually
                            without any kwargs
     at_pre_puppet(player)- (player-controlled objects only) called just
                             before puppeting
     at_post_puppet()     - (player-controlled objects only) called just
                             after completing connection player<->object
     at_pre_unpuppet()    - (player-controlled objects only) called just
                             before un-puppeting
     at_post_unpuppet(player) (player-controlled objects only) called
                              just after disconnecting player<->object link
     at_server_reload()   - called before server is reloaded
     at_server_shutdown() - called just before server is fully shut down

     at_before_move(destination)    called just before moving
                                    object to the destination. If returns
                                    False, move is cancelled.
     announce_move_from(destination)  - called in old location, just before
                                        move, if obj.move_to() has
                                        quiet=False
     announce_move_to(source_location) - called in new location,
                                         just after move, if obj.move_to()
                                         has quiet=False
     at_after_move(source_location)    - always called after a move
                                         has been successfully performed.
     at_object_leave(obj, target_location)   - called when an object leaves
                                               this object in any fashion
     at_object_receive(obj, source_location) - called when this object
                                               receives another object
     at_access(result, **kwargs) - this is called with the result of an
                                   access call, along with any kwargs used
                                   for that call. The return of this
                                   method does not affect the result of the
                                   lock check.
     at_before_traverse(traversing_object) - (exit-objects only) called
                                              just before an object
                                              traverses this object
     at_after_traverse(traversing_object, source_location) - (exit-objects
                          only) called just after a traversal has happened.
     at_failed_traverse(traversing_object)      - (exit-objects only) called
                if traversal fails and property err_traverse is not defined.

     at_msg_receive(self, msg, from_obj=None, data=None) - called when a
                             message (via self.msg()) is sent to this obj.
                             If returns false, aborts send.
     at_msg_send(self, msg, to_obj=None, data=None) - called when this
                         objects sends a message to someone via self.msg().

     return_appearance(looker) - describes this object. Used by "look"
                                 command by default
     at_desc(looker=None)      - called by 'look' whenever the appearance
                                 is requested.
     at_get(getter)            - called after object has been picked up.
                                 Does not stop pickup.
     at_drop(dropper)          - called when this object has been dropped.
     at_say(speaker, message)  - by default, called if an object inside
                                 this object speaks

     """
    # typeclass setup
    __metaclass__ = TypeclassBase
    objects = ObjectManager()

    # on-object properties

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

    @property
    def sessions(self):
        """
        Retrieve sessions connected to this object.
        """
        # if the player is not connected, this will simply be an empty list.
        if self.db_player:
            return self.db_player.get_all_sessions()
        return []

    @property
    def has_player(self):
        """
        Convenience function for checking if an active player is
        currently connected to this object
        """
        return any(self.sessions)

    @property
    def is_superuser(self):
        "Check if user has a player, and if so, if it is a superuser."
        return self.db_player and self.db_player.is_superuser \
                and not self.db_player.attributes.get("_quell")

    def contents_get(self, exclude=None):
        """
        Returns the contents of this object, i.e. all
        objects that has this object set as its location.
        This should be publically available.

        exclude is one or more objects to not return
        """
        return ObjectDB.objects.get_contents(self, excludeobj=exclude)
    contents = property(contents_get)


    @property
    def exits(self):
        """
        Returns all exits from this object, i.e. all objects
        at this location having the property destination != None.
        """
        return [exi for exi in self.contents if exi.destination]

    # main methods

    ## methods inherited from the database object (overload them here)

    def search(self, searchdata,
               global_search=False,
               use_nicks=True,  # should this default to off?
               typeclass=None,
               location=None,
               attribute_name=None,
               quiet=False,
               exact=False,
               candidates=None,
               nofound_string=None,
               multimatch_string=None):
        """
        Returns the typeclass of an Object matching a search string/condition

        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully. By default, only
        objects in self's current location or inventory is searched.
        Note: to find Players, use eg. evennia.player_search.

        Args:
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
            quiet (bool): don't display default error messages - this tells the
                          search method that the user wants to handle all errors
                          themselves. It also changes the return value type, see
                          below.
            exact (bool): if unset (default) - prefers to match to beginning of
                          string rather than not matching at all. If set, requires
                          exact mathing of entire string.
            candidates (list of objects): this is an optional custom list of objects
                        to search (filter) between. It is ignored if global_search
                        is given. If not set, this list will automatically be defined
                        to include the location, the contents of location and the
                        caller's contents (inventory).
            nofound_string (str):  optional custom string for not-found error message
            multimatch_string (str): optional custom string for multimatch error header

        Returns:
            match (Object, None or list): will return an Object/None if quiet=False,
                otherwise it will return a list of 0, 1 or more matches.

        Notes:
            If quiet=False, error messages will be handled by settings.SEARCH_AT_RESULT
            and echoed automatically (on error, return will be None). If quiet=True, the
            error messaging is assumed to be handled by the caller.

        """
        is_string = isinstance(searchdata, basestring)

        if is_string:
            # searchdata is a string; wrap some common self-references
            if searchdata.lower() in ("here", ):
                return [self.location] if quiet else self.location
            if searchdata.lower() in ("me", "self",):
                return [self] if quiet else self

        if use_nicks:
            # do nick-replacement on search
            searchdata = self.nicks.nickreplace(searchdata, categories=("object", "player"), include_player=True)

        if(global_search or (is_string and searchdata.startswith("#") and
                    len(searchdata) > 1 and searchdata[1:].isdigit())):
            # only allow exact matching if searching the entire database
            # or unique #dbrefs
            exact = True
        elif not candidates:
            # no custom candidates given - get them automatically
            if location:
                # location(s) were given
                candidates = []
                for obj in make_iter(location):
                    candidates.extend(obj.contents)
            else:
                # local search. Candidates are taken from
                # self.contents, self.location and
                # self.location.contents
                location = self.location
                candidates = self.contents
                if location:
                    candidates = candidates + [location] + location.contents
                else:
                    # normally we don't need this since we are
                    # included in location.contents
                    candidates.append(self)

        results = ObjectDB.objects.object_search(searchdata,
                                                 attribute_name=attribute_name,
                                                 typeclass=typeclass,
                                                 candidates=candidates,
                                                 exact=exact)
        if quiet:
            return results
        return  _AT_SEARCH_RESULT(self, searchdata, results, global_search, nofound_string, multimatch_string)

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
        if isinstance(searchdata, basestring):
            # searchdata is a string; wrap some common self-references
            if searchdata.lower() in ("me", "self",):
                return self.player

        results = self.player.__class__.objects.player_search(searchdata)

        if quiet:
            return results
        return _AT_SEARCH_RESULT(self, searchdata, results, global_search=True)

    def execute_cmd(self, raw_string, sessid=None, **kwargs):
        """
        Do something as this object. This method is a copy of the execute_
        cmd method on the session. This is never called normally, it's only
        used when wanting specifically to let an object be the caller of a
        command. It makes use of nicks of eventual connected players as well.

        Argument:
        raw_string (string) - raw command input
        sessid (int) - optional session id to return results to
        **kwargs - other keyword arguments will be added to the found command
                   object instace as variables before it executes. This is
                   unused by default Evennia but may be used to set flags and
                   change operating paramaters for commands at run-time.

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
        return cmdhandler.cmdhandler(self, raw_string, callertype="object", sessid=sessid, **kwargs)


    def msg(self, text=None, from_obj=None, sessid=0, **kwargs):
        """
        Emits something to a session attached to the object.

        Args:
            text (str, optional): The message to send
            from_obj (obj, optional): object that is sending. If
                given, at_msg_send will be called
            sessid (int or list, optional): sessid or list of
                sessids to relay to, if any. If set, will
                force send regardless of MULTISESSION_MODE.
        Notes:
            `at_msg_receive` will be called on this Object.
            All extra kwargs will be passed on to the protocol.

        """
        text = to_str(text, force_string=True) if text else ""
        if from_obj:
            # call hook
            try:
                from_obj.at_msg_send(text=text, to_obj=self, **kwargs)
            except Exception:
                log_trace()
        try:
            if not self.at_msg_receive(text=text, **kwargs):
                # if at_msg_receive returns false, we abort message to this object
                return
        except Exception:
            log_trace()

        # session relay

        if self.player:
            # for there to be a session there must be a Player.
            if sessid:
                # this could still be an iterable if sessid is.
                sessions = self.player.get_session(sessid)
                if sessions:
                    # this is a special instruction to ignore MULTISESSION_MODE
                    # and only relay to this given session.
                    kwargs["_nomulti"] = True
                    for session in make_iter(sessions):
                        session.msg(text=text, **kwargs)
                    return
            # we only send to the first of any connected sessions - the sessionhandler
            # will disperse this to the other sessions based on MULTISESSION_MODE.
            sessions = self.player.get_all_sessions()
            if sessions:
                sessions[0].msg(text=text, **kwargs)

    def msg_contents(self, message, exclude=None, from_obj=None, **kwargs):
        """
        Emits something to all objects inside an object.

        exclude is a list of objects not to send to. See self.msg() for
                more info.
        """
        contents = self.contents
        if exclude:
            exclude = make_iter(exclude)
            contents = [obj for obj in contents if obj not in exclude]
        for obj in contents:
            obj.msg(message, from_obj=from_obj, **kwargs)

    def move_to(self, destination, quiet=False,
                emit_to_obj=None, use_destination=True, to_none=False, move_hooks=True):
        """
        Moves this object to a new location.

        Moves this object to a new location. Note that if <destination> is an
        exit object (i.e. it has "destination"!=None), the move_to will
        happen to this destination and -not- into the exit object itself, unless
        use_destination=False. Note that no lock checks are done by this
        function, such things are assumed to have been handled before calling
        move_to.

        Args:
            destination (Object): Reference to the object to move to. This
                 can also be an exit object, in which case the
                 destination property is used as destination.
            quiet (bool): If true, turn off the calling of the emit hooks
                (announce_move_to/from etc)
            emit_to_obj (Object): object to receive error messages
            use_destination (bool): Default is for objects to use the "destination"
                 property of destinations as the target to move to. Turning off this
                 keyword allows objects to move "inside" exit objects.
            to_none (bool): Allow destination to be None. Note that no hooks are run when
                 moving to a None location. If you want to run hooks, run them manually
                 (and make sure they can manage None locations).
            move_hooks (bool): If False, turn off the calling of move-related hooks (at_before/after_move etc)
                with quiet=True, this is as quiet a move as can be done.

        Returns:
            result (bool): True/False depending on if there were problems with the move.
                    This method may also return various error messages to the
                    emit_to_obj.
        """
        def logerr(string=""):
            trc = traceback.format_exc()
            errstring = "%s%s" % (trc, string)
            log_trace()
            self.msg(errstring)

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
        if move_hooks:
            try:
                if not self.at_before_move(destination):
                    return
            except Exception:
                logerr(errtxt % "at_before_move()")
                #emit_to_obj.msg(errtxt % "at_before_move()")
                #logger.log_trace()
                return False

        # Save the old location
        source_location = self.location
        if not source_location:
            # there was some error in placing this room.
            # we have to set one or we won't be able to continue
            if self.home:
                source_location = self.home
            else:
                default_home = ObjectDB.objects.get_id(settings.DEFAULT_HOME)
                source_location = default_home

        # Call hook on source location
        if move_hooks:
            try:
                source_location.at_object_leave(self, destination)
            except Exception:
                logerr(errtxt % "at_object_leave()")
                #emit_to_obj.msg(errtxt % "at_object_leave()")
                #logger.log_trace()
                return False

        if not quiet:
            #tell the old room we are leaving
            try:
                self.announce_move_from(destination)
            except Exception:
                logerr(errtxt % "at_announce_move()")
                #emit_to_obj.msg(errtxt % "at_announce_move()" )
                #logger.log_trace()
                return False

        # Perform move
        try:
            #print "move_to location:", destination
            self.location = destination
        except Exception:
            emit_to_obj.msg(errtxt % "location change")
            log_trace()
            return False

        if not quiet:
            # Tell the new room we are there.
            try:
                self.announce_move_to(source_location)
            except Exception:
                logerr(errtxt % "announce_move_to()")
                #emit_to_obj.msg(errtxt % "announce_move_to()")
                #logger.log_trace()
                return  False

        if move_hooks:
            # Perform eventual extra commands on the receiving location
            # (the object has already arrived at this point)
            try:
                destination.at_object_receive(self, source_location)
            except Exception:
                logerr(errtxt % "at_object_receive()")
                #emit_to_obj.msg(errtxt % "at_object_receive()")
                #logger.log_trace()
                return False

        # Execute eventual extra commands on this object after moving it
        # (usually calling 'look')
        if move_hooks:
            try:
                self.at_after_move(source_location)
            except Exception:
                logerr(errtxt % "at_after_move")
                #emit_to_obj.msg(errtxt % "at_after_move()")
                #logger.log_trace()
                return False
        return True

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
            if default_home.dbid == self.dbid:
                # we are deleting default home!
                default_home = None
        except Exception:
            string = _("Could not find default home '(#%d)'.")
            log_errmsg(string % default_home_id)
            default_home = None

        for obj in objs:
            home = obj.home
            # Obviously, we can't send it back to here.
            if not home or (home and home.dbid == self.dbid):
                obj.home = default_home
                home = default_home

            # If for some reason it's still None...
            if not home:
                string = "Missing default home, '%s(#%d)' "
                string += "now has a null location."
                obj.location = None
                obj.msg(_("Something went wrong! You are dumped into nowhere. Contact an admin."))
                log_errmsg(string % (obj.name, obj.dbid))
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
            key = self.key
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
            from evennia.scripts.models import ScriptDB as _ScriptDB

        if self.delete_iter > 0:
            # make sure to only call delete once on this object
            # (avoid recursive loops)
            return False

        if not self.at_object_delete():
            # this is an extra pre-check
            # run before deletio field-related properties
            # is kicked into gear.
            self.delete_iter = 0
            return False

        self.delete_iter += 1

        # See if we need to kick the player off.

        for session in self.sessions:
            session.msg(_("Your character %s has been destroyed.") % self.key)
            # no need to disconnect, Player just jumps to OOC mode.
        # sever the connection (important!)
        if self.player:
            for sessid in self.sessid.all():
                self.player.unpuppet_object(sessid)
        self.player = None

        for script in _ScriptDB.objects.get_all_scripts_on_obj(self):
            script.stop()

        # Destroy any exits to and from this room, if any
        self.clear_exits()
        # Clear out any non-exit objects located within the object
        self.clear_contents()
        self.attributes.clear()
        self.nicks.clear()
        self.aliases.clear()

        # Perform the deletion of the object
        super(ObjectDB, self).delete()
        return True


    def __eq__(self, other):
        """
        Checks for equality against an id string or another object or user.

        This has be located at this level, having it in the
        parent doesn't work.
        """
        try:
            return self.dbid == other.dbid
        except AttributeError:
           # compare players instead
            try:
                return self.player.uid == other.player.uid
            except AttributeError:
                return False

    def at_first_save(self):
        """
        This is called by the typeclass system whenever an instance of
        this class is saved for the first time. It is a generic hook
        for calling the startup hooks for the various game entities.
        When overloading you generally don't overload this but
        overload the hooks called by this method.
        """
        self.basetype_setup()
        self.at_object_creation()

        if hasattr(self, "_createdict"):
            # this will only be set if the utils.create function
            # was used to create the object. We want the create
            # call's kwargs to override the values set by hooks.
            cdict = self._createdict
            updates = []
            if not cdict.get("key"):
                if not self.db_key:
                    self.db_key = "#%i" % self.dbid
                    updates.append("db_key")
            elif self.key != cdict.get("key"):
                updates.append("db_key")
                self.db_key = cdict["key"]
            if cdict.get("location") and self.location != cdict["location"]:
                self.db_location = cdict["location"]
                updates.append("db_location")
            if cdict.get("home") and self.home != cdict["home"]:
                self.home = cdict["home"]
                updates.append("db_home")
            if cdict.get("destination") and self.destination != cdict["destination"]:
                self.destination = cdict["destination"]
                updates.append("db_destination")
            if updates:
                self.save(update_fields=updates)

            if cdict.get("permissions"):
                self.permissions.add(cdict["permissions"])
            if cdict.get("locks"):
                self.locks.add(cdict["locks"])
            if cdict.get("aliases"):
                self.aliases.add(cdict["aliases"])
            if cdict.get("location"):
                cdict["location"].at_object_receive(self, None)
                self.at_after_move(None)
            if cdict.get("attributes"):
                # this should be a dict of attrname:value
                keys, values = cdict["attributes"].keys(), cdict["attributes"].values()
                self.attributes.batch_add(keys, values)
            if cdict.get("nattributes"):
                # this should be a dict of nattrname:value
                for key, value in cdict["nattributes"].items():
                    self.nattributes.add(key, value)

            del self._createdict

        self.basetype_posthook_setup()


    ## hooks called by the game engine

    def basetype_setup(self):
        """
        This sets up the default properties of an Object,
        just before the more general at_object_creation.

        You normally don't need to change this unless you change some
        fundamental things like names of permission groups.
        """
        # the default security setup fallback for a generic
        # object. Overload in child for a custom setup. Also creation
        # commands may set this (create an item and you should be its
        # controller, for example)

        self.locks.add(";".join([
            "control:perm(Immortals)",  # edit locks/permissions, delete
            "examine:perm(Builders)",   # examine properties
            "view:all()",               # look at object (visibility)
            "edit:perm(Wizards)",       # edit properties/attributes
            "delete:perm(Wizards)",     # delete object
            "get:all()",                # pick up object
            "call:true()",              # allow to call commands on this object
            "tell:perm(Wizards)",        # allow emits to this object
            "puppet:pperm(Immortals)"])) # lock down puppeting only to staff by default

    def basetype_posthook_setup(self):
        """
        Called once, after basetype_setup and at_object_creation. This
        should generally not be overloaded unless you are redefining
        how a room/exit/object works. It allows for basetype-like
        setup after the object is created. An example of this is
        EXITs, who need to know keys, aliases, locks etc to set up
        their exit-cmdsets.
        """
        pass

    def at_object_creation(self):
        """
        Called once, when this object is first created. This is
        the normal hook to overload for most object types.
        """
        pass

    def at_object_delete(self):
        """
        Called just before the database object is
        permanently delete()d from the database. If
        this method returns False, deletion is aborted.
        """
        return True

    def at_init(self):
        """
        This is always called whenever this object is initiated --
        that is, whenever it its typeclass is cached from memory. This
        happens on-demand first time the object is used or activated
        in some way after being created but also after each server
        restart or reload.
        """
        pass

    def at_cmdset_get(self, **kwargs):
        """
        Called just before cmdsets on this object are requested by the
        command handler. If changes need to be done on the fly to the
        cmdset before passing them on to the cmdhandler, this is the
        place to do it. This is called also if the object currently
        have no cmdsets. **kwargs are usually not set but could be
        used e.g. to force rebuilding of a dynamically created cmdset
        or similar.
        """
        pass

    def at_pre_puppet(self, player, sessid=None):
        """
        Called just before a Player connects to this object
        to puppet it.

        player - connecting player object
        sessid - session id controlling the connection
        """
        pass

    def at_post_puppet(self):
        """
        Called just after puppeting has been completed and
        all Player<->Object links have been established.
        """
        self.player.db._last_puppet = self

    def at_pre_unpuppet(self):
        """
        Called just before beginning to un-connect a puppeting
        from this Player.
        """
        pass

    def at_post_unpuppet(self, player, sessid=None):
        """
        Called just after the Player successfully disconnected
        from this object, severing all connections.

        player - the player object that just disconnected from
                 this object.
        sessid - session id controlling the connection
        """
        pass

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for
        restart/reboot. If you want to, for example, save non-persistent
        properties across a restart, this is the place to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully
        (i.e. not for a restart).
        """
        pass

    def at_access(self, result, accessing_obj, access_type, **kwargs):
        """
        This is called with the result of an access call, along with
        any kwargs used for that call. The return of this method does
        not affect the result of the lock check. It can be used e.g. to
        customize error messages in a central location or other effects
        based on the access result.
        """
        pass


    # hooks called when moving the object

    def at_before_move(self, destination):
        """
        Called just before starting to move
        this object to destination.

        destination - the object we are moving to

        If this method returns False/None, the move
        is cancelled before it is even started.
        """
        #return has_perm(self, destination, "can_move")
        return True

    def announce_move_from(self, destination):
        """
        Called if the move is to be announced. This is
        called while we are still standing in the old
        location.

        destination - the place we are going to.
        """
        if not self.location:
            return
        name = self.name
        loc_name = ""
        loc_name = self.location.name
        dest_name = destination.name
        string = "%s is leaving %s, heading for %s."
        self.location.msg_contents(string % (name, loc_name, dest_name), exclude=self)

    def announce_move_to(self, source_location):
        """
        Called after the move if the move was not quiet. At this
        point we are standing in the new location.

        source_location - the place we came from
        """

        name = self.name
        if not source_location and self.location.has_player:
            # This was created from nowhere and added to a player's
            # inventory; it's probably the result of a create command.
            string = "You now have %s in your possession." % name
            self.location.msg(string)
            return

        src_name = "nowhere"
        loc_name = self.location.name
        if source_location:
            src_name = source_location.name
        string = "%s arrives to %s from %s."
        self.location.msg_contents(string % (name, loc_name, src_name), exclude=self)

    def at_after_move(self, source_location):
        """
        Called after move has completed, regardless of quiet mode or not.
        Allows changes to the object due to the location it is now in.

        source_location - where we came from. This may be None.
        """
        pass

    def at_object_leave(self, moved_obj, target_location):
        """
        Called just before an object leaves from inside this object

        moved_obj - the object leaving
        target_location - where the object is going.
        """
        pass

    def at_object_receive(self, moved_obj, source_location):
        """
        Called after an object has been moved into this object.

        moved_obj - the object moved into this one
        source_location - where moved_object came from.
        """
        pass

    def at_before_traverse(self, traversing_object):
        """
        Called just before an object uses this object to
        traverse to another object (i.e. this object is a type of Exit)

        The target location should normally be available as self.destination.
        """
        pass

    def at_traverse(self, traversing_object, target_location):
        """
        This hook is responsible for handling the actual traversal, normally
        by calling traversing_object.move_to(target_location). It is normally
        only implemented by Exit objects. If it returns False (usually because
        move_to returned False), at_after_traverse below should not be called
        and instead at_failed_traverse should be called.
        """
        pass

    def at_after_traverse(self, traversing_object, source_location):
        """
        Called just after an object successfully used this object to
        traverse to another object (i.e. this object is a type of Exit)

        The target location should normally be available as self.destination.
        """
        pass

    def at_failed_traverse(self, traversing_object):
        """
        This is called if an object fails to traverse this object for some
        reason. It will not be called if the attribute err_traverse is defined,
        that attribute will then be echoed back instead.
        """
        pass

    def at_msg_receive(self, text=None, **kwargs):
        """
        This hook is called whenever someone
        sends a message to this object.

        Note that from_obj may be None if the sender did
        not include itself as an argument to the obj.msg()
        call - so you have to check for this. .

        Consider this a pre-processing method before
        msg is passed on to the user sesssion. If this
        method returns False, the msg will not be
        passed on.
        Input:
            msg = the message received
            from_obj = the one sending the message
        Output:
            boolean True/False
        """
        return True

    def at_msg_send(self, text=None, to_obj=None, **kwargs):
        """
        This is a hook that is called when /this/ object
        sends a message to another object with obj.msg()
        while also specifying that it is the one sending.

        Note that this method is executed on the object
        passed along with the msg() function (i.e. using
        obj.msg(msg, from_obj=caller) will then launch caller.at_msg())
        and if no object was passed, it will never be called.
        """
        pass

    # hooks called by the default cmdset.

    def return_appearance(self, pobject):
        """
        This is a convenient hook for a 'look'
        command to call.
        """
        if not pobject:
            return
        # get and identify all objects
        visible = (con for con in self.contents if con != pobject and
                                                    con.access(pobject, "view"))
        exits, users, things = [], [], []
        for con in visible:
            key = con.key
            if con.destination:
                exits.append(key)
            elif con.has_player:
                users.append("{c%s{n" % key)
            else:
                things.append(key)
        # get description, build string
        string = "{c%s{n\n" % self.key
        desc = self.db.desc
        if desc:
            string += "%s" % desc
        if exits:
            string += "\n{wExits:{n " + ", ".join(exits)
        if users or things:
            string += "\n{wYou see:{n " + ", ".join(users + things)
        return string

    def at_desc(self, looker=None):
        """
        This is called whenever someone looks
        at this object. Looker is the looking
        object.
        """
        pass

    def at_get(self, getter):
        """
        Called when this object has been picked up. Obs-
        this method cannot stop the pickup - use permissions
        for that!

        getter - the object getting this object.
        """
        pass

    def at_drop(self, dropper):
        """
        Called when this object has been dropped.

        dropper - the object which just dropped this object.
        """
        pass

    def at_say(self, speaker, message):
        """
        Called on this object if an object inside this object speaks.
        The string returned from this method is the final form
        of the speech. Obs - you don't have to add things like
        'you say: ' or similar, that is handled by the say command.

        speaker - the object speaking
        message - the words spoken.
        """
        return message


#
# Base Character object
#

class DefaultCharacter(DefaultObject):
    """
    This is just like the Object except it implements its own
    version of the at_object_creation to set up the script
    that adds the default cmdset to the object.
    """

    def basetype_setup(self):
        """
        Setup character-specific security

        You should normally not need to overload this, but if you do, make
        sure to reproduce at least the two last commands in this method (unless
        you want to fundamentally change how a Character object works).

        """
        super(DefaultCharacter, self).basetype_setup()
        self.locks.add(";".join(["get:false()",  # noone can pick up the character
                                 "call:false()"])) # no commands can be called on character from outside
        # add the default cmdset
        self.cmdset.add_default(settings.CMDSET_CHARACTER, permanent=True)

    def at_object_creation(self):
        """
        All this does (for now) is to add the default cmdset. Since
        the script is permanently stored to this object (the permanent
        keyword creates a script to do this), we should never need to
        do this again for as long as this object exists.
        """
        pass

    def at_after_move(self, source_location):
        "Default is to look around after a move."
        self.execute_cmd('look')

    def at_pre_puppet(self, player, sessid=None):
        """
        This recovers the character again after having been "stoved away"
        at the unpuppet
        """
        if self.db.prelogout_location:
            # try to recover
            self.location = self.db.prelogout_location
        if self.location is None:
            # make sure location is never None (home should always exist)
            self.location = self.home
        if self.location:
            # save location again to be sure
            self.db.prelogout_location = self.location
            self.location.at_object_receive(self, self.location)
        else:
            player.msg("{r%s has no location and no home is set.{n" % self, sessid=sessid)

    def at_post_puppet(self):
        """
        Called just after puppeting has completed.
        """
        self.msg("\nYou become {c%s{n.\n" % self.name)
        self.execute_cmd("look")
        if self.location:
            self.location.msg_contents("%s has entered the game." % self.name, exclude=[self])

    def at_post_unpuppet(self, player, sessid=None):
        """
        We stove away the character when the player goes ooc/logs off,
        otherwise the character object will remain in the room also after the
        player logged off ("headless", so to say).
        """
        if self.location: # have to check, in case of multiple connections closing
            self.location.msg_contents("%s has left the game." % self.name, exclude=[self])
            self.db.prelogout_location = self.location
            self.location = None

#
# Base Room object
#

class DefaultRoom(DefaultObject):
    """
    This is the base room object. It's just like any Object except its
    location is None.
    """
    def basetype_setup(self):
        """
        Simple setup, shown as an example
        (since default is None anyway)
        """

        super(DefaultRoom, self).basetype_setup()
        self.locks.add(";".join(["get:false()",
                                 "puppet:false()"])) # would be weird to puppet a room ...
        self.location = None


#
# Base Exit object
#

class DefaultExit(DefaultObject):
    """
    This is the base exit object - it connects a location to another.
    This is done by the exit assigning a "command" on itself with the
    same name as the exit object (to do this we need to remember to
    re-create the command when the object is cached since it must be
    created dynamically depending on what the exit is called). This
    command (which has a high priority) will thus allow us to traverse
    exits simply by giving the exit-object's name on its own.
    """

    # Helper classes and methods to implement the Exit. These need not
    # be overloaded unless one want to change the foundation for how
    # Exits work. See the end of the class for hook methods to overload.

    def create_exit_cmdset(self, exidbobj):
        """
        Helper function for creating an exit command set + command.

        The command of this cmdset has the same name as the Exit object
        and allows the exit to react when the player enter the exit's name,
        triggering the movement between rooms.

        Note that exitdbobj is an ObjectDB instance. This is necessary
        for handling reloads and avoid tracebacks if this is called while
        the typeclass system is rebooting.
        """
        class ExitCommand(command.Command):
            """
            This is a command that simply cause the caller
            to traverse the object it is attached to.
            """
            obj = None

            def func(self):
                "Default exit traverse if no syscommand is defined."

                if self.obj.access(self.caller, 'traverse'):
                    # we may traverse the exit.
                    self.obj.at_traverse(self.caller, self.obj.destination)
                else:
                    # exit is locked
                    if self.obj.db.err_traverse:
                        # if exit has a better error message, let's use it.
                        self.caller.msg(self.obj.db.err_traverse)
                    else:
                        # No shorthand error message. Call hook.
                        self.obj.at_failed_traverse(self.caller)

        # create an exit command. We give the properties here,
        # to always trigger metaclass preparations
        cmd = ExitCommand(key=exidbobj.db_key.strip().lower(),
                          aliases=exidbobj.aliases.all(),
                          locks=str(exidbobj.locks),
                          auto_help=False,
                          destination=exidbobj.db_destination,
                          arg_regex=r"^$",
                          is_exit=True,
                          obj=exidbobj)
        # create a cmdset
        exit_cmdset = cmdset.CmdSet(None)
        exit_cmdset.key = '_exitset'
        exit_cmdset.priority = 101
        exit_cmdset.duplicates = True
        # add command to cmdset
        exit_cmdset.add(cmd)
        return exit_cmdset

    # Command hooks
    def basetype_setup(self):
        """
        Setup exit-security

        You should normally not need to overload this - if you do make sure you
        include all the functionality in this method.
        """
        super(DefaultExit, self).basetype_setup()

        # setting default locks (overload these in at_object_creation()
        self.locks.add(";".join(["puppet:false()", # would be weird to puppet an exit ...
                                 "traverse:all()", # who can pass through exit by default
                                 "get:false()"]))   # noone can pick up the exit

        # an exit should have a destination (this is replaced at creation time)
        if self.location:
            self.destination = self.location

    def at_cmdset_get(self, **kwargs):
        """
        Called when the cmdset is requested from this object, just before the
        cmdset is actually extracted. If no Exit-cmdset is cached, create
        it now.

        kwargs:
          force_init=True - force a re-build of the cmdset (for example to update aliases)
        """

        if "force_init" in kwargs or not self.cmdset.has_cmdset("_exitset", must_be_default=True):
            # we are resetting, or no exit-cmdset was set. Create one dynamically.
            self.cmdset.add_default(self.create_exit_cmdset(self), permanent=False)

    # this and other hooks are what usually can be modified safely.

    def at_object_creation(self):
        "Called once, when object is first created (after basetype_setup)."
        pass

    def at_traverse(self, traversing_object, target_location):
        """
        This implements the actual traversal. The traverse lock has already been
        checked (in the Exit command) at this point.
        """
        source_location = traversing_object.location
        if traversing_object.move_to(target_location):
            self.at_after_traverse(traversing_object, source_location)
        else:
            if self.db.err_traverse:
                # if exit has a better error message, let's use it.
                self.caller.msg(self.db.err_traverse)
            else:
                # No shorthand error message. Call hook.
                self.at_failed_traverse(traversing_object)

    def at_after_traverse(self, traversing_object, source_location):
        """
        Called after a successful traverse.
        """
        pass

    def at_failed_traverse(self, traversing_object):
        """
        This is called if an object fails to traverse this object for some
        reason. It will not be called if the attribute "err_traverse" is
        defined, that attribute will then be echoed back instead as a
        convenient shortcut.

        (See also hooks at_before_traverse and at_after_traverse).
        """
        traversing_object.msg("You cannot go there.")
