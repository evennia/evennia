"""
This module implements the telnet protocol.

This depends on a generic session module that implements
the actual login procedure of the game, tracks
sessions etc.

"""

import re
from twisted.conch.telnet import Telnet, StatefulTelnetProtocol, IAC, LINEMODE, GA
from src.server.session import Session
from src.server.portal import ttype, mssp, msdp
from src.server.portal.mccp import Mccp, mccp_compress, MCCP
from src.utils import utils, ansi, logger

_RE_N = re.compile(r"\{n$")


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
        self.iaw_mode = False
        client_address = self.transport.client
        self.init_session("telnet", client_address, self.factory.sessionhandler)
        # negotiate ttype (client info)
        # Obs: mudlet ttype does not seem to work if we start mccp before ttype. /Griatch
        self.ttype = ttype.Ttype(self)
        # negotiate mccp (data compression) - turn this off for wireshark analysis
        self.mccp = Mccp(self)
        # negotiate mssp (crawler communication)
        self.mssp = mssp.Mssp(self)
        # msdp
        self.msdp = msdp.Msdp(self)
        # add this new connection to sessionhandler so
        # the Server becomes aware of it.

        # This is a fix to make sure the connection does not
        # continue until the handshakes are done. This is a
        # dumb delay of 1 second. This solution is not ideal (and
        # potentially buggy for slow connections?) but
        # adding a callback chain to all protocols (and notably
        # to their handshakes, which in some cases are multi-part)
        # is not trivial. Without it, the protocol will default
        # to their defaults since sessionhandler.connect will sync
        # before the handshakes have had time to finish. Keeping this patch
        # until coming up with a more elegant solution /Griatch
        from src.utils.utils import delay
        delay(1, callback=self.sessionhandler.connect, retval=self)
        #self.sessionhandler.connect(self)

    def enableRemote(self, option):
        """
        This sets up the remote-activated options we allow for this protocol.
        """
        return (option == LINEMODE or
                option == ttype.TTYPE or
                option == MCCP or
                option == mssp.MSSP)

    def enableLocal(self, option):
        """
        Call to allow the activation of options for this protocol
        """
        return option == MCCP

    def disableLocal(self, option):
        """
        Disable a given option
        """
        if option == MCCP:
            self.mccp.no_mccp(option)
            return True
        else:
            return super(TelnetProtocol, self).disableLocal(option)

    def connectionLost(self, reason):
        """
        this is executed when the connection is lost for
        whatever reason. it can also be called directly, from
        the disconnect method
        """
        self.sessionhandler.disconnect(self)
        self.transport.loseConnection()

    def dataReceived(self, data):
        """
        This method will split the incoming data depending on if it
        starts with IAC (a telnet command) or not. All other data will
        be handled in line mode. Some clients also sends an erroneous
        line break after IAC, which we must watch out for.

        OOB protocols (MSDP etc) already intercept subnegotiations
        on their own, never entering this method. They will relay
        their parsed data directly to self.data_in.

        """

        if data and data[0] == IAC or self.iaw_mode:
            try:
                #print "IAC mode"
                super(TelnetProtocol, self).dataReceived(data)
                if len(data) == 1:
                    self.iaw_mode = True
                else:
                    self.iaw_mode = False
                return
            except Exception, err1:
                conv = ""
                try:
                    for b in data:
                        conv += " " + repr(ord(b))
                except Exception, err2:
                    conv = str(err2) + ":", str(data)
                out = "Telnet Error (%s): %s (%s)" % (err1, data, conv)
                logger.log_trace(out)
                return
        # if we get to this point the command must end with a linebreak.
        # We make sure to add it, to fix some clients messing this up.
        data = data.rstrip("\r\n") + "\n"
        #print "line data in:", repr(data)
        StatefulTelnetProtocol.dataReceived(self, data)

    def _write(self, data):
        "hook overloading the one used in plain telnet"
        # print "_write (%s): %s" % (self.state,  " ".join(str(ord(c)) for c in data))
        data = data.replace('\n', '\r\n').replace('\r\r\n', '\r\n')
        #data = data.replace('\n', '\r\n')
        super(TelnetProtocol, self)._write(mccp_compress(self, data))

    def sendLine(self, line):
        "hook overloading the one used by linereceiver"
        #print "sendLine (%s):\n%s" % (self.state, line)
        #escape IAC in line mode, and correctly add \r\n
        line += self.delimiter
        line = line.replace(IAC, IAC + IAC).replace('\n', '\r\n')
        return self.transport.write(mccp_compress(self, line))

    def lineReceived(self, string):
        """
        Telnet method called when data is coming in over the telnet
        connection. We pass it on to the game engine directly.
        """
        self.data_in(text=string)

    # Session hooks

    def disconnect(self, reason=None):
        """
        generic hook for the engine to call in order to
        disconnect this protocol.
        """
        if reason:
            self.data_out(reason)
        self.connectionLost(reason)

    def data_in(self, text=None, **kwargs):
        """
        Data Telnet -> Server
        """
        self.sessionhandler.data_in(self, text=text, **kwargs)

    def data_out(self, text=None, **kwargs):
        """
        Data Evennia -> Player.
        generic hook method for engine to call in order to send data
        through the telnet connection.

        valid telnet kwargs:
            oob=<string> - supply an Out-of-Band instruction.
            xterm256=True/False - enforce xterm256 setting. If not
                                  given, ttype result is used. If
                                  client does not suport xterm256, the
                                  ansi fallback will be used
            ansi=True/False - enforce ansi setting. If not given,
                              ttype result is used.
            nomarkup=True - strip all ansi markup (this is the same as
                            xterm256=False, ansi=False)
            raw=True - pass string through without any ansi
                       processing (i.e. include Evennia ansi markers but do
                       not convert them into ansi tokens)

        The telnet ttype negotiation flags, if any, are used if no kwargs
        are given.
        """
        try:
            text = utils.to_str(text if text else "", encoding=self.encoding)
        except Exception, e:
            self.sendLine(str(e))
            return
        if "oob" in kwargs:
            oobstruct = self.sessionhandler.oobstruct_parser(kwargs.pop("oob"))
            if "MSDP" in self.protocol_flags:
                for cmdname, args, kwargs in oobstruct:
                    #print "cmdname, args, kwargs:", cmdname, args, kwargs
                    msdp_string = self.msdp.evennia_to_msdp(cmdname, *args, **kwargs)
                    #print "msdp_string:", msdp_string
                    self.msdp.data_out(msdp_string)

        # parse **kwargs, falling back to ttype if nothing is given explicitly
        ttype = self.protocol_flags.get('TTYPE', {})
        xterm256 = kwargs.get("xterm256", ttype and ttype.get('256 COLORS', False))
        useansi = kwargs.get("ansi", ttype and ttype.get('ANSI', False))
        raw = kwargs.get("raw", False)
        nomarkup = kwargs.get("nomarkup", not (xterm256 or useansi) or not ttype.get("init_done"))
        prompt = kwargs.get("prompt")

        if prompt:
            # Send prompt separately
            prompt = ansi.parse_ansi(_RE_N.sub("", text) + "{n", strip_ansi=nomarkup, xterm256=xterm256)
            prompt = prompt.replace(IAC, IAC + IAC).replace('\n', '\r\n')
            prompt += IAC + GA
            self.transport.write(mccp_compress(self, prompt))

        #print "telnet kwargs=%s, message=%s" % (kwargs, text)
        #print "xterm256=%s, useansi=%s, raw=%s, nomarkup=%s, init_done=%s" % (xterm256, useansi, raw, nomarkup, ttype.get("init_done"))
        if raw:
            # no processing whatsoever
            self.sendLine(text)
        else:
            # we need to make sure to kill the color at the end in order
            # to match the webclient output.
            # print "telnet data out:", self.protocol_flags, id(self.protocol_flags), id(self)
            self.sendLine(ansi.parse_ansi(_RE_N.sub("", text) + "{n", strip_ansi=nomarkup, xterm256=xterm256))
