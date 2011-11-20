"""

MSDP (Mud Server Data Protocol)

This implements the MSDP protocol as per
http://tintin.sourceforge.net/msdp/.  MSDP manages out-of-band
communication between the client and server, for updating health bars
etc.

!TODO - this is just a partial implementation and not used by telnet yet.

"""
import re

# variables
MSDP = chr(69)
MSDP_VAR = chr(1)
MSDP_VAL = chr(2)
MSDP_TABLE_OPEN = chr(3)
MSDP_TABLE_CLOSE = chr(4)
MSDP_ARRAY_OPEN = chr(5)
MSDP_ARRAY_CLOSE = chr(6)

regex_array = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL, MSDP_ARRAY_OPEN, MSDP_ARRAY_CLOSE)) # return 2-tuple
regex_table = re.compile(r"%s(.*?)%s%s(.*?)%s" % (MSDP_VAR, MSDP_VAL, MSDP_TABLE_OPEN, MSDP_TABLE_CLOSE)) # return 2-tuple (may be nested)
regex_varval = re.compile(r"%s(.*?)%s(.*?)[%s]" % (MSDP_VAR, MSDP_VAL, ENDING)) # return 2-tuple

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

    def no_msdp(self, option):
        "No msdp"
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
        it into a function mapping

        OBS-this does not support receiving nested tables 
        from the client at this point! 
        """
        tables = {}
        arrays = {}
        variables = {}

        for table in regex_table.findall(data):
            tables[table[0]] = dict(regex_varval(table[1]))
        for array in regex_array.findall(data):
            arrays[array[0]] = dict(regex_varval(array[1]))
        variables = dict(regex._varval(regex_array.sub("", regex_table.sub("", data))))
    
    # Some given MSDP (varname, value) pairs can also be treated as command + argument. 
    # Generic msdp command map. The argument will be sent to the given command.
    # See http://tintin.sourceforge.net/msdp/ for definitions of each command. 
    MSDP_COMMANDS = {
        "LIST": "msdp_list",
        "REPORT":"mspd_report",
        "RESET":"mspd_reset",
        "SEND":"mspd_send",
        "UNREPORT":"mspd_unreport"
        }


    # MSDP_MAP is a standard suggestions for making it easy to create generic guis.         
    # this maps MSDP command names to Evennia commands found in OOB_FUNC_MODULE. It
    # is up to these commands to return data on proper form. 
    MSDP_MAP = {
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
