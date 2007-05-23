import os
import resource

from django.contrib.auth.models import User
from apps.objects.models import Object
import defines_global
import session_mgr
import functions_general
import functions_db
import commands_general
import ansi
"""
Any command here is prefixed by an '@' sign, usually denoting a 
builder, staff or otherwise manipulative command that doesn't fall within 
the scope of normal gameplay.
"""

def cmd_reload(cdat):
   """
   Reloads all modules.
   """
   session = cdat['session']
   server = session.server.reload(session)

def cmd_destroy(cdat):
   """
   Destroy an object.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   switches = cdat['uinput']['root_chunk'][1:]
   switch_override = False
   
   if "override" in switches:
      switch_override = True
   
   if len(args) == 0:   
      session.msg("Destroy what?")
      return
   else:
      results = functions_db.local_and_global_search(pobject, ' '.join(args))
      
      if len(results) > 1:
         session.msg("More than one match found (please narrow target):")
         for result in results:
            session.msg(" %s" % (result.get_name(),))
         return
      elif len(results) == 0:
         session.msg("I don't see that here.")
         return
      elif results[0].is_player():
         if pobject.id == results[0].id:
            session.msg("You can't destroy yourself.")
            return
         if not switch_override:
            session.msg("You must use @destroy/override on players.")
            return
         if results[0].is_superuser():
            session.msg("You can't destroy a superuser.")
            return
         target_obj = results[0]
      elif results[0].is_going():
         session.msg("That object is already destroyed.")
         return
      elif results[0].is_garbage():
         session.msg("That object is already destroyed.")
         return
      else:
         target_obj = results[0]
   
   session.msg("You destroy %s." % (target_obj,))
   target_obj.destroy()

def cmd_list(cdat):
   """
   Shows some game related information.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   argstr = ''.join(args)
   
   msg_invalid = "Unknown option. Use one of: commands, flags, process"
   
   if len(argstr) == 0:   
      session.msg(msg_invalid)
   elif argstr == "commands":
      session.msg('Commands: '+ ' '.join(session.server.command_list()))
   elif argstr == "process":
      loadvg = os.getloadavg()
      psize = resource.getpagesize()
      rusage = resource.getrusage(resource.RUSAGE_SELF)
      session.msg("Process ID:  %10d        %10d bytes per page" % (os.getpid(), psize))
      session.msg("Time used:   %10d user   %10d sys" % (rusage[0],rusage[1]))
      session.msg("Integral mem:%10d shared %10d private%10d stack" % (rusage[3], rusage[4], rusage[5]))
      session.msg("Max res mem: %10d pages  %10d bytes" % (rusage[2],rusage[2] * psize))
      session.msg("Page faults: %10d hard   %10d soft   %10d swapouts" % (rusage[7], rusage[6], rusage[8]))
      session.msg("Disk I/O:    %10d reads  %10d writes" % (rusage[9], rusage[10]))
      session.msg("Network I/O: %10d in     %10d out" % (rusage[12], rusage[11]))
      session.msg("Context swi: %10d vol    %10d forced %10d sigs" % (rusage[14], rusage[15], rusage[13]))
   elif argstr == "flags":
      session.msg("Flags: "+" ".join(defines_global.SERVER_FLAGS))
   else:
      session.msg(msg_invalid)

def cmd_description(cdat):
   """
   Set an object's description.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   eq_args = ' '.join(args).split('=')
   searchstring = ''.join(eq_args[0])
   
   if len(args) == 0:   
      session.msg("What do you want to describe?")
   elif len(eq_args) < 2:
      session.msg("How would you like to describe that object?")
   else:
      results = functions_db.local_and_global_search(pobject, searchstring)
      
      if len(results) > 1:
         session.msg("More than one match found (please narrow target):")
         for result in results:
            session.msg(" %s" % (result.get_name(),))
         return
      elif len(results) == 0:
         session.msg("I don't see that here.")
         return
      else:
         target_obj = results[0]
         if not pobject.controls_other(target):
            session.msg(defines_global.NOCONTROL_MSG)
            return
         
         new_desc = '='.join(eq_args[1:])
         session.msg("%s - DESCRIPTION set." % (target_obj,))
         target_obj.set_description(new_desc)

def cmd_newpassword(cdat):
   """
   Set a player's password.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   eq_args = ' '.join(args).split('=')
   searchstring = ''.join(eq_args[0])
   newpass = ''.join(eq_args[1:])
   
   if len(args) == 0:   
      session.msg("What player's password do you want to change")
      return
   if len(newpass) == 0:
      session.msg("You must supply a new password.")
      return

   results = functions_db.local_and_global_search(pobject, searchstring)
   

   if len(results) > 1:
      session.msg("More than one match found (please narrow target):")
      for result in results:
         session.msg(" %s" % (result.get_name(),))
   elif len(results) == 0:
      session.msg("I don't see that here.")
   elif not pobject.controls_other(results[0]):
      session.msg("You do not control %s." % (results[0],))
   else:
      uaccount = results[0].get_user_account()
      if len(newpass) == 0:
         uaccount.set_password()
      else:
         uaccount.set_password(newpass)
      uaccount.save()
      session.msg("%s - PASSWORD set." % (results[0],))
      results[0].emit_to("%s has changed your password." % (pobject,))

