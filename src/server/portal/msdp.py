"""

MSDP (Mud Server Data Protocol)

This implements the MSDP protocol as per
http://tintin.sourceforge.net/msdp/.  MSDP manages out-of-band
communication between the client and server, for updating health bars
etc.

!TODO - this is just a partial implementation and not used by telnet yet.

"""
import re
from django.conf import settings
from src.utils.utils import make_iter, mod_import, to_str
from src.utils import logger

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
regex_array = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL, MSDP_ARRAY_OPEN, MSDP_ARRAY_CLOSE)) # return 2-tuple
regex_table = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL, MSDP_TABLE_OPEN, MSDP_TABLE_CLOSE)) # return 2-tuple (may be nested)
regex_var = re.compile(MSDP_VAR)
regex_val = re.compile(MSDP_VAL)

# MSDP default definition commands supported by Evennia (can be supplemented with custom commands as well)
MSDP_COMMANDS = ("LIST", "REPORT", "RESET", "SEND", "UNREPORT")

# fallbacks if no custom OOB module is available
MSDP_COMMANDS_CUSTOM = {}
# MSDP_REPORTABLE is a standard suggestions for making it easy to create generic guis.
# this maps MSDP command names to Evennia commands found in OOB_FUNC_MODULE. It
# is up to these commands to return data on proper form. This is overloaded if
# OOB_REPORTABLE is defined in the custom OOB module below.
MSDP_REPORTABLE = {
    # General
    "CHARACTER_NAME": "get_character_name",
    "SERVER_ID": "get_server_id",
    "SERVER_TIME": "get_server_time",
    # Character
    "AFFECTS": "char_affects",
    "ALIGNMENT": "char_alignment",
    "EXPERIENCE": "char_experience",
    "EXPERIENCE_MAX": "char_experience_max",
    "EXPERIENCE_TNL": "char_experience_tnl",
    "HEALTH": "char_health",
    "HEALTH_MAX": "char_health_max",
    "LEVEL": "char_level",
    "RACE": "char_race",
    "CLASS": "char_class",
    "MANA": "char_mana",
    "MANA_MAX": "char_mana_max",
    "WIMPY": "char_wimpy",
    "PRACTICE": "char_practice",
    "MONEY": "char_money",
    "MOVEMENT": "char_movement",
    "MOVEMENT_MAX": "char_movement_max",
    "HITROLL": "char_hitroll",
    "DAMROLL": "char_damroll",
    "AC": "char_ac",
    "STR": "char_str",
    "INT": "char_int",
    "WIS": "char_wis",
    "DEX": "char_dex",
    "CON": "char_con",
    # Combat
    "OPPONENT_HEALTH": "opponent_health",
    "OPPONENT_HEALTH_MAX":"opponent_health_max",
    "OPPONENT_LEVEL": "opponent_level",
    "OPPONENT_NAME": "opponent_name",
    # World
    "AREA_NAME": "area_name",
    "ROOM_EXITS": "area_room_exits",
    "ROOM_NAME": "room_name",
    "ROOM_VNUM": "room_dbref",
    "WORLD_TIME": "world_time",
    # Configurable variables
    "CLIENT_ID": "client_id",
    "CLIENT_VERSION": "client_version",
    "PLUGIN_ID": "plugin_id",
    "ANSI_COLORS": "ansi_colours",
    "XTERM_256_COLORS": "xterm_256_colors",
    "UTF_8": "utf_8",
    "SOUND": "sound",
    "MXP": "mxp",
   # GUI variables
    "BUTTON_1": "button1",
    "BUTTON_2": "button2",
    "BUTTON_3": "button3",
    "BUTTON_4": "button4",
    "BUTTON_5": "button5",
    "GAUGE_1": "gauge1",
    "GAUGE_2": "gauge2",
    "GAUGE_3": "gauge3",
    "GAUGE_4": "gauge4",
    "GAUGE_5": "gauge5"}
MSDP_SENDABLE = MSDP_REPORTABLE

