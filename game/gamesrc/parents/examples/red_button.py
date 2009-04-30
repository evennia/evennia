"""
An example script parent for a nice red button object. It has
custom commands defined on itself that are only useful in relation to this
particular object. See example.py in gamesrc/commands for more info
on the pluggable command system. 

Assuming this script remains in gamesrc/parents/examples, create an object
of this type using @create button=examples.red_button

This file also shows the use of the Event system to make the button
send a message to the players at regular intervals. Note that if you create a
test button you must drop it before you will see its messages!

"""
from game.gamesrc.parents.base.basicobject import BasicObject

#you have to import the event definition(s) from somewhere covered by @reload,
# - this is as good a place as any.
import game.gamesrc.events.example 

import game.gamesrc.events.eventSystem

#
#commands on the button object
#

def cmd_push_button(command):
    """

    This is a simple command that handles a user pressing the
    button by returning a message.
    """    
    retval = "There is a loud bang: BOOOM!"
    command.source_object.emit_to(retval)

def cmd_pull_button(command):
    """
    An example of a second defined command (for those who
    don't know how a button works ... ;) )
    """
    retval = "A button is meant to be pushed, not pulled!"
    command.source_object.emit_to(retval)
                        
#
#The object itself
#
    
class RedButton(BasicObject):

    def __init__(self, scripted_obj, *args, **kwargs):
        """
        This is called when class_factory() instantiates a temporary instance
        of the script parent. This is typically not something you want to
        mess with much.
        """
        # Calling the super class' __init__ is critical! Never forget to do
        # this or everything else from here on out will fail.
        super(RedButton, self).__init__(scripted_obj, args, kwargs)
        # Add the commands to the object's command table (this is about
        #the only thing you should use the __init__ for).
        self.command_table.add_command("pushbutton", cmd_push_button)
        self.command_table.add_command("pullbutton", cmd_pull_button)


    def at_object_creation(self):
        """
        This function is called when object is created. Use this
        preferably over __init__.

        In this case all we do is add the commandtable
        to the object's own command_table variable; this makes
        the commands we've added to COMMAND_TABLE available to
        the user whenever the object is around.
        """
        #get stored object related to this class
        obj = self.scripted_obj
        
        obj.set_description("This is your standard big red button.")
        obj.set_attribute("breakpoint", 10)
        obj.set_attribute("count", 0)
        
    def blink(self):
        """If the event system is active, it will regularly call this function to make
        the button blink. Note the use of attributes to store the variable count and
        breakpoint in a persistent way."""
        obj = self.scripted_obj
        
        try:            
            count = int(obj.get_attribute_value("count"))
            breakpoint = int(obj.get_attribute_value("breakpoint"))        
        except TypeError:
            return 

        if count <= breakpoint:
            if int(count) == int(breakpoint):            
                s = "The button flashes, then goes dark. "
                s += "Looks like the lamp just broke."
            else: 
                s = "The red button flashes, demanding your attention."
            count += 1            
            obj.set_attribute("count",count)            
            obj.get_location().emit_to_contents(s)
    
    def update_tick(self):                
        self.blink()


def class_factory(source_obj):
    """
    This method is called by any script you retrieve (via the scripthandler). It
    creates an instance of the class and returns it transparently. 
    
    source_obj: (Object) A reference to the object being scripted (the child).
    """
    return RedButton(source_obj)  