def cmd_password(cdat):
   """
   Changes your own password.
   
   @newpass <Oldpass>=<Newpass>
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   eq_args = ' '.join(args).split('=')
   oldpass = ''.join(eq_args[0])
   newpass = ''.join(eq_args[1:])
   
   if len(oldpass) == 0:   
      session.msg("You must provide your old password.")
   elif len(newpass) == 0:
      session.msg("You must provide your new password.")
   else:
      uaccount = User.objects.get(id=pobject.id)
      
      if not uaccount.check_password(oldpass):
         session.msg("The specified old password isn't correct.")
      elif len(newpass) < 3:
         session.msg("Passwords must be at least three characters long.")
         return
      else:
         uaccount.set_password(newpass)
         uaccount.save()
         session.msg("Password changed.")

def cmd_name(cdat):
   """
   Handle naming an object.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   eq_args = ' '.join(args).split('=')
   searchstring = ''.join(eq_args[0])
   
   if len(args) == 0:   
      session.msg("What do you want to name?")
   elif len(eq_args) < 2:
      session.msg("What would you like to name that object?")
   else:
      results = functions_db.local_and_global_search(pobject, searchstring)
      
      if len(results) > 1:
         session.msg("More than one match found (please narrow target):")
         for result in results:
            session.msg(" %s" % (result.get_name(),))
         return
      elif len(results) == 0:
         session.msg("I don't see that here.")
         return
      elif len(eq_args[1]) == 0:
         session.msg("What would you like to name that object?")
      else:
         newname = '='.join(eq_args[1:])
         target_obj = results[0]
         session.msg("You have renamed %s to %s." % (target_obj, ansi.parse_ansi(newname, strip_formatting=True)))
         target_obj.set_name(newname)

def cmd_dig(cdat):      
   """
   Creates a new object of type 'ROOM'.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   uinput= cdat['uinput']['splitted']
   roomname = ' '.join(uinput[1:])
   
   if roomname == '':
      session.msg("You must supply a name!")
   else:
      # Create and set the object up.
      odat = {"name": roomname, "type": 2, "location": None, "owner": pobject}
      new_object = functions_db.create_object(odat)
      
      session.msg("You create a new room: %s" % (new_object,))
      
def cmd_emit(cdat):      
   """
   Emits something to your location.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   uinput= cdat['uinput']['splitted']
   message = ' '.join(uinput[1:])
   
   if message == '':
      session.msg("Emit what?")
   else:
      pobject.get_location().emit_to_contents(message)
      
def cmd_create(cdat):
   """
   Creates a new object of type 'THING'.
   """
   session = cdat['session']
   server = session.server
   pobject = session.get_pobject()
   uinput= cdat['uinput']['splitted']
   thingname = ' '.join(uinput[1:])
   
   if thingname == '':
      session.msg("You must supply a name!")
   else:
      # Create and set the object up.
      odat = {"name": thingname, "type": 3, "location": pobject, "owner": pobject}
      new_object = functions_db.create_object(odat)
      
      session.msg("You create a new thing: %s" % (new_object,))
   
def cmd_nextfree(cdat):
   """
   Returns the next free object number.
   """
   session = cdat['session']
   
   nextfree = functions_db.get_nextfree_dbnum()
   if str(nextfree).isdigit():
      retval = "Next free object number: #%s" % (nextfree,)
   else:
      retval = "Next free object number: #%s (GARBAGE)" % (nextfree.id,)
   
   session.msg(retval)
   
