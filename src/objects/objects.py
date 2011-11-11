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

from src.typeclasses.typeclass import TypeClass
from src.commands import cmdset, command

#
# Base class to inherit from. 
#

class Object(TypeClass):
    """
    This is the base class for all in-game objects.
    Inherit from this to create different types of
    objects in the game. 
    """    

    def __eq__(self, other):
        """
        This has be located at this level, having it in the
        parent doesn't work.
        """
        
        result = other and other.id == self.id
        try:
            uresult = other and (other.user.id == self.user.id) 
        except AttributeError:
            uresult = False 
        return result or uresult 

    # hooks called by the game engine

    def basetype_setup(self):
        """
        This sets up the default properties of an Object,
        just before the more general at_object_creation.

        Don't change this, instead edit at_object_creation() to
        overload the defaults (it is called after this one). 
        """
        # the default security setup fallback for a generic
        # object. Overload in child for a custom setup. Also creation
        # commands may set this (create an item and you should be its
        # controller, for example)

        dbref = self.dbobj.dbref

        self.locks.add("control:id(%s) or perm(Immortals)" % dbref)  # edit locks/permissions, delete
        self.locks.add("examine:perm(Builders)")  # examine properties 
        self.locks.add("view:all()") # look at object (visibility)
        self.locks.add("edit:perm(Wizards)")   # edit properties/attributes 
        self.locks.add("delete:perm(Wizards)") # delete object 
        self.locks.add("get:all()")   # pick up object
        self.locks.add("call:true()") # allow to call commands on this object
        self.locks.add("puppet:id(%s) or perm(Immortals) or pperm(Immortals)" % dbref) # restricts puppeting of this object 

    def at_object_creation(self):
        """
        Called once, when this object is first
        created. 
        """ 
        pass

    def at_init(self):
        """        
        This is always called whenever this object is initiated --
        that is, whenever it its typeclass is cached from memory. This
        happens on-demand first time the object is used or activated
        in some way after being created but also after each server
        restart or reload. 
        """
        pass     

    def basetype_posthook_setup(self):
        """
        Called once, after basetype_setup and at_object_creation. This should generally not be overloaded unless
        you are redefining how a room/exit/object works. It allows for basetype-like setup
        after the object is created. An example of this is EXITs, who need to know keys, aliases, locks
        etc to set up their exit-cmdsets.
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

    # hooks called by the default cmdset. 
    
    def return_appearance(self, pobject):
        """
        This is a convenient hook for a 'look'
        command to call. 
        """
        if not pobject:
            return 
        string = "{c%s{n" % self.name
        desc = self.attr("desc")
        if desc:
            string += "\n %s" % desc
        exits = [] 
        users = []
        things = []
        for content in [con for con in self.contents if con.access(pobject, 'view')]:
            if content == pobject:
                continue 
            name = content.name
            if content.destination:
                exits.append(name)
            elif content.has_player:
                users.append(name)
            else:
                things.append(name)
        if exits:
            string += "\n{wExits:{n " + ", ".join(exits)
        if users or things:
            string += "\n{wYou see: {n"
            if users: 
                string += "{c" + ", ".join(users) + "{n "
            if things: 
                string += ", ".join(things)            
        return string

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

        msg = the message received
        from_obj = the one sending the message
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
        
    def at_desc(self, looker=None):
        """
        This is called whenever someone looks
        at this object. Looker is the looking
        object. 
        """
        pass
    
    def at_object_delete(self):
        """
        Called just before the database object is
        permanently delete()d from the database. If
        this method returns False, deletion is aborted. 
        """
        return True

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

        Don't change this, instead edit at_object_creation() to
        overload the defaults (it is called after this one). 
        """
        super(Character, self).basetype_setup()
        self.locks.add("get:false()") # noone can pick up the character
        self.locks.add("call:false()") # no commands can be called on character from outside       

        # add the default cmdset
        from settings import CMDSET_DEFAULT        
        self.cmdset.add_default(CMDSET_DEFAULT, permanent=True)
        # no other character should be able to call commands on the Character. 
        self.cmdset.outside_access = False 

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
        if self.location: # have to check, in case of multiple connections closing           
            self.location.msg_contents("%s has left the game." % self.name, exclude=[self])
            self.db.prelogout_location = self.location
            self.location = None 

    def at_post_login(self):
        """
        This recovers the character again after having been "stoved away" at disconnect.
        """
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

        Don't change this, instead edit at_object_creation() to
        overload the defaults (it is called after this one). 
        """

        super(Room, self).basetype_setup()
        self.locks.add("get:false();puppet:false()") # would be weird to puppet a room ...
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

            def func(self):
                "Default exit traverse if no syscommand is defined."

                if self.obj.access(self.caller, 'traverse'):
                    # we may traverse the exit. 

                    old_location = None 
                    if hasattr(self.caller, "location"):
                        old_location = self.caller.location                

                    # call pre/post hooks and move object.
                    self.obj.at_before_traverse(self.caller)
                    self.caller.move_to(self.obj.destination)            
                    self.obj.at_after_traverse(self.caller, old_location)

                else:
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

        Don't change this, instead edit at_object_creation() to
        overload the default locks (it is called after this one). 
        """
        super(Exit, self).basetype_setup()

        # setting default locks (overload these in at_object_creation()
        self.locks.add("puppet:false()") # would be weird to puppet an exit ...
        self.locks.add("traverse:all()") # who can pass through exit by default
        self.locks.add("get:false()")    # noone can pick up the exit
 
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

    def at_failed_traverse(self, traversing_object):
        """
        This is called if an object fails to traverse this object for some 
        reason. It will not be called if the attribute "err_traverse" is defined,
        that attribute will then be echoed back instead as a convenient shortcut. 

        (See also hooks at_before_traverse and at_after_traverse). 
        """
        traversing_object.msg("You cannot go there.")
