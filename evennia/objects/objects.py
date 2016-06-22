"""
This module defines the basic `DefaultObject` and its children
`DefaultCharacter`, `DefaultPlayer`, `DefaultRoom` and `DefaultExit`.
These are the (default) starting points for all in-game visible
entities.

"""
import time
from builtins import object
from future.utils import listvalues, with_metaclass

from django.conf import settings

from evennia.typeclasses.models import TypeclassBase
from evennia.typeclasses.attributes import NickHandler
from evennia.objects.manager import ObjectManager
from evennia.objects.models import ObjectDB
from evennia.scripts.scripthandler import ScriptHandler
from evennia.commands import cmdset, command
from evennia.commands.cmdsethandler import CmdSetHandler
from evennia.commands import cmdhandler
from evennia.utils import logger
from evennia.utils.utils import (variable_from_module, lazy_property,
                                 make_iter, to_unicode)

_MULTISESSION_MODE = settings.MULTISESSION_MODE

_ScriptDB = None
_SESSIONS = None

_AT_SEARCH_RESULT = variable_from_module(*settings.SEARCH_AT_RESULT.rsplit('.', 1))
# the sessid_max is based on the length of the db_sessid csv field (excluding commas)
_SESSID_MAX = 16 if _MULTISESSION_MODE in (1, 3) else 1

from django.utils.translation import ugettext as _

