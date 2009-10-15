"""
An example script parent for a nice red button object. It has
custom commands defined on itself that are only useful in relation to this
particular object. See example.py in gamesrc/commands for more info
on the pluggable command system. 

Assuming this script remains in gamesrc/parents/examples, create an object
of this type using @create button:examples.red_button

This file also shows the use of the Event system to make the button
send a message to the players at regular intervals. Note that if you create a
test button you must drop it before you will see its messages!

"""
from game.gamesrc.parents.base.basicobject import BasicObject

# you have to import the event definition(s) from somewhere
# covered by @reload, and this is as good a place as any.
# Doing this will start the event ticking.

import game.gamesrc.events.example 

#
# commands for using the button object. These are added to 
# the object in the class_factory function at the
# bottom of this module.
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
# Definition of the object itself
#
    
class RedButton(BasicObject):
    """
    This class describes an evil red button.
    It will use the event definition in
    game/gamesrc/events/example.py to blink
    at regular intervals until the lightbulb
    breaks. 
    """
    def at_object_creation(self):
        """
        This function is called when object is created. Use this
        preferably over __init__.
        """        
        #get stored object related to this class
        obj = self.scripted_obj
        
        obj.set_attribute('desc', "This is your standard big red button.")
        obj.set_attribute("breakpoint", 10)
        obj.set_attribute("count", 0)
        
    def blink(self):
        """
        If the event system is active, it will regularly call this
        function to make the button blink. Note the use of attributes
        to store the variable count and breakpoint in a persistent
        way.
        """
        obj = self.scripted_obj
        
        try:            
            count = int(obj.get_attribute_value("count"))
            breakpoint = int(obj.get_attribute_value("breakpoint"))        
        except TypeError:
            return 

        if count <= breakpoint:
            if int(count) == int(breakpoint):            
                string = "The button flashes, then goes dark. "
                string += "Looks like the lamp just broke."
            else: 
                string = "The red button flashes, demanding your attention."
            count += 1            
            obj.set_attribute("count", count)            
            obj.get_location().emit_to_contents(string)

def class_factory(source_obj):
    """
    This method is called by any script you retrieve (via the scripthandler). It
    creates an instance of the class and returns it transparently. 
    
    source_obj: (Object) A reference to the object being scripted (the child).

    This is a good place for adding new commands to the button since this is
    where it is actually instantiated. 
    """
    button = RedButton(source_obj)  
    # add the object-based commands to the button
    button.command_table.add_command("pushbutton", cmd_push_button)
    button.command_table.add_command("pullbutton", cmd_pull_button)
    return button
