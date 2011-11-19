"""
This module implements the telnet protocol.

This depends on a generic session module that implements
the actual login procedure of the game, tracks 
sessions etc. 

"""

from twisted.conch.telnet import Telnet, StatefulTelnetProtocol, IAC, LINEMODE
from src.server.session import Session
from src.server import ttype 
from src.utils import utils, ansi 

class TelnetProtocol(Telnet, StatefulTelnetProtocol, Session):
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

        # setup ttype 
        self.ttype = ttype.Ttype(self)

        # add us to sessionhandler 
        self.sessionhandler.connect(self)

    def enableRemote(self, option): 
        """
        This sets up the options we allow for this protocol.
        """
        return (option == LINEMODE or
                option == ttype.TTYPE)
    
    def connectionLost(self, reason):
        """
        This is executed when the connection is lost for 
        whatever reason. It can also be called directly, from
        the disconnect method
        """            
        self.sessionhandler.disconnect(self)        
        self.transport.loseConnection()

    def dataReceived(self, data):
        """
        This method will split the incoming data depending on if it
        starts with IAC (a telnet command) or not. All other data will
        be handled in line mode.
        """
        # print "dataRcv:", data,
        # try:
        #     for b in data:
        #         print ord(b),
        #         if b == chr(24): print "ttype found!"
        #     print ""
        # except Exception, e:
        #     print str(e) + ":", str(data)

        if data and data[0] == IAC:
            super(TelnetProtocol, self).dataReceived(data)
        else:
            StatefulTelnetProtocol.dataReceived(self, data)

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
