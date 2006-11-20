from django.contrib.auth.models import User
from apps.objects.models import Object
import settings
import string
from ansi import *
"""
This is the command processing module. It is instanced once in the main
server module and the handle() function is hit every time a player sends
something.
"""

class GenCommands:
   """
   Generic command class. Pretty much every command should go here for
   now.
   """
   def __init__(self): pass
   
   def do_look(self, cdat):
      """
      Handle looking at objects.
      """
      session = cdat['session']
      server = session.server
      player_loc = session.player_loc
      player_loc_obj = Object.objects.filter(id=player_loc)[0]
      
      retval = "%s%s%s%s\n\r%s\n\r" % (
         ansi["normal"],
         ansi["hilite"], 
         player_loc_obj.name,
         ansi["normal"],
         player_loc_obj.description,
      )
      session.push(retval)
      
   def do_quit(self, cdat):
      """
      Gracefully disconnect the user as per his own request.
      """
      session = cdat['session']
      session.push("Quitting!\n\r")
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
      retval += '%d Players logged in.\n\r' % (len(session_list),)
      
      session.push(retval)
   
   def do_say(self, cdat):
      """
      Room-based speech command.
      """
      session_list = cdat['server'].session_list
      session = cdat['session']
      speech = cdat['uinput'][1:]
      players_present = [player for player in session_list if player.player_loc == session.player_loc and player != session]
      
      retval = "You say, '%s'\n\r" % (''.join(speech),)
      for player in players_present:
         player.push("%s says, '%s'\n\r" % (session.name, speech,))
      
      session.push(retval)
      
   def do_sa(self, cdat):
      """
      Temporary alias until we come up with a command alias system.
      """
      self.do_say(cdat)
      
   def do_version(self, cdat):
      """
      Version info command.
      """
      session = cdat['session']
      retval = "-"*50 +"\n\r"
      retval += "Evennia %s\n\r" % (settings.EVENNIA_VERSION,)
      retval += "-"*50 +"\n\r"
      session.push(retval)

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
         session.push("You must supply a room name!")
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
      
      nextfree = server.nextfree_objnum()
      retval = "Next free object number: %d" % (nextfree,)
      
      session.push(retval)

class UnLoggedInCommands:
   """
   Commands that are available from the connect screen.
   """
   def __init__(self): pass
   def do_connect(self, cdat):
      """
      This is the connect command at the connection screen. Fairly simple,
      uses the Django database API and User model to make it extremely simple.
      """
      session = cdat['session']
      uname = cdat['uinput'][1]
      password = cdat['uinput'][2]
      
      account = User.objects.filter(username=uname)
      user = account[0]
      
      autherror = "Invalid username or password!\n\r"
      if account.count() == 0:
         session.push(autherror)
      if not user.check_password(password):
         session.push(autherror)
      else:
         uname = user.username
         session.login(user)
         
   def do_create(self, cdat):
      """
      Handle the creation of new accounts.
      """
      session = cdat['session']
      uname = cdat['uinput'][1]
      email = cdat['uinput'][2]
      password = cdat['uinput'][3]
      account = User.objects.filter(username=uname)
      
      if not account.count() == 0:
         session.push("There is already a player with that name!")
      elif len(password) < 3:
         session.push("Your password must be 3 characters or longer.")
      else:
         session.create_user(uname, email, password)         
         
   def do_quit(self, cdat):
      """
      We're going to maintain a different version of the quit command
      here for unconnected users for the sake of simplicity. The logged in
      version will be a bit more complicated.
      """
      session = cdat['session']
      session.push("Disconnecting...\n\r")
      session.handle_close()

# We'll use this for our getattr() in the Handler class.
gencommands = GenCommands()
staffcommands = StaffCommands()
unloggedincommands = UnLoggedInCommands()

class Handler:
   def __init__(self): pass
   def handle(self, cdat):
      """
      Use the spliced (list) uinput variable to retrieve the correct
      command, or return an invalid command error.

      We're basically grabbing the player's command by tacking
      their input on to 'do_' and looking it up in the GenCommands
      class.
      """
      session = cdat['session']
      uinput = cdat['uinput']
      
      if session.logged_in:
         # If it's prefixed by an '@', it's a staff command.
         if uinput[0].find('@') == -1:
            cmdtable = gencommands
         else:
            cmdtable = staffcommands
      else:
         cmdtable = unloggedincommands
      cmd = getattr(cmdtable, 'do_' + uinput[0].lower(), None)
      
      if callable(cmd):
         cmd(cdat)
      else:
         session.push("Unknown command.\n\r")
      
