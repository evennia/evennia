from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore, time, sys
import cmdhandler
from apps.objects.models import Object
from django.contrib.auth.models import User

class PlayerSession(async_chat):
   """
   This class represents a player's sesssion. From here we branch down into
   other various classes, please try to keep this one tidy!
   """
   def __init__(self, server, sock, addr):
      async_chat.__init__(self, sock)
      self.server = server
      self.address = addr
      self.set_terminator("\n")
      self.name = None
      self.data = []
      self.sock = sock
      self.logged_in = False
      self.pobject = None
      # The time the user last issued a command.
      self.cmd_last = time.time()
      # Total number of commands issued.
      self.cmd_total = 0
      # The time when the user connected.
      self.conn_time = time.time()
      # Player's room location. Move this to a player sub-class.
      self.player_loc = 1
                
   def collect_incoming_data(self, data):
      """
      Stuff any incoming data into our buffer, self.data
      """
      self.data.append(data)
                
   def found_terminator(self):
      """
      Any line return indicates a command for the purpose of a MUD. So we take
      the user input and pass it to our command handler.
      """
      line = (''.join(self.data))
      line = line.strip('\r')
      uinput = line
      self.data = []
      
      # Increment our user's command counter.
      self.cmd_total += 1
      # Store the timestamp of the user's last command.
      self.cmd_last = time.time()
      # Stuff anything we need to pass in this dictionary.
      cdat = {"server": self.server, "uinput": uinput, "session": self}
      cmdhandler.handle(cdat)
         
   def handle_close(self):
      """
      Break the connection and do some accounting.
      """
      async_chat.handle_close(self)
      self.logged_in = False
      self.server.session_list.remove(self)
      print 'Sessions active:', len(self.server.session_list)
      
   def game_connect_screen(self, session):
      """
      Show our banner screen.
      """
      buffer =  '-'*50
      buffer += ' \n\rWelcome to Evennia!\n\r'
      buffer += '-'*50 + '\n\r'
      buffer += """Please type one of the following to begin:\n\r 
         connect <username> <password>\n\r
         create <username> <email> <password>\n\r"""
      buffer += '-'*50
      session.msg(buffer)
      
   def login(self, user):
      """
      After the user has authenticated, handle logging him in.
      """
      self.pobject = Object.objects.filter(id=user.id)[0]
      self.name = user.username
      self.logged_in = True
      self.conn_time = time.time()
      self.msg("Logging in as %s." % (self.name,))
      print "Login: %s" % (self,)
      
   def msg(self, message):
      """
      Sends a message with the newline/return included. Use this instead of
      directly calling push().
      """
      self.push("%s\n\r" % (message,))
      
   def msg_no_nl(self, message):
      """
      Sends a message without the newline/return included. Use this instead of
      directly calling push().
      """
      self.push("%s" % (message,))
          
   def __str__(self):
      """
      String representation of the user session class. We use
      this a lot in the server logs and stuff.
      """
      if self.logged_in:
         symbol = '#'
      else:
         symbol = '?'
      return "<%s> %s@%s" % (symbol, self.name, self.address,)

#       def handle_error(self):
#               self.handle_close()
