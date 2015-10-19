"""
This module implements the telnet protocol.

This depends on a generic session module that implements
the actual login procedure of the game, tracks
sessions etc.

"""

import re
from twisted.internet.task import LoopingCall
from twisted.conch.telnet import Telnet, StatefulTelnetProtocol, IAC, LINEMODE, GA, WILL, WONT, ECHO
from evennia.server.session import Session
from evennia.server.portal import ttype, mssp, telnet_oob, naws
from evennia.server.portal.mccp import Mccp, mccp_compress, MCCP
from evennia.server.portal.mxp import Mxp, mxp_parse
from evennia.utils import utils, ansi, logger

IAC = chr(255)
NOP = chr(241)

_RE_N = re.compile(r"\{n$")
_RE_LEND = re.compile(r"\n$|\r$", re.MULTILINE)

class TelnetProtocol(Telnet, StatefulTelnetProtocol, Session):
    """
    Each player connecting over telnet (ie using most traditional mud
    clients) gets a telnet protocol instance assigned to them.  All
    communication between game and player goes through here.
    """
    def connectionMade(self):
        """
        This is called when the connection is first established.

        """
        # initialize the session
        self.iaw_mode = False
        self.no_lb_mode = False
        client_address = self.transport.client
        # this number is counted down for every handshake that completes.
        # when it reaches 0 the portal/server syncs their data
        self.handshakes = 7 # naws, ttype, mccp, mssp, msdp, gmcp, mxp
        self.init_session("telnet", client_address, self.factory.sessionhandler)

        # negotiate client size
        self.naws = naws.Naws(self)
        # negotiate ttype (client info)
        # Obs: mudlet ttype does not seem to work if we start mccp before ttype. /Griatch
        self.ttype = ttype.Ttype(self)
        # negotiate mccp (data compression) - turn this off for wireshark analysis
        self.mccp = Mccp(self)
        # negotiate mssp (crawler communication)
        self.mssp = mssp.Mssp(self)
        # oob communication (MSDP, GMCP) - two handshake calls!
        self.oob = telnet_oob.TelnetOOB(self)
        # mxp support
        self.mxp = Mxp(self)
        # keepalive watches for dead links
        self.transport.setTcpKeepAlive(1)
        # add this new connection to sessionhandler so
        # the Server becomes aware of it.
        self.sessionhandler.connect(self)

        # timeout the handshakes in case the client doesn't reply at all
        from evennia.utils.utils import delay
        delay(2, callback=self.handshake_done, retval=True)

        # set up a keep-alive
        self.keep_alive = LoopingCall(self._write, IAC + NOP)
        self.keep_alive.start(30, now=False)


    def handshake_done(self, force=False):
        """
        This is called by all telnet extensions once they are finished.
        When all have reported, a sync with the server is performed.
        The system will force-call this sync after a small time to handle
        clients that don't reply to handshakes at all.
        """
        if self.handshakes > 0:
            if force:
                self.sessionhandler.sync(self)
                return
            self.handshakes -= 1
            if self.handshakes <= 0:
                # do the sync
                self.sessionhandler.sync(self)

    def enableRemote(self, option):
        """
        This sets up the remote-activated options we allow for this protocol.

        Args:
            option (char): The telnet option to enable.

        Returns:
            enable (bool): If this option should be enabled.

        """
        return (option == LINEMODE or
                option == ttype.TTYPE or
                option == naws.NAWS or
                option == MCCP or
                option == mssp.MSSP)

    def enableLocal(self, option):
        """
        Call to allow the activation of options for this protocol

        Args:
            option (char): The telnet option to enable locally.

        Returns:
            enable (bool): If this option should be enabled.

        """
        return (option == MCCP or option==ECHO)

    def disableLocal(self, option):
        """
        Disable a given option locally.

        Args:
            option (char): The telnet option to disable locally.

        """
        if option == ECHO:
            return True
        if option == MCCP:
            self.mccp.no_mccp(option)
            return True
        else:
            return super(TelnetProtocol, self).disableLocal(option)

    def connectionLost(self, reason):
        """
        this is executed when the connection is lost for whatever
        reason. it can also be called directly, from the disconnect
        method

        Args:
            reason (str): Motivation for losing connection.

        """
        self.sessionhandler.disconnect(self)
        self.transport.loseConnection()

    def dataReceived(self, data):
        """
        Handle incoming data over the wire.

        This method will split the incoming data depending on if it
        starts with IAC (a telnet command) or not. All other data will
        be handled in line mode. Some clients also sends an erroneous
        line break after IAC, which we must watch out for.

        Args:
            data (str): Incoming data.

        Notes:
            OOB protocols (MSDP etc) already intercept subnegotiations on
            their own, never entering this method. They will relay their
            parsed data directly to self.data_in.

        """
        if data and data[0] == IAC or self.iaw_mode:
            try:
                super(TelnetProtocol, self).dataReceived(data)
                if len(data) == 1:
                    self.iaw_mode = True
                else:
                    self.iaw_mode = False
                return
            except Exception as err1:
                conv = ""
                try:
                    for b in data:
                        conv += " " + repr(ord(b))
                except Exception as err2:
                    conv = str(err2) + ":", str(data)
                out = "Telnet Error (%s): %s (%s)" % (err1, data, conv)
                logger.log_trace(out)
                return

        if self.no_lb_mode and _RE_LEND.match(data):
            # we are in no_lb_mode and we get a single line break
            # - this line break should have come with the previous
            # command - it was already added so we drop it here
            self.no_lb_mode = False
            return
        elif not _RE_LEND.search(data):
            # no line break at the end of the command, note this.
            data = data.rstrip("\r\n") + "\n"
            self.no_lb_mode = True

        # if we get to this point the command should end with a linebreak.
        # We make sure to add it, to fix some clients messing this up.
        StatefulTelnetProtocol.dataReceived(self, data)

    def _write(self, data):
        "hook overloading the one used in plain telnet"
        data = data.replace('\n', '\r\n').replace('\r\r\n', '\r\n')
        #data = data.replace('\n', '\r\n')
        super(TelnetProtocol, self)._write(mccp_compress(self, data))

    def sendLine(self, line):
        """
        Hook overloading the one used by linereceiver.

        Args:
            line (str): Line to send.

        """
        #escape IAC in line mode, and correctly add \r\n
        line += self.delimiter
        line = line.replace(IAC, IAC + IAC).replace('\n', '\r\n')
        return self.transport.write(mccp_compress(self, line))

    def lineReceived(self, string):
        """
        Telnet method called when data is coming in over the telnet
        connection. We pass it on to the game engine directly.

        Args:
            string (str): Incoming data.

        """
        self.data_in(text=string)

    # Session hooks

    def disconnect(self, reason=None):
        """
        generic hook for the engine to call in order to
        disconnect this protocol.

        Args:
            reason (str): Reason for disconnecting.

        """
        if reason:
            self.data_out(reason)
        self.connectionLost(reason)

    def data_in(self, text=None, **kwargs):
        """
        Data User -> Evennia

        Kwargs:
            text (str): Incoming text.
            kwargs (any): Options from the protocol.

        """
        #from evennia.server.profiling.timetrace import timetrace
        #text = timetrace(text, "telnet.data_in")

        self.sessionhandler.data_in(self, text=text, **kwargs)

    def data_out(self, text=None, **kwargs):
        """
        Data Evennia -> User. A generic hook method for engine to call
        in order to send data through the telnet connection.

        Kwargs:
            text (str): Text to send.
            oob (list): `[(cmdname,args,kwargs), ...]`, supply an
                Out-of-Band instruction.
            xterm256 (bool): Enforce xterm256 setting. If not given,
                ttype result is used. If client does not suport xterm256,
                the ansi fallback will be used
            mxp (bool): Enforce mxp setting. If not given, enables if
                we detected client support for it
            ansi (bool): Enforce ansi setting. If not given, ttype
                result is used.
            nomarkup (bool): If True, strip all ansi markup (this is
                the same as `xterm256=False, ansi=False`)
            raw (bool):Pass string through without any ansi processing
                (i.e. include Evennia ansi markers but do not convert them
                into ansi tokens)
            prompt (str): Supply a prompt text which gets sent without
                a newline added to the end.
            echo (str): Turn on/off line echo on the client, if the
                client supports it (e.g. for password input). Remember
                that you must manually activate it again later.

        Notes:
            The telnet TTYPE negotiation flags, if any, are used if no kwargs
            are given.

        """
        ## profiling, debugging
        #if text.startswith("TEST_MESSAGE"): 1/0
        #from evennia.server.profiling.timetrace import timetrace
        #text = timetrace(text, "telnet.data_out", final=True)

        try:
            text = utils.to_str(text if text else "", encoding=self.encoding)
        except Exception as e:
            self.sendLine(str(e))
            return
        if "oob" in kwargs and "OOB" in self.protocol_flags:
            # oob is a list of [(cmdname, arg, kwarg), ...]
            for cmdname, args, okwargs in kwargs["oob"]:
                self.oob.data_out(cmdname, *args, **okwargs)

        # parse **kwargs, falling back to ttype if nothing is given explicitly
        ttype = self.protocol_flags.get('TTYPE', {})
        xterm256 = kwargs.get("xterm256", ttype.get('256 COLORS', False) if ttype.get("init_done") else True)
        useansi = kwargs.get("ansi", ttype and ttype.get('ANSI', False) if ttype.get("init_done") else True)
        raw = kwargs.get("raw", False)
        nomarkup = kwargs.get("nomarkup", not (xterm256 or useansi))
        prompt = kwargs.get("prompt")
        echo = kwargs.get("echo", None)
        mxp = kwargs.get("mxp", self.protocol_flags.get("MXP", False))

        if raw:
            # no processing whatsoever
            self.sendLine(text)
        elif text:
            # we need to make sure to kill the color at the end in order
            # to match the webclient output.
            linetosend = ansi.parse_ansi(_RE_N.sub("", text) + "{n", strip_ansi=nomarkup, xterm256=xterm256, mxp=mxp)
            if mxp:
                linetosend = mxp_parse(linetosend)
            self.sendLine(linetosend)

        if prompt:
            # Send prompt separately
            prompt = ansi.parse_ansi(_RE_N.sub("", prompt) + "{n", strip_ansi=nomarkup, xterm256=xterm256)
            if mxp:
                prompt = mxp_parse(prompt)
            prompt = prompt.replace(IAC, IAC + IAC).replace('\n', '\r\n')
            prompt += IAC + GA
            self.transport.write(mccp_compress(self, prompt))
        if echo:
            self.transport.write(mccp_compress(self, IAC+WONT+ECHO))
        elif echo == False:
            self.transport.write(mccp_compress(self, IAC+WILL+ECHO))

