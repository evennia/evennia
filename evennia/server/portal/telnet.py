"""
This module implements the telnet protocol.

This depends on a generic session module that implements
the actual login procedure of the game, tracks
sessions etc.

"""

import re
from twisted.internet import protocol
from twisted.internet.task import LoopingCall
from twisted.conch.telnet import Telnet, StatefulTelnetProtocol
from twisted.conch.telnet import (
    IAC,
    NOP,
    LINEMODE,
    GA,
    WILL,
    WONT,
    ECHO,
    NULL,
    MODE,
    LINEMODE_EDIT,
    LINEMODE_TRAPSIG,
)
from django.conf import settings
from evennia.server.session import Session
from evennia.server.portal import ttype, mssp, telnet_oob, naws, suppress_ga
from evennia.server.portal.mccp import Mccp, mccp_compress, MCCP
from evennia.server.portal.mxp import Mxp, mxp_parse
from evennia.utils import ansi
from evennia.utils.utils import to_bytes

_RE_N = re.compile(r"\|n$")
_RE_LEND = re.compile(br"\n$|\r$|\r\n$|\r\x00$|", re.MULTILINE)
_RE_LINEBREAK = re.compile(br"\n\r|\r\n|\n|\r", re.DOTALL + re.MULTILINE)
_RE_SCREENREADER_REGEX = re.compile(
    r"%s" % settings.SCREENREADER_REGEX_STRIP, re.DOTALL + re.MULTILINE
)
_IDLE_COMMAND = str.encode(settings.IDLE_COMMAND + "\n")


class TelnetServerFactory(protocol.ServerFactory):
    "This is only to name this better in logs"
    noisy = False

    def logPrefix(self):
        return "Telnet"


