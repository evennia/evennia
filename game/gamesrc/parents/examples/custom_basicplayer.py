"""
This is an example of customizing the basic player character object.
You will want to do this to add all sorts of custom things like
attributes, skill values, injuries and so on. 

If you want to make this the default player object for all players, move it
into gamesrc/parents and set SCRIPT_DEFAULT_PLAYER = 'custom_basicplayer'
in game/settings.py.
"""

from game.gamesrc.parents.base.basicplayer import BasicPlayer

class CustomBasicPlayer(BasicPlayer):    

    def at_player_creation(self):        
        """
        Called when player object is first created. Use this
        instead of __init__ to define any custom attributes
        all your player characters should have. 
        """
        
        #Example: Adding a default sdesc (short description)

        #get the stored object related to this class
        pobject = self.scripted_obj
        #set the attribute
        pobject.set_attribute('sdesc', 'A normal person')
        
    def at_pre_login(self, session):
        """
        Called when the player has entered the game but has not
        logged in yet.
        """
        pass
    
    def at_post_login(self, session):
        """
        This command is called after the player has logged in but
        before he is allowed to give any commands. 
        """
        #get the object linked to this class
        pobject = self.scripted_obj
        
        #find out more about our object
        name = pobject.get_name(fullname=False,
                                show_dbref=False,
                                show_flags=False)
        sdesc = pobject.get_attribute_value('sdesc')
                
        #send a greeting using our new sdesc attribute
        pobject.emit_to("You are now logged in as %s - %s." % (name, sdesc))

        #tell everyone else we're here
        pobject.get_location().emit_to_contents("%s - %s, has connected." %
                                                (name, sdesc), exclude=pobject)
        #show us our surroundings                                        
        pobject.execute_cmd("look")

    def at_move(self):
        """
        This is triggered whenever the object is moved to a new location
        (for whatever reason) using the src.objects.models.move_to() function. 
        """
        pass

                            
def class_factory(source_obj):
    """
    This method is called by any script you retrieve (via the scripthandler). It
    creates an instance of the class and returns it transparently. 
    
    source_obj: (Object) A reference to the object being scripted (the child).
    """    
    return CustomBasicPlayer(source_obj)
