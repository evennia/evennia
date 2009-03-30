"""
This is the base object type/interface that all parents are derived from by
default. Each object type sub-classes this class and over-rides methods as
needed. 

NOTE: This file should NOT be directly modified. Sub-class the BasicObject
class in game/gamesrc/parents/base/basicobject.py and change the 
SCRIPT_DEFAULT_OBJECT variable in settings.py to point to the new class. 
"""
from src import ansi

class EvenniaBasicObject(object):
    def __init__(self, source_obj, *args, **kwargs):
        """
        Get our ducks in a row.
        
        source_obj: (Object) A reference to the object being scripted (the child).
        """
        self.source_obj = source_obj
        
    def a_desc(self, pobject):
        """
        Perform this action when someone uses the LOOK command on the object.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        # Un-comment the line below for an example
        #print "SCRIPT TEST: %s looked at %s." % (pobject, self.source_obj)
        pass

    def return_appearance(self, pobject):
        """
        Returns a string representation of an object's appearance when LOOKed at.
        
        values: 
            * pobject: (Object) The object requesting the action.
        """
        # This is the object being looked at.
        target_obj = self.source_obj
        # See if the envoker sees dbref numbers.        
        show_dbrefs = pobject.sees_dbrefs()
            
        description = target_obj.get_description()
        if description is not None:
            retval = "%s\r\n%s" % (
                target_obj.get_name(show_dbref=show_dbrefs),
                target_obj.get_description(),
            )
        else:
            retval = "%s" % (
                target_obj.get_name(show_dbref=show_dbrefs),
            )

        con_players = []
        con_things = []
        con_exits = []
        
        for obj in target_obj.get_contents():
            if obj.is_player():
                if obj != pobject and obj.is_connected_plr():
                    con_players.append(obj)
            elif obj.is_exit():
                con_exits.append(obj)
            else:
                con_things.append(obj)
        
        if not con_players == []:
            retval += "\n\r%sPlayers:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],)
            for player in con_players:
                retval +='\n\r%s' %(player.get_name(show_dbref=show_dbrefs),)
        if not con_things == []:
            retval += "\n\r%sContents:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],)
            for thing in con_things:
                retval += '\n\r%s' %(thing.get_name(show_dbref=show_dbrefs),)
        if not con_exits == []:
            retval += "\n\r%sExits:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],)
            for exit in con_exits:
                retval += '\n\r%s' %(exit.get_name(show_dbref=show_dbrefs),)

        return retval

    def a_get(self, pobject):
        """
        Perform this action when someone uses the GET command on the object.
        
        values: 
            * pobject: (Object) The object requesting the action.
        """
        # Un-comment the line below for an example
        #print "SCRIPT TEST: %s got %s." % (pobject, self.source_obj)
        pass

    def a_drop(self, pobject):
        """
        Perform this action when someone uses the GET command on the object.
        
        values:
            * pobject: (Object) The object requesting the action.
        """
        # Un-comment the line below for an example
        #print "SCRIPT TEST: %s dropped %s." % (pobject, self.source_obj)
        pass

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