class ObjectSessionHandler(object):
    """
    Handles the get/setting of the sessid
    comma-separated integer field
    """
    def __init__(self, obj):
        """
        Initializes the handler.

        Args:
            obj (Object): The object on which the handler is defined.

        """
        self.obj = obj
        self._sessid_cache = []
        self._recache()

    def _recache(self):
        self._sessid_cache = list(set(int(val) for val in (self.obj.db_sessid or "").split(",") if val))

    def get(self, sessid=None):
        """
        Get the sessions linked to this Object.

        Args:
            sessid (int, optional): A specific session id.

        Returns:
            sessions (list): The sessions connected to this object. If `sessid` is given,
                this is a list of one (or zero) elements.

        Notes:
            Aliased to `self.all()`.

        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        if sessid:
            return [_SESSIONS[sessid]] if sessid in self._sessid_cache and sessid in _SESSIONS else []
        else:
            return [_SESSIONS[sessid] for sessid in self._sessid_cache if sessid in _SESSIONS]

    def all(self):
        """
        Alias to get(), returning all sessions.

        Returns:
            sessions (list): All sessions.

        """
        return self.get()

    def add(self, session):
        """
        Add session to handler.

        Args:
            session (Session or int): Session or session id to add.

        Notes:
            We will only add a session/sessid if this actually also exists
            in the the core sessionhandler.

        """
        global _SESSIONS
        if not _SESSIONS:
            from evennia.server.sessionhandler import SESSIONS as _SESSIONS
        try:
            sessid = session.sessid
        except AttributeError:
            sessid = session

        sessid_cache = self._sessid_cache
        if sessid in _SESSIONS and sessid not in sessid_cache:
            if len(sessid_cache) >= _SESSID_MAX:
                return
            sessid_cache.append(sessid)
            self.obj.db_sessid = ",".join(str(val) for val in sessid_cache)
            self.obj.save(update_fields=["db_sessid"])

    def remove(self, session):
        """
        Remove session from handler.

        Args:
            sessid (Session or int): Session or session id to remove.

        """
        try:
            sessid = session.sessid
        except AttributeError:
            sessid = session

        sessid_cache = self._sessid_cache
        if sessid in sessid_cache:
            sessid_cache.remove(sessid)
            self.obj.db_sessid =  ",".join(str(val) for val in sessid_cache)
            self.obj.save(update_fields=["db_sessid"])

    def clear(self):
        """
        Clear all handled sessids.

        """
        self._sessid_cache = []
        self.obj.db_sessid = None
        self.obj.save(update_fields=["db_sessid"])

    def count(self):
        """
        Get amount of sessions connected.

        Returns:
            sesslen (int): Number of sessions handled.

        """
        return len(self._sessid_cache)



#
# Base class to inherit from.
#

class DefaultObject(with_metaclass(TypeclassBase, ObjectDB)):
    """
    This is the root typeclass object, representing all entities that
    have an actual presence in-game. DefaultObjects generally have a
    location. They can also be manipulated and looked at. Game
    entities you define should inherit from DefaultObject at some distance.

    It is recommended to create children of this class using the
    `evennia.create_object()` function rather than to initialize the class
    directly - this will both set things up and efficiently save the object
    without `obj.save()` having to be called explicitly.

    """
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
    def sessions(self):
        return ObjectSessionHandler(self)

    @property
    def has_player(self):
        """
        Convenience property for checking if an active player is
        currently connected to this object.

        """
        return self.sessions.count()

    @property
    def is_superuser(self):
        """
        Check if user has a player, and if so, if it is a superuser.

        """
        return self.db_player and self.db_player.is_superuser \
                and not self.db_player.attributes.get("_quell")

    def contents_get(self, exclude=None):
        """
        Returns the contents of this object, i.e. all
        objects that has this object set as its location.
        This should be publically available.

        Args:
            exclude (Object): Object to exclude from returned
                contents list

        Returns:
            contents (list): List of contents of this Object.

        Notes:
            Also available as the `contents` property.

        """
        return self.contents_cache.get(exclude=exclude)
    contents = property(contents_get)

    @property
    def exits(self):
        """
        Returns all exits from this object, i.e. all objects at this
        location having the property destination != `None`.
        """
        return [exi for exi in self.contents if exi.destination]

    # main methods

    def get_display_name(self, looker, **kwargs):
        """
        Displays the name of the object in a viewer-aware manner.

        Args:
            looker (TypedObject): The object or player that is looking
                at/getting inforamtion for this object.

        Returns:
            name (str): A string containing the name of the object,
                including the DBREF if this user is privileged to control
                said object.

        Notes:
            This function could be extended to change how object names
            appear to users in character, but be wary. This function
            does not change an object's keys or aliases when
            searching, and is expected to produce something useful for
            builders.

        """
        if self.locks.check_lockstring(looker, "perm(Builders)"):
            return "{}(#{})".format(self.name, self.id)
        return self.name


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
        Returns the typeclass of an `Object` matching a search
        string/condition

        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully. By default, only
        objects in the current `location` of `self` or its inventory are searched for.

        Args:
            searchdata (str or obj): Primary search criterion. Will be matched
                against `object.key` (with `object.aliases` second) unless
                the keyword attribute_name specifies otherwise.
                **Special strings:**
                - `#<num>`: search by unique dbref. This is always
                   a global search.
                - `me,self`: self-reference to this object
                - `<num>-<string>` - can be used to differentiate
                   between multiple same-named matches
            global_search (bool): Search all objects globally. This is overruled
                by `location` keyword.
            use_nicks (bool): Use nickname-replace (nicktype "object") on `searchdata`.
            typeclass (str or Typeclass, or list of either): Limit search only
                to `Objects` with this typeclass. May be a list of typeclasses
                for a broader search.
            location (Object or list): Specify a location or multiple locations 
                to search. Note that this is used to query the *contents* of a 
                location and will not match for the location itself -
                if you want that, don't set this or use `candidates` to specify 
                exactly which objects should be searched.
            attribute_name (str): Define which property to search. If set, no
                key+alias search will be performed. This can be used
                to search database fields (db_ will be automatically
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
                to search (filter) between. It is ignored if `global_search`
                is given. If not set, this list will automatically be defined
                to include the location, the contents of location and the
                caller's contents (inventory).
            nofound_string (str):  optional custom string for not-found error message.
            multimatch_string (str): optional custom string for multimatch error header.

        Returns:
            match (Object, None or list): will return an Object/None if `quiet=False`,
                otherwise it will return a list of 0, 1 or more matches.

        Notes:
            To find Players, use eg. `evennia.player_search`. If
            `quiet=False`, error messages will be handled by
            `settings.SEARCH_AT_RESULT` and echoed automatically (on
            error, return will be `None`). If `quiet=True`, the error
            messaging is assumed to be handled by the caller.

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
        return  _AT_SEARCH_RESULT(results, self, query=searchdata,
                nofound_string=nofound_string, multimatch_string=multimatch_string)

    def search_player(self, searchdata, quiet=False):
        """
        Simple shortcut wrapper to search for players, not characters.

        Args:
            searchdata (str): Search criterion - the key or dbref of the player
                to search for. If this is "here" or "me", search
                for the player connected to this object.
            quiet (bool): Returns the results as a list rather than
                echo eventual standard error messages. Default `False`.

        Returns:
            result (Player, None or list): Just what is returned depends on
                the `quiet` setting:
                    - `quiet=True`: No match or multumatch auto-echoes errors
                      to self.msg, then returns `None`. The esults are passed
                      through `settings.SEARCH_AT_RESULT` and
                      `settings.SEARCH_AT_MULTIMATCH_INPUT`. If there is a
                      unique match, this will be returned.
                    - `quiet=True`: No automatic error messaging is done, and
                      what is returned is always a list with 0, 1 or more
                      matching Players.

        """
        if isinstance(searchdata, basestring):
            # searchdata is a string; wrap some common self-references
            if searchdata.lower() in ("me", "self",):
                return [self.player] if quiet else self.player

        results = self.player.__class__.objects.player_search(searchdata)

        if quiet:
            return results
        return _AT_SEARCH_RESULT(results, self, query=searchdata)

    def execute_cmd(self, raw_string, session=None, **kwargs):
        """
        Do something as this object. This is never called normally,
        it's only used when wanting specifically to let an object be
        the caller of a command. It makes use of nicks of eventual
        connected players as well.

        Args:
            raw_string (string): Raw command input
            session (Session, optional): Session to
                return results to

        Kwargs:
            Other keyword arguments will be added to the found command
            object instace as variables before it executes.  This is
            unused by default Evennia but may be used to set flags and
            change operating paramaters for commands at run-time.

        Returns:
            defer (Deferred): This is an asynchronous Twisted object that
                will not fire until the command has actually finished
                executing. To overload this one needs to attach
                callback functions to it, with addCallback(function).
                This function will be called with an eventual return
                value from the command execution. This return is not
                used at all by Evennia by default, but might be useful
                for coders intending to implement some sort of nested
                command structure.

        """
        # nick replacement - we require full-word matching.
        # do text encoding conversion
        raw_string = to_unicode(raw_string)
        raw_string = self.nicks.nickreplace(raw_string,
                     categories=("inputline", "channel"), include_player=True)
        return cmdhandler.cmdhandler(self, raw_string, callertype="object", session=session, **kwargs)


    def msg(self, text=None, from_obj=None, session=None, options=None, **kwargs):
        """
        Emits something to a session attached to the object.

        Args:
            text (str or tuple, optional): The message to send. This
                is treated internally like any send-command, so its
                value can be a tuple if sending multiple arguments to
                the `text` oob command.
            from_obj (obj, optional): object that is sending. If
                given, at_msg_send will be called. This value will be
                passed on to the protocol.
            session (Session or list, optional): Session or list of
                Sessions to relay data to, if any. If set, will force send
                to these sessions. If unset, who receives the message
                depends on the MULTISESSION_MODE.
            options (dict, optional): Message-specific option-value
                pairs. These will be applied at the protocol level.
        Kwargs:
            any (string or tuples): All kwarg keys not listed above
                will be treated as send-command names and their arguments
                (which can be a string or a tuple).

        Notes:
            `at_msg_receive` will be called on this Object.
            All extra kwargs will be passed on to the protocol.

        """
        # try send hooks
        if from_obj:
            try:
                from_obj.at_msg_send(text=text, to_obj=self, **kwargs)
            except Exception:
                logger.log_trace()
        try:
            if not self.at_msg_receive(text=text, **kwargs):
                # if at_msg_receive returns false, we abort message to this object
                return
        except Exception:
            logger.log_trace()

        kwargs["options"] = options

        # relay to session(s)
        sessions = make_iter(session) if session else self.sessions.all()
        for session in sessions:
            session.data_out(text=text, **kwargs)

    def for_contents(self, func, exclude=None, **kwargs):
        """
        Runs a function on every object contained within this one.

        Args:
            func (callable): Function to call. This must have the
                formal call sign func(obj, **kwargs), where obj is the
                object currently being processed and `**kwargs` are
                passed on from the call to `for_contents`.
            exclude (list, optional): A list of object not to call the
                function on.

        Kwargs:
            Keyword arguments will be passed to the function for all objects.
        """
        contents = self.contents
        if exclude:
            exclude = make_iter(exclude)
            contents = [obj for obj in contents if obj not in exclude]
        for obj in contents:
            func(obj, **kwargs)

    def msg_contents(self, message, exclude=None, from_obj=None, **kwargs):
        """
        Emits a message to all objects inside this object.

        Args:
            message (str): Message to send.
            exclude (list, optional): A list of objects not to send to.
            from_obj (Object, optional): An object designated as the
                "sender" of the message. See `DefaultObject.msg()` for
                more info.

        Kwargs:
            Keyword arguments will be passed on to `obj.msg()` for all
            messaged objects.

        """
        def msg(obj, message, from_obj, **kwargs):
            obj.msg(message, from_obj=from_obj, **kwargs)
        self.for_contents(msg, exclude=exclude, from_obj=from_obj, message=message, **kwargs)

    def move_to(self, destination, quiet=False,
                emit_to_obj=None, use_destination=True, to_none=False, move_hooks=True):
        """
        Moves this object to a new location.

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
            move_hooks (bool): If False, turn off the calling of move-related hooks
                (at_before/after_move etc) with quiet=True, this is as quiet a move
                as can be done.

        Returns:
            result (bool): True/False depending on if there were problems with the move.
                    This method may also return various error messages to the
                    `emit_to_obj`.

        Notes:
            No access checks are done in this method, these should be handled before
            calling `move_to`.

            The `DefaultObject` hooks called (if `move_hooks=True`) are, in order:

             1. `self.at_before_move(destination)` (if this returns False, move is aborted)
             2. `source_location.at_object_leave(self, destination)`
             3. `self.announce_move_from(destination)`
             4. (move happens here)
             5. `self.announce_move_to(source_location)`
             6. `destination.at_object_receive(self, source_location)`
             7. `self.at_after_move(source_location)`

        """
        def logerr(string="", err=None):
            "Simple log helper method"
            logger.log_trace()
            self.msg("%s%s" % (string, "" if err is None else " (%s)" % err))

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
            except Exception as err:
                logerr(errtxt % "at_before_move()", err)
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
            except Exception as err:
                logerr(errtxt % "at_object_leave()", err)
                return False

        if not quiet:
            #tell the old room we are leaving
            try:
                self.announce_move_from(destination)
            except Exception as err:
                logerr(errtxt % "at_announce_move()", err)
                return False

        # Perform move
        try:
            self.location = destination
        except Exception as err:
            logerr(errtxt % "location change", err)
            return False

        if not quiet:
            # Tell the new room we are there.
            try:
                self.announce_move_to(source_location)
            except Exception as err:
                logerr(errtxt % "announce_move_to()", err)
                return  False

        if move_hooks:
            # Perform eventual extra commands on the receiving location
            # (the object has already arrived at this point)
            try:
                destination.at_object_receive(self, source_location)
            except Exception as err:
                logerr(errtxt % "at_object_receive()", err)
                return False

        # Execute eventual extra commands on this object after moving it
        # (usually calling 'look')
        if move_hooks:
            try:
                self.at_after_move(source_location)
            except Exception as err:
                logerr(errtxt % "at_after_move", err)
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
        Moves all objects (players/things) to their home location or
        to default home.
        """
        # Gather up everything that thinks this is its location.
        default_home_id = int(settings.DEFAULT_HOME.lstrip("#"))
        try:
            default_home = ObjectDB.objects.get(id=default_home_id)
            if default_home.dbid == self.dbid:
                # we are deleting default home!
                default_home = None
        except Exception:
            string = _("Could not find default home '(#%d)'.")
            logger.log_err(string % default_home_id)
            default_home = None

        for obj in self.contents:
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
                logger.log_err(string % (obj.name, obj.dbid))
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
        Makes an identical copy of this object, identical except for a
        new dbref in the database. If you want to customize the copy
        by changing some settings, use ObjectDB.object.copy_object()
        directly.

        Args:
            new_key (string): New key/name of copied object. If new_key is not
                specified, the copy will be named <old_key>_copy by default.
        Returns:
            copy (Object): A copy of this object.

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
        Deletes this object.  Before deletion, this method makes sure
        to move all contained objects to their respective home
        locations, as well as clean up all exits to/from the object.

        Returns:
            noerror (bool): Returns whether or not the delete completed
                successfully or not.

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
            # run before deletion field-related properties
            # is kicked into gear.
            self.delete_iter = 0
            return False

        self.delete_iter += 1

        # See if we need to kick the player off.

        for session in self.sessions.all():
            session.msg(_("Your character %s has been destroyed.") % self.key)
            # no need to disconnect, Player just jumps to OOC mode.
        # sever the connection (important!)
        if self.player:
            for session in self.sessions.all():
                self.player.unpuppet_object(session)
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
        self.location = None # this updates contents_cache for our location

        # Perform the deletion of the object
        super(ObjectDB, self).delete()
        return True

    def access(self, accessing_obj, access_type='read', default=False, no_superuser_bypass=False, **kwargs):
        """
        Determines if another object has permission to access this object
        in whatever way.

        Args:
          accessing_obj (Object): Object trying to access this one.
          access_type (str, optional): Type of access sought.
          default (bool, optional): What to return if no lock of access_type was found.
          no_superuser_bypass (bool, optional): If `True`, don't skip
            lock check for superuser (be careful with this one).

        Kwargs:
          Passed on to the at_access hook along with the result of the access check.

        """
        result = super(DefaultObject, self).access(accessing_obj, access_type=access_type,
                                                   default=default, no_superuser_bypass=no_superuser_bypass)
        self.at_access(result, accessing_obj, access_type, **kwargs)
        return result

    def __eq__(self, other):
        """
        Checks for equality against an id string or another object or
        user.

        Args:
            other (Object): object to compare to.

        """
        try:
            return self.dbid == other.dbid
        except AttributeError:
           # compare players instead
            try:
                return self.player.uid == other.player.uid
            except AttributeError:
                return False

    #
    # Hook methods
    #

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
            if cdict.get("tags"):
                # this should be a list of tags
                self.tags.add(cdict["tags"])
            if cdict.get("attributes"):
                # this should be a dict of attrname:value
                keys, values = list(cdict["attributes"]), listvalues(cdict["attributes"])
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
        This sets up the default properties of an Object, just before
        the more general at_object_creation.

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
        Called once, when this object is first created. This is the
        normal hook to overload for most object types.

        """
        pass

    def at_object_delete(self):
        """
        Called just before the database object is permanently
        delete()d from the database. If this method returns False,
        deletion is aborted.

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
        have no cmdsets.

        Kwargs:
            Usually not set but could be used e.g. to force rebuilding
            of a dynamically created cmdset or similar.

        """
        pass

    def at_pre_puppet(self, player, session=None):
        """
        Called just before a Player connects to this object to puppet
        it.

        Args:
            player (Player): This is the connecting player.
            session (Session): Session controlling the connection.
        """
        pass

    def at_post_puppet(self):
        """
        Called just after puppeting has been completed and all
        Player<->Object links have been established.

        Note:
            You can use `self.player` and `self.sessions.get()` to get
            player and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        self.player.db._last_puppet = self

    def at_pre_unpuppet(self):
        """
        Called just before beginning to un-connect a puppeting from
        this Player.

        Note:
            You can use `self.player` and `self.sessions.get()` to get
            player and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        pass

    def at_post_unpuppet(self, player, session=None):
        """
        Called just after the Player successfully disconnected from
        this object, severing all connections.

        Args:
            player (Player): The player object that just disconnected
                from this object.
            session (Session): Session id controlling the connection that
                just disconnected.

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

        Args:
            result (bool): The outcome of the access call.
            accessing_obj (Object or Player): The entity trying to
            gain access.  access_type (str): The type of access that
            was requested.

        Kwargs:
            Not used by default, added for possible expandability in a
            game.

        """
        pass


    # hooks called when moving the object

    def at_before_move(self, destination):
        """
        Called just before starting to move this object to
        destination.

        Args:
            destination (Object): The object we are moving to

        Returns:
            shouldmove (bool): If we should move or not.

        Notes:
            If this method returns False/None, the move is cancelled
            before it is even started.

        """
        #return has_perm(self, destination, "can_move")
        return True

    def announce_move_from(self, destination):
        """
        Called if the move is to be announced. This is
        called while we are still standing in the old
        location.

        Args:
            destination (Object): The place we are going to.

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
        Called after the move if the move was not quiet. At this point
        we are standing in the new location.

        Args:
            source_location (Object): The place we came from

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
        Called after move has completed, regardless of quiet mode or
        not.  Allows changes to the object due to the location it is
        now in.

        Args:
            source_location (Object): Wwhere we came from. This may be `None`.

        """
        pass

    def at_object_leave(self, moved_obj, target_location):
        """
        Called just before an object leaves from inside this object

        Args:
            moved_obj (Object): The object leaving
            target_location (Object): Where `moved_obj` is going.

        """
        pass

    def at_object_receive(self, moved_obj, source_location):
        """
        Called after an object has been moved into this object.

        Args:
            moved_obj (Object): The object moved into this one
            source_location (Object): Where `moved_object` came from.

        """
        pass

    def at_traverse(self, traversing_object, target_location):
        """
        This hook is responsible for handling the actual traversal,
        normally by calling
        `traversing_object.move_to(target_location)`. It is normally
        only implemented by Exit objects. If it returns False (usually
        because `move_to` returned False), `at_after_traverse` below
        should not be called and instead `at_failed_traverse` should be
        called.

        Args:
            traversing_object (Object): Object traversing us.
            target_location (Object): Where target is going.

        """
        pass

    def at_after_traverse(self, traversing_object, source_location):
        """
        Called just after an object successfully used this object to
        traverse to another object (i.e. this object is a type of
        Exit)

        Args:
            traversing_object (Object): The object traversing us.
            source_location (Object): Where `traversing_object` came from.

        Notes:
            The target location should normally be available as `self.destination`.
        """
        pass

    def at_failed_traverse(self, traversing_object):
        """
        This is called if an object fails to traverse this object for
        some reason.

        Args:
            traversing_object (Object): The object that failed traversing us.

        Notes:
            Using the default exits, this hook will not be called if an
            Attribute `err_traverse` is defined - this will in that case be
            read for an error string instead.

        """
        pass

    def at_msg_receive(self, text=None, **kwargs):
        """
        This hook is called whenever someone sends a message to this
        object using the `msg` method.

        Note that from_obj may be None if the sender did not include
        itself as an argument to the obj.msg() call - so you have to
        check for this. .

        Consider this a pre-processing method before msg is passed on
        to the user sesssion. If this method returns False, the msg
        will not be passed on.

        Args:
            text (str, optional): The message received.

        Kwargs:
            This includes any keywords sent to the `msg` method.

        Returns:
            receive (bool): If this message should be received.

        Notes:
            If this method returns False, the `msg` operation
            will abort without sending the message.

        """
        return True

    def at_msg_send(self, text=None, to_obj=None, **kwargs):
        """
        This is a hook that is called when *this* object sends a
        message to another object with `obj.msg(text, to_obj=obj)`.

        Args:
            text (str): Text to send.
            to_obj (Object): The object to send to.

        Kwargs:
            Keywords passed from msg()

        Notes:
            Since this method is executed `from_obj`, if no `from_obj`
            was passed to `DefaultCharacter.msg` this hook will never
            get called.

        """
        pass

    # hooks called by the default cmdset.

    def return_appearance(self, looker):
        """
        This formats a description. It is the hook a 'look' command
        should call.

        Args:
            looker (Object): Object doing the looking.
        """
        if not looker:
            return
        # get and identify all objects
        visible = (con for con in self.contents if con != looker and
                                                    con.access(looker, "view"))
        exits, users, things = [], [], []
        for con in visible:
            key = con.get_display_name(looker)
            if con.destination:
                exits.append(key)
            elif con.has_player:
                users.append("{c%s{n" % key)
            else:
                things.append(key)
        # get description, build string
        string = "{c%s{n\n" % self.get_display_name(looker)
        desc = self.db.desc
        if desc:
            string += "%s" % desc
        if exits:
            string += "\n{wExits:{n " + ", ".join(exits)
        if users or things:
            string += "\n{wYou see:{n " + ", ".join(users + things)
        return string

    def at_look(self, target):
        """
        Called when this object performs a look. It allows to
        customize just what this means. It will not itself
        send any data.

        Args:
            target (Object): The target being looked at. This is
                commonly an object or the current location. It will
                be checked for the "view" type access.

        Returns:
            lookstring (str): A ready-processed look string
                potentially ready to return to the looker.

        """
        if not target.access(self, "view"):
            try:
                return "Could not view '%s'." % target.get_display_name(self)
            except AttributeError:
                return "Could not view '%s'." % target.key
        # the target's at_desc() method.
        target.at_desc(looker=self)
        return target.return_appearance(self)

    def at_desc(self, looker=None):
        """
        This is called whenever someone looks at this object.

        looker (Object): The object requesting the description.

        """
        pass

    def at_get(self, getter):
        """
        Called by the default `get` command when this object has been
        picked up.

        Args:
            getter (Object): The object getting this object.

        Notes:
            This hook cannot stop the pickup from happening. Use
            permissions for that.

        """
        pass

    def at_drop(self, dropper):
        """
        Called by the default `drop` command when this object has been
        dropped.

        Args:
            dropper (Object): The object which just dropped this object.

        Notes:
            This hook cannot stop the pickup from happening. Use
            permissions from that.

        """
        pass

    def at_say(self, speaker, message):
        """
        Called on this object if an object inside this object speaks.
        The string returned from this method is the final form of the
        speech.

        Args:
            speaker (Object): The object speaking.
            message (str): The words spoken.

        Notes:
            You should not need to add things like 'you say: ' or
            similar here, that should be handled by the say command before
            this.

        """
        return message


#
# Base Character object
#

class DefaultCharacter(DefaultObject):
    """
    This implements an Object puppeted by a Session - that is,
    a character avatar controlled by a player.

    """

    def basetype_setup(self):
        """
        Setup character-specific security.

        You should normally not need to overload this, but if you do,
        make sure to reproduce at least the two last commands in this
        method (unless you want to fundamentally change how a
        Character object works).

        """
        super(DefaultCharacter, self).basetype_setup()
        self.locks.add(";".join(["get:false()",  # noone can pick up the character
                                 "call:false()"])) # no commands can be called on character from outside
        # add the default cmdset
        self.cmdset.add_default(settings.CMDSET_CHARACTER, permanent=True)

    def at_after_move(self, source_location):
        """
        We make sure to look around after a move.

        """
        if self.location.access(self, "view"):
            self.msg(self.at_look(self.location))

    def at_pre_puppet(self, player, session=None):
        """
        This implementation recovers the character again after having been "stoved
        away" to the `None` location in `at_post_unpuppet`.

        Args:
            player (Player): This is the connecting player.
            session (Session): Session controlling the connection.

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
            player.msg("{r%s has no location and no home is set.{n" % self, session=session)

    def at_post_puppet(self):
        """
        Called just after puppeting has been completed and all
        Player<->Object links have been established.

        Note:
            You can use `self.player` and `self.sessions.get()` to get
            player and sessions at this point; the last entry in the
            list from `self.sessions.get()` is the latest Session
            puppeting this Object.

        """
        self.msg("\nYou become {c%s{n.\n" % self.name)
        self.msg(self.at_look(self.location))

        def message(obj, from_obj):
            obj.msg("%s has entered the game." % self.get_display_name(obj), from_obj=from_obj)
        self.location.for_contents(message, exclude=[self], from_obj=self)

    def at_post_unpuppet(self, player, session=None):
        """
        We stove away the character when the player goes ooc/logs off,
        otherwise the character object will remain in the room also
        after the player logged off ("headless", so to say).

        Args:
            player (Player): The player object that just disconnected
                from this object.
            session (Session): Session controlling the connection that
                just disconnected.
        """
        if not self.sessions.count():
            # only remove this char from grid if no sessions control it anymore.
            if self.location:
                def message(obj, from_obj):
                    obj.msg("%s has left the game." % self.get_display_name(obj), from_obj=from_obj)
                self.location.for_contents(message, exclude=[self], from_obj=self)
                self.db.prelogout_location = self.location
                self.location = None

    @property
    def idle_time(self):
        """
        Returns the idle time of the least idle session in seconds. If
        no sessions are connected it returns nothing.
        """
        idle = [session.cmd_last_visible for session in self.sessions.all()]
        if idle:
            return time.time() - float(max(idle))

    @property
    def connection_time(self):
        """
        Returns the maximum connection time of all connected sessions
        in seconds. Returns nothing if there are no sessions.
        """
        conn = [session.conn_time for session in self.sessions.all()]
        if conn:
            return time.time() - float(min(conn))

