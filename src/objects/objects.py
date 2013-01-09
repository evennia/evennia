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

import datetime
from django.conf import settings
from src.typeclasses.typeclass import TypeClass
from src.commands import cmdset, command
from src.comms.models import Channel
from src.utils import logger

__all__ = ("Object", "Character", "Room", "Exit")

_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__


_CONNECT_CHANNEL = None

#
# Base class to inherit from.
#

class Object(TypeClass):
    """
    This is the base class for all in-game objects.  Inherit from this
    to create different types of objects in the game.
    """
    # __init__ is only defined here in order to present docstring to API.
    def __init__(self, dbobj):
        """
        This is the root typeclass object representing all entities
        that has and actual presence in-game. Objects generally has a
        location, can be manipulated and looked at. Most game entities
        you define should inherit from Object at some distance.
        Important subclasses of Object are that Evennia defines by
        default for you are Characters, Exits and Rooms.

        Note that all Objects and its subclasses *must* always be
        created using the ev.create_object() function. This is so the
        typeclass system can be correctly initiated behind the scenes.


        Object Typeclass API:

        * Available properties (only available on *initiated* typeclass objects)

         key (string) - name of object
         name (string)- same as key
         aliases (list of strings) - aliases to the object. Will be saved to database as AliasDB entries but returned as strings.
         dbref (int, read-only) - unique #id-number. Also "id" can be used.
         dbobj (Object, read-only) - link to database model. dbobj.typeclass points back to this class
         typeclass (Object, read-only) - this links back to this class as an identified only. Use self.swap_typeclass() to switch.
         date_created (string) - time stamp of object creation
         permissions (list of strings) - list of permission strings

         player (Player) - controlling player (will also return offline player)
         location (Object) - current location. Is None if this is a room
         home (Object) - safety start-location
         sessions (list of Sessions, read-only) - returns all sessions connected to this object
         has_player (bool, read-only)- will only return *connected* players
         contents (list of Objects, read-only) - returns all objects inside this object (including exits)
         exits (list of Objects, read-only) - returns all exits from this object, if any
         destination (Object) - only set if this object is an exit.
         is_superuser (bool, read-only) - True/False if this user is a superuser

        * Handlers available

         locks - lock-handler: use locks.add() to add new lock strings
         db - attribute-handler: store/retrieve database attributes on this self.db.myattr=val, val=self.db.myattr
         ndb - non-persistent attribute handler: same as db but does not create a database entry when storing data
         scripts - script-handler. Add new scripts to object with scripts.add()
         cmdset - cmdset-handler. Use cmdset.add() to add new cmdsets to object
         nicks - nick-handler. New nicks with nicks.add().

        * Helper methods (see src.objects.objects.py for full headers)

         search(ostring, global_search=False, global_dbref=False, attribute_name=None,
                use_nicks=False, location=None, ignore_errors=False, player=False)
         execute_cmd(raw_string)
         msg(message, from_obj=None, data=None)
         msg_contents(message, exclude=None, from_obj=None, data=None)
         move_to(destination, quiet=False, emit_to_obj=None, use_destination=True, to_none=False)
         copy(new_key=None)
         delete()
         is_typeclass(typeclass, exact=False)
         swap_typeclass(new_typeclass, clean_attributes=False, no_default=True)
         access(accessing_obj, access_type='read', default=False)
         check_permstring(permstring)

        * Hook methods

         basetype_setup()     - only called once, used for behind-the-scenes setup. Normally not modified.
         basetype_posthook_setup() - customization in basetype, after the object has been created; Normally not modified.

         at_object_creation() - only called once, when object is first created. Object customizations go here.
         at_object_delete() - called just before deleting an object. If returning False, deletion is aborted. Note that all objects
                              inside a deleted object are automatically moved to their <home>, they don't need to be removed here.

         at_init()            - called whenever typeclass is cached from memory, at least once every server restart/reload
         at_cmdset_get()      - this is called just before the command handler requests a cmdset from this object
         at_first_login()     - (player-controlled objects only) called once, the very first time user logs in.
         at_pre_login()       - (player-controlled objects only) called every time the user connects, after they have identified, before other setup
         at_post_login()      - (player-controlled objects only) called at the end of login, just before setting the player loose in the world.
         at_disconnect()      - (player-controlled objects only) called just before the user disconnects (or goes linkless)
         at_server_reload()   - called before server is reloaded
         at_server_shutdown() - called just before server is fully shut down

         at_before_move(destination)             - called just before moving object to the destination. If returns False, move is cancelled.
         announce_move_from(destination)         - called in old location, just before move, if obj.move_to() has quiet=False
         announce_move_to(source_location)       - called in new location, just after move, if obj.move_to() has quiet=False
         at_after_move(source_location)          - always called after a move has been successfully performed.
         at_object_leave(obj, target_location)   - called when an object leaves this object in any fashion
         at_object_receive(obj, source_location) - called when this object receives another object

         at_before_traverse(traversing_object)                 - (exit-objects only) called just before an object traverses this object
         at_after_traverse(traversing_object, source_location) - (exit-objects only) called just after a traversal has happened.
         at_failed_traverse(traversing_object)      - (exit-objects only) called if traversal fails and property err_traverse is not defined.

         at_msg_receive(self, msg, from_obj=None, data=None) - called when a message (via self.msg()) is sent to this obj.
                                                               If returns false, aborts send.
         at_msg_send(self, msg, to_obj=None, data=None) - called when this objects sends a message to someone via self.msg().

         return_appearance(looker) - describes this object. Used by "look" command by default
         at_desc(looker=None)      - called by 'look' whenever the appearance is requested.
         at_get(getter)            - called after object has been picked up. Does not stop pickup.
         at_drop(dropper)          - called when this object has been dropped.
         at_say(speaker, message)  - by default, called if an object inside this object speaks

         """
        super(Object, self).__init__(dbobj)

    ## methods inherited from the database object (overload them here)

    def search(self, ostring,
               global_search=False,
               global_dbref=False,
               attribute_name=None,
               use_nicks=False,
               location=None,
               ignore_errors=False,
               player=False):
        """
        Perform a standard object search in the database, handling
        multiple results and lack thereof gracefully.

        ostring: (str) The string to match object names against.
                       Obs - To find a player, append * to the
                       start of ostring.
        global_search(bool): Search all objects, not just the current
                       location/inventory
        attribute_name (string) Which attribute to match
                        (if None, uses default 'name')
        use_nicks (bool) : Use nickname replace (off by default)
        location (Object): If None, use caller's current location
        ignore_errors (bool): Don't display any error messages even
                        if there are none/multiple matches -
                        just return the result as a list.
        player (Objectt):  Don't search for an Object but a Player.
                           This will also find players that don't
                           currently have a character.

        Returns - a unique Object/Player match or None. All error
                  messages are handled by system-commands and the parser-handlers
                  specified in settings.

        Use *<string> to search for objects controlled by a specific
        player. Note that the object controlled by the player will be
        returned, not the player object itself. This also means that
        this will not find Players without a character. Use the keyword
        player=True to find player objects.

        Note - for multiple matches, the engine accepts a number
        linked to the key in order to separate the matches from
        each other without showing the dbref explicitly. Default
        syntax for this is 'N-searchword'. So for example, if there
        are three objects in the room all named 'ball', you could
        address the individual ball as '1-ball', '2-ball', '3-ball'
        etc.
        """
        return self.dbobj.search(ostring,
                                 global_search=global_search,
                                 global_dbref=global_dbref,
                                 attribute_name=attribute_name,
                                 use_nicks=use_nicks,
                                 location=location,
                                 ignore_errors=ignore_errors,
                                 player=player)

    def execute_cmd(self, raw_string):
        """
        Do something as this object. This command transparently
        lets its typeclass execute the command. Evennia also calls
        this method whenever the player sends a command on the command line.

        Argument:
        raw_string (string) - raw command input

        Returns Deferred - this is an asynchronous Twisted object that will
            not fire until the command has actually finished executing. To overload
            this one needs to attach callback functions to it, with addCallback(function).
            This function will be called with an eventual return value from the command
            execution.

            This return is not used at all by Evennia by default, but might be useful
            for coders intending to implement some sort of nested command structure.
        """
        return self.dbobj.execute_cmd(raw_string)

    def msg(self, message, from_obj=None, data=None):
        """
        Emits something to any sessions attached to the object.

        message (str): The message to send
        from_obj (obj): object that is sending.
        data (object): an optional data object that may or may not
                       be used by the protocol.
        """
        self.dbobj.msg(message, from_obj=from_obj, data=data)

    def msg_contents(self, message, exclude=None, from_obj=None, data=None):
        """
        Emits something to all objects inside an object.

        exclude is a list of objects not to send to. See self.msg() for more info.
        """
        self.dbobj.msg_contents(message, exclude=exclude, from_obj=from_obj, data=data)

    def move_to(self, destination, quiet=False,
                emit_to_obj=None, use_destination=True, to_none=False):
        """
        Moves this object to a new location. Note that if <destination> is an
        exit object (i.e. it has "destination"!=None), the move_to will
        happen to this destination and -not- into the exit object itself, unless
        use_destination=False. Note that no lock checks are done by this function,
        such things are assumed to have been handled before calling move_to.

        destination: (Object) Reference to the object to move to. This
                     can also be an exit object, in which case the destination
                     property is used as destination.
        quiet:  (bool)    If true, don't emit left/arrived messages.
        emit_to_obj: (Object) object to receive error messages
        use_destination (bool): Default is for objects to use the "destination" property
                              of destinations as the target to move to. Turning off this
                              keyword allows objects to move "inside" exit objects.
        to_none - allow destination to be None. Note that no hooks are run when moving
                      to a None location. If you want to run hooks, run them manually.
        Returns True/False depending on if there were problems with the move. This method
                may also return various error messages to the emit_to_obj.

        """
        return self.dbobj.move_to(destination, quiet=quiet,
                                  emit_to_obj=emit_to_obj, use_destination=use_destination)

    def copy(self, new_key=None):
        """
        Makes an identical copy of this object. If you want to customize the copy by
        changing some settings, use ObjectDB.object.copy_object() directly.

        new_key (string) - new key/name of copied object. If new_key is not specified, the copy will be named
                           <old_key>_copy by default.
        Returns: Object (copy of this one)
        """
        return self.dbobj.copy(new_key=new_key)

    def delete(self):
        """
        Deletes this object.
        Before deletion, this method makes sure to move all contained
        objects to their respective home locations, as well as clean
        up all exits to/from the object.

        Returns: boolean True if deletion succeded, False if there
                 were errors during deletion or deletion otherwise
                 failed.
        """
        return self.dbobj.delete()


    # methods inherited from the typeclass system

    def is_typeclass(self, typeclass, exact=False):
        """
        Returns true if this object has this type
          OR has a typeclass which is an subclass of
          the given typeclass.

        typeclass - can be a class object or the
                python path to such an object to match against.

        exact - returns true only if the object's
               type is exactly this typeclass, ignoring
               parents.

        Returns: Boolean
        """
        return self.dbobj.is_typeclass(typeclass, exact=exact)

    def swap_typeclass(self, new_typeclass, clean_attributes=False, no_default=True):
        """
        This performs an in-situ swap of the typeclass. This means
        that in-game, this object will suddenly be something else.
        Player will not be affected. To 'move' a player to a different
        object entirely (while retaining this object's type), use
        self.player.swap_object().

        Note that this might be an error prone operation if the
        old/new typeclass was heavily customized - your code
        might expect one and not the other, so be careful to
        bug test your code if using this feature! Often its easiest
        to create a new object and just swap the player over to
        that one instead.

        Arguments:
        new_typeclass (path/classobj) - type to switch to
        clean_attributes (bool/list) - will delete all attributes
                           stored on this object (but not any
                           of the database fields such as name or
                           location). You can't get attributes back,
                           but this is often the safest bet to make
                           sure nothing in the new typeclass clashes
                           with the old one. If you supply a list,
                           only those named attributes will be cleared.
        no_default - if this is active, the swapper will not allow for
                     swapping to a default typeclass in case the given
                     one fails for some reason. Instead the old one
                     will be preserved.
        Returns:
          boolean True/False depending on if the swap worked or not.


        """
        return self.dbobj.swap_typeclass(new_typeclass, clean_attributes=clean_attributes, no_default=no_default)

    def access(self, accessing_obj, access_type='read', default=False):
        """
        Determines if another object has permission to access this object in whatever way.

          accessing_obj (Object)- object trying to access this one
          access_type (string) - type of access sought
          default (bool) - what to return if no lock of access_type was found

        This function will call at_access_success or at_access_failure depending on the
        outcome of the access check.

        """
        if self.dbobj.access(accessing_obj, access_type=access_type, default=default):
            self.at_access_success(accessing_obj, access_type)
            return True
        else:
            self.at_access_failure(accessing_obj, access_type)
            return False

    def check_permstring(self, permstring):
        """
        This explicitly checks the given string against this object's
        'permissions' property without involving any locks.

        permstring (string) - permission string that need to match a permission on the object.
                              (example: 'Builders')
        """
        return self.dbobj.check_permstring(permstring)


    def __eq__(self, other):
        """
        Checks for equality against an id string or another object or user.

        This has be located at this level, having it in the
        parent doesn't work.
        """
        try:
                return _GA(_GA(self, "dbobj"),"dbid") == _GA(_GA(other,"dbobj"),"dbid")
        except AttributeError:
           # compare players instead
            try:
                return _GA(_GA(_GA(self, "dbobj"),"player"),"uid") == _GA(_GA(other, "player"),"uid")
            except AttributeError:
                return False

    ## hooks called by the game engine


    def basetype_setup(self):
        """
        This sets up the default properties of an Object,
        just before the more general at_object_creation.

        You normally don't need to change this unless you change some fundamental
        things like names of permission groups.
        """
        # the default security setup fallback for a generic
        # object. Overload in child for a custom setup. Also creation
        # commands may set this (create an item and you should be its
        # controller, for example)

        dbref = self.dbobj.dbref
        self.locks.add(";".join(["control:perm(Immortals)",  # edit locks/permissions, delete
                                 "examine:perm(Builders)",   # examine properties
                                 "view:all()",               # look at object (visibility)
                                 "edit:perm(Wizards)",       # edit properties/attributes
                                 "delete:perm(Wizards)",     # delete object
                                 "get:all()",                # pick up object
                                 "call:true()",              # allow to call commands on this object
                                 "puppet:id(%s) or perm(Immortals) or pperm(Immortals)" % dbref])) # restricts puppeting of this object

    def basetype_posthook_setup(self):
        """
        Called once, after basetype_setup and at_object_creation. This should generally not be overloaded unless
        you are redefining how a room/exit/object works. It allows for basetype-like setup
        after the object is created. An example of this is EXITs, who need to know keys, aliases, locks
        etc to set up their exit-cmdsets.
        """
        pass

    def at_object_creation(self):
        """
        Called once, when this object is first created.
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

    def at_cmdset_get(self):
        """
        Called just before cmdsets on this object are requested by the
        command handler. If changes need to be done on the fly to the cmdset
        before passing them on to the cmdhandler, this is the place to do it.
        This is called also if the object currently have no cmdsets.
        """
        pass

    def at_first_login(self):
        """
        Only called once, the very first
        time the user logs in.
        """
        pass
    def at_pre_login(self):
        """
        Called every time the user logs in,
        before they are actually logged in.
        """
        pass
    def at_post_login(self):
        """
        Called at the end of the login
        process, just before letting
        them loose.
        """
        pass

    def at_disconnect(self):
        """
        Called just before user
        is disconnected.
        """
        pass

    def at_server_reload(self):
        """
        This hook is called whenever the server is shutting down for restart/reboot.
        If you want to, for example, save non-persistent properties across a restart,
        this is the place to do it.
        """
        pass

    def at_server_shutdown(self):
        """
        This hook is called whenever the server is shutting down fully (i.e. not for
        a restart).
        """
        pass

    def at_access_success(self, accessing_obj, access_type):
        """
        This hook is called whenever accessing_obj succeed a lock check of type access_type
        on this object, for whatever reason. The return value of this hook is not used,
        the lock will still pass regardless of what this hook does (use lockstring/funcs to tweak
        the lock result).
        """
        pass

    def at_access_failure(self, accessing_obj, access_type):
        """
        This hook is called whenever accessing_obj fails a lock check of type access_type
        on this object, for whatever reason. The return value of this hook is not used, the
        lock will still fail regardless of what this hook does (use lockstring/funcs to tweak the
        lock result).
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

        source_location - where we came from
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
        only implemented by Exit objects. If it returns False (usually because move_to
        returned False), at_after_traverse below should not be called and
        instead at_failed_traverse should be called.
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

    def at_msg_receive(self, msg, from_obj=None, data=None):
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

    def at_msg_send(self, msg, to_obj=None, data=None):
        """
        This is a hook that is called when /this/ object
        sends a message to another object with obj.msg()
        while also specifying that it is the one sending.

        Note that this method is executed on the object
        passed along with the msg() function (i.e. using
        obj.msg(msg, caller) will then launch caller.at_msg())
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
        visible = (con for con in self.contents if con != pobject and con.access(pobject, "view"))
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
        string = "{c%s{n" % self.key
        desc = self.db.desc
        if desc:
            string += "\n %s" % desc
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
# Base Player object
#

class Character(Object):
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
        super(Character, self).basetype_setup()
        self.locks.add(";".join(["get:false()",  # noone can pick up the character
                                 "call:false()"])) # no commands can be called on character from outside
        # add the default cmdset
        self.cmdset.add_default(settings.CMDSET_DEFAULT, permanent=True)

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

    def at_disconnect(self):
        """
        We stove away the character when logging off, otherwise the character object will
        remain in the room also after the player logged off ("headless", so to say).
        """
        global _CONNECT_CHANNEL
        if not _CONNECT_CHANNEL:
            try:
                _CONNECT_CHANNEL = Channel.objects.filter(db_key=settings.CHANNEL_CONNECTINFO[0])[0]
            except Exception, e:
                logger.log_trace()

        if self.location: # have to check, in case of multiple connections closing
            self.location.msg_contents("%s has left the game." % self.name, exclude=[self])
            self.db.prelogout_location = self.location
            self.location = None
        if _CONNECT_CHANNEL:
            now = datetime.datetime.now()
            now = "%02i-%02i-%02i(%02i:%02i)" % (now.year, now.month, now.day, now.hour, now.minute)
            _CONNECT_CHANNEL.tempmsg("[%s, %s]: {R%s disconnected{n" % (_CONNECT_CHANNEL.key, now, self.key))

    def at_post_login(self):
        """
        This recovers the character again after having been "stoved away" at disconnect.
        """
        global _CONNECT_CHANNEL
        if not _CONNECT_CHANNEL:
            try:
                _CONNECT_CHANNEL = Channel.objects.filter(db_key=settings.CHANNEL_CONNECTINFO[0])[0]
            except Exception, e:
                logger.log_trace()
        if self.db.prelogout_location:
            # try to recover
            self.location = self.db.prelogout_location
        if self.location == None:
            # make sure location is never None (home should always exist)
            self.location = self.home
        # save location again to be sure
        self.db.prelogout_location = self.location

        self.location.msg_contents("%s has entered the game." % self.name, exclude=[self])
        self.location.at_object_receive(self, self.location)
        # call look
        self.execute_cmd("look")
        # send to connect channel, if available
        if _CONNECT_CHANNEL:
            now = datetime.datetime.now()
            now = "%02i-%02i-%02i(%02i:%02i)" % (now.year, now.month, now.day, now.hour, now.minute)
            _CONNECT_CHANNEL.tempmsg("[%s, %s]: {G%s connected{n" % (_CONNECT_CHANNEL.key, now, self.key))


#
# Base Room object
#

class Room(Object):
    """
    This is the base room object. It's basically
    like any Object except its location is None.
    """
    def basetype_setup(self):
        """
        Simple setup, shown as an example
        (since default is None anyway)

        """

        super(Room, self).basetype_setup()
        self.locks.add(";".join(["get:false()",
                                 "puppet:false()"])) # would be weird to puppet a room ...
        self.location = None

#
# Exits
#

class Exit(Object):
    """
    This is the base exit object - it connects a location to
    another. This is done by the exit assigning a "command" on itself
    with the same name as the exit object (to do this we need to
    remember to re-create the command when the object is cached since it must be
    created dynamically depending on what the exit is called). This
    command (which has a high priority) will thus allow us to traverse exits
    simply by giving the exit-object's name on its own.

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
            locks = "cmd:all()" # should always be set to this.
            obj = None
            arg_regex=r"\s.*?|$"
            is_exit = True      # this helps cmdhandler disable exits in cmdsets with no_exits=True.

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

        # create an exit command.
        cmd = ExitCommand()
        cmd.key = exidbobj.db_key.strip().lower()
        cmd.obj = exidbobj
        cmd.aliases = exidbobj.aliases
        cmd.locks = str(exidbobj.locks)
        cmd.destination = exidbobj.db_destination
        cmd.auto_help = False
        # create a cmdset
        exit_cmdset = cmdset.CmdSet(None)
        exit_cmdset.key = '_exitset'
        exit_cmdset.priority = 9
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
        super(Exit, self).basetype_setup()

        # setting default locks (overload these in at_object_creation()
        self.locks.add(";".join(["puppet:false()", # would be weird to puppet an exit ...
                                 "traverse:all()", # who can pass through exit by default
                                 "get:false()"]))   # noone can pick up the exit

        # an exit should have a destination (this is replaced at creation time)
        if self.dbobj.location:
            self.destination = self.dbobj.location

    def at_cmdset_get(self):
        """
        Called when the cmdset is requested from this object, just before the cmdset is
        actually extracted. If no Exit-cmdset is cached, create it now.
        """

        if self.ndb.exit_reset or not self.cmdset.has_cmdset("_exitset", must_be_default=True):
            # we are resetting, or no exit-cmdset was set. Create one dynamically.
            self.cmdset.add_default(self.create_exit_cmdset(self.dbobj), permanent=False)
            self.ndb.exit_reset = False

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
        reason. It will not be called if the attribute "err_traverse" is defined,
        that attribute will then be echoed back instead as a convenient shortcut.

        (See also hooks at_before_traverse and at_after_traverse).
        """
        traversing_object.msg("You cannot go there.")
