import settings
from ansi import *

class GenCommands:
   """
   Generic command class. Pretty much every command should go here for
   now.
   """   
   def do_look(self, cdat):
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
      
   def do_quit(self, cdat):
      """
      Gracefully disconnect the user as per his own request.
      """
      session = cdat['session']
      session.msg("Quitting!")
      session.handle_close()
      
   def do_who(self, cdat):
      """
      Generic WHO command.
      """
      session_list = cdat['server'].session_list
      session = cdat['session']
      
      retval = "Player Name\n\r"
      for player in session_list:
         retval += '%s\n\r' % (player,)
      retval += '%d Players logged in.' % (len(session_list),)
      
      session.msg(retval)
   
   def do_say(self, cdat):
      """
      Room-based speech command.
      """
      session_list = cdat['server'].session_list
      session = cdat['session']
      speech = cdat['uinput']['splitted'][1:]
      players_present = [player for player in session_list if player.player_loc == session.player_loc and player != session]
      
      retval = "You say, '%s'" % (''.join(speech),)
      for player in players_present:
         player.msg("%s says, '%s'" % (session.name, speech,))
      
      session.msg(retval)
      
   def do_version(self, cdat):
      """
      Version info command.
      """
      session = cdat['session']
      retval = "-"*50 +"\n\r"
      retval += "Evennia %s\n\r" % (settings.EVENNIA_VERSION,)
      retval += "-"*50
      session.msg(retval)
