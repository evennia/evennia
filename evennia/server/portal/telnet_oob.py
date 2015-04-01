"""

Telnet OOB (Out of band communication)

This implements the following telnet oob protocols:
MSDP (Mud Server Data Protocol)
GMCP (Generic Mud Communication Protocol)

This implements the MSDP protocol as per
http://tintin.sourceforge.net/msdp/ and the GMCP protocol as per
http://www.ironrealms.com/rapture/manual/files/FeatGMCP-txt.html#Generic_MUD_Communication_Protocol%28GMCP%29

Following the lead of KaVir's protocol snippet, we first check if
client supports MSDP and if not, we fallback to GMCP with a MSDP
header where applicable.

OOB manages out-of-band
communication between the client and server, for updating health bars
etc. See also GMCP which is another standard doing the same thing.

"""
import re
import json
from evennia.utils.utils import to_str

# MSDP-relevant telnet cmd/opt-codes
MSDP = chr(69)
MSDP_VAR = chr(1)
MSDP_VAL = chr(2)
MSDP_TABLE_OPEN = chr(3)
MSDP_TABLE_CLOSE = chr(4)
MSDP_ARRAY_OPEN = chr(5)
MSDP_ARRAY_CLOSE = chr(6)

# GMCP
GMCP = chr(201)

# General Telnet
IAC = chr(255)
SB = chr(250)
SE = chr(240)

force_str = lambda inp: to_str(inp, force_string=True)

# pre-compiled regexes
# returns 2-tuple
msdp_regex_array = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL,
                                                  MSDP_ARRAY_OPEN,
                                                  MSDP_ARRAY_CLOSE))
# returns 2-tuple (may be nested)
msdp_regex_table = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL,
                                                  MSDP_TABLE_OPEN,
                                                  MSDP_TABLE_CLOSE))
msdp_regex_var = re.compile(MSDP_VAR)
msdp_regex_val = re.compile(MSDP_VAL)

# Msdp object handler

