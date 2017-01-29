"""

MSSP - Mud Server Status Protocol

This implements the MSSP telnet protocol as per
http://tintin.sourceforge.net/mssp/.  MSSP allows web portals and
listings to have their crawlers find the mud and automatically
extract relevant information about it, such as genre, how many
active players and so on.


"""
from builtins import object
from django.conf import settings
from evennia.utils import utils

MSSP = chr(70)
MSSP_VAR = chr(1)
MSSP_VAL = chr(2)


# try to get the customized mssp info, if it exists.
MSSPTable_CUSTOM = utils.variable_from_module(settings.MSSP_META_MODULE, "MSSPTable", default={})

class Mssp(object):
    """
    Implements the MSSP protocol. Add this to a variable on the telnet
    protocol to set it up.

    """
    def __init__(self, protocol):
        """
        initialize MSSP by storing protocol on ourselves and calling
        the client to see if it supports MSSP.

        Args:
            protocol (Protocol): The active protocol instance.

        """
        self.protocol = protocol
        self.protocol.will(MSSP).addCallbacks(self.do_mssp, self.no_mssp)

    def get_player_count(self):
        """
        Get number of logged-in players.

        Returns:
            count (int): The number of players in the MUD.

        """
        return str(self.protocol.sessionhandler.count_loggedin())

    def get_uptime(self):
        """
        Get how long the portal has been online (reloads are not counted).

        Returns:
            uptime (int): Number of seconds of uptime.

        """
        return str(self.protocol.sessionhandler.uptime)

    def no_mssp(self, option):
        """
        Called when mssp is not requested. This is the normal
        operation.

        Args:
            option (Option): Not used.

        """
        self.protocol.handshake_done()

    def do_mssp(self, option):
        """
        Negotiate all the information.

        Args:
            option (Option): Not used.

        """

        self.mssp_table =  {

        # Required fields

        "NAME":               "Evennia",
        "PLAYERS":            self.get_player_count,
        "UPTIME" :            self.get_uptime,

        # Generic

        "CRAWL DELAY":        "-1",

        "HOSTNAME":           "",       # current or new hostname
        "PORT":               ["4000"], # most important port should be last in list
        "CODEBASE":           "Evennia",
        "CONTACT":            "",       # email for contacting the mud
        "CREATED":            "",       # year MUD was created
        "ICON":               "",       # url to icon 32x32 or larger; <32kb.
        "IP":                 "",       # current or new IP address
        "LANGUAGE":           "",       # name of language used, e.g. English
        "LOCATION":           "",       # full English name of server country
        "MINIMUM AGE":        "0",      # set to 0 if not applicable
        "WEBSITE":            "www.evennia.com",

        # Categorisation

        "FAMILY":             "Custom", # evennia goes under 'Custom'
        "GENRE":              "None",   # Adult, Fantasy, Historical, Horror, Modern, None, or Science Fiction
        "GAMEPLAY":           "None",   # Adventure, Educational, Hack and Slash, None,
                                        # Player versus Player, Player versus Environment,
                                        # Roleplaying, Simulation, Social or Strategy
        "STATUS":             "Open Beta",  # Alpha, Closed Beta, Open Beta, Live
        "GAMESYSTEM":         "Custom", # D&D, d20 System, World of Darkness, etc. Use Custom if homebrew
        "SUBGENRE":           "None",   # LASG, Medieval Fantasy, World War II, Frankenstein,
                                        # Cyberpunk, Dragonlance, etc. Or None if not available.

        # World

        "AREAS":              "0",
        "HELPFILES":          "0",
        "MOBILES":            "0",
        "OBJECTS":            "0",
        "ROOMS":              "0",      # use 0 if room-less
        "CLASSES":            "0",      # use 0 if class-less
        "LEVELS":             "0",      # use 0 if level-less
        "RACES":              "0",      # use 0 if race-less
        "SKILLS":             "0",      # use 0 if skill-less

        # Protocols set to 1 or 0)

        "ANSI":               "1",
        "GMCP":               "0",
        "ATCP":               "0",
        "MCCP":               "0",
        "MCP":                "0",
        "MSDP":               "0",
        "MSP":                "0",
        "MXP":                "0",
        "PUEBLO":             "0",
        "SSL":                "1",
        "UTF-8":              "1",
        "ZMP":                "0",
        "VT100":              "0",
        "XTERM 256 COLORS":   "0",

        # Commercial set to 1 or 0)

        "PAY TO PLAY":        "0",
        "PAY FOR PERKS":      "0",

        # Hiring  set to 1 or 0)

        "HIRING BUILDERS":    "0",
        "HIRING CODERS":      "0",

        # Extended variables

        # World

        "DBSIZE":             "0",
        "EXITS":              "0",
        "EXTRA DESCRIPTIONS": "0",
        "MUDPROGS":           "0",
        "MUDTRIGS":           "0",
        "RESETS":             "0",

        # Game (set to 1, 0 or one of the given alternatives)

        "ADULT MATERIAL":     "0",
        "MULTICLASSING":      "0",
        "NEWBIE FRIENDLY":    "0",
        "PLAYER CITIES":      "0",
        "PLAYER CLANS":       "0",
        "PLAYER CRAFTING":    "0",
        "PLAYER GUILDS":      "0",
        "EQUIPMENT SYSTEM":   "None",  # "None", "Level", "Skill", "Both"
        "MULTIPLAYING":       "None",  # "None", "Restricted", "Full"
        "PLAYERKILLING":      "None",  # "None", "Restricted", "Full"
        "QUEST SYSTEM":       "None",  # "None", "Immortal Run", "Automated", "Integrated"
        "ROLEPLAYING":        "None",  # "None", "Accepted", "Encouraged", "Enforced"
        "TRAINING SYSTEM":    "None",  # "None", "Level", "Skill", "Both"
        "WORLD ORIGINALITY":  "None",  # "All Stock", "Mostly Stock", "Mostly Original", "All Original"
        }

        # update the static table with the custom one
        if MSSPTable_CUSTOM:
            self.mssp_table.update(MSSPTable_CUSTOM)

        varlist = ''
        for variable, value in self.mssp_table.items():
            if callable(value):
                value = value()
            if utils.is_iter(value):
                for partval in value:
                    varlist += MSSP_VAR + str(variable) + MSSP_VAL + str(partval)
            else:
                varlist += MSSP_VAR + str(variable) + MSSP_VAL + str(value)

        # send to crawler by subnegotiation
        self.protocol.requestNegotiation(MSSP, varlist)
        self.protocol.handshake_done()
