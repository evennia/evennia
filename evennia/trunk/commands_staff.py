from apps.objects.models import Object
import functions_db
import functions_general
import commands_general
import cmdhandler

"""
Staff commands may be a bad description for this file, but it'll do for now.
Any command here is prefixed by an '@' sign, usually denoting a builder, staff
or otherwise manipulative command that doesn't fall within the scope of
normal gameplay.
"""

def cmd_dig(cdat):      
   """
   Creates a new object of type 'ROOM'.
   """
   session = cdat['session']
   server = session.server
   uinput= cdat['uinput']['splitted']
   roomname = ' '.join(uinput[1:])
   
   if roomname == '':
      session.msg("You must supply a name!")
   else:
      # Create and set the object up.
      odat = {"name": roomname, "type": 2, "location": None, "owner": session.pobject}
      new_object = functions_db.create_object(server, odat)
      
      session.msg("You create a new room: %s" % (new_object,))
      
def cmd_create(cdat):
   """
   Creates a new object of type 'THING'.
   """
   session = cdat['session']
   server = session.server
   uinput= cdat['uinput']['splitted']
   thingname = ' '.join(uinput[1:])
   
   if thingname == '':
      session.msg("You must supply a name!")
   else:
      # Create and set the object up.
      odat = {"name": thingname, "type": 3, "location": session.pobject, "owner": session.pobject}
      new_object = functions_db.create_object(server, odat)
      
      session.msg("You create a new thing: %s" % (new_object,))
   
def cmd_nextfree(cdat):
   """
   Returns the next free object number.
   """
   session = cdat['session']
   server = cdat['server']
   
   nextfree = functions_db.get_nextfree_dbnum()
   retval = "Next free object number: #%s" % (nextfree,)
   
   session.msg(retval)
   
def cmd_teleport(cdat):
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
      victim = functions_db.local_and_global_search(pobject, eq_args[0], searcher=pobject)
      destination = functions_db.local_and_global_search(pobject, eq_args[1], searcher=pobject)
      
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
         victim_session = functions_db.session_from_object(server.get_session_list(), victim[0])
         if victim_session:
            # We need to form up a new cdat dictionary to pass with the command.
            # Kinda yucky I guess.
            cdat2 = {"server": server, "uinput": 'look', "session": victim_session}
            cmdhandler.handle(cdat2)
         
   else:
      # Direct teleport (no equal sign)
      results = functions_db.local_and_global_search(pobject, search_str, searcher=pobject)
      
      if len(results) > 1:
         session.msg("More than one match found (please narrow target):")
         for result in results:
            session.msg(" %s" % (result,))
      elif len(results) == 0:
         session.msg("I don't see that here.")
         return
      else:
         if results[0] == pobject:
            session.msg("You can't teleport inside yourself!")
            return
         session.msg("Teleported.")
         pobject.move_to(server, results[0])
         commands_general.cmd_look(cdat)
         
def cmd_set(cdat):
   """
   Sets flags or attributes on objects.
   """
   session = cdat['session']
   pobject = session.pobject
   server = cdat['server']
   args = cdat['uinput']['splitted'][1:]
   
   if len(args) == 0:
      session.msg("Set what?")
      return
   
   # There's probably a better way to do this. Break the arguments (minus
   # the root command) up so we have two items in the list, 0 being the victim,
   # 1 being the list of flags or the attribute/value pair.   
   eq_args = ' '.join(args).split('=')
   
   if len(eq_args) < 2:
      session.msg("Set what?")
      return
      
   victim = functions_db.local_and_global_search(pobject, eq_args[0], searcher=pobject)
   
   if len(victim) == 0:
      session.msg("I don't see that here.")
      return
   elif len(victim) > 1:
      session.msg("I don't know which one you mean!")
      return
      
   victim = victim[0]
   attrib_args = eq_args[1].split(':')

   if len(attrib_args) > 1:
      # We're dealing with an attribute/value pair.
      attrib_name = attrib_args[0].upper()
      attrib_value = ' '.join(attrib_args[1:])
      session.msg("%s - %s set." % (victim.get_name(), attrib_name))
   else:
      # Flag manipulation form.
      flag_list = eq_args[1].split()
      
      for flag in flag_list:
         flag = flag.upper()
         if flag[0] == '!':
            # We're un-setting the flag.
            flag = flag[1:]
            if not functions_db.modifiable_flag(flag):
               session.msg("You can't set/unset the flag - %s." % (flag,))
            else:
               session.msg('%s - %s cleared.' % (victim.get_name(), flag.upper(),))
               victim.set_flag(flag, False)
         else:
            # We're setting the flag.
            if not functions_db.modifiable_flag(flag):
               session.msg("You can't set/unset the flag - %s." % (flag,))
            else:
               session.msg('%s - %s set.' % (victim.get_name(), flag.upper(),))
               victim.set_flag(flag, True)

def cmd_find(cdat):
   """
   Searches for an object of a particular name.
   """
   session = cdat['session']
   server = cdat['server']
   searchstring = ' '.join(cdat['uinput']['splitted'][1:])
   
   if searchstring == '':
      session.msg("No search pattern given.")
      return
   
   results = functions_db.list_search_object_namestr(server.object_list.values(), searchstring)

   if len(results) > 0:
      session.msg("Name matches for: %s" % (searchstring,))
      for result in results:
         session.msg(" %s" % (result,))
      session.msg("%d matches returned." % (len(results),))
   else:
      session.msg("No name matches found for: %s" % (searchstring,))
         
def cmd_wall(cdat):
   """
   Announces a message to all connected players.
   """
   session = cdat['session']
   server = cdat['server']
   wallstring = ' '.join(cdat['uinput']['splitted'][1:])
   
   if wallstring == '':
      session.msg("Announce what?")
      return
      
   message = "%s shouts \"%s\"" % (session.pobject.name, wallstring)
   functions_general.announce_all(server, message)   

def cmd_shutdown(cdat):
   """
   Shut the server down gracefully.
   """
   session = cdat['session']
   server = cdat['server']

   session.msg('Shutting down...')
   print 'Server shutdown by %s(#%d)' % (session.name, session.pobject.id,)
   server.shutdown()
