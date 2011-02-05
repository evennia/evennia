"""
This module implements the telnet protocol.

This depends on a generic session module that implements
the actual login procedure of the game, tracks 
sessions etc. 

"""

from twisted.conch.telnet import StatefulTelnetProtocol
from django.conf import settings 
from src.config.models import ConnectScreen
from src.server import session
from src.utils import ansi, utils

ENCODINGS = settings.ENCODINGS

class TelnetProtocol(StatefulTelnetProtocol, session.Session):
    """
    Each player connecting over telnet (ie using most traditional mud
    clients) gets a telnet protocol instance assigned to them.  All
    communication between game and player goes through here.
    """

    # telnet-specific hooks 

    def connectionMade(self):
        """
        This is called when the connection is first 
        established. 
        """        
        # initialize the session
        self.session_connect(self.getClientAddress())
        
    def connectionLost(self, reason=None, step=1):
        """
        This is executed when the connection is lost for 
        whatever reason. 
        
        Closing the connection takes two steps
        
        step 1 - is the default and is used when this method is
                 called automatically. The method should then call self.session_disconnect().
        Step 2 - means this method is called from at_disconnect(). At this point 
                 the sessions are assumed to have been handled, and so the transport can close
                 without further ado. 
        """
        if step == 1:
            self.session_disconnect()
        else:
            self.transport.loseConnection()
        
    def getClientAddress(self):
        """
        Returns the client's address and port in a tuple. For example
        ('127.0.0.1', 41917)
        """
        return self.transport.client

    def lineReceived(self, string):
        """
        Communication Player -> Evennia. Any line return indicates a
        command for the purpose of the MUD.  So we take the user input
        and pass it on to the game engine.
        """        
        self.at_data_in(string)

    def lineSend(self, string):
        """
        Communication Evennia -> Player
        Any string sent should already have been
        properly formatted and processed 
        before reaching this point.

        """
        self.sendLine(string) #this is the telnet-specific method for sending

    # session-general method hooks

    def at_connect(self):
        """
        Show the banner screen. Grab from the 'connect_screen'
        config directive. If more than one connect screen is
        defined in the ConnectScreen attribute, it will be
        random which screen is used. 
        """
        self.telnet_markup = True 
        # show screen 
        screen = ConnectScreen.objects.get_random_connect_screen()
        string = ansi.parse_ansi(screen.text)        
        self.at_data_out(string)
        
    def at_login(self):
        """
        Called after authentication. self.logged_in=True at this point.
        """
        if self.player.has_attribute('telnet_markup'):
            self.telnet_markup = self.player.get_attribute("telnet_markup")
        else:
            self.telnet_markup = True             

    def at_disconnect(self, reason="Connection closed. Goodbye for now."):
        """
        Disconnect from server
        """                
        self.at_data_out(reason)
        self.connectionLost(step=2)

    def at_data_out(self, string, data=None):
        """
        Data Evennia -> Player access hook. 'data' argument is ignored.
        """
        if self.encoding:
            try:
                string = utils.to_str(string, encoding=self.encoding)
                self.lineSend(ansi.parse_ansi(string, strip_ansi=not self.telnet_markup))
                return 
            except Exception:
                pass
        # malformed/wrong encoding defined on player - try some defaults
        for encoding in ENCODINGS:
            try:
                string = utils.to_str(string, encoding=encoding)
                err = None
                break 
            except Exception, e:
                err = str(e)                
                continue
        if err:
            self.lineSend(err)
        else:
            self.lineSend(ansi.parse_ansi(string, strip_ansi=not self.telnet_markup))

    def at_data_in(self, string, data=None):
        """
        Line from Player -> Evennia. 'data' argument is not used.
        
        """        
        if self.encoding:
            try:            
                string = utils.to_unicode(string, encoding=self.encoding)
                self.execute_cmd(string)
                return 
            except Exception, e:
                err = str(e)
                print err
        # malformed/wrong encoding defined on player - try some defaults 
        for encoding in ENCODINGS:
            try:
                string = utils.to_unicode(string, encoding=encoding)
                err = None
                break             
            except Exception, e:
                err = str(e)
                continue         
        self.execute_cmd(string)