# try to load custom OOB module
OOB_MODULE = None#mod_import(settings.OOB_FUNC_MODULE)
if OOB_MODULE:
    # loading customizations from OOB_FUNC_MODULE if available
    try: MSDP_REPORTABLE = OOB_MODULE.OOB_REPORTABLE # replaces the default MSDP definitions
    except AttributeError: pass
    try: MSDP_SENDABLE = OOB_MODULE.OOB_SENDABLE
    except AttributeError: MSDP_SENDABLE = MSDP_REPORTABLE
    try: MSDP_COMMANDS_CUSTOM = OOB_MODULE.OOB_COMMANDS
    except: pass

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
        pass

    def do_msdp(self, option):
        """
        Called when client confirms that it can do MSDP.
        """
        self.protocol.protocol_flags['MSDP'] = True

    def evennia_to_msdp(self, cmdname, *args, **kwargs):
        """
        handle return data from cmdname by converting it to
        a proper msdp structure. data can either be a single value (will be
        converted to a string), a list (will be converted to an MSDP_ARRAY),
        or a dictionary (will be converted to MSDP_TABLE).

        Obs - this normally only returns tables and lists (var val val ...) rather than
        arrays.  It will convert *args to lists and **kwargs to tables and
        if both are given to this method, this will result in a list followed
        by a table, both having the same names.
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

        # Default MSDP commands

        cupper = cmdname.upper()
        if cupper == "LIST":
            self.data_out(make_list("LIST", *args))
        elif cupper == "REPORT":
            self.data_out(make_list("REPORT", *args))
        elif cupper == "UNREPORT":
            self.data_out(make_list("UNREPORT", *args))
        elif cupper == "RESET":
            self.data_out(make_list("RESET", *args))
        elif cupper == "SEND":
            self.data_out(make_list("SEND", *args))
        else:
            # return list or tables. If both arg/kwarg is given, return one array and one table, both
            # with the same name.
            msdp_string = ""
            if args:
                msdp_string += make_list(cupper, *args)
            if kwargs:
                msdp_string += make_table(cupper, **kwargs)
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
                tables[key].expand({parts[0] : tuple(parts[1:]) if len(parts)>1 else ("",)})
        for key, array in regex_array.findall(data):
            arrays[key] = []
            for val in regex_val.split(array):
                arrays[key].append(val)
            arrays[key] = tuple(arrays[key])
        for varval in regex_var.split(regex_array.sub("", regex_table.sub("", data))):
            # get remaining varvals after cleaning away tables/arrays
            parts = regex_val.split(varval)
            variables[parts[0].upper()] = tuple(parts[1:]) if len(parts)>1 else ("", )

        #print "MSDP: table, array, variables:", tables, arrays, variables

        # all variables sent through msdp to Evennia are considered commands with arguments.
        # there are three forms of commands possible through msdp:
        #
        # VARNAME VAR -> varname(var)
        # ARRAYNAME VAR VAL VAR VAL VAR VAL ENDARRAY -> arrayname(val,val,val)
        # TABLENAME TABLE VARNAME VAL VARNAME VAL ENDTABLE -> tablename(varname=val, varname=val)
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

   # # MSDP Commands
   # # Some given MSDP (varname, value) pairs can also be treated as command + argument.
   # # Generic msdp command map. The argument will be sent to the given command.
   # # See http://tintin.sourceforge.net/msdp/ for definitions of each command.
   # # These are client->server commands.
   # def msdp_cmd_list(self, arg):
   #     """
   #     The List command allows for retrieving various info about the server/client
   #     """
   #     if arg == 'COMMANDS':
   #         return self.evennia_to_msdp(arg, MSDP_COMMANDS)
   #     elif arg == 'LISTS':
   #         return self.evennia_to_msdp(arg, ("COMMANDS", "LISTS", "CONFIGURABLE_VARIABLES",
   #                                        "REPORTED_VARIABLES", "SENDABLE_VARIABLES"))
   #     elif arg == 'CONFIGURABLE_VARIABLES':
   #         return self.evennia_to_msdp(arg, ("CLIENT_NAME", "CLIENT_VERSION", "PLUGIN_ID"))
   #     elif arg == 'REPORTABLE_VARIABLES':
   #         return self.evennia_to_msdp(arg, MSDP_REPORTABLE.keys())
   #     elif arg == 'REPORTED_VARIABLES':
   #         # the dynamically set items to report
   #         return self.evennia_to_msdp(arg, self.msdp_reported.keys())
   #     elif arg == 'SENDABLE_VARIABLES':
   #         return self.evennia_to_msdp(arg, MSDP_SENDABLE.keys())
   #     else:
   #         return self.evennia_to_msdp("LIST", arg)

   # # default msdp commands

   # def msdp_cmd_report(self, *arg):
   #     """
   #     The report command instructs the server to start reporting a
   #     reportable variable to the client.
   #     """
   #     try:
   #         return MSDP_REPORTABLE[arg](report=True)
   #     except Exception:
   #         logger.log_trace()

   # def msdp_cmd_unreport(self, arg):
   #     """
   #     Unreport a previously reported variable
   #     """
   #     try:
   #         MSDP_REPORTABLE[arg](report=False)
   #     except Exception:
   #         self.logger.log_trace()

   # def msdp_cmd_reset(self, arg):
   #     """
   #     The reset command resets a variable to its initial state.
   #     """
   #     try:
   #         MSDP_REPORTABLE[arg](reset=True)
   #     except Exception:
   #         logger.log_trace()

   # def msdp_cmd_send(self, *args):
   #     """
   #     Request the server to send a particular variable
   #     to the client.

   #     arg - this is a list of variables the client wants.
   #     """
   #     ret = []
   #     for var in make_iter(arg)




   #         for var in make_iter(arg):
   #             try:
   #                 ret.append(MSDP_REPORTABLE[var.upper()])# (send=True))
   #             except Exception:
   #                 ret.append("ERROR")#logger.log_trace()
   #     return ret