def cmd_open(cdat):
   """
   Handle the opening of exits.
   
   Forms:
   @open <Name>
   @open <Name>=<Dbref>
   @open <Name>=<Dbref>,<Name>
   """
   session = cdat['session']
   pobject = session.get_pobject()
   server = cdat['server']
   args = cdat['uinput']['splitted'][1:]
   
   if len(args) == 0:
      session.msg("Open an exit to where?")
      return
      
   eq_args = ' '.join(args).split('=')
   exit_name = eq_args[0]
   
   if len(exit_name) == 0:
      session.msg("You must supply an exit name.")
      return
      
   # If we have more than one entry in our '=' delimited argument list,
   # then we're doing a @open <Name>=<Dbref>[,<Name>]. If not, we're doing
   # an un-linked exit, @open <Name>.
   if len(eq_args) > 1:
      # Opening an exit to another location via @open <Name>=<Dbref>[,<Name>].
      comma_split = eq_args[1].split(',')
      destination = functions_db.local_and_global_search(pobject, comma_split[0])
      
      if len(destination) == 0:
         session.msg("I can't find the location to link to.")
         return
      elif len(destination) > 1:
         session.msg("Multiple results returned for exit destination!")
      else:
         destination = destination[0]
         if destination.is_exit():
            session.msg("You can't open an exit to an exit!")
            return
         
         odat = {"name": exit_name, "type": 4, "location": pobject.get_location(), "owner": pobject, "home":destination}
         new_object = functions_db.create_object(odat)
         
         session.msg("You open the an exit - %s to %s" % (new_object.get_name(),destination.get_name()))
         
         if len(comma_split) > 1:
            second_exit_name = ','.join(comma_split[1:])
            odat = {"name": second_exit_name, "type": 4, "location": destination, "owner": pobject, "home": pobject.get_location()}
            new_object = functions_db.create_object(odat)
            session.msg("You open the an exit - %s to %s" % (new_object.get_name(),pobject.get_location().get_name()))

   else:
      # Create an un-linked exit.
      odat = {"name": exit_name, "type": 4, "location": pobject.get_location(), "owner": pobject, "home":None}
      new_object = functions_db.create_object(odat)

      session.msg("You open an unlinked exit - %s" % (new_object,))
         
def cmd_link(cdat):
   """
   Sets an object's home or an exit's destination.
   
   Forms:
   @link <Object>=<Target>
   """
   session = cdat['session']
   pobject = session.get_pobject()
   server = cdat['server']
   args = cdat['uinput']['splitted'][1:]
   
   if len(args) == 0:
      session.msg("Link what?")
      return
      
   eq_args = args[0].split('=')
   target_name = eq_args[0]
   dest_name = '='.join(eq_args[1:])   
   
   if len(target_name) == 0:
      session.msg("What do you want to link?")
      return
      
   if len(eq_args) > 1:
      target = functions_db.local_and_global_search(pobject, target_name)
      
      if len(target) == 0:
         session.msg("I can't find the object you want to link.")
         return
      elif len(target) > 1:
         session.msg("Multiple results returned for link target.")
         return
         
      # We know we can get the first entry now. 
      target = target[0]

      if not pobject.controls_other(target):
         session.msg(defines_global.NOCONTROL_MSG)
         return
      
      # If we do something like "@link blah=", we unlink the object.
      if len(dest_name) == 0:
         target.set_home(None)
         session.msg("You have unlinked %s." % (target,))
         return
      
      destination = functions_db.local_and_global_search(pobject, dest_name)
      
      if len(destination) == 0:
         session.msg("I can't find the location to link to.")
         return
      elif len(destination) > 1:
         session.msg("Multiple results returned for destination.")
         return
         
      destination = destination[0]
      target.set_home(destination)
      session.msg("You link %s to %s." % (target,destination))
         
   else:
      # We haven't provided a target.
      session.msg("You must provide a destination to link to.")
      return
      
