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

class Player(TypeClass):
    """
    Base typeclass for all Players.     
    """
    
    def at_player_creation(self):
        """
        This is called once, the very first time
        the player is created (i.e. first time they
        register with the game). It's a good place
        to store attributes all players should have,
        like configuration values etc. 
        """        
        # the text encoding to use.
        self.db.encoding = "utf-8"
        pass 

    # Note that the hooks below also exist
    # in the character object's typeclass. You
    # can often ignore these and rely on the
    # character ones instead, unless you
    # are implementing a multi-character game
    # and have some things that should be done
    # regardless of which character is currently
    # connected to this player. 

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