class TelnetProtocol(Telnet, StatefulTelnetProtocol, Session):
    """
    Each player connecting over telnet (ie using most traditional mud
    clients) gets a telnet protocol instance assigned to them.  All
    communication between game and player goes through here.
    """

    def __init__(self, *args, **kwargs):
        self.protocol_key = "telnet"
        super().__init__(*args, **kwargs)

    def connectionMade(self):
        """
        This is called when the connection is first established.

        """
        # important in order to work normally with standard telnet
        self.do(LINEMODE)
        # initialize the session
        self.line_buffer = b""
        client_address = self.transport.client
        client_address = client_address[0] if client_address else None
        # this number is counted down for every handshake that completes.
        # when it reaches 0 the portal/server syncs their data
        self.handshakes = 8  # suppress-go-ahead, naws, ttype, mccp, mssp, msdp, gmcp, mxp

        self.init_session(self.protocol_key, client_address, self.factory.sessionhandler)
        self.protocol_flags["ENCODING"] = settings.ENCODINGS[0] if settings.ENCODINGS else "utf-8"
        # add this new connection to sessionhandler so
        # the Server becomes aware of it.
        self.sessionhandler.connect(self)
        # change encoding to ENCODINGS[0] which reflects Telnet default encoding

        # suppress go-ahead
        self.sga = suppress_ga.SuppressGA(self)
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

        from evennia.utils.utils import delay

        # timeout the handshakes in case the client doesn't reply at all
        self._handshake_delay = delay(2, callback=self.handshake_done, timeout=True)

        # TCP/IP keepalive watches for dead links
        self.transport.setTcpKeepAlive(1)
        # The TCP/IP keepalive is not enough for some networks;
        # we have to complement it with a NOP keep-alive.
        self.protocol_flags["NOPKEEPALIVE"] = True
        self.nop_keep_alive = None
        self.toggle_nop_keepalive()

    def _send_nop_keepalive(self):
        """Send NOP keepalive unless flag is set"""
        if self.protocol_flags.get("NOPKEEPALIVE"):
            self._write(IAC + NOP)

    def toggle_nop_keepalive(self):
        """
        Allow to toggle the NOP keepalive for those sad clients that
        can't even handle a NOP instruction. This is turned off by the
        protocol_flag NOPKEEPALIVE (settable e.g. by the default
        `@option` command).
        """
        if self.nop_keep_alive and self.nop_keep_alive.running:
            self.nop_keep_alive.stop()
        else:
            self.nop_keep_alive = LoopingCall(self._send_nop_keepalive)
            self.nop_keep_alive.start(30, now=False)

    def handshake_done(self, timeout=False):
        """
        This is called by all telnet extensions once they are finished.
        When all have reported, a sync with the server is performed.
        The system will force-call this sync after a small time to handle
        clients that don't reply to handshakes at all.
        """
        if timeout:
            if self.handshakes > 0:
                self.handshakes = 0
                self.sessionhandler.sync(self)
        else:
            self.handshakes -= 1
            if self.handshakes <= 0:
                # do the sync
                self.sessionhandler.sync(self)

    def at_login(self):
        """
        Called when this session gets authenticated by the server.
        """
        pass

    def enableRemote(self, option):
        """
        This sets up the remote-activated options we allow for this protocol.

        Args:
            option (char): The telnet option to enable.

        Returns:
            enable (bool): If this option should be enabled.

        """
        if option == LINEMODE:
            # make sure to activate line mode with local editing for all clients
            self.requestNegotiation(
                LINEMODE, MODE + bytes(chr(ord(LINEMODE_EDIT) + ord(LINEMODE_TRAPSIG)), "ascii")
            )
            return True
        else:
            return (
                option == ttype.TTYPE
                or option == naws.NAWS
                or option == MCCP
                or option == mssp.MSSP
                or option == suppress_ga.SUPPRESS_GA
            )

    def enableLocal(self, option):
        """
        Call to allow the activation of options for this protocol

        Args:
            option (char): The telnet option to enable locally.

        Returns:
            enable (bool): If this option should be enabled.

        """
        return (
            option == LINEMODE
            or option == MCCP
            or option == ECHO
            or option == suppress_ga.SUPPRESS_GA
        )

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
            return super().disableLocal(option)

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

    def applicationDataReceived(self, data):
        """
        Telnet method called when non-telnet-command data is coming in
        over the telnet connection. We pass it on to the game engine
        directly.

        Args:
            data (str): Incoming data.

        """
        if not data:
            data = [data]
        elif data.strip() == NULL:
            # this is an ancient type of keepalive used by some
            # legacy clients. There should never be a reason to send a
            # lone NULL character so this seems to be a safe thing to
            # support for backwards compatibility. It also stops the
            # NULL from continuously popping up as an unknown command.
            data = [_IDLE_COMMAND]
        else:
            data = _RE_LINEBREAK.split(data)
            if self.line_buffer and len(data) > 1:
                # buffer exists, it is terminated by the first line feed
                data[0] = self.line_buffer + data[0]
                self.line_buffer = b""
            # if the last data split is empty, it means all splits have
            # line breaks, if not, it is unterminated and must be
            # buffered.
            self.line_buffer += data.pop()
        # send all data chunks
        for dat in data:
            self.data_in(text=dat + b"\n")

    def _write(self, data):
        """hook overloading the one used in plain telnet"""
        data = data.replace(b"\n", b"\r\n").replace(b"\r\r\n", b"\r\n")
        super()._write(mccp_compress(self, data))

    def sendLine(self, line):
        """
        Hook overloading the one used by linereceiver.

        Args:
            line (str): Line to send.

        """
        line = to_bytes(line, self)
        # escape IAC in line mode, and correctly add \r\n (the TELNET end-of-line)
        line = line.replace(IAC, IAC + IAC)
        line = line.replace(b"\n", b"\r\n")
        if not line.endswith(b"\r\n") and self.protocol_flags.get("FORCEDENDLINE", True):
            line += b"\r\n"
        if not self.protocol_flags.get("NOGOAHEAD", True):
            line += IAC + GA
        return self.transport.write(mccp_compress(self, line))

    # Session hooks

    def disconnect(self, reason=""):
        """
        generic hook for the engine to call in order to
        disconnect this protocol.

        Args:
            reason (str, optional): Reason for disconnecting.

        """
        self.data_out(text=((reason,), {}))
        self.connectionLost(reason)

    def data_in(self, **kwargs):
        """
        Data User -> Evennia

        Kwargs:
            kwargs (any): Options from the protocol.

        """
        # from evennia.server.profiling.timetrace import timetrace  # DEBUG
        # text = timetrace(text, "telnet.data_in")  # DEBUG

        self.sessionhandler.data_in(self, **kwargs)

    def data_out(self, **kwargs):
        """
        Data Evennia -> User

        Kwargs:
            kwargs (any): Options to the protocol
        """
        self.sessionhandler.data_out(self, **kwargs)

    # send_* methods

    def send_text(self, *args, **kwargs):
        """
        Send text data. This is an in-band telnet operation.

        Args:
            text (str): The first argument is always the text string to send. No other arguments
                are considered.
        Kwargs:
            options (dict): Send-option flags
                   - mxp: Enforce MXP link support.
                   - ansi: Enforce no ANSI colors.
                   - xterm256: Enforce xterm256 colors, regardless of TTYPE.
                   - noxterm256: Enforce no xterm256 color support, regardless of TTYPE.
                   - nocolor: Strip all Color, regardless of ansi/xterm256 setting.
                   - raw: Pass string through without any ansi processing
                        (i.e. include Evennia ansi markers but do not
                        convert them into ansi tokens)
                   - echo: Turn on/off line echo on the client. Turn
                        off line echo for client, for example for password.
                        Note that it must be actively turned back on again!

        """
        text = args[0] if args else ""
        if text is None:
            return

        # handle arguments
        options = kwargs.get("options", {})
        flags = self.protocol_flags
        xterm256 = options.get(
            "xterm256", flags.get("XTERM256", False) if flags.get("TTYPE", False) else True
        )
        useansi = options.get(
            "ansi", flags.get("ANSI", False) if flags.get("TTYPE", False) else True
        )
        raw = options.get("raw", flags.get("RAW", False))
        nocolor = options.get("nocolor", flags.get("NOCOLOR") or not (xterm256 or useansi))
        echo = options.get("echo", None)
        mxp = options.get("mxp", flags.get("MXP", False))
        screenreader = options.get("screenreader", flags.get("SCREENREADER", False))

        if screenreader:
            # screenreader mode cleans up output
            text = ansi.parse_ansi(text, strip_ansi=True, xterm256=False, mxp=False)
            text = _RE_SCREENREADER_REGEX.sub("", text)

        if options.get("send_prompt"):
            # send a prompt instead.
            prompt = text
            if not raw:
                # processing
                prompt = ansi.parse_ansi(
                    _RE_N.sub("", prompt) + ("||n" if prompt.endswith("|") else "|n"),
                    strip_ansi=nocolor,
                    xterm256=xterm256,
                )
                if mxp:
                    prompt = mxp_parse(prompt)
            prompt = to_bytes(prompt, self)
            prompt = prompt.replace(IAC, IAC + IAC).replace(b"\n", b"\r\n")
            prompt += IAC + GA
            self.transport.write(mccp_compress(self, prompt))
        else:
            if echo is not None:
                # turn on/off echo. Note that this is a bit turned around since we use
                # echo as if we are "turning off the client's echo" when telnet really
                # handles it the other way around.
                if echo:
                    # by telling the client that WE WON'T echo, the client knows
                    # that IT should echo. This is the expected behavior from
                    # our perspective.
                    self.transport.write(mccp_compress(self, IAC + WONT + ECHO))
                else:
                    # by telling the client that WE WILL echo, the client can
                    # safely turn OFF its OWN echo.
                    self.transport.write(mccp_compress(self, IAC + WILL + ECHO))
            if raw:
                # no processing
                self.sendLine(text)
                return
            else:
                # we need to make sure to kill the color at the end in order
                # to match the webclient output.
                linetosend = ansi.parse_ansi(
                    _RE_N.sub("", text) + ("||n" if text.endswith("|") else "|n"),
                    strip_ansi=nocolor,
                    xterm256=xterm256,
                    mxp=mxp,
                )
                if mxp:
                    linetosend = mxp_parse(linetosend)
                self.sendLine(linetosend)

    def send_prompt(self, *args, **kwargs):
        """
        Send a prompt - a text without a line end. See send_text for argument options.

        """
        kwargs["options"].update({"send_prompt": True})
        self.send_text(*args, **kwargs)

    def send_default(self, cmdname, *args, **kwargs):
        """
        Send other oob data
        """
        if not cmdname == "options":
            self.oob.data_out(cmdname, *args, **kwargs)
