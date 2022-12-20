"""
TTYPE (MTTS) - Mud Terminal Type Standard

This module implements the TTYPE telnet protocol as per
http://tintin.sourceforge.net/mtts/. It allows the server to ask the
client about its capabilities. If the client also supports TTYPE, it
will return with information such as its name, if it supports colour
etc. If the client does not support TTYPE, this will be ignored.

All data will be stored on the protocol's protocol_flags dictionary,
under the 'TTYPE' key.

"""

# telnet option codes
TTYPE = bytes([24])  # b"\x18"
IS = bytes([0])  # b"\x00"
SEND = bytes([1])  # b"\x01"

# terminal capabilities and their codes
MTTS = [
    (128, "PROXY"),
    (64, "SCREENREADER"),
    (32, "OSC_COLOR_PALETTE"),
    (16, "MOUSE_TRACKING"),
    (8, "XTERM256"),
    (4, "UTF-8"),
    (2, "VT100"),
    (1, "ANSI"),
]


class Ttype:
    """
    Handles ttype negotiations. Called and initiated by the
    telnet protocol.

    """

    def __init__(self, protocol):
        """
        Initialize ttype by storing protocol on ourselves and calling
        the client to see if it supporst ttype.

        Args:
            protocol (Protocol): The protocol instance.

        Notes:
            The `self.ttype_step` indicates how far in the data
            retrieval we've gotten.

        """
        self.ttype_step = 0
        self.protocol = protocol
        # we set FORCEDENDLINE for clients not supporting ttype
        self.protocol.protocol_flags["FORCEDENDLINE"] = True
        self.protocol.protocol_flags["TTYPE"] = False
        # is it a safe bet to assume ANSI is always supported?
        self.protocol.protocol_flags["ANSI"] = True
        # setup protocol to handle ttype initialization and negotiation
        self.protocol.negotiationMap[TTYPE] = self.will_ttype
        # ask if client will ttype, connect callback if it does.
        self.protocol.do(TTYPE).addCallbacks(self.will_ttype, self.wont_ttype)

    def wont_ttype(self, option):
        """
        Callback if ttype is not supported by client.

        Args:
            option (Option): Not used.

        """
        self.protocol.protocol_flags["TTYPE"] = False
        self.protocol.handshake_done()

    def will_ttype(self, option):
        """
        Handles negotiation of the ttype protocol once the client has
        confirmed that it will respond with the ttype protocol.

        Args:
            option (Option): Not used.

        Notes:
            The negotiation proceeds in several steps, each returning a
            certain piece of information about the client. All data is
            stored on protocol.protocol_flags under the TTYPE key.

        """
        options = self.protocol.protocol_flags

        if options and options.get("TTYPE", False) or self.ttype_step > 3:
            return

        try:
            option = b"".join(option).lstrip(IS).decode()
        except TypeError:
            # option is not on a suitable form for joining
            pass

        if self.ttype_step == 0:
            # just start the request chain
            self.protocol.requestNegotiation(TTYPE, SEND)

        elif self.ttype_step == 1:
            # this is supposed to be the name of the client/terminal.
            # For clients not supporting the extended TTYPE
            # definition, subsequent calls will just repeat-return this.
            try:
                clientname = option.upper()
            except AttributeError:
                # malformed option (not a string)
                clientname = "UNKNOWN"

            # use name to identify support for xterm256. Many of these
            # only support after a certain version, but all support
            # it since at least 4 years. We assume recent client here for now.
            xterm256 = False
            if clientname.startswith("MUDLET"):
                # supports xterm256 stably since 1.1 (2010?)
                xterm256 = clientname.split("MUDLET", 1)[1].strip() >= "1.1"
                # Mudlet likes GA's on a prompt line for the prompt trigger to
                # match, if it's not wanting NOGOAHEAD.
                if not self.protocol.protocol_flags["NOGOAHEAD"]:
                    self.protocol.protocol_flags["NOGOAHEAD"] = True
                    self.protocol.protocol_flags["NOPROMPTGOAHEAD"] = False

            if (
                clientname.startswith("XTERM")
                or clientname.endswith("-256COLOR")
                or clientname
                in (
                    "ATLANTIS",  # > 0.9.9.0 (aug 2009)
                    "CMUD",  # > 3.04 (mar 2009)
                    "KILDCLIENT",  # > 2.2.0 (sep 2005)
                    "MUDLET",  # > beta 15 (sep 2009)
                    "MUSHCLIENT",  # > 4.02 (apr 2007)
                    "PUTTY",  # > 0.58 (apr 2005)
                    "BEIP",  # > 2.00.206 (late 2009) (BeipMu)
                    "POTATO",  # > 2.00 (maybe earlier)
                    "TINYFUGUE",  # > 4.x (maybe earlier)
                )
            ):
                xterm256 = True

            # all clients supporting TTYPE at all seem to support ANSI
            self.protocol.protocol_flags["ANSI"] = True
            self.protocol.protocol_flags["XTERM256"] = xterm256
            self.protocol.protocol_flags["CLIENTNAME"] = clientname
            self.protocol.requestNegotiation(TTYPE, SEND)

        elif self.ttype_step == 2:
            # this is a term capabilities flag
            term = option
            tupper = term.upper()
            # identify xterm256 based on flag
            xterm256 = (
                tupper.endswith("-256COLOR")
                or tupper.endswith("XTERM")  # Apple Terminal, old Tintin
                and not tupper.endswith("-COLOR")  # old Tintin, Putty
            )
            if xterm256:
                self.protocol.protocol_flags["ANSI"] = True
                self.protocol.protocol_flags["XTERM256"] = xterm256
            self.protocol.protocol_flags["TERM"] = term
            # request next information
            self.protocol.requestNegotiation(TTYPE, SEND)

        elif self.ttype_step == 3:
            # the MTTS bitstring identifying term capabilities
            if option.startswith("MTTS"):
                option = option[4:].strip()
                if option.isdigit():
                    # a number - determine the actual capabilities
                    option = int(option)
                    support = dict(
                        (capability, True) for bitval, capability in MTTS if option & bitval > 0
                    )
                    self.protocol.protocol_flags.update(support)
                else:
                    # some clients send erroneous MTTS as a string. Add directly.
                    self.protocol.protocol_flags[option.upper()] = True

            self.protocol.protocol_flags["TTYPE"] = True
            # we must sync ttype once it'd done
            self.protocol.handshake_done()
        self.ttype_step += 1