class TelnetOOB(object):
    """
    Implements the MSDP and GMCP protocols.
    """

    def __init__(self, protocol):
        """
        Initiates by storing the protocol
        on itself and trying to determine
        if the client supports MSDP.
        """
        self.protocol = protocol
        self.protocol.protocol_flags['OOB'] = False
        self.MSDP = False
        self.GMCP = False
        # ask for the available protocols and assign decoders
        # (note that handshake_done() will be called twice!)
        self.protocol.negotiationMap[MSDP] = self.decode_msdp
        self.protocol.negotiationMap[GMCP] = self.decode_gmcp
        self.protocol.will(MSDP).addCallbacks(self.do_msdp, self.no_msdp)
        self.protocol.will(GMCP).addCallbacks(self.do_gmcp, self.no_gmcp)
        self.oob_reported = {}

    def no_msdp(self, option):
        "No msdp supported or wanted"
        # no msdp, check GMCP
        self.protocol.handshake_done()

    def do_msdp(self, option):
        "MSDP supported by client"
        self.MSDP = True
        self.protocol.protocol_flags['OOB'] = True
        self.protocol.handshake_done()

    def no_gmcp(self, option):
        "Neither MSDP nor GMCP supported"
        self.protocol.handshake_done()

    def do_gmcp(self, option):
        """
        Called when client confirms that it can do MSDP or GMCP.
        """
        self.GMCP = True
        self.protocol.protocol_flags['OOB'] = True
        self.protocol.handshake_done()

    # encoders

    def encode_msdp(self, cmdname, *args, **kwargs):
        """
        handle return data from cmdname by converting it to
        a proper msdp structure. These are the combinations we
        support:

        cmdname string    ->  cmdname string
        cmdname *args  -> cmdname MSDP_ARRAY
        cmdname **kwargs -> cmdname MSDP_TABLE

        # send 'raw' data structures
        MSDP_ARRAY *args -> MSDP_ARRAY
        MSDP_TABLE **kwargs -> MSDP_TABLE

        """
        msdp_string = ""
        if args:
            if cmdname == "MSDP_ARRAY":
                msdp_string = "".join(["%s%s" % (MSDP_VAL, val) for val in args])
            else:
                msdp_string = "%s%s%s" % (MSDP_VAR, cmdname, "".join(
                                            "%s%s" % (MSDP_VAL, val) for val in args))
        elif kwargs:
            if cmdname == "MSDP_TABLE":
                msdp_string = "".join(["%s%s%s%s" % (MSDP_VAR, key, MSDP_VAL, val)
                                        for key, val in kwargs.items()])
            else:
                msdp_string = "%s%s%s" % (MSDP_VAR. cmdname, "".join(
                    ["%s%s%s%s" % (MSDP_VAR, key, MSDP_VAL, val) for key, val in kwargs.items()]))
        #print "encode msdp result:", cmdname, args, kwargs, "->", msdp_string
        return force_str(msdp_string)

    def encode_gmcp(self, cmdname, *args, **kwargs):
        """
        Gmcp messages are on one of the following outgoing forms:

        cmdname string -> cmdname string
        cmdname *args -> cmdname [arg, arg, arg, ...]
        cmdname **kwargs -> cmdname {key:arg, key:arg, ...}

        cmdname is generally recommended to be a string on the form
        Module.Submodule.Function
        """
        if cmdname in ("SEND", "REPORT", "UNREPORT", "LIST"):
            # we wrap the standard MSDP commands in a MSDP.submodule
            # here as far as GMCP is concerned.
            cmdname = "MSDP.%s" % cmdname
        elif cmdname in ("MSDP_ARRAY", "MSDP_TABLE"):
            # no cmdname should accompany these, just the MSDP wrapper
            cmdname = "MSDP"

        gmcp_string = ""
        if args:
            gmcp_string = "%s %s" % (cmdname, json.dumps(args))
        elif kwargs:
            gmcp_string = "%s %s" % (cmdname, json.dumps(kwargs))
        #print "gmcp_encode", cmdname, args, kwargs, "->", gmcp_string
        return force_str(gmcp_string).strip()

    def decode_msdp(self, data):
        """
        Decodes incoming MSDP data

        cmdname var  --> cmdname arg
        cmdname array --> cmdname *args
        cmdname table --> cmdname **kwargs

        """
        tables = {}
        arrays = {}
        variables = {}

        if hasattr(data, "__iter__"):
            data = "".join(data)

        # decode
        for key, table in msdp_regex_table.findall(data):
            tables[key] = {}
            for varval in msdp_regex_var.split(table):
                parts = msdp_regex_val.split(varval)
                tables[key].expand({parts[0]: tuple(parts[1:]) if len(parts) > 1 else ("",)})
        for key, array in msdp_regex_array.findall(data):
            arrays[key] = []
            for val in msdp_regex_val.split(array):
                arrays[key].append(val)
            arrays[key] = tuple(arrays[key])
        for varval in msdp_regex_var.split(msdp_regex_array.sub("", msdp_regex_table.sub("", data))):
            # get remaining varvals after cleaning away tables/arrays
            parts = msdp_regex_val.split(varval)
            variables[parts[0]] = tuple(parts[1:]) if len(parts) > 1 else ("", )

        #print "OOB: MSDP decode:", data, "->", variables, arrays, tables

        # send to the sessionhandler
        if data:
            for varname, var in variables.items():
                # a simple function + argument
                self.protocol.data_in(oob=(varname, var, {}))
            for arrayname, array in arrays.items():
                # we assume the array are multiple arguments to the function
                self.protocol.data_in(oob=(arrayname, array, {}))
            for tablename, table in tables.items():
                # we assume tables are keyword arguments to the function
                self.protocol.data_in(oob=(tablename, (), table))

    def decode_gmcp(self, data):
        """
        Decodes incoming GMCP data on the form 'varname <structure>'

        cmdname string -> cmdname arg
        cmdname [arg, arg,...] -> cmdname *args
        cmdname {key:arg, key:arg, ...} -> cmdname **kwargs

        """
        if hasattr(data, "__iter__"):
            data = "".join(data)

        #print "decode_gmcp:", data
        if data:
            splits = data.split(None, 1)
            cmdname = splits[0]
            if len(splits) < 2:
                self.protocol.data_in(oob=(cmdname, (), {}))
            elif splits[1]:
                try:
                    struct = json.loads(splits[1])
                except ValueError:
                    struct = splits[1]
                args, kwargs = (), {}
                if hasattr(struct, "__iter__"):
                    if isinstance(struct, dict):
                        kwargs = struct
                    else:
                        args = tuple(struct)
                else:
                    args = (struct,)
                #print "gmcp decode:", data, "->", cmdname, args, kwargs
                self.protocol.data_in(oob=(cmdname, args, kwargs))

    # access methods

    def data_out(self, cmdname, *args, **kwargs):
        """
        Return a msdp-valid subnegotiation across the protocol.
        """
        #print "data_out:", encoded_oob
        if self.MSDP:
            encoded_oob = self.encode_msdp(cmdname, *args, **kwargs)
            self.protocol._write(IAC + SB + MSDP + encoded_oob + IAC + SE)
        if self.GMCP:
            encoded_oob = self.encode_gmcp(cmdname, *args, **kwargs)
            self.protocol._write(IAC + SB + GMCP + encoded_oob + IAC + SE)
