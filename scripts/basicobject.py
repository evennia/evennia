"""
This will be the base object type/interface that all scripts are derived from by
default. It will have the necessary outline for developers to sub-class and override.
"""

import ansi

class BasicObject:
   def __init__(self, source_obj):
      """
      Get our ducks in a row.
      
      source_obj: (Object) A reference to the object being scripted (the child).
      """
      self.source_obj = source_obj
      
   def a_desc(self, actor):
      """
      Perform this action when someone uses the LOOK command on the object.
      
      actor: (Object) Reference to the looker
      """
      # Un-comment the line below for an example
      #print "SCRIPT TEST: %s looked at %s." % (actor, self.source_obj)
      pass

   def return_appearance(self, values):
      target_obj = values["target_obj"]
      pobject = values["pobject"]
      retval = "\r\n%s\r\n%s" % (
         target_obj.get_name(),
         target_obj.get_description(),
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
      
      if con_players:
         retval += "\n\r%sPlayers:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],)
         for player in con_players:
            retval +='\n\r%s' %(player.get_name(),)
      if con_things:
         retval += "\n\r%sContents:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],)
         for thing in con_things:
            retval += '\n\r%s' %(thing.get_name(),)
      if con_exits:
         retval += "\n\r%sExits:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],)
         for exit in con_exits:
            retval += '\n\r%s' %(exit.get_name(),)

      return retval

   def a_get(self, actor):
      """
      Perform this action when someone uses the GET command on the object.
      
      actor: (Object) Reference to the person who got the object
      """
      # Un-comment the line below for an example
      #print "SCRIPT TEST: %s got %s." % (actor, self.source_obj)
      pass

   def a_drop(self, actor):
      """
      Perform this action when someone uses the GET command on the object.
      
      actor: (Object) Reference to the person who dropped the object
      """
      # Un-comment the line below for an example
      #print "SCRIPT TEST: %s got %s." % (actor, self.source_obj)
      pass

   def default_lock(self, actor):
      """
      This method returns a True or False boolean value to determine whether
      the actor passes the lock. This is generally used for picking up
      objects or traversing exits.
      
      actor: (Object) Reference to the person attempting an action
      """
      # Assume everyone passes the default lock by default.
      return True

   def use_lock(self, actor):
      """
      This method returns a True or False boolean value to determine whether
      the actor passes the lock. This is generally used for seeing whether
      a player can use an object or any of its commands.
      
      actor: (Object) Reference to the person attempting an action
      """
      # Assume everyone passes the use lock by default.
      return True

   def enter_lock(self, actor):
      """
      This method returns a True or False boolean value to determine whether
      the actor passes the lock. This is generally used for seeing whether
      a player can enter another object.
      
      actor: (Object) Reference to the person attempting an action
      """
      # Assume everyone passes the enter lock by default.
      return True
      
def class_factory(source_obj):
   """
   This method is called any script you retrieve (via the scripthandler). It
   creates an instance of the class and returns it transparently. I'm not
   sure how well this will scale, but we'll find out. We may need to
   re-factor this eventually.
   
   source_obj: (Object) A reference to the object being scripted (the child).
   """
   return BasicObject(source_obj)      