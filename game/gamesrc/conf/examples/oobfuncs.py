"""

** OBS This module is not yet used by Evennia **

 Example module holding functions for out-of-band protocols to
 import and map to given commands from the client. This module
 is selected by settings.OOB_FUNC_MODULE.

 All functions defined global in this module will be available
 for the oob system to call. They will be called in the following
 way:

 a session/character
 as first argument (depending on if the session is logged in or not),
 following by any number of extra arguments. The return value will
 be packed and returned to the oob protocol and can be on any form.


"""

def testoob(character, *args, **kwargs):
    "Simple test function"
    print "Called testoob: %s" % val
    return "testoob did stuff to the input string '%s'!" % val


# MSDP_MAP is a standard suggestions for making it easy to create generic guis.
# this maps MSDP command names to Evennia commands found in OOB_FUNC_MODULE. It
# is up to these commands to return data on proper form.
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
