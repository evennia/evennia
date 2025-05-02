"""

Telnet OOB (Out of band communication)

OOB protocols allow for asynchronous communication between Evennia and
compliant telnet clients. The "text" type of send command will always
be sent "in-band", appearing in the client's main text output. OOB
commands, by contrast, can have many forms and it is up to the client
how and if they are handled.  Examples of OOB instructions could be to
instruct the client to play sounds or to update a graphical health
bar.

Note that in Evennia's Web client, all send commands are "OOB
commands", (including the "text" one), there is no equivalence to
MSDP/GMCP for the webclient since it doesn't need it.

This implements the following telnet OOB communication protocols:

- MSDP (Mud Server Data Protocol), as per http://tintin.sourceforge.net/msdp/
- GMCP (Generic Mud Communication Protocol) as per
  http://www.ironrealms.com/rapture/manual/files/FeatGMCP-txt.html#Generic_MUD_Communication_Protocol%28GMCP%29

----

"""

import json
import re
import weakref

# General Telnet
from twisted.conch.telnet import IAC, SB, SE

from evennia.utils.utils import is_iter

# MSDP-relevant telnet cmd/opt-codes
MSDP = bytes([69])
MSDP_VAR = bytes([1])
MSDP_VAL = bytes([2])
MSDP_TABLE_OPEN = bytes([3])
MSDP_TABLE_CLOSE = bytes([4])

MSDP_ARRAY_OPEN = bytes([5])
MSDP_ARRAY_CLOSE = bytes([6])

# GMCP
GMCP = bytes([201])


# pre-compiled regexes
# returns 2-tuple
msdp_regex_table = re.compile(
    rb"%s\s*(\w*?)\s*%s\s*%s(.*?)%s" % (MSDP_VAR, MSDP_VAL, MSDP_TABLE_OPEN, MSDP_TABLE_CLOSE)
)
# returns 2-tuple
msdp_regex_array = re.compile(
    rb"%s\s*(\w*?)\s*%s\s*%s(.*?)%s" % (MSDP_VAR, MSDP_VAL, MSDP_ARRAY_OPEN, MSDP_ARRAY_CLOSE)
)
msdp_regex_var = re.compile(rb"%s" % MSDP_VAR)
msdp_regex_val = re.compile(rb"%s" % MSDP_VAL)

EVENNIA_TO_GMCP = {
    "client_options": "Core.Supports.Get",
    "get_inputfuncs": "Core.Commands.Get",
    "get_value": "Char.Value.Get",
    "repeat": "Char.Repeat.Update",
    "monitor": "Char.Monitor.Update",
}


# MSDP/GMCP communication handler


