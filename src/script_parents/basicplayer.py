"""
This is the basic Evennia-standard player parent. 

NOTE: This file should NOT be directly modified. Sub-class the BasicPlayer
class in game/gamesrc/parents/base/basicplayer.py and change the 
SCRIPT_DEFAULT_PLAYER variable in settings.py to point to the new class. 
"""
import time
from src import comsys
from src.config.models import ConfigValue

class EvenniaBasicPlayer(object):
    def at_player_creation(self):
        """
        This is triggered after a new User and accompanying Object is created.
        By the time this is triggered, the player is ready to go but not
        logged in. Note that this is different from at_object_creation(), which
        is executed before at_player_creation(). This function is only 
        triggered when the User account _and_ the Object are ready.
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

    def at_first_login(self, session):
        """
        This hook is called only *once*, when the player is created and logs
        in for first time. It is called after the user has logged in, but
        before at_post_login() is called.
        """
        pobject = self.scripted_obj
        pobject.emit_to("Welcome to %s, %s.\n\r" % (
            ConfigValue.objects.get_configvalue('site_name'), 
            pobject.get_name(show_dbref=False)))
        
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

    def at_before_move(self, target_location):
        """
        This hook is called just before the player is moved.
        Input:
          target_location (obj): The location the player is about to move to.
        Return value: 
            If this function returns anything but None (no return value),
            the move is aborted. This allows for character-based move
            restrictions (not only exit locks).
        """
        pass

    def announce_move_from(self, target_location):
        """
        Called when announcing to leave a destination. 
        target_location - the place we are about to move to
        """
        obj = self.scripted_obj
        loc = obj.get_location()
        if loc:
            loc.emit_to_contents("%s has left." % obj.get_name(), exclude=obj)
            if loc.is_player():
                loc.emit_to("%s has left your inventory." % (obj.get_name()))

    def announce_move_to(self, source_location):
        """
        Called when announcing one's arrival at a destination.
        source_location - the place we are coming from
        """
        obj = self.scripted_obj
        loc = obj.get_location()
        if loc: 
            loc.emit_to_contents("%s has arrived." % obj.get_name(),exclude=obj)
            if loc.is_player():
                loc.emit_to("%s is now in your inventory." % obj.get_name())

    def at_after_move(self):
        """
        This hook is called just after the player has been successfully moved.
        """
        pass


    def at_disconnect(self):
        """
        This is called just before the session disconnects, for whatever reason.
        """
        pobject = self.scripted_obj

        location = pobject.get_location()
        if location != None:
            location.emit_to_contents("%s has disconnected." % (pobject.get_name(show_dbref=False),), exclude=pobject)

    def default_lock(self, pobject):
        """
        This method returns a True or False boolean value to determine whether
        the actor passes the lock. This is generally used for picking up
        objects or traversing exits.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        locks = self.scripted_obj.get_attribute_value("LOCKS")
        if locks: 
            return locks.check("DefaultLock", pobject)
        else:
            return True

    def use_lock(self, pobject):
        """
        This method returns a True or False boolean value to determine whether
        the actor passes the lock. This is generally used for seeing whether
        a player can use an object or any of its commands.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        locks = self.scripted_obj.get_attribute_value("LOCKS")
        if locks: 
            return locks.check("UseLock", pobject)
        else:
            return True

    def enter_lock(self, pobject):
        """
        This method returns a True or False boolean value to determine whether
        the actor passes the lock. This is generally used for seeing whether
        a player can enter another object.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        locks = self.scripted_obj.get_attribute_value("LOCKS")
        if locks: 
            return locks.check("EnterLock", pobject)
        else:
            return True

    def visible_lock(self, pobject):
        """
        This method returns a True or False boolean value to determine whether
        the actor passes the lock. This is generally used for picking up
        objects or traversing exits.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        locks = self.scripted_obj.get_attribute_value("LOCKS")
        if locks: 
            return locks.check("VisibleLock", pobject)
        else:
            return True
    
    def lock_func(self, obj):
        """
        This is a custom function called by locks with the FuncKey key. Its
        return value should match that specified in the lock (so no true/false
        lock result is actually determined in here). Default desired return
        value is True. Also remember that the comparison in FuncKey is made
        using the string representation of the return value, since @lock can
        only define string lock criteria. 
        """
        return False
