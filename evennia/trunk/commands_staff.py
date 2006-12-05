from apps.objects.models import Object
import functions_db
import commands_general
import cmdhandler

"""
Restricted staff commands.
"""

def do_dig(cdat):      
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
      
def do_nextfree(cdat):
   """
   Returns the next free object number.
   """
   session = cdat['session']
   server = cdat['server']
   
   nextfree = functions_db.get_nextfree_dbnum()
   retval = "Next free object number: #%s" % (nextfree,)
   
   session.msg(retval)
   
def do_teleport(cdat):
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
   search_str = ''.join(args)
      
   # If we have more than one entry in our '=' delimited argument list,
   # then we're doing a @tel <victim>=<location>. If not, we're doing
   # a direct teleport, @tel <destination>.
   if len(eq_args) > 1:
      # Equal sign teleport.
      victim = functions_db.local_and_global_search(pobject, eq_args[0])
      destination = functions_db.local_and_global_search(pobject, eq_args[1])
      
      if len(victim) == 0:
         session.msg("I can't find the victim to teleport.")
         return
      elif len(destination) == 0:
         session.msg("I can't find the destination for the victim.")
         return
      elif len(victim) > 1:
         session.msg("Multiple results returned for victim!")
         return
      elif len(destination) > 1:
         session.msg("Multiple results returned for destination!")
      else:
         if victim == destination:
            session.msg("You can't teleport an object inside of itself!")
            return
         session.msg("Teleported.")
         victim[0].move_to(server, destination[0])
         
         # This is somewhat kludgy right now, we'll have to find a better way
         # to do it sometime else. If we can find a session in the server's
         # session list matching the object we're teleporting, force it to
         # look. This is going to typically be a player.
         victim_session = functions_db.session_from_object(server.session_list, victim[0])
         if victim_session:
            # We need to form up a new cdat dictionary to pass with the command.
            # Kinda yucky I guess.
            cdat2 = {"server": server, "uinput": 'look', "session": victim_session}
            cmdhandler.handle(cdat2)
         
   else:
      # Direct teleport (no equal sign)
      results = functions_db.local_and_global_search(pobject, search_str)
      
      if len(results) > 1:
         session.msg("More than one match found (please narrow target):")
         for result in results:
            session.msg(" %s(#%s)" % (result.name, result.id,))
      elif len(results) == 0:
         session.msg("I don't see that here.")
         return
      else:
         if results[0] == pobject:
            session.msg("You can't teleport inside yourself!")
            return
         session.msg("Teleported.")
         pobject.move_to(server, results[0])
         commands_general.do_look(cdat)
         
   #session.msg("Args: %s\n\rEqargs: %s" % (args, eq_args,))

def do_find(cdat):
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
         
def do_shutdown(cdat):
   """
   Shut the server down gracefully.
   """
   session = cdat['session']
   server = cdat['server']

   session.msg('Shutting down...')
   print 'Server shutdown by %s(#%d)' % (session.name, session.pobject.id,)
   server.shutdown()
