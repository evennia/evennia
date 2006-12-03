import settings
import time
import functions_general
from ansi import *

"""
Generic command module. Pretty much every command should go here for
now.
"""   

def do_look(cdat):
   """
   Handle looking at objects.
   """
   session = cdat['session']
   server = cdat['server']
   player_loc = session.player_loc
   player_loc_obj = server.object_list[player_loc]
   
   retval = "%s%s%s%s\n\r%s" % (
      ansi["normal"],
      ansi["hilite"], 
      player_loc_obj.name,
      ansi["normal"],
      player_loc_obj.description,
   )
   session.msg(retval)
   
def do_quit(cdat):
   """
   Gracefully disconnect the user as per his own request.
   """
   session = cdat['session']
   session.msg("Quitting!")
   session.handle_close()
   
def do_who(cdat):
   """
   Generic WHO command.
   """
   session_list = cdat['server'].session_list
   session = cdat['session']
   
   retval = "Player Name        On For Idle   Room    Cmds   Host\n\r"
   for player in session_list:
      delta_cmd = time.time() - player.cmd_last
      delta_conn = time.time() - player.conn_time

      retval += '%-16s%9s %4s%-3s#%-6d%5d%3s%-25s\r\n' % \
         (player.name, \
         # On-time
         functions_general.time_format(delta_conn,0), \
         # Idle time
         functions_general.time_format(delta_cmd,1), \
         # Flags
         '', \
         # Location
         player.pobject.location.id, \
         player.cmd_total, \
         # More flags?
         '', \
         player.address[0])
   retval += '%d Players logged in.' % (len(session_list),)
   
   session.msg(retval)

def do_say(cdat):
   """
   Room-based speech command.
   """
   session_list = cdat['server'].session_list
   session = cdat['session']
   speech = ''.join(cdat['uinput']['splitted'][1:])
   players_present = [player for player in session_list if player.player_loc == session.player_loc and player != session]
   
   retval = "You say, '%s'" % (speech,)
   for player in players_present:
      player.msg("%s says, '%s'" % (session.name, speech,))
   
   session.msg(retval)
   
def do_version(cdat):
   """
   Version info command.
   """
   session = cdat['session']
   retval = "-"*50 +"\n\r"
   retval += "Evennia %s\n\r" % (settings.EVENNIA_VERSION,)
   retval += "-"*50
   session.msg(retval)