def cmd_unlink(cdat):
   """
   Unlinks an object.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   
   if len(args) == 0:   
      session.msg("Unlink what?")
      return
   else:
      results = functions_db.local_and_global_search(pobject, ' '.join(args))
      
      if len(results) > 1:
         session.msg("More than one match found (please narrow target):")
         for result in results:
            session.msg(" %s" % (result.get_name(),))
         return
      elif len(results) == 0:
         session.msg("I don't see that here.")
         return
      else:
         if not pobject.controls_other(results[0]):
            session.msg(defines_global.NOCONTROL_MSG)
            return
         
         results[0].set_home(None)
         session.msg("You have unlinked %s." % (results[0],))

def cmd_teleport(cdat):
   """
   Teleports an object somewhere.
   """
   session = cdat['session']
   pobject = session.get_pobject()
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
         victim[0].move_to(destination[0])
         
         # This is somewhat kludgy right now, we'll have to find a better way
         # to do it sometime else. If we can find a session in the server's
         # session list matching the object we're teleporting, force it to
         # look. This is going to typically be a player.
         victim_session = session_mgr.session_from_object(victim[0])
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
            session.msg(" %s" % (result.get_name(),))
      elif len(results) == 0:
         session.msg("I don't see that here.")
         return
      else:
         if results[0] == pobject:
            session.msg("You can't teleport inside yourself!")
            return
         session.msg("Teleported.")
         pobject.move_to(results[0])
         commands_general.cmd_look(cdat)
         
def cmd_set(cdat):
   """
   Sets flags or attributes on objects.
   """
   session = cdat['session']
   pobject = session.get_pobject()
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
      
   victim = functions_db.local_and_global_search(pobject, eq_args[0])
   
   if len(victim) == 0:
      session.msg("I don't see that here.")
      return
   elif len(victim) > 1:
      session.msg("I don't know which one you mean!")
      return
      
   victim = victim[0]
   if not pobject.controls_other(victim):
      session.msg(defines_global.NOCONTROL_MSG)
      return
   
   attrib_args = eq_args[1].split(':')

   if len(attrib_args) > 1:
      # We're dealing with an attribute/value pair.
      attrib_name = attrib_args[0].upper()
      splicenum = eq_args[1].find(':') + 1
      attrib_value = eq_args[1][splicenum:]
      
      # In global_defines.py, see NOSET_ATTRIBS for protected attribute names.
      if not functions_db.is_modifiable_attrib(attrib_name) and not pobject.is_superuser():
         session.msg("You can't modify that attribute.")
         return
      
      if attrib_value:
         # An attribute value was specified, create or set the attribute.
         verb = 'set'
         victim.set_attribute(attrib_name, attrib_value)
      else:
         # No value was given, this means we delete the attribute.
         verb = 'cleared'
         victim.clear_attribute(attrib_name)
      session.msg("%s - %s %s." % (victim.get_name(), attrib_name, verb))
   else:
      # Flag manipulation form.
      flag_list = eq_args[1].split()
      
      for flag in flag_list:
         flag = flag.upper()
         if flag[0] == '!':
            # We're un-setting the flag.
            flag = flag[1:]
            if not functions_db.is_modifiable_flag(flag):
               session.msg("You can't set/unset the flag - %s." % (flag,))
            else:
               session.msg('%s - %s cleared.' % (victim.get_name(), flag.upper(),))
               victim.set_flag(flag, False)
         else:
            # We're setting the flag.
            if not functions_db.is_modifiable_flag(flag):
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
   pobject = session.get_pobject()
   can_find = pobject.user_has_perm("genperms.builder")

   if searchstring == '':
      session.msg("No search pattern given.")
      return
   
   results = functions_db.global_object_name_search(searchstring)

   if len(results) > 0:
      session.msg("Name matches for: %s" % (searchstring,))
      for result in results:
         session.msg(" %s" % (result.get_name(fullname=True),))
      session.msg("%d matches returned." % (len(results),))
   else:
      session.msg("No name matches found for: %s" % (searchstring,))
         
def cmd_wall(cdat):
   """
   Announces a message to all connected players.
   """
   session = cdat['session']
   wallstring = ' '.join(cdat['uinput']['splitted'][1:])
   pobject = session.get_pobject()
      
   if wallstring == '':
      session.msg("Announce what?")
      return
      
   message = "%s shouts \"%s\"" % (session.get_pobject().get_name(), wallstring)
   functions_general.announce_all(message)   

def cmd_shutdown(cdat):
   """
   Shut the server down gracefully.
   """
   session = cdat['session']
   server = cdat['server']
   pobject = session.get_pobject()
   
   session.msg('Shutting down...')
   print 'Server shutdown by %s' % (pobject.get_name(show_dbref=False),)
   server.shutdown()
