"""
This is the base object type/interface that all parents are derived from by
default. Each object type sub-classes this class and over-rides methods as
needed. 

NOTE: This file should NOT be directly modified. Sub-class the BasicObject
class in game/gamesrc/parents/base/basicobject.py and change the 
SCRIPT_DEFAULT_OBJECT variable in settings.py to point to the new class. 
"""
from src.cmdtable import CommandTable
from src.ansi import ANSITable

class EvenniaBasicObject(object):
    def __init__(self, scripted_obj, *args, **kwargs):
        """
        Get our ducks in a row. You should generally never override this. Note
        that this will not be called on object creation in a manner typical to
        most Python objects. This is only called when the script parent is
        cached or recalled on an object. This means that this function is not
        called until someone does something to warrant calling get_scriptlink().
        This happens very often, so nothing too intense should be done here.
        
        If you're wanting to do something on object/player creation, override
        at_object_creation() (in basicobject.py) or at_player_creation() 
        (in basicplayer.py).
        
        scripted_obj: (Object) A reference to the object being scripted (the child).
        """
        self.scripted_obj = scripted_obj
        self.command_table = CommandTable()
        
    def at_object_creation(self):
        """
        This is triggered after a new object is created and ready to go. If
        you'd like to set attributes, flags, or do anything when the object
        is created, do it here and not in __init__().
        """
        pass
    
    def at_object_destruction(self, pobject=None):
        """
        This is triggered when an object is about to be destroyed via
        @destroy ONLY. If an object is deleted via delete(), it is assumed
        that this method is to be skipped.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        # Un-comment the line below for an example
        #print "SCRIPT TEST: %s looked at %s." % (pobject, self.scripted_obj)
        pass
        
    def at_desc(self, pobject=None):
        """
        Perform this action when someone uses the LOOK command on the object.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        # Un-comment the line below for an example
        #print "SCRIPT TEST: %s looked at %s." % (pobject, self.scripted_obj)
        pass

    def at_get(self, pobject):
        """
        Perform this action when someone uses the GET command on the object.
        
        values: 
            * pobject: (Object) The object requesting the action.
        """
        # Un-comment the line below for an example
        #print "SCRIPT TEST: %s got %s." % (pobject, self.scripted_obj)
        pass

    def at_before_move(self, target_location):
        """
        This hook is called just before the object is moved.
        arg:
          target_location (obj): the place where this object is to be moved
        returns:
          if this function returns anything but None, the move is cancelled. 
        
        """
        pass

    def at_after_move(self):
        """
        This hook is called just after the object was successfully moved.
        No return values.
        """
        pass

    def at_drop(self, pobject):
        """
        Perform this action when someone uses the DROP command on the object.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        # Un-comment the line below for an example
        #print "SCRIPT TEST: %s dropped %s." % (pobject, self.scripted_obj)
        pass
    
    def return_appearance(self, pobject=None):
        """
        Returns a string representation of an object's appearance when LOOKed at.
        
        values: 
            * pobject: (Object) The object requesting the action.
        """
        # This is the object being looked at.
        target_obj = self.scripted_obj
        # See if the envoker sees dbref numbers.
        if pobject:        
            show_dbrefs = pobject.sees_dbrefs()
        else:
            show_dbrefs = False
            
        description = target_obj.get_attribute_value('desc')
        if description is not None:
            retval = "%s\r\n%s" % (
                target_obj.get_name(show_dbref=show_dbrefs),
                target_obj.get_attribute_value('desc'),
            )
        else:
            retval = "%s" % (
                target_obj.get_name(show_dbref=show_dbrefs),
            )

        # Storage for the different object types.
        con_players = []
        con_things = []
        con_exits = []
        
        for obj in target_obj.get_contents():
            if obj.is_player():
                if (obj != pobject and obj.is_connected_plr()) or pobject == None:
                    con_players.append(obj)
            elif obj.is_exit():
                con_exits.append(obj)
            else:
                con_things.append(obj)
        
        if not con_players == []:
            retval += "\n\r%sPlayers:%s" % (ANSITable.ansi["hilite"], 
                                            ANSITable.ansi["normal"])
            for player in con_players:
                retval +='\n\r%s' % (player.get_name(show_dbref=show_dbrefs),)
        if not con_things == []:
            retval += "\n\r%sContents:%s" % (ANSITable.ansi["hilite"], 
                                             ANSITable.ansi["normal"])
            for thing in con_things:
                retval += '\n\r%s' % (thing.get_name(show_dbref=show_dbrefs),)
        if not con_exits == []:
            retval += "\n\r%sExits:%s" % (ANSITable.ansi["hilite"], 
                                          ANSITable.ansi["normal"])
            for exit in con_exits:
                retval += '\n\r%s' %(exit.get_name(show_dbref=show_dbrefs),)

        return retval

    def default_lock(self, pobject):
        """
        This method returns a True or False boolean value to determine whether
        the actor passes the lock. This is generally used for picking up
        objects or traversing exits.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        # Assume everyone passes the default lock by default.
        return True

    def use_lock(self, pobject):
        """
        This method returns a True or False boolean value to determine whether
        the actor passes the lock. This is generally used for seeing whether
        a player can use an object or any of its commands.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        # Assume everyone passes the use lock by default.
        return True

    def enter_lock(self, pobject):
        """
        This method returns a True or False boolean value to determine whether
        the actor passes the lock. This is generally used for seeing whether
        a player can enter another object.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        # Assume everyone passes the enter lock by default.
        return True   
