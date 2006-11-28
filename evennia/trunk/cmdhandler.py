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
   def do_look(self, cdat):
      """
      Handle looking at objects.
      """
      session = cdat['session']
      server = cdat['server']
      player_loc = session.player_loc
      player_loc_obj = server.object_list[player_loc]
      
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
      speech = cdat['uinput']['splitted'][1:]
      players_present = [player for player in session_list if player.player_loc == session.player_loc and player != session]
      
      retval = "You say, '%s'\n\r" % (''.join(speech),)
      for player in players_present:
         player.push("%s says, '%s'\n\r" % (session.name, speech,))
      
      session.push(retval)
      
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
      
      nextfree = server.get_nextfree_dbnum()
      retval = "Next free object number: %s\n\r" % (nextfree,)
      
      session.push(retval)

class UnLoggedInCommands:
   """
   Commands that are available from the connect screen.
   """
   def do_connect(self, cdat):
      """
      This is the connect command at the connection screen. Fairly simple,
      uses the Django database API and User model to make it extremely simple.
      """
      session = cdat['session']
      uname = cdat['uinput']['splitted'][1]
      password = cdat['uinput']['splitted'][2]
      
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
      server = cdat['server']
      uname = cdat['uinput']['splitted'][1]
      email = cdat['uinput']['splitted'][2]
      password = cdat['uinput']['splitted'][3]
      account = User.objects.filter(username=uname)
      
      if not account.count() == 0:
         session.push("There is already a player with that name!\n\r")
      elif len(password) < 3:
         session.push("Your password must be 3 characters or longer.\n\r")
      else:
         server.create_user(session, uname, email, password)         
         
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

class UnknownCommand(Exception):
   """
   Throw this when a user enters an an invalid command.
   """

class Handler:
   def handle(self, cdat):
      """
      Use the spliced (list) uinput variable to retrieve the correct
      command, or return an invalid command error.

      We're basically grabbing the player's command by tacking
      their input on to 'do_' and looking it up in the GenCommands
      class.
      """
      session = cdat['session']
      server = cdat['server']
      
      try:
         # TODO: Protect against non-standard characters.
         if cdat['uinput'] == '':
            raise UnknownCommand
            
         uinput = cdat['uinput'].split()
         parsed_input = {}
         
         # First we split the input up by spaces.
         parsed_input['splitted'] = uinput
         # Now we find the root command chunk (with switches attached).
         parsed_input['root_chunk'] = parsed_input['splitted'][0].split('/')
         # And now for the actual root command. It's the first entry in root_chunk.
         parsed_input['root_cmd'] = parsed_input['root_chunk'][0].lower()
         
         # Now we'll see if the user is using an alias. We do a dictionary lookup,
         # if the key (the player's root command) doesn't exist on the dict, we
         # don't replace the existing root_cmd. If the key exists, its value
         # replaces the previously splitted root_cmd. For example, sa -> say.
         alias_list = server.cmd_alias_list
         parsed_input['root_cmd'] = alias_list.get(parsed_input['root_cmd'],parsed_input['root_cmd'])

         if session.logged_in:
            # If it's prefixed by an '@', it's a staff command.
            if parsed_input['root_cmd'][0] != '@':
               cmdtable = gencommands
            else:
               parsed_input['root_cmd'] = parsed_input['root_cmd'][1:]
               cmdtable = staffcommands
         else:
            cmdtable = unloggedincommands
         
         # cmdtable now equals the command table we need to use. Do a command
         # lookup for a particular function based on the user's input.   
         cmd = getattr(cmdtable, 'do_%s' % (parsed_input['root_cmd'],), None )
         
         if callable(cmd):
            cdat['uinput'] = parsed_input
            cmd(cdat)
         else:
            raise UnknownCommand
            
      except UnknownCommand:
         session.push("Unknown command.\n\r")
      
