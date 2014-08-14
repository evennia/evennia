"""

MSDP (Mud Server Data Protocol)

This implements the MSDP protocol as per
http://tintin.sourceforge.net/msdp/.  MSDP manages out-of-band
communication between the client and server, for updating health bars
etc.

"""
import re
from src.utils.utils import to_str

# MSDP-relevant telnet cmd/opt-codes
MSDP = chr(69)
MSDP_VAR = chr(1)
MSDP_VAL = chr(2)
MSDP_TABLE_OPEN = chr(3)
MSDP_TABLE_CLOSE = chr(4)
MSDP_ARRAY_OPEN = chr(5)
MSDP_ARRAY_CLOSE = chr(6)

IAC = chr(255)
SB = chr(250)
SE = chr(240)

force_str = lambda inp: to_str(inp, force_string=True)

# pre-compiled regexes
# returns 2-tuple
regex_array = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL,
                                                  MSDP_ARRAY_OPEN,
                                                  MSDP_ARRAY_CLOSE))
# returns 2-tuple (may be nested)
regex_table = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL,
                                                  MSDP_TABLE_OPEN,
                                                  MSDP_TABLE_CLOSE))
regex_var = re.compile(MSDP_VAR)
regex_val = re.compile(MSDP_VAL)


# Msdp object handler