class TelnetOOB:
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
        self.protocol = weakref.ref(protocol)
        self.protocol().protocol_flags["OOB"] = False
        self.MSDP = False
        self.GMCP = False
        # ask for the available protocols and assign decoders
        # (note that handshake_done() will be called twice!)
        self.protocol().negotiationMap[MSDP] = self.decode_msdp
        self.protocol().negotiationMap[GMCP] = self.decode_gmcp
        self.protocol().will(MSDP).addCallbacks(self.do_msdp, self.no_msdp)
        self.protocol().will(GMCP).addCallbacks(self.do_gmcp, self.no_gmcp)
        self.oob_reported = {}

    def no_msdp(self, option):
        """
        Client reports No msdp supported or wanted.

        Args:
            option (Option): Not used.

        """
        # no msdp, check GMCP
        self.protocol().handshake_done()

    def do_msdp(self, option):
        """
        Client reports that it supports msdp.

        Args:
            option (Option): Not used.

        """
        self.MSDP = True
        self.protocol().protocol_flags["OOB"] = True
        self.protocol().handshake_done()

    def no_gmcp(self, option):
        """
        If this is reached, it means neither MSDP nor GMCP is
        supported.

        Args:
            option (Option): Not used.

        """
        self.protocol().handshake_done()

    def do_gmcp(self, option):
        """
        Called when client confirms that it can do MSDP or GMCP.

        Args:
            option (Option): Not used.

        """
        self.GMCP = True
        self.protocol().protocol_flags["OOB"] = True
        self.protocol().handshake_done()

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
            ::

                [cmdname, [], {}]           -> VAR cmdname VAL ""
                [cmdname, [arg], {}]        -> VAR cmdname VAL arg
                [cmdname, [args],{}]        -> VAR cmdname VAL ARRAYOPEN VAL arg VAL arg ... ARRAYCLOSE
                [cmdname, [], {kwargs}]     -> VAR cmdname VAL TABLEOPEN VAR key VAL val ... TABLECLOSE
                [cmdname, [args], {kwargs}] -> VAR cmdname VAL ARRAYOPEN VAL arg VAL arg ... ARRAYCLOSE
                                               VAR cmdname VAL TABLEOPEN VAR key VAL val ... TABLECLOSE

            Further nesting is not supported, so if an array argument
            consists of an array (for example), that array will be
            json-converted to a string.

        """
        msdp_cmdname = "{msdp_var}{msdp_cmdname}{msdp_val}".format(
            msdp_var=MSDP_VAR.decode(), msdp_cmdname=cmdname, msdp_val=MSDP_VAL.decode()
        )

        if not (args or kwargs):
            return msdp_cmdname.encode()

        # print("encode_msdp in:", cmdname, args, kwargs)  # DEBUG

        msdp_args = ""
        if args:
            msdp_args = msdp_cmdname
            if len(args) == 1:
                msdp_args += args[0]
            else:
                msdp_args += (
                    "{msdp_array_open}"
                    "{msdp_args}"
                    "{msdp_array_close}".format(
                        msdp_array_open=MSDP_ARRAY_OPEN.decode(),
                        msdp_array_close=MSDP_ARRAY_CLOSE.decode(),
                        msdp_args="".join("%s%s" % (MSDP_VAL.decode(), val) for val in args),
                    )
                )

        msdp_kwargs = ""
        if kwargs:
            msdp_kwargs = msdp_cmdname
            msdp_kwargs += (
                "{msdp_table_open}"
                "{msdp_kwargs}"
                "{msdp_table_close}".format(
                    msdp_table_open=MSDP_TABLE_OPEN.decode(),
                    msdp_table_close=MSDP_TABLE_CLOSE.decode(),
                    msdp_kwargs="".join(
                        "%s%s%s%s" % (MSDP_VAR.decode(), key, MSDP_VAL.decode(), val)
                        for key, val in kwargs.items()
                    ),
                )
            )

        msdp_string = msdp_args + msdp_kwargs

        # print("msdp_string:", msdp_string)  # DEBUG
        return msdp_string.encode()

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
            to have adopted). A cmdname without Package will end
            up in the Core package, while Core package names will
            be stripped on the Evennia side.
            ::

                [cmd_name, [], {}]          -> Cmd.Name
                [cmd_name, [arg], {}]       -> Cmd.Name arg
                [cmd_name, [args],{}]       -> Cmd.Name [args]
                [cmd_name, [], {kwargs}]    -> Cmd.Name {kwargs}
                [cmdname, [args, {kwargs}]  -> Core.Cmdname [[args],{kwargs}]

            For more flexibility with certain clients, if `cmd_name` is capitalized,
            Evennia will leave its current capitalization (So CMD_nAmE would be sent
            as CMD.nAmE but cMD_Name would be Cmd.Name)

        Notes:
            There are also a few default mappings between evennia outputcmds and GMCP:
            ::

                client_options -> Core.Supports.Get
                get_inputfuncs -> Core.Commands.Get
                get_value      -> Char.Value.Get
                repeat         -> Char.Repeat.Update
                monitor        -> Char.Monitor.Update

        """

        if cmdname in EVENNIA_TO_GMCP:
            gmcp_cmdname = EVENNIA_TO_GMCP[cmdname]
        elif "_" in cmdname:
            # enforce initial capitalization of each command part, leaving fully-capitalized sections intact
            gmcp_cmdname = ".".join(
                word.capitalize() if not word.isupper() else word for word in cmdname.split("_")
            )
        else:
            gmcp_cmdname = "Core.%s" % (cmdname if cmdname.istitle() else cmdname.capitalize())

        if not (args or kwargs):
            gmcp_string = gmcp_cmdname
        elif args:
            if len(args) == 1:
                args = args[0]
            if kwargs:
                gmcp_string = "%s %s" % (gmcp_cmdname, json.dumps([args, kwargs]))
            else:
                gmcp_string = "%s %s" % (gmcp_cmdname, json.dumps(args))
        else:  # only kwargs
            gmcp_string = "%s %s" % (gmcp_cmdname, json.dumps(kwargs))

        # print("gmcp string", gmcp_string)  # DEBUG
        return gmcp_string.encode()

    def decode_msdp(self, data):
        """
        Decodes incoming MSDP data.

        Args:
            data (str or list): MSDP data.

        Notes:
            Clients should always send MSDP data on
            one of the following forms:
            ::

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
        if isinstance(data, list):
            data = b"".join(data)

        # print("decode_msdp in:", data)  # DEBUG

        tables = {}
        arrays = {}
        variables = {}

        # decode tables
        for key, table in msdp_regex_table.findall(data):
            key = key.decode()
            tables[key] = {} if key not in tables else tables[key]
            for varval in msdp_regex_var.split(table)[1:]:
                var, val = msdp_regex_val.split(varval, 1)
                var, val = var.decode(), val.decode()
                if var:
                    tables[key][var] = val

        # decode arrays from all that was not a table
        data_no_tables = msdp_regex_table.sub(b"", data)
        for key, array in msdp_regex_array.findall(data_no_tables):
            key = key.decode()
            arrays[key] = [] if key not in arrays else arrays[key]
            parts = msdp_regex_val.split(array)
            parts = [part.decode() for part in parts]
            if len(parts) == 2:
                arrays[key].append(parts[1])
            elif len(parts) > 1:
                arrays[key].extend(parts[1:])

        # decode remainders from all that were not tables or arrays
        data_no_tables_or_arrays = msdp_regex_array.sub(b"", data_no_tables)
        for varval in msdp_regex_var.split(data_no_tables_or_arrays):
            # get remaining varvals after cleaning away tables/arrays. If mathcing
            # an existing key in arrays, it will be added as an argument to that command,
            # otherwise it will be treated as a command without argument.
            parts = msdp_regex_val.split(varval)
            parts = [part.decode() for part in parts]
            if len(parts) == 2:
                variables[parts[0]] = parts[1]
            elif len(parts) > 1:
                variables[parts[0]] = parts[1:]

        cmds = {}
        # merge matching table/array/variables together
        for key, table in tables.items():
            args, kwargs = [], table
            if key in arrays:
                args.extend(arrays.pop(key))
            if key in variables:
                args.append(variables.pop(key))
            cmds[key] = [args, kwargs]

        for key, arr in arrays.items():
            args, kwargs = arr, {}
            if key in variables:
                args.append(variables.pop(key))
            cmds[key] = [args, kwargs]

        for key, var in variables.items():
            cmds[key] = [[var], {}]

        # remap the 'generic msdp commands' to avoid colliding with builtins etc
        # by prepending "msdp_"
        lower_case = {key.lower(): key for key in cmds}
        for remap in ("list", "report", "reset", "send", "unreport"):
            if remap in lower_case:
                cmds["msdp_{}".format(remap)] = cmds.pop(lower_case[remap])

        # print("msdp data in:", cmds)  # DEBUG
        self.protocol().data_in(**cmds)

    def decode_gmcp(self, data):
        """
        Decodes incoming GMCP data on the form 'varname <structure>'.

        Args:
            data (str or list): GMCP data.

        Notes:
            Clients send data on the form "Module.Submodule.Cmdname <structure>".
            We assume the structure is valid JSON.

            The following is parsed into Evennia's formal structure:
            ::

                Core.Name                         -> [name, [], {}]
                Core.Name string                  -> [name, [string], {}]
                Core.Name [arg, arg,...]          -> [name, [args], {}]
                Core.Name {key:arg, key:arg, ...} -> [name, [], {kwargs}]
                Core.Name [[args], {kwargs}]      -> [name, [args], {kwargs}]

        """
        if isinstance(data, list):
            data = b"".join(data)

        # print("decode_gmcp in:", data)  # DEBUG
        if data:
            try:
                cmdname, structure = data.split(None, 1)
            except ValueError:
                cmdname, structure = data, b""
            cmdname = cmdname.replace(b".", b"_")
            try:
                structure = json.loads(structure)
            except ValueError:
                # maybe the structure is not json-serialized at all
                pass
            args, kwargs = [], {}
            if is_iter(structure):
                if isinstance(structure, dict):
                    kwargs = {key: value for key, value in structure.items() if key}
                else:
                    args = list(structure)
            else:
                args = (structure,)
            if cmdname.lower().startswith(b"core_"):
                # if Core.cmdname, then use cmdname
                cmdname = cmdname[5:]
            self.protocol().data_in(**{cmdname.lower().decode(): [args, kwargs]})

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
            encoded_oob = self.encode_msdp(cmdname, *args, **kwargs)
            self.protocol()._write(IAC + SB + MSDP + encoded_oob + IAC + SE)

        if self.GMCP:
            encoded_oob = self.encode_gmcp(cmdname, *args, **kwargs)
            self.protocol()._write(IAC + SB + GMCP + encoded_oob + IAC + SE)
