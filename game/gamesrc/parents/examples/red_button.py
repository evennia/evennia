"""
An example script parent for a 
"""
from game.gamesrc.parents.base.basicobject import BasicObject

def cmd_push_button(command):
    """
    An example command to show how the pluggable command system works.
    """
    # By building one big string and passing it at once, we cut down on a lot
    # of emit_to() calls, which is generally a good idea.
    retval = "You have pushed the button on: %s" % (command.scripted_obj.get_name())
    command.source_object.emit_to(retval)

class RedButton(BasicObject):
    def __init__(self, scripted_obj, *args, **kwargs):
        """
        
        """
        # Calling the super classes __init__ is critical! Never forget to do
        # this or everything else from here on out will fail.
        super(RedButton, self).__init__(scripted_obj, args, kwargs)
        # Add the command to the object's command table.
        self.command_table.add_command("pushbutton", cmd_push_button)

def class_factory(source_obj):
    """
    This method is called any script you retrieve (via the scripthandler). It
    creates an instance of the class and returns it transparently. 
    
    source_obj: (Object) A reference to the object being scripted (the child).
    """
    return RedButton(source_obj)  