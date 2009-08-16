"""
Simple example of a custom modified object, derived from the base object. 

If you want to make this your new default object type, move this into
gamesrc/parents and set SCRIPT_DEFAULT_OBJECT = 'custom_basicobject'
in game/settings.py. 

Generally, if you want to conveniently set future objects to inherit from this
script parent, this files and others like it need to be
located under the game/gamesrc/parent directory. 
"""
from game.gamesrc.parents.base.basicobject import BasicObject

class CustomBasicObject(BasicObject):
    
    def at_object_creation(self):
        """
        This function is called whenever the object is created. Use
        this instead of __init__ to set start attributes etc on a
        particular object type.
        """
        
        #Set an "sdesc" (short description) attribute on object,
        #defaulting to its given name

        #get the stored object related to this class
        obj = self.scripted_obj 

        #find out the object's name
        name = obj.get_name(fullname=False,
                            show_dbref=False,
                            show_flags=False)
        #assign the name to the new attribute
        obj.set_attribute('sdesc',name)

    def at_object_destruction(self, pobject=None):
        """
        This is triggered when an object is about to be destroyed via
        @destroy ONLY. If an object is deleted via delete(), it is assumed
        that this method is to be skipped.
        
        values:
            * pobject: (Object) The object requesting the action.
        """        
        pass

    def at_before_move(self, target_location):
        """
        This hook is called just before the object is moved.
        Input:
          target_location (obj): The location the player is about to move to.
        Return value: 
            If this function returns anything but None (no return value),
            the move is aborted. This allows for character-based move
            restrictions (not only exit locks).
        """
        pass

    def at_after_move(self):
        """
        This hook is called just after the player has been successfully moved.
        """
        pass


def class_factory(source_obj):
    """
    This method is called by any script you retrieve (via the scripthandler). It
    creates an instance of the class and returns it transparently. 
    
    source_obj: (Object) A reference to the object being scripted (the child).
    """
    return CustomBasicObject(source_obj)     
