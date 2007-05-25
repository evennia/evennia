import settings
import time
import functions_general
import functions_db
import functions_help
import defines_global as global_defines
import session_mgr
import ansi
import os
"""
Generic command module. Pretty much every command should go here for
now.
"""   
def cmd_idle(cdat):
   """
   Returns nothing, this lets the player set an idle timer without spamming
   his screen.
   """
   pass
   
def cmd_inventory(cdat):
   """
   Shows a player's inventory.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   session.msg("You are carrying:")
   
   for item in pobject.get_contents():
      session.msg(" %s" % (item.get_name(),))
      
   money = int(pobject.get_attribute_value("MONEY", default=0))
   if money == 1:
      money_name = functions_db.get_server_config("MONEY_NAME_SINGULAR")
   else:
      money_name = functions_db.get_server_config("MONEY_NAME_PLURAL")

   session.msg("You have %d %s." % (money,money_name))

def cmd_look(cdat):
   """
   Handle looking at objects.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]

   if len(args) == 0:   
      target_obj = pobject.get_location()
   else:
      target_obj = functions_db.standard_plr_objsearch(session, ' '.join(args))
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return
   
   retval = "%s\r\n%s" % (
      target_obj.get_name(),
      target_obj.get_description(),
   )
   session.msg(retval)
   
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
      session.msg("%sPlayers:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],))
      for player in con_players:
         session.msg('%s' %(player.get_name(),))
   if con_things:
      session.msg("%sContents:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],))
      for thing in con_things:
         session.msg('%s' %(thing.get_name(),))
   if con_exits:
      session.msg("%sExits:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],))
      for exit in con_exits:
         session.msg('%s' %(exit.get_name(),))
         
def cmd_get(cdat):
   """
   Get an object and put it in a player's inventory.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   plr_is_staff = pobject.is_staff()

   if len(args) == 0:   
      session.msg("Get what?")
      return
   else:
      target_obj = functions_db.standard_plr_objsearch(session, ' '.join(args), search_contents=False)
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return

   if pobject == target_obj:
      session.msg("You can't get yourself.")
      return
   
   if not plr_is_staff and (target_obj.is_player() or target_obj.is_exit()):
      session.msg("You can't get that.")
      return
      
   if target_obj.is_room() or target_obj.is_garbage() or target_obj.is_going():
      session.msg("You can't get that.")
      return
      
   target_obj.move_to(pobject, quiet=True)
   session.msg("You pick up %s." % (target_obj.get_name(),))
   pobject.get_location().emit_to_contents("%s picks up %s." % (pobject.get_name(), target_obj.get_name()), exclude=pobject)
         
def cmd_drop(cdat):
   """
   Drop an object from a player's inventory into their current location.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   plr_is_staff = pobject.is_staff()

   if len(args) == 0:   
      session.msg("Drop what?")
      return
   else:
      target_obj = functions_db.standard_plr_objsearch(session, ' '.join(args), search_location=False)
      # Use standard_plr_objsearch to handle duplicate/nonexistant results.
      if not target_obj:
         return

   if not pobject == target_obj.get_location():
      session.msg("You don't appear to be carrying that.")
      return
      
   target_obj.move_to(pobject.get_location(), quiet=True)
   session.msg("You drop %s." % (target_obj.get_name(),))
   pobject.get_location().emit_to_contents("%s drops %s." % (pobject.get_name(), target_obj.get_name()), exclude=pobject)
         
def cmd_examine(cdat):
   """
   Detailed object examine command
   """
   session = cdat['session']
   pobject = session.get_pobject()
   args = cdat['uinput']['splitted'][1:]
   attr_search = False
   
   if len(args) == 0:   
      # If no arguments are provided, examine the invoker's location.
      target_obj = pobject.get_location()
   else:
      # Look for a slash in the input, indicating an attribute search.
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
      attr_matches = target_obj.attribute_namesearch(attr_searchstr)
      if attr_matches:
         for attribute in attr_matches:
            session.msg(attribute.get_attrline())
      else:
         session.msg("No matching attributes found.")
      # End attr_search if()
   else:
      session.msg("%s\r\n%s" % (
         target_obj.get_name(fullname=True),
         target_obj.get_description(no_parsing=True),
      ))
      session.msg("Type: %s Flags: %s" % (target_obj.get_type(), target_obj.get_flags()))
      session.msg("Owner: %s " % (target_obj.get_owner(),))
      session.msg("Zone: %s" % (target_obj.get_zone(),))
      
      for attribute in target_obj.get_all_attributes():
         session.msg(attribute.get_attrline())
      
      con_players = []
      con_things = []
      con_exits = []
      
      for obj in target_obj.get_contents():
         if obj.is_player():
            con_players.append(obj)  
         elif obj.is_exit():
            con_exits.append(obj)
         elif obj.is_thing():
            con_things.append(obj)
      
      if con_players or con_things:
         session.msg("%sContents:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],))
         for player in con_players:
            session.msg('%s' % (player.get_name(fullname=True),))
         for thing in con_things:
            session.msg('%s' % (thing.get_name(fullname=True),))
            
      if con_exits:
         session.msg("%sExits:%s" % (ansi.ansi["hilite"], ansi.ansi["normal"],))
         for exit in con_exits:
            session.msg('%s' %(exit.get_name(fullname=True),))
            
      if not target_obj.is_room():
         if target_obj.is_exit():
            session.msg("Destination: %s" % (target_obj.get_home(),))
         else:
            session.msg("Home: %s" % (target_obj.get_home(),))
            
         session.msg("Location: %s" % (target_obj.get_location(),))
   
def cmd_page(cdat):
   """
   Send a message to target user (if online).
   """
   session = cdat['session']
   pobject = session.get_pobject()
   server = cdat['server']
   args = cdat['uinput']['splitted'][1:]

   if len(args) == 0:
      session.msg("Page who/what?")
      return

   # Combine the arguments into one string, split it by equal signs into
   # victim (entry 0 in the list), and message (entry 1 and above).
   eq_args = ' '.join(args).split('=')

   # If no equal sign is in the passed arguments, see if the player has
   # a LASTPAGED attribute. If they do, default the page to them, if not,
   # don't touch anything and error out.
   if len(eq_args) == 1 and pobject.has_attribute("LASTPAGED"):
      eq_args.insert(0, "#%s" % (pobject.get_attribute_value("LASTPAGED"),))
         
   if len(eq_args) > 1:
      target = functions_db.player_search(pobject, eq_args[0])
      message = ' '.join(eq_args[1:])

      if len(target) == 0:
         session.msg("I don't recognize \"%s\"." % (eq_args[0].capitalize(),))
         return
      elif len(message) == 0:
         session.msg("I need a message to deliver.")
         return
      elif len(target) > 1:
         session.msg("Try a more unique spelling of their name.")
         return
      else:
         if target[0].is_connected_plr():
            target[0].emit_to("%s pages: %s" %
               (pobject.get_name(show_dbref=False), message))
            session.msg("You paged %s with '%s'." %
               (target[0].get_name(show_dbref=False), message))
            pobject.set_attribute("LASTPAGED", target[0].id)
         else:
            session.msg("Player %s does not exist or is not online." %
               (target[0].get_name(show_dbref=False),))
   else:
      session.msg("Page who?")
      return

def cmd_quit(cdat):
   """
   Gracefully disconnect the user as per his own request.
   """
   session = cdat['session']
   session.msg("Quitting!")
   session.handle_close()
   
def cmd_who(cdat):
   """
   Generic WHO command.
   """
   session_list = session_mgr.get_session_list()
   session = cdat['session']
   pobject = session.get_pobject()
   show_session_data = pobject.user_has_perm("genperms.see_session_data")

   # Only those with the see_session_data or superuser status can see
   # session details.
   if show_session_data:
      retval = "Player Name           On For Idle   Room    Cmds   Host\n\r"
   else:
      retval = "Player Name           On For Idle\n\r"
      
   for player in session_list:
      if not player.logged_in:
         continue
      delta_cmd = time.time() - player.cmd_last_visible
      delta_conn = time.time() - player.conn_time
      plr_pobject = player.get_pobject()

      if show_session_data:
         retval += '%-16s%9s %4s%-3s#%-6d%5d%3s%-25s\r\n' % \
            (plr_pobject.get_name(show_dbref=False)[:25].ljust(27), \
            # On-time
            functions_general.time_format(delta_conn,0), \
            # Idle time
            functions_general.time_format(delta_cmd,1), \
            # Flags
            '', \
            # Location
            plr_pobject.get_location().id, \
            player.cmd_total, \
            # More flags?
            '', \
            player.address[0])
      else:
         retval += '%-16s%9s %4s%-3s\r\n' % \
            (plr_pobject.get_name(show_dbref=False)[:25].ljust(27), \
            # On-time
            functions_general.time_format(delta_conn,0), \
            # Idle time
            functions_general.time_format(delta_cmd,1), \
            # Flags
            '')
   retval += '%d Players logged in.' % (len(session_list),)
   
   session.msg(retval)

def cmd_say(cdat):
   """
   Room-based speech command.
   """
   session = cdat['session']

   if not functions_general.cmd_check_num_args(session, cdat['uinput']['splitted'], 1, errortext="Say what?"):
      return
   
   session_list = session_mgr.get_session_list()
   pobject = session.get_pobject()
   speech = ' '.join(cdat['uinput']['splitted'][1:])
   
   players_present = [player for player in session_list if player.get_pobject().get_location() == session.get_pobject().get_location() and player != session]
   
   retval = "You say, '%s'" % (speech,)
   for player in players_present:
      player.msg("%s says, '%s'" % (pobject.get_name(show_dbref=False), speech,))
   
   session.msg(retval)

def cmd_pose(cdat):
   """
   Pose/emote command.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   switches = cdat['uinput']['root_chunk'][1:]

   if not functions_general.cmd_check_num_args(session, cdat['uinput']['splitted'], 1, errortext="Do what?"):
      return
   
   session_list = session_mgr.get_session_list()
   speech = ' '.join(cdat['uinput']['splitted'][1:])
   
   if "nospace" in switches:
      sent_msg = "%s%s" % (pobject.get_name(show_dbref=False), speech)
   else:
      sent_msg = "%s %s" % (pobject.get_name(show_dbref=False), speech)
   
   players_present = [player for player in session_list if player.get_pobject().get_location() == session.get_pobject().get_location()]
   
   for player in players_present:
      player.msg(sent_msg)
   
def cmd_help(cdat):
   """
   Help system commands.
   """
   session = cdat['session']
   pobject = session.get_pobject()
   topicstr = ' '.join(cdat['uinput']['splitted'][1:])
   
   if len(topicstr) == 0:
      topicstr = "Help Index"   
   elif len(topicstr) < 2 and not topicstr.isdigit():
      session.msg("Your search query is too short. It must be at least three letters long.")
      return
      
   topics = functions_help.find_topicmatch(pobject, topicstr)      
      
   if len(topics) == 0:
      session.msg("No matching topics found, please refine your search.")
      suggestions = functions_help.find_topicsuggestions(pobject, topicstr)
      if len(suggestions) > 0:
         session.msg("Matching similarly named topics:")
         for result in suggestions:
            session.msg(" %s" % (result,))
            session.msg("You may type 'help <#>' to see any of these topics.")
   elif len(topics) > 1:
      session.msg("More than one match found:")
      for result in topics:
         session.msg("%3d. %s" % (result.id, result.get_topicname()))
      session.msg("You may type 'help <#>' to see any of these topics.")
   else:   
      topic = topics[0]
      session.msg("\r\n%s%s%s" % (ansi.ansi["hilite"], topic.get_topicname(), ansi.ansi["normal"]))
      session.msg(topic.get_entrytext_ingame())
   
def cmd_version(cdat):
   """
   Version info command.
   """
   session = cdat['session']
   retval = "-"*50 +"\n\r"
   retval += "Evennia %s\n\r" % (global_defines.EVENNIA_VERSION,)
   retval += "-"*50
   session.msg(retval)

def cmd_time(cdat):
   """
   Server local time.
   """
   session = cdat['session']
   session.msg('Current server time : %s' % (time.strftime('%a %b %d %H:%M %Y (%Z)', time.localtime(),)))
   
def cmd_uptime(cdat):
   """
   Server uptime and stats.
   """
   session = cdat['session']
   server = cdat['server']
   start_delta = time.time() - server.start_time
   loadavg = os.getloadavg()
   session.msg('Current server time : %s' % (time.strftime('%a %b %d %H:%M %Y (%Z)', time.localtime(),)))
   session.msg('Server start time   : %s' % (time.strftime('%a %b %d %H:%M %Y', time.localtime(server.start_time),)))
   session.msg('Server uptime       : %s' % functions_general.time_format(start_delta, style=2))
   session.msg('Server load (1 min) : %.2f' % loadavg[0])
