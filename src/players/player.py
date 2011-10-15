"""
Typeclass for Player objects

Note that this object is primarily intended to 
store OOC information, not game info! This 
object represents the actual user (not their
character) and has NO actual precence in the 
game world (this is handled by the associated
character object, so you should customize that
instead for most things).

"""
from src.typeclasses.typeclass import TypeClass

from settings import CMDSET_OOC

class Player(TypeClass):
    """
    Base typeclass for all Players.     
    """
    
    def basetype_setup(self):
        """
        This sets up the basic properties for a player. 
        Overload this with at_player_creation rather than
        changing this method. 
        
        """
        # the text encoding to use.
        self.db.encoding = "utf-8"
        
        # A basic security setup
        self.locks.add("examine:perm(Wizards)")
        self.locks.add("edit:perm(Wizards)")
        self.locks.add("delete:perm(Wizards)")
        self.locks.add("boot:perm(Wizards)")        
        self.locks.add("msg:all()")

        # The ooc player cmdset 
        self.cmdset.add_default(CMDSET_OOC, permanent=True)
        self.cmdset.outside_access = False 
    
    def at_player_creation(self):
        """
        This is called once, the very first time
        the player is created (i.e. first time they
        register with the game). It's a good place
        to store attributes all players should have,
        like configuration values etc. 
        """        
        pass
 

    def at_init(self):
        """
        This is always called whenever this object is initiated --
        that is, whenever it its typeclass is cached from memory. This
        happens on-demand first time the object is used or activated
        in some way after being created but also after each server
        restart or reload. In the case of player objects, this usually
        happens the moment the player logs in or reconnects after a
        reload.
        """
        pass 

    # Note that the hooks below also exist
    # in the character object's typeclass. You
    # can often ignore these and rely on the
    # character ones instead, unless you
    # are implementing a multi-character game
    # and have some things that should be done
    # regardless of which character is currently
    # connected to this player. 

    def at_cmdset_get(self):
        """
        Called just before cmdsets on this player are requested by the
        command handler. If changes need to be done on the fly to the cmdset
        before passing them on to the cmdhandler, this is the place to do it.
        This is called also if the player currently have no cmdsets.
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
    def at_disconnect(self, reason=None):
        """
        Called just before user
        is disconnected.
        """
        pass

    def at_message_receive(self, message, from_obj=None):
        """
        Called when any text is emitted to this
        object. If it returns False, no text
        will be sent automatically. 
        """
        return True 

    def at_message_send(self, message, to_object):
        """
        Called whenever this object tries to send text
        to another object. Only called if the object supplied
        itself as a sender in the msg() call. 
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