#
# Base Room object
#

class DefaultRoom(DefaultObject):
    """
    This is the base room object. It's just like any Object except its
    location is always `None`.
    """
    def basetype_setup(self):
        """
        Simple room setup setting locks to make sure the room
        cannot be picked up.

        """

        super(DefaultRoom, self).basetype_setup()
        self.locks.add(";".join(["get:false()",
                                 "puppet:false()"])) # would be weird to puppet a room ...
        self.location = None


#
# Default Exit command, used by the base exit object
#

class ExitCommand(command.Command):
    """
    This is a command that simply cause the caller to traverse
    the object it is attached to.

    """
    obj = None

    def func(self):
        """
        Default exit traverse if no syscommand is defined.
        """

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

    def get_extra_info(self, caller, **kwargs):
        """
        Shows a bit of information on where the exit leads.

        Args:
            caller (Object): The object (usually a character) that entered an ambiguous command.

        Returns:
            A string with identifying information to disambiguate the command, conventionally with a preceding space.
        """
        if self.obj.destination:
            return " (exit to %s)" % self.obj.destination.get_display_name(caller)
        else:
            return " (%s)" % self.obj.get_display_name(caller)

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

    exit_command = ExitCommand
    priority = 101
    # Helper classes and methods to implement the Exit. These need not
    # be overloaded unless one want to change the foundation for how
    # Exits work. See the end of the class for hook methods to overload.

    def create_exit_cmdset(self, exidbobj):
        """
        Helper function for creating an exit command set + command.

        The command of this cmdset has the same name as the Exit
        object and allows the exit to react when the player enter the
        exit's name, triggering the movement between rooms.

        Args:
            exidbobj (Object): The DefaultExit object to base the command on.

        """

        # create an exit command. We give the properties here,
        # to always trigger metaclass preparations
        cmd = self.exit_command(key=exidbobj.db_key.strip().lower(),
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
        exit_cmdset.priority = self.priority
        exit_cmdset.duplicates = True
        # add command to cmdset
        exit_cmdset.add(cmd)
        return exit_cmdset


    # Command hooks
    def basetype_setup(self):
        """
        Setup exit-security

        You should normally not need to overload this - if you do make
        sure you include all the functionality in this method.

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
        Called just before cmdsets on this object are requested by the
        command handler. If changes need to be done on the fly to the
        cmdset before passing them on to the cmdhandler, this is the
        place to do it. This is called also if the object currently
        has no cmdsets.

        Kwargs:
          force_init (bool): If `True`, force a re-build of the cmdset
            (for example to update aliases).

        """

        if "force_init" in kwargs or not self.cmdset.has_cmdset("_exitset", must_be_default=True):
            # we are resetting, or no exit-cmdset was set. Create one dynamically.
            self.cmdset.add_default(self.create_exit_cmdset(self), permanent=False)

    def at_init(self):
        """
        This is called when this objects is re-loaded from cache. When
        that happens, we make sure to remove any old _exitset cmdset
        (this most commonly occurs when renaming an existing exit)
        """
        self.cmdset.remove_default()

    def at_traverse(self, traversing_object, target_location):
        """
        This implements the actual traversal. The traverse lock has
        already been checked (in the Exit command) at this point.

        Args:
            traversing_object (Object): Object traversing us.
            target_location (Object): Where target is going.

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

    def at_failed_traverse(self, traversing_object):
        """
        Overloads the default hook to implement a simple default error message.

        Args:
            traversing_object (Object): The object that failed traversing us.

        Notes:
            Using the default exits, this hook will not be called if an
            Attribute `err_traverse` is defined - this will in that case be
            read for an error string instead.

        """
        traversing_object.msg("You cannot go there.")