class Msdp(object):
    """
    Implements the MSDP protocol.
    """

    def __init__(self, protocol):
        """
        Initiates by storing the protocol
        on itself and trying to determine
        if the client supports MSDP.
        """
        self.protocol = protocol
        self.protocol.protocol_flags['MSDP'] = False
        self.protocol.negotiationMap[MSDP] = self.msdp_to_evennia
        self.protocol.will(MSDP).addCallbacks(self.do_msdp, self.no_msdp)
        self.msdp_reported = {}

    def no_msdp(self, option):
        "No msdp supported or wanted"
        self.protocol.handshake_done()

    def do_msdp(self, option):
        """
        Called when client confirms that it can do MSDP.
        """
        self.protocol.protocol_flags['MSDP'] = True
        self.protocol.handshake_done()

    def evennia_to_msdp(self, cmdname, *args, **kwargs):
        """
        handle return data from cmdname by converting it to
        a proper msdp structure. data can either be a single value (will be
        converted to a string), a list (will be converted to an MSDP_ARRAY),
        or a dictionary (will be converted to MSDP_TABLE).

        OBS - there is no actual use of arrays and tables in the MSDP
        specification or default commands -- are returns are implemented
        as simple lists or named lists (our name for them here, these
        un-bounded structures are not named in the specification). So for
        now, this routine will not explicitly create arrays nor tables,
        although there are helper methods ready should it be needed in
        the future.
        """

        def make_table(name, **kwargs):
            "build a table that may be nested with other tables or arrays."
            string = MSDP_VAR + force_str(name) + MSDP_VAL + MSDP_TABLE_OPEN
            for key, val in kwargs.items():
                if isinstance(val, dict):
                    string += make_table(string, key, **val)
                elif hasattr(val, '__iter__'):
                    string += make_array(string, key, *val)
                else:
                    string += MSDP_VAR + force_str(key) + MSDP_VAL + force_str(val)
            string += MSDP_TABLE_CLOSE
            return string

        def make_array(name, *args):
            "build a array. Arrays may not nest tables by definition."
            string = MSDP_VAR + force_str(name) + MSDP_ARRAY_OPEN
            string += MSDP_VAL.join(force_str(arg) for arg in args)
            string += MSDP_ARRAY_CLOSE
            return string

        def make_list(name, *args):
            "build a simple list - an array without start/end markers"
            string = MSDP_VAR + force_str(name)
            string += MSDP_VAL.join(force_str(arg) for arg in args)
            return string

        def make_named_list(name, **kwargs):
            "build a named list - a table without start/end markers"
            string = MSDP_VAR + force_str(name)
            for key, val in kwargs.items():
                string += MSDP_VAR + force_str(key) + MSDP_VAL + force_str(val)
            return string

        # Default MSDP commands

        print "MSDP outgoing:", cmdname, args, kwargs

        cupper = cmdname.upper()
        if cupper == "LIST":
            if args:
                args = list(args)
                mode = args.pop(0).upper()
            self.data_out(make_array(mode, *args))
        elif cupper == "REPORT":
            self.data_out(make_list("REPORT", *args))
        elif cupper == "UNREPORT":
            self.data_out(make_list("UNREPORT", *args))
        elif cupper == "RESET":
            self.data_out(make_list("RESET", *args))
        elif cupper == "SEND":
            self.data_out(make_named_list("SEND", **kwargs))
        else:
            # return list or named lists.
            msdp_string = ""
            if args:
                msdp_string += make_list(cupper, *args)
            if kwargs:
                msdp_string += make_named_list(cupper, **kwargs)
            self.data_out(msdp_string)

    def msdp_to_evennia(self, data):
        """
        Handle a client's requested negotiation, converting
        it into a function mapping - either one of the MSDP
        default functions (LIST, SEND etc) or a custom one
        in OOB_FUNCS dictionary. command names are case-insensitive.

        varname, var  --> mapped to function varname(var)
        arrayname, array --> mapped to function arrayname(*array)
        tablename, table --> mapped to function tablename(**table)

        Note: Combinations of args/kwargs to one function is not supported
        in this implementation (it complicates the code for limited
        gain - arrayname(*array) is usually as complex as anyone should
        ever need to go anyway (I hope!).

        """
        tables = {}
        arrays = {}
        variables = {}

        if hasattr(data, "__iter__"):
            data = "".join(data)

        #logger.log_infomsg("MSDP SUBNEGOTIATION: %s" % data)

        for key, table in regex_table.findall(data):
            tables[key] = {}
            for varval in regex_var.split(table):
                parts = regex_val.split(varval)
                tables[key].expand({parts[0]: tuple(parts[1:]) if len(parts) > 1 else ("",)})
        for key, array in regex_array.findall(data):
            arrays[key] = []
            for val in regex_val.split(array):
                arrays[key].append(val)
            arrays[key] = tuple(arrays[key])
        for varval in regex_var.split(regex_array.sub("", regex_table.sub("", data))):
            # get remaining varvals after cleaning away tables/arrays
            parts = regex_val.split(varval)
            variables[parts[0].upper()] = tuple(parts[1:]) if len(parts) > 1 else ("", )

        #print "MSDP: table, array, variables:", tables, arrays, variables

        # all variables sent through msdp to Evennia are considered commands
        # with arguments. There are three forms of commands possible
        # through msdp:
        #
        # VARNAME VAR -> varname(var)
        # ARRAYNAME VAR VAL VAR VAL VAR VAL ENDARRAY -> arrayname(val,val,val)
        # TABLENAME TABLE VARNAME VAL VARNAME VAL ENDTABLE ->
        #                                    tablename(varname=val, varname=val)
        #

        # default MSDP functions
        if "LIST" in variables:
            self.data_in("list", *variables.pop("LIST"))
        if "REPORT" in variables:
            self.data_in("report", *variables.pop("REPORT"))
        if "REPORT" in arrays:
            self.data_in("report", *(arrays.pop("REPORT")))
        if "UNREPORT" in variables:
            self.data_in("unreport", *(arrays.pop("UNREPORT")))
        if "RESET" in variables:
            self.data_in("reset", *variables.pop("RESET"))
        if "RESET" in arrays:
            self.data_in("reset", *(arrays.pop("RESET")))
        if "SEND" in variables:
            self.data_in("send", *variables.pop("SEND"))
        if "SEND" in arrays:
            self.data_in("send", *(arrays.pop("SEND")))

        # if there are anything left consider it a call to a custom function

        for varname, var in variables.items():
            # a simple function + argument
            self.data_in(varname, (var,))
        for arrayname, array in arrays.items():
            # we assume the array are multiple arguments to the function
            self.data_in(arrayname, *array)
        for tablename, table in tables.items():
            # we assume tables are keyword arguments to the function
            self.data_in(tablename, **table)

    def data_out(self, msdp_string):
        """
        Return a msdp-valid subnegotiation across the protocol.
        """
        #print "msdp data_out (without IAC SE):", msdp_string
        self.protocol ._write(IAC + SB + MSDP + force_str(msdp_string) + IAC + SE)

    def data_in(self, funcname, *args, **kwargs):
        """
        Send oob data to Evennia
        """
        #print "msdp data_in:", funcname, args, kwargs
        self.protocol.data_in(text=None, oob=(funcname, args, kwargs))
