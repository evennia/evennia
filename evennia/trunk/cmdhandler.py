from commands_staff import StaffCommands
from commands_general import GenCommands
from commands_unloggedin import UnLoggedInCommands
"""
This is the command processing module. It is instanced once in the main
server module and the handle() function is hit every time a player sends
something.
"""
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
         session.msg("Unknown command.")
      
