"""

Telnet OOB (Out of band communication)

OOB protocols allow for asynchronous communication between Evennia and
compliant telnet clients. The "text" type of send command will always
be sent "in-band", appearing in the client's main text output. OOB
commands, by contrast, can have many forms and it is up to the client
how and if they are handled.  Examples of OOB instructions could be to
instruct the client to play sounds or to update a graphical health
bar.

> Note that in Evennia's Web client, all send commands are "OOB
commands", (including the "text" one), there is no equivalence to
MSDP/GMCP for the webclient since it doesn't need it.

This implements the following telnet OOB communication protocols:
- MSDP (Mud Server Data Protocol), as per
    http://tintin.sourceforge.net/msdp/
- GMCP (Generic Mud Communication Protocol) as per
    http://www.ironrealms.com/rapture/manual/files/FeatGMCP-txt.html#Generic_MUD_Communication_Protocol%28GMCP%29

Following the lead of KaVir's protocol snippet, we first check if
client supports MSDP and if not, we fallback to GMCP with a MSDP
header where applicable.

"""
from builtins import object
import re
import json
from evennia.utils.utils import to_str

# MSDP-relevant telnet cmd/opt-codes
MSDP = chr(69)
MSDP_VAR = chr(1)          # ^A
MSDP_VAL = chr(2)          # ^B
MSDP_TABLE_OPEN = chr(3)   # ^C
MSDP_TABLE_CLOSE = chr(4)  # ^D
MSDP_ARRAY_OPEN = chr(5)   # ^E
MSDP_ARRAY_CLOSE = chr(6)  # ^F

# GMCP
GMCP = chr(201)

# General Telnet
IAC = chr(255)
SB = chr(250)
SE = chr(240)


def force_str(inp):
    """Helper to shorten code"""
    return to_str(inp, force_string=True)


# pre-compiled regexes
# returns 2-tuple
msdp_regex_table = re.compile(r"%s\s*(\w*?)\s*%s\s*%s(.*?)%s"
                              % (MSDP_VAR, MSDP_VAL,
                                 MSDP_TABLE_OPEN,
                                 MSDP_TABLE_CLOSE))
# returns 2-tuple
msdp_regex_array = re.compile(r"%s\s*(\w*?)\s*%s\s*%s(.*?)%s"
                              % (MSDP_VAR, MSDP_VAL,
                                 MSDP_ARRAY_OPEN,
                                 MSDP_ARRAY_CLOSE))
msdp_regex_var = re.compile(r"%s" % MSDP_VAR)
msdp_regex_val = re.compile(r"%s" % MSDP_VAL)

EVENNIA_TO_GMCP = {"client_options": "Core.Supports.Get",
                   "get_inputfuncs": "Core.Commands.Get",
                   "get_value": "Char.Value.Get",
                   "repeat": "Char.Repeat.Update",
                   "monitor": "Char.Monitor.Update"}


# MSDP/GMCP communication handler

