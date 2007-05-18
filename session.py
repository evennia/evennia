from asyncore import dispatcher
from asynchat import async_chat
import socket, asyncore, time, sys
import cPickle as pickle
import cmdhandler
from apps.objects.models import Object
from django.contrib.auth.models import User
import commands_general
import functions_db
import functions_general
import session_mgr

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
      self.uid = None
      self.sock = sock
      self.logged_in = False
      # The time the user last issued a command.
      self.cmd_last = time.time()
      # Player-visible idle time, excluding the IDLE command.
      self.cmd_last_visible = time.time()
      # Total number of commands issued.
      self.cmd_total = 0
      # The time when the user connected.
      self.conn_time = time.time()
      self.channels_subscribed = {}

   def has_user_channel(self, cname, alias_search=False, return_muted=False):
      """
      Is this session subscribed to the named channel?
      return_muted: (bool) Take the user's enabling/disabling of the channel
                           into consideration?
      """
      has_channel = False

      if alias_search:
         # Search by aliases only.
         cdat = self.channels_subscribed.get(cname, False)
         # No key match, fail immediately.
         if not cdat:
            return False
         
         # If channel status is taken into consideration, see if the user
         # has the channel muted or not.
         if return_muted:
            return cdat[1]
         else:
            return True
      else:
         # Search by complete channel name.
         chan_list = self.channels_subscribed.values()
         for chan in chan_list:
            # Check for a name match
            if cname == chan[0]:
               has_channel = True

               # If channel status is taken into consideration, see if the user
               # has the channel muted or not.
               if return_muted is False and not chan[1]:
                  has_channel = False
               break

      return has_channel
      
   def set_user_channel(self, alias, cname, listening):
      """
      Add a channel to a session's channel list.
      """
      self.channels_subscribed[alias] = [cname, listening]
      self.get_pobject().set_attribute("CHANLIST", pickle.dumps(self.channels_subscribed))

   def del_user_channel(self, alias):
      """
      Remove a channel from a session's channel list.
      """
      del self.channels_subscribed[alias]

   def load_user_channels(self):
      """
      Un-pickle a user's channel list from their CHANLIST attribute.
      """
      chan_list = self.get_pobject().get_attribute_value("CHANLIST")
      if chan_list:
         self.channels_subscribed = pickle.loads(chan_list)
      
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
      
      # Stuff anything we need to pass in this dictionary.
      cdat = {"server": self.server, "uinput": uinput, "session": self}
      cmdhandler.handle(cdat)
         
   def handle_close(self):
      """
      Break the connection and do some accounting.
      """
      pobject = self.get_pobject()
      if pobject:
         pobject.set_flag("CONNECTED", False)
         pobject.get_location().emit_to_contents("%s has disconnected." % (pobject.get_name(),), exclude=pobject)
         
      async_chat.handle_close(self)
      self.logged_in = False
      session_mgr.remove_session(self)
      print 'Sessions active:', len(session_mgr.get_session_list())
      
   def get_pobject(self):
      """
      Returns the object associated with a session.
      """
      try:
         result = Object.objects.get(id=self.uid)
         return result
      except:
         return False
      
   def game_connect_screen(self, session):
      """
      Show the banner screen.
      """
      buffer =  '-'*50
      buffer += ' \n\rWelcome to Evennia!\n\r'
      buffer += '-'*50 + '\n\r'
      buffer += """Please type one of the following to begin:\n\r 
         connect <email> <password>\n\r
         create \"<username>\" <email> <password>\n\r"""
      buffer += '-'*50
      session.msg(buffer)
      
   def login(self, user):
      """
      After the user has authenticated, handle logging him in.
      """
      self.uid = user.id
      self.name = user.username
      self.logged_in = True
      self.conn_time = time.time()
      pobject = self.get_pobject()
      pobject.set_flag("CONNECTED", True)

      self.msg("You are now logged in as %s." % (self.name,))
      pobject.get_location().emit_to_contents("%s has connected." % (pobject.get_name(),), exclude=pobject)
      cdat = {"session": self, "uinput":'look', "server": self.server}
      cmdhandler.handle(cdat)
      functions_general.log_infomsg("Login: %s" % (self,))
      pobject.set_attribute("Last", "%s" % (time.strftime("%a %b %d %H:%M:%S %Y", time.localtime()),))
      pobject.set_attribute("Lastsite", "%s" % (self.address[0],))
      self.load_user_channels()
      
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

#   def handle_error(self):
#      self.handle_close()
