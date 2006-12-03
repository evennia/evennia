from apps.objects.models import Object
import functions_db

class StaffCommands:
   """
   Restricted staff commands.
   """
   def do_dig(self, cdat):      
      """
      Digs a new room out.
      """
      session = cdat['session']
      uinput= cdat['uinput']
      roomname = ''.join(uinput[1:])
      
      if roomname == '':
         session.msg("You must supply a room name!")
      else:
         newroom = Object()
         newroom.name = roomname
         newroom.type = "Room"
         
   def do_nextfree(self, cdat):
      """
      Returns the next free object number.
      """
      session = cdat['session']
      server = cdat['server']
      
      nextfree = server.get_nextfree_dbnum()
      retval = "Next free object number: %s" % (nextfree,)
      
      session.msg(retval)
      
   def do_teleport(self, cdat):
      """
      Teleports an object somewhere.
      """
      session = cdat['session']
      pobject = session.pobject
      server = cdat['server']
      args = cdat['uinput']['splitted'][1:]
      
      if len(args) == 0:
         session.msg("Teleport where/what?")
         return
         
      eq_args = args[0].split('=')
         
      # If we have more than one entry in our '=' delimited argument list,
      # then we're doing a @tel <victim>=<location>. If not, we're doing
      # a direct teleport, @tel <destination>.
      if len(eq_args) > 1:
         session.msg("Equal sign present.")
      else:
         session.msg("No equal sign, direct tport.")
         results = functions_db.local_and_global_search(pobject, ''.join(args))
         
         if len(results) > 1:
            session.msg("More than one match found (please narrow target):")
            for result in results:
               session.msg(" %s(#%s)" % (result.name, result.id,))
         elif len(results) == 0:
            session.msg("I don't see that here.")
         else:
            session.msg("Teleported.")
            pobject.move_to(results[0])
            #GenCommands.do_look(cdat)
            
      #session.msg("Args: %s\n\rEqargs: %s" % (args, eq_args,))

   def do_find(self, cdat):
      """
      Searches for an object of a particular name.
      """
      session = cdat['session']
      server = cdat['server']
      searchstring = ''.join(cdat['uinput']['splitted'][1:])
      
      if searchstring == '':
         session.msg("No search pattern given.")
         return
      
      memory_based = True
      
      if memory_based:
         results = functions_db.list_search_object_namestr(server.object_list.values(), searchstring)

         if len(results) > 0:
            session.msg("Name matches for: %s" % (searchstring,))
            for result in results:
               session.msg(" %s(#%s)" % (result.name, result.id,))
            session.msg("%d matches returned." % (len(results),))
         else:
            session.msg("No name matches found for: %s" % (searchstring,))