class TelnetOOB(object):
    """
    Implements the MSDP and GMCP protocols.
    """

    def __init__(self, protocol):
        """
        Initiates by storing the protocol on itself and trying to
        determine if the client supports MSDP.

        Args:
            protocol (Protocol): The active protocol.

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
        """
        Client reports No msdp supported or wanted.

        Args:
            option (Option): Not used.

        """
        # no msdp, check GMCP
        self.protocol.handshake_done()

    def do_msdp(self, option):
        """
        Client reports that it supports msdp.

        Args:
            option (Option): Not used.

        """
        self.MSDP = True
        self.protocol.protocol_flags['OOB'] = True
        self.protocol.handshake_done()

    def no_gmcp(self, option):
        """
        If this is reached, it means neither MSDP nor GMCP is
        supported.

        Args:
            option (Option): Not used.

        """
        self.protocol.handshake_done()

    def do_gmcp(self, option):
        """
        Called when client confirms that it can do MSDP or GMCP.

        Args:
            option (Option): Not used.

        """
        self.GMCP = True
        self.protocol.protocol_flags['OOB'] = True
        self.protocol.handshake_done()

    # encoders

    def encode_msdp(self, cmdname, *args, **kwargs):
        """
        Encode into a valid MSDP command.

        Args:
            cmdname (str): Name of send instruction.
            args, kwargs (any): Arguments to OOB command.

        Notes:
            The output of this encoding will be
            MSDP structures on these forms:

            [cmdname, [], {}]          -> VAR cmdname VAL ""
            [cmdname, [arg], {}]       -> VAR cmdname VAL arg
            [cmdname, [args],{}]       -> VAR cmdname VAL ARRAYOPEN VAL arg VAL arg ... ARRAYCLOSE
            [cmdname, [], {kwargs}]    -> VAR cmdname VAL TABLEOPEN VAR key VAL val ... TABLECLOSE
            [cmdname, [args], {kwargs}] -> VAR cmdname VAL ARRAYOPEN VAL arg VAL arg ... ARRAYCLOSE
                                           VAR cmdname VAL TABLEOPEN VAR key VAL val ... TABLECLOSE

            Further nesting is not supported, so if an array argument
            consists of an array (for example), that array will be
            json-converted to a string.

        """
        msdp_cmdname = "{msdp_var}{msdp_cmdname}{msdp_val}".format(
                    msdp_var=MSDP_VAR, msdp_cmdname=cmdname, msdp_val=MSDP_VAL)

        if not (args or kwargs):
            return msdp_cmdname

        # print("encode_msdp in:", cmdname, args, kwargs)  # DEBUG

        msdp_args = ''
        if args:
            msdp_args = msdp_cmdname
            if len(args) == 1:
                msdp_args += args[0]
            else:
                msdp_args += "{msdp_array_open}" \
                             "{msdp_args}" \
                             "{msdp_array_close}".format(
                                                         msdp_array_open=MSDP_ARRAY_OPEN,
                                                         msdp_array_close=MSDP_ARRAY_CLOSE,
                                                         msdp_args="".join("%s%s"
                                                                           % (MSDP_VAL, json.dumps(val))
                                                                           for val in args))

        msdp_kwargs = ""
        if kwargs:
            msdp_kwargs = msdp_cmdname
            msdp_kwargs += "{msdp_table_open}" \
                           "{msdp_kwargs}" \
                           "{msdp_table_close}".format(
                                                       msdp_table_open=MSDP_TABLE_OPEN,
                                                       msdp_table_close=MSDP_TABLE_CLOSE,
                                                       msdp_kwargs="".join("%s%s%s%s"
                                                                           % (MSDP_VAR, key, MSDP_VAL,
                                                                              json.dumps(val))
                                                                           for key, val in kwargs.iteritems()))

        msdp_string = msdp_args + msdp_kwargs

        # print("msdp_string:", msdp_string)  # DEBUG
        return msdp_string

    def encode_gmcp(self, cmdname, *args, **kwargs):
        """
        Encode into GMCP messages.

        Args:
            cmdname (str): GMCP OOB command name.
            args, kwargs (any): Arguments to OOB command.

        Notes:
            GMCP messages will be outgoing on the following
            form (the non-JSON cmdname at the start is what
            IRE games use, supposedly, and what clients appear
            to have adopted):

            [cmdname, [], {}]          -> cmdname
            [cmdname, [arg], {}]       -> cmdname arg
            [cmdname, [args],{}]       -> cmdname [args]
            [cmdname, [], {kwargs}]    -> cmdname {kwargs}
            [cmdname, [args, {kwargs}] -> cmdname [[args],{kwargs}]

        """
        if not (args or kwargs):
            gmcp_string = cmdname
        elif args:
            if len(args) == 1:
                args = args[0]
            if kwargs:
                gmcp_string = "%s %s" % (cmdname, json.dumps([args, kwargs]))
            else:
                gmcp_string = "%s %s" % (cmdname, json.dumps(args))
        else:  # only kwargs
            gmcp_string = "%s %s" % (cmdname, json.dumps(kwargs))

        # print("gmcp string", gmcp_string)  # DEBUG
        return gmcp_string

    def decode_msdp(self, data):
        """
        Decodes incoming MSDP data.

        Args:
            data (str or list): MSDP data.

        Notes:
            Clients should always send MSDP data on
            one of the following forms:

            cmdname ''          -> [cmdname, [], {}]
            cmdname val         -> [cmdname, [val], {}]
            cmdname array       -> [cmdname, [array], {}]
            cmdname table       -> [cmdname, [], {table}]
            cmdname array cmdname table -> [cmdname, [array], {table}]

            Observe that all MSDP_VARS are used to identify cmdnames,
            so if there are multiple arrays with the same cmdname
            given, they will be merged into one argument array, same
            for tables. Different MSDP_VARS (outside tables) will be
            identified as separate cmdnames.

        """
        if hasattr(data, "__iter__"):
            data = "".join(data)

        # print("decode_msdp in:", data)  # DEBUG

        tables = {}
        arrays = {}
        variables = {}

        # decode tables
        for key, table in msdp_regex_table.findall(data):
            tables[key] = {} if key not in tables else tables[key]
            for varval in msdp_regex_var.split(table)[1:]:
                var, val = msdp_regex_val.split(varval, 1)
                if var:
                    tables[key][var] = val

        # decode arrays from all that was not a table
        data_no_tables = msdp_regex_table.sub("", data)
        for key, array in msdp_regex_array.findall(data_no_tables):
            arrays[key] = [] if key not in arrays else arrays[key]
            parts = msdp_regex_val.split(array)
            if len(parts) == 2:
                arrays[key].append(parts[1])
            elif len(parts) > 1:
                arrays[key].extend(parts[1:])

        # decode remainders from all that were not tables or arrays
        data_no_tables_or_arrays = msdp_regex_array.sub("", data_no_tables)
        for varval in msdp_regex_var.split(data_no_tables_or_arrays):
            # get remaining varvals after cleaning away tables/arrays. If mathcing
            # an existing key in arrays, it will be added as an argument to that command,
            # otherwise it will be treated as a command without argument.
            parts = msdp_regex_val.split(varval)
            if len(parts) == 2:
                variables[parts[0]] = parts[1]
            elif len(parts) > 1:
                variables[parts[0]] = parts[1:]

        cmds = {}
        # merge matching table/array/variables together
        for key, table in tables.iteritems():
            args, kwargs = [], table
            if key in arrays:
                args.extend(arrays.pop(key))
            if key in variables:
                args.append(variables.pop(key))
            cmds[key] = [args, kwargs]

        for key, arr in arrays.iteritems():
            args, kwargs = arr, {}
            if key in variables:
                args.append(variables.pop(key))
            cmds[key] = [args, kwargs]

        for key, var in variables.iteritems():
            cmds[key] = [[var], {}]

        # print("msdp data in:", cmds)  # DEBUG
        self.protocol.data_in(**cmds)

    def decode_gmcp(self, data):
        """
        Decodes incoming GMCP data on the form 'varname <structure>'.

        Args:
            data (str or list): GMCP data.

        Notes:
            Clients send data on the form "Module.Submodule.Cmdname <structure>".
            We assume the structure is valid JSON.

            The following is parsed into Evennia's formal structure:

            Core.Name                         -> [name, [], {}]
            Core.Name string                  -> [name, [string], {}]
            Core.Name [arg, arg,...]          -> [name, [args], {}]
            Core.Name {key:arg, key:arg, ...} -> [name, [], {kwargs}]
            Core.Name [[args], {kwargs}]      -> [name, [args], {kwargs}]

        """
        if hasattr(data, "__iter__"):
            data = "".join(data)

        # print("decode_gmcp in:", data)  # DEBUG
        if data:
            try:
                cmdname, structure = data.split(None, 1)
            except ValueError:
                cmdname, structure = data, ""
            cmdname = cmdname.replace(".", "_")
            try:
                structure = json.loads(structure)
            except ValueError:
                # maybe the structure is not json-serialized at all
                pass
            args, kwargs = [], {}
            if hasattr(structure, "__iter__"):
                if isinstance(structure, dict):
                    kwargs = {key: value for key, value in structure.iteritems() if key}
                else:
                    args = list(structure)
            else:
                args = (structure,)
            if cmdname.lower().startswith("core_"):
                # if Core.cmdname, then use cmdname
                cmdname = cmdname[5:]
            self.protocol.data_in(**{cmdname.lower(): [args, kwargs]})

    # access methods

    def data_out(self, cmdname, *args, **kwargs):
        """
        Return a MSDP- or GMCP-valid subnegotiation across the protocol.

        Args:
            cmdname (str): OOB-command name.
            args, kwargs (any): Arguments to OOB command.

        """
        kwargs.pop("options", None)

        if self.MSDP:
            msdp_cmdname = cmdname
            encoded_oob = self.encode_msdp(msdp_cmdname, *args, **kwargs)
            self.protocol._write(IAC + SB + MSDP + encoded_oob + IAC + SE)

        if self.GMCP:
            if cmdname in EVENNIA_TO_GMCP:
                gmcp_cmdname = EVENNIA_TO_GMCP[cmdname]
            else:
                gmcp_cmdname = "Custom.Cmd"
            encoded_oob = self.encode_gmcp(gmcp_cmdname, *args, **kwargs)
            self.protocol._write(IAC + SB + GMCP + encoded_oob + IAC + SE)
