"""
This module implements the telnet protocol.

This depends on a generic session module that implements
the actual login procedure of the game, tracks 
sessions etc. 

"""

from twisted.conch.telnet import StatefulTelnetProtocol
from src.server.session import Session
from src.utils import utils, ansi 

class TelnetProtocol(StatefulTelnetProtocol, Session):
    """
    Each player connecting over telnet (ie using most traditional mud
    clients) gets a telnet protocol instance assigned to them.  All
    communication between game and player goes through here.
    """

    def connectionMade(self):
        """
        This is called when the connection is first 
        established. 
        """        
        # initialize the session
        client_address = self.transport.client        
        self.init_session("telnet", client_address, self.factory.sessionhandler)
        # add us to sessionhandler 
        self.sessionhandler.connect(self)
        
    def connectionLost(self, reason):
        """
        This is executed when the connection is lost for 
        whatever reason. It can also be called directly, from
        the disconnect method
        """            
        self.sessionhandler.disconnect(self)        
        self.transport.loseConnection()
        
    def lineReceived(self, string):
        """
        Telnet method called when data is coming in over the telnet 
        connection. We pass it on to the game engine directly.
        """        
        self.sessionhandler.data_in(self, string)

    # Session hooks 

    def disconnect(self, reason=None):
        """
        generic hook for the engine to call in order to 
        disconnect this protocol.
        """
        if reason:
            self.data_out(reason)
        self.connectionLost(reason)

    def data_out(self, string, data=None):
        """
        generic hook method for engine to call in order to send data 
        through the telnet connection. 
        Data Evennia -> Player. 'data' argument is not used 
        """
        try:                                                                                                           
            string = utils.to_str(string, encoding=self.encoding)                                                      
        except Exception, e:                                                                                           
            self.sendLine(str(e))                                                                                      
            return                                                                                                     
        nomarkup = False
        raw = False                                                                                                    
        if type(data) == dict:                                                                                         
            # check if we want escape codes to go through unparsed.
            raw = data.get("raw", False)
            # check if we want to remove all markup
            nomarkup = data.get("nomarkup", False)
        if raw:                                                                                                        
            self.sendLine(string)                                                                                      
        else:                                                                                                          
            self.sendLine(ansi.parse_ansi(string, strip_ansi=nomarkup))
