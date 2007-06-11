import ansi
import session_mgr
import functions_db
# For aliases
from apps.objects.models import Attribute


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
      victim = functions_db.standard_plr_objsearch(session, eq_args[0])
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not victim:
         return

      destination = functions_db.standard_plr_objsearch(session, eq_args[1])
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not destination:
         return

      if victim.is_room():
         session.msg("You can't teleport a room.")
         return

      if victim == destination:
         session.msg("You can't teleport an object inside of itself!")
         return
      session.msg("Teleported.")
      victim.move_to(destination)

      # This is somewhat kludgy right now, we'll have to find a better way
      # to do it sometime else. If we can find a session in the server's
      # session list matching the object we're teleporting, force it to
      # look. This is going to typically be a player.
      victim_session = session_mgr.session_from_object(victim)
      if victim_session:
         victim_session.execute_cmd("look")

   else:
      # Direct teleport (no equal sign)
      target_obj = functions_db.standard_plr_objsearch(session, search_str)
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return

      if target_obj == pobject:
         session.msg("You can't teleport inside yourself!")
         return
      session.msg("Teleported.")
      pobject.move_to(target_obj)
      session.execute_cmd("look")

def cmd_stats(cdat):
   """
   Shows stats about the database.
   4012 objects = 144 rooms, 212 exits, 613 things, 1878 players. (1165 garbage)
   """
   session = cdat['session']
   stats_dict = functions_db.object_totals()
   session.msg("%d objects = %d rooms, %d exits, %d things, %d players. (%d garbage)" % (stats_dict["objects"],
      stats_dict["rooms"],
      stats_dict["exits"],
      stats_dict["things"],
      stats_dict["players"],
      stats_dict["garbage"]))

def cmd_alias(cdat):
   """
   Assigns an alias to a player object for ease of paging, etc.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]

   if len(args) == 0:
      session.msg("Alias whom?")
      return
   
   # Resplit the args on = to check for an almost-required =
   eq_args = ' '.join(args).split('=')
   
   if len(eq_args) < 2:
      session.msg("Alias missing.")
      return
   
   target = functions_db.standard_plr_objsearch(session, eq_args[0])
   # Use standard_plr_objsearch to handle duplicate/nonexistant results.
   if not target:
      session.msg("Alias whom?")
      return
  
   duplicates = functions_db.alias_search(pobject, eq_args[1])
   # duplicates = Attribute.objects.filter(attr_name="ALIAS").filter(attr_value=eq_args[1])
   
   if duplicates:
      session.msg("Alias '%s' already exists." % (eq_args[1],))
      return
   else:
      if pobject.controls_other(target):
         target.set_attribute('ALIAS', eq_args[1])
         session.msg("Alias '%s' set for %s." % (eq_args[1], target.get_name()))
      else:
         session.msg("You do not have access to set an alias for %s." % (target.get_name(),))

def cmd_wipe(cdat):
   """
   Wipes an object's attributes, or optionally only those matching a search
   string.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   attr_search = False

   if len(args) == 0:   
      session.msg("Wipe what?")
      return

   # Look for a slash in the input, indicating an attribute wipe.
   attr_split = args[0].split("/")

   # If the splitting by the "/" character returns a list with more than 1
   # entry, it's an attribute match.
   if len(attr_split) > 1:
      attr_search = True
      # Strip the object search string from the input with the
      # object/attribute pair.
      searchstr = attr_split[0]
      # Just in case there's a slash in an attribute name.
      attr_searchstr = '/'.join(attr_split[1:])
   else:
      searchstr = ' '.join(args)

   target_obj = functions_db.standard_plr_objsearch(session, searchstr)
   # Use standard_plr_objsearch to handle duplicate/nonexistant results.
   if not target_obj:
      return

   if attr_search:
      # User has passed an attribute wild-card string. Search for name matches
      # and wipe.
      attr_matches = target_obj.attribute_namesearch(attr_searchstr, exclude_noset=True)
      if attr_matches:
         for attr in attr_matches:
            target_obj.clear_attribute(attr.get_name())
         session.msg("%s - %d attributes wiped." % (target_obj.get_name(), len(attr_matches)))
      else:
         session.msg("No matching attributes found.")
   else:
      # User didn't specify a wild-card string, wipe entire object.
      attr_matches = target_obj.attribute_namesearch("*", exclude_noset=True)
      for attr in attr_matches:
         target_obj.clear_attribute(attr.get_name())
      session.msg("%s - %d attributes wiped." % (target_obj.get_name(), len(attr_matches)))

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
   
   victim = functions_db.standard_plr_objsearch(session, eq_args[0])
   # Use standard_plr_objsearch to handle duplicate/nonexistant results.
   if not victim:
      return

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
      destination = functions_db.standard_plr_objsearch(session, comma_split[0])
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not destination:
         return

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
      target_obj = functions_db.standard_plr_objsearch(session, target_name)
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return

      if not pobject.controls_other(target_obj):
         session.msg(defines_global.NOCONTROL_MSG)
         return

      # If we do something like "@link blah=", we unlink the object.
      if len(dest_name) == 0:
         target_obj.set_home(None)
         session.msg("You have unlinked %s." % (target_obj,))
         return

      destination = functions_db.standard_plr_objsearch(session, dest_name)
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not destination:
         return

      target_obj.set_home(destination)
      session.msg("You link %s to %s." % (target_obj,destination))

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
      target_obj = functions_db.standard_plr_objsearch(session, ' '.join(args))
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return

      if not pobject.controls_other(target_obj):
         session.msg(defines_global.NOCONTROL_MSG)
         return

      target_obj.set_home(None)
      session.msg("You have unlinked %s." % (target_obj.get_name(),))

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
      target_obj = functions_db.standard_plr_objsearch(session, searchstring)
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return
      
      if len(eq_args[1]) == 0:
         session.msg("What would you like to name that object?")
      else:
         newname = '='.join(eq_args[1:])
         session.msg("You have renamed %s to %s." % (target_obj, ansi.parse_ansi(newname, strip_formatting=True)))
         target_obj.set_name(newname)

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
      target_obj = functions_db.standard_plr_objsearch(session, searchstring)
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return

      if not pobject.controls_other(target_obj):
         session.msg(defines_global.NOCONTROL_MSG)
         return

      new_desc = '='.join(eq_args[1:])
      session.msg("%s - DESCRIPTION set." % (target_obj,))
      target_obj.set_description(new_desc)

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
      target_obj = functions_db.standard_plr_objsearch(session, ' '.join(args))
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return
      
      if target_obj.is_player():
         if pobject.id == target_obj.id:
            session.msg("You can't destroy yourself.")
            return
         if not switch_override:
            session.msg("You must use @destroy/override on players.")
            return
         if target_obj.is_superuser():
            session.msg("You can't destroy a superuser.")
            return
      elif target_obj.is_going() or target_obj.is_garbage():
         session.msg("That object is already destroyed.")
         return
   
   session.msg("You destroy %s." % (target_obj.get_name(),))
   target_obj.destroy()
