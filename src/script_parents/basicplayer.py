"""
This is the basic Evennia-standard player parent. 

NOTE: This file should NOT be directly modified. Sub-class the BasicPlayer
class in game/gamesrc/parents/base/basicplayer.py and change the 
SCRIPT_DEFAULT_PLAYER variable in settings.py to point to the new class. 
"""
import time
from src import comsys

class EvenniaBasicPlayer(object):
    def at_player_creation(self):
        """
        This is triggered after a new User and accompanying Object is created.
        By the time this is triggered, the player is ready to go but not
        logged in.
        """
        pass
    
    def at_pre_login(self, session):
        """
        Everything done here takes place before the player is actually
        'logged in', in a sense that they're not ready to send logged in
        commands or receive communication.
        """
        pobject = self.scripted_obj
        
        # Load the player's channels from their JSON __CHANLIST attribute.
        comsys.load_object_channels(pobject)
        pobject.set_attribute("Last", "%s" % (time.strftime("%a %b %d %H:%M:%S %Y", time.localtime()),))
        pobject.set_attribute("Lastsite", "%s" % (session.address[0],))
        pobject.set_flag("CONNECTED", True)
        
    def at_post_login(self, session):
        """
        The user is now logged in. This is what happens right after the moment
        they are 'connected'.
        """
        pobject = self.scripted_obj
        
        pobject.emit_to("You are now logged in as %s." % (pobject.name,))
        pobject.get_location().emit_to_contents("%s has connected." % 
            (pobject.get_name(show_dbref=False),), exclude=pobject)
        pobject.execute_cmd("look")
