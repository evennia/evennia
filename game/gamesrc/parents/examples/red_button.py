"""
An example script parent for a 
"""
from src.cmdtable import CommandTable
from game.gamesrc.parents.base.basicobject import BasicObject

COMMAND_TABLE = CommandTable()
def cmd_push_button(command):
    """
    An example command to show how the pluggable command system works.
    """
    # By building one big string and passing it at once, we cut down on a lot
    # of emit_to() calls, which is generally a good idea.
    retval = "Test"
    command.source_object.emit_to(retval)
# Add the command to the object's command table.
COMMAND_TABLE.add_command("push button", cmd_push_button)

class RedButton(BasicObject):
    def __init__(self, source_obj, *args, **kwargs):
        super(RedButton, self).__init__(source_obj, args, kwargs)
        self.command_table = COMMAND_TABLE

def class_factory(source_obj):
    """
    This method is called any script you retrieve (via the scripthandler). It
    creates an instance of the class and returns it transparently. 
    
    source_obj: (Object) A reference to the object being scripted (the child).
    """
    return RedButton(source_obj)  