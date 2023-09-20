"""

MSSP (Mud Server Status Protocol) meta information

Modify this file to specify what MUD listing sites will report about your game.
All fields are static. The number of currently active players and your game's
current uptime will be added automatically by Evennia.

You don't have to fill in everything (and most fields are not shown/used by all
crawlers anyway); leave the default if so needed. You need to reload the server
before the updated information is made available to crawlers (reloading does
not affect uptime).

After changing the values in this file, you must register your game with the
MUD website list you want to track you. The listing crawler will then regularly
connect to your server to get the latest info. No further configuration is
needed on the Evennia side.

"""

MSSPTable = {
    # Required fields
    "NAME": "Mygame",  # usually the same as SERVERNAME
    # Generic
    "CRAWL DELAY": "-1",  # limit how often crawler may update the listing. -1 for no limit
    "HOSTNAME": "",  # telnet hostname
    "PORT": ["4000"],  # telnet port - most important port should be *last* in list!
    "CODEBASE": "Evennia",
    "CONTACT": "",  # email for contacting the mud
    "CREATED": "",  # year MUD was created
    "ICON": "",  # url to icon 32x32 or larger; <32kb.
    "IP": "",  # current or new IP address
    "LANGUAGE": "",  # name of language used, e.g. English
    "LOCATION": "",  # full English name of server country
    "MINIMUM AGE": "0",  # set to 0 if not applicable
    "WEBSITE": "",  # http:// address to your game website
    # Categorisation
    "FAMILY": "Evennia",
    "GENRE": "None",  # Adult, Fantasy, Historical, Horror, Modern, None, or Science Fiction
    # Gameplay: Adventure, Educational, Hack and Slash, None,
    # Player versus Player, Player versus Environment,
    # Roleplaying, Simulation, Social or Strategy
    "GAMEPLAY": "",
    "STATUS": "Open Beta",  # Allowed: Alpha, Closed Beta, Open Beta, Live
    "GAMESYSTEM": "Custom",  # D&D, d20 System, World of Darkness, etc. Use Custom if homebrew
    # Subgenre: LASG, Medieval Fantasy, World War II, Frankenstein,
    # Cyberpunk, Dragonlance, etc. Or None if not applicable.
    "SUBGENRE": "None",
    # World
    "AREAS": "0",
    "HELPFILES": "0",
    "MOBILES": "0",
    "OBJECTS": "0",
    "ROOMS": "0",  # use 0 if room-less
    "CLASSES": "0",  # use 0 if class-less
    "LEVELS": "0",  # use 0 if level-less
    "RACES": "0",  # use 0 if race-less
    "SKILLS": "0",  # use 0 if skill-less
    # Protocols set to 1 or 0; should usually not be changed)
    "ANSI": "1",
    "GMCP": "1",
    "MSDP": "1",
    "MXP": "1",
    "SSL": "1",
    "UTF-8": "1",
    "MCCP": "1",
    "XTERM 256 COLORS": "1",
    "XTERM TRUE COLORS": "0",
    "ATCP": "0",
    "MCP": "0",
    "MSP": "0",
    "VT100": "0",
    "PUEBLO": "0",
    "ZMP": "0",
    # Commercial set to 1 or 0)
    "PAY TO PLAY": "0",
    "PAY FOR PERKS": "0",
    # Hiring  set to 1 or 0)
    "HIRING BUILDERS": "0",
    "HIRING CODERS": "0",
    # Extended variables
    # World
    "DBSIZE": "0",
    "EXITS": "0",
    "EXTRA DESCRIPTIONS": "0",
    "MUDPROGS": "0",
    "MUDTRIGS": "0",
    "RESETS": "0",
    # Game  (set to 1 or 0, or one of the given alternatives)
    "ADULT MATERIAL": "0",
    "MULTICLASSING": "0",
    "NEWBIE FRIENDLY": "0",
    "PLAYER CITIES": "0",
    "PLAYER CLANS": "0",
    "PLAYER CRAFTING": "0",
    "PLAYER GUILDS": "0",
    "EQUIPMENT SYSTEM": "None",  # "None", "Level", "Skill", "Both"
    "MULTIPLAYING": "None",  # "None", "Restricted", "Full"
    "PLAYERKILLING": "None",  # "None", "Restricted", "Full"
    "QUEST SYSTEM": "None",  # "None", "Immortal Run", "Automated", "Integrated"
    "ROLEPLAYING": "None",  # "None", "Accepted", "Encouraged", "Enforced"
    "TRAINING SYSTEM": "None",  # "None", "Level", "Skill", "Both"
    # World originality: "All Stock", "Mostly Stock", "Mostly Original", "All Original"
    "WORLD ORIGINALITY": "All Original",
}
