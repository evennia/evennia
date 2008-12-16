"""
This module contains classes related to Sessions. session_mgr has the things
needed to manage them.
"""
import time
import sys
from datetime import datetime

from twisted.conch.telnet import StatefulTelnetProtocol

from django.contrib.auth.models import User

from src.objects.models import Object
from src.config.models import ConnectScreen, ConfigValue
import cmdhandler
import logger
import session_mgr
import ansi
from util import functions_general

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
        logger.log_infomsg('Connection: %s' % (self,))
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
        logger.log_infomsg('Disconnect: %s' % (self,))
        self.handle_close()
        
    def lineReceived(self, data):
        """
        Any line return indicates a command for the purpose of a MUD. So we take
        the user input and pass it to our command handler.
        """
        # Clean up the input.
        line = (''.join(data))
        line = line.strip('\r')
        uinput = line
        
        # The Command object has all of the methods for parsing and preparing
        # for searching and execution.
        command = cmdhandler.Command(uinput, 
                                     server=self.factory.server, 
                                     session=self)
        
        # Send the command object to the command handler for parsing
        # and eventual execution.
        cmdhandler.handle(command)

    def execute_cmd(self, cmdstr):
        """
        Executes a command as this session.
        """
        self.lineReceived(data=cmdstr)
      
    def count_command(self, silently=False):
        """
        Hit this when the user enters a command in order to update idle timers
        and command counters. If silently is True, the public-facing idle time
        is not updated.
        """
        # Store the timestamp of the user's last command.
        self.cmd_last = time.time()
        # Increment the user's command counter.
        self.cmd_total += 1
        if not silently:
            # Player-visible idle time, not used in idle timeout calcs.
            self.cmd_last_visible = time.time()
            
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
            logger.log_errmsg("No session match for object: #%s" % self.uid)
            return None
        
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
        
        pobject.scriptlink.at_pre_login()
        pobject.scriptlink.at_post_login()
        
        logger.log_infomsg("Login: %s" % (self,))
        
        # Update their account's last login time.
        user.last_login = datetime.now()
        user.save()
        
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
