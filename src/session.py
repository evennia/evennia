"""
This module contains classes related to Sessions. session_mgr has the things
needed to manage them.
"""
import time
import sys
from datetime import datetime

from twisted.conch.telnet import StatefulTelnetProtocol

from django.utils import simplejson
from django.contrib.auth.models import User

from apps.objects.models import Object
from apps.config.models import ConnectScreen, ConfigValue
import cmdhandler
import functions_general
import functions_log
import session_mgr
import ansi

class SessionProtocol(StatefulTelnetProtocol):
    """
    This class represents a player's sesssion. From here we branch down into
    other various classes, please try to keep this one tidy!
    """

    def connectionMade(self):
        """
        What to do when we get a connection.
        """
        self.prep_session()
        functions_log.log_infomsg('Connection: %s' % (self,))
        session_mgr.add_session(self)
        self.game_connect_screen()

    def getClientAddress(self):
        """
        Returns the client's address and port in a tuple. For example
        ('127.0.0.1', 41917)
        """
        return self.transport.client

    def prep_session(self):
        self.server = self.factory.server
        self.address = self.getClientAddress()
        self.name = None
        self.uid = None
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

    def disconnectClient(self):
        """
        Manually disconnect the client.
        """
        self.transport.loseConnection()

    def connectionLost(self, reason):
        """
        Execute this when a client abruplty loses their connection.
        """
        functions_log.log_infomsg('Disconnect: %s' % (self,))
        self.handle_close()

    def load_user_channels(self):
        """
        Parse JSON dict of a user's channel list from their CHANLIST attribute.
        """
        chan_list = self.get_pobject().get_attribute_value("__CHANLIST")
        if chan_list:
            self.channels_subscribed = simplejson.loads(chan_list)
        
    def lineReceived(self, data):
        """
        Any line return indicates a command for the purpose of a MUD. So we take
        the user input and pass it to our command handler.
        """
        line = (''.join(data))
        line = line.strip('\r')
        uinput = line
        
        # Stuff anything we need to pass in this dictionary.
        cdat = {"server": self.factory.server, "uinput": uinput, "session": self}
        cmdhandler.handle(cdat)

    def execute_cmd(self, cmdstr):
      """
      Executes a command as this session.
      """
      self.lineReceived(data=cmdstr)
            
    def handle_close(self):
        """
        Break the connection and do some accounting.
        """
        pobject = self.get_pobject()
        if pobject:
            pobject.set_flag("CONNECTED", False)
            pobject.get_location().emit_to_contents("%s has disconnected." % (pobject.get_name(show_dbref=False),), exclude=pobject)
            uaccount = pobject.get_user_account()
            uaccount.last_login = datetime.now()
            uaccount.save()
            
        self.disconnectClient()
        self.logged_in = False
        session_mgr.remove_session(self)
        
    def get_pobject(self):
        """
        Returns the object associated with a session.
        """
        try:
            result = Object.objects.get(id=self.uid)
            return result
        except:
            return False
        
    def game_connect_screen(self):
        """
        Show the banner screen. Grab from the 'connect_screen' config directive.
        """
        screen = ConnectScreen.objects.get_random_connect_screen()
        buffer = ansi.parse_ansi(screen.connect_screen_text)
        self.msg(buffer)

    def is_loggedin(self):
        """
        Returns a boolean True if the session is logged in.
        """
        try:
            return self.logged_in
        except:
            return False
    
    def login(self, user):
        """
        After the user has authenticated, handle logging him in.
        """
        self.uid = user.id
        self.name = user.username
        self.logged_in = True
        self.conn_time = time.time()
        pobject = self.get_pobject()
        session_mgr.disconnect_duplicate_session(self)
        pobject.set_flag("CONNECTED", True)

        self.msg("You are now logged in as %s." % (self.name,))
        pobject.get_location().emit_to_contents("%s has connected." % (pobject.get_name(show_dbref=False),), exclude=pobject)
        self.execute_cmd("look")
        functions_log.log_infomsg("Login: %s" % (self,))
        
        # Update their account's last login time.
        user.last_login = datetime.now()
        user.save()
        pobject.set_attribute("Last", "%s" % (time.strftime("%a %b %d %H:%M:%S %Y", time.localtime()),))
        pobject.set_attribute("Lastsite", "%s" % (self.address[0],))

        # Load their channel selection from a JSON-encoded string attribute.
        self.load_user_channels()
        
    def msg(self, message):
        """
        Sends a message to the session.
        """
        if isinstance(message, unicode):
             message = message.encode("utf-8")
        self.sendLine("%s" % (message,))
        
    def __str__(self):
        """
        String representation of the user session class. We use
        this a lot in the server logs and stuff.
        """
        if self.is_loggedin():
            symbol = '#'
        else:
            symbol = '?'
        return "<%s> %s@%s" % (symbol, self.name, self.address,)
