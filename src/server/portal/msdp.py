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
from src.utils.utils import make_iter, mod_import
from src.utils import logger

# MSDP-relevant telnet cmd/opt-codes
MSDP = chr(69)
MSDP_VAR = chr(1)
MSDP_VAL = chr(2)
MSDP_TABLE_OPEN = chr(3)
MSDP_TABLE_CLOSE = chr(4)
MSDP_ARRAY_OPEN = chr(5)
MSDP_ARRAY_CLOSE = chr(6)

# pre-compiled regexes
regex_array = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL, MSDP_ARRAY_OPEN, MSDP_ARRAY_CLOSE)) # return 2-tuple
regex_table = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL, MSDP_TABLE_OPEN, MSDP_TABLE_CLOSE)) # return 2-tuple (may be nested)
regex_varval = re.compile(r"%s(.*?)%s(.*?)" % (MSDP_VAR, MSDP_VAL)) # return 2-tuple

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
OOB_MODULE = mod_import(settings.OOB_FUNC_MODULE)
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
        self.protocol.protocol_FLAGS['MSDP'] = False
        self.protocol.negotiationMap['MSDP'] = self.parse_msdp
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

    def func_to_msdp(self, cmdname, data):
        """
        handle return data from cmdname by converting it to
        a proper msdp structure. data can either be a single value (will be
        converted to a string), a list (will be converted to an MSDP_ARRAY),
        or a dictionary (will be converted to MSDP_TABLE).

        OBS - this supports nested tables and even arrays nested
        inside tables, as opposed to the receive method. Arrays
        cannot hold tables by definition (the table must be named
        with MSDP_VAR, and an array can only contain MSDP_VALs).
        """

        def make_table(name, datadict, string):
            "build a table that may be nested with other tables or arrays."
            string += MSDP_VAR + name + MSDP_VAL + MSDP_TABLE_OPEN
            for key, val in datadict.items():
                if type(val) == type({}):
                    string += make_table(key, val, string)
                elif hasattr(val, '__iter__'):
                    string += make_array(key, val, string)
                else:
                    string += MSDP_VAR + key + MSDP_VAL + val
            string += MSDP_TABLE_CLOSE
            return string

        def make_array(name, string, datalist):
            "build a simple array. Arrays may not nest tables by definition."
            string += MSDP_VAR + name + MSDP_ARRAY_OPEN
            for val in datalist:
                string += MSDP_VAL + val
            string += MSDP_ARRAY_CLOSE
            return string

        if type(data) == type({}):
            msdp_string = make_table(cmdname, data, "")
        elif hasattr(data, '__iter__'):
            msdp_string = make_array(cmdname, data, "")
        else:
            msdp_string = MSDP_VAR + cmdname + MSDP_VAL + data
        return msdp_string


    def msdp_to_func(self, data):
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

        for table in regex_table.findall(data):
            tables[table[0].upper()] = dict(regex_varval(table[1]))
        for array in regex_array.findall(data):
            arrays[array[0].upper()] = dict(regex_varval(array[1]))
        variables = dict((key.upper(), val) for key, val in regex_varval(regex_array.sub("", regex_table.sub("", data))))

        ret = ""

        # default MSDP functions
        if "LIST" in variables:
            ret += self.func_to_msdp("LIST", self.msdp_cmd_list(variables["LIST"]))
            del variables["LIST"]
        if "REPORT" in variables:
            ret += self.func_to_msdp("REPORT", self.msdp_cmd_report(*(variables["REPORT"],)))
            del variables["REPORT"]
        if "REPORT" in arrays:
            ret += self.func_to_msdp("REPORT", self.msdp_cmd_report(*arrays["REPORT"]))
            del arrays["REPORT"]
        if "RESET" in variables:
            ret += self.func_to_msdp("RESET", self.msdp_cmd_reset(*(variables["RESET"],)))
            del variables["RESET"]
        if "RESET" in arrays:
            ret += self.func_to_msdp("RESET", self.msdp_cmd_reset(*arrays["RESET"]))
            del arrays["RESET"]
        if "SEND" in variables:
            ret += self.func_to_msdp("SEND", self.msdp_cmd_send(*(variables["SEND"],)))
            del variables["SEND"]
        if "SEND" in arrays:
            ret += self.func_to_msdp("SEND",self.msdp_cmd_send(*arrays["SEND"]))
            del arrays["SEND"]

        # if there are anything left we look for a custom function
        for varname, var in variables.items():
            # a simple function + argument
            ooc_func = MSDP_COMMANDS_CUSTOM.get(varname.upper())
            if ooc_func:
                ret += self.func_to_msdp(varname, ooc_func(var))
        for arrayname, array in arrays.items():
            # we assume the array are multiple arguments to the function
            ooc_func = MSDP_COMMANDS_CUSTOM.get(arrayname.upper())
            if ooc_func:
                ret += self.func_to_msdp(arrayname, ooc_func(*array))
        for tablename, table in tables.items():
            # we assume tables are keyword arguments to the function
            ooc_func = MSDP_COMMANDS_CUSTOM.get(arrayname.upper())
            if ooc_func:
                ret += self.func_to_msdp(tablename, ooc_func(**table))
        return ret

    # MSDP Commands
    # Some given MSDP (varname, value) pairs can also be treated as command + argument.
    # Generic msdp command map. The argument will be sent to the given command.
    # See http://tintin.sourceforge.net/msdp/ for definitions of each command.
    # These are client->server commands.
    def msdp_cmd_list(self, arg):
        """
        The List command allows for retrieving various info about the server/client
        """
        if arg == 'COMMANDS':
            return self.func_to_msdp(arg, MSDP_COMMANDS)
        elif arg == 'LISTS':
            return self.func_to_msdp(arg, ("COMMANDS", "LISTS", "CONFIGURABLE_VARIABLES",
                                           "REPORTED_VARIABLES", "SENDABLE_VARIABLES"))
        elif arg == 'CONFIGURABLE_VARIABLES':
            return self.func_to_msdp(arg, ("CLIENT_NAME", "CLIENT_VERSION", "PLUGIN_ID"))
        elif arg == 'REPORTABLE_VARIABLES':
            return self.func_to_msdp(arg, MSDP_REPORTABLE.keys())
        elif arg == 'REPORTED_VARIABLES':
            # the dynamically set items to report
            return self.func_to_msdp(arg, self.msdp_reported.keys())
        elif arg == 'SENDABLE_VARIABLES':
            return self.func_to_msdp(arg, MSDP_SENDABLE.keys())
        else:
            return self.func_to_msdp("LIST", arg)

    # default msdp commands

    def msdp_cmd_report(self, *arg):
        """
        The report command instructs the server to start reporting a
        reportable variable to the client.
        """
        try:
            MSDP_REPORTABLE[arg](report=True)
        except Exception:
            logger.log_trace()

    def msdp_cmd_unreport(self, arg):
        """
        Unreport a previously reported variable
        """
        try:
            MSDP_REPORTABLE[arg](report=False)
        except Exception:
            self.logger.log_trace()

    def msdp_cmd_reset(self, arg):
        """
        The reset command resets a variable to its initial state.
        """
        try:
            MSDP_REPORTABLE[arg](reset=True)
        except Exception:
            logger.log_trace()

    def msdp_cmd_send(self, arg):
        """
        Request the server to send a particular variable
        to the client.

        arg - this is a list of variables the client wants.
        """
        ret = []
        for var in make_iter(arg):
            try:
                ret.append(MSDP_REPORTABLE[arg](send=True))
            except Exception:
                logger.log_trace()
        return ret


